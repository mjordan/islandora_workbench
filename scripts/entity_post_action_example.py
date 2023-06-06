#!/usr/bin/env python3

'''Example/template entity post-action script.
   Docs at https://mjordan.github.io/islandora_workbench_docs/hooks/.
'''

import sys
import json
import logging

logging.basicConfig(
    filename='entity_post_create.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%b-%y %H:%M:%S')

workbench_config_file_path = sys.argv[1]
http_response_code = sys.argv[2]
http_response_body = sys.argv[3]
entity = json.loads(http_response_body)

if http_response_code == '201':
    # Execute code if entity was successfully created.
else:
    # Execute code if entity was not successfully created.

