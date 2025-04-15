import os
import sys
import json
import logging
import datetime
import collections
import requests_cache
from workbench_utils import *
from progress_bar import InitBar


def deduplicate_list(input_list):
    """Remove duplicates while preserving order."""
    seen = set()
    return [x for x in input_list if not (x in seen or seen.add(x))]


def initialize_csv_writer(
    csv_file, field_names, field_definitions=None, export_mode=False
):
    """Initialize CSV writer with optional metadata rows for export mode."""
    writer = csv.DictWriter(csv_file, fieldnames=field_names, lineterminator="\n")
    writer.writeheader()

    if export_mode and field_definitions:
        # Write field labels row
        field_labels = collections.OrderedDict()
        for field_name in field_names:
            if (
                field_name in field_definitions
                and field_definitions[field_name]["label"] != ""
            ):
                field_labels[field_name] = field_definitions[field_name]["label"]
            elif field_name == "REMOVE THIS COLUMN (KEEP THIS ROW)":
                field_labels[field_name] = "LABEL (REMOVE THIS ROW)"
            else:
                field_labels[field_name] = ""
        writer.writerow(field_labels)

        # Write cardinality row
        cardinality = collections.OrderedDict()
        cardinality["REMOVE THIS COLUMN (KEEP THIS ROW)"] = (
            "NUMBER OF VALUES ALLOWED (REMOVE THIS ROW)"
        )
        cardinality["node_id"] = "1"
        cardinality["uid"] = "1"
        cardinality["langcode"] = "1"
        cardinality["created"] = "1"
        cardinality["title"] = "1"

        for field_name in field_definitions:
            if field_name in field_names:
                cardinality[field_name] = (
                    "unlimited"
                    if field_definitions[field_name]["cardinality"] == -1
                    else str(field_definitions[field_name]["cardinality"])
                )
        writer.writerow(cardinality)

    return writer


def setup_csv_output_path(config, args=None):
    """Set up CSV output path with optional timestamp for view exports."""
    if config["export_csv_file_path"]:
        return config["export_csv_file_path"]

    if args:
        # View export case
        config_base = os.path.basename(args.config).split(".")[0]
        csv_path = os.path.join(
            config["input_dir"],
            f"{config_base}_view_export_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
        )
    else:
        # CSV export case
        csv_path = os.path.join(
            config["input_dir"], config["input_csv"] + ".csv_file_with_field_values"
        )

    if os.path.exists(csv_path):
        os.remove(csv_path)
    return csv_path


def process_file_data(config, node_id, media_use_term_id=None, media_list=None):
    """Handle file processing (download or URL) based on config."""
    if config.get("export_file_url_instead_of_download", False):
        result = get_media_file_url(
            config, node_id, media_use_term_id=media_use_term_id, media_list=media_list
        )
    else:
        result = download_file_from_drupal(
            config, node_id, media_use_term_id=media_use_term_id, media_list=media_list
        )
    return result if result else ""


def process_node_fields_to_row(config, node_json, field_names, field_definitions):
    """Process node fields into a dictionary for CSV output."""
    row = collections.OrderedDict()
    nid = extract_node_id(config, node_json)

    if not nid:
        return None

    row["node_id"] = nid
    row["title"] = node_json.get("title", [{}])[0].get("value", "No title")

    # Process fields
    for field in field_names:
        if field.startswith("field_") and field in node_json:
            try:
                row[field] = serialize_field_json(
                    config, field_definitions, field, node_json[field]
                )
            except Exception as e:
                message = f"Error serializing {field} for node {nid}: {str(e)}"
                print(message)
                logging.error(message)
                row[field] = "SERIALIZATION_ERROR"

    return row


def log_progress(config, message, row_count=None, total_rows=None, pbar=None):
    """Standardized progress logging with optional progress bar."""
    if (
        config.get("progress_bar")
        and pbar
        and row_count is not None
        and total_rows is not None
    ):
        pbar(get_percentage(row_count, total_rows))
    else:
        print(message)
    logging.info(message)


def initialize_view_config(config):
    """Initialize configuration for View export."""
    view_parameters = (
        "&".join(config["view_parameters"]) if "view_parameters" in config else ""
    )
    return {
        "base_url": f"{config['host']}/{config['view_path'].lstrip('/')}",
        "parameters": view_parameters,
        "initial_url": f"{config['host']}/{config['view_path'].lstrip('/')}?page=0&{view_parameters}",
    }


def verify_view_accessibility(config, view_config):
    """Verify that the View endpoint is accessible."""
    status_code = ping_view_endpoint(config, view_config["initial_url"])
    if status_code != 200:
        message = (
            f"Cannot access View at {view_config['initial_url']} (HTTP {status_code})."
        )
        log_progress(config, message)
        sys.exit("Error: " + message + " See log for more information.")


def prepare_csv_headers(config):
    """Generate deduplicated list of CSV column headers."""
    field_definitions = get_field_definitions(config, "node")
    fields = ["node_id", "title"]

    if config.get("export_csv_field_list"):
        fields += [f for f in config["export_csv_field_list"] if f not in fields]
    else:
        fields += [f for f in field_definitions.keys() if f.startswith("field_")]

    if needs_file_column(config):
        fields.append("file")

    if "additional_files" in config:
        fields += get_additional_files_config(config)

    return deduplicate_list(fields)


def needs_file_column(config):
    """Check if we need file column in CSV."""
    return config.get("export_file_url_instead_of_download", False) or config.get(
        "export_file_directory"
    )


