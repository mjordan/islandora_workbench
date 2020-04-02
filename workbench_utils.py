import os
import sys
import json
import csv
import time
import re
import logging
import datetime
import requests
import subprocess
import mimetypes
from ruamel.yaml import YAML
from functools import lru_cache

yaml = YAML()


def set_media_type(filepath, config):
    """Using configuration options, determine which media type to use.
       Options are either a single media type or a set of mappings from
       file extenstion to media type.
    """
    if 'media_type' in config:
        return config['media_type']

    extension_with_dot = os.path.splitext(filepath)[1]
    extension = extension_with_dot[1:]
    normalized_extension = extension.lower()
    for types in config['media_types']:
        for type, extensions in types.items():
            if normalized_extension in extensions:
                return type

    # If extension isn't in one of the lists, default to 'file'.
    return 'file'


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
    if 'validate_title_length' not in config:
        config['validate_title_length'] = True

    if config['task'] == 'create':
        if 'id_field' not in config:
            config['id_field'] = 'id'
    if config['task'] == 'create':
        if 'published' not in config:
            config['published'] = True

    if config['task'] == 'create':
        if 'preprocessors' in config_data:
            config['preprocessors'] = {}
            for preprocessor in config_data['preprocessors']:
                for key, value in preprocessor.items():
                    config['preprocessors'][key] = value

    if args.check:
        config['check'] = True
    else:
        config['check'] = False

    return config


