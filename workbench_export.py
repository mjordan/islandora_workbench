import os
import sys
import json
import logging
import datetime
import collections
import requests_cache
from workbench_utils import *
from progress_bar import InitBar


class WorkbenchExportBase:
    def __init__(self, config, args=None):
        self.config = config
        self.args = args
        self.field_definitions = get_field_definitions(config, "node")
        self.seen_nids = set()
        self.pbar = InitBar() if config.get("progress_bar") else None

    @staticmethod
    def deduplicate_list(input_list):
        """Remove duplicates while preserving order."""
        seen = set()
        return [x for x in input_list if not (x in seen or seen.add(x))]

    def initialize_csv_writer(self, csv_file, field_names, export_mode=False):
        """Initialize CSV writer with optional metadata rows for export mode."""
        writer = csv.DictWriter(csv_file, fieldnames=field_names, lineterminator="\n")
        writer.writeheader()

        if export_mode and self.field_definitions:
            self._write_metadata_rows(writer, field_names)

        return writer

    def _write_metadata_rows(self, writer, field_names):
        """Write field labels and cardinality rows for export mode."""
        field_labels = collections.OrderedDict()
        for field_name in field_names:
            if (
                field_name in self.field_definitions
                and self.field_definitions[field_name]["label"] != ""
            ):
                field_labels[field_name] = self.field_definitions[field_name]["label"]
            elif field_name == "REMOVE THIS COLUMN (KEEP THIS ROW)":
                field_labels[field_name] = "LABEL (REMOVE THIS ROW)"
            else:
                field_labels[field_name] = ""
        writer.writerow(field_labels)

        cardinality = collections.OrderedDict()
        cardinality["REMOVE THIS COLUMN (KEEP THIS ROW)"] = (
            "NUMBER OF VALUES ALLOWED (REMOVE THIS ROW)"
        )
        cardinality["node_id"] = "1"
        cardinality["uid"] = "1"
        cardinality["langcode"] = "1"
        cardinality["created"] = "1"
        cardinality["title"] = "1"

        for field_name in self.field_definitions:
            if field_name in field_names:
                cardinality[field_name] = (
                    "unlimited"
                    if self.field_definitions[field_name]["cardinality"] == -1
                    else str(self.field_definitions[field_name]["cardinality"])
                )
        writer.writerow(cardinality)

    def process_file_data(self, node_id, media_use_term_id=None, media_list=None):
        """Handle file processing (download or URL) based on config."""
        if self.config.get("export_file_url_instead_of_download", False):
            result = get_media_file_url(
                self.config,
                node_id,
                media_use_term_id=media_use_term_id,
                media_list=media_list,
            )
        else:
            result = download_file_from_drupal(
                self.config,
                node_id,
                media_use_term_id=media_use_term_id,
                media_list=media_list,
            )
        return result if result else ""  # Avoid 'False' values in file columns.

    def log_progress(self, message, row_count=None, total_rows=None, level=logging.INFO):
        """Standardized progress logging with optional progress bar and log levels.

        Args:
            message: The message to log
            row_count: Current row count (for progress bar)
            total_rows: Total rows (for progress bar)
            level: Logging level (e.g., logging.INFO, logging.WARNING, logging.ERROR)
        """
        if (
            self.config.get("progress_bar")
            and self.pbar
            and row_count is not None
            and total_rows is not None
        ):
            self.pbar(get_percentage(row_count, total_rows))
        else:
            print(f"{logging.getLevelName(level)}: {message}")

        # Log to file with appropriate level
        if level == logging.INFO:
            logging.info(message)
        elif level == logging.WARNING:
            logging.warning(message)
        elif level == logging.ERROR:
            logging.error(message)
        elif level == logging.DEBUG:
            logging.debug(message)
        else:
            logging.info(message)  # default to info if unknown level

    def row_log_suffix(self, node, nid, row):
        and_files = ""
        if self.needs_file_column:
            if self.config.get("export_file_url_instead_of_download", False):
                and_files = " and file URL(s)"
            else:
                and_files = " and file(s)"

        return and_files

    def extract_node_id(self, node):
        """Extract and validate node ID."""
        try:
            return node["nid"][0]["value"]
        except (KeyError, IndexError):
            message = "Skipping node with missing/invalid NID"
            self.log_progress(message, level=logging.WARNING)
            return None

    def validate_content_type(self, node, nid):
        """Verify node matches configured content type."""
        try:
            node_type = node["type"][0]["target_id"]
        except (KeyError, IndexError):
            node_type = "unknown"

        if node_type != self.config["content_type"]:
            message = (
                f"Node {nid} not written to output CSV because its content type {node_type}"
                + f' does not match the "content_type" configuration setting.'
            )
            self.log_progress(message, level=logging.ERROR)
            return False
        return True

    def parse_json_response(self, response):
        """Safely parse JSON from response."""
        try:
            return json.loads(response.text)
        except json.decoder.JSONDecodeError as e:
            message = f"Failed to decode JSON: {str(e)}"
            self.log_progress(message, level=logging.WARNING)
            return []

    def needs_file_column(self):
        """Check if we need file column in CSV."""
        return self.config.get(
            "export_file_url_instead_of_download", False
        ) or self.config.get("export_file_directory")

    def get_additional_files_config(self):
        """Get additional files configuration as OrderedDict."""
        if "additional_files" not in self.config:
            return collections.OrderedDict()

        additional_files = collections.OrderedDict()
        for entry in self.config["additional_files"]:
            for col_name, media_use_uri in entry.items():
                additional_files[col_name] = media_use_uri
        return additional_files

    def execute_post_export_script(self, response, node_json):
        """Execute node-specific post-export scripts, if any are configured."""
        if len(self.config.get("node_post_export", [])) > 0:
            for command in self.config.get("node_post_export", []):
                (
                    post_task_output,
                    post_task_return_code,
                ) = execute_entity_post_task_script(
                    command,
                    self.args.config,
                    response.status_code,
                    node_json,
                )
                if post_task_return_code == 0:
                    logging.info(
                        "Post node export script " + command + " executed successfully."
                    )
                else:
                    logging.error("Post node export script " + command + " failed.")


