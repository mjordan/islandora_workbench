import os
import sys
import json
import logging
import datetime
import requests_cache
from workbench_utils import *
from progress_bar import InitBar


def initialize_csv_writer(csv_file, field_names):
    """Set up CSV writer with headers."""
    import csv

    writer = csv.DictWriter(csv_file, fieldnames=field_names, lineterminator="\n")
    writer.writeheader()
    return writer


# Functions related to get_data_from_view.


def initialize_view_config(config):
    view_parameters = (
        "&".join(config["view_parameters"]) if "view_parameters" in config else ""
    )
    return {
        "base_url": f"{config['host']}/{config['view_path'].lstrip('/')}",
        "parameters": view_parameters,
        "initial_url": f"{config['host']}/{config['view_path'].lstrip('/')}?page=0&{view_parameters}",
    }


def verify_view_accessibility(config, view_config):
    status_code = ping_view_endpoint(config, view_config["initial_url"])
    if status_code != 200:
        message = (
            f"Cannot access View at {view_config['initial_url']} (HTTP {status_code})."
        )
        print(message)
        logging.error(message)
        sys.exit("Error: " + message + " See log for more information.")


def setup_csv_output_path(config, args):
    if config["export_csv_file_path"]:
        return config["export_csv_file_path"]

    config_base = os.path.basename(args.config).split(".")[0]
    csv_path = os.path.join(
        config["input_dir"],
        f"{config_base}_view_export_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv",
    )

    if os.path.exists(csv_path):
        os.remove(csv_path)
    return csv_path


def print_export_progress(config, nid, title):
    file_status = (
        "with file URL " if config.get("export_file_url_instead_of_download") else ""
    )
    message = f"Exported node {nid}: {title} {file_status}".strip()
    print(message)
    logging.info(message)


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
            message = f"Skipping page {page} due to HTTP {response.status_code}"
            print(message)
            logging.warning(message)
            page += 1
            continue

        nodes = parse_json_response(response)
        if not nodes:
            break

        process_nodes_batch(
            config, nodes, writer, seen_nids, field_names, field_definitions
        )
        page += 1


def deduplicate_list(input_list):
    """Remove duplicates while preserving order."""
    seen = set()
    return [x for x in input_list if not (x in seen or seen.add(x))]


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
        print(message)
        logging.error(message)
        return []


def process_nodes_batch(
    config, nodes, writer, seen_nids, field_names, field_definitions
):
    """Process a batch of nodes from one View page."""
    for node in nodes:
        if config.get("enable_http_cache", False):
            requests_cache.delete(expired=True)

        nid = extract_node_id(node)
        if not nid or nid in seen_nids:
            continue

        seen_nids.add(nid)
        process_single_node(config, node, nid, writer, field_names, field_definitions)


def extract_node_id(node):
    """Extract and validate node ID."""
    try:
        return node["nid"][0]["value"]
    except (KeyError, IndexError):
        message = "Skipping node with missing/invalid NID"
        print(message)
        logging.warning(message)
        return None


def process_single_node(config, node, nid, writer, field_names, field_definitions):
    """Process an individual node and write its CSV row."""
    if not validate_content_type(config, node, nid):
        return

    media_list = get_media_list(config, nid)
    row = build_base_row(node, nid)

    add_file_data(config, row, nid, media_list)
    add_additional_files(config, row, nid, media_list)
    process_node_fields(config, row, node, field_names, field_definitions)

    writer.writerow(row)
    print_export_progress(config, nid, row["title"])


def validate_content_type(config, node, nid):
    """Verify node matches configured content type."""
    try:
        node_type = node["type"][0]["target_id"]
    except (KeyError, IndexError):
        node_type = "unknown"

    if node_type != config["content_type"]:
        message = f"Skipping node {nid} - type '{node_type}' doesn't match '{config['content_type']}'"
        print(message)
        logging.warning(message)
        return False
    return True


def build_base_row(node, nid):
    """Create initial CSV row structure."""
    return {
        "node_id": nid,
        "title": node.get("title", [{}])[0].get("value", "No title"),
    }


def add_file_data(config, row, nid, media_list):
    """Add main file data to row if configured."""
    if needs_file_column(config):
        if config.get("export_file_url_instead_of_download", False):
            file_result = get_media_file_url(config, nid, media_list=media_list)
        else:
            file_result = download_file_from_drupal(config, nid, media_list=media_list)
        row["file"] = file_result if file_result else ""