def issue_request(config, method, path, headers='', json='', data='', query={}):
    """Issue the REST request to Drupal.
    """
    if config['check'] is False:
        if 'pause' in config and method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            time.sleep(config['pause'])

    if config['host'] in path:
        url = path
    else:
        url = config['host'] + path

    if method == 'GET':
        response = requests.get(
            url,
            auth=(config['username'], config['password']),
            params=query,
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


def ping_node(config, nid):
    """Ping the node to see if it exists.
    """
    url = config['host'] + '/node/' + nid + '?_format=json'
    response = issue_request(config, 'HEAD', url)
    if response.status_code == 200:
        return True
    else:
        logging.warning(
            "Node ping (HEAD) on %s returned a %s status code",
            url,
            response.status_code)
        return False


def get_field_definitions(config):
    """Get field definitions from Drupal.
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
        # Hacky implementation of parsing Drupal's JSON:API pager.
        offset = 0
        while 'next' in field_storage_config['links']:
            offset = offset + 50
            field_storage_config_response = issue_request(config, 'GET', field_storage_config_url, headers, '', '', {'page[offset]': offset, 'page[limit]': '50'})
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
            if 'next' not in field_storage_config['links']:
                break

    field_config_url = config['host'] + '/jsonapi/field_config/field_config'
    field_config_response = issue_request(config, 'GET', field_config_url, headers)
    if field_config_response.status_code == 200:
        field_config = json.loads(field_config_response.text)
        for item in field_config['data']:
            field_name = item['attributes']['field_name']
            if field_name in field_definitions:
                required = item['attributes']['required']
                field_definitions[field_name]['required'] = required
                # E.g., comment, media, node.
                entity_type = item['attributes']['entity_type']
                field_definitions[field_name]['entity_type'] = entity_type
                # If the current field is a taxonomy field, get the referenced taxonomies.
                if 'config' in item['attributes']['dependencies']:
                    raw_vocabularies = [x for x in item['attributes']['dependencies']['config'] if re.match("^taxonomy.vocabulary.", x)]
                    if len(raw_vocabularies) > 0:
                        vocabularies = [x.replace("taxonomy.vocabulary.", '') for x in raw_vocabularies]
                        field_definitions[field_name]['vocabularies'] = vocabularies
        # Hacky implementation of parsing Drupal's JSON:API pager.
        offset = 0
        while 'next' in field_config['links']:
            offset = offset + 50
            field_config_response = issue_request(config, 'GET', field_config_url, headers, '', '', {'page[offset]': offset, 'page[limit]': '50'})
            field_config = json.loads(field_config_response.text)
            for item in field_config['data']:
                field_name = item['attributes']['field_name']
                if field_name in field_definitions:
                    required = item['attributes']['required']
                    field_definitions[field_name]['required'] = required
                    # E.g., comment, media, node.
                    entity_type = item['attributes']['entity_type']
                    field_definitions[field_name]['entity_type'] = entity_type
                    # If the current field is a taxonomy field, get the referenced taxonomies.
                    if 'config' in item['attributes']['dependencies']:
                        raw_vocabularies = [x for x in item['attributes']['dependencies']['config'] if re.match("^taxonomy.vocabulary.", x)]
                        if len(raw_vocabularies) > 0:
                            vocabularies = [x.replace("taxonomy.vocabulary.", '') for x in raw_vocabularies]
                            field_definitions[field_name]['vocabularies'] = vocabularies
            if 'next' not in field_config['links']:
                break

    # Base fields include title, promote, status, sticky, etc. Title is required in the CSV file.
    base_field_override_url = config['host'] + '/jsonapi/base_field_override/base_field_override?filter[type][condition][path]=bundle&filter[type][condition][value]=' + config['content_type']
    base_field_override_response = issue_request(config, 'GET', base_field_override_url, headers)
    if base_field_override_response.status_code == 200:
        field_config = json.loads(base_field_override_response.text)
        for item in field_config['data']:
            field_name = item['attributes']['field_name']
            required = item['attributes']['required']
            field_type = item['attributes']['field_type']
            entity_type = item['attributes']['entity_type']
            field_definitions[field_name] = {
                'cardinality': 1,
                'field_type': field_type,
                'required': required,
                'entity_type': entity_type
            }
        # Hacky implementation of parsing Drupal's JSON:API pager.
        offset = 0
        while 'next' in field_config['links']:
            base_field_override_response = issue_request(config, 'GET', base_field_override_url, headers, '', '', {'page[offset]': offset, 'page[limit]': '50'})
            field_config = json.loads(base_field_override_response.text)
            for item in field_config['data']:
                field_name = item['attributes']['field_name']
                required = item['attributes']['required']
                field_type = item['attributes']['field_type']
                entity_type = item['attributes']['entity_type']
                field_definitions[field_name] = {
                    'cardinality': 1,
                    'field_type': field_type,
                    'required': required,
                    'entity_type': entity_type
                }
                if 'next' not in field_config['links']:
                    break

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
    optional_config_keys = ['delimiter', 'subdelimiter', 'log_file_path', 'log_file_mode',
                            'allow_missing_files', 'preprocessors', 'bootstrap', 'published',
                            'validate_title_length', 'media_type', 'media_types', 'pause',
                            'output_csv']

    for optional_config_key in optional_config_keys:
        if optional_config_key in config_keys:
            config_keys.remove(optional_config_key)

    # Check for presence of required config keys.
    if config['task'] == 'create':
        create_options = ['task', 'host', 'username', 'password', 'content_type',
                          'input_dir', 'input_csv', 'media_use_tid',
                          'drupal_filesystem', 'id_field']
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
    csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
    csv_column_headers = csv_data.fieldnames

    # Check whether each row contains the same number of columns as there
    # are headers.
    for count, row in enumerate(csv_data, start=1):
        string_field_count = 0
        for field in row:
            if (row[field] is not None):
                string_field_count += 1
        if len(csv_column_headers) > string_field_count:
            logging.error("Error: Row %s of your CSV file does not " +
                          "have same number of columns (%s) as there are headers " +
                          "(%s).", str(count), str(string_field_count), str(len(csv_column_headers)))
            sys.exit("Error: Row " + str(count) + " of your CSV file " +
                     "does not have same number of columns (" + str(string_field_count) +
                     ") as there are headers (" + str(len(csv_column_headers)) + ").")
        if len(csv_column_headers) < string_field_count:
            logging.error("Error: Row %s of your CSV file has more columns than there are headers " +
                          "(%s).", str(count), str(string_field_count), str(len(csv_column_headers)))
            sys.exit("Error: Row " + str(count) + " of your CSV file " +
                     "has more columns than there are headers (" + str(len(csv_column_headers)) + ").")
    print("OK, all " + str(count) + " rows in the CSV file have the same number of columns as there are headers (" + str(len(csv_column_headers)) + ").")

    # Task-specific CSV checks.
    langcode_was_present = False
    if config['task'] == 'create':
        field_definitions = get_field_definitions(config)
        if config['id_field'] not in csv_column_headers:
            message = 'Error: For "create" tasks, your CSV file must have a column containing a unique identifier.'
            logging.error(message)
            sys.exit(message)
        if 'file' not in csv_column_headers:
            message = 'Error: For "create" tasks, your CSV file must contain a "file" column.'
            logging.error(message)
            sys.exit(message)
        if 'title' not in csv_column_headers:
            message = 'Error: For "create" tasks, your CSV file must contain a "title" column.'
            logging.error(message)
            sys.exit(message)

        if 'output_csv' in config.keys():
            if os.path.exists(config['output_csv']):
                print('Output CSV already exists at ' + config['output_csv'] + ', records will be appended to it.')

        # Specific to creating paged content. Current, if 'parent_id'
        # is present in the CSV file, so must 'field_weight' and 'field_member_of'.
        if 'parent_id' in csv_column_headers:
            if ('field_weight' not in csv_column_headers or 'field_member_of' not in csv_column_headers):
                message = 'Error: If your CSV file contains a "parent_id" column, it must also contain "field_weight" and "field_member_of" columns.'
                logging.error(message)
                sys.exit(message)
        drupal_fieldnames = []
        for drupal_fieldname in field_definitions:
            drupal_fieldnames.append(drupal_fieldname)
        # We .remove() CSV column headers for this check because they are not Drupal field names
        # (including 'langcode'). Any new columns introduced into the CSV need to be removed here.
        if config['id_field'] in csv_column_headers:
            csv_column_headers.remove(config['id_field'])
        if 'file' in csv_column_headers:
            csv_column_headers.remove('file')
        if 'node_id' in csv_column_headers:
            csv_column_headers.remove('node_id')
        if 'parent_id' in csv_column_headers:
            csv_column_headers.remove('parent_id')
        # langcode is a standard Drupal field but it doesn't show up in any field configs.
        if 'langcode' in csv_column_headers:
            csv_column_headers.remove('langcode')
            # Set this so we can validate langcode below.
            langcode_was_present = True
        for csv_column_header in csv_column_headers:
            if csv_column_header not in drupal_fieldnames:
                logging.error("Error: CSV column header %s does not appear to match any Drupal field names.", csv_column_header)
                sys.exit('Error: CSV column header "' + csv_column_header + '" does not appear to match any Drupal field names.')
        print('OK, CSV column headers match Drupal field names.')

    # Check that Drupal fields that are required are in the CSV file (create task only).
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
            logging.error(message)
            sys.exit(message)
        if 'node_id' in csv_column_headers:
            csv_column_headers.remove('node_id')
        for csv_column_header in csv_column_headers:
            if csv_column_header not in drupal_fieldnames:
                logging.error('Error: CSV column header %s does not ' +
                              'appear to match any Drupal field names.', csv_column_header)
                sys.exit('Error: CSV column header "' + csv_column_header +
                         '" does not appear to match any Drupal field names.')
        print('OK, CSV column headers match Drupal field names.')

    if config['task'] == 'update' or config['task'] == 'create':
        # Validate values in fields that are of type 'typed_relation'.
        # Each value (don't forget multivalued fields) needs to have this
        # pattern: string:string:int.
        validate_typed_relation_values(config, field_definitions, csv_data)

        # Requires a View installed by the Islandora Workbench Integration module.
        # If the View is not enabled, Drupal returns a 404.
        terms_view_url = config['host'] + '/vocabulary'
        terms_view_response = issue_request(config, 'GET', terms_view_url)
        if terms_view_response.status_code == 404:
            logging.warning('Not validating taxonomy term IDs used in CSV file. To use this feature, install the Islandora Workbench Integration module.')
        else:
            validate_taxonomy_field_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
            validate_taxonomy_field_values(config, field_definitions, validate_taxonomy_field_csv_data)

        # Validate length of 'title'.
        if config['validate_title_length']:
            validate_title_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
            for count, row in enumerate(validate_title_csv_data, start=1):
                if len(row['title']) > 255:
                    message = "Error: The 'title' column in row " + str(count) + " of your CSV file exceeds Drupal's maximum length of 255 characters."
                    logging.error(message)
                    sys.exit(message)

        # Validate existence of nodes specified in 'field_member_of'.
        validate_field_member_of_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
        for count, row in enumerate(validate_field_member_of_csv_data, start=1):
            if 'field_member_of' in csv_column_headers:
                parent_nids = row['field_member_of'].split(config['subdelimiter'])
                for parent_nid in parent_nids:
                    parent_node_exists = ping_node(config, parent_nid)
                    if parent_node_exists is False:
                        message = "Error: The 'field_member_of field' in row " + str(count) + " of your CSV file contains a node ID that doesn't exist (" + parent_nid + ")"
                        logging.error(message)
                        sys.exit(message)

        # Validate 'langcode' values if that field exists.
        if langcode_was_present:
            validate_langcode_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
            for count, row in enumerate(validate_langcode_csv_data, start=1):
                langcode_valid = validate_language_code(row['langcode'])
                if not langcode_valid:
                    message = "Error: Row " + str(count) + " of your CSV file contains an invalid Drupal language code (" + row['langcode'] + ") in its 'langcode' column."
                    logging.error(message)
                    sys.exit(message)

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

    # Check for existence of files listed in the 'file' column.
    if config['task'] == 'create' or config['task'] == 'add_media':
        file_check_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
        if config['allow_missing_files'] is False:
            for count, file_check_row in enumerate(file_check_csv_data, start=1):
                if len(file_check_row['file']) == 0:
                    sys.exit('Error: Row ' + file_check_row[config['id_field']] + ' contains an empty "file" value.')
                file_path = os.path.join(config['input_dir'], file_check_row['file'])
                if not os.path.exists(file_path) or not os.path.isfile(file_path):
                    sys.exit('Error: File ' + file_path + ' identified in CSV "file" column for record ' +
                             'with ID field value ' + file_check_row[config['id_field']] + ' not found.')
            print('OK, files named in the CSV "file" column are all present.')
        empty_file_values_exist = False
        if config['allow_missing_files'] is True:
            for count, file_check_row in enumerate(file_check_csv_data, start=1):
                if len(file_check_row['file']) == 0:
                    empty_file_values_exist = True
                else:
                    file_path = os.path.join(config['input_dir'], file_check_row['file'])
                    if not os.path.exists(file_path) or not os.path.isfile(file_path):
                        sys.exit('Error: File ' + file_path + ' identified in CSV "file" column not found.')
            if empty_file_values_exist is True:
                ok_message = 'OK, files named in the CSV "file" column are all present; the "allow_missing_files" option is enabled and empty "file" values exist.'
            else:
                ok_message = 'OK, files named in the CSV "file" column are all present.'
            print(ok_message)

        # Check that either 'media_type' or 'media_types' are present in the config file.
        if ('media_type' not in config and 'media_types' not in config):
            sys.exit('Error: You must configure media type using either the "media_type" or "media_types" option.')

    # If nothing has failed by now, exit with a positive message.
    print("Configuration and input data appear to be valid.")
    logging.info("Configuration checked for %s task using config file " +
                 "%s, no problems found.", config['task'], args.config)
    sys.exit(0)


def validate_language_code(langcode):
    # Drupal's language codes.
    codes = ['af', 'am', 'ar', 'ast', 'az', 'be', 'bg', 'bn', 'bo', 'bs',
             'ca', 'cs', 'cy', 'da', 'de', 'dz', 'el', 'en', 'en-x-simple', 'eo',
             'es', 'et', 'eu', 'fa', 'fi', 'fil', 'fo', 'fr', 'fy', 'ga', 'gd', 'gl',
             'gsw-berne', 'gu', 'he', 'hi', 'hr', 'ht', 'hu', 'hy', 'id', 'is', 'it',
             'ja', 'jv', 'ka', 'kk', 'km', 'kn', 'ko', 'ku', 'ky', 'lo', 'lt', 'lv',
             'mg', 'mk', 'ml', 'mn', 'mr', 'ms', 'my', 'ne', 'nl', 'nb', 'nn', 'oc',
             'pa', 'pl', 'pt-pt', 'pt-br', 'ro', 'ru', 'sco', 'se', 'si', 'sk', 'sl',
             'sq', 'sr', 'sv', 'sw', 'ta', 'ta-lk', 'te', 'th', 'tr', 'tyv', 'ug',
             'uk', 'ur', 'vi', 'xx-lolspeak', 'zh-hans', 'zh-hant']
    if langcode in codes:
        return True
    else:
        return False


def clean_csv_values(row):
    """Strip whitespace, etc. from row values.
    """
    for field in row:
        if isinstance(row[field], str):
            row[field] = row[field].strip()
    return row


def get_node_field_values(config, nid):
    """Get a node's field data so we can use it during PATCH updates,
       which replace a field's values.
    """
    node_url = config['host'] + '/node/' + nid + '?_format=json'
    response = issue_request(config, 'GET', node_url)
    node_fields = json.loads(response.text)
    return node_fields


def get_target_ids(node_field_values):
    """Get the target IDs of all entities in a field.
    """
    target_ids = []
    for target in node_field_values:
        target_ids.append(target['target_id'])
    return target_ids


def split_typed_relation_string(config, typed_relation_string, target_type):
    """Fields of type 'typed_relation' are represented in the CSV file
       using a structured string, specifically namespace:property:id,
       e.g., 'relators:pht:5'. 'id' is either a term ID or a node ID.
       This function takes one of those strings (optionally with a multivalue
       subdelimiter) and returns a list of dictionaries in the form they
       take in existing node values.
    """
    return_list = []
    temp_list = typed_relation_string.split(config['subdelimiter'])
    for item in temp_list:
        item_list = item.split(':')
        item_dict = {'target_id': int(item_list[2]), 'rel_type': item_list[0] + ':' + item_list[1], 'target_type': target_type}
        return_list.append(item_dict)

    return return_list


def split_geolocation_string(config, geolocation_string):
    """Fields of type 'geolocation' are represented in the CSV file using a
       structured string, specifically lat,lng, e.g. "49.16667, -123.93333".
       This function takes one of those strings (optionally with a multivalue
       subdelimiter) and returns a list of dictionaries with 'lat' and 'lng' keys.
    """
    return_list = []
    temp_list = geolocation_string.split(config['subdelimiter'])
    for item in temp_list:
        item_list = item.split(',')
        item_dict = {'lat': item_list[0].strip(), 'lng': item_list[1].strip()}
        return_list.append(item_dict)

    return return_list


def validate_typed_relation_values(config, field_definitions, csv_data):
    """Validate values in fields that are of type 'typed_relation'.
       Each value (don't forget multivalued fields) must have this
       pattern: string:string:int.
    """
    # @todo: Complete this function: validate that the relations are from
    # the list configured in the field config, and validate that the target
    # ID exists in the linked taxonomy. See issue #41.
    pass


def preprocess_field_data(subdelimiter, field_value, path_to_script):
    """Executes a field preprocessor script and returns its output and exit status code. The script
       is passed the field subdelimiter as defined in the config YAML and the field's value, and
       prints a modified vesion of the value (result) back to this function.
    """
    cmd = subprocess.Popen([path_to_script, subdelimiter, field_value], stdout=subprocess.PIPE)
    result, stderrdata = cmd.communicate()

    return result, cmd.returncode


def execute_bootstrap_script(path_to_script, path_to_config_file):
    """Executes a bootstrap script and returns its output and exit status code.
       @todo: pass config into script.
    """
    cmd = subprocess.Popen([path_to_script, path_to_config_file], stdout=subprocess.PIPE)
    result, stderrdata = cmd.communicate()

    return result, cmd.returncode


def create_media(config, filename, node_uri):
    """Logging, etc. happens in caller.
    """
    file_path = os.path.join(config['input_dir'], filename)
    mimetype = mimetypes.guess_type(file_path)
    media_type = set_media_type(filename, config)

    media_endpoint_path = ('/media/' +
                           media_type +
                           '/' + str(config['media_use_tid']))
    media_endpoint = node_uri + media_endpoint_path
    location = config['drupal_filesystem'] + os.path.basename(filename)
    media_headers = {
        'Content-Type': mimetype[0],
        'Content-Location': location
    }
    binary_data = open(os.path.join(
        config['input_dir'], filename), 'rb')
    media_response = issue_request(config, 'PUT', media_endpoint, media_headers, '', binary_data)
    binary_data.close()

    return media_response.status_code


# @lru_cache(maxsize=None)
def get_csv_data(input_dir, input_csv, delimiter):
    """Read the input CSV file once and cache its contents.
    """
    input_csv_path = os.path.join(input_dir, input_csv)
    if not os.path.exists(input_csv_path):
        sys.exit('Error: CSV file ' + input_csv_path + 'not found.')
    csv_file_handle = open(input_csv_path, 'r')
    csv_data = csv.DictReader(csv_file_handle, delimiter=delimiter)
    # Yes, we leave the file open because Python.
    # https://github.com/mjordan/islandora_workbench/issues/74.
    return csv_data


def get_term_pairs(config, vocab_id):
    """Get all the term IDs plus associated term names in a vocabulary. If
       the vocabulary does not exist, or is not registered with the view, the
       request to Islandora returns a 200 plus an empty JSON list, i.e., [].
    """
    term_dict = dict()
    # Note: this URL requires a custom view be present on the target Islandora.
    vocab_url = config['host'] + '/vocabulary?_format=json&vid=' + vocab_id
    response = issue_request(config, 'GET', vocab_url)
    vocab = json.loads(response.text)
    for term in vocab:
        name = term['name'][0]['value']
        tid = term['tid'][0]['value']
        term_dict[tid] = name

    return term_dict


def validate_taxonomy_field_values(config, field_definitions, csv_data):
    """Loop through all fields in field_definitions, and if a field
       is a taxonomy reference field, validate all values in the CSV
       data in that field against term IDs in the taxonomies referenced
       by the field.
    """
    # Define a dictionary to store CSV field: term IDs mappings.
    fields_with_vocabularies = dict()
    # Get all the term IDs for vocabularies referenced in all fields in the CSV.
    for column_name in csv_data.fieldnames:
        if column_name in field_definitions:
            if 'vocabularies' in field_definitions[column_name]:
                fields_with_vocabularies[column_name] = []
                # Get the vocabularies linked from the current field (usually
                # only one vocabulary)
                vocabularies = field_definitions[column_name]['vocabularies']
                all_tids_for_field = []
                for vocabulary in vocabularies:
                    terms = get_term_pairs(config, vocabulary)
                    if len(terms) == 0:
                        message = 'Error: Taxonomy "' + vocabulary + '" referenced in CSV field "' + column_name + '" either does not exist or contains no terms.'
                        logging.error(message)
                        sys.exit(message)
                    vocab_term_ids = list(terms.keys())
                    # If more than one vocab in this field, combine their
                    # term IDs into a single list.
                    all_tids_for_field = all_tids_for_field + vocab_term_ids
                fields_with_vocabularies[column_name] = all_tids_for_field

    # Iterate throught the CSV and validate each taxonomy fields's values.
    for count, row in enumerate(csv_data, start=1):
        for column_name in fields_with_vocabularies:
            if len(row[column_name]):
                # Allow for multiple values in one field.
                tids_to_check = row[column_name].split(config['subdelimiter'])
                for tid in tids_to_check:
                    if int(tid) not in fields_with_vocabularies[column_name]:
                        message = 'Error: CSV field "' + column_name + '" in row ' + str(count) + ' contains a term ID (' + tid + ') that is not in the referenced taxonomy.'
                        logging.error(message)
                        sys.exit(message)

    # All term IDs are in their field's vocabularies.
    print("OK, term IDs in CSV file exist in their respective taxonomies.")


def write_to_output_csv(config, id, node_json):
    """Appends a row to the CVS file located at config['output_csv'].
    """
    node_dict = json.loads(node_json)
    node_field_names = list(node_dict.keys())
    node_field_names.insert(0, config['id_field'])
    # Don't need these Drupal fields.
    fields_to_remove = ['vid', 'langcode', 'type', 'revision_timestamp',
                        'revision_uid', 'revision_log', 'uid']
    for field_to_remove in fields_to_remove:
        node_field_names.remove(field_to_remove)
    csvfile = open(config['output_csv'], 'a+')
    writer = csv.DictWriter(csvfile, fieldnames=node_field_names)
    writer.writeheader()
    # Assemble the row to write.
    row = dict()
    row['node_id'] = node_dict
    writer.writerow(row)
    csvfile.close()
