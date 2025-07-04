#!/usr/bin/env python

"""Sample script to illustrate Workbench's "run_scripts" task."""

import sys
import logging
import json
import requests
from ruamel.yaml import YAML

# All scripts registered in "run_scripts" are passed the path to the Workbench config file
# and a single entity ID, in that order.
config_file = sys.argv[1]
node_id = sys.argv[2]

# Note that like hook scripts, scripts registered in "run_scripts" only have access
# to configuration values defined in the Workbench config file, not to default values.
# Therefore, if you want to reuse the Workbench config file in your scripts, the config
# file should include settings that would otherwise have the default values.
yaml = YAML()
with open(config_file, "r") as stream:
    config = yaml.load(stream)

# Scripts should do their own logging, although if the Workbench config setting is
# "run_scripts_log_script_output" is set to true (its default value), the output
# of your scripts will be logged in the Workbench log file. Set "run_scripts_log_script_output"
# to false to omit scripts' output from the Workbench log.
logging.basicConfig(
    filename="script_to_run_sample.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

requests.packages.urllib3.disable_warnings()

# The demonstration purpose of this script is to fetch each node's title and print/log it,
# using the "host" setting defined in the Workbench config file.
url = f'{config["host"].rstrip("/")}/node/{node_id}?_format=json'
result = requests.get(url, verify=False)
try:
    node = json.loads(result.text)
    title = node["title"][0]["value"]
    logging.info(f'Title is "{title}".')
    print(f'Title is "{title}".')
except Exception as e:
    logging.error(
        f"Could not retrieve data from {url}, HTTP response code was {result.status_code} {e}."
    )
    # Scripts should always exit with a non-0 code on failure so Workbench can detect the failure.
    sys.exit(1)
