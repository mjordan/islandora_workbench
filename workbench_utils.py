import os
import sys
import logging
import datetime
from ruamel.yaml import YAML
yaml = YAML()


def set_config_defaults(args):
    """Convert the YAML configuration data into an array for easy use.
       Also set some sensible defaults config values.
    """

    # Check existence of configuration file.
    if not os.path.exists(args.config):
        sys.exit('Error: Configuration file ' + args.config + 'not found.')

    config_file_contents = open(args.config).read()
    config_data = yaml.load(config_file_contents)

    config = {}
    for k, v in config_data.items():
        config[k] = v

    # Set up defaults for some settings.
    if 'delimiter' not in config:
        config['delimiter'] = ','
    if 'subdelimiter' not in config:
        config['subdelimiter'] = '|'
    if 'log_file_path' not in config:
        config['log_file_path'] = 'workbench.log'
    if 'log_file_mode' not in config:
        config['log_file_mode'] = 'a'
    if 'allow_missing_files' not in config:
        config['allow_missing_files'] = False

    if args.check:
        config['check'] = True
    else:
        config['check'] = False

    return config


def clean_csv_values(row):
    """Strip whitespace, etc. from row values.
    """
    for field in row:
        row[field] = row[field].strip()
    return row
