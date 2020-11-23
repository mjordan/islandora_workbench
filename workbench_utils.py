import os
import sys
import json
import csv
import time
import string
import re
import copy
import logging
import datetime
import requests
import subprocess
import mimetypes
import urllib.parse
from ruamel.yaml import YAML
from functools import lru_cache

yaml = YAML()


def set_config_defaults(args):
    """Convert the YAML configuration data into an array for easy use.
       Also set some sensible defaults config values.
    """
    # Check existence of configuration file.
    if not os.path.exists(args.config):
        message = 'Error: Configuration file ' + args.config + 'not found.'
        logging.error(message)
        sys.exit(message)

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
    if 'paged_content_from_directories' not in config:
        config['paged_content_from_directories'] = False
    if 'delete_media_with_nodes' not in config:
        config['delete_media_with_nodes'] = True
    if 'allow_adding_terms' not in config:
        config['allow_adding_terms'] = False
    if 'log_json' not in config:
        config['log_json'] = False
    if 'user_agent' not in config:
        config['user_agent'] = 'Islandora Workbench'
    if 'allow_redirects' not in config:
        config['allow_redirects'] = True

    if config['task'] == 'create':
        if 'id_field' not in config:
            config['id_field'] = 'id'
    if config['task'] == 'create' or config['task'] == 'create_from_files':
        if 'published' not in config:
            config['published'] = 1

    if config['task'] == 'create' or config['task'] == 'create_from_files':
        if 'preprocessors' in config_data:
            config['preprocessors'] = {}
            for preprocessor in config_data['preprocessors']:
                for key, value in preprocessor.items():
                    config['preprocessors'][key] = value

    if config['task'] == 'create':
        if 'paged_content_sequence_seprator' not in config:
            config['paged_content_sequence_seprator'] = '-'
        if 'paged_content_page_content_type' not in config:
            config['paged_content_page_content_type'] = config['content_type']

    if args.check:
        config['check'] = True
    else:
        config['check'] = False

    return config


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


def set_model_from_extension(file_name, config):
    """Using configuration options, determine which Islandora Model value
       to assign to nodes created from files. Options are either a single model
       or a set of mappings from file extenstion to Islandora Model term ID.
    """
    if config['task'] != 'create_from_files':
        return None

    if 'model' in config:
        return config['model']

    extension_with_dot = os.path.splitext(file_name)[1]
    extension = extension_with_dot[1:]
    normalized_extension = extension.lower()
    for model_tids in config['models']:
        for tid, extensions in model_tids.items():
            if tid.startswith('http'):
                tid = get_term_id_from_uri(config, tid)
            if normalized_extension in extensions:
                return tid
            # If the file's extension is not listed in the config,
            # We use the term ID that contains an empty extension.
            if '' in extensions:
                return tid


