import os
import sys
import json
import csv
import logging
import datetime
import requests
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


def issue_request(config, method, path, headers='', json='', data=''):
    if config['host'] in path:
        url = path
    else:
        url = config['host'] + path

    if method == 'GET':
        response = requests.get(
            url,
            auth=(config['username'], config['password']),
            headers=headers
        )
    if method == 'HEAD':
        response = requests.head(
            url,
            auth=(config['username'], config['password']),
            headers=headers
        )
    if method == 'POST':
        response = requests.post(
            url,
            auth=(config['username'], config['password']),
            headers=headers,
            json=json,
            data=data
        )
    if method == 'PUT':
        response = requests.put(
            url,
            auth=(config['username'], config['password']),
            headers=headers,
            json=json,
            data=data
        )
    if method == 'PATCH':
        response = requests.patch(
            url,
            auth=(config['username'], config['password']),
            headers=headers,
            json=json,
            data=data
        )
    if method == 'DELETE':
        response = requests.delete(
            url,
            auth=(config['username'], config['password']),
            headers=headers
        )
    return response


def ping_node(nid):
    url = config['host'] + '/node/' + nid + '?_format=json'
    response = issue_request(config, 'GET', url)
    if response.status_code == 200:
        return True
    else:
        logging.warning(
            "Node ping (HEAD) on %s returned a %s status code",
            url,
            response.status_code)
        return False


def get_field_definitions(config):
    """Query Drupal to get field definitions.
    """
    headers = {'Accept': 'Application/vnd.api+json'}
    field_definitions = {}

    # We need to get both the field config and the field storage config.
    field_storage_config_url = config['host'] + '/jsonapi/field_storage_config/field_storage_config'
    field_storage_config_response = issue_request(config, 'GET', field_storage_config_url, headers)
    if field_storage_config_response.status_code == 200:
        field_storage_config = json.loads(field_storage_config_response.text)
        for item in field_storage_config['data']:
            field_name = item['attributes']['field_name']
            if 'target_type' in item['attributes']['settings']:
                target_type = item['attributes']['settings']['target_type']
            else:
                target_type = None
            field_definitions[field_name] = {
                'field_type': item['attributes']['field_storage_config_type'],
                'cardinality': item['attributes']['cardinality'],
                'target_type': target_type}

    field_config_url = config['host'] + '/jsonapi/field_config/field_config'
    field_config_response = issue_request(config, 'GET', field_config_url, headers)
    if field_config_response.status_code == 200:
        field_config = json.loads(field_config_response.text)
        for item in field_config['data']:
            field_name = item['attributes']['field_name']
            required = item['attributes']['required']
            field_definitions[field_name]['required'] = required
            # E.g., comment, media, node.
            entity_type = item['attributes']['entity_type']
            field_definitions[field_name]['entity_type'] = entity_type

    return field_definitions


