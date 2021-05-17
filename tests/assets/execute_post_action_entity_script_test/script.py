#!/usr/bin/env python3

import os
import sys
import json
import tempfile

temp_dir = tempfile.gettempdir()
output_file_path = os.path.join(temp_dir, 'execute_post_action_entity_script.dat')

http_response_body = sys.argv[3]
entity = json.loads(http_response_body)

with open(output_file_path, "a+") as file_object:
    file_object.write(entity['title'][0]['value'] + "\n")