def issue_request(config, method, path, headers=dict(), json='', data='', query={}):
    """Issue the REST request to Drupal.
    """
    if config['check'] is False:
        if 'pause' in config and method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            time.sleep(config['pause'])

    headers.update({'User-Agent':config['user_agent']})

    config['host'] = config['host'].rstrip('/')
    if config['host'] in path:
        url = path
    else:
        url = config['host'] + path

    if method == 'GET':
        response = requests.get(
            url,
            allow_redirects=config['allow_redirects'],
            auth=(config['username'], config['password']),
            params=query,
            headers=headers
        )
    if method == 'HEAD':
        response = requests.head(
            url,
            allow_redirects=config['allow_redirects'],
            auth=(config['username'], config['password']),
            headers=headers
        )
    if method == 'POST':
        if config['log_json'] is True:
            logging.info(json)
        response = requests.post(
            url,
            allow_redirects=config['allow_redirects'],
            auth=(config['username'], config['password']),
            headers=headers,
            json=json,
            data=data
        )
    if method == 'PUT':
        if config['log_json'] is True:
            logging.info(json)
        response = requests.put(
            url,
            allow_redirects=config['allow_redirects'],
            auth=(config['username'], config['password']),
            headers=headers,
            json=json,
            data=data
        )
    if method == 'PATCH':
        if config['log_json'] is True:
            logging.info(json)
        response = requests.patch(
            url,
            allow_redirects=config['allow_redirects'],
            auth=(config['username'], config['password']),
            headers=headers,
            json=json,
            data=data
        )
    if method == 'DELETE':
        response = requests.delete(
            url,
            allow_redirects=config['allow_redirects'],
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


def ping_url_alias(config, url_alias):
    """Ping the URL alias to see if it exists. Return the status code.
    """
    url = config['host'] + url_alias + '?_format=json'
    response = issue_request(config, 'GET', url)
    return response.status_code


def ping_islandora(config):
    # First, test host. Surprisingly, using credentials to ping the base URL results in a 403, so we don't
    # go through issue_request(), which always uses credentials.
    try:
        host_response = requests.head(config['host'], allow_redirects=config['allow_redirects'], headers={'User-Agent': config['user_agent']})
        host_response.raise_for_status()
    except requests.exceptions.RequestException as error:
        message = 'Workbench cannot connect to ' + config['host'] + '. Please check the hostname or network.'
        logging.error(message)
        sys.exit('Error: ' + message)

    print("Retrieving field definitions from Drupal...")
    field_definitions = get_field_definitions(config)
    if len(field_definitions) == 0:
        message = 'Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled.'
        logging.error(message)
        sys.exit('Error: ' + message)


def get_field_definitions(config):
    """Get field definitions from Drupal.
    """
    # For media, entity_type will need to be 'media' and bundle_type will need to be one of
    # 'image', 'document', 'audio', 'video', 'file'
    entity_type = 'node'
    bundle_type = config['content_type']

    field_definitions = {}
    fields = get_entity_fields(config, entity_type, bundle_type)
    for fieldname in fields:
        field_definitions[fieldname] = {}
        raw_field_config = get_entity_field_config(config, fieldname, entity_type, bundle_type)
        field_config = json.loads(raw_field_config)
        field_definitions[fieldname]['entity_type'] = field_config['entity_type']
        field_definitions[fieldname]['required'] = field_config['required']
        raw_vocabularies = [x for x in field_config['dependencies']['config'] if re.match("^taxonomy.vocabulary.", x)]
        if len(raw_vocabularies) > 0:
            vocabularies = [x.replace("taxonomy.vocabulary.", '') for x in raw_vocabularies]
            field_definitions[fieldname]['vocabularies'] = vocabularies
        if entity_type == 'media' and 'file_extensions' in field_config['settings']:
            field_definitions[fieldname]['file_extensions'] = field_config['settings']['file_extensions']
        if entity_type == 'media':
            field_definitions[fieldname]['media_type'] = bundle_type    

        raw_field_storage = get_entity_field_storage(config, fieldname, entity_type)
        field_storage = json.loads(raw_field_storage)
        field_definitions[fieldname]['field_type'] = field_storage['type']        
        field_definitions[fieldname]['cardinality'] = field_storage['cardinality']
        if 'max_length' in field_storage['settings']:
            field_definitions[fieldname]['max_length'] = field_storage['settings']['max_length']
        else:
            field_definitions[fieldname]['max_length'] = None
        if 'target_type' in field_storage['settings']:
            field_definitions[fieldname]['target_type'] = field_storage['settings']['target_type']
        else:
            field_definitions[fieldname]['target_type'] = None  

    return field_definitions


def get_entity_fields(config, entity_type, bundle_type):
    fields_endpoint = config['host'] + '/entity/entity_form_display/' + entity_type + '.' + bundle_type + '.default?_format=json'
    bundle_type_response = issue_request(config, 'GET', fields_endpoint)

    fields = []

    if bundle_type_response.status_code == 200:
        node_config_raw = json.loads(bundle_type_response.text)
        fieldname_prefix = 'field.field.node.' + bundle_type + '.'
        fieldnames = [field_dependency.replace(fieldname_prefix, '') for field_dependency in node_config_raw['dependencies']['config']]
        for fieldname in node_config_raw['dependencies']['config']:
            fieldname_prefix = 'field.field.' + entity_type + '.' + bundle_type + '.'
            if re.match(fieldname_prefix, fieldname):
                fieldname = fieldname.replace(fieldname_prefix, '')
                fields.append(fieldname)
    else:
        message = 'Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled.'
        logging.error(message)
        sys.exit('Error: ' + message)

    return fields


def get_entity_field_config(config, fieldname, entity_type, bundle_type):
    field_config_endpoint = config['host'] + '/entity/field_config/' + entity_type + '.' + bundle_type + '.' + fieldname + '?_format=json'
    field_config_response = issue_request(config, 'GET', field_config_endpoint)
    if field_config_response.status_code == 200:
        return field_config_response.text
    else:
        message = 'Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled.'
        logging.error(message)
        sys.exit('Error: ' + message)


def get_entity_field_storage(config, fieldname, entity_type):
    field_storage_endpoint = config['host'] + '/entity/field_storage_config/' + entity_type + '.' + fieldname + '?_format=json'
    field_storage_response = issue_request(config, 'GET', field_storage_endpoint)
    if field_storage_response.status_code == 200:
        return field_storage_response.text
    else:
        message = 'Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled.'
        logging.error(message)
        sys.exit('Error: ' + message)


def check_input(config, args):
    """Validate the config file and input data.
    """
    logging.info('Starting configuration check for "%s" task using config file %s.', config['task'], args.config)

    ping_islandora(config)

    base_fields = ['title', 'status', 'promote', 'sticky', 'uid', 'created']

    # Check the config file.
    tasks = ['create', 'update', 'delete', 'add_media', 'delete_media', 'create_from_files']
    joiner = ', '
    if config['task'] not in tasks:
        message = '"task" in your configuration file must be one of "create", "update", "delete", "add_media", or "create_from_files".'
        logging.error(message)
        sys.exit('Error: ' + message)

    config_keys = list(config.keys())
    config_keys.remove('check')

    # Dealing with optional config keys. If you introduce a new optional key, add it to this list. Note that optional
    # keys are not validated.
    optional_config_keys = ['delimiter', 'subdelimiter', 'log_file_path', 'log_file_mode',
                            'allow_missing_files', 'preprocessors', 'bootstrap', 'published',
                            'validate_title_length', 'media_type', 'media_types', 'pause',
                            'output_csv', 'delete_media_with_nodes', 'paged_content_from_directories',
                            'paged_content_sequence_seprator', 'paged_content_page_model_tid',
                            'paged_content_page_display_hints', 'paged_content_page_content_type',
                            'allow_adding_terms', 'log_json', 'user_agent', 'allow_redirects']

    for optional_config_key in optional_config_keys:
        if optional_config_key in config_keys:
            config_keys.remove(optional_config_key)

    # Check for presence of required config keys.
    if config['task'] == 'create':
        create_options = ['task', 'host', 'username', 'password', 'content_type',
                          'input_dir', 'input_csv', 'media_use_tid',
                          'drupal_filesystem', 'id_field']
        if not set(config_keys) == set(create_options):
            message = 'Please check your config file for required values: ' + joiner.join(create_options) + '.'
            logging.error(message)
            sys.exit('Error: ' + message)
    if config['task'] == 'update':
        update_options = ['task', 'host', 'username', 'password',
                          'content_type', 'input_dir', 'input_csv']
        if not set(config_keys) == set(update_options):
            message = 'Please check your config file for required values: ' + joiner.join(update_options) + '.'
            logging.error(message)
            sys.exit('Error: ' + message)
    if config['task'] == 'delete':
        delete_options = ['task', 'host', 'username', 'password',
                          'input_dir', 'input_csv']
        if not set(config_keys) == set(delete_options):
            message = 'Please check your config file for required values: ' + joiner.join(delete_options) + '.'
            logging.error(message)
            sys.exit('Error: ' + message)
    if config['task'] == 'add_media':
        add_media_options = ['task', 'host', 'username', 'password',
                             'input_dir', 'input_csv', 'media_use_tid',
                             'drupal_filesystem']
        if not set(config_keys) == set(add_media_options):
            message = 'Please check your config file for required values: ' + joiner.join(add_media_options)  + '.'
            logging.error(message)
            sys.exit('Error: ' + message)
    if config['task'] == 'delete_media':
        delete_media_options = ['task', 'host', 'username', 'password',
                                'input_dir', 'input_csv']
        if not set(config_keys) == set(delete_media_options):
            message = 'Please check your config file for required values: ' + joiner.join(delete_media_options) + '.'
            logging.error(message)
            sys.exit('Error: ' + message)
    message = 'OK, configuration file has all required values (did not check for optional values).'
    print(message)
    logging.info(message)

    # Check existence of CSV file.
    input_csv = os.path.join(config['input_dir'], config['input_csv'])
    if os.path.exists(input_csv):
        message = 'OK, CSV file ' + input_csv + ' found.'
        print(message)
        logging.info(message)
    else:
        message = 'CSV file ' + input_csv + ' not found.'
        logging.error(message)
        sys.exit('Error: ' + message)

    # Check column headers in CSV file.
    csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
    csv_column_headers = csv_data.fieldnames

    # Check whether each row contains the same number of columns as there are headers.
    for count, row in enumerate(csv_data, start=1):
        string_field_count = 0
        for field in row:
            if (row[field] is not None):
                string_field_count += 1
        if len(csv_column_headers) > string_field_count:
            logging.error("Row %s of your CSV file does not " +
                          "have same number of columns (%s) as there are headers " +
                          "(%s).", str(count), str(string_field_count), str(len(csv_column_headers)))
            sys.exit("Error: Row " + str(count) + " of your CSV file " +
                     "does not have same number of columns (" + str(string_field_count) +
                     ") as there are headers (" + str(len(csv_column_headers)) + ").")
        if len(csv_column_headers) < string_field_count:
            logging.error("Row %s of your CSV file has more columns than there are headers " +
                          "(%s).", str(count), str(string_field_count), str(len(csv_column_headers)))
            sys.exit("Error: Row " + str(count) + " of your CSV file " +
                     "has more columns than there are headers (" + str(len(csv_column_headers)) + ").")
    message = "OK, all " + str(count) + " rows in the CSV file have the same number of columns as there are headers (" + str(len(csv_column_headers)) + ")."
    print(message)
    logging.info(message)

    # Task-specific CSV checks.
    langcode_was_present = False
    if config['task'] == 'create':
        field_definitions = get_field_definitions(config)
        if config['id_field'] not in csv_column_headers:
            message = 'For "create" tasks, your CSV file must have a column containing a unique identifier.'
            logging.error(message)
            sys.exit('Error: ' + message)
        if 'file' not in csv_column_headers and config['paged_content_from_directories'] is False:
            message = 'For "create" tasks, your CSV file must contain a "file" column.'
            logging.error(message)
            sys.exit('Error: ' + message)
        if 'title' not in csv_column_headers:
            message = 'For "create" tasks, your CSV file must contain a "title" column.'
            logging.error(message)
            sys.exit('Error: ' + message)

        if 'output_csv' in config.keys():
            if os.path.exists(config['output_csv']):
                message = 'Output CSV already exists at ' + config['output_csv'] + ', records will be appended to it.'
                print(message)
                logging.info(message)

        if 'url_alias' in csv_column_headers:
            validate_url_aliases_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
            validate_url_aliases(config, validate_url_aliases_csv_data)

        # Specific to creating paged content. Current, if 'parent_id' is present in the CSV file, so must 'field_weight' and 'field_member_of'.
        if 'parent_id' in csv_column_headers:
            if ('field_weight' not in csv_column_headers or 'field_member_of' not in csv_column_headers):
                message = 'If your CSV file contains a "parent_id" column, it must also contain "field_weight" and "field_member_of" columns.'
                logging.error(message)
                sys.exit('Error: ' + message)
        drupal_fieldnames = []
        for drupal_fieldname in field_definitions:
            drupal_fieldnames.append(drupal_fieldname)

        if len(drupal_fieldnames) == 0:
            message = 'Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled.'
            logging.error(message)
            sys.exit('Error: ' + message)

        # We .remove() CSV column headers for this check because they are not Drupal field names (including 'langcode').
        # Any new columns introduced into the CSV need to be removed here.
        if config['id_field'] in csv_column_headers:
            csv_column_headers.remove(config['id_field'])
        if 'file' in csv_column_headers:
            csv_column_headers.remove('file')
        if 'node_id' in csv_column_headers:
            csv_column_headers.remove('node_id')
        if 'parent_id' in csv_column_headers:
            csv_column_headers.remove('parent_id')
        if 'image_alt_text' in csv_column_headers:
            csv_column_headers.remove('image_alt_text')
        if 'url_alias' in csv_column_headers:
            csv_column_headers.remove('url_alias')            
        # langcode is a standard Drupal field but it doesn't show up in any field configs.
        if 'langcode' in csv_column_headers:
            csv_column_headers.remove('langcode')
            # Set this so we can validate langcode below.
            langcode_was_present = True
        for csv_column_header in csv_column_headers:
            if csv_column_header not in drupal_fieldnames and csv_column_header not in base_fields:
                logging.error("CSV column header %s does not match any Drupal field names.", csv_column_header)
                sys.exit('Error: CSV column header "' + csv_column_header + '" does not match any Drupal field names.')
        message = 'OK, CSV column headers match Drupal field names.'
        print(message)
        logging.info(message)

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
                logging.error("Required Drupal field %s is not present in the CSV file.", required_drupal_field)
                sys.exit('Error: Field "' + required_drupal_field + '" required for content type "' + config['content_type'] + '" is not present in the CSV file.')
        message = 'OK, required Drupal fields are present in the CSV file.'
        print(message)
        logging.info(message)

        # Validate dates in 'created' field, if present.
        if 'created' in csv_column_headers:
            validate_node_created_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
            validate_node_created_date(validate_node_created_csv_data)
        # Validate user IDs in 'uid' field, if present.
        if 'uid' in csv_column_headers:
            validate_node_uid_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
            validate_node_uid(config, validate_node_uid_csv_data)

    if config['task'] == 'update':
        if 'node_id' not in csv_column_headers:
            message = 'For "update" tasks, your CSV file must contain a "node_id" column.'
            logging.error(message)
            sys.exit('Error: ' + message)
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
                logging.error('CSV column header %s does not match any Drupal field names.', csv_column_header)
                sys.exit('Error: CSV column header "' + csv_column_header + '" does not match any Drupal field names.')
        message = 'OK, CSV column headers match Drupal field names.'
        print(message)
        logging.info(message)

    if config['task'] == 'add_media' or config['task'] == 'create':
        validate_media_use_tid(config)

    if config['task'] == 'update' or config['task'] == 'create':
        # Validate values in fields that are of type 'typed_relation'. Each value (don't forget multivalued fields) needs to have
        # this pattern: string:string:int.
        validate_typed_relation_values(config, field_definitions, csv_data)

        validate_csv_field_cardinality_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
        validate_csv_field_cardinality(config, field_definitions, validate_csv_field_cardinality_csv_data)

        validate_csv_field_length_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
        validate_csv_field_length(config, field_definitions, validate_csv_field_length_csv_data)

        # Validating values in CSV taxonomy fields requires a View installed by the Islandora Workbench Integration module.
        # If the View is not enabled, Drupal returns a 404. Use a dummy vocabulary ID or we'll get a 404 even if the View
        # is enabled.
        terms_view_url = config['host'] + '/vocabulary/dummyvid?_format=json'
        terms_view_response = issue_request(config, 'GET', terms_view_url)
        if terms_view_response.status_code == 404:
            logging.warning('Not validating taxonomy term IDs used in CSV file. To use this feature, install the Islandora Workbench Integration module.')
            print('Warning: Not validating taxonomy term IDs used in CSV file. To use this feature, install the Islandora Workbench Integration module.')
        else:
            validate_taxonomy_field_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
            validate_taxonomy_field_values(config, field_definitions, validate_taxonomy_field_csv_data)

        # Validate length of 'title'.
        if config['validate_title_length']:
            validate_title_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
            for count, row in enumerate(validate_title_csv_data, start=1):
                if len(row['title']) > 255:
                    message = "The 'title' column in row " + str(count) + " of your CSV file exceeds Drupal's maximum length of 255 characters."
                    logging.error(message)
                    sys.exit('Error: ' + message)

        # Validate existence of nodes specified in 'field_member_of'. This could be generalized out to validate node IDs in other fields.
        # See https://github.com/mjordan/islandora_workbench/issues/90.
        validate_field_member_of_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
        for count, row in enumerate(validate_field_member_of_csv_data, start=1):
            if 'field_member_of' in csv_column_headers:
                parent_nids = row['field_member_of'].split(config['subdelimiter'])
                for parent_nid in parent_nids:
                    if len(parent_nid) > 0:
                        parent_node_exists = ping_node(config, parent_nid)
                        if parent_node_exists is False:
                            message = "The 'field_member_of' field in row " + str(count) + " of your CSV file contains a node ID (" + parent_nid + ") that doesn't exist."
                            logging.error(message)
                            sys.exit('Error: ' + message)

        # Validate 'langcode' values if that field exists.
        if langcode_was_present:
            validate_langcode_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
            for count, row in enumerate(validate_langcode_csv_data, start=1):
                langcode_valid = validate_language_code(row['langcode'])
                if not langcode_valid:
                    message = "Row " + str(count) + " of your CSV file contains an invalid Drupal language code (" + row['langcode'] + ") in its 'langcode' column."
                    logging.error(message)
                    sys.exit('Error: ' + message)

    if config['task'] == 'delete':
        if 'node_id' not in csv_column_headers:
            message = 'For "delete" tasks, your CSV file must contain a "node_id" column.'
            logging.error(message)
            sys.exit('Error: ' + message)
    if config['task'] == 'add_media':
        if 'node_id' not in csv_column_headers:
            message = 'For "add_media" tasks, your CSV file must contain a "node_id" column.'
            logging.error(message)
            sys.exit('Error: ' + message)
        if 'file' not in csv_column_headers:
            message = 'For "add_media" tasks, your CSV file must contain a "file" column.'
            logging.error(message)
            sys.exit('Error: ' + message)
    if config['task'] == 'delete_media':
        if 'media_id' not in csv_column_headers:
            message = 'For "delete_media" tasks, your CSV file must contain a "media_id" column.'
            logging.error(message)
            sys.exit('Error: ' + message)

    # Check for existence of files listed in the 'file' column.
    if (config['task'] == 'create' or config['task'] == 'add_media') and config['paged_content_from_directories'] is False:
        file_check_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
        if config['allow_missing_files'] is False:
            for count, file_check_row in enumerate(file_check_csv_data, start=1):
                if len(file_check_row['file']) == 0:
                    message = 'Row ' + file_check_row[config['id_field']] + ' contains an empty "file" value.'
                    logging.error(message)
                    sys.exit('Error: ' + message)
                file_path = os.path.join(config['input_dir'], file_check_row['file'])
                if not os.path.exists(file_path) or not os.path.isfile(file_path):
                    message = 'File ' + file_path + ' identified in CSV "file" column for record with ID field value ' + file_check_row[config['id_field']] + ' not found.'
                    logging.error(message)
                    sys.exit('Error: ' + message)
            message = 'OK, files named in the CSV "file" column are all present.'
            print(message)
            logging.info(message)
        empty_file_values_exist = False
        if config['allow_missing_files'] is True:
            for count, file_check_row in enumerate(file_check_csv_data, start=1):
                if len(file_check_row['file']) == 0:
                    empty_file_values_exist = True
                else:
                    file_path = os.path.join(config['input_dir'], file_check_row['file'])
                    if not os.path.exists(file_path) or not os.path.isfile(file_path):
                        message = 'File ' + file_path + ' identified in CSV "file" column not found.'
                        logging.error(message)
                        sys.exit('Error: ' + message)
            if empty_file_values_exist is True:
                message = 'OK, files named in the CSV "file" column are all present; the "allow_missing_files" option is enabled and empty "file" values exist.'
                print(message)
                logging.info(message)
            else:
                message = 'OK, files named in the CSV "file" column are all present.'
                print(message)
                logging.info(message)

         # To do: check that each file's extension is allowed for the current media type usin get_registered_media_extensions().
         # See https://github.com/mjordan/islandora_workbench/issues/126. Maybe also compare allowed extensions with those in
         # 'media_type[s]' config option?

        # Check that either 'media_type' or 'media_types' are present in the config file.
        if ('media_type' not in config and 'media_types' not in config):
            message = 'You must configure media type using either the "media_type" or "media_types" option.'
            logging.error(message)
            sys.exit('Error: ' + message)

    if config['task'] == 'create' and config['paged_content_from_directories'] is True:
        if 'paged_content_page_model_tid' not in config:
            message = 'If you are creating paged content, you must include "paged_content_page_model_tid" in your configuration.'
            logging.error('Configuration requires "paged_content_page_model_tid" setting when creating paged content.')
            sys.exit('Error: ' + message)
        paged_content_from_directories_csv_data = get_csv_data(config['input_dir'], config['input_csv'], config['delimiter'])
        for count, file_check_row in enumerate(paged_content_from_directories_csv_data, start=1):
            dir_path = os.path.join(config['input_dir'], file_check_row[config['id_field']])
            if not os.path.exists(dir_path) or os.path.isfile(dir_path):
                message = 'Page directory ' + dir_path + ' for CSV record with ID "' + file_check_row[config['id_field']] + '"" not found.'
                logging.error(message)
                sys.exit('Error: ' + message)
            page_files = os.listdir(dir_path)
            if len(page_files) == 0:
                print('Warning: Page directory ' + dir_path + ' is empty; is that intentional?')
                logging.warning('Page directory ' + dir_path + ' is empty.')
            for page_file_name in page_files:
                if config['paged_content_sequence_seprator'] not in page_file_name:
                    message = 'Page file ' + os.path.join(dir_path, page_file_name) + ' does not contain a sequence separator (' + config['paged_content_sequence_seprator'] + ').'
                    logging.error(message)
                    sys.exit('Error: ' + message)

        print('OK, page directories are all present.')

    # If nothing has failed by now, exit with a positive message.
    print("Configuration and input data appear to be valid.")
    logging.info('Configuration checked for "%s" task using config file %s, no problems found.', config['task'], args.config)
    sys.exit(0)


def get_registered_media_extensions(field_definitions):
    # Unfinished. See https://github.com/mjordan/islandora_workbench/issues/126.
    for field_name, field_def in field_definitions.items():
        print("Field name: " + field_name + ' / ' + str(field_def))
        """
        print(field_def)
        if field_def['entity_type'] == 'media':
            if 'file_extensions' in field_def:
                print('Allowed file extensions for ' + field_def['media_type'] + ' :' + field_def['file_extensions'])
            else:
                print("No file extensions for " + field_def['media_type'])
        """


def check_input_for_create_from_files(config, args):
    """Validate the config file and input data if task is 'create_from_files'.
    """
    if config['task'] != 'create_from_files':
        message = 'Your task must be "create_from_files".'
        logging.error(message)
        sys.exit('Error: ' + message)        

    logging.info('Starting configuration check for "%s" task using config file %s.', config['task'], args.config)

    ping_islandora(config)

    config_keys = list(config.keys())
    unwanted_in_create_from_files = ['check', 'delimiter', 'subdelimiter', 'allow_missing_files', 'validate_title_length',
        'paged_content_from_directories', 'delete_media_with_nodes', 'allow_adding_terms']
    for option in unwanted_in_create_from_files:
        if option in config_keys:
            config_keys.remove(option)

    # If you introduce a new optional key, add it to this list. Note thatoptional_config_key optional keys are not validated.
    joiner = ', '
    optional_config_keys = ['log_file_path', 'log_file_mode', 'preprocessors', 'bootstrap', 'published', 'pause',
                           'published', 'validate_title_length', 'media_type', 'media_types', 'media_types',
                           'model', 'models', 'output_csv','log_json', 'user_agent', 'allow_redirects']

    for optional_config_key in optional_config_keys:
        if optional_config_key in config_keys:
            config_keys.remove(optional_config_key)

    # Check for presence of required config keys.
    create_options = ['task', 'host', 'username', 'password', 'content_type',
                      'input_dir', 'media_use_tid', 'drupal_filesystem']
    if not set(config_keys) == set(create_options):
        message = 'Please check your config file for required values: ' + joiner.join(create_options) + '.'
        logging.error(message)
        sys.exit('Error: ' + message)

    # Check existence of input directory.
    if os.path.exists(config['input_dir']):
        message = 'OK, input directory "' + config['input_dir'] + '"" found.'
        print(message)
        logging.info(message)
    else:
        message = 'Input directory "' + config['input_dir'] + '"" not found.'
        logging.error(message)
        sys.exit('Error: ' + message)

    # Validate length of 'title'.
    files = os.listdir(config['input_dir'])
    for file_name in files:
        filename_without_extension = os.path.splitext(file_name)[0]
        if len(filename_without_extension) > 255:
            message = 'The filename "' + filename_without_extension + '" exceeds Drupal\'s maximum length of 255 characters and cannot be used for a node title.'
            logging.error(message)
            sys.exit('Error: ' + message)

    # Check that either 'media_type' or 'media_types' are present in the config file.
    if ('media_type' not in config and 'media_types' not in config):
        message = 'You must configure media type using either the "media_type" or "media_types" option in your configuration.'
        logging.error(message)
        sys.exit('Error: ' + message)

    # Check that either 'model' or 'models' are present in the config file.
    if ('model' not in config and 'models' not in config):
        message = 'You must include either the "model" or "models" option in your configuration.'
        logging.error(message)
        sys.exit('Error: ' + message)

    # If nothing has failed by now, exit with a positive message.
    print("Configuration and input data appear to be valid.")
    logging.info('Configuration checked for "%s" task using config file %s, no problems found.', config['task'], args.config)
    sys.exit(0)


def log_field_cardinality_violation(field_name, record_id, cardinality):
    """Writes an entry to the log during create/update tasks if any field values
       are sliced off. Workbench does this if the number of values in a field
       exceeds the field's cardinality.
    """
    logging.warning("Adding all values in CSV field %s for record %s would exceed maximum " +
                    "number of allowed values (%s), so only adding first value.", field_name, record_id, cardinality)


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


def truncate_csv_value(field_name, record_id, field_config, value):
    """Drupal will not accept field values that have a length that
       exceeds the configured maximum length for that field. 'value'
       here is a field subvalue.
    """
    if isinstance(value, str) and 'max_length' in field_config:
        max_length = field_config['max_length']
        if max_length is not None and len(value) > max_length:
            original_value = value
            value = value[:max_length]
            logging.warning('CSV field value "%s" in field "%s" (record ID %s) truncated at %s characters as required by the field\'s configuration.',
                            original_value, field_name, record_id, max_length)
    return value


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


def validate_media_use_tid(config):
    """Validate whether the term ID or URI provided in the config value for media_use_tid is
       in the Islandora Media Use vocabulary.
    """
    if value_is_numeric(config['media_use_tid']) is not True and config['media_use_tid'].startswith('http'):
        media_use_tid = get_term_id_from_uri(config, config['media_use_tid'])
        if media_use_tid is False:
            message = 'URI "' + config['media_use_tid'] + '" provided in configuration option "media_use_tid" does not match any taxonomy terms.'
            logging.error(message)
            sys.exit('Error: ' + message)
    else:
        # Confirm the tid exists and is in the islandora_media_use vocabulary
        term_endpoint = config['host'] + '/taxonomy/term/' + str(config['media_use_tid']) + '?_format=json'
        headers = {'Content-Type': 'application/json'}
        response = issue_request(config, 'GET', term_endpoint, headers)
        if response.status_code == 404:
            message = 'Term ID "' + str(config['media_use_tid']) + '" used in the "media_use_tid" configuration option is not a term ID (term doesn\'t exist).'
            logging.error(message)
            sys.exit('Error: ' + message)
        if response.status_code == 200:         
            response_body = json.loads(response.text)
            if 'vid' in response_body:
                if response_body['vid'][0]['target_id'] != 'islandora_media_use':
                    message = 'Term ID "' + str(config['media_use_tid']) + '" provided in configuration option "media_use_tid" is not in the Islandora Media Use vocabulary.'
                    logging.error(message)
                    sys.exit('Error: ' + message)


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


def create_media(config, filename, node_uri, node_csv_row):
    """node_csv_row is an OrderedDict, e.g.
       OrderedDict([('file', 'IMG_5083.JPG'), ('id', '05'), ('title', 'Alcatraz Island').
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
    binary_data = open(os.path.join(config['input_dir'], filename), 'rb')
    media_response = issue_request(config, 'PUT', media_endpoint, media_headers, '', binary_data)
    if media_response.status_code == 201:
        if 'location' in media_response.headers:
            # A 201 response provides a 'location' header, but a '204' response does not.
            media_uri = media_response.headers['location']
            logging.info("Media (%s) created at %s, linked to node %s.", media_type, media_uri, node_uri)
            media_id = media_uri.rsplit('/', 1)[-1]
            patch_media_fields(config, media_id, media_type, node_csv_row)

            if media_type == 'image':
                patch_image_alt_text(config, media_id, node_csv_row)
    elif media_response.status_code == 204:
        logging.warning("Media created and linked to node %s, but its URI is not available since its creation returned an HTTP status code of %s", node_uri, media_response.status_code)
        logging.warning("Media linked to node %s base fields not updated.", node_uri)
    else:
        logging.error('Media not created, PUT request to "%s" returned an HTTP status code of "%s".', media_endpoint, media_response.status_code)
   
    binary_data.close()

    return media_response.status_code

def patch_media_fields(config, media_id, media_type, node_csv_row):
    """Patch the media entity with base fields from the parent node.
    """
    media_json = {
        'bundle': [
            {'target_id': media_type}
        ]
    }

    for field_name, field_value in node_csv_row.items():
        if field_name == 'created' and len(field_value) > 0:
            media_json['created'] = [{'value': field_value}]
        if field_name == 'uid' and len(field_value) > 0:
            media_json['uid'] = [{'target_id': field_value}]

    # curl -v -H"Content-type: application/json" -X PATCH -d '{"bundle": [{"target_id": "image"}] , "uid": [{"target_id": "1"}], "created": [{"value": "2018-11-18T03:57:40+00:00"}]}' -uadmin:islandora "http://localhost:8000/media/214?_format=json"

    if len(media_json) > 1:
        endpoint = config['host'] + '/media/' + media_id + '?_format=json'
        headers = {'Content-Type': 'application/json'}
        response = issue_request(config, 'PATCH', endpoint, headers, media_json)

        if response.status_code == 200:
            logging.info("Media %s fields updated to match parent node's.", config['host'] + '/media/' + media_id)
        else:
            logging.warning("Media %s fields not updated to match parent node's.", config['host'] + '/media/' + media_id)


def patch_image_alt_text(config, media_id, node_csv_row):
    """Patch the alt text value for an image media. Use the parent node's title
       unless the CSV record contains an image_alt_text field with something in it.
    """
    get_endpoint = config['host'] + '/media/' + media_id + '?_format=json'
    get_headers = {'Content-Type': 'application/json'}
    get_response = issue_request(config, 'GET', get_endpoint, get_headers)
    get_response_body = json.loads(get_response.text)
    field_media_image_target_id = get_response_body['field_media_image'][0]['target_id']

    for field_name, field_value in node_csv_row.items():
        if field_name == 'title':
            # Strip out HTML markup to guard against CSRF in alt text.
            alt_text = re.sub('<[^<]+?>', '', field_value)
        if field_name == 'image_alt_text' and len(field_value) > 0:
            alt_text = re.sub('<[^<]+?>', '', field_value)

    media_json = {
        'bundle': [
            {'target_id': 'image'}
        ],
        'field_media_image': [
            {"target_id": field_media_image_target_id, "alt": alt_text}
        ],
    }

    patch_endpoint = config['host'] + '/media/' + media_id + '?_format=json'
    patch_headers = {'Content-Type': 'application/json'}
    patch_response = issue_request(config, 'PATCH', patch_endpoint, patch_headers, media_json)

    if patch_response.status_code != 200:
        logging.warning("Alt text for image media %s not updated.", config['host'] + '/media/' + media_id)


def remove_media_and_file(config, media_id):
    """Delete a media and the file associated with it.
    """
    # First get the media JSON.
    get_media_url = '/media/' + str(media_id) + '?_format=json'
    get_media_response = issue_request(config, 'GET', get_media_url)
    get_media_response_body = json.loads(get_media_response.text)

    # These are the Drupal field names on the various types of media.
    file_fields = ['field_media_file', 'field_media_image', 'field_media_document', 'field_media_audio_file', 'field_media_video_file']
    for file_field_name in file_fields:
        if file_field_name in get_media_response_body:
            file_id = get_media_response_body[file_field_name][0]['target_id']
            break

    # Delete the file first.
    file_endpoint = config['host'] + '/entity/file/' + str(file_id) + '?_format=json'
    file_response = issue_request(config, 'DELETE', file_endpoint)
    if file_response.status_code == 204:
        logging.info("File %s (from media %s) deleted.", file_id, media_id)
    else:
        logging.error("File %s (from media %s) not deleted (HTTP response code %s).", file_id, media_id, file_response.status_code)

    # Then the media.
    if file_response.status_code == 204:
        media_endpoint = config['host'] + '/media/' + str(media_id) + '?_format=json'
        media_response = issue_request(config, 'DELETE', media_endpoint)
        if media_response.status_code == 204:
            logging.info("Media %s deleted.", media_id)
            return media_response.status_code
        else:
            logging.error("Media %s not deleted (HTTP response code %s).", media_id, media_response.status_code)
            return False

    return False


# @lru_cache(maxsize=None)
def get_csv_data(input_dir, input_csv, delimiter):
    """Read the input CSV file once and cache its contents.
    """
    input_csv_path = os.path.join(input_dir, input_csv)
    if not os.path.exists(input_csv_path):
        messsage = 'Error: CSV file ' + input_csv_path + 'not found.'
        logging.error(message)
        sys.exit(message)
    csv_file_handle = open(input_csv_path, 'r')
    csv_data = csv.DictReader(csv_file_handle, delimiter=delimiter)
    # Yes, we leave the file open because Python.
    # https://github.com/mjordan/islandora_workbench/issues/74.
    return csv_data


def get_term_pairs(config, vocab_id):
    """Get all the term IDs plus associated term names in a vocabulary. If
       the vocabulary does not exist, or is not registered with the view, the
       request to Drupal returns a 200 plus an empty JSON list, i.e., [].
    """
    term_dict = dict()
    # Note: this URL requires the view "Terms in vocabulary", created by the
    # Islandora Workbench Integation module, to present on the target Islandora.
    vocab_url = config['host'] + '/vocabulary/' + vocab_id + '?_format=json'
    response = issue_request(config, 'GET', vocab_url)
    vocab = json.loads(response.text)
    for term in vocab:
        name = term['name'][0]['value']
        tid = term['tid'][0]['value']
        term_dict[tid] = name

    return term_dict


def find_term_in_vocab(config, vocab_id, term_name_to_find):
    """For a given term name, loops through all term names in vocab_id
       to see if term is there already. If so, returns term ID; if not
       returns False.
    """
    terms_in_vocab = get_term_pairs(config, vocab_id)
    for tid, term_name in terms_in_vocab.items():
        match = compare_strings(term_name, term_name_to_find)
        if match:
            return tid

    # None matched.
    return False


def get_term_id_from_uri(config, uri):
    """For a given URI, query the Term from URI View created by the Islandora
       Workbench Integration module. Because we don't know which field each
       taxonomy uses to store URIs (it's either field_external_uri or field_authority_link),
       we need to check both options in the "Term from URI" View.
    """
    # Some vocabuluaries use this View.
    terms_with_uri = []
    term_from_uri_url = config['host'] + '/term_from_uri?_format=json&uri=' + uri.replace('#', '%23')
    term_from_uri_response = issue_request(config, 'GET', term_from_uri_url)
    if term_from_uri_response.status_code == 200:
        term_from_uri_response_body_json = term_from_uri_response.text
        term_from_uri_response_body = json.loads(term_from_uri_response_body_json)
        if len(term_from_uri_response_body) == 1:
            tid = term_from_uri_response_body[0]['tid'][0]['value']
            return tid
        if len(term_from_uri_response_body) > 1:
            for term in term_from_uri_response_body:
                terms_with_uri.append({term['tid'][0]['value']:term['vid'][0]['target_id']})
                tid = term_from_uri_response_body[0]['tid'][0]['value']
            print("Warning: See log for important message about use of term URIs.")
            logging.warning('Term URI "%s" is used for more than one term (with these term ID/vocabulary ID combinations: ' + str(terms_with_uri) + '). Workbench is choosing the first term ID (%s)).', uri, tid)
            return tid

    # And some vocabuluaries use this View.
    term_from_authority_link_url = config['host'] + '/term_from_authority_link?_format=json&authority_link=' + uri.replace('#', '%23')
    term_from_authority_link_response = issue_request(config, 'GET', term_from_authority_link_url)
    if term_from_authority_link_response.status_code == 200:
        term_from_authority_link_response_body_json = term_from_authority_link_response.text
        term_from_authority_link_response_body = json.loads(term_from_authority_link_response_body_json)
        if len(term_from_authority_link_response_body) == 1:
            tid = term_from_authority_link_response_body[0]['tid'][0]['value']
            return tid            
        elif len(term_from_authority_link_response_body) > 1:
            for term in term_from_authority_link_response_body:
                terms_with_uri.append({term['tid'][0]['value']:term['vid'][0]['target_id']})
                tid = term_from_authority_link_response_body[0]['tid'][0]['value']
            print("Warning: See log for important message about use of term URIs.")
            logging.warning('Term URI "%s" is used for more than one term (with these term ID/vocabulary ID combinations: ' + str(terms_with_uri) + '). Workbench is choosing the first term ID (%s)).', uri, tid)
            return tid
        else:
            # URI does not match any term.
            return False

    # Non-200 response code.
    return False


def create_term(config, vocab_id, term_name):
    """Adds a term to the target vocabulary. Returns the new term's ID
       if successful (or the term already exists) or False if not.
    """

    # Check to see if term exists; if so, return its ID, if not, proceed to create it.
    tid = find_term_in_vocab(config, vocab_id, term_name)
    if value_is_numeric(tid):
        logging.info('Term "%s" (term ID %s) already exists in vocabulary "%s".', term_name, tid, vocab_id)
        return tid

    if config['allow_adding_terms'] is False:
        logging.warning('To create new taxonomy terms, you must add "allow_adding_terms: true" to your configuration file.')
        return False

    if len(term_name) > 255:
        truncated_term_name = term_name[:255]
        message = 'Term "' + term_name + '"' + "provided in the CSV data exceeds Drupal's maximum length of 255 characters."
        message_2 = ' It has been trucated to "' + truncated_term_name + '".'
        logging.info(message + message_2)
        term_name = truncated_term_name

    term = {
        "vid": [
           {
               "target_id": vocab_id,
               "target_type": "taxonomy_vocabulary"
           }
           ],
           "status": [
              {
                 "value": True
              }
           ],
           "name": [
              {
                 "value": term_name
              }
           ],
           "description": [
              {
                 "value": "",
                 "format": None
              }
           ],
           "weight": [
              {
                 "value": 0
              }
           ],
           "parent": [
              {
                 "target_id": None
              }
           ],
           "default_langcode": [
              {
                 "value": True
              }
           ],
           "path": [
              {
                 "alias": None,
                 "pid": None,
                 "langcode": "en"
              }
           ]
        }

    term_endpoint = config['host'] + '/taxonomy/term?_format=json'
    headers = {'Content-Type': 'application/json'}
    response = issue_request(config, 'POST', term_endpoint, headers, term, None)
    if response.status_code == 201:
        term_response_body = json.loads(response.text)
        tid = term_response_body['tid'][0]['value']
        logging.info('Term %s ("%s") added to vocabulary "%s".', tid, term_name, vocab_id)
        return tid
    else:
        logging.warning("Term '%s' not created, HTTP response code was %s.", term_name, response.status_code)
        return False


def create_url_alias(config, node_id, url_alias):
    json = {'path': [
            {'value': '/node/' + str(node_id)}
        ],
        'alias':[
            {'value': url_alias}
        ]
    }

    headers = {'Content-Type': 'application/json'}
    response = issue_request(config, 'POST', config['host'] + '/entity/path_alias?_format=json', headers, json, None)
    if response.status_code != 201:
        logging.error("URL alias '%s' not created for node %s, HTTP response code was %s (it might already exist).", url_alias, config['host'] + '/node/' + node_id, response.status_code) 


def prepare_term_id(config, vocab_ids, term):
    """REST POST and PATCH operations require taxonomy term IDs, not term names. This
       funtion checks its 'term' argument to see if it's numeric (i.e., a term ID) and
       if it is, returns it as is. If it's not (i.e., a term name) it looks for the
       term name in the referenced vocabulary and returns its term ID (existing or
       newly created).
    """
    # Special case: if the term starts with 'http', assume it's a Linked Data URI
    # and get its term ID from the URI.
    if term.startswith('http'):
        # Note: get_term_from_uri() will return False if the URI doesn't match a term.
        tid_from_uri = get_term_id_from_uri(config, term)
        if value_is_numeric(tid_from_uri):
            return tid_from_uri

    term = term.strip()
    if value_is_numeric(term):
        return term
    else:
        if len(vocab_ids) == 1:
            tid = create_term(config, vocab_ids[0].strip(), term.strip())
            return tid
        else:
            # Term names used in mult-taxonomy fields. They need to be namespaced with
            # the taxonomy ID.
            #
            # If the field has more than one vocabulary linked to it, we don't know which
            # vocabulary the user wants a new term to be added to, and if the term name is
            # already used in any of the taxonomies linked to this field, we also don't know
            # which vocabulary to look for it in to get its term ID. Therefore, we always need
            # to namespace term names if they are used in multi-taxonomy fields. If people want
            # to use term names that contain a colon, they need to add them to Drupal first
            # and use the term ID. Workaround PRs welcome.
            #
            # Split the namespace/vocab ID from the term name on ':'.
            namespaced = re.search(':', term)
            if namespaced:
                [vocab_id, term_name] = term.split(':')
                tid = create_term(config, vocab_id.strip(), term_name.strip())
                return tid


def get_field_vocabularies(config, field_definitions, field_name):
    """Gets IDs of vocabularies linked from the current field (could be more than one).
    """
    if 'vocabularies' in field_definitions[field_name]:
        vocabularies = field_definitions[field_name]['vocabularies']
        return vocabularies
    else:
        return False


def value_is_numeric(value):
    """Tests to see if value is numeric.
    """
    var = str(value)
    var = var.strip()
    if var.isnumeric():
        return True
    else:
        return False


def compare_strings(known, unknown):
    """Normalizes the unknown string and the known one, and compares
       them. If they match, returns True, if not, False. We could
       use FuzzyWuzzy or something but this is probably sufficient.
    """
    # Strips leading and trailing whitespace.
    known = known.strip()
    unknown = unknown.strip()
    # Converts to lower case.
    known = known.lower()
    unknown = unknown.lower()
    # Remove all punctuation.
    known = known.translate(str.maketrans('', '', string.punctuation))
    unknown = unknown.translate(str.maketrans('', '', string.punctuation))
    # Replaces whitespace with a single space.
    known = " ".join(known.split())
    unknown = " ".join(unknown.split())

    if unknown == known:
        return True
    else:
        return False


def validate_csv_field_cardinality(config, field_definitions, csv_data):
    """Compare values in the CSV data with the fields' cardinality. Log CSV
       fields that have more values than allowed, and warn user if
       these fields exist in their CSV data.
    """
    field_cardinalities = dict()
    csv_headers = csv_data.fieldnames
    csv_headers.remove('title')
    for csv_header in csv_headers:
        if csv_header in field_definitions.keys():
            cardinality = field_definitions[csv_header]['cardinality']
            # We don't care about cardinality of -1 (unlimited)
            if cardinality > 0:
                field_cardinalities[csv_header] = cardinality

    for count, row in enumerate(csv_data, start=1):
        for field_name in field_cardinalities.keys():
            if field_name in row:
                delimited_field_values = row[field_name].split(config['subdelimiter'])
                if config['task'] == 'create':
                    message = 'CSV field "' + field_name + '" in record with ID ' + row[config['id_field']] + ' contains more values than the number '
                if config['task'] == 'update':
                    message = 'CSV field "' + field_name + '" in record with node ID ' + row['node_id'] + ' contains more values than the number '      
                if field_cardinalities[field_name] == 1 and len(delimited_field_values) > 1:
                    message_2 = 'allowed for that field (' + str(field_cardinalities[field_name]) + '). Workbench will add only the first value.'
                    print('Warning: ' + message + message_2)
                    logging.warning(message + message_2)
                if field_cardinalities[field_name] > 1 and len(delimited_field_values) > field_cardinalities[field_name]:
                    message_2 = 'allowed for that field (' + str(field_cardinalities[field_name]) + '). Workbench will add only the first ' + str(field_cardinalities[field_name]) + ' values.'
                    print('Warning: ' + message + message_2)
                    logging.warning(message + message_2)


def validate_csv_field_length(config, field_definitions, csv_data):
    """Compare values in the CSV data with the fields' max_length. Log CSV
       fields that exceed their max_length, and warn user if
       these fields exist in their CSV data.
    """
    field_max_lengths = dict()
    csv_headers = csv_data.fieldnames
    for csv_header in csv_headers:
        if csv_header in field_definitions.keys():
            if 'max_length' in field_definitions[csv_header]:
                max_length = field_definitions[csv_header]['max_length']
                # We don't care about max_length of None (not applicable or unlimited)
                if max_length is not None:
                    field_max_lengths[csv_header] = max_length

    for count, row in enumerate(csv_data, start=1):
        for field_name in field_max_lengths.keys():
            if field_name in row:
                delimited_field_values = row[field_name].split(config['subdelimiter'])
                for field_value in delimited_field_values:
                    field_value_length = len(field_value)
                    if field_name in field_max_lengths and len(field_value) > field_max_lengths[field_name]:
                        if config['task'] == 'create':
                            message = 'CSV field "' + field_name + '" in record with ID ' + row[config['id_field']] + ' contains a value that is longer (' + str(len(field_value)) + ' characters)'
                        if config['task'] == 'update':
                            message = 'CSV field "' + field_name + '" in record with node ID ' + row['node_id'] + ' contains a value that is longer (' + str(len(field_value)) + ' characters)'           
                        message_2 = ' than allowed for that field (' + str(field_max_lengths[field_name]) + ' characters). Workbench will truncate this value prior to populating Drupal.'
                        print('Warning: ' + message + message_2)
                        logging.warning(message + message_2)


def validate_term_name_length(term_name, row_number, column_name):
    """Checks that the length of a term name does not exceed
       Drupal's 255 character length.
    """
    term_name = term_name.strip()
    if len(term_name) > 255:
        message = 'CSV field "' + column_name + '" in record ' + row_number + " contains a taxonomy term that exceeds Drupal's limit of 255 characters (length of term is " + str(len(term_name)) + ' characters).'
        message_2 = ' Term provided in CSV is "' + term_name + '".'
        message_3 = " Please reduce the term's length to less than 256 characters."
        logging.error(message + message_2 + message_3)
        sys.exit('Error: ' + message + ' See the Workbench log for more information.')


def validate_node_created_date(csv_data):
    """Checks that date_string is in the format used by Drupal's 'created' node property,
       e.g., 2020-11-15T23:49:22+00:00. Also check to see if the date is in the future.
    """
    for count, row in enumerate(csv_data, start=1):
        for field_name, field_value in row.items():
            if field_name == 'created' and len(field_value) > 0:
                matches = re.match(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$', field_value)
                if not matches:
                    message = 'CSV field "created" in record ' + str(count) + ' contains a date "' + field_value + '" that is not formatted properly.'
                    logging.error(message)
                    sys.exit('Error: ' + message)

                now = datetime.datetime.now()
                # Remove the GMT differential at the end of the time string.
                date_string_trimmed = re.sub(r'[+-]\d\d:\d\d$', '', field_value)
                created_date = datetime.datetime.strptime(date_string_trimmed, '%Y-%m-%dT%H:%M:%S')
                if created_date > now:
                    message = 'CSV field "created" in record ' + str(count) + ' contains a date "' + field_value + '" that is in the future.'
                    logging.error(message)
                    sys.exit('Error: ' + message)

    message = 'OK, dates in the "created" CSV field are all formated correctly and in the future.'
    print(message)
    logging.info(message)


def validate_url_aliases(config, csv_data):
    """Checks that URL aliases don't already exist.
    """
    for count, row in enumerate(csv_data, start=1):
        for field_name, field_value in row.items():
            if field_name == 'url_alias' and len(field_value) > 0:
                if field_value.strip()[0] != '/':
                    message = 'CSV field "url_alias" in record ' + str(count) + ' contains an alias "' + field_value + '" that is missing its leading /.'
                    logging.error(message)
                    sys.exit('Error: ' + message)                    

                alias_ping = ping_url_alias(config, field_value)
                if alias_ping == 200:
                    message = 'CSV field "url_alias" in record ' + str(count) + ' contains an alias "' + field_value + '" that already exists.'
                    logging.error(message)
                    sys.exit('Error: ' + message)

    message = 'OK, URL aliases do not already exist.'
    print(message)
    logging.info(message)


def validate_node_uid(config, csv_data):
    """Checks that the user identified in the 'uid' field exists in Drupal. Note that this does not validate
       any permissions the user may have.
    """
    for count, row in enumerate(csv_data, start=1):
        for field_name, field_value in row.items():
            if field_name == 'uid' and len(field_value) > 0:
                # Request to /user/x?_format=json goes here; 200 means the user exists, 404 means they do no.
                uid_url = config['host'] + '/user/' + str(field_value) + '?_format=json'
                uid_response = issue_request(config, 'GET', uid_url)
                if uid_response.status_code == 404:
                    message = 'CSV field "uid" in record ' + str(count) + ' contains a user ID "' + field_value + '" that does not exist in the target Drupal.'
                    logging.error(message)
                    sys.exit('Error: ' + message)

    message = 'OK, user IDs in the "uid" CSV field all exist.'
    print(message)
    logging.info(message)


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
                vocabularies = get_field_vocabularies(config, field_definitions, column_name)
                # If there are no vocabularies linked to the current field, 'vocabularies'
                # will be False and will throw a TypeError.
                try:
                    num_vocabs = len(vocabularies)
                except:
                    message = 'Workbench cannot get vocabularies linked to field "' + column_name + '". Please confirm that field has at least one vocabulary.'
                    logging.error(message)
                    sys.exit('Error: ' + message)
                all_tids_for_field = []
                vocab_validation_issues = False
                for vocabulary in vocabularies:
                    terms = get_term_pairs(config, vocabulary)
                    if len(terms) == 0:
                        if config['allow_adding_terms'] is True:
                            vocab_validation_issues = True
                            message = 'Vocabulary "' + vocabulary + '" referenced in CSV field "' + column_name + '" may not be enabled in the "Terms in vocabulary" View (please confirm it is) or may contains no terms.'
                            logging.warning(message)
                        else:
                            vocab_validation_issues = True
                            message = 'Vocabulary "' + vocabulary + '" referenced in CSV field "' + column_name + '" may not enabled in the "Terms in vocabulary" View (please confirm it is) or may contains no terms.'
                            logging.warning(message)
                    vocab_term_ids = list(terms.keys())
                    # If more than one vocab in this field, combine their term IDs into a single list.
                    all_tids_for_field = all_tids_for_field + vocab_term_ids
                fields_with_vocabularies.update({column_name:all_tids_for_field})
                if vocab_validation_issues is True:
                    print('Warning: Issues detected with validating taxonomy terms used in the CSV column "' + column_name + '". See the Workbench log for important details.')

    # If none of the CSV fields are taxonomy reference fields, return.
    if len(fields_with_vocabularies) == 0:
        return

    # Iterate throught the CSV and validate each taxonomy fields's values.
    new_term_names_in_csv = False
    for count, row in enumerate(csv_data, start=1):
        for column_name in fields_with_vocabularies:
            this_fields_vocabularies = get_field_vocabularies(config, field_definitions, column_name)
            this_fields_vocabularies_string = ', '.join(this_fields_vocabularies)
            if len(row[column_name]):
                # Allow for multiple values in one field.
                tids_to_check = row[column_name].split(config['subdelimiter'])
                for field_value in tids_to_check:
                    # If this is a multi-taxonomy field, all term names must be namespaced using the vocab_id:term_name pattern,
                    # regardless of whether config['allow_adding_terms'] is True.
                    if len(this_fields_vocabularies) > 1 and value_is_numeric(field_value) is not True:
                        # URIs are unique so don't need namespacing.
                        if field_value.startswith('http'):
                            continue
                        split_field_values = field_value.split(config['subdelimiter'])
                        for split_field_value in split_field_values:
                            namespaced = re.search(':', field_value)
                            if not namespaced:
                                message = 'Term names in multi-vocabulary CSV field "' + column_name + '" require a vocabulary namespace; value '
                                message_2 = '"' + field_value + '" in row ' + str(count) + ' does not have one.'
                                logging.error(message + message_2)
                                sys.exit('Error: ' + message + message_2)

                                validate_term_name_length(split_field_value, str(count), column_name)

                    # Check to see if field_value is a member of the field's vocabularies. First,
                    # check the field_value if it is a term ID.
                    if value_is_numeric(field_value):
                        field_value = field_value.strip()
                        if int(field_value) not in fields_with_vocabularies[column_name]:
                            message = 'CSV field "' + column_name + '" in row ' + str(count) + ' contains a term ID (' + field_value + ') that is '
                            if len(this_fields_vocabularies) > 1:
                                message_2 = 'not in one of the referenced vocabularies (' + this_fields_vocabularies_string + ').'
                            else:
                                message_2 = 'not in the referenced vocabulary ("' + this_fields_vocabularies[0] + '").'
                            logging.error(message + message_2)
                            sys.exit('Error: ' + message + message_2)
                    # Then check values that are URIs.
                    elif field_value.startswith('http'):
                        tid_from_uri = get_term_id_from_uri(config, field_value)
                        if value_is_numeric(tid_from_uri):
                            if tid_from_uri not in fields_with_vocabularies[column_name]:
                                message = 'CSV field "' + column_name + '" in row ' + str(count) + ' contains a term URI (' + field_value + ') that is '
                                if len(this_fields_vocabularies) > 1:
                                    message_2 = 'not in one of the referenced vocabularies (' + this_fields_vocabularies_string + ').'
                                else:
                                    message_2 = 'not in the referenced vocabulary ("' + this_fields_vocabularies[0] + '").'
                                logging.error(message + message_2)
                                sys.exit('Error: ' + message + message_2)
                        else:               
                            message = 'Term URI "' + term_to_check_uri + '" used in CSV column "' + column_name + '"" row ' + str(count) + ' does not match any terms.'
                            logging.error(message)
                            sys.exit('Error: ' + message)
                    # Finally, check values that string term names.
                    else:
                        tid = find_term_in_vocab(config, vocabulary, field_value)
                        if value_is_numeric(tid) is not True:
                            # Single taxonomy fields.
                            if len(this_fields_vocabularies) == 1:
                                    if config['allow_adding_terms'] is True:
                                        # Warn if namespaced term name is not in specified vocab.
                                        if tid is False:
                                            new_term_names_in_csv = True
                                            validate_term_name_length(field_value, str(count), column_name)
                                            message = 'CSV field "' + column_name + '" in row ' + str(count) + ' contains a term ("' + field_value.strip() + '") that is '
                                            message_2 = 'not in the referenced vocabulary ("' + this_fields_vocabularies[0] + '"). That term will be created.'
                                            logging.warning(message + message_2)
                                    else:
                                        new_term_names_in_csv = True
                                        message = 'CSV field "' + column_name + '" in row ' + str(count) + ' contains a term ("' + field_value.strip() + '") that is '
                                        message_2 = 'not in the referenced vocabulary ("' + this_fields_vocabularies[0] + '").'
                                        logging.error(message + message_2)
                                        sys.exit('Error: ' + message + message_2)

                            # If this is a multi-taxonomy field, all term names must be namespaced using the vocab_id:term_name pattern,
                            # regardless of whether config['allow_adding_terms'] is True.
                            if len(this_fields_vocabularies) > 1:
                                split_field_values = field_value.split(config['subdelimiter'])
                                for split_field_value in split_field_values:
                                    # Check to see if namespaced vocab is referenced by this field.
                                    [namespace_vocab_id, namespaced_term_name] = split_field_value.split(':')
                                    if namespace_vocab_id not in this_fields_vocabularies:
                                        message = 'CSV field "' + column_name + '" in row ' + str(count) + ' contains a namespaced term name '
                                        message_2 = '(' + namespaced_term_name.strip() + '") that specifies a vocabulary not associated with that field.'
                                        logging.error(message + message_2)
                                        sys.exit('Error: ' + message + message_2)

                                    tid = find_term_in_vocab(config, namespace_vocab_id, namespaced_term_name)

                                    if config['allow_adding_terms'] is True:
                                        # Warn if namespaced term name is not in specified vocab.
                                        if tid is False:
                                            new_term_names_in_csv = True
                                            message = 'CSV field "' + column_name + '" in row ' + str(count) + ' contains a term ("' + namespaced_term_name.strip() + '") that is '
                                            message_2 = 'not in the referenced vocabulary ("' + namespace_vocab_id + '"). That term will be created.'
                                            logging.warning(message + message_2)

                                            validate_term_name_length(split_field_value, str(count), column_name)
                                    else:
                                        # Die if namespaced term name is not specified vocab.
                                        if tid is False:
                                            message = 'CSV field "' + column_name + '" in row ' + str(count) + ' contains a term ("' + namespaced_term_name.strip() + '") that is '
                                            message_2 = 'not in the referenced vocabulary ("' + namespace_vocab_id + '").'
                                            logging.warning(message + message_2)
                                            sys.exit('Error: ' + message + message_2)

    if new_term_names_in_csv is True and config['allow_adding_terms'] is True:
        print("OK, term IDs/names in CSV file exist in their respective taxonomies (and new terms will be created as noted in the Workbench log).")
    else:
        # All term IDs are in their field's vocabularies.
        print("OK, term IDs/names in CSV file exist in their respective taxonomies.")
        logging.info("OK, term IDs/names in CSV file exist in their respective taxonomies.")


def write_to_output_csv(config, id, node_json):
    """Appends a row to the CVS file located at config['output_csv'].
    """
    if config['task'] == 'create_from_files':
        config['id_field'] = 'ID'

    node_dict = json.loads(node_json)
    node_field_names = list(node_dict.keys())
    node_field_names.insert(0, 'node_id')
    node_field_names.insert(0, config['id_field'])
    # Don't include these Drupal fields in our output.
    fields_to_remove = ['nid', 'vid', 'created', 'changed', 'langcode', 'default_langcode',
                        'uid', 'type', 'revision_timestamp', 'revision_translation_affected',
                        'revision_uid', 'revision_log', 'content_translation_source',
                        'content_translation_outdated']
    for field_to_remove in fields_to_remove:
        node_field_names.remove(field_to_remove)

    csvfile = open(config['output_csv'], 'a+')
    writer = csv.DictWriter(csvfile, fieldnames=node_field_names, lineterminator="\n")

    # Check for presence of header row, don't add it if it's already there.
    with open(config['output_csv']) as f:
        first_line = f.readline()
    if not first_line.startswith(config['id_field']):
        writer.writeheader()

    # Assemble the CSV record to write.
    row = dict()
    row[config['id_field']] = id
    row['node_id'] = node_dict['nid'][0]['value']
    row['uuid'] = node_dict['uuid'][0]['value']
    row['title'] = node_dict['title'][0]['value']
    row['status'] = node_dict['status'][0]['value']
    writer.writerow(row)
    csvfile.close()


def create_children_from_directory(config, parent_csv_record, parent_node_id, parent_title):
    # These objects will have a title (derived from filename), an ID based on the parent's
    # id, and a config-defined Islandora model. Content type and status are inherited
    # as is from parent. The weight assigned to the page is the last segment in the filename,
    # split from the rest of the filename using the character defined in the
    # 'paged_content_sequence_seprator' config option.
    parent_id = parent_csv_record[config['id_field']]
    page_dir_path = os.path.join(config['input_dir'], parent_id)
    page_files = os.listdir(page_dir_path)
    page_file_return_dict = dict()
    for page_file_name in page_files:
        filename_without_extension = os.path.splitext(page_file_name)[0]
        filename_segments = filename_without_extension.split(config['paged_content_sequence_seprator'])
        weight = filename_segments[-1]
        weight = weight.lstrip("0")
        # @todo: come up with a templated way to generate the page_identifier,
        # and what field to POST it to.
        page_identifier = parent_id + '_' + filename_without_extension
        page_title = parent_title + ', page ' + weight

        # @todo: provide a config option for page content type.
        node_json = {
            'type': [
                {'target_id': config['paged_content_page_content_type'],
                 'target_type': 'node_type'}
            ],
            'title': [
                {'value': page_title}
            ],
            'status': [
                {'value': config['published']}
            ],
            'field_model': [
                {'target_id': config['paged_content_page_model_tid'],
                 'target_type': 'taxonomy_term'}
            ],
            'field_member_of': [
                {'target_id': parent_node_id,
                 'target_type': 'node'}
            ],
            'field_weight': [
                {'value': weight}
            ],
            'field_display_hints': [
                {'target_id': parent_csv_record['field_display_hints'],
                 'target_type': 'taxonomy_term'}
            ]
        }

        # Some optional base fields, inherited from the parent object.
        if 'uid' in parent_csv_record:
            if len(parent_csv_record['uid']) > 0:
                node_json['uid'] = [{'target_id': parent_csv_record['uid']}]

        if 'created' in parent_csv_record:
            if len(parent_csv_record['created']) > 0:
                node_json['created'] = [{'value': parent_csv_record['created']}]

        node_headers = {
            'Content-Type': 'application/json'
        }
        node_endpoint = '/node?_format=json'
        node_response = issue_request(config, 'POST', node_endpoint, node_headers, node_json, None)
        if node_response.status_code == 201:
            node_uri = node_response.headers['location']
            print('+ Node for child "' + page_title + '" created at ' + node_uri + '.')
            logging.info('Node for child "%s" created at %s.', page_title, node_uri)
            if 'output_csv' in config.keys():
                write_to_output_csv(config, page_identifier, node_response.text)
        else:
            logging.warning('Node for page "%s" not created, HTTP response code was %s.', page_identifier, node_response.status_code)

        page_file_path = os.path.join(parent_id, page_file_name)
        media_response_status_code = create_media(config, page_file_path, node_uri)
        allowed_media_response_codes = [201, 204]
        if media_response_status_code in allowed_media_response_codes:
            logging.info("Media for %s created.", page_file_path)