def check_input(config, args):
    """Validate the config file and input data.
    """
    # First, check the config file.
    tasks = ['create', 'update', 'delete', 'add_media']
    joiner = ', '
    if config['task'] not in tasks:
        sys.exit('Error: "task" in your configuration file must be one of "create", "update", "delete", "add_media".')

    config_keys = list(config.keys())
    config_keys.remove('check')

    # Dealing with optional config keys. If you introduce a new
    # optional key, add it to this list. Note that optional
    # keys are not validated.
    optional_config_keys = ['id_field', 'delimiter', 'subdelimiter', 'log_file_path', 'log_file_mode', 'allow_missing_files']

    for optional_config_key in optional_config_keys:
        if optional_config_key in config_keys:
            config_keys.remove(optional_config_key)

    # Check for presence of required config keys.
    if config['task'] == 'create':
        create_options = ['task', 'host', 'username', 'password', 'content_type',
                          'input_dir', 'input_csv', 'media_use_tid',
                          'drupal_filesystem']
        if not set(config_keys) == set(create_options):
            sys.exit('Error: Please check your config file for required ' +
                     'values: ' + joiner.join(create_options))
    if config['task'] == 'update':
        update_options = ['task', 'host', 'username', 'password',
                          'content_type', 'input_dir', 'input_csv']
        if not set(config_keys) == set(update_options):
            sys.exit('Error: Please check your config file for required ' +
                     'values: ' + joiner.join(update_options))
    if config['task'] == 'delete':
        delete_options = ['task', 'host', 'username', 'password',
                          'input_dir', 'input_csv']
        if not set(config_keys) == set(delete_options):
            sys.exit('Error: Please check your config file for required ' +
                     'values: ' + joiner.join(delete_options))
    if config['task'] == 'add_media':
        add_media_options = ['task', 'host', 'username', 'password',
                             'input_dir', 'input_csv', 'media_use_tid',
                             'drupal_filesystem']
        if not set(config_keys) == set(add_media_options):
            sys.exit('Error: Please check your config file for required ' +
                     'values: ' + joiner.join(add_media_options))
    print('OK, configuration file has all required values (did not check ' +
          'for optional values).')

    # Test host and credentials.
    # jsonapi_url = config['host'] + '/jsonapi/field_storage_config/field_storage_config'
    jsonapi_url = '/jsonapi/field_storage_config/field_storage_config'
    headers = {'Accept': 'Application/vnd.api+json'}
    response = issue_request(config, 'GET', jsonapi_url, headers, None, None)
    """
    try:
        response = requests.get(
            jsonapi_url,
            auth=(config['username'], config['password']),
            headers=headers
        )
        response.raise_for_status()
    except requests.exceptions.TooManyRedirects as error:
        print(error)
        sys.exit(1)
    except requests.exceptions.RequestException as error:
        print(error)
        sys.exit(1)
    """

    # JSON:API returns a 200 but an empty 'data' array if credentials are bad.
    if response.status_code == 200:
        field_config = json.loads(response.text)
        if field_config['data'] == []:
            sys.exit('Error: ' + config['host'] + ' does not recognize the ' +
                     'username/password combination you have provided.')
        else:
            print('OK, ' + config['host'] + ' is accessible using the ' +
                  'credentials provided.')

    # Check existence of CSV file.
    input_csv = os.path.join(config['input_dir'], config['input_csv'])
    if os.path.exists(input_csv):
        print('OK, CSV file ' + input_csv + ' found.')
    else:
        sys.exit('Error: CSV file ' + input_csv + 'not found.')

    # Check column headers in CSV file.
    with open(input_csv) as csvfile:
        csv_data = csv.DictReader(csvfile, delimiter=config['delimiter'])
        csv_column_headers = csv_data.fieldnames

        # Check whether each row contains the same number of columns as there
        # are headers.
        for count, row in enumerate(csv_data, start=1):
            if len(csv_column_headers) != len(row):
                sys.exit("Error: Row " + str(count) + " of your CSV file " +
                         "does not have same number of columns (" + str(len(row)) +
                         ") as there are headers (" + str(len(csv_column_headers)) + ").")
                logging.error("Error: Row %s of your CSV file does not " +
                              "have same number of columns (%s) as there are headers " +
                              "(%s).", str(count), str(len(row)), str(len(csv_column_headers)))

        # Task-specific CSV checks.
        if config['task'] == 'create':
            if 'file' not in csv_column_headers:
                message = 'Error: For "create" tasks, your CSV file must contain a "file" column.'
                sys.exit(message)
                logging.error(message)
            if 'title' not in csv_column_headers:
                message = 'Error: For "create" tasks, your CSV file must contain a "title" column.'
                sys.exit(message)
                logging.error(message)
            field_definitions = get_field_definitions(config)
            drupal_fieldnames = []
            for drupal_fieldname in field_definitions:
                drupal_fieldnames.append(drupal_fieldname)
            if 'title' in csv_column_headers:
                csv_column_headers.remove('title')
            if 'file' in csv_column_headers:
                csv_column_headers.remove('file')
            if 'node_id' in csv_column_headers:
                csv_column_headers.remove('node_id')
            for csv_column_header in csv_column_headers:
                if csv_column_header not in drupal_fieldnames:
                    sys.exit('Error: CSV column header "' + csv_column_header + '" does not appear to match any Drupal field names.')
                    logging.error("Error: CSV column header %s does not appear to match any Drupal field names.", csv_column_header)
            print('OK, CSV column headers match Drupal field names.')

        # Check that Drupal fields that are configured as required are in the
        # CSV file (create task only)
        if config['task'] == 'create':
            required_drupal_fields = []
            for drupal_fieldname in field_definitions:
                # In the create task, we only check for required fields that apply to nodes.
                if 'entity_type' in field_definitions[drupal_fieldname] and field_definitions[drupal_fieldname]['entity_type'] == 'node':
                    if 'required' in field_definitions[drupal_fieldname] and field_definitions[drupal_fieldname]['required'] is True:
                        required_drupal_fields.append(drupal_fieldname)
            for required_drupal_field in required_drupal_fields:
                if required_drupal_field not in csv_column_headers:
                    sys.exit('Error: Required Drupal field "' + required_drupal_field + '" is not present in the CSV file.')
                    logging.error("Required Drupal field %s is not present in the CSV file.", required_drupal_field)
            print('OK, required Drupal fields are present in the CSV file.')

        if config['task'] == 'update':
            if 'node_id' not in csv_column_headers:
                sys.exit('Error: For "update" tasks, your CSV file must ' +
                         'contain a "node_id" column.')
            field_definitions = get_field_definitions(config)
            drupal_fieldnames = []
            for drupal_fieldname in field_definitions:
                drupal_fieldnames.append(drupal_fieldname)
            if 'title' in csv_column_headers:
                csv_column_headers.remove('title')
            if 'file' in csv_column_headers:
                message = 'Error: CSV column header "file" is not allowed in update tasks.'
                sys.exit(message)
                logging.error(message)
            if 'node_id' in csv_column_headers:
                csv_column_headers.remove('node_id')
            for csv_column_header in csv_column_headers:
                if csv_column_header not in drupal_fieldnames:
                    sys.exit('Error: CSV column header "' + csv_column_header +
                             '" does not appear to match any Drupal field names.')
                    logging.error('Error: CSV column header %s does not ' +
                                  'appear to match any Drupal field names.', csv_column_header)
            print('OK, CSV column headers match Drupal field names.')

        if config['task'] == 'delete':
            if 'node_id' not in csv_column_headers:
                sys.exit('Error: For "delete" tasks, your CSV file must ' +
                         'contain a "node_id" column.')
        if config['task'] == 'add_media':
            if 'node_id' not in csv_column_headers:
                sys.exit('Error: For "add_media" tasks, your CSV file must ' +
                         'contain a "node_id" column.')
            if 'file' not in csv_column_headers:
                sys.exit('Error: For "add_media" tasks, your CSV file must ' +
                         'contain a "file" column.')

        # Check for existence of files listed in the 'files' column.
        if config['task'] == 'create' or config['task'] == 'add_media':
            # Opening the CSV again is easier than copying the unmodified csv_data variable. Because Python.
            with open(input_csv) as csvfile:
                file_check_csv_data = csv.DictReader(csvfile, delimiter=config['delimiter'])
                for file_check_row in file_check_csv_data:
                    file_path = os.path.join(config['input_dir'], file_check_row['file'])
                    if config['allow_missing_files'] is False:
                        if not os.path.exists(file_path) or not os.path.isfile(file_path):
                            sys.exit('Error: File ' + file_path +
                                     ' identified in CSV "file" column not found.')
                print('OK, files named in the CSV "file" column are ' +
                      'all present.')

    # If nothing has failed by now, exit with a positive message.
    print("Configuration and input data appear to be valid.")
    logging.info("Configuration checked for %s task using config file " +
                 "%s, no problems found", config['task'], args.config)
    sys.exit(0)


def clean_csv_values(row):
    """Strip whitespace, etc. from row values.
    """
    for field in row:
        row[field] = row[field].strip()
    return row
