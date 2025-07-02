#!/usr/bin/env python

"""Sample script to illustrate Workbench's "run_scripts" task."""

import sys
import logging
import json
import requests
from ruamel.yaml import YAML

config_file = sys.argv[1]
node_id = sys.argv[2]

yaml = YAML()
with open(config_file, "r") as stream:
    config = yaml.load(stream)

logging.basicConfig(
    filename="script_to_run_sample.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

requests.packages.urllib3.disable_warnings()

# All this script does is print and log a message for each node ID.
message = f"Processing node id {node_id}."
print(message)
logging.info(message)