class CSVExporter(WorkbenchExportBase):
    def __init__(self, config, args=None):
        super().__init__(config, args)
        self.csv_data = get_csv_data(config)

    def setup_csv_output_path(self):
        """Set up CSV output path for CSV export."""
        if self.config["export_csv_file_path"]:
            return self.config["export_csv_file_path"]

        csv_path = os.path.join(
            self.config["input_dir"],
            self.config["input_csv"] + ".csv_file_with_field_values",
        )

        if os.path.exists(csv_path):
            os.remove(csv_path)
        return csv_path

    def prepare_headers(self):
        """Generate deduplicated list of CSV column headers for export_csv."""
        field_names = list(self.field_definitions.keys())

        # Add required fields at beginning
        for field_name in [
            "created",
            "uid",
            "langcode",
            "title",
            "node_id",
            "REMOVE THIS COLUMN (KEEP THIS ROW)",
        ]:
            field_names.insert(0, field_name)

        if len(self.config["export_csv_field_list"]) > 0:
            field_names = self.config["export_csv_field_list"]

        deduped_field_names = self.deduplicate_list(field_names)

        # We always include 'node_id and 'REMOVE THIS COLUMN (KEEP THIS ROW)'.
        if "node_id" not in deduped_field_names:
            deduped_field_names.insert(0, "node_id")
            deduped_field_names.insert(0, "REMOVE THIS COLUMN (KEEP THIS ROW)")

        # Handle file columns
        if self.needs_file_column() and "file" not in deduped_field_names:
            deduped_field_names.append("file")

        # Add additional files columns
        additional_files_entries = self.get_additional_files_config()
        if additional_files_entries:
            for column in additional_files_entries.keys():
                if column not in deduped_field_names:
                    deduped_field_names.append(column)

        return deduped_field_names

    def validate_and_get_node_id(self, csv_row):
        """Validate and get node ID from CSV row."""
        node_id = csv_row["node_id"]
        if not value_is_numeric(node_id):
            node_id = get_nid_from_url_alias(self.config, node_id)

        if not ping_node(self.config, node_id):
            self.log_progress(
                f"Node {node_id} not found/accessible, skipping export.",
                level=logging.WARNING
            )
            return None

        return node_id

    def fetch_node_json(self, node_id):
        """Fetch node JSON from Drupal."""
        url = f"{self.config['host']}/node/{node_id}?_format=json"
        response = issue_request(self.config, "GET", url)

        if response.status_code != 200:
            self.log_progress(
                f"Error retrieving node {node_id}: HTTP {response.status_code}",
                level=logging.WARNING
            )
            return None

        return json.loads(response.text)

    def process_node_fields_to_row(self, node_json, field_names):
        """Process node fields into a dictionary for CSV output."""
        row = collections.OrderedDict()
        nid = self.extract_node_id(node_json)

        if not nid:
            return None

        row["node_id"] = nid
        row["title"] = node_json.get("title", [{}])[0].get("value", "No title")

        # Process fields
        for field in field_names:
            if field.startswith("field_") and field in node_json:
                try:
                    row[field] = serialize_field_json(
                        self.config, self.field_definitions, field, node_json[field]
                    )
                except Exception as e:
                    self.log_progress(
                        f"Error serializing {field} for node {nid}: {str(e)}",
                        level=logging.ERROR
                    )
                    row[field] = "SERIALIZATION_ERROR"

        return row

    def process_node_row(self, node_json, field_names):
        """Common processing for node rows."""
        row = self.process_node_fields_to_row(node_json, field_names)
        if not row:
            return None

        media_list = get_media_list(self.config, row["node_id"])
        additional_files_entries = self.get_additional_files_config()

        if self.needs_file_column():
            row["file"] = self.process_file_data(row["node_id"], media_list=media_list)

        if additional_files_entries:
            for col_name, media_use_uri in additional_files_entries.items():
                row[col_name] = self.process_file_data(
                    row["node_id"],
                    media_use_term_id=media_use_uri,
                    media_list=media_list,
                )

        return row

    def export(self):
        """Main export method for CSV export."""
        csv_file_path = self.setup_csv_output_path()
        field_names = self.prepare_headers()

        with open(csv_file_path, "a+", encoding="utf-8") as csv_file:
            writer = self.initialize_csv_writer(csv_file, field_names, True)
            self._process_nodes(writer, field_names)

        return csv_file_path

    def _process_nodes(self, writer, field_names):
        """Process all nodes for CSV export."""
        csv_data_list = list(self.csv_data)
        row_count = 0

        for row in csv_data_list:
            # Delete expired items from request_cache before processing a row.
            if self.config["enable_http_cache"]:
                requests_cache.delete(expired=True)

            node_id = self.validate_and_get_node_id(row)
            if not node_id:
                continue

            node_json = self.fetch_node_json(node_id)
            if not node_json or not self.validate_content_type(node_json, node_id):
                continue

            output_row = self.process_node_row(node_json, field_names)
            if not output_row:
                continue

            writer.writerow(output_row)
            and_files = ""
            if self.needs_file_column:
                if self.config.get("export_file_url_instead_of_download", False):
                    and_files = " and file URL(s)"
                else:
                    and_files = " and file(s)"

            self.log_progress(
                f'Exporting data{and_files} for node {node_id} "{output_row["title"]}."',
                row_count,
                len(csv_data_list),
            )
            row_count += 1