def parse_json_response(response):
    """Safely parse JSON from response."""
    try:
        return json.loads(response.text)
    except json.decoder.JSONDecodeError as e:
        message = f"Failed to decode JSON: {str(e)}"
        logging.warn(message)
        print(message)
        return []


def extract_node_id(config, node):
    """Extract and validate node ID."""
    try:
        return node["nid"][0]["value"]
    except (KeyError, IndexError):
        message = "Skipping node with missing/invalid NID"
        log_progress(config, message)
        return None


def validate_content_type(config, node, nid):
    """Verify node matches configured content type."""
    try:
        node_type = node["type"][0]["target_id"]
    except (KeyError, IndexError):
        node_type = "unknown"

    if node_type != config["content_type"]:
        message = f"Skipping node {nid} - type '{node_type}' doesn't match '{config['content_type']}'"
        log_progress(config, message)
        return False
    return True


def process_view_pages(config, view_config, writer, field_names):
    """Process paginated View results."""
    page = 0
    seen_nids = set()
    field_definitions = get_field_definitions(config, "node")

    while True:
        current_url = (
            f"{view_config['base_url']}?page={page}&{view_config['parameters']}"
        )
        response = issue_request(config, "GET", current_url)

        if response.status_code != 200:
            log_progress(
                config, f"Skipping page {page} due to HTTP {response.status_code}"
            )
            page += 1
            continue

        nodes = parse_json_response(response)
        if not nodes:
            break

        for node in nodes:
            if config.get("enable_http_cache", False):
                requests_cache.delete(expired=True)

            nid = extract_node_id(config, node)
            if not nid or nid in seen_nids:
                continue

            seen_nids.add(nid)
            if not validate_content_type(config, node, nid):
                continue

            media_list = get_media_list(config, nid)
            row = process_node_fields_to_row(
                config, node, field_names, field_definitions
            )

            if needs_file_column(config):
                row["file"] = process_file_data(config, nid, media_list=media_list)

            if "additional_files" in config:
                for col_name, media_use_uri in get_additional_files_config(
                    config
                ).items():
                    row[col_name] = process_file_data(
                        config,
                        nid,
                        media_use_term_id=media_use_uri,
                        media_list=media_list,
                    )

            writer.writerow(row)
            log_progress(config, f"Exported node {nid}: {row['title']}")

        page += 1


def prepare_export_csv_headers(config, field_definitions):
    """Generate deduplicated list of CSV column headers for export_csv."""
    field_names = list(field_definitions.keys())

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

    if len(config["export_csv_field_list"]) > 0:
        field_names = config["export_csv_field_list"]

    deduped_field_names = deduplicate_list(field_names)

    # Ensure required fields are present
    if "node_id" not in deduped_field_names:
        deduped_field_names.insert(0, "node_id")
        deduped_field_names.insert(0, "REMOVE THIS COLUMN (KEEP THIS ROW)")

    # Handle file columns
    if needs_file_column(config) and "file" not in deduped_field_names:
        deduped_field_names.append("file")

    # Add additional files columns
    additional_files_entries = get_additional_files_config(config)
    if additional_files_entries:
        for column in additional_files_entries.keys():
            if column not in deduped_field_names:
                deduped_field_names.append(column)

    return deduped_field_names


def validate_and_get_node_id(config, csv_row):
    """Validate and get node ID from CSV row."""
    node_id = csv_row["node_id"]
    if not value_is_numeric(node_id):
        node_id = get_nid_from_url_alias(config, node_id)

    if not ping_node(config, node_id):
        log_progress(config, f"Node {node_id} not found/accessible, skipping export.")
        logging.warning(f"Node {node_id} not found/accessible, skipping export.")
        return None

    return node_id


def fetch_node_json(config, node_id):
    """Fetch node JSON from Drupal."""
    url = f"{config['host']}/node/{node_id}?_format=json"
    response = issue_request(config, "GET", url)

    if response.status_code != 200:
        log_progress(
            config, f"Error retrieving node {node_id}: HTTP {response.status_code}"
        )
        logging.warning(f"Node {node_id} HTTP {response.status_code}")
        return None

    return json.loads(response.text)


def process_export_csv_nodes(config, csv_data, writer, field_names, field_definitions):
    """Process all nodes for CSV export."""
    csv_data_list = list(csv_data)
    row_count = 0
    pbar = InitBar()

    for row in csv_data_list:
        if config["enable_http_cache"]:
            requests_cache.delete(expired=True)

        node_id = validate_and_get_node_id(config, row)
        if not node_id:
            continue

        node_json = fetch_node_json(config, node_id)
        if not node_json or not validate_content_type(config, node_json, node_id):
            continue

        output_row = process_node_fields_to_row(
            config, node_json, field_names, field_definitions
        )
        if not output_row:
            continue

        media_list = get_media_list(config, node_id)
        additional_files_entries = get_additional_files_config(config)

        if needs_file_column(config):
            output_row["file"] = process_file_data(
                config, node_id, media_list=media_list
            )

        if additional_files_entries:
            for col_name, media_use_uri in additional_files_entries.items():
                output_row[col_name] = process_file_data(
                    config,
                    node_id,
                    media_use_term_id=media_use_uri,
                    media_list=media_list,
                )

        writer.writerow(output_row)
        log_progress(
            config,
            f'Exported node {node_id} "{output_row["title"]}"',
            row_count,
            len(csv_data_list),
            pbar,
        )
        row_count += 1
