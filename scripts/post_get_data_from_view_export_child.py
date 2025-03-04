#!/usr/bin/env python3

"""WIP on #603."""

import sys
import json
import logging

logging.basicConfig(
    filename="issue_603.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

workbench_config_file_path = sys.argv[1]
http_response_code = sys.argv[2]
http_response_body = sys.argv[3]
entity = json.loads(http_response_body)

if http_response_code == "200":
    logging.info(entity)
else:
    logging.error("Response code was %s", http_response_code)
