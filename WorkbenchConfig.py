# Class to encapsulate Workbench config

import logging
from ruamel.yaml import YAML
import os
import sys
from workbench_utils import *


class WorkbenchConfig:
    def __init__(self, args):
        self.args = args
        self.path_check()
        self.config = self.get_config()
        self.validate()
        logging.basicConfig(
            filename=self.config['log_file_path'],
            level=logging.INFO,
            filemode='a',
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%d-%b-%y %H:%M:%S')

    # Get fully constructed config dictionary
    def get_config(self):
        config = self.get_default_config()
        user_mods = self.get_user_config()
        # Blend defaults with user mods
        for key, value in user_mods.items():
            config[key] = value
        # Modify some conditional values
        if 'paged_content_page_content_type' not in user_mods:
            config['paged_content_page_content_type'] = config['content_type']
        if 'id' not in user_mods and config['task'] == 'add_media':
            config['id'] = 'node_id'
        # Add preprocessor, if specified.
        if 'preprocessors' in user_mods:
            config['preprocessors'] = {}
            for preprocessor in user_mods['preprocessors']:
                for key, value in preprocessor.items():
                    config['preprocessors'][key] = value

        return config

    # Get user input as dictionary
    def get_user_config(self):
        yaml = YAML()
        with open(self.args.config, 'r') as stream:
            try:
                loaded = yaml.load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        if 'media_file_fields' in loaded:
            media_fields = self.get_media_fields()
            for media_field in loaded['media_file_fields']:
                for media_type, media_field in media_field.items():
                    media_fields[media_type] = media_field
            loaded['media_fields'] = media_fields
        if os.path.isabs(self.args.config):
            loaded['config_file_path'] = self.args.config
        else:
            loaded['config_file_path'] = os.path.join(os.getcwd(), self.args.config)
        return loaded

    def get_media_fields(self):
        return dict({
            'file': 'field_media_file',
            'document': 'field_media_document',
            'image': 'field_media_image',
            'audio': 'field_media_audio_file',
            'video': 'field_media_video_file',
            'extracted_text': 'field_media_file',
            'fits_technical_metadata': 'field_media_file'
        })

    def get_media_types(self):
        return [
            {'image': ['png', 'gif', 'jpg', 'jpeg']},
            {'document': ['pdf', 'doc', 'docx', 'ppt', 'pptx']},
            {'file': ['tif', 'tiff', 'jp2', 'zip', 'tar']},
            {'audio': ['mp3', 'wav', 'aac']},
            {'video': ['mp4']},
            {'extracted_text': ['txt']}
        ]

    def get_default_config(self):
        return {
            'input_dir': 'input_data',
            'input_csv': 'metadata.csv',
            'media_use_tid': 'http://pcdm.org/use#OriginalFile',
            'drupal_filesystem': 'fedora://',
            'id_field': 'id',
            'content_type': 'islandora_object',
            'delimiter': ',',
            'subdelimiter': '|',
            'log_file_path': 'workbench.log',
            'log_file_mode': 'a',
            'allow_missing_files': False,
            'update_mode': 'replace',
            'validate_title_length': True,
            'paged_content_from_directories': False,
            'delete_media_with_nodes': True,
            'allow_adding_terms': False,
            'nodes_only': False,
            'log_request_url': False,
            'log_json': False,
            'log_response_body': False,
            'log_response_status_code': False,
            'log_headers': False,
            'progress_bar': False,
            'user_agent': 'Islandora Workbench',
            'allow_redirects': True,
            'secure_ssl_only': True,
            'google_sheets_csv_filename': 'google_sheet.csv',
            'google_sheets_gid': '0',
            'excel_worksheet': 'Sheet1',
            'excel_csv_filename': 'excel.csv',
            'ignore_csv_columns': list(),
            'use_node_title_for_media': False,
            'use_node_title_for_media_title': True,
            'delete_tmp_upload': False,
            'list_missing_drupal_fields': False,
            'secondary_tasks': None,
            'secondary_tasks_data_file': 'id_to_node_map.tsv',
            'fixity_algorithm': None,
            'validate_fixity_during_check': False,
            'output_csv_include_input_csv': False,
            'timestamp_rollback': False,
            'enable_http_cache': True,
            'validate_terms_exist': True,
            'drupal_8': None,
            'published': 1,
            'media_types': self.get_media_types(),
            'preprocessors': {},
            'check': self.args.check,
            'get_csv_template': self.args.get_csv_template,
            'paged_content_sequence_separator': '-',
            'media_bundle_file_fields': self.get_media_fields(),
            'media_fields': self.get_media_fields(),
        }

    def path_check(self):
        # Check existence of configuration file.
        if not os.path.exists(self.args.config):
            # Since the main logger gets its log file location from this file, we
            # need to define a local logger to write to the default log file location,
            # 'workbench.log'.
            logging.basicConfig(
                filename='workbench.log',
                format='%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%d-%b-%y %H:%M:%S')
            message = 'Error: Configuration file "' + self.args.config + '" not found.'
            logging.error(message)
            sys.exit(message)

    def validate(self):
        error_messages = []
        type_check = issue_request(self.config, 'GET', f"{self.config['host']}/admin/structure/types/manage/{self.config['content_type']}")
        if type_check.status_code == 404:
            message = f"Content type {self.config['content_type']} not defined on {self.config['host']}."
            error_messages.append(message)
        if error_messages:
           sys.exit('Error: ' + message)
