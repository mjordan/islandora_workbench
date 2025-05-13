#!/usr/bin/env python3

"""Script for exporting Islandora 7 content (metadata and OBJ datastreams). See
https://mjordan.github.io/islandora_workbench_docs/exporting_islandora_7_content/
for more info.
"""

import os
import sys
from typing import Generator

import requests
import argparse
import json
import re
from progress_bar import InitBar
from i7ImportUtilities import i7ImportUtilities, get_metadata_solr_request
import csv


class SkipException(Exception):
    """Simple exception to skip a PID."""

    pass


def cleanup_row(row_to_clean: dict) -> dict:
    """Switch single element lists to straight strings.
    Parameters:
    row_to_clean: dict: The row to clean.
    -------
    Returns:
    dict: The cleaned row.
    """
    for k, v in row_to_clean.items():
        if isinstance(v, list) and len(v) == 1:
            row_to_clean[k] = v[0]
    return row_to_clean


def get_rows(query_url) -> list:
    """Get rows from Solr.
    Parameters:
    query_url: str: The Solr query URL.
    -------
    Returns:
    list: A list of rows from Solr as dictionaries.
    """
    try:
        resp = requests.get(url=query_url, allow_redirects=True)
        if not resp.ok:
            print(f"Error: {resp.status_code}")
            sys.exit()
        return resp.json()["response"]["docs"]
    except requests.exceptions.RequestException as e:
        utils.get_logger().error(f"Solr Query failed. {e}")
        raise SystemExit(e)


def process_row(row: dict, row_id: int, failed_list: list) -> dict:
    """Process a single row from Solr.
    Parameters:
    row: dict: The row to process.
    row_id: int: The current row ID.
    failed_list: list: A running list of failed PIDs.
    -------
    Returns:
    dict: The processed row.
    """
    if row["PID"] in config["pids_to_skip"]:
        raise SkipException()
    rels_ext = utils.parse_rels_ext(row["PID"])
    if rels_ext:
        if "isSequenceNumber" in rels_ext.keys():
            row["sequence"] = str(rels_ext["isSequenceNumber"])
    else:
        failed_list.append(row["PID"])
        utils.get_logger().error(f"{row['PID']} was unsuccessful.")
        raise SkipException()
    if config["fetch_files"] or config["get_file_url"]:
        for datastream in config["datastreams"]:
            file = utils.get_i7_asset(row["PID"], datastream)
            if file:
                row["file"] = file
                break

    if config["id_field"] in headers:
        row[config["id_field"]] = config["id_start_number"] + (row_id - 1)
    return cleanup_row(row)


def process_block(
    solr_request_string: str,
    inner_row_count: int,
    failed_list: list,
    inner_step: int = None,
) -> int:
    """Request and process a block of rows from Solr.
    Parameters:
    solr_request_string: str: The base Solr request string.
    inner_row_count: int: The current row count.
    failed_list: list: A running list of failed PIDs.
    inner_step: int: The current step if paginating.
    -------
    Returns:
    int: The updated row count.
    """
    if inner_step:
        solr_request_string = re.sub(
            "start=\d+",
            f"start={inner_step * utils._get_config()['rows']}",
            solr_request_string,
        )
    for row in get_rows(solr_request_string):
        inner_row_count += 1
        pbar(inner_row_count)
        try:
            row = process_row(row, inner_row_count, failed_list)
            writer.writerow(row)
        except SkipException:
            continue
    return inner_row_count


if __name__ == "__main__":
    ############################
    # Configuration variables. #
    ############################

    parser = argparse.ArgumentParser(
        description="Generate CSV from Islandora Legacy (7) resources."
    )
    parser.add_argument("--config", required=True, help="Configuration file to use.")
    parser.add_argument(
        "--metadata_solr_request",
        required=False,
        help="Option to supply solr metadata request.",
    )
    args = parser.parse_args()
    utils = i7ImportUtilities(args.config)
    config = utils.config

    # Set a local SSL certificate if one is provided in the config file.
    if "local_ssl_cert" in config:
        os.environ["REQUESTS_CA_BUNDLE"] = config["local_ssl_cert"]
    #######################
    # Main program logic. #
    #######################

    if args.metadata_solr_request:
        metadata_solr_request = get_metadata_solr_request(args.metadata_solr_request)
    else:
        metadata_solr_request = utils.get_default_metadata_solr_request()
    if config["secure_ssl_only"] is False:
        requests.packages.urllib3.disable_warnings()
    pretty_print = metadata_solr_request.replace("&", "\n&")
    utils.get_logger().debug(f"Solr request: {pretty_print}")
    if config["deep_debug"]:
        utils.print_config()

    if config["fetch_files"] is True:
        if not os.path.exists(config["obj_directory"]):
            os.makedirs(config["obj_directory"])

    """Switch to rows=0 to just get the count"""
    numFound = 0
    metadata_solr_request_count = metadata_solr_request.replace("rows=\d+", "rows=0")
    try:
        metadata_solr_response = requests.get(
            url=metadata_solr_request_count, allow_redirects=True
        )

        if not metadata_solr_response.ok:
            warning = ""
            if len(metadata_solr_request) > 2000:
                warning = (
                    "The default query may be too long for a url request.  See docs"
                )
            message = f"Illegal request: Server returned status of {metadata_solr_response.status_code} \n{warning}"
            print(message)
            utils.get_logger().error(message)
            sys.exit()

        response = json.loads(metadata_solr_response.content.decode())
        numFound = response["response"]["numFound"]
    except requests.exceptions.RequestException as e:
        utils.get_logger().error(f"Solr Query failed. {e}")
        raise SystemExit(e)
    if numFound == 0:
        utils.get_logger().info("No items found.")
        print("No items found. Exiting...")
        sys.exit()

    utils.get_logger().info(f"Found {numFound} items.")

    headers = utils.get_solr_field_list()
    # We add a 'sequence' column to store the Islandora 7.x property "isSequenceNumberOfxxx"/"isSequenceNumber".
    headers.append("sequence")
    # Add a column to store the files
    headers.append("file")
    if config["id_field"] not in headers:
        headers.insert(0, config["id_field"])

    # Counter of all rows processed
    row_count = 1
    total_processed = numFound if config["paginate"] else utils._get_config()["rows"]
    pbar = InitBar(title="Exporting Islandora 7 content", size=total_processed)
    # Step counter for pagination
    step = 0
    with open(config["csv_output_path"], "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        failed_pids = []
        if config["paginate"]:
            print("Exporting all {0} items".format(numFound))
            while row_count <= numFound:
                max_row = row_count + utils._get_config()["rows"] - 1
                if max_row > numFound:
                    max_row = numFound
                utils.get_logger().info(
                    f"Processing rows {row_count} to {max_row} of {numFound}"
                )
                row_count = process_block(
                    metadata_solr_request, row_count, failed_pids, inner_step=step
                )
                step += 1
        else:
            print(
                f"Exporting only results {utils.config['start']} to {utils.config['start'] + utils.config['rows']}"
            )
            row_count = process_block(metadata_solr_request, row_count, failed_pids)
        if failed_pids:
            output = "The following PIDS returned no data:\n"
            for pid in failed_pids:
                output += f"{pid}\n"
            print(output)
            if utils.config["debug"]:
                with open(utils.config["failure_report"], "w") as f:
                    f.write(output)
