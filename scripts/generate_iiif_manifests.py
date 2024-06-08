#!/usr/bin/env python3

"""Iterates over all nodes that are parents and warms the cache of the
   View that generates the node's IIIF Manifest at /node/xxx/book-manifest.
"""

import sys
import os
import logging
import sqlite3
import logging
import tempfile
from ruamel.yaml import YAML
import requests
from requests.exceptions import ConnectTimeout, ReadTimeout, ConnectionError

logging.basicConfig(
    filename="iiif_generation.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

current_config_file_path = sys.argv[1]

yaml = YAML()
config_yaml = open(current_config_file_path, "r")
config = yaml.load(config_yaml)
if "csv_id_to_node_id_map_path" in config:
    csv_id_to_node_id_map_path = config["csv_id_to_node_id_map_path"]
else:
    csv_id_to_node_id_map_path = os.path.join(
        tempfile.gettempdir(), "csv_id_to_node_id_map.db"
    )

if os.path.exists(csv_id_to_node_id_map_path) is False:
    logging.error(
        f"Can't find CSV ID to node ID map database at {csv_id_to_node_id_map_path}"
    )
    sys.exit(1)

query = (
    "select config_file,csv_id,node_id from csv_id_to_node_id_map where node_id in"
    + f" (select parent_node_id from csv_id_to_node_id_map where parent_node_id != '') and config_file = '{current_config_file_path}'"
)

try:
    params = ()
    con = sqlite3.connect(csv_id_to_node_id_map_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    res = cur.execute(query, params).fetchall()
    con.close()
except sqlite3.OperationalError as e:
    logging.error(f"Error executing database query: {e}")
    sys.exit(1)

for row in res:
    try:
        # row[1] is CSV ID, row[2] is node ID
        url = f"{config['host']}/node/{row[2]}/book-manifest"
        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            logging.info(f"Generated IIIF Manifest {url} (CSV ID {row[1]}).")
        else:
            logging.error(
                f"Problem hitting IIIF Manfiest for {url} (CSV ID {row[1]}): HTTP response code was {r.status_code}."
            )
    except Exception as e:
        logging.error(f"Problem accessing {url}: {e}")
