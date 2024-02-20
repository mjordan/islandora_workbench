#!/usr/bin/env python3

import sys
from ruamel.yaml import YAML

config_file_path = sys.argv[1]

yaml = YAML()
with open(config_file_path, "r") as f:
    config_file_contents = f.read()
    config_yaml = yaml.load(config_file_contents)

config = {}
for k, v in config_yaml.items():
    config[k] = v

if config["media_type"] == "document":
    print("Hello")
