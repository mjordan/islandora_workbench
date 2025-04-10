import os
import sys
import json
import logging
import datetime
import requests_cache
from workbench_utils import *


def print_and_log(message, level="info"):
    print(message)
    getattr(logging, level)(message)


def initialize_csv_writer(csv_file, field_names):
    """Set up CSV writer with headers."""
    import csv  # Ensure csv module is imported

    writer = csv.DictWriter(csv_file, fieldnames=field_names, lineterminator="\n")
    writer.writeheader()
    return writer


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
        print_and_log(message, "error")
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
    print(f"Exported node {nid}: {title} {file_status}".strip())


def prepare_csv_headers(config):
    """Generate deduplicated list of CSV column headers."""
    field_definitions = get_field_definitions(config, "node")
    fields = ["node_id", "title"]  # Core columns

    # Add configured fields
    if config.get("export_csv_field_list"):
        fields += [f for f in config["export_csv_field_list"] if f not in fields]
    else:
        fields += [f for f in field_definitions.keys() if f.startswith("field_")]

    # File handling columns
    if needs_file_column(config):
        fields.append("file")

    # Additional files columns
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
            print_and_log(
                f"Skipping page {page} due to HTTP {response.status_code}", "warning"
            )
            page += 1
            continue

        nodes = parse_json_response(response)
        if not nodes:
            break  # No more results

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
        print_and_log(f"Failed to decode JSON: {str(e)}", "error")
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
        print_and_log("Skipping node with missing/invalid NID", "warning")
        return None


def process_single_node(config, node, nid, writer, field_names, field_definitions):
    """Process an individual node and write its CSV row."""
    if not validate_content_type(config, node, nid):
        return

    media_list = fetch_media_list(config, nid)
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
        msg = f"Skipping node {nid} - type '{node_type}' doesn't match '{config['content_type']}'"
        print_and_log(msg, "warning")
        return False
    return True


def fetch_media_list(config, nid):
    """Retrieve media associated with a node."""
    media_url = f"{config['host']}/node/{nid}/media?_format=json"
    response = issue_request(config, "GET", media_url)

    if response.status_code != 200:
        print_and_log(
            f"Media request failed for node {nid} ({response.status_code})", "error"
        )
        return []

    try:
        return json.loads(response.text)
    except json.decoder.JSONDecodeError as e:
        print_and_log(f"Media parse failed for node {nid}: {e}", "error")
        return []


def build_base_row(node, nid):
    """Create initial CSV row structure."""
    return {
        "node_id": nid,
        "title": node.get("title", [{}])[0].get("value", "No title"),
    }


def add_file_data(config, row, nid, media_list):
    """Add main file data to row if configured."""
    if needs_file_column(config):
        file_result = download_file_from_drupal(config, nid, media_list=media_list)
        row["file"] = file_result if file_result else ""


def add_additional_files(config, row, nid, media_list):
    """Process additional files from configuration."""
    if "additional_files" in config:
        for col_name, media_use_uri in get_additional_files_config(config).items():
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
                print_and_log(
                    f"Error serializing {field} for node {row['node_id']}: {str(e)}",
                    "error",
                )
                row[field] = "SERIALIZATION_ERROR"
