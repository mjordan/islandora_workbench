#!/usr/bin/env python3

"""Script for exporting Islandora 7 content (metadata and OBJ datastreams). See
   https://mjordan.github.io/islandora_workbench_docs/exporting_islandora_7_content/
   for more info.
"""

import os
import sys

import requests
import logging
import argparse
from progress_bar import InitBar
from i7ImportUtilities import i7ImportUtilities
import csv

############################
# Configuration variables. #
############################

parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True, help="Configuration file to use.")
parser.add_argument(
    "--metadata_solr_request",
    required=False,
    help="Option to supply solr metadata request.",
)
args = parser.parse_args()
utils = i7ImportUtilities(args.config)
config = utils.config

#######################
# Main program logic. #
#######################

logging.basicConfig(
    filename=config["log_file_path"],
    level=logging.INFO,
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

if args.metadata_solr_request:
    metadata_solr_request = utils.get_metadata_solr_request(args.metadata_solr_request)
else:
    metadata_solr_request = utils.get_default_metadata_solr_request()
if config["secure_ssl_only"] is False:
    requests.packages.urllib3.disable_warnings()
if config["debug"]:
    pretty_print = metadata_solr_request.replace("&", "\n&")
    print(f"Solr request: {pretty_print}")
    utils.print_config()

try:
    metadata_solr_response = requests.get(
        url=metadata_solr_request, allow_redirects=True
    )
except requests.exceptions.RequestException as e:
    logging.info("Solr Query failed.")
    raise SystemExit(e)
if not metadata_solr_response.ok:
    warning = ""
    if len(metadata_solr_request) > 2000:
        warning = "The default query may be too long for a url request.  See docs"
    print(
        f"Illegal request: Server returned status of {metadata_solr_response.status_code} \n{warning} "
    )
    sys.exit()
rows = metadata_solr_response.content.decode().splitlines()
logging.info(f"Processing {len(rows)} items.")
reader = csv.DictReader(rows)
headers = reader.fieldnames
# We add a 'sequence' column to store the Islandora 7.x property "isSequenceNumberOfxxx"/"isSequenceNumber".
headers.append("sequence")
# Add a column to store the files
headers.append("file")
if config["id_field"] not in headers:
    headers.append(config["id_field"])
    index = config["id_start_number"]

if config["fetch_files"] is True:
    if not os.path.exists(config["obj_directory"]):
        os.makedirs(config["obj_directory"])

row_count = 0
pbar = InitBar()
num_csv_rows = len(rows)
print(f"Processing {num_csv_rows - 1}.")
with open(config["csv_output_path"], "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=headers)
    writer.writeheader()
    failed_pids = []
    for row in reader:
        if row["PID"] in config["pids_to_skip"]:
            continue
        rels_ext = utils.parse_rels_ext(row["PID"])
        if rels_ext:
            for key, value in rels_ext.items():
                if "isSequenceNumber" in key:
                    row["sequence"] = str(value)
        else:
            failed_pids.append(row["PID"])
            logging.error(f"{row['PID']} was unsuccessful.")
            continue
        if config["fetch_files"] or config["get_file_url"]:
            row_count += 1
            row_position = utils.get_percentage(row_count, num_csv_rows)
            pbar(row_position)
            for datastream in config["datastreams"]:
                file = utils.get_i7_asset(row["PID"], datastream)
                if file:
                    row["file"] = file
                    break

        if config["id_field"] in headers:
            row[config["id_field"]] = index + reader.line_num - 2
        writer.writerow(row)
    if failed_pids:
        output = "The following PIDS returned no data:\n"
        for pid in failed_pids:
            output += f"{pid}\n"
        print(output)
        if config["debug"]:
            with open("failure_report.txt", "w") as f:
                f.write(output)
pbar(100)