def add_additional_files(config, row, nid, media_list):
    """Process additional files from configuration."""
    if "additional_files" in config:
        for col_name, media_use_uri in get_additional_files_config(config).items():
            if config.get("export_file_url_instead_of_download", False):
                file_result = get_media_file_url(
                    config, nid, media_use_term_id=media_use_uri, media_list=media_list
                )
            else:
                file_result = download_file_from_drupal(
                    config, nid, media_use_term_id=media_use_uri, media_list=media_list
                )
            row[col_name] = file_result if file_result else ""


def process_node_fields(config, row, node, field_names, field_definitions):
    """Process all defined fields for the node."""
    for field in field_names:
        if field.startswith("field_") and field in node:
            try:
                row[field] = serialize_field_json(
                    config, field_definitions, field, node[field]
                )
            except Exception as e:
                message = (
                    f"Error serializing {field} for node {row['node_id']}: {str(e)}"
                )
                print(message)
                logging.error(message)
                row[field] = "SERIALIZATION_ERROR"


# Functions related to csv_export task.


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


def setup_export_csv_output_path(config):
    """Set up the output path for the export CSV file."""
    if config["export_csv_file_path"] is not None:
        csv_file_path = config["export_csv_file_path"]
    else:
        csv_file_path = os.path.join(
            config["input_dir"], config["input_csv"] + ".csv_file_with_field_values"
        )
    if os.path.exists(csv_file_path):
        os.remove(csv_file_path)
    return csv_file_path


def initialize_export_csv_writer(csv_file, field_names, field_definitions):
    """Initialize CSV writer with headers and metadata rows."""
    writer = csv.DictWriter(csv_file, fieldnames=field_names, lineterminator="\n")
    writer.writeheader()

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


def process_export_csv_nodes(config, csv_data, writer, field_names, field_definitions):
    """Process all nodes for CSV export."""
    # Convert csv_data (DictReader) to a list so we can get its length
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

        output_row = build_export_csv_row(
            config, node_id, node_json, field_names, field_definitions
        )
        if output_row:
            writer.writerow(output_row)
            log_export_progress(
                config,
                row_count,
                len(csv_data_list),
                node_id,
                node_json["title"][0]["value"],
                pbar,
            )
            row_count += 1


def validate_and_get_node_id(config, csv_row):
    """Validate and get node ID from CSV row."""
    node_id = csv_row["node_id"]
    if not value_is_numeric(node_id):
        node_id = get_nid_from_url_alias(config, node_id)

    if not ping_node(config, node_id):
        if not config["progress_bar"]:
            print(f"Node {node_id} not found/accessible, skipping export.")
        logging.warning(f"Node {node_id} not found/accessible, skipping export.")
        return None

    return node_id


def fetch_node_json(config, node_id):
    """Fetch node JSON from Drupal."""
    url = f"{config['host']}/node/{node_id}?_format=json"
    response = issue_request(config, "GET", url)

    if response.status_code != 200:
        print(f"Error retrieving node {node_id}: HTTP {response.status_code}")
        logging.warning(f"Node {node_id} HTTP {response.status_code}")
        return None

    return json.loads(response.text)


def build_export_csv_row(config, node_id, node_json, field_names, field_definitions):
    """Build a CSV row for the exported node."""
    output_row = collections.OrderedDict()

    # Serialize fields
    for field in field_names:
        if field in node_json and field in field_definitions:
            output_row[field] = serialize_field_json(
                config, field_definitions, field, node_json[field]
            )

    # Process media files
    media_list = get_media_list(config, node_id)
    additional_files_entries = get_additional_files_config(config)

    # Main file
    if needs_file_column(config):
        if config["export_file_url_instead_of_download"]:
            file_val = get_media_file_url(config, node_id, media_list=media_list)
        else:
            file_val = download_file_from_drupal(config, node_id, media_list=media_list)
        output_row["file"] = file_val if file_val else ""

    # Additional files
    if additional_files_entries:
        for col_name, media_use_uri in additional_files_entries.items():
            if config["export_file_url_instead_of_download"]:
                file_val = get_media_file_url(
                    config,
                    node_id,
                    media_use_term_id=media_use_uri,
                    media_list=media_list,
                )
            else:
                file_val = download_file_from_drupal(
                    config,
                    node_id,
                    media_use_term_id=media_use_uri,
                    media_list=media_list,
                )
            output_row[col_name] = file_val if file_val else ""

    output_row["node_id"] = node_id
    return output_row


def log_export_progress(config, row_count, total_rows, node_id, title, pbar):
    """Log export progress for a node."""
    msg = f'Exported node {node_id} "{title}"'
    if config["progress_bar"]:
        pbar(get_percentage(row_count, total_rows))
    else:
        print(msg)
    logging.info(msg)
