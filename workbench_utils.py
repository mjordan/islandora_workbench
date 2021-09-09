import os
import sys
import json
import csv
import openpyxl
import time
import string
import re
import copy
import logging
import datetime
import requests
import subprocess
import hashlib
import mimetypes
import collections
import urllib.parse
from pathlib import Path
from ruamel.yaml import YAML, YAMLError
from unidecode import unidecode
import edtf_validate.valid_edtf
import shutil


yaml = YAML()


def set_config_defaults(args):
    """Convert the YAML configuration data into an array for easy use.
       Also set some sensible default config values.
    """
    # Check existence of configuration file.
    if not os.path.exists(args.config):
        # Since the main logger gets its log file location from this file, we
        # need to define a local logger to write to the default log file location,
        # 'workbench.log'.
        logging.basicConfig(
            filename='workbench.log',
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%d-%b-%y %H:%M:%S')
        message = 'Error: Configuration file "' + args.config + '" not found.'
        logging.error(message)
        sys.exit(message)

    try:
        with open(args.config, 'r') as f:
            config_file_contents = f.read()
            original_config_data = yaml.load(config_file_contents)
            # Convert all keys to lower case.
            config_data = collections.OrderedDict()
            for k, v in original_config_data.items():
                if isinstance(k, str):
                    k = k.lower()
                    config_data[k] = v
    except YAMLError as e:
        # Since the main logger gets its log file location from this file, we
        # need to define a local logger to write to the default log file location,
        # 'workbench.log'.
        logging.basicConfig(
            filename='workbench.log',
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%d-%b-%y %H:%M:%S')

        message = 'Error: There appears to be a YAML syntax error with the configuration file "' + args.config + '". ' \
            '\nIf you use an online YAML validator to find the error, *be sure to remove your Drupal hostname and user credentials first.*'
        logging.exception(message)
        sys.exit(message + "\n" + str(e))

    config = {}
    for k, v in config_data.items():
        config[k] = v

    # Add the location of the config file. We do not
    # check for this in the config file itself.
    if os.path.isabs(args.config):
        config['config_file_path'] = args.config
    else:
        config['config_file_path'] = os.path.join(os.getcwd(), args.config)
    # Set up defaults for some settings.
    if 'input_dir' not in config:
        config['input_dir'] = 'input_data'
    if 'input_csv' not in config:
        config['input_csv'] = 'metadata.csv'
    if 'media_use_tid' not in config:
        config['media_use_tid'] = 'http://pcdm.org/use#OriginalFile'
    # @todo: remove 'drupal_filesystem' when Workbench drops support
    # for create_islandora_media().
    if 'drupal_filesystem' not in config:
        config['drupal_filesystem'] = 'fedora://'
    if 'id_field' not in config:
        config['id_field'] = 'id'
    if 'content_type' not in config:
        config['content_type'] = 'islandora_object'
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
    if 'update_mode' not in config:
        config['update_mode'] = 'replace'
    if 'validate_title_length' not in config:
        config['validate_title_length'] = True
    if 'paged_content_from_directories' not in config:
        config['paged_content_from_directories'] = False
    if 'delete_media_with_nodes' not in config:
        config['delete_media_with_nodes'] = True
    if 'allow_adding_terms' not in config:
        config['allow_adding_terms'] = False
    if 'nodes_only' not in config:
        config['nodes_only'] = False
    if 'log_json' not in config:
        config['log_json'] = False
    if 'log_headers' not in config:
        config['log_headers'] = False
    if 'progress_bar' not in config:
        config['progress_bar'] = False
    if 'user_agent' not in config:
        config['user_agent'] = 'Islandora Workbench'
    if 'allow_redirects' not in config:
        config['allow_redirects'] = True
    if 'secure_ssl_only' not in config:
        config['secure_ssl_only'] = True
    if 'google_sheets_csv_filename' not in config:
        config['google_sheets_csv_filename'] = 'google_sheet.csv'
    if 'google_sheets_gid' not in config:
        config['google_sheets_gid'] = '0'
    if 'excel_worksheet' not in config:
        config['excel_worksheet'] = 'Sheet1'
    if 'excel_csv_filename' not in config:
        config['excel_csv_filename'] = 'excel.csv'
    if 'ignore_csv_columns' not in config:
        config['ignore_csv_columns'] = list()
    if 'use_node_title_for_media' not in config:
        config['use_node_title_for_media'] = False
    if 'delete_tmp_upload' not in config:
        config['delete_tmp_upload'] = False
    if 'list_missing_drupal_fields' not in config:
        config['list_missing_drupal_fields'] = False
    if 'secondary_tasks' not in config:
        config['secondary_tasks'] = None
    if 'secondary_tasks_data_file' not in config:
        config['secondary_tasks_data_file'] = 'id_to_node_map.tsv'
    if 'fixity_algorithm' not in config:
        config['fixity_algorithm'] = None
    if 'validate_fixity_during_check' not in config:
        config['validate_fixity_during_check'] = False
    # Used for integration tests only, in which case it will either be True or False.
    if 'drupal_8' not in config:
        config['drupal_8'] = None

    if config['task'] == 'create':
        if 'id_field' not in config:
            config['id_field'] = 'id'
    if config['task'] == 'add_media':
        if 'id_field' not in config:
            config['id_field'] = 'node_id'
    if config['task'] == 'create' or config['task'] == 'create_from_files':
        if 'published' not in config:
            config['published'] = 1

    if config['task'] == 'create' or config['task'] == 'add_media' or config['task'] == 'create_from_files':
        if 'preprocessors' in config_data:
            config['preprocessors'] = {}
            for preprocessor in config_data['preprocessors']:
                for key, value in preprocessor.items():
                    config['preprocessors'][key] = value

        if 'media_types' not in config:
            config['media_types'] = []
            image = collections.OrderedDict({'image': ['png', 'gif', 'jpg', 'jpeg']})
            config['media_types'].append(image)
            document = collections.OrderedDict({'document': ['pdf', 'doc', 'docx', 'ppt', 'pptx']})
            config['media_types'].append(document)
            file = collections.OrderedDict({'file': ['tif', 'tiff', 'jp2', 'zip', 'tar']})
            config['media_types'].append(file)
            audio = collections.OrderedDict({'audio': ['mp3', 'wav', 'aac']})
            config['media_types'].append(audio)
            video = collections.OrderedDict({'video': ['mp4']})
            config['media_types'].append(video)
            extracted_text = collections.OrderedDict({'extracted_text': ['txt']})
            config['media_types'].append(extracted_text)

        # Set config['media_bundle_file_fields']. If 'media_fields' option is present in
        # the config file, determine which field to use for the file, per media bundle.
        # Note that 'media_file_fields' is the option used in the config file, and that
        # config['media_bundle_file_fields'] is the internal name of the setting.
        media_fields = dict({
            'file': 'field_media_file',
            'document': 'field_media_document',
            'image': 'field_media_image',
            'audio': 'field_media_audio_file',
            'video': 'field_media_video_file',
            'extracted_text': 'field_media_file',
            'fits_technical_metadata': 'field_media_file'
        })
        if 'media_file_fields' in config:
            for media_field in config['media_file_fields']:
                for media_type, media_field in media_field.items():
                    media_fields[media_type] = media_field
        else:
            config['media_fields'] = media_fields

        config['media_bundle_file_fields'] = media_fields

    if config['task'] == 'create':
        if 'paged_content_sequence_seprator' not in config:
            config['paged_content_sequence_seprator'] = '-'
        if 'paged_content_page_content_type' not in config:
            config['paged_content_page_content_type'] = config['content_type']

    if args.check:
        config['check'] = True
    else:
        config['check'] = False

    if args.get_csv_template:
        config['get_csv_template'] = True
    else:
        config['get_csv_template'] = False

    return config


def set_media_type(config, filepath, file_fieldname, csv_row):
    """Using configuration options, determine which media bundle type to use.
       Options are either a single media type or a set of mappings from
       file extenstion to media type.
    """
    if 'media_type' in config:
        return config['media_type']

    if filepath.strip().startswith('http'):
        preprocessed_file_path = get_prepocessed_file_path(config, file_fieldname, csv_row)
        filename = preprocessed_file_path.split('/')[-1]
        extension = filename.split('.')[-1]
        extension_with_dot = '.' + extension
    else:
        extension_with_dot = os.path.splitext(filepath)[-1]

    extension = extension_with_dot[1:]
    normalized_extension = extension.lower()
    for types in config['media_types']:
        for type, extensions in types.items():
            if normalized_extension in extensions:
                return type

    # If extension isn't in one of the lists, default to 'file' bundle.
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
            if str(tid).startswith('http'):
                tid = get_term_id_from_uri(config, tid)
            if normalized_extension in extensions:
                return tid
            # If the file's extension is not listed in the config,
            # We use the term ID that contains an empty extension.
            if '' in extensions:
                return tid


def issue_request(
        config,
        method,
        path,
        headers=dict(),
        json='',
        data='',
        query={}):
    """Issue the HTTP request to Drupal. Note: calls to non-Drupal URLs
       do not use this function.
    """
    if config['check'] is False:
        if 'pause' in config and method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            time.sleep(config['pause'])

    headers.update({'User-Agent': config['user_agent']})

    config['host'] = config['host'].rstrip('/')
    if config['host'] in path:
        url = path
    else:
        url = config['host'] + path

    if method == 'GET':
        if config['log_headers'] is True:
            logging.info(headers)
        response = requests.get(
            url,
            allow_redirects=config['allow_redirects'],
            verify=config['secure_ssl_only'],
            auth=(config['username'], config['password']),
            params=query,
            headers=headers
        )
    if method == 'HEAD':
        if config['log_headers'] is True:
            logging.info(headers)
        response = requests.head(
            url,
            allow_redirects=config['allow_redirects'],
            verify=config['secure_ssl_only'],
            auth=(config['username'], config['password']),
            headers=headers
        )
    if method == 'POST':
        if config['log_headers'] is True:
            logging.info(headers)
        if config['log_json'] is True:
            logging.info(json)
        response = requests.post(
            url,
            allow_redirects=config['allow_redirects'],
            verify=config['secure_ssl_only'],
            auth=(config['username'], config['password']),
            headers=headers,
            json=json,
            data=data
        )
    if method == 'PUT':
        if config['log_headers'] is True:
            logging.info(headers)
        if config['log_json'] is True:
            logging.info(json)
        response = requests.put(
            url,
            allow_redirects=config['allow_redirects'],
            verify=config['secure_ssl_only'],
            auth=(config['username'], config['password']),
            headers=headers,
            json=json,
            data=data
        )
    if method == 'PATCH':
        if config['log_headers'] is True:
            logging.info(headers)
        if config['log_json'] is True:
            logging.info(json)
        response = requests.patch(
            url,
            allow_redirects=config['allow_redirects'],
            verify=config['secure_ssl_only'],
            auth=(config['username'], config['password']),
            headers=headers,
            json=json,
            data=data
        )
    if method == 'DELETE':
        if config['log_headers'] is True:
            logging.info(headers)
        response = requests.delete(
            url,
            allow_redirects=config['allow_redirects'],
            verify=config['secure_ssl_only'],
            auth=(config['username'], config['password']),
            headers=headers
        )
    return response


def get_drupal_core_version(config):
    """Get Drupal's version number.

        Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        Returns
        -------
        string|False
            The Drupal core version number string (i.e., may contain -dev, etc.).
    """
    url = config['host'] + '/islandora_workbench_integration/core_version'
    response = issue_request(config, 'GET', url)
    if response.status_code == 200:
        version_body = json.loads(response.text)
        return version_body['core_version']
    else:
        logging.warning(
            "Attempt to get Drupal core version number returned a %s status code", response.status_code)
        return False


def convert_drupal_core_version_to_number(version_string):
    """Convert Drupal's version string to a number. We only need the major and minor numbers (e.g. 9.2).

        Parameters
        ----------
        version_string: string
            The version string as retrieved from Drupal.
        Returns
        -------
        tuple
            A tuple containing the major and minor Drupal core version numbers as integers.
    """
    parts = version_string.split('.')
    parts = parts[:2]
    int_parts = [int(part) for part in parts]
    version_tuple = tuple(int_parts)
    return version_tuple


def check_drupal_core_version(config):
    """Used during --check.
    """
    drupal_core_version = get_drupal_core_version(config)
    if drupal_core_version is not False:
        core_version_number = convert_drupal_core_version_to_number(drupal_core_version)
    else:
        message = "Workbench cannot determine Drupal's version number."
        logging.error(message)
        sys.exit('Error: ' + message)
    if core_version_number < tuple([8, 6]):
        message = "Warning: Media creation in your version of Drupal (" + \
            drupal_core_version + \
            ") is less reliable than in Drupal 8.6 or higher."
        print(message)


def set_drupal_8(config):
    """Used for integration tests only, in which case it
       will either be True or False.
    """
    if config['drupal_8'] is not None:
        return config['drupal_8']

    drupal_8 = False
    drupal_core_version_string = get_drupal_core_version(config)
    if drupal_core_version_string is not False:
        drupal_core_version = convert_drupal_core_version_to_number(drupal_core_version_string)
    else:
        message = "Workbench cannot determine Drupal's version number."
        logging.error(message)
        sys.exit('Error: ' + message)
    if drupal_core_version < tuple([8, 6]):
        drupal_8 = True
    return drupal_8


def ping_node(config, nid):
    """Ping the node to see if it exists.
    """
    url = config['host'] + '/node/' + nid + '?_format=json'
    response = issue_request(config, 'HEAD', url)
    # @todo: Add 301 and 302 to the allowed status codes?
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


def ping_vocabulary(config, vocab_id):
    """Ping the node to see if it exists.
    """
    url = config['host'] + '/entity/taxonomy_vocabulary/' + vocab_id.strip() + '?_format=json'
    response = issue_request(config, 'GET', url)
    if response.status_code == 200:
        return True
    else:
        logging.warning(
            "Node ping (HEAD) on %s returned a %s status code",
            url,
            response.status_code)
        return False


def ping_islandora(config, print_message=True):
    """Connect to Islandora in prep for subsequent HTTP requests.
    """
    # First, test a known request that requires Administrator-level permissions.
    url = config['host'] + '/islandora_workbench_integration/upload_max_filesize'
    try:
        host_response = issue_request(config, 'GET', url)
    except requests.exceptions.Timeout as err_timeout:
        message = 'Workbench timed out trying to reach ' + \
            config['host'] + '. Please verify the "host" setting in your configuration ' + \
            'and check your network connection.'
        logging.error(message)
        logging.error(err_timeout)
        sys.exit('Error: ' + message)
    except requests.exceptions.ConnectionError as error_connection:
        message = 'Workbench cannot connect to ' + \
            config['host'] + '. Please verify the "host" setting in your configuration ' + \
            'and check your network connection.'
        logging.error(message)
        logging.error(error_connection)
        sys.exit('Error: ' + message)

    if host_response.status_code == 404:
        message = 'Workbench cannot detect whether the Islandora Workbench Integration module is ' + \
            'enabled on ' + config['host'] + '. Please ensure it is enabled.'
        logging.error(message)
        sys.exit('Error: ' + message)

    not_authorized = [401, 403]
    if host_response.status_code in not_authorized:
        message = 'Workbench can connect to ' + \
            config['host'] + ' but the user "' + config['username'] + \
            '" does not have sufficient permissions to continue, or the credentials are invalid.'
        logging.error(message)
        sys.exit('Error: ' + message)

    if config['secure_ssl_only'] is True:
        message = "OK, connection to Drupal at " + config['host'] + " verified."
    else:
        message = "OK, connection to Drupal at " + config['host'] + " verified. Ignoring SSL certificates."
    if print_message is True:
        logging.info(message)
        print(message)


def ping_media_bundle(config, bundle_name):
    """Ping the Media bunlde/type to see if it exists. Return the status code,
       a 200 if it exists or a 404 if it doesn't exist or the Media Type REST resource
       is not enabled on the target Drupal.
    """
    url = config['host'] + '/entity/media_type/' + bundle_name + '?_format=json'
    response = issue_request(config, 'GET', url)
    return response.status_code


def ping_remote_file(config, url):
    """Logging, exiting, etc. happens in caller, except on requests error.
    """
    sections = urllib.parse.urlparse(url)
    try:
        response = requests.head(url, allow_redirects=True, verify=config['secure_ssl_only'])
        return response.status_code
    except requests.exceptions.Timeout as err_timeout:
        message = 'Workbench timed out trying to reach ' + \
            sections.netloc + ' while connecting to ' + url + '. Please verify that URL and check your network connection.'
        logging.error(message)
        logging.error(err_timeout)
        sys.exit('Error: ' + message)
    except requests.exceptions.ConnectionError as error_connection:
        message = 'Workbench cannot connect to ' + \
            sections.netloc + ' while connecting to ' + url + '. Please verify that URL and check your network connection.'
        logging.error(message)
        logging.error(error_connection)
        sys.exit('Error: ' + message)


def get_nid_from_url_alias(config, url_alias):
    """Gets a node ID from a URL alias.

        Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        url_alias : string
            The full URL alias, including http://, etc.
        Returns
        -------
        int
            The node ID, or False if the URL alias cannot be found.
    """
    url = url_alias + '?_format=json'
    response = issue_request(config, 'GET', url)
    if response.status_code != 200:
        return False
    else:
        node = json.loads(response.text)
        return node['nid'][0]['value']


def get_field_definitions(config, entity_type, bundle_type=None):
    """Get field definitions from Drupal.

        Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        entity_type : string
            One of 'node', 'media', or 'taxonomy_term'.
        bundle_type : string
            None for nodes (the content type can optionally be gotten from config),
            the vocabulary name, or the media type (image', 'document', 'audio',
            'video', 'file', etc.).
        Returns
        -------
        dict
            A dictionary with field names as keys and values arrays containing
            field config data. Config data varies slightly by entity type.
    """
    ping_islandora(config, print_message=False)
    field_definitions = {}

    if entity_type == 'node':
        bundle_type = config['content_type']
        fields = get_entity_fields(config, entity_type, bundle_type)
        for fieldname in fields:
            field_definitions[fieldname] = {}
            raw_field_config = get_entity_field_config(config, fieldname, entity_type, bundle_type)
            field_config = json.loads(raw_field_config)
            field_definitions[fieldname]['entity_type'] = field_config['entity_type']
            field_definitions[fieldname]['required'] = field_config['required']
            field_definitions[fieldname]['label'] = field_config['label']
            raw_vocabularies = [x for x in field_config['dependencies']['config'] if re.match("^taxonomy.vocabulary.", x)]
            if len(raw_vocabularies) > 0:
                vocabularies = [x.replace("taxonomy.vocabulary.", '')
                                for x in raw_vocabularies]
                field_definitions[fieldname]['vocabularies'] = vocabularies
            '''
            if entity_type == 'media' and 'file_extensions' in field_config['settings']:
                field_definitions[fieldname]['file_extensions'] = field_config['settings']['file_extensions']
            if entity_type == 'media':
                field_definitions[fieldname]['media_type'] = bundle_type
            '''
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
            if field_storage['type'] == 'typed_relation' and 'rel_types' in field_config['settings']:
                field_definitions[fieldname]['typed_relations'] = field_config['settings']['rel_types']

        field_definitions['title'] = {'entity_type': 'node', 'required': True, 'label': 'Title', 'field_type': 'string', 'cardinality': 1, 'max_length': 255, 'target_type': None}

    if entity_type == 'taxonomy_term':
        fields = get_entity_fields(config, 'taxonomy_term', bundle_type)
        for fieldname in fields:
            field_definitions[fieldname] = {}
            raw_field_config = get_entity_field_config(config, fieldname, entity_type, bundle_type)
            field_config = json.loads(raw_field_config)
            # print(field_config)
            field_definitions[fieldname]['entity_type'] = field_config['entity_type']
            field_definitions[fieldname]['required'] = field_config['required']
            field_definitions[fieldname]['label'] = field_config['label']
            raw_field_storage = get_entity_field_storage(config, fieldname, entity_type)
            field_storage = json.loads(raw_field_storage)
            # print(field_storage)
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

        field_definitions['term_name'] = {'entity_type': 'taxonomy_term', 'required': True, 'label': 'Name', 'field_type': 'string', 'cardinality': 1, 'max_length': 255, 'target_type': None}

    if entity_type == 'media':
        # @note: this section is incomplete.
        fields = get_entity_fields(config, entity_type, bundle_type)
        for fieldname in fields:
            field_definitions[fieldname] = {}
            if entity_type == 'media' and 'file_extensions' in field_config['settings']:
                field_definitions[fieldname]['file_extensions'] = field_config['settings']['file_extensions']
            if entity_type == 'media':
                field_definitions[fieldname]['media_type'] = bundle_type

    return field_definitions


def get_entity_fields(config, entity_type, bundle_type):
    """Get all the fields configured on a bundle.
    """
    if entity_type == 'taxonomy_term':
        fields_endpoint = config['host'] + '/entity/entity_form_display/' + \
            entity_type + '.' + bundle_type + '.default?_format=json'
        bundle_type_response = issue_request(config, 'GET', fields_endpoint)
    else:
        fields_endpoint = config['host'] + '/entity/entity_form_display/' + \
            entity_type + '.' + bundle_type + '.default?_format=json'
        bundle_type_response = issue_request(config, 'GET', fields_endpoint)

    fields = []

    if bundle_type_response.status_code == 200:
        node_config_raw = json.loads(bundle_type_response.text)
        fieldname_prefix = 'field.field.node.' + bundle_type + '.'
        fieldnames = [
            field_dependency.replace(
                fieldname_prefix,
                '') for field_dependency in node_config_raw['dependencies']['config']]
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
    """Get a specific fields's configuration.

       Example query for taxo terms: /entity/field_config/taxonomy_term.islandora_media_use.field_external_uri?_format=json
    """
    field_config_endpoint = config['host'] + '/entity/field_config/' + entity_type + '.' + bundle_type + '.' + fieldname + '?_format=json'
    field_config_response = issue_request(config, 'GET', field_config_endpoint)
    if field_config_response.status_code == 200:
        return field_config_response.text
    else:
        message = 'Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled.'
        logging.error(message)
        sys.exit('Error: ' + message)


def get_entity_field_storage(config, fieldname, entity_type):
    """Get a specific fields's storage configuration.

       Example query for taxo terms: /entity/field_storage_config/taxonomy_term.field_external_uri?_format=json
    """
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
    logging.info(
        'Starting configuration check for "%s" task using config file %s.',
        config['task'],
        args.config)

    ping_islandora(config, print_message=False)

    base_fields = ['title', 'status', 'promote', 'sticky', 'uid', 'created']
    # Any new reserved columns introduced into the CSV need to be removed here. 'langcode' is a standard Drupal field
    # but it doesn't show up in any field configs.
    reserved_fields = [config['id_field'], 'file', 'media_use_tid', 'checksum', 'node_id', 'url_alias', 'image_alt_text', 'parent_id', 'langcode']

    # Check the config file.
    tasks = [
        'create',
        'update',
        'delete',
        'add_media',
        'delete_media',
        'create_from_files']
    joiner = ', '
    if config['task'] not in tasks:
        message = '"task" in your configuration file must be one of "create", "update", "delete", "add_media", or "create_from_files".'
        logging.error(message)
        sys.exit('Error: ' + message)

    config_keys = list(config.keys())
    config_keys.remove('check')

    # Check for presence of required config keys, which varies by task.
    if config['task'] == 'create':
        if config['nodes_only'] is True:
            message = '"nodes_only" option in effect. Media files will not be checked/validated.'
            print(message)
            logging.info(message)

        create_required_options = [
            'task',
            'host',
            'username',
            'password']
        for create_required_option in create_required_options:
            if create_required_option not in config_keys:
                message = 'Please check your config file for required values: ' + joiner.join(create_required_options) + '.'
                logging.error(message)
                sys.exit('Error: ' + message)
    if config['task'] == 'update':
        update_required_options = [
            'task',
            'host',
            'username',
            'password']
        for update_required_option in update_required_options:
            if update_required_option not in config_keys:
                message = 'Please check your config file for required values: ' + joiner.join(update_required_options) + '.'
                logging.error(message)
                sys.exit('Error: ' + message)
        update_mode_options = ['replace', 'append', 'delete']
        if config['update_mode'] not in update_mode_options:
            message = 'Your "update_mode" config option must be one of the following: ' + joiner.join(update_mode_options) + '.'
            logging.error(message)
            sys.exit('Error: ' + message)

    if config['task'] == 'delete':
        delete_required_options = [
            'task',
            'host',
            'username',
            'password']
        for delete_required_option in delete_required_options:
            if delete_required_option not in config_keys:
                message = 'Please check your config file for required values: ' + joiner.join(delete_required_options) + '.'
                logging.error(message)
                sys.exit('Error: ' + message)
    if config['task'] == 'add_media':
        add_media_required_options = [
            'task',
            'host',
            'username',
            'password']
        for add_media_required_option in add_media_required_options:
            if add_media_required_option not in config_keys:
                message = 'Please check your config file for required values: ' + joiner.join(add_media_required_options) + '.'
                logging.error(message)
                sys.exit('Error: ' + message)
    if config['task'] == 'delete_media':
        delete_media_required_options = [
            'task',
            'host',
            'username',
            'password']
        for delete_media_required_option in delete_media_required_options:
            if delete_media_required_option not in config_keys:
                message = 'Please check your config file for required values: ' + joiner.join(delete_media_required_options) + '.'
                logging.error(message)
                sys.exit('Error: ' + message)
    message = 'OK, configuration file has all required values (did not check for optional values).'
    print(message)
    logging.info(message)

    validate_input_dir(config)

    check_csv_file_exists(config, 'node_fields')

    # Check column headers in CSV file.
    csv_data = get_csv_data(config)
    csv_column_headers = csv_data.fieldnames

    # Check whether each row contains the same number of columns as there are headers.
    for count, row in enumerate(csv_data, start=1):
        extra_headers = False
        field_count = 0
        for field in row:
            # 'stringtopopulateextrafields' is added by get_csv_data() if there are extra headers.
            if row[field] == 'stringtopopulateextrafields':
                extra_headers = True
            else:
                field_count += 1
        if extra_headers is True:
            message = "Row " + str(count) + " (ID " + row[config['id_field']] + ") of the CSV file has fewer columns " +  \
                "than there are headers (" + str(len(csv_column_headers)) + ")."
            logging.error(message)
            sys.exit('Error: ' + message)
        # Note: this message is also generated in get_csv_data() since CSV Writer thows an exception if the row has
        # form fields than headers.
        if len(csv_column_headers) < field_count:
            message = "Row " + str(count) + " (ID " + row[config['id_field']] + ") of the CSV file has more columns (" +  \
                str(field_count) + ") than there are headers (" + str(len(csv_column_headers)) + ")."
            logging.error(message)
            sys.exit('Error: ' + message)
    message = "OK, all " \
        + str(count) + " rows in the CSV file have the same number of columns as there are headers (" \
        + str(len(csv_column_headers)) + ")."
    print(message)
    logging.info(message)

    # Task-specific CSV checks.
    langcode_was_present = False
    if config['task'] == 'create':
        field_definitions = get_field_definitions(config, 'node')
        if config['id_field'] not in csv_column_headers:
            message = 'For "create" tasks, your CSV file must have a column containing a unique identifier.'
            logging.error(message)
            sys.exit('Error: ' + message)
        if config['nodes_only'] is False and 'file' not in csv_column_headers and config['paged_content_from_directories'] is False:
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
            validate_url_aliases_csv_data = get_csv_data(config)
            validate_url_aliases(config, validate_url_aliases_csv_data)

        # Specific to creating aggregated content such as collections, compound objects and paged content. Currently, if 'parent_id' is present
        # in the CSV file 'field_member_of' is mandatory.
        if 'parent_id' in csv_column_headers:
            if ('field_weight' not in csv_column_headers):
                message = 'If ingesting paged content, or compound objects where order is required a "field_weight" column is required.'
                logging.info(message)
            if ('field_member_of' not in csv_column_headers):
                message = 'If your CSV file contains a "parent_id" column, it must also contain an empty "field_member_of" column.'
                logging.error(message)
                sys.exit('Error: ' + message)
        drupal_fieldnames = []
        for drupal_fieldname in field_definitions:
            drupal_fieldnames.append(drupal_fieldname)

        if len(drupal_fieldnames) == 0:
            message = 'Workbench cannot retrieve field definitions from Drupal. Please confirm that the Field, Field Storage, and Entity Form Display REST resources are enabled.'
            logging.error(message)
            sys.exit('Error: ' + message)

        if config['list_missing_drupal_fields'] is True:
            missing_drupal_fields = []
            for csv_column_header in csv_column_headers:
                if csv_column_header not in drupal_fieldnames and csv_column_header not in base_fields:
                    if csv_column_header not in reserved_fields and csv_column_header not in get_additional_files_config(config).keys():
                        if csv_column_header != config['id_field']:
                            missing_drupal_fields.append(csv_column_header)
            if len(missing_drupal_fields) > 0:
                missing_drupal_fields_message = ', '.join(missing_drupal_fields)
                logging.error("The following header(s) require a matching Drupal field name: %s.", missing_drupal_fields_message)
                sys.exit('Error: The following header(s) require a matching Drupal field name: ' + missing_drupal_fields_message + '.')

        # We .remove() CSV column headers for this check because they are not Drupal field names (including 'langcode').
        for reserved_field in reserved_fields:
            if reserved_field in csv_column_headers:
                csv_column_headers.remove(reserved_field)

        # langcode is a standard Drupal field but it doesn't show up in any field configs.
        if 'langcode' in csv_column_headers:
            csv_column_headers.remove('langcode')
            # Set this so we can validate langcode below.
            langcode_was_present = True

        for csv_column_header in csv_column_headers:
            if get_additional_files_config(config) is not None:
                if csv_column_header not in drupal_fieldnames and csv_column_header not in base_fields and csv_column_header not in get_additional_files_config(config).keys():
                    if csv_column_header in config['ignore_csv_columns']:
                        continue
                    additional_files_entries = get_additional_files_config(config)
                    if csv_column_header in additional_files_entries.keys():
                        continue
                    logging.error('CSV column header %s does not match any Drupal, reserved, or "additional_files" field names.', csv_column_header)
                    sys.exit('Error: CSV column header "' + csv_column_header + '" does not match any Drupal, reserved, or "additional_files" field names.')
            else:
                if csv_column_header not in drupal_fieldnames and csv_column_header not in base_fields and csv_column_header:
                    if csv_column_header in config['ignore_csv_columns']:
                        continue
                    logging.error("CSV column header %s does not match any Drupal or reserved field names.", csv_column_header)
                    sys.exit('Error: CSV column header "' + csv_column_header + '" does not match any Drupal or reserved field names.')
        message = 'OK, CSV column headers match Drupal field names.'
        print(message)
        logging.info(message)

    # Check that Drupal fields that are required are in the CSV file (create task only).
    if config['task'] == 'create':
        required_drupal_fields = []
        for drupal_fieldname in field_definitions:
            # In the create task, we only check for required fields that apply to nodes.
            if 'entity_type' in field_definitions[drupal_fieldname] and field_definitions[
                    drupal_fieldname]['entity_type'] == 'node':
                if 'required' in field_definitions[drupal_fieldname] and field_definitions[
                        drupal_fieldname]['required'] is True:
                    required_drupal_fields.append(drupal_fieldname)
        for required_drupal_field in required_drupal_fields:
            if required_drupal_field not in csv_column_headers:
                logging.error(
                    "Required Drupal field %s is not present in the CSV file.",
                    required_drupal_field)
                sys.exit(
                    'Error: Field "' +
                    required_drupal_field +
                    '" required for content type "' +
                    config['content_type'] +
                    '" is not present in the CSV file.')
        message = 'OK, required Drupal fields are present in the CSV file.'
        print(message)
        logging.info(message)

        # Validate dates in 'created' field, if present.
        if 'created' in csv_column_headers:
            validate_node_created_csv_data = get_csv_data(config)
            validate_node_created_date(validate_node_created_csv_data)
        # Validate user IDs in 'uid' field, if present.
        if 'uid' in csv_column_headers:
            validate_node_uid_csv_data = get_csv_data(config)
            validate_node_uid(config, validate_node_uid_csv_data)

    if config['task'] == 'update':
        if 'node_id' not in csv_column_headers:
            message = 'For "update" tasks, your CSV file must contain a "node_id" column.'
            logging.error(message)
            sys.exit('Error: ' + message)
        if 'url_alias' in csv_column_headers:
            validate_url_aliases_csv_data = get_csv_data(config)
            validate_url_aliases(config, validate_url_aliases_csv_data)
        field_definitions = get_field_definitions(config, 'node')
        drupal_fieldnames = []
        for drupal_fieldname in field_definitions:
            drupal_fieldnames.append(drupal_fieldname)
        if 'title' in csv_column_headers:
            csv_column_headers.remove('title')
        if 'url_alias' in csv_column_headers:
            csv_column_headers.remove('url_alias')
        if 'image_alt_text' in csv_column_headers:
            csv_column_headers.remove('image_alt_text')
        if 'media_use_tid' in csv_column_headers:
            csv_column_headers.remove('media_use_tid')
        if 'file' in csv_column_headers:
            message = 'Error: CSV column header "file" is not allowed in update tasks.'
            logging.error(message)
            sys.exit(message)
        if 'node_id' in csv_column_headers:
            csv_column_headers.remove('node_id')

        # langcode is a standard Drupal field but it doesn't show up in any field configs.
        if 'langcode' in csv_column_headers:
            csv_column_headers.remove('langcode')
            # Set this so we can validate langcode below.
            langcode_was_present = True

        for csv_column_header in csv_column_headers:
            if csv_column_header not in drupal_fieldnames and csv_column_header not in base_fields:
                if csv_column_header in config['ignore_csv_columns']:
                    continue
                logging.error(
                    'CSV column header %s does not match any Drupal field names.',
                    csv_column_header)
                sys.exit(
                    'Error: CSV column header "' +
                    csv_column_header +
                    '" does not match any Drupal field names.')
        message = 'OK, CSV column headers match Drupal field names.'
        print(message)
        logging.info(message)

    if config['task'] == 'add_media' or config['task'] == 'create' and config['nodes_only'] is False:
        validate_media_use_tid(config)
        validate_media_use_tid_values_csv_data = get_csv_data(config)
        validate_media_use_tids_in_csv(config, validate_media_use_tid_values_csv_data)

        if config['fixity_algorithm'] is not None:
            allowed_algorithms = ['md5', 'sha1', 'sha256']
            if config['fixity_algorithm'] not in allowed_algorithms:
                message = "Configured fixity algorithm '" + config['fixity_algorithm'] + "' must be one of 'md5', 'sha1', or 'sha256'."
                logging.error(message)
                sys.exit('Error: ' + message)

        if config['validate_fixity_during_check'] is True and config['fixity_algorithm'] is not None:
            print("Performing local checksum validation. This might take some time.")
            if 'file' in csv_column_headers and 'checksum' in csv_column_headers:
                validate_checksums_csv_data = get_csv_data(config)
                if config['task'] == 'add_media':
                    row_id = 'node_id'
                else:
                    row_id = config['id_field']
                checksum_validation_all_ok = True
                for checksum_validation_row_count, checksum_validation_row in enumerate(validate_checksums_csv_data, start=1):
                    file_path = checksum_validation_row['file']
                    hash_from_local = get_file_hash_from_local(config, file_path, config['fixity_algorithm'])
                    if 'checksum' in checksum_validation_row:
                        if hash_from_local == checksum_validation_row['checksum'].strip():
                            logging.info('Local %s checksum and value in the CSV "checksum" field for file "%s" (%s) match.', config['fixity_algorithm'], file_path, hash_from_local)
                        else:
                            checksum_validation_all_ok = False
                            logging.warning('Local %s checksum and value in the CSV "checksum" field for file "%s" (named in CSV row "%s") do not match (local: %s, CSV: %s).',
                                            config['fixity_algorithm'], file_path, checksum_validation_row[row_id], hash_from_local, checksum_validation_row['checksum'])

                if checksum_validation_all_ok is True:
                    checksum_validation_message = "OK, checksum validation during complete. All checks pass."
                    logging.info(checksum_validation_message)
                    print(checksum_validation_message + " See the log for more detail.")
                else:
                    checksum_validation_message = "Not all checksum validation passed."
                    logging.warning(checksum_validation_message)
                    print("Warning: " + checksum_validation_message + " See the log for more detail.")

    if config['task'] == 'update' or config['task'] == 'create':
        validate_geolocation_values_csv_data = get_csv_data(config)
        validate_geolocation_fields(config, field_definitions, validate_geolocation_values_csv_data)

        validate_link_values_csv_data = get_csv_data(config)
        validate_link_fields(config, field_definitions, validate_link_values_csv_data)

        validate_edtf_values_csv_data = get_csv_data(config)
        validate_edtf_fields(config, field_definitions, validate_edtf_values_csv_data)

        validate_csv_field_cardinality_csv_data = get_csv_data(config)
        validate_csv_field_cardinality(config, field_definitions, validate_csv_field_cardinality_csv_data)

        validate_csv_field_length_csv_data = get_csv_data(config)
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
            validate_taxonomy_field_csv_data = get_csv_data(config)
            warn_user_about_taxo_terms = validate_taxonomy_field_values(config, field_definitions, validate_taxonomy_field_csv_data)
        if warn_user_about_taxo_terms is True:
            print('Warning: Issues detected with validating taxonomy field values in the CSV file. See the log for more detail.')

        if 'vocab_csv' in config and len(config['vocab_csv']) > 0:
            for vocab_csv_file in config['vocab_csv']:
                for complex_vocab_id, complex_vocab_csv_file_path in vocab_csv_file.items():
                    complex_vocab_exists = ping_vocabulary(config, complex_vocab_id)
                    if complex_vocab_exists is False:
                        message = 'Vocabulary "' + complex_vocab_id + '" specified in the "vocab_csv" setting does not exist.'
                        logging.error(message)
                        sys.exit('Error: ' + message)
                    check_csv_file_exists(config, 'taxonomy_fields', complex_vocab_csv_file_path)
                    validate_vocabulary_fields_in_csv(config, complex_vocab_id, complex_vocab_csv_file_path)

        validate_csv_typed_relation_values_csv_data = get_csv_data(config)
        warn_user_about_typed_relation_terms = validate_typed_relation_field_values(config, field_definitions, validate_csv_typed_relation_values_csv_data)
        if warn_user_about_typed_relation_terms is True:
            print('Warning: Issues detected with validating typed relation field values in the CSV file. See the log for more detail.')

        # Validate length of 'title'.
        if config['validate_title_length']:
            validate_title_csv_data = get_csv_data(config)
            for count, row in enumerate(validate_title_csv_data, start=1):
                if 'title' in row and len(row['title']) > 255:
                    message = "The 'title' column in row " + str(count) + " of your CSV file exceeds Drupal's maximum length of 255 characters."
                    logging.error(message)
                    sys.exit('Error: ' + message)

        # Validate existence of nodes specified in 'field_member_of'. This could be generalized out to validate node IDs in other fields.
        # See https://github.com/mjordan/islandora_workbench/issues/90.
        validate_field_member_of_csv_data = get_csv_data(config)
        for count, row in enumerate(validate_field_member_of_csv_data, start=1):
            if 'field_member_of' in csv_column_headers:
                parent_nids = row['field_member_of'].split(config['subdelimiter'])
                for parent_nid in parent_nids:
                    if len(parent_nid) > 0:
                        parent_node_exists = ping_node(config, parent_nid)
                        if parent_node_exists is False:
                            message = "The 'field_member_of' field in row " + \
                                str(count) + " of your CSV file contains a node ID (" + parent_nid + ") that doesn't exist."
                            logging.error(message)
                            sys.exit('Error: ' + message)

        # Validate 'langcode' values if that field exists in the CSV.
        if langcode_was_present:
            validate_langcode_csv_data = get_csv_data(config)
            for count, row in enumerate(validate_langcode_csv_data, start=1):
                langcode_valid = validate_language_code(row['langcode'])
                if not langcode_valid:
                    message = "Row " + \
                        str(count) + " of your CSV file contains an invalid Drupal language code (" + row['langcode'] + ") in its 'langcode' column."
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
        file_check_csv_data = get_csv_data(config)
        if config['nodes_only'] is False and config['allow_missing_files'] is False:
            for count, file_check_row in enumerate(file_check_csv_data, start=1):
                if len(file_check_row['file']) == 0:
                    message = 'CSV row ' + file_check_row[config['id_field']] + ' contains an empty "file" value.'
                    logging.error(message)
                    sys.exit('Error: ' + message)
                file_check_row['file'] = file_check_row['file'].strip()
                if file_check_row['file'].startswith('http'):
                    http_response_code = ping_remote_file(config, file_check_row['file'])
                    if http_response_code != 200 or ping_remote_file(config, file_check_row['file']) is False:
                        message = 'Remote file ' + file_check_row['file'] + ' identified in CSV "file" column for record with ID field value ' \
                            + file_check_row[config['id_field']] + ' not found or not accessible (HTTP response code ' + str(http_response_code) + ').'
                        logging.error(message)
                        sys.exit('Error: ' + message)
                if os.path.isabs(file_check_row['file']):
                    file_path = file_check_row['file']
                else:
                    file_path = os.path.join(config['input_dir'], file_check_row['file'])
                if not file_check_row['file'].startswith('http'):
                    if not os.path.exists(file_path) or not os.path.isfile(file_path):
                        message = 'File ' + file_path + ' identified in CSV "file" column for record with ID field value ' \
                            + file_check_row[config['id_field']] + ' not found.'
                        logging.error(message)
                        sys.exit('Error: ' + message)
            message = 'OK, files named in the CSV "file" column are all present.'
            print(message)
            logging.info(message)
        empty_file_values_exist = False
        if config['nodes_only'] is False and config['allow_missing_files'] is True:
            for count, file_check_row in enumerate(file_check_csv_data, start=1):
                if len(file_check_row['file']) == 0:
                    empty_file_values_exist = True
                else:
                    if os.path.isabs(file_check_row['file']):
                        file_path = file_check_row['file']
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

        # Verify that all media bundles/types exist.
        if config['nodes_only'] is False:
            media_type_check_csv_data = get_csv_data(config)
            for count, file_check_row in enumerate(media_type_check_csv_data, start=1):
                filename_fields_to_check = ['file']
                if 'additional_files' in config and len(config['additional_files']) > 0:
                    additional_files_entries = get_additional_files_config(config)
                    filename_fields_to_check.extend(additional_files_entries.keys())
                for filename_field in filename_fields_to_check:
                    if len(file_check_row[filename_field]) != 0:
                        media_type = set_media_type(config, file_check_row[filename_field], filename_field, file_check_row)
                        media_bundle_response_code = ping_media_bundle(config, media_type)
                        if media_bundle_response_code == 404:
                            message = 'File "' + file_check_row[filename_field] + '" identified in CSV row ' + file_check_row[config['id_field']] + \
                                ' will create a media of type (' + media_type + '), but that media type is not configured in the destination Drupal.'
                            logging.error(message)
                            sys.exit('Error: ' + message)

        # @todo: check that each file's extension is allowed for the current media type using get_registered_media_extensions().
        # See https://github.com/mjordan/islandora_workbench/issues/126. Maybe also compare allowed extensions with those in
        # 'media_type[s]' config option?

    # Check existence of fields identified in 'additional_files' config setting, and the files named in those fields.
    # Also check for the acommpanying Media Use tid.
    if (config['task'] == 'create' or config['task'] == 'add_media') and config['paged_content_from_directories'] is False:
        if 'additional_files' in config and len(config['additional_files']) > 0:
            additional_files_entries = get_additional_files_config(config)
            additional_files_check_csv_data = get_csv_data(config)
            additional_files_fields = additional_files_entries.keys()
            additional_files_fields_csv_headers = additional_files_check_csv_data.fieldnames
            if config['nodes_only'] is False:
                for additional_file_field in additional_files_fields:
                    if additional_file_field not in additional_files_fields_csv_headers:
                        message = 'CSV column "' + additional_file_field + '" registered in the "additional_files" configuration setting is missing from your CSV file.'
                        logging.error(message)
                        sys.exit('Error: ' + message)

            # Verify media use tids.
            for additional_files_media_use_field, additional_files_media_use_tid in additional_files_entries.items():
                validate_media_use_tid_in_additional_files_setting(config, additional_files_media_use_tid, additional_files_media_use_field)

            if config['nodes_only'] is False and config['allow_missing_files'] is False:
                for count, file_check_row in enumerate(additional_files_check_csv_data, start=1):
                    for additional_file_field in additional_files_fields:
                        if len(file_check_row[additional_file_field]) == 0:
                            message = 'CVS row ' + file_check_row[config['id_field']] + ' contains an empty "' + additional_file_field + '" value.'
                            logging.error(message)
                            sys.exit('Error: ' + message)
                        file_check_row[additional_file_field] = file_check_row[additional_file_field].strip()
                        if file_check_row[additional_file_field].startswith('http'):
                            http_response_code = ping_remote_file(config, file_check_row[additional_file_field])
                            if http_response_code != 200 or ping_remote_file(config, file_check_row[additional_file_field]) is False:
                                message = 'Remote file ' + file_check_row[additional_file_field] + ' identified in CSV "' + additional_file_field + '" column for record with ID field value ' \
                                    + file_check_row[config['id_field']] + ' not found or not accessible (HTTP response code ' + str(http_response_code) + ').'
                                logging.error(message)
                                sys.exit('Error: ' + message)
                        if os.path.isabs(file_check_row[additional_file_field]):
                            file_path = file_check_row[additional_file_field]
                        else:
                            file_path = os.path.join(config['input_dir'], file_check_row[additional_file_field])
                        if not file_check_row[additional_file_field].startswith('http'):
                            if not os.path.exists(file_path) or not os.path.isfile(file_path):
                                message = 'File ' + file_path + ' identified in CSV "' + additional_file_field + '" column for record with ID field value ' \
                                    + file_check_row[config['id_field']] + ' not found.'
                                logging.error(message)
                                sys.exit('Error: ' + message)
                message = 'OK, files named in the CSV "' + additional_file_field + '" column are all present.'
                print(message)
                logging.info(message)
            empty_file_values_exist = False
            if config['nodes_only'] is False and config['allow_missing_files'] is True:
                additional_files_check_csv_data = get_csv_data(config)
                additional_file_fields_for_message = []
                for count, file_check_row in enumerate(additional_files_check_csv_data, start=1):
                    for additional_file_field in additional_files_fields:
                        if len(file_check_row[additional_file_field]) == 0:
                            empty_file_values_exist = True
                        else:
                            if file_check_row[additional_file_field].startswith('http'):
                                http_response_code = ping_remote_file(config, file_check_row[additional_file_field])
                                if http_response_code != 200 or ping_remote_file(config, file_check_row[additional_file_field]) is False:
                                    message = 'Remote file ' + file_check_row[additional_file_field] + ' identified in CSV "' + additional_file_field + '" column for record with ID field value ' \
                                        + file_check_row[config['id_field']] + ' not found or not accessible (HTTP response code ' + str(http_response_code) + ').'
                                    logging.error(message)
                                    sys.exit('Error: ' + message)
                            else:
                                if os.path.isabs(file_check_row[additional_file_field]):
                                    file_path = file_check_row[additional_file_field]
                                else:
                                    file_path = os.path.join(config['input_dir'], file_check_row[additional_file_field])
                                if not os.path.exists(file_path) or not os.path.isfile(file_path):
                                    message = 'File ' + file_path + ' identified in CSV "' + additional_file_field + '" column not found.'
                                    logging.error(message)
                                    sys.exit('Error: ' + message)
                        if '"' + additional_file_field + '"' not in additional_file_fields_for_message:
                            additional_file_fields_for_message.append('"' + additional_file_field + '"')
                if empty_file_values_exist is True:
                    message = 'OK, files named in the CSV ' + ', '.join(additional_file_fields_for_message) + ' column(s) are all present; the "allow_missing_files" ' + \
                        'option is enabled and empty ' + ', '.join(additional_file_fields_for_message) + ' values exist.'
                    print(message)
                    logging.info(message)
                else:
                    message = 'OK, files named in the CSV ' + ', '.join(additional_file_fields_for_message) + ' column(s) are all present.'
                    print(message)
                    logging.info(message)

    if config['task'] == 'create' and config['paged_content_from_directories'] is True:
        if 'paged_content_page_model_tid' not in config:
            message = 'If you are creating paged content, you must include "paged_content_page_model_tid" in your configuration.'
            logging.error('Configuration requires "paged_content_page_model_tid" setting when creating paged content.')
            sys.exit('Error: ' + message)
        paged_content_from_directories_csv_data = get_csv_data(config)
        for count, file_check_row in enumerate(paged_content_from_directories_csv_data, start=1):
            dir_path = os.path.join(config['input_dir'], file_check_row[config['id_field']])
            if not os.path.exists(dir_path) or os.path.isfile(dir_path):
                message = 'Page directory ' + dir_path + ' for CSV record with ID "' + file_check_row[config['id_field']] + '"" not found.'
                logging.error(message)
                sys.exit('Error: ' + message)
            page_files = os.listdir(dir_path)
            if len(page_files) == 0:
                print(
                    'Warning: Page directory ' +
                    dir_path +
                    ' is empty; is that intentional?')
                logging.warning('Page directory ' + dir_path + ' is empty.')
            for page_file_name in page_files:
                if config['paged_content_sequence_seprator'] not in page_file_name:
                    message = 'Page file ' + os.path.join(
                        dir_path,
                        page_file_name) + ' does not contain a sequence separator (' + config['paged_content_sequence_seprator'] + ').'
                    logging.error(message)
                    sys.exit('Error: ' + message)

        print('OK, page directories are all present.')

    # Check for bootstrap scripts, if any are configured.
    bootsrap_scripts_present = False
    if 'bootstrap' in config and len(config['bootstrap']) > 0:
        bootsrap_scripts_present = True
        for bootstrap_script in config['bootstrap']:
            if not os.path.exists(bootstrap_script):
                message = "Bootstrap script " + bootstrap_script + " not found."
                logging.error(message)
                sys.exit('Error: ' + message)
            if os.access(bootstrap_script, os.X_OK) is False:
                message = "Bootstrap script " + bootstrap_script + " is not executable."
                logging.error(message)
                sys.exit('Error: ' + message)
        if bootsrap_scripts_present is True:
            message = "OK, registered bootstrap scripts found and executable."
            logging.info(message)
            print(message)

    # Check for preprocessor scripts, if any are configured.
    preprocessor_scripts_present = False
    if 'preprocessors' in config and len(config['preprocessors']) > 0:
        preprocessor_scripts_present = True
        for preprocessor_script in config['preprocessors']:
            if not os.path.exists(preprocessor_script):
                message = "Preprocessor script " + preprocessor_script + " not found."
                logging.error(message)
                sys.exit('Error: ' + message)
            if os.access(preprocessor_script, os.X_OK) is False:
                message = "Preprocessor script " + preprocessor_script + " is not executable."
                logging.error(message)
                sys.exit('Error: ' + message)
        if preprocessor_scripts_present is True:
            message = "OK, registered preprocessor scripts found and executable."
            logging.info(message)
            print(message)

    # Check for the existence and executableness of post-action scripts, if any are configured.
    if config['task'] == 'create' or config['task'] == 'update' or config['task'] == 'add_media':
        post_action_scripts_configs = ['node_post_create', 'node_post_update', 'media_post_create']
        for post_action_script_config in post_action_scripts_configs:
            post_action_scripts_present = False
            if post_action_script_config in config and len(config[post_action_script_config]) > 0:
                post_action_scripts_present = True
                for post_action_script in config[post_action_script_config]:
                    if not os.path.exists(post_action_script):
                        message = "Post-action script " + post_action_script + " not found."
                        logging.error(message)
                        sys.exit('Error: ' + message)
                    if os.access(post_action_script, os.X_OK) is False:
                        message = "Post-action script " + post_action_script + " is not executable."
                        logging.error(message)
                        sys.exit('Error: ' + message)
            if post_action_scripts_present is True:
                message = "OK, registered post-action scripts found and executable."
                logging.info(message)
                print(message)

    # If nothing has failed by now, exit with a positive, upbeat message.
    print("Configuration and input data appear to be valid.")
    logging.info('Configuration checked for "%s" task using config file "%s", no problems found.', config['task'], args.config)

    if config['secondary_tasks'] is None:
        sys.exit(0)
    else:
        for secondary_config_file in config['secondary_tasks']:
            print("")
            print('Running --check using secondary configuration file "' + secondary_config_file + '"')
            cmd = ["./workbench", "--config", secondary_config_file, "--check"]
            output = subprocess.run(cmd)

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

    ping_islandora(config, print_message=False)

    config_keys = list(config.keys())
    unwanted_in_create_from_files = [
        'check',
        'delimiter',
        'subdelimiter',
        'allow_missing_files',
        'validate_title_length',
        'paged_content_from_directories',
        'delete_media_with_nodes',
        'allow_adding_terms']
    for option in unwanted_in_create_from_files:
        if option in config_keys:
            config_keys.remove(option)

    # Check for presence of required config keys.
    create_required_options = [
        'task',
        'host',
        'username',
        'password']
    for create_required_option in create_required_options:
        if create_required_option not in config_keys:
            message = 'Please check your config file for required values: ' \
                + joiner.join(create_options) + '.'
            logging.error(message)
            sys.exit('Error: ' + message)

    # Check existence of input directory.
    if os.path.exists(config['input_dir']):
        message = 'OK, input directory "' + config['input_dir'] + '" found.'
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
            message = 'The filename "' + filename_without_extension + \
                '" exceeds Drupal\'s maximum length of 255 characters and cannot be used for a node title.'
            logging.error(message)
            sys.exit('Error: ' + message)

    # Check that either 'model' or 'models' are present in the config file.
    if ('model' not in config and 'models' not in config):
        message = 'You must include either the "model" or "models" option in your configuration.'
        logging.error(message)
        sys.exit('Error: ' + message)

    # If nothing has failed by now, exit with a positive message.
    print("Configuration and input data appear to be valid.")
    logging.info(
        'Configuration checked for "%s" task using config file %s, no problems found.',
        config['task'],
        args.config)
    sys.exit(0)


def log_field_cardinality_violation(field_name, record_id, cardinality):
    """Writes an entry to the log during create/update tasks if any field values
       are sliced off. Workbench does this if the number of values in a field
       exceeds the field's cardinality. record_id could be a value from the
       configured id_field or a node ID.
    """
    logging.warning(
        "Adding all values in CSV field %s for record %s would exceed maximum " +
        "number of allowed values (%s), so only adding first value.",
        field_name,
        record_id,
        cardinality)


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
    """Convert row values to strings and strip leading and trailing whitespace.
       Could be used in the future for other normalization tasks.
    """
    for field in row:
        row[field] = str(row[field]).strip()
    return row


def truncate_csv_value(field_name, record_id, field_config, value):
    """Drupal will not accept field values that have a length that
       exceeds the configured maximum length for that field. 'value'
       here is a field subvalue.
    """
    if isinstance(value, str) and 'max_length' in field_config:
        max_length = field_config['max_length']
        if max_length is not None and len(value) > int(max_length):
            original_value = value
            value = value[:max_length]
            logging.warning(
                'CSV field value "%s" in field "%s" (record ID %s) truncated at %s characters as required by the field\'s configuration.',
                original_value,
                field_name,
                record_id,
                max_length)
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


def get_additional_files_config(config):
    """Converts values in 'additional_files' config setting to a simple
       dictionary for easy access.
    """
    if 'additional_files' in config and len(config['additional_files']) > 0:
        additional_files_entries = dict()
        for additional_files_entry in config['additional_files']:
            for additional_file_field, additional_file_media_use_tid in additional_files_entry.items():
                additional_files_entries[additional_file_field] = additional_file_media_use_tid
        return additional_files_entries
    else:
        return None


def split_typed_relation_string(config, typed_relation_string, target_type):
    """Fields of type 'typed_relation' are represented in the CSV file
       using a structured string, specifically namespace:property:id,
       e.g., 'relators:pht:5'. 'id' is either a term ID or a node ID. This
       function takes one of those strings (optionally with a multivalue
       subdelimiter) and returns a list of dictionaries in the form they
       take in existing node values.

       Also, these values can (but don't need to) have an optional namespace
       in the term ID segment, which is the vocabulary ID string. These
       typed relation strings look like 'relators:pht:person:Jordan, Mark'.
       However, since we split the typed relation strings only on the first
       two :, we don't need to worry about what's in the third segment.
    """
    return_list = []
    temp_list = typed_relation_string.split(config['subdelimiter'])
    for item in temp_list:
        item_list = item.split(':', 2)
        if value_is_numeric(item_list[2]):
            target_id = int(item_list[2])
        else:
            target_id = item_list[2]
        item_dict = {
            'target_id': target_id,
            'rel_type': item_list[0] + ':' + item_list[1],
            'target_type': target_type}
        return_list.append(item_dict)

    return return_list


def split_geolocation_string(config, geolocation_string):
    """Fields of type 'geolocation' are represented in the CSV file using a
       structured string, specifically lat,lng, e.g. "49.16667, -123.93333"
       or "+49.16667, -123.93333". This function takes one of those strings
       (optionally with a multivalue subdelimiter) and returns a list of
       dictionaries with 'lat' and 'lng' keys required by the 'geolocation'
       field type.
    """
    return_list = []
    temp_list = geolocation_string.split(config['subdelimiter'])
    for item in temp_list:
        item_list = item.split(',')
        # Remove any leading \ which might be in value if it comes from a spreadsheet.
        item_dict = {'lat': item_list[0].lstrip('\\').strip(), 'lng': item_list[1].lstrip('\\').strip()}
        return_list.append(item_dict)

    return return_list


def split_link_string(config, link_string):
    """Fields of type 'link' are represented in the CSV file using a structured string,
       specifically uri%%title, e.g. "https://www.lib.sfu.ca%%SFU Library Website".
       This function takes one of those strings (optionally with a multivalue subdelimiter)
       and returns a list of dictionaries with 'uri' and 'title' keys required by the
       'link' field type.
    """
    return_list = []
    temp_list = link_string.split(config['subdelimiter'])
    for item in temp_list:
        if '%%' in item:
            item_list = item.split('%%', 1)
            item_dict = {'uri': item_list[0].strip(), 'title': item_list[1].strip()}
            return_list.append(item_dict)
        else:
            # If there is no %% and title, use the URL as the title.
            item_dict = {'uri': item.strip(), 'title': item.strip()}
            return_list.append(item_dict)

    return return_list


def validate_media_use_tid_in_additional_files_setting(config, media_use_tid_value, additional_field_name):
    """Validate whether the term ID registered in the "additional_files" config setting
       is in the Islandora Media Use vocabulary.
    """
    media_use_tids = []
    if (config['subdelimiter'] in str(media_use_tid_value)):
        media_use_tids = str(media_use_tid_value).split(config['subdelimiter'])
    else:
        media_use_tids.append(media_use_tid_value)

    for media_use_tid in media_use_tids:
        if not value_is_numeric(media_use_tid) and media_use_tid.strip().startswith('http'):
            media_use_tid = get_term_id_from_uri(config, media_use_tid.strip())
        if not value_is_numeric(media_use_tid) and not media_use_tid.strip().startswith('http'):
            media_use_tid = find_term_in_vocab(config, 'islandora_media_use', media_use_tid.strip())

        term_endpoint = config['host'] + '/taxonomy/term/' + str(media_use_tid).strip() + '?_format=json'
        headers = {'Content-Type': 'application/json'}
        response = issue_request(config, 'GET', term_endpoint, headers)
        if response.status_code == 404:
            message = 'Term ID "' + str(media_use_tid) + '" registered in the "additional_files" config option ' + \
                'for field "' + additional_field_name + '" is not a term ID (term doesn\'t exist).'
            logging.error(message)
            sys.exit('Error: ' + message)
        if response.status_code == 200:
            response_body = json.loads(response.text)
            if 'vid' in response_body:
                if response_body['vid'][0]['target_id'] != 'islandora_media_use':
                    message = 'Term ID "' + str(media_use_tid) + '" registered in the "additional_files" config option ' + \
                        'for field "' + additional_field_name + '" is not in the Islandora Media Use vocabulary.'
                    logging.error(message)
                    sys.exit('Error: ' + message)
            if 'field_external_uri' in response_body:
                if response_body['field_external_uri'][0]['uri'] != 'http://pcdm.org/use#OriginalFile':
                    message = 'Warning: Term ID "' + str(media_use_tid) + '" registered in the "additional_files" config option ' + \
                        'for field "' + additional_field_name + '" will assign an Islandora Media Use term that might ' + \
                        "conflict with derivative media. You should temporarily disable the Context or Action that generates those derivatives."
                    print(message)
                    logging.warning(message)


def validate_media_use_tid(config, media_use_tid_value_from_csv=None, csv_row_id=None):
    """Validate whether the term ID, term name, or terms URI provided in the
       config value for media_use_tid is in the Islandora Media Use vocabulary.
    """
    if media_use_tid_value_from_csv is not None and csv_row_id is not None:
        if len(str(media_use_tid_value_from_csv)) > 0:
            media_use_tid_value = media_use_tid_value_from_csv
            message_wording = ' in the CSV "media_use_tid" column '
    else:
        media_use_tid_value = config['media_use_tid']
        message_wording = ' in configuration option "media_use_tid" '

    media_use_terms = str(media_use_tid_value).split(config['subdelimiter'])
    for media_use_term in media_use_terms:
        if value_is_numeric(media_use_term) is not True and media_use_term.strip().startswith('http'):
            media_use_tid = get_term_id_from_uri(config, media_use_term.strip())
            if csv_row_id is None:
                if media_use_tid is False:
                    message = 'URI "' + media_use_term + '" provided ' + message_wording + ' does not match any taxonomy terms.'
                    logging.error(message)
                    sys.exit('Error: ' + message)
                if media_use_tid is not False and media_use_term.strip() != 'http://pcdm.org/use#OriginalFile':
                    message = 'Warning: URI "' + media_use_term + '" provided ' + message_wording + \
                        "will assign an Islandora Media Use term that might conflict with derivative media. " + \
                        " You should temporarily disable the Context or Action that generates those derivatives."
                    print(message)
                    logging.warning(message)
            else:
                if media_use_tid is False:
                    message = 'URI "' + media_use_term + '" provided in "media_use_tid" field in CSV row ' + \
                        str(csv_row_id) + ' does not match any taxonomy terms.'
                    logging.error(message)
                    sys.exit('Error: ' + message)
                if media_use_tid is not False and media_use_term.strip() != 'http://pcdm.org/use#OriginalFile':
                    message = 'Warning: URI "' + media_use_term + '" provided in "media_use_tid" field in CSV row ' + \
                        str(csv_row_id) + "will assign an Islandora Media Use term that might conflict with " + \
                        "derivative media. You should temporarily disable the Context or Action that generates those derivatives."
                    logging.warning(message)

        elif value_is_numeric(media_use_term) is not True and media_use_term.strip().startswith('http') is not True:
            media_use_tid = find_term_in_vocab(config, 'islandora_media_use', media_use_term.strip())
            if csv_row_id is None:
                if media_use_tid is False:
                    message = 'Warning: Term name "' + media_use_term.strip() + '" provided in configuration option "media_use_tid" does not match any taxonomy terms.'
                    logging.warning(message)
                    sys.exit('Error: ' + message)
            else:
                if media_use_tid is False:
                    message = 'Warning: Term name "' + media_use_term.strip() + '" provided in "media_use_tid" field in CSV row ' + \
                        str(csv_row_id) + ' does not match any taxonomy terms.'
                    logging.warning(message)
                    sys.exit('Error: ' + message)
        else:
            # Confirm the tid exists and is in the islandora_media_use vocabulary
            term_endpoint = config['host'] + '/taxonomy/term/' + str(media_use_term.strip()) + '?_format=json'
            headers = {'Content-Type': 'application/json'}
            response = issue_request(config, 'GET', term_endpoint, headers)
            if response.status_code == 404:
                if csv_row_id is None:
                    message = 'Term ID "' + str(media_use_term) + '" used in the "media_use_tid" configuration option is not a term ID (term doesn\'t exist).'
                    logging.error(message)
                    sys.exit('Error: ' + message)
                else:
                    message = 'Term ID "' + str(media_use_term) + '" used in the "media_use_tid" field in CSV row ' + \
                        str(csv_row_id) + ' is not a term ID (term doesn\'t exist).'
                    logging.error(message)
                    sys.exit('Error: ' + message)
            if response.status_code == 200:
                response_body = json.loads(response.text)
                if csv_row_id is None:
                    if 'vid' in response_body:
                        if response_body['vid'][0]['target_id'] != 'islandora_media_use':
                            message = 'Term ID "' + \
                                str(media_use_term) + '" provided in configuration option "media_use_tid" is not in the Islandora Media Use vocabulary.'
                            logging.error(message)
                            sys.exit('Error: ' + message)
                    if 'field_external_uri' in response_body:
                        if response_body['field_external_uri'][0]['uri'] != 'http://pcdm.org/use#OriginalFile':
                            message = 'Warning: Term ID "' + media_use_term + '" provided in configuration option "media_use_tid" ' + \
                                "will assign an Islandora Media Use term that might conflict with derivative media. " + \
                                " You should temporarily disable the Context or Action that generates those derivatives."
                            print(message)
                            logging.warning(message)
                else:
                    if 'vid' in response_body:
                        if response_body['vid'][0]['target_id'] != 'islandora_media_use':
                            message = 'Term ID "' + \
                                str(media_use_term) + '" provided in the "media_use_tid" field in CSV row ' + \
                                str(csv_row_id) + ' is not in the Islandora Media Use vocabulary.'
                            logging.error(message)
                            sys.exit('Error: ' + message)
                    if 'field_external_uri' in response_body:
                        if response_body['field_external_uri'][0]['uri'] != 'http://pcdm.org/use#OriginalFile':
                            message = 'Warning: Term ID "' + media_use_term + '" provided in "media_use_tid" field in CSV row ' + \
                                str(csv_row_id) + " will assign an Islandora Media Use term that might conflict with " + \
                                "derivative media. You should temporarily disable the Context or Action that generates those derivatives."
                            print(message)
                            logging.warning(message)


def validate_media_use_tids_in_csv(config, csv_data):
    """Validate 'media_use_tid' values in CSV if they exist.
    """
    if config['task'] == 'add_media':
        csv_id_field = 'node_id'
    else:
        csv_id_field = config['id_field']

    for count, row in enumerate(csv_data, start=1):
        if 'media_use_tid' in row:
            delimited_field_values = row['media_use_tid'].split(config['subdelimiter'])
            for field_value in delimited_field_values:
                if len(field_value.strip()) > 0:
                    validate_media_use_tid(config, field_value, row[csv_id_field])


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
    """
    cmd = subprocess.Popen([path_to_script, path_to_config_file], stdout=subprocess.PIPE)
    result, stderrdata = cmd.communicate()

    return result, cmd.returncode


def execute_entity_post_task_script(path_to_script, path_to_config_file, http_response_code, entity_json=''):
    """Executes a entity-level post-task script and returns its output and exit status code.
    """
    cmd = subprocess.Popen([path_to_script, path_to_config_file, str(http_response_code), entity_json], stdout=subprocess.PIPE)
    result, stderrdata = cmd.communicate()

    return result, cmd.returncode


def create_file(config, filename, file_fieldname, node_csv_row):
    """Creates a file in Drupal, which is then referenced by the accompanying media.
           Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            filename : string
                The full path to the file (either from the 'file' CSV column or downloaded from somewhere).
            file_fieldname: string
                The name of the CSV column containing the filename.
            node_csv_row: OrderedDict
                E.g., OrderedDict([('file', 'IMG_5083.JPG'), ('id', '05'), ('title', 'Alcatraz Island').
            Returns
            -------
            string|int|bool|None
                The file ID of the successfully created file; the HTTP status code if the
                attempt was unsuccessful, False if there is insufficient information to create
                the file or file creation failed, or None if config['nodes_only'] or
                config['allow_missing_files'] is True.
    """
    if config['nodes_only'] is True:
        return None

    if config['task'] == 'add_media' or config['task'] == 'create':
        if config['allow_missing_files'] and len(node_csv_row[file_fieldname].strip()) == 0:
            return None

    is_remote = False
    filename = filename.strip()

    if filename.startswith('http'):
        remote_file_http_response_code = ping_remote_file(config, filename)
        if remote_file_http_response_code != 200:
            return False

        filename_parts = urllib.parse.urlparse(filename)
        file_path = download_remote_file(config, filename, file_fieldname, node_csv_row)
        if file_path is False:
            return False
        filename = file_path.split("/")[-1]
        is_remote = True
    elif os.path.isabs(filename):
        file_path = filename
    else:
        file_path = os.path.join(config['input_dir'], filename)

    mimetype = mimetypes.guess_type(file_path)
    media_type = set_media_type(config, file_path, file_fieldname, node_csv_row)
    if media_type in config['media_bundle_file_fields']:
        media_file_field = config['media_bundle_file_fields'][media_type]
    else:
        logging.error('File not created for CSV row "%s": media type "%s" not recognized.', node_csv_row[config['id_field']], media_type)
        return False

    # Requests/urllib3 requires filenames used in Content-Disposition headers to be encoded as latin-1.
    # Since it is impossible to reliably convert to latin-1 without knowing the source encoding of the filename
    # (which may or may not have originated on the machine running Workbench, so sys.stdout.encoding isn't reliable),
    # the best we can do for now is to use unidecode to replace non-ASCII characters in filenames with their ASCII
    # equivalents (at least the unidecode() equivalents). Also, while Requests requires filenames to be encoded
    # in latin-1, Drupal passes filenames through its validateUtf8() function. So ASCII is a low common denominator
    # of both requirements.
    ascii_only = is_ascii(filename)
    if ascii_only is False:
        original_filename = copy.copy(filename)
        filename = unidecode(filename)
        logging.warning("Filename '" + original_filename + "' contains non-ASCII characters, normalized to '" + filename + "'.")

    file_endpoint_path = '/file/upload/media/' + media_type + '/' + media_file_field + '?_format=json'
    file_headers = {
        'Content-Type': 'application/octet-stream',
        'Content-Disposition': 'file; filename="' + filename + '"'
    }

    binary_data = open(file_path, 'rb')

    try:
        file_response = issue_request(config, 'POST', file_endpoint_path, file_headers, '', binary_data)
        if file_response.status_code == 201:
            file_json = json.loads(file_response.text)
            file_id = file_json['fid'][0]['value']
            # For now, we can only validate checksums for files named in the 'file' CSV column.
            # See https://github.com/mjordan/islandora_workbench/issues/307.
            if config['fixity_algorithm'] is not None and file_fieldname == 'file':
                file_uuid = file_json['uuid'][0]['value']
                hash_from_drupal = get_file_hash_from_drupal(config, file_uuid, config['fixity_algorithm'])
                hash_from_local = get_file_hash_from_local(config, file_path, config['fixity_algorithm'])
                if hash_from_drupal == hash_from_local:
                    logging.info('Local and Drupal %s checksums for file "%s" (%s) match.', config['fixity_algorithm'], file_path, hash_from_local)
                else:
                    print("Warning: local and Drupal checksums for '" + file_path + "' do not match. See the log for more detail.")
                    logging.warning('Local and Drupal %s checksums for file "%s" (named in CSV row "%s") do not match (local: %s, Drupal: %s).',
                                    config['fixity_algorithm'], file_path, node_csv_row[config['id_field']], hash_from_local, hash_from_drupal)
                if 'checksum' in node_csv_row:
                    if hash_from_local == node_csv_row['checksum'].strip():
                        logging.info('Local %s checksum and value in the CSV "checksum" field for file "%s" (%s) match.', config['fixity_algorithm'], file_path, hash_from_local)
                    else:
                        print("Warning: local checksum and value in CSV for '" + file_path + "' do not match. See the log for more detail.")
                        logging.warning('Local %s checksum and value in the CSV "checksum" field for file "%s" (named in CSV row "%s") do not match (local: %s, CSV: %s).',
                                        config['fixity_algorithm'], file_path, node_csv_row[config['id_field']], hash_from_local, node_csv_row['checksum'])
            if is_remote and config['delete_tmp_upload'] is True:
                containing_folder = os.path.join(config['input_dir'], re.sub('[^A-Za-z0-9]+', '_', node_csv_row[config['id_field']]))
                shutil.rmtree(containing_folder)
            return file_id
        else:
            logging.error('File not created, POST request to "%s" returned an HTTP status code of "%s".', file_endpoint_path, file_response.status_code)
            return False
    except requests.exceptions.RequestException as e:
        logging.error(e)
        return False


def create_media(config, filename, file_fieldname, node_id, node_csv_row, media_use_tid=None):
    """Creates a media in Drupal.

           Parameters
           ----------
            config : dict
                The configuration object defined by set_config_defaults().
            filename : string
                The value of the CSV 'file' field for the current node.
            file_fieldname: string
                The name of the CSV column containing the filename.
            node_id: string
                The ID of the node to attach the media to. This is False if file creation failed.
            node_csv_row: OrderedDict
                E.g., OrderedDict([('file', 'IMG_5083.JPG'), ('id', '05'), ('title', 'Alcatraz Island').
            media_use_tid : int|str
                A valid term ID (or a subdelimited list of IDs) from the Islandora Media Use vocabulary.
            Returns
            -------
            int|False
                 The HTTP status code from the attempt to create the media, False if
                 it doesn't have sufficient information to create the media, or None
                 if config['nodes_only'] is True.
    """
    if config['nodes_only'] is True:
        return

    file_result = create_file(config, filename, file_fieldname, node_csv_row)
    if filename.startswith('http'):
        if file_result is False:
            return False
        filename = get_prepocessed_file_path(config, file_fieldname, node_csv_row)
    if isinstance(file_result, int):
        if 'media_use_tid' in node_csv_row and len(node_csv_row['media_use_tid']) > 0:
            media_use_tid_value = node_csv_row['media_use_tid']
        else:
            media_use_tid_value = config['media_use_tid']

        if media_use_tid is not None:
            media_use_tid_value = media_use_tid

        media_use_tids = []
        media_use_terms = str(media_use_tid_value).split(config['subdelimiter'])
        for media_use_term in media_use_terms:
            if value_is_numeric(media_use_term):
                media_use_tids.append(media_use_term)
            if not value_is_numeric(media_use_term) and media_use_term.strip().startswith('http'):
                media_use_tids.append(get_term_id_from_uri(config, media_use_term))
            if not value_is_numeric(media_use_term) and not media_use_term.strip().startswith('http'):
                media_use_tids.append(find_term_in_vocab(config, 'islandora_media_use', media_use_term.strip()))

        media_type = set_media_type(config, filename, file_fieldname, node_csv_row)
        media_field = config['media_fields'][media_type]

        if 'title' in node_csv_row:
            media_name = node_csv_row['title']
        else:
            media_name = os.path.basename(filename)

        media_json = {
            "bundle": [{
                "target_id": media_type,
                "target_type": "media_type",
            }],
            "status": [{
                "value": True
            }],
            "name": [{
                "value": media_name
            }],
            media_field: [{
                "target_id": file_result,
                "target_type": 'file'
            }],
            "field_media_of": [{
                "target_id": int(node_id),
                "target_type": 'node'
            }],
            "field_media_use": [{
                "target_id": media_use_tids[0],
                "target_type": 'taxonomy_term'
            }]
        }

        # @todo: We'll need a more generalized way of determining which media fields are required.
        if media_field == 'field_media_image':
            if 'image_alt_text' in node_csv_row and len(node_csv_row['image_alt_text']) > 0:
                alt_text = clean_image_alt_text(node_csv_row['image_alt_text'])
                media_json[media_field][0]['alt'] = alt_text
            else:
                alt_text = clean_image_alt_text(media_name)
                media_json[media_field][0]['alt'] = alt_text

        media_endpoint_path = '/entity/media'
        media_headers = {
            'Content-Type': 'application/json'
        }
        try:
            media_response = issue_request(config, 'POST', media_endpoint_path, media_headers, media_json)

            if len(media_use_tids) > 1:
                media_response_body = json.loads(media_response.text)
                if 'mid' in media_response_body:
                    media_id = media_response_body['mid'][0]['value']
                    patch_media_use_terms(config, media_id, media_type, media_use_tids)
                else:
                    logging.error("Could not PATCH additional media use terms to media created from '%s' because media ID is not available.", filename)

            # Execute media-specific post-create scripts, if any are configured.
            if 'media_post_create' in config and len(config['media_post_create']) > 0:
                for command in config['media_post_create']:
                    post_task_output, post_task_return_code = execute_entity_post_task_script(command, config['config_file_path'], media_response.status_code, media_response.text)
                    if post_task_return_code == 0:
                        logging.info("Post media create script " + command + " executed successfully.")
                    else:
                        logging.error("Post media create script " + command + " failed.")

            return media_response.status_code
        except requests.exceptions.RequestException as e:
            logging.error(e)
            return False

    if file_result is False:
        return file_result

    if file_result is None:
        return file_result


def create_islandora_media(config, filename, file_fieldname, node_uri, node_csv_row, media_use_tid=None):
    """node_csv_row is an OrderedDict, e.g.
       OrderedDict([('file', 'IMG_5083.JPG'), ('id', '05'), ('title', 'Alcatraz Island').

       Returns the HTTP status code from the attempt to create the media, or False if
       it doesn't have sufficient information to create the media.
    """
    if config['nodes_only'] is True:
        return

    is_remote = False

    filename = filename.strip()
    if filename.startswith('http'):
        remote_file_http_reponse = ping_remote_file(config, filename)
        if remote_file_http_reponse != 200:
            return False
        file_path = download_remote_file(config, filename, file_fieldname, node_csv_row)
        if file_path is False:
            return False
        filename = file_path.split("/")[-1]
        is_remote = True
    elif os.path.isabs(filename):
        file_path = filename
    else:
        file_path = os.path.join(config['input_dir'], filename)

    mimetype = mimetypes.guess_type(file_path)
    media_type = set_media_type(config, filename, file_fieldname, node_csv_row)

    if 'media_use_tid' in node_csv_row and len(node_csv_row['media_use_tid']) > 0:
        media_use_tid_value = node_csv_row['media_use_tid']
    else:
        media_use_tid_value = config['media_use_tid']

    if media_use_tid is not None:
        media_use_tid_value = media_use_tid

    media_use_tids = []
    media_use_terms = str(media_use_tid_value).split(config['subdelimiter'])
    for media_use_term in media_use_terms:
        if value_is_numeric(media_use_term):
            media_use_tids.append(media_use_term)
        if not value_is_numeric(media_use_term) and media_use_term.strip().startswith('http'):
            media_use_tids.append(get_term_id_from_uri(config, media_use_term))
        if not value_is_numeric(media_use_term) and not media_use_term.strip().startswith('http'):
            media_use_tids.append(find_term_in_vocab(config, 'islandora_media_use', media_use_term.strip()))

    media_endpoint_path = '/media/' + media_type + '/' + str(media_use_tids[0])
    media_endpoint = node_uri + media_endpoint_path
    location = config['drupal_filesystem'] + os.path.basename(filename)
    media_headers = {
        'Content-Type': mimetype[0],
        'Content-Location': location
    }
    binary_data = open(file_path, 'rb')
    media_response = issue_request(config, 'PUT', media_endpoint, media_headers, '', binary_data)

    # Execute media-specific post-create scripts, if any are configured.
    if 'media_post_create' in config and len(config['media_post_create']) > 0:
        for command in config['media_post_create']:
            post_task_output, post_task_return_code = execute_entity_post_task_script(command, config['config_file_path'], media_response.status_code, media_response.text)
            if post_task_return_code == 0:
                logging.info("Post media create script " + command + " executed successfully.")
            else:
                logging.error("Post media create script " + command + " failed.")

    if is_remote and config['delete_tmp_upload'] is True:
        containing_folder = os.path.join(config['input_dir'], re.sub('[^A-Za-z0-9]+', '_', node_csv_row[config['id_field']]))
        shutil.rmtree(containing_folder)

    if media_response.status_code == 201:
        if 'location' in media_response.headers:
            # A 201 response provides a 'location' header, but a '204' response does not.
            media_uri = media_response.headers['location']
            logging.info("Media (%s) created at %s, linked to node %s.", media_type, media_uri, node_uri)
            media_id = media_uri.rsplit('/', 1)[-1]
            patch_media_fields(config, media_id, media_type, node_csv_row)

            if media_type == 'image':
                patch_image_alt_text(config, media_id, node_csv_row)

            if len(media_use_tids) > 1:
                patch_media_use_terms(config, media_id, media_type, media_use_tids)
    elif media_response.status_code == 204:
        if len(media_use_tids) > 1:
            patch_media_use_terms(config, media_id, media_type, media_use_tids)
        logging.warning(
            "Media created and linked to node %s, but its URI is not available since its creation returned an HTTP status code of %s",
            node_uri,
            media_response.status_code)
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

    if len(media_json) > 1:
        endpoint = config['host'] + '/media/' + media_id + '?_format=json'
        headers = {'Content-Type': 'application/json'}
        response = issue_request(config, 'PATCH', endpoint, headers, media_json)
        if response.status_code == 200:
            logging.info("Media %s fields updated to match parent node's.", config['host'] + '/media/' + media_id)
        else:
            logging.warning("Media %s fields not updated to match parent node's.", config['host'] + '/media/' + media_id)


def patch_media_use_terms(config, media_id, media_type, media_use_tids):
    """Patch the media entity's field_media_use.
    """
    media_json = {
        'bundle': [
            {'target_id': media_type}
        ]
    }

    media_use_tids_json = []
    for media_use_tid in media_use_tids:
        media_use_tids_json.append({'target_id': media_use_tid, 'target_type': 'taxonomy_term'})

    media_json['field_media_use'] = media_use_tids_json
    endpoint = config['host'] + '/media/' + str(media_id) + '?_format=json'
    headers = {'Content-Type': 'application/json'}
    response = issue_request(config, 'PATCH', endpoint, headers, media_json)
    if response.status_code == 200:
        logging.info("Media %s Islandora Media Use terms updated.", config['host'] + '/media/' + str(media_id))
    else:
        logging.warning("Media %s Islandora Media Use terms not updated.", config['host'] + '/media/' + str(media_id))


def clean_image_alt_text(input_string):
    ''' Strip out HTML markup to guard against CSRF in alt text.
    '''
    cleaned_string = re.sub('<[^<]+?>', '', input_string)
    return cleaned_string


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
            alt_text = clean_image_alt_text(field_value)
        if field_name == 'image_alt_text' and len(field_value) > 0:
            alt_text = clean_image_alt_text(field_value)

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
    patch_response = issue_request(
        config,
        'PATCH',
        patch_endpoint,
        patch_headers,
        media_json)

    if patch_response.status_code != 200:
        logging.warning(
            "Alt text for image media %s not updated.",
            config['host'] + '/media/' + media_id)


def remove_media_and_file(config, media_id):
    """Delete a media and the file associated with it.
    """
    # First get the media JSON.
    get_media_url = '/media/' + str(media_id) + '?_format=json'
    get_media_response = issue_request(config, 'GET', get_media_url)
    get_media_response_body = json.loads(get_media_response.text)

    # These are the Drupal field names on the various types of media.
    file_fields = [
        'field_media_file',
        'field_media_image',
        'field_media_document',
        'field_media_audio_file',
        'field_media_video_file']
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
        logging.error(
            "File %s (from media %s) not deleted (HTTP response code %s).",
            file_id,
            media_id,
            file_response.status_code)

    # Then the media.
    if file_response.status_code == 204:
        media_endpoint = config['host'] + '/media/' + str(media_id) + '?_format=json'
        media_response = issue_request(config, 'DELETE', media_endpoint)
        if media_response.status_code == 204:
            logging.info("Media %s deleted.", media_id)
            return media_response.status_code
        else:
            logging.error(
                "Media %s not deleted (HTTP response code %s).",
                media_id,
                media_response.status_code)
            return False

    return False


def get_csv_data(config, csv_file_target='node_fields', file_path=None):
    """Read the input CSV data and prepare it for use in create, update, etc. tasks.

       This function reads the source CSV file (or the CSV dump from Google Sheets or Excel),
       applies some prepocessing to each CSV record (specifically, it adds any CSV field
       templates that are registered in the config file, and it filters out any CSV
       records or lines in the CSV file that begine with a #), and finally, writes out
       a version of the CSV data to a file that appends .prepocessed to the input
       CSV file name. It is this .prepocessed file that is used in create, update, etc.
       tasks.
    """
    """Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        csv_file_target: string
            Either 'node_fields' or 'taxonomy_fields'.
        file_path: string
            The path to the file to check (applies only to vocabulary CSVs).
        Returns
        -------
        preprocessed_csv_reader
            The CSV DictReader object.
    """

    if csv_file_target == 'taxonomy_fields':
        config['id_field'] = 'term_name'

    if csv_file_target == 'node_fields':
        file_path = config['input_csv']

    if os.path.isabs(file_path):
        input_csv_path = file_path
    elif file_path.startswith('http') is True:
        input_csv_path = os.path.join(config['input_dir'], config['google_sheets_csv_filename'])
    elif file_path.endswith('.xlsx') is True:
        input_csv_path = os.path.join(config['input_dir'], config['excel_csv_filename'])
    else:
        input_csv_path = os.path.join(config['input_dir'], file_path)

    if not os.path.exists(input_csv_path):
        message = 'Error: CSV file ' + input_csv_path + ' not found.'
        logging.error(message)
        sys.exit(message)

    try:
        # 'utf-8-sig' encoding skips Microsoft BOM (0xef, 0xbb, 0xbf) at the start of files,
        # e.g. exported from Excel and has no effect when reading standard UTF-8 encoded files.
        csv_reader_file_handle = open(input_csv_path, 'r', encoding="utf-8-sig", newline='')
    except (UnicodeDecodeError):
        message = 'Error: CSV file ' + input_csv_path + ' must be encoded in ASCII or UTF-8.'
        logging.error(message)
        sys.exit(message)

    # 'restval' is what is used to populate superfluous fields/labels.
    csv_writer_file_handle = open(input_csv_path + '.prepocessed', 'w+', newline='')
    csv_reader = csv.DictReader(csv_reader_file_handle, delimiter=config['delimiter'], restval='stringtopopulateextrafields')

    csv_reader_fieldnames = csv_reader.fieldnames
    confirmed = []
    duplicates = []
    for item in csv_reader_fieldnames:
        if item not in confirmed:
            confirmed.append(item)
        else:
            duplicates.append(item)
    if len(duplicates) > 0:
        message = "Error: CSV has duplicate header names - " + ', '.join(duplicates)
        logging.error(message)
        sys.exit(message)
    csv_reader_fieldnames = [x for x in csv_reader_fieldnames if x not in config['ignore_csv_columns']]

    tasks = ['create', 'update']
    # CSV field templates only apply to node CSV files, not vocabulary CSV files.
    if config['task'] in tasks and csv_file_target == 'node_fields' and 'csv_field_templates' in config and len(config['csv_field_templates']) > 0:
        # If the config file contains CSV field templates, append them to the CSV data.
        # Make a copy of the column headers so we can skip adding templates to the new CSV
        # if they're present in the source CSV. We don't want fields in the source CSV to be
        # stomped on by templates.
        csv_reader_fieldnames_orig = copy.copy(csv_reader_fieldnames)
        for template in config['csv_field_templates']:
            for field_name, field_value in template.items():
                if field_name not in csv_reader_fieldnames_orig:
                    csv_reader_fieldnames.append(field_name)
        csv_writer = csv.DictWriter(csv_writer_file_handle, fieldnames=csv_reader_fieldnames, delimiter=config['delimiter'])
        csv_writer.writeheader()
        row_num = 0
        unique_identifiers = []
        for row in csv_reader:
            row_num += 1

            # Remove columns specified in config['ignore_csv_columns'].
            if len(config['ignore_csv_columns']) > 0:
                for column_to_ignore in config['ignore_csv_columns']:
                    if column_to_ignore in row:
                        del row[column_to_ignore]

            for template in config['csv_field_templates']:
                for field_name, field_value in template.items():
                    if field_name not in csv_reader_fieldnames_orig:
                        row[field_name] = field_value

            # Skip CSV records whose first column begin with #.
            if not list(row.values())[0].startswith('#'):
                try:
                    unique_identifiers.append(row[config['id_field']])
                    csv_writer.writerow(row)
                except (ValueError):
                    # Note: this message is also generated in check_input().
                    message = "Row " + str(row_num) + " (ID " + row[config['id_field']] + ') of the CSV file "' + input_csv_path + '" ' + \
                              "has more columns (" + str(len(row)) + ") than there are headers (" + \
                              str(len(csv_reader.fieldnames)) + ').'
                    logging.error(message)
                    print('Error: ' + message)
                    sys.exit(message)
        repeats = set(([x for x in unique_identifiers if unique_identifiers.count(x) > 1]))
        if len(repeats) > 0:
            message = "Duplicate identifiers in column " + config['id_field'] + " found: " + str(repeats)
            logging.error(message)
            sys.exit("Error: " + message)
    else:
        csv_writer = csv.DictWriter(csv_writer_file_handle, fieldnames=csv_reader_fieldnames, delimiter=config['delimiter'])
        csv_writer.writeheader()
        row_num = 0
        for row in csv_reader:
            row_num += 1
            # Remove columns specified in config['ignore_csv_columns'].
            if len(config['ignore_csv_columns']) > 0:
                for column_to_ignore in config['ignore_csv_columns']:
                    if column_to_ignore in row:
                        del row[column_to_ignore]

            # Skip CSV records whose first column begin with #.
            if not list(row.values())[0].startswith('#'):
                try:
                    csv_writer.writerow(row)
                except (ValueError):
                    # Note: this message is also generated in check_input().
                    message = "Row " + str(row_num) + " (ID " + row[config['id_field']] + ') of the CSV file "' + input_csv_path + '" ' + \
                              "has more columns (" + str(len(row)) + ") than there are headers (" + \
                              str(len(csv_reader.fieldnames)) + ').'
                    logging.error(message)
                    sys.exit('Error: ' + message)

    csv_writer_file_handle.close()
    preprocessed_csv_reader_file_handle = open(input_csv_path + '.prepocessed', 'r')
    preprocessed_csv_reader = csv.DictReader(preprocessed_csv_reader_file_handle, delimiter=config['delimiter'], restval='stringtopopulateextrafields')
    return preprocessed_csv_reader


def get_term_pairs(config, vocab_id):
    """Get all the term IDs plus associated term names in a vocabulary. If
       the vocabulary does not exist, or is not registered with the view, the
       request to Drupal returns a 200 plus an empty JSON list, i.e., [].
    """
    term_dict = dict()
    # Note: this URL requires the view "Terms in vocabulary", which is created by the
    # by the Islandora Workbench Integation module, to be present on the target Drupal.
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
    # Some vocabularies use this View.
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
                terms_with_uri.append({term['tid'][0]['value']: term['vid'][0]['target_id']})
                tid = term_from_uri_response_body[0]['tid'][0]['value']
            print("Warning: See log for important message about use of term URIs.")
            logging.warning(
                'Term URI "%s" is used for more than one term (with these term ID/vocabulary ID combinations: ' +
                str(terms_with_uri) +
                '). Workbench is choosing the first term ID (%s)).',
                uri,
                tid)
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
                terms_with_uri.append({term['tid'][0]['value']: term['vid'][0]['target_id']})
                tid = term_from_authority_link_response_body[0]['tid'][0]['value']
            print("Warning: See log for important message about use of term URIs.")
            logging.warning(
                'Term URI "%s" is used for more than one term (with these term ID/vocabulary ID combinations: ' +
                str(terms_with_uri) +
                '). Workbench is choosing the first term ID (%s)).',
                uri,
                tid)
            return tid
        else:
            # URI does not match any term.
            return False

    # Non-200 response code.
    return False


def create_term(config, vocab_id, term_name, term_csv_row=None):
    """Adds a term to the target vocabulary. Returns the new term's ID
       if successful (or if the term already exists) or False if not.
    """

    # Check to see if term exists; if so, return its ID, if not, proceed to create it.
    tid = find_term_in_vocab(config, vocab_id, term_name)
    if value_is_numeric(tid):
        logging.info(
            'Term "%s" (term ID %s) already exists in vocabulary "%s".',
            term_name,
            tid,
            vocab_id)
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
               "target_id": str(vocab_id),
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
    response = issue_request(
        config,
        'POST',
        term_endpoint,
        headers,
        term,
        None)
    if response.status_code == 201:
        term_response_body = json.loads(response.text)
        tid = term_response_body['tid'][0]['value']
        logging.info(
            'Term %s ("%s") added to vocabulary "%s".',
            tid,
            term_name,
            vocab_id)
        return tid
    else:
        logging.warning(
            "Term '%s' not created, HTTP response code was %s.",
            term_name,
            response.status_code)
        return False


def get_term_uuid(config, term_id):
    """Given a term ID, get the term's UUID.
    """
    term_url = config['host'] + '/taxonomy/term/' + str(term_id) + '?_format=json'
    response = issue_request(config, 'GET', term_url)
    term = json.loads(response.text)
    uuid = term['uuid'][0]['value']

    return uuid


def create_url_alias(config, node_id, url_alias):
    json = {'path': [
            {'value': '/node/' + str(node_id)}
            ],
            'alias': [
            {'value': url_alias}
    ]
    }

    headers = {'Content-Type': 'application/json'}
    response = issue_request(
        config,
        'POST',
        config['host'] +
        '/entity/path_alias?_format=json',
        headers,
        json,
        None)
    if response.status_code != 201:
        logging.error(
            "URL alias '%s' not created for node %s, HTTP response code was %s (it might already exist).",
            url_alias,
            config['host'] +
            '/node/' +
            node_id,
            response.status_code)


def prepare_term_id(config, vocab_ids, term):
    """REST POST and PATCH operations require taxonomy term IDs, not term names. This
       funtion checks its 'term' argument to see if it's numeric (i.e., a term ID) and
       if it is, returns it as is. If it's not (i.e., a term name) it looks for the
       term name in the referenced vocabulary and returns its term ID (existing or
       newly created).
    """
    term = str(term)
    term = term.strip()
    if value_is_numeric(term):
        return term
    # Special case: if the term starts with 'http', assume it's a Linked Data URI
    # and get its term ID from the URI.
    elif term.startswith('http'):
        # Note: get_term_id_from_uri() will return False if the URI doesn't match
        # a term.
        tid_from_uri = get_term_id_from_uri(config, term)
        if value_is_numeric(tid_from_uri):
            return tid_from_uri
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
                [vocab_id, term_name] = term.split(':', maxsplit=1)
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
    for p in string.punctuation:
        known = known.replace(p, ' ')
        unknown = unknown.replace(p, ' ')
    # Replaces whitespace with a single space.
    known = " ".join(known.split())
    unknown = " ".join(unknown.split())

    if unknown == known:
        return True
    else:
        return False


def get_csv_record_hash(row):
    """Concatenate values in the CSV record and get an MD5 hash on the
       resulting string.
    """
    serialized_row = ''
    for field in row:
        if isinstance(row[field], str) or isinstance(row[field], int):
            if isinstance(row[field], int):
                row[field] = str(row[field])
            row_value = row[field].strip()
            row_value = " ".join(row_value.split())
            serialized_row = serialized_row + row_value + " "

    serialized_row = bytes(serialized_row.strip().lower(), 'utf-8')
    hash_object = hashlib.md5(serialized_row)
    return hash_object.hexdigest()


def validate_input_dir(config):
    # Check existence input directory.
    if os.path.isabs(config['input_dir']):
        input_dir_path = config['input_dir']
    else:
        input_dir_path = os.path.abspath(config['input_dir'])
    if not os.path.exists(input_dir_path):
        message = 'Input directory specified in the "input_dir" configuration setting ("' + config['input_dir'] + '") not found.'
        logging.error(message)
        sys.exit('Error: ' + message)


def validate_csv_field_cardinality(config, field_definitions, csv_data):
    """Compare values in the CSV data with the fields' cardinality. Log CSV
       fields that have more values than allowed, and warn user if
       these fields exist in their CSV data.
    """
    field_cardinalities = dict()
    csv_headers = csv_data.fieldnames
    for csv_header in csv_headers:
        if csv_header in field_definitions.keys():
            cardinality = field_definitions[csv_header]['cardinality']
            # We don't care about cardinality of -1 (unlimited).
            if int(cardinality) > 0:
                field_cardinalities[csv_header] = cardinality

    for count, row in enumerate(csv_data, start=1):
        for field_name in field_cardinalities.keys():
            if field_name in row:
                # Don't check for the subdelimiter in title.
                if field_name == 'title':
                    continue
                delimited_field_values = row[field_name].split(config['subdelimiter'])
                if field_cardinalities[field_name] == 1 and len(delimited_field_values) > 1:
                    if config['task'] == 'create':
                        message = 'CSV field "' + field_name + '" in record with ID ' + row[config['id_field']] + ' contains more values than the number '
                    if config['task'] == 'update':
                        message = 'CSV field "' + field_name + '" in record with node ID ' + row['node_id'] + ' contains more values than the number '
                    message_2 = 'allowed for that field (' + str(field_cardinalities[field_name]) + '). Workbench will add only the first value.'
                    print('Warning: ' + message + message_2)
                    logging.warning(message + message_2)
                if int(field_cardinalities[field_name]) > 1 and len(delimited_field_values) > field_cardinalities[field_name]:
                    if config['task'] == 'create':
                        message = 'CSV field "' + field_name + '" in record with ID ' + row[config['id_field']] + ' contains more values than the number '
                    if config['task'] == 'update':
                        message = 'CSV field "' + field_name + '" in record with node ID ' + row['node_id'] + ' contains more values than the number '
                    message_2 = 'allowed for that field (' + str(field_cardinalities[field_name]) + '). Workbench will add only the first ' + str(
                        field_cardinalities[field_name]) + ' values.'
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
                # We don't care about max_length of None (i.e., it's
                # not applicable or unlimited).
                if max_length is not None:
                    field_max_lengths[csv_header] = max_length

    for count, row in enumerate(csv_data, start=1):
        for field_name in field_max_lengths.keys():
            if field_name in row:
                delimited_field_values = row[field_name].split(
                    config['subdelimiter'])
                for field_value in delimited_field_values:
                    field_value_length = len(field_value)
                    if field_name in field_max_lengths and len(field_value) > int(field_max_lengths[field_name]):
                        if config['task'] == 'create':
                            message = 'CSV field "' + field_name + '" in record with ID ' + \
                                row[config['id_field']] + ' contains a value that is longer (' + str(len(field_value)) + ' characters)'
                        if config['task'] == 'update':
                            message = 'CSV field "' + field_name + '" in record with node ID ' + \
                                row['node_id'] + ' contains a value that is longer (' + str(len(field_value)) + ' characters)'
                        message_2 = ' than allowed for that field (' + \
                            str(field_max_lengths[field_name]) + ' characters). Workbench will truncate this value prior to populating Drupal.'
                        print('Warning: ' + message + message_2)
                        logging.warning(message + message_2)


def validate_geolocation_fields(config, field_definitions, csv_data):
    """Validate lat,long values in fields that are of type 'geolocation'.
    """
    geolocation_fields_present = False
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if field_definitions[field_name]['field_type'] == 'geolocation':
                if field_name in row:
                    geolocation_fields_present = True
                    delimited_field_values = row[field_name].split(config['subdelimiter'])
                    for field_value in delimited_field_values:
                        if len(field_value.strip()):
                            if not validate_latlong_value(field_value.strip()):
                                message = 'Value in field "' + field_name + '" in row ' + str(count) + ' (' + field_value + ') is not a valid lat,long pair.'
                                logging.error(message)
                                sys.exit('Error: ' + message)

    if geolocation_fields_present is True:
        message = "OK, geolocation field values in the CSV file validate."
        print(message)
        logging.info(message)


def validate_link_fields(config, field_definitions, csv_data):
    """Validate values in fields that are of type 'link'.
    """
    link_fields_present = False
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if field_definitions[field_name]['field_type'] == 'link':
                if field_name in row:
                    link_fields_present = True
                    delimited_field_values = row[field_name].split(config['subdelimiter'])
                    for field_value in delimited_field_values:
                        if len(field_value.strip()):
                            if not validate_link_value(field_value.strip()):
                                message = 'Value in field "' + field_name + '" in row ' + str(count) + \
                                    ' (' + field_value + ') is not a valid link field value.'
                                logging.error(message)
                                sys.exit('Error: ' + message)

    if link_fields_present is True:
        message = "OK, link field values in the CSV file validate."
        print(message)
        logging.info(message)


def validate_latlong_value(latlong):
    # Remove leading \ that may be present if input CSV is from a spreadsheet.
    latlong = latlong.lstrip('\\')
    if re.match(r"^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$", latlong):
        return True
    else:
        return False


def validate_link_value(link_value):
    """Validates that the value in 'link_value' starts with either 'http://' or 'https://'
       and optionally contains the url/label delimiter '%%'.
    """
    """Parameters
        ----------
        link_value : string
            The URL.
        Returns
        -------
        boolean
            True if it does, False if not.
    """
    parts = link_value.split('%%', 1)
    if re.match(r"^https?://", parts[0]):
        return True
    else:
        return False


def validate_term_name_length(term_name, row_number, column_name):
    """Checks that the length of a term name does not exceed
       Drupal's 255 character length.
    """
    term_name = term_name.strip()
    if len(term_name) > 255:
        message = 'CSV field "' + column_name + '" in record ' + row_number + \
            " contains a taxonomy term that exceeds Drupal's limit of 255 characters (length of term is " + str(len(term_name)) + ' characters).'
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
                # matches = re.match(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$', field_value)
                if not validate_node_created_date_string(field_value):
                    message = 'CSV field "created" in record ' + \
                        str(count) + ' contains a date "' + field_value + '" that is not formatted properly.'
                    logging.error(message)
                    sys.exit('Error: ' + message)

                now = datetime.datetime.now()
                # Remove the GMT differential at the end of the time string.
                date_string_trimmed = re.sub(
                    r'[+-]\d\d:\d\d$', '', field_value)
                created_date = datetime.datetime.strptime(date_string_trimmed, '%Y-%m-%dT%H:%M:%S')
                if created_date > now:
                    message = 'CSV field "created" in record ' + \
                        str(count) + ' contains a date "' + field_value + '" that is in the future.'
                    logging.error(message)
                    sys.exit('Error: ' + message)

    message = 'OK, dates in the "created" CSV field are all formated correctly and in the future.'
    print(message)
    logging.info(message)


def validate_node_created_date_string(created_date_string):
    if re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$", created_date_string):
        return True
    else:
        return False


def validate_edtf_fields(config, field_definitions, csv_data):
    """Validate values in fields that are of type 'edtf'.
    """
    edtf_fields_present = False
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if field_definitions[field_name]['field_type'] == 'edtf':
                if field_name in row:
                    edtf_fields_present = True
                    delimited_field_values = row[field_name].split(config['subdelimiter'])
                    for field_value in delimited_field_values:
                        if len(field_value.strip()):
                            valid = validate_edtf_date(field_value)
                            if valid is False:
                                message = 'Value in field "' + field_name + '" in row ' + str(count) + ' ("' + field_value + '") is not a valid EDTF date/time.'
                                logging.error(message)
                                sys.exit('Error: ' + message)

    if edtf_fields_present is True:
        message = "OK, EDTF field values in the CSV file validate."
        print(message)
        logging.info(message)


def validate_edtf_date(date):
    valid = edtf_validate.valid_edtf.is_valid(date.strip())
    return valid


def validate_url_aliases(config, csv_data):
    """Checks that URL aliases don't already exist.
    """
    for count, row in enumerate(csv_data, start=1):
        for field_name, field_value in row.items():
            if field_name == 'url_alias' and len(field_value) > 0:
                if field_value.strip()[0] != '/':
                    message = 'CSV field "url_alias" in record ' + \
                        str(count) + ' contains an alias "' + field_value + '" that is missing its leading /.'
                    logging.error(message)
                    sys.exit('Error: ' + message)

                alias_ping = ping_url_alias(config, field_value)
                # @todo: Add 301 and 302 as acceptable status codes?
                if alias_ping == 200:
                    message = 'CSV field "url_alias" in record ' + \
                        str(count) + ' contains an alias "' + field_value + '" that already exists.'
                    logging.error(message)
                    sys.exit('Error: ' + message)

    message = 'OK, URL aliases do not already exist.'
    print(message)
    logging.info(message)


def validate_node_uid(config, csv_data):
    """Checks that the user identified in the 'uid' field exists in Drupal. Note that
       this does not validate any permissions the user may have.
    """
    for count, row in enumerate(csv_data, start=1):
        for field_name, field_value in row.items():
            if field_name == 'uid' and len(field_value) > 0:
                # Request to /user/x?_format=json goes here; 200 means the user
                # exists, 404 means they do no.
                uid_url = config['host'] + '/user/' + str(field_value) + '?_format=json'
                uid_response = issue_request(config, 'GET', uid_url)
                if uid_response.status_code == 404:
                    message = 'CSV field "uid" in record ' + \
                        str(count) + ' contains a user ID "' + field_value + '" that does not exist in the target Drupal.'
                    logging.error(message)
                    sys.exit('Error: ' + message)

    message = 'OK, user IDs in the "uid" CSV field all exist.'
    print(message)
    logging.info(message)


def validate_taxonomy_field_values(config, field_definitions, csv_data):
    """Loop through all fields in field_definitions, and if a field
       is a taxonomy reference field, validate all values in the CSV
       data in that field against term IDs in the taxonomies referenced
       by the field. Does not validate Typed Relation fields
       (see validate_typed_relation_field_values()).
    """
    # Define a dictionary to store CSV field: term IDs mappings.
    fields_with_vocabularies = dict()
    vocab_validation_issues = False
    # Get all the term IDs for vocabularies referenced in all fields in the CSV.
    for column_name in csv_data.fieldnames:
        if column_name in field_definitions:
            if field_definitions[column_name]['field_type'] == 'typed_relation':
                continue
            if 'vocabularies' in field_definitions[column_name]:
                vocabularies = get_field_vocabularies(config, field_definitions, column_name)
                # If there are no vocabularies linked to the current field, 'vocabularies'
                # will be False and will throw a TypeError.
                try:
                    num_vocabs = len(vocabularies)
                except BaseException:
                    message = 'Workbench cannot get vocabularies linked to field "' + \
                        column_name + '". Please confirm that field has at least one vocabulary.'
                    logging.error(message)
                    sys.exit('Error: ' + message)
                all_tids_for_field = []
                for vocabulary in vocabularies:
                    terms = get_term_pairs(config, vocabulary)
                    if len(terms) == 0:
                        if config['allow_adding_terms'] is True:
                            vocab_validation_issues = True
                            message = 'Vocabulary "' + vocabulary + '" referenced in CSV field "' + column_name + \
                                '" may not be enabled in the "Terms in vocabulary" View (please confirm it is) or may contains no terms.'
                            logging.warning(message)
                        else:
                            vocab_validation_issues = True
                            message = 'Vocabulary "' + vocabulary + '" referenced in CSV field "' + column_name + \
                                '" may not enabled in the "Terms in vocabulary" View (please confirm it is) or may contains no terms.'
                            logging.warning(message)
                    vocab_term_ids = list(terms.keys())
                    # If more than one vocab in this field, combine their term IDs into a single list.
                    all_tids_for_field = all_tids_for_field + vocab_term_ids
                fields_with_vocabularies.update({column_name: all_tids_for_field})

    # If none of the CSV fields are taxonomy reference fields, return.
    if len(fields_with_vocabularies) == 0:
        return

    # Iterate through the CSV and validate each taxonomy fields's values.
    new_term_names_in_csv_results = []
    for count, row in enumerate(csv_data, start=1):
        for column_name in fields_with_vocabularies:
            if len(row[column_name]):
                new_term_names_in_csv = validate_taxonomy_reference_value(config, field_definitions, fields_with_vocabularies, column_name, row[column_name], count)
                new_term_names_in_csv_results.append(new_term_names_in_csv)

    if True in new_term_names_in_csv_results and config['allow_adding_terms'] is True:
        print("OK, term IDs/names in CSV file exist in their respective taxonomies (and new terms will be created as noted in the Workbench log).")
    else:
        # All term IDs are in their field's vocabularies.
        print("OK, term IDs/names in CSV file exist in their respective taxonomies.")
        logging.info("OK, term IDs/names in CSV file exist in their respective taxonomies.")

    return vocab_validation_issues


def validate_vocabulary_fields_in_csv(config, vocabulary_id, vocab_csv_file_path):
    """Loop through all fields in CSV to ensure that all present fields match field
       from the vocab's field definitions, and that any required fields are present.
       Also checks that each row has the same number of columns are headers.
    """
    """Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        vocabulary_id : string
            The ID of the vocabulary to validate.
        vocab_csv_file_path: string
            Location of vocabulary CSV file.
    """
    csv_data = get_csv_data(config, 'taxonomy_fields', vocab_csv_file_path)
    csv_column_headers = copy.copy(csv_data.fieldnames)

    # Check whether each row contains the same number of columns as there are headers.
    for count, row in enumerate(csv_data, start=1):
        extra_headers = False
        field_count = 0
        for field in row:
            # 'stringtopopulateextrafields' is added by get_csv_data() if there are extra headers.
            if row[field] == 'stringtopopulateextrafields':
                extra_headers = True
            else:
                field_count += 1
        if extra_headers is True:
            message = "Row " + str(count) + ' (ID ' + row[config['id_field']] + ') of the vocabulary CSV file "' + \
                vocab_csv_file_path + '" has fewer columns than there are headers (' + str(len(csv_column_headers)) + ")."
            logging.error(message)
            sys.exit('Error: ' + message)
        # Note: this message is also generated in get_csv_data() since CSV Writer thows an exception if the row has
        # form fields than headers.
        if len(csv_column_headers) < field_count:
            message = "Row " + str(count) + " (ID " + row['term_name'] + ') of the vocabulary CSV file "' + vocab_csv_file_path + \
                '" has more columns (' + str(field_count) + ") than there are headers (" + str(len(csv_column_headers)) + ")."
            logging.error(message)
            sys.exit('Error: ' + message)
    message = "OK, all " \
        + str(count) + ' rows in the vocabulary CSV file "' + vocab_csv_file_path + '" have the same number of columns as there are headers (' \
        + str(len(csv_column_headers)) + ').'
    print(message)
    logging.info(message)

    # Check that the required 'term_name' and 'parent' columns are present in the CSV, and that
    # any fields defined as required in the vocabulary are also present.
    field_definitions = get_field_definitions(config, 'taxonomy_term', vocabulary_id.strip())
    for column_name in csv_column_headers:
        # Check that 'term_name' and 'parent' are in the CSV.
        if 'term_name' not in csv_column_headers:
            message = 'Required column "term_name" not found in vocabulary CSV file "' + vocab_csv_file_path + '".'
            logging.error(message)
            sys.exit('Error: ' + message)
        if 'parent' not in csv_column_headers:
            message = 'Required column "parent" not found in vocabulary CSV file "' + vocab_csv_file_path + '".'
            logging.error(message)
            sys.exit('Error: ' + message)
        # Then vocabulary fields that are defined as required.
        field_definition_fieldnames = field_definitions.keys()
        for field in field_definition_fieldnames:
            if field_definitions[field]['required'] is True and field not in csv_data.fieldnames:
                message = 'Required column "' + field + '" not found in vocabulary CSV file "' + vocab_csv_file_path + '".'
                logging.error(message)
                sys.exit('Error: ' + message)

    # Check whether remaining fields in the vocabulary CSV are fields defined in the current vocabulary.
    if 'field_name' in csv_column_headers:
        csv_column_headers.remove('field_name')
    if 'parent' in csv_fieldnames:
        csv_column_headers.remove('parent')
    for csv_field in csv_column_headers:
        if csv_field not in field_definitions.keys():
            message = 'CSV column "' + csv_field + '" in vocabulary CSV file "' + vocab_csv_file_path + '" is not a field in the "' + vocabulary_id + '" vocabulary.'
            logging.error(message)
            sys.exit('Error: ' + message)


def validate_typed_relation_field_values(config, field_definitions, csv_data):
    """Validate values in fields that are of type 'typed_relation'. Each CSV
       value must have this pattern: "string:string:int" or "string:string:string".
       If the last segment is a string, it must be term name, a namespaced term name,
       or an http URI.
    """
    # Define a dictionary to store CSV field: term IDs mappings.
    fields_with_vocabularies = dict()
    # Get all the term IDs for vocabularies referenced in all fields in the CSV.
    vocab_validation_issues = False
    for column_name in csv_data.fieldnames:
        if column_name in field_definitions:
            if 'vocabularies' in field_definitions[column_name]:
                vocabularies = get_field_vocabularies(config, field_definitions, column_name)
                # If there are no vocabularies linked to the current field, 'vocabularies'
                # will be False and will throw a TypeError.
                try:
                    num_vocabs = len(vocabularies)
                except BaseException:
                    message = 'Workbench cannot get vocabularies linked to field "' + \
                        column_name + '". Please confirm that field has at least one vocabulary.'
                    logging.error(message)
                    sys.exit('Error: ' + message)
                all_tids_for_field = []
                for vocabulary in vocabularies:
                    terms = get_term_pairs(config, vocabulary)
                    if len(terms) == 0:
                        if config['allow_adding_terms'] is True:
                            vocab_validation_issues = True
                            message = 'Vocabulary "' + vocabulary + '" referenced in CSV field "' + column_name + \
                                '" may not be enabled in the "Terms in vocabulary" View (please confirm it is) or may contains no terms.'
                            logging.warning(message)
                        else:
                            vocab_validation_issues = True
                            message = 'Vocabulary "' + vocabulary + '" referenced in CSV field "' + column_name + \
                                '" may not enabled in the "Terms in vocabulary" View (please confirm it is) or may contains no terms.'
                            logging.warning(message)
                    vocab_term_ids = list(terms.keys())
                    # If more than one vocab in this field, combine their term IDs into a single list.
                    all_tids_for_field = all_tids_for_field + vocab_term_ids
                fields_with_vocabularies.update({column_name: all_tids_for_field})

    # If none of the CSV fields are taxonomy reference fields, return.
    if len(fields_with_vocabularies) == 0:
        return

    typed_relation_fields_present = False
    new_term_names_in_csv_results = []
    for count, row in enumerate(csv_data, start=1):
        for field_name in field_definitions.keys():
            if field_definitions[field_name]['field_type'] == 'typed_relation' and 'typed_relations' in field_definitions[field_name]:
                if field_name in row:
                    typed_relation_fields_present = True
                    delimited_field_values = row[field_name].split(config['subdelimiter'])
                    for field_value in delimited_field_values:
                        if len(field_value) == 0:
                            continue
                        # First check the required patterns.
                        if not re.match("^[a-zA-Z]+:[a-zA-Z]+:.+$", field_value.strip()):
                            message = 'Value in field "' + field_name + '" in row ' + str(count) + \
                                ' (' + field_value + ') does not use the pattern required for typed relation fields.'
                            logging.error(message)
                            sys.exit('Error: ' + message)

                        # Then, check to see if the relator string (the first two parts of the
                        # value) exist in the field_definitions[fieldname]['typed_relations'] list.
                        typed_relation_value_parts = field_value.split(':', 2)
                        relator_string = typed_relation_value_parts[0] + ':' + typed_relation_value_parts[1]
                        if relator_string not in field_definitions[field_name]['typed_relations']:
                            message = 'Value in field "' + field_name + '" in row ' + str(count) + \
                                ' contains a relator (' + relator_string + ') that is not configured for that field.'
                            logging.error(message)
                            sys.exit('Error: ' + message)

                    # Iterate through the CSV and validate the taxonomy term/name/URI in each field subvalue.
                    for column_name in fields_with_vocabularies:
                        if len(row[column_name]):
                            delimited_field_values = row[column_name].split(config['subdelimiter'])
                            delimited_field_values_without_relator_strings = []
                            for field_value in delimited_field_values:
                                # Strip the relator string out from field_value, leaving the vocabulary ID and term ID/name/URI.
                                term_to_check = re.sub('^[a-zA-Z]+:[a-zA-Z]+:', '', field_value)
                                delimited_field_values_without_relator_strings.append(term_to_check)

                            field_value_to_check = config['subdelimiter'].join(delimited_field_values_without_relator_strings)
                            new_term_names_in_csv = validate_taxonomy_reference_value(config, field_definitions, fields_with_vocabularies, column_name, field_value_to_check, count)
                            new_term_names_in_csv_results.append(new_term_names_in_csv)

    if typed_relation_fields_present is True and True in new_term_names_in_csv_results and config['allow_adding_terms'] is True:
        print("OK, term IDs/names used in typed relation fields in the CSV file exist in their respective taxonomies (and new terms will be created as noted in the Workbench log).")
    else:
        if typed_relation_fields_present is True:
            # All term IDs are in their field's vocabularies.
            print("OK, term IDs/names used in typed relation fields in the CSV file exist in their respective taxonomies.")
            logging.info("OK, term IDs/names used in typed relation fields in the CSV file exist in their respective taxonomies.")

    return vocab_validation_issues


def validate_taxonomy_reference_value(config, field_definitions, fields_with_vocabularies, csv_field_name, csv_field_value, record_number):
    this_fields_vocabularies = get_field_vocabularies(config, field_definitions, csv_field_name)
    this_fields_vocabularies_string = ', '.join(this_fields_vocabularies)

    new_term_names_in_csv = False

    # Allow for multiple values in one field.
    terms_to_check = csv_field_value.split(config['subdelimiter'])
    for field_value in terms_to_check:
        # If this is a multi-taxonomy field, all term names must be namespaced
        # using the vocab_id:term_name pattern, regardless of whether
        # config['allow_adding_terms'] is True.
        if len(this_fields_vocabularies) > 1 and value_is_numeric(field_value) is not True and not field_value.startswith('http'):
            # URIs are unique so don't need namespacing.
            split_field_values = field_value.split(config['subdelimiter'])
            for split_field_value in split_field_values:
                namespaced = re.search(':', field_value)
                if namespaced:
                    # If the : is present, validate that the namespace is one of
                    # the vocabulary IDs referenced by this field.
                    field_value_parts = field_value.split(':')
                    if field_value_parts[0] not in this_fields_vocabularies:
                        message = 'Vocabulary ID ' + field_value_parts[0] + \
                            ' used in CSV column "' + csv_field_name + '", row ' + str(record_number) + \
                            ' does not match any of the vocabularies referenced by the' + \
                            ' corresponding Drupal field (' + this_fields_vocabularies_string + ').'
                        logging.error(message)
                        sys.exit('Error: ' + message)
                else:
                    message = 'Term names in multi-vocabulary CSV field "' + \
                        csv_field_name + '" require a vocabulary namespace; value '
                    message_2 = '"' + field_value + '" in row ' \
                        + str(record_number) + ' does not have one.'
                    logging.error(message + message_2)
                    sys.exit('Error: ' + message + message_2)

                validate_term_name_length(split_field_value, str(record_number), csv_field_name)

        # Check to see if field_value is a member of the field's vocabularies. First,
        # check whether field_value is a term ID.
        if value_is_numeric(field_value):
            field_value = field_value.strip()
            if int(field_value) not in fields_with_vocabularies[csv_field_name]:
                message = 'CSV field "' + csv_field_name + '" in row ' + \
                    str(record_number) + ' contains a term ID (' + field_value + ') that is '
                if len(this_fields_vocabularies) > 1:
                    message_2 = 'not in one of the referenced vocabularies (' + \
                        this_fields_vocabularies_string + ').'
                else:
                    message_2 = 'not in the referenced vocabulary ("' + \
                        this_fields_vocabularies[0] + '").'
                logging.error(message + message_2)
                sys.exit('Error: ' + message + message_2)
        # Then check values that are URIs.
        elif field_value.startswith('http'):
            tid_from_uri = get_term_id_from_uri(config, field_value)
            if value_is_numeric(tid_from_uri):
                if tid_from_uri not in fields_with_vocabularies[csv_field_name]:
                    message = 'CSV field "' + csv_field_name + '" in row ' + \
                        str(record_number) + ' contains a term URI (' + field_value + ') that is '
                    if len(this_fields_vocabularies) > 1:
                        message_2 = 'not in one of the referenced vocabularies (' \
                            + this_fields_vocabularies_string + ').'
                    else:
                        message_2 = 'not in the referenced vocabulary ("' \
                            + this_fields_vocabularies[0] + '").'
                    logging.error(message + message_2)
                    sys.exit('Error: ' + message + message_2)
            else:
                message = 'Term URI "' + field_value + '" used in CSV column "' + \
                    csv_field_name + '" row ' + str(record_number) + ' does not match any terms.'
                logging.error(message)
                sys.exit('Error: ' + message)
        # Finally, check values that are string term names.
        else:
            new_terms_to_add = []
            for vocabulary in this_fields_vocabularies:
                tid = find_term_in_vocab(config, vocabulary, field_value)
                if value_is_numeric(tid) is not True:
                    # Single taxonomy fields.
                    if len(this_fields_vocabularies) == 1:
                        if config['allow_adding_terms'] is True:
                            # Warn if namespaced term name is not in specified vocab.
                            if tid is False:
                                new_term_names_in_csv = True
                                validate_term_name_length(field_value, str(record_number), csv_field_name)
                                message = 'CSV field "' + csv_field_name + '" in row ' + \
                                    str(record_number) + ' contains a term ("' + field_value.strip() + '") that is '
                                message_2 = 'not in the referenced vocabulary ("' + \
                                    this_fields_vocabularies[0] + '"). That term will be created.'
                                logging.warning(message + message_2)
                        else:
                            new_term_names_in_csv = True
                            message = 'CSV field "' + csv_field_name + '" in row ' + \
                                str(record_number) + ' contains a term ("' + field_value.strip() + '") that is '
                            message_2 = 'not in the referenced vocabulary ("' + this_fields_vocabularies[0] + '").'
                            logging.error(message + message_2)
                            sys.exit('Error: ' + message + message_2)

                # If this is a multi-taxonomy field, all term names must be namespaced using
                # the vocab_id:term_name pattern, regardless of whether
                # config['allow_adding_terms'] is True.
                if len(this_fields_vocabularies) > 1:
                    split_field_values = field_value.split(config['subdelimiter'])
                    for split_field_value in split_field_values:
                        # Check to see if the namespaced vocab is referenced by this field.
                        [namespace_vocab_id, namespaced_term_name] = split_field_value.split(':', 1)
                        if namespace_vocab_id not in this_fields_vocabularies:
                            message = 'CSV field "' + csv_field_name + '" in row ' + \
                                str(record_number) + ' contains a namespaced term name '
                            message_2 = '(' + namespaced_term_name.strip() + '") that specifies a vocabulary not associated with that field.'
                            logging.error(message + message_2)
                            sys.exit('Error: ' + message + message_2)

                        tid = find_term_in_vocab(config, namespace_vocab_id, namespaced_term_name)

                        # Warn if namespaced term name is not in specified vocab.
                        if config['allow_adding_terms'] is True:
                            if tid is False and split_field_value not in new_terms_to_add:
                                new_term_names_in_csv = True
                                message = 'CSV field "' + csv_field_name + '" in row ' + \
                                    str(record_number) + ' contains a term ("' + namespaced_term_name.strip() + '") that is '
                                message_2 = 'not in the referenced vocabulary ("' + \
                                    namespace_vocab_id + '"). That term will be created.'
                                logging.warning(message + message_2)
                                new_terms_to_add.append(split_field_value)

                                validate_term_name_length(split_field_value, str(record_number), csv_field_name)
                        # Die if namespaced term name is not specified vocab.
                        else:
                            if tid is False:
                                message = 'CSV field "' + csv_field_name + '" in row ' + \
                                    str(record_number) + ' contains a term ("' + namespaced_term_name.strip() + '") that is '
                                message_2 = 'not in the referenced vocabulary ("' + \
                                    namespace_vocab_id + '").'
                                logging.warning(message + message_2)
                                sys.exit('Error: ' + message + message_2)

    return new_term_names_in_csv


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
    fields_to_remove = [
        'nid',
        'vid',
        'created',
        'changed',
        'langcode',
        'default_langcode',
        'uid',
        'type',
        'revision_timestamp',
        'revision_translation_affected',
        'revision_uid',
        'revision_log',
        'content_translation_source',
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
    drupal_8 = set_drupal_8(config)
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
            'field_member_of': [
                {'target_id': parent_node_id,
                 'target_type': 'node'}
            ],
            'field_weight': [
                {'value': weight}
            ]
        }

        # Add field_model if that field exists in the child's content type.
        entity_fields = get_entity_fields(config, 'node', config['paged_content_page_content_type'])
        if 'field_model' in entity_fields:
            node_json['field_model'] = [{'target_id': config['paged_content_page_model_tid'], 'target_type': 'taxonomy_term'}]

        if 'field_display_hints' in parent_csv_record:
            node_json['field_display_hints'] = [{'target_id': parent_csv_record['field_display_hints'], 'target_type': 'taxonomy_term'}]

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
        node_response = issue_request(
            config,
            'POST',
            node_endpoint,
            node_headers,
            node_json,
            None)
        if node_response.status_code == 201:
            node_uri = node_response.headers['location']
            print('+ Node for child "' + page_title + '" created at ' + node_uri + '.')
            logging.info('Node for child "%s" created at %s.', page_title, node_uri)
            if 'output_csv' in config.keys():
                write_to_output_csv(config, page_identifier, node_response.text)

            node_nid = node_uri.rsplit('/', 1)[-1]
            write_rollback_node_id(config, node_nid)

            page_file_path = os.path.join(parent_id, page_file_name)
            fake_csv_record = collections.OrderedDict()
            fake_csv_record['title'] = page_title
            fake_csv_record['file'] = page_file_path
            if drupal_8 is True:
                media_response_status_code = create_islandora_media(config, page_file_path, 'file', node_uri, fake_csv_record)
            else:
                media_response_status_code = create_media(config, page_file_path, 'file', node_nid, fake_csv_record)
            allowed_media_response_codes = [201, 204]
            if media_response_status_code in allowed_media_response_codes:
                if media_response_status_code is False:
                    logging.info("Media for %s not created.", page_file_path)
                    continue
                else:
                    logging.info("Media for %s created.", page_file_path)
        else:
            logging.warning('Node for page "%s" not created, HTTP response code was %s.', page_identifier, node_response.status_code)

        # Execute node-specific post-create scripts, if any are configured.
        if 'node_post_create' in config and len(config['node_post_create']) > 0:
            for command in config['node_post_create']:
                post_task_output, post_task_return_code = execute_entity_post_task_script(command, args.config, node_response.status_code, node_response.text)
                if post_task_return_code == 0:
                    logging.info("Post node create script " + command + " executed successfully.")
                else:
                    logging.error("Post node create script " + command + " failed.")


def write_rollback_config(config):
    path_to_rollback_config_file = os.path.join('rollback.yml')
    rollback_config_file = open(path_to_rollback_config_file, "w")
    yaml.dump(
        {'task': 'delete',
            'host': config['host'],
            'username': config['username'],
            'password': config['password'],
            'input_dir': config['input_dir'],
            'input_csv': 'rollback.csv'},
        rollback_config_file)


def prep_rollback_csv(config):
    path_to_rollback_csv_file = os.path.join(
        config['input_dir'], 'rollback.csv')
    if os.path.exists(path_to_rollback_csv_file):
        os.remove(path_to_rollback_csv_file)
    rollback_csv_file = open(path_to_rollback_csv_file, "a+")
    rollback_csv_file.write("node_id" + "\n")
    rollback_csv_file.close()


def write_rollback_node_id(config, node_id):
    path_to_rollback_csv_file = os.path.join(config['input_dir'], 'rollback.csv')
    rollback_csv_file = open(path_to_rollback_csv_file, "a+")
    rollback_csv_file.write(node_id + "\n")
    rollback_csv_file.close()


def get_csv_from_google_sheet(config):
    url_parts = config['input_csv'].split('/')
    url_parts[6] = 'export?gid=' + str(config['google_sheets_gid']) + '&format=csv'
    csv_url = '/'.join(url_parts)
    response = requests.get(url=csv_url, allow_redirects=True)

    if response.status_code == 404:
        message = 'Workbench cannot find the Google spreadsheet at ' + config['input_csv'] + '. Please check the URL.'
        logging.error(message)
        sys.exit('Error: ' + message)

    # Sheets that aren't publicly readable return a 302 and then a 200 with a bunch of HTML for humans to look at.
    if response.content.strip().startswith(b'<!DOCTYPE'):
        message = 'The Google spreadsheet at ' + config['input_csv'] + ' is not accessible.\nPlease check its "Share" settings.'
        logging.error(message)
        sys.exit('Error: ' + message)

    input_csv_path = os.path.join(config['input_dir'], config['google_sheets_csv_filename'])
    open(input_csv_path, 'wb+').write(response.content)


def get_csv_from_excel(config):
    """Read the input Excel 2010 (or later) file and write it out as CSV.
    """
    if os.path.isabs(config['input_csv']):
        input_excel_path = config['input_csv']
    else:
        input_excel_path = os.path.join(config['input_dir'], config['input_csv'])

    if not os.path.exists(input_excel_path):
        message = 'Error: Excel file ' + input_excel_path + ' not found.'
        logging.error(message)
        sys.exit(message)

    excel_file_path = config['input_csv']
    wb = openpyxl.load_workbook(filename=input_excel_path)
    ws = wb[config['excel_worksheet']]

    headers = []
    header_row = ws[1]
    ws.delete_rows(0)
    for header_cell in header_row:
        headers.append(header_cell.value)

    records = []
    for row in ws:
        record = {}
        for x in range(len(header_row)):
            if headers[x] is not None and row[x] is not None:
                record[headers[x]] = row[x].value
        records.append(record)

    input_csv_path = os.path.join(config['input_dir'], config['excel_csv_filename'])
    csv_writer_file_handle = open(input_csv_path, 'w+', newline='')
    csv_writer = csv.DictWriter(csv_writer_file_handle, fieldnames=headers)
    csv_writer.writeheader()
    for record in records:
        if (config['id_field'] in record or 'node_id' in record) and record[config['id_field']] is not None:
            csv_writer.writerow(record)
    csv_writer_file_handle.close()


def get_extension_from_mimetype(mimetype):
    # mimetypes.add_type() is not working, e.g. mimetypes.add_type('image/jpeg', '.jpg')
    # Maybe related to https://bugs.python.org/issue4963? In the meantime, provide our own
    # MIMETYPE to extension mapping for common types, then let mimetypes guess at others.
    map = {'image/jpeg': '.jpg',
           'image/jp2': '.jp2',
           'image/png': '.png',
           'audio/mpeg': '.mp3',
           'text/plain': '.txt',
           'application/octet-stream': '.bin'
           }
    if mimetype in map:
        return map[mimetype]
    else:
        return mimetypes.guess_extension(mimetype)


def get_deduped_file_path(path):
    """Given a file path, return a version of it that contains a version of
       the same name with an incremented integer inserted before the extension.
    """
    """Parameters
        ----------
        path : string
            The file path we want to dedupe.
        Returns
        -------
        string
            The deduped version of 'path', i.e., the original path with an
            underscore and an incremented digit inserted before the extension.
    """
    [base_path, extension] = os.path.splitext(path)

    numbers = re.findall(r"_\d+$", base_path)
    if len(numbers) == 0:
        incremented_path = base_path + '_1' + extension
    else:
        number = int(numbers[0].lstrip('_')) + 1
        base_path_parts = base_path.split('_')
        del base_path_parts[-1]
        incremented_path = '_'.join(base_path_parts) + '_' + str(number) + extension

    return incremented_path


def check_file_exists(config, filename):
    """Cconfirms file exists and is a file (not a directory).
       For remote/downloaded files, checks for a 200 response from a HEAD request.
    """
    """Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        filename: string
            The filename.
        Returns
        -------
        boolean
            True if the file exists, false if not.
    """
    # It's a remote file.
    if filename.startswith('http'):
        try:
            head_response = requests.head(filename, allow_redirects=True, verify=config['secure_ssl_only'])
            if head_response.status_code == 200:
                return True
            else:
                return False
        except requests.exceptions.Timeout as err_timeout:
            message = 'Workbench timed out trying to reach ' + filename + '. Details in next log entry.'
            logging.error(message)
            logging.error(err_timeout)
            return False
        except requests.exceptions.ConnectionError as error_connection:
            message = 'Workbench cannot connect to ' + filename + '. Details in next log entry.'
            logging.error(message)
            logging.error(error_connection)
            return False
    # It's a local file.
    else:
        if os.path.isabs(filename):
            file_path = filename
        else:
            file_path = os.path.join(config['input_dir'], filename)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            return True


def get_prepocessed_file_path(config, file_fieldname, node_csv_row):
    """For remote/downloaded files, generates the path to the local temporary
       copy and returns that path. For local files, just returns the value of
       node_csv_row['file'].
    """
    """Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        file_fieldname: string
            The name of the CSV column containing the filename.
        node_csv_row : OrderedDict
            The CSV row for the current item.
        Returns
        -------
        string
            The path (absolute or relative) to the file.
    """
    file_path_from_csv = node_csv_row[file_fieldname].strip()
    if config['task'] == 'add_media':
        config['id_field'] = 'node_id'

    # It's a remote file.
    if file_path_from_csv.startswith('http'):
        sections = urllib.parse.urlparse(file_path_from_csv)
        if config['task'] == 'add_media':
            subdir = os.path.join(config['input_dir'], re.sub('[^A-Za-z0-9]+', '_', 'nid_' + str(node_csv_row['node_id'])))
        else:
            subdir = os.path.join(config['input_dir'], re.sub('[^A-Za-z0-9]+', '_', node_csv_row[config['id_field']]))
        Path(subdir).mkdir(parents=True, exist_ok=True)

        if config["use_node_title_for_media"]:
            # CSVs for add_media tasks don't contain 'title', so we need to get it.
            if config['task'] == 'add_media':
                node_id = node_csv_row['node_id']
                node_url = config['host'] + '/node/' + node_id + '?_format=json'
                node_response = issue_request(config, 'GET', node_url)
                if node_response.status_code == 200:
                    node_dict = json.loads(node_response.text)
                    node_csv_row['title'] = node_dict['title'][0]['value']
                else:
                    message = 'Cannot access node " + node_id + ", so cannot get its title for use in media filename. Using filename instead.'
                    logging.warning(message)
                    node_csv_row['title'] = os.path.basename(node_csv_row[file_fieldname].strip())
            filename = re.sub(r'\s+', '_', node_csv_row['title'])
            filename = re.sub('[^A-Za-z0-9]+', '_', filename)
            if filename[-1] == '_':
                filename = filename[:-1]
            downloaded_file_path = os.path.join(subdir, filename)
            extension = os.path.splitext(downloaded_file_path)[1]
        else:
            extension = os.path.splitext(sections.path)[1]
            filename = sections.path.split("/")[-1]
            downloaded_file_path = os.path.join(subdir, filename)

        if extension == '':
            try:
                head_response = requests.head(file_path_from_csv, allow_redirects=True, verify=config['secure_ssl_only'])
                mimetype = head_response.headers['content-type']
                # In case servers return stuff beside the MIME type in Content-Type header.
                # Assumes they use ; to separate stuff and that what we're looking for is
                # in the first position.
                if ';' in mimetype:
                    mimetype_parts = mimetype.split(';')
                    mimetype = mimetype_parts[0].strip()
            except KeyError:
                mimetype = 'application/octet-stream'

            extension_with_dot = get_extension_from_mimetype(mimetype)
            downloaded_file_path = os.path.join(subdir, filename + extension_with_dot)

            # Check to see if a file with this path already exists; if so, insert an
            # incremented digit into the file path before the extension.
            if os.path.exists(downloaded_file_path):
                downloaded_file_path = get_deduped_file_path(downloaded_file_path)

        return downloaded_file_path
    # It's a local file.
    else:
        if os.path.isabs(file_path_from_csv):
            file_path = file_path_from_csv
        else:
            file_path = os.path.join(config['input_dir'], file_path_from_csv)
        return file_path


def download_remote_file(config, url, file_fieldname, node_csv_row):
    sections = urllib.parse.urlparse(url)
    try:
        response = requests.get(url, allow_redirects=True, verify=config['secure_ssl_only'])
    except requests.exceptions.Timeout as err_timeout:
        message = 'Workbench timed out trying to reach ' + \
            sections.netloc + ' while connecting to ' + url + '. Please verify that URL and check your network connection.'
        logging.error(message)
        logging.error(err_timeout)
        print('Error: ' + message)
        return False
    except requests.exceptions.ConnectionError as error_connection:
        message = 'Workbench cannot connect to ' + \
            sections.netloc + ' while connecting to ' + url + '. Please verify that URL and check your network connection.'
        logging.error(message)
        logging.error(error_connection)
        print('Error: ' + message)
        return False

    downloaded_file_path = get_prepocessed_file_path(config, file_fieldname, node_csv_row)

    f = open(downloaded_file_path, 'wb+')
    f.write(response.content)
    f.close

    return downloaded_file_path


def get_file_hash_from_drupal(config, file_uuid, algorithm):
    """Query the Integration module's hash controller at '/islandora_workbench_integration/file_hash'
       to get the hash of the file identified by file_uuid.
    """
    """Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        file_uuid : string
            The file's UUID.
        algorithm : string
            One of 'md5', 'sha1', or 'sha256'
        Returns
        -------
        string
            The requested hash.
    """
    url = config['host'] + '/islandora_workbench_integration/file_hash?file_uuid=' + file_uuid + '&algorithm=' + algorithm
    response = issue_request(config, 'GET', url)
    if response.status_code == 200:
        response_body = json.loads(response.text)
        return response_body[0]['checksum']
    else:
        logging.warning("Request to get %s hash for file %s returned a %s status code", algorithm, file_uuid, response.status_code)
        return False


def get_file_hash_from_local(config, file_path, algorithm):
    """Get the file's hash/checksum.
    """
    """Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        file_path : string
            The file's path.
        algorithm : string
            One of 'md5', 'sha1', or 'sha256'
        Returns
        -------
        string
            The requested hash.
    """
    if algorithm == 'md5':
        hash_object = hashlib.md5()
    if algorithm == 'sha1':
        hash_object = hashlib.sha1()
    if algorithm == 'sha256':
        hash_object = hashlib.sha256()

    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(hash_object.block_size)
            if not chunk:
                break
            hash_object.update(chunk)

    return hash_object.hexdigest()


def check_csv_file_exists(config, csv_file_target, file_path=None):
    """Confirms a CSV file exists.
    """
    """Parameters
        ----------
        config : dict
            The configuration object defined by set_config_defaults().
        csv_file_target: string
            Either 'node_fields' or 'taxonomy_fields'.
        file_path: string
            The path to the file to check (applies only to vocabulary CSVs).
        Returns
        -------
        string
            The absolute file path to the CSV file.
    """
    if csv_file_target == 'node_fields':
        if os.path.isabs(config['input_csv']):
            input_csv = config['input_csv']
        # For Google Sheets, the "extraction" is fired over in workbench.
        elif config['input_csv'].startswith('http'):
            input_csv = os.path.join(config['input_dir'], config['google_sheets_csv_filename'])
            message = "Extracting CSV data from " + config['input_csv'] + " (worksheet gid " + str(config['google_sheets_gid']) + ") to " + input_csv + '.'
            print(message)
            logging.info(message)
        elif config['input_csv'].endswith('xlsx'):
            input_csv = os.path.join(config['input_dir'], config['excel_csv_filename'])
            message = "Extracting CSV data from " + config['input_csv'] + " to " + input_csv + '.'
            print(message)
            logging.info(message)
        else:
            input_csv = os.path.join(config['input_dir'], config['input_csv'])

        if os.path.exists(input_csv):
            message = 'OK, CSV file ' + input_csv + ' found.'
            print(message)
            logging.info(message)
            return input_csv
        else:
            message = 'CSV file ' + input_csv + ' not found.'
            logging.error(message)
            sys.exit('Error: ' + message)
    if csv_file_target == 'taxonomy_fields':
        if os.path.isabs(file_path):
            input_csv = file_path
            '''
            <- because python
            # For Google Sheets, the "extraction" is fired over in workbench.
            elif config['input_csv'].startswith('http'):
                input_csv = os.path.join(config['input_dir'], config['google_sheets_csv_filename'])
                message = "Extracting CSV data from " + config['input_csv'] + " (worksheet gid " + str(config['google_sheets_gid']) + ") to " + input_csv + '.'
                print(message)
                logging.info(message)
            elif config['input_csv'].endswith('xlsx'):
                input_csv = os.path.join(config['input_dir'], config['excel_csv_filename'])
                message = "Extracting CSV data from " + config['input_csv'] + " to " + input_csv + '.'
                print(message)
                logging.info(message)
            '''
        else:
            input_csv = os.path.join(config['input_dir'], file_path)

        if os.path.exists(input_csv):
            message = 'OK, vocabulary CSV file ' + input_csv + ' found.'
            print(message)
            logging.info(message)
            return input_csv
        else:
            message = 'Vocabulary CSV file ' + input_csv + ' not found.'
            logging.error(message)
            sys.exit('Error: ' + message)


def get_csv_template(config, args):
    field_definitions = get_field_definitions(config, 'node')

    field_labels = collections.OrderedDict()
    field_labels['REMOVE THIS COLUMN (KEEP THIS ROW)'] = 'LABEL (REMOVE THIS ROW)'
    for field_name in field_definitions:
        if field_definitions[field_name]['label'] != '':
            field_labels[field_name] = field_definitions[field_name]['label']
        else:
            field_labels[field_name] = ''

    required = collections.OrderedDict()
    required['REMOVE THIS COLUMN (KEEP THIS ROW)'] = 'REQUIRED IN CREATE TASKS (REMOVE THIS ROW)'
    for field_name in field_definitions:
        if field_definitions[field_name]['required'] != '':
            if field_definitions[field_name]['required'] is True:
                required[field_name] = 'Yes'
            else:
                required[field_name] = 'No'
    required['title'] = 'Yes'
    required['uid'] = 'No'
    required['langcode'] = 'No'
    required['created'] = 'No'
    required[config['id_field']] = 'Yes'
    if config['nodes_only'] is True:
        required['file'] = 'Yes'
    else:
        required['file'] = 'No'

    mapping = dict()
    mapping['string'] = 'Free text'
    mapping['string_long'] = 'Free text'
    mapping['text'] = 'Free text'
    mapping['text_long'] = 'Free text'
    mapping['geolocation'] = '+49.16,-123.93'
    mapping['entity_reference'] = '100 [or term name or http://foo.com/someuri]'
    mapping['edtf'] = '2020-10-28'
    mapping['typed_relation'] = 'relators:art:30'
    mapping['integer'] = 100

    sample_data = collections.OrderedDict()
    sample_data['REMOVE THIS COLUMN (KEEP THIS ROW)'] = 'SAMPLE DATA (REMOVE THIS ROW)'
    sample_data[config['id_field']] = '0001'
    sample_data['file'] = 'myimage.jpg'
    sample_data['uid'] = '21'
    sample_data['langcode'] = 'fr'
    sample_data['created'] = '2020-11-15T23:49:22+00:00'
    sample_data['title'] = 'Free text'

    for field_name in field_definitions:
        if field_definitions[field_name]['field_type'] in mapping:
            sample_data[field_name] = mapping[field_definitions[field_name]['field_type']]
        else:
            sample_data[field_name] = ''

    csv_file_path = os.path.join(config['input_dir'], config['input_csv'] + '.csv_file_template')
    csv_file = open(csv_file_path, 'a+')
    writer = csv.DictWriter(csv_file, fieldnames=sample_data.keys(), lineterminator="\n")
    writer.writeheader()
    # We want the labels and required rows to appear as the second and third rows so
    # add them before we add the sample data.
    writer.writerow(field_labels)
    writer.writerow(required)
    writer.writerow(sample_data)

    cardinality = collections.OrderedDict()
    cardinality['REMOVE THIS COLUMN (KEEP THIS ROW)'] = 'NUMBER OF VALUES ALLOWED (REMOVE THIS ROW)'
    cardinality[config['id_field']] = '1'
    cardinality['file'] = '1'
    cardinality['uid'] = '1'
    cardinality['langcode'] = '1'
    cardinality['created'] = '1'
    cardinality['title'] = '1'
    for field_name in field_definitions:
        if field_definitions[field_name]['cardinality'] == -1:
            cardinality[field_name] = 'unlimited'
        else:
            cardinality[field_name] = field_definitions[field_name]['cardinality']
    writer.writerow(cardinality)

    docs = dict()
    docs['string'] = 'Single-valued fields'
    docs['string_long'] = 'Single-valued fields'
    docs['text'] = 'Single-valued fields'
    docs['text_long'] = 'Single-valued fields'
    docs['geolocation'] = 'Geolocation fields'
    docs['entity_reference'] = 'Taxonomy reference fields'
    docs['edtf'] = 'EDTF fields'
    docs['typed_relation'] = 'Typed Relation fields'
    docs['integer'] = 'Single-valued fields'

    docs_tips = collections.OrderedDict()
    docs_tips['REMOVE THIS COLUMN (KEEP THIS ROW)'] = 'SECTION IN DOCUMENTATION (REMOVE THIS ROW)'
    docs_tips[config['id_field']] = 'Required fields'
    docs_tips['file'] = 'Required fields'
    docs_tips['uid'] = 'Base fields'
    docs_tips['langcode'] = 'Base fields'
    docs_tips['created'] = 'Base fields'
    docs_tips['title'] = 'Base fields'
    for field_name in field_definitions:
        if field_definitions[field_name]['field_type'] in docs:
            doc_reference = docs[field_definitions[field_name]['field_type']]
            docs_tips[field_name] = doc_reference
        else:
            docs_tips[field_name] = ''
    docs_tips['field_member_of'] = ''
    writer.writerow(docs_tips)

    csv_file.close()
    print('CSV template saved at ' + csv_file_path + '.')
    sys.exit()


def prep_node_ids_tsv(config):
    path_to_tsv_file = os.path.join(config['input_dir'], config['secondary_tasks_data_file'])
    if os.path.exists(path_to_tsv_file):
        os.remove(path_to_tsv_file)
    if len(config['secondary_tasks']) > 0:
        tsv_file = open(path_to_tsv_file, "a+")
    else:
        return False

    # Write to the data file the names of config files identified in config['secondary_tasks']
    # since we need a way to ensure that only tasks whose names are registered there should
    # populate their objects' 'field_member_of'.
    for secondary_config_file in config['secondary_tasks']:
        tsv_file.write(secondary_config_file + "\t" + '' + "\n")
    tsv_file.close()


def write_to_node_ids_tsv(config, row_id, node_id):
    path_to_tsv_file = os.path.join(config['input_dir'], config['secondary_tasks_data_file'])
    tsv_file = open(path_to_tsv_file, "a+")
    tsv_file.write(str(row_id) + "\t" + str(node_id) + "\n")
    tsv_file.close()


def read_node_ids_tsv(config):
    map = dict()
    path_to_tsv_file = os.path.join(config['input_dir'], config['secondary_tasks_data_file'])
    if config['secondary_tasks'] is not None:
        if not os.path.exists(path_to_tsv_file):
            message = 'Secondary task data file ' + path_to_tsv_file + ' not found.'
            print('Error: ' + message)
            logging.error(message)
            return map
            sys.exit()

    if os.path.exists(path_to_tsv_file):
        map_file = open(path_to_tsv_file, "r")
        entries = map_file.read().splitlines()
        for entry in entries:
            parts = entry.split("\t")
            map[parts[0]] = parts[1]

    return map


def get_percentage(part, whole):
    return 100 * float(part) / float(whole)


def is_ascii(input):
    """Check if a string contains only ASCII characters.
    """
    """Parameters
        ----------
        input : str
            The string to test.
        Returns
        -------
        string
            True if all characters are within the ASCII character set,
            False otherwise.
    """
    return all(ord(c) < 128 for c in input)