class ViewExporter(WorkbenchExportBase):
    def __init__(self, config, args):
        super().__init__(config, args)
        self.view_config = self.initialize_view_config()

    def setup_csv_output_path(self):
        """Set up CSV output path with timestamp for view exports."""
        if self.config["export_csv_file_path"]:
            return self.config["export_csv_file_path"]

        config_base = os.path.basename(self.args.config).split(".")[0]
        csv_path = os.path.join(
            self.config["input_dir"],
            f"{config_base}_view_export_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
        )

        if os.path.exists(csv_path):
            os.remove(csv_path)
        return csv_path

    def initialize_view_config(self):
        """Initialize configuration for View export."""
        view_parameters = (
            "&".join(self.config["view_parameters"])
            if "view_parameters" in self.config
            else ""
        )
        return {
            "base_url": f"{self.config['host']}/{self.config['view_path'].lstrip('/')}",
            "parameters": view_parameters,
            "initial_url": f"{self.config['host']}/{self.config['view_path'].lstrip('/')}?page=0&{view_parameters}",
        }

    def verify_view_accessibility(self):
        """Verify that the View endpoint is accessible."""
        status_code = ping_view_endpoint(self.config, self.view_config["initial_url"])
        if status_code != 200:
            message = f"Cannot access View at {self.view_config['initial_url']} (HTTP {status_code})."
            self.log_progress(message, level=logging.ERROR)
            sys.exit("Error: " + message + " See log for more information.")

    def prepare_headers(self):
        """Generate deduplicated list of CSV column headers."""
        fields = ["node_id", "title"]

        if self.config.get("export_csv_field_list"):
            fields += [
                f for f in self.config["export_csv_field_list"] if f not in fields
            ]
        else:
            fields += [
                f for f in self.field_definitions.keys() if f.startswith("field_")
            ]

        if self.needs_file_column():
            fields.append("file")

        if "additional_files" in self.config:
            fields += self.get_additional_files_config().keys()

        return self.deduplicate_list(fields)

    def process_node_fields_to_row(self, node_json, field_names):
        """Process node fields into a dictionary for CSV output."""
        row = collections.OrderedDict()
        nid = self.extract_node_id(node_json)

        if not nid:
            return None

        row["node_id"] = nid
        row["title"] = node_json.get("title", [{}])[0].get("value", "No title")

        # Process fields
        for field in field_names:
            if field.startswith("field_") and field in node_json:
                try:
                    row[field] = serialize_field_json(
                        self.config, self.field_definitions, field, node_json[field]
                    )
                except Exception as e:
                    self.log_progress(
                        f"Error serializing {field} for node {nid}: {str(e)}",
                        level=logging.ERROR
                    )
                    row[field] = "SERIALIZATION_ERROR"

        return row

    def process_node_row(self, node_json, field_names):
        """Process node data into CSV row."""
        row = self.process_node_fields_to_row(node_json, field_names)
        if not row:
            return None

        media_list = get_media_list(self.config, row["node_id"])
        additional_files_entries = self.get_additional_files_config()

        if self.needs_file_column():
            row["file"] = self.process_file_data(row["node_id"], media_list=media_list)

        if additional_files_entries:
            for col_name, media_use_uri in additional_files_entries.items():
                row[col_name] = self.process_file_data(
                    row["node_id"],
                    media_use_term_id=media_use_uri,
                    media_list=media_list,
                )

        return row

    def export(self):
        """Main export method for View export."""
        self.verify_view_accessibility()
        csv_file_path = self.setup_csv_output_path()
        field_names = self.prepare_headers()

        with open(csv_file_path, "a+", encoding="utf-8") as csv_file:
            writer = self.initialize_csv_writer(csv_file, field_names)
            self._process_view_pages(writer, field_names)

        return csv_file_path

    def _process_view_pages(self, writer, field_names):
        """Process paginated View results."""
        page = 0

        while True:
            current_url = f"{self.view_config['base_url']}?page={page}&{self.view_config['parameters']}"
            response = issue_request(self.config, "GET", current_url)

            if response.status_code != 200:
                self.log_progress(
                    f"Skipping page {page} due to HTTP {response.status_code}",
                    level=logging.WARNING
                )
                page += 1
                continue

            nodes = self.parse_json_response(response)
            if not nodes:
                break

            for node in nodes:
                if self.config.get("enable_http_cache", False):
                    requests_cache.delete(expired=True)

                nid = self.extract_node_id(node)
                if not nid or nid in self.seen_nids:
                    continue

                self.seen_nids.add(nid)
                if not self.validate_content_type(node, nid):
                    continue

                row = self.process_node_row(node, field_names)
                if row:
                    writer.writerow(row)

                    suffix = self.row_log_suffix(node, nid, row)
                    self.log_progress(f"Exported node{suffix} {nid}: {row['title']}")
                    self.execute_post_export_script(response, json.dumps(node))

            page += 1
