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

# Get each node's title and print/log it.
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
    sys.exit(1)
