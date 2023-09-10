import unittest
from unittest.mock import patch
import argparse
from collections import namedtuple
from WorkbenchConfig import WorkbenchConfig


class TestWorkbenchConfig(unittest.TestCase):

    def setUp(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', required=True, help='Configuration file to use.')
        parser.add_argument('--check', help='Check input data and exit without creating/updating/etc.',
                            action='store_true')
        parser.add_argument('--get_csv_template',
                            help='Generate a CSV template using the specified configuration file.', action='store_true')
        parser.add_argument('--quick_delete_node',
                            help='Delete the node (and all attached media) identified by the URL).')
        parser.add_argument('--quick_delete_media', help='Delete the media (and attached file) identified by the URL).')
        parser.add_argument('--contactsheet', help='Generate a contact sheet.', action='store_true')
        parser.add_argument('--version', action='version', version='Islandora Workbench 0.0.0')
        self.parser = parser

    def test_init_path_check_invalid_file(self):
        test_file_name = '/file/does/not/exist.yml'

        args = self.parser.parse_args(['--config', test_file_name])

        with self.assertRaises(SystemExit) as exit_return, \
                patch('WorkbenchConfig.logging') as mocked_logging:

            mocked_logging.return_value = None

            WorkbenchConfig(args)

        error_message = 'Error: Configuration file "' + test_file_name + '" not found.'
        self.assertEqual(exit_return.exception.code, error_message)

        # TODO: check values sent to logger

    def test_init_path_check_valid_file(self):
        test_file_name = 'tests/assets/execute_bootstrap_script_test/config.yml'

        args = self.parser.parse_args(['--config', test_file_name])

        with patch('sys.exit', side_effect=lambda x: None) as mock_exit, \
                patch('WorkbenchConfig.WorkbenchConfig.validate') as mocked_validate, \
                patch('WorkbenchConfig.logging') as mocked_logging:

            mocked_validate.return_value = None
            mocked_logging.return_value = None

            WorkbenchConfig(args)

            mock_exit.assert_not_called()

        # TODO: check values sent to logger

    def test_get_config_valid_config_file_01(self):
        test_file_name = 'tests/assets/WorkbenchConfig_test/config_01_create_short_valid.yml'

        args = self.parser.parse_args(['--config', test_file_name])

        with patch('WorkbenchConfig.WorkbenchConfig.validate') as mocked_validate, \
                patch('WorkbenchConfig.logging') as mocked_logging:

            mocked_validate.return_value = None
            mocked_logging.return_value = None

            test_config_obj = WorkbenchConfig(args)

            test_config_dict = test_config_obj.get_config()

            # checking for config variables set in
            # tests/assets/execute_bootstrap_script_test/config.yml
            self.assertEqual(test_config_dict['task'], 'create')
            self.assertEqual(test_config_dict['host'], 'https://islandora.traefik.me')
            self.assertEqual(test_config_dict['username'], 'admin')
            self.assertEqual(test_config_dict['password'], 'password')
            # self.assertEqual(test_config_dict['media_type'], 'document')

        # TODO: check values sent to logger

    def test_init_validate_valid(self):
        test_file_name = 'tests/assets/WorkbenchConfig_test/config_01_create_short_valid.yml'

        args = self.parser.parse_args(['--config', test_file_name])

        with patch('WorkbenchConfig.issue_request') as mocked_issue_request, \
                patch('WorkbenchConfig.logging') as mocked_logging:

            mocked_logging.return_value = None

            fake_response = namedtuple('fake_response', ['status_code'])
            fake_response.status_code = 200
            mocked_issue_request.return_value = fake_response

            test_config_obj = WorkbenchConfig(args)

            content_type = 'islandora_object'
            url = f"https://islandora.traefik.me/entity/entity_form_display/node.{content_type}.default?_format=json"
            mocked_issue_request.assert_called_with(test_config_obj.get_config(), 'GET', url)

    def test_init_validate_invalid_content_type(self):
        test_file_name = 'tests/assets/WorkbenchConfig_test/config_02_01_create_short_invalid.yml'

        args = self.parser.parse_args(['--config', test_file_name])

        with patch('WorkbenchConfig.issue_request') as mocked_issue_request, \
                patch('WorkbenchConfig.logging') as mocked_logging, \
                self.assertRaises(SystemExit) as exit_return:

            mocked_logging.return_value = None

            fake_response = namedtuple('fake_response', ['status_code'])
            fake_response.status_code = 404
            mocked_issue_request.return_value = fake_response

            test_config_obj = WorkbenchConfig(args)

            content_type = 'invalid_content_type'
            host = 'https://islandora.traefik.me'
            url = f"{host}/entity/entity_form_display/node.{content_type}.default?_format=json"
            mocked_issue_request.assert_called_with(test_config_obj.get_config(), 'GET', url)

            error_message = f'Error: Content type {content_type} does not exist on {host}.'
            self.assertEqual(exit_return.exception.code, error_message)

    def test_init_validate_invalid_mutators_01(self):
        test_file_name = 'tests/assets/WorkbenchConfig_test/config_02_02_create_short_invalid.yml'

        args = self.parser.parse_args(['--config', test_file_name])

        with patch('WorkbenchConfig.issue_request') as mocked_issue_request, \
                patch('WorkbenchConfig.logging') as mocked_logging:

            mocked_logging.return_value = None

            fake_response = namedtuple('fake_response', ['status_code'])
            fake_response.status_code = 200
            mocked_issue_request.return_value = fake_response

            # Error text should only be this line, therefore use ^ and $ at the start and end of the message respectively
            error_message = "^Error: You may only select one of \['use_node_title_for_media', "  \
                + "'use_nid_in_media_title', 'field_for_media_title'\].\n  - This config  has selected " \
                + "\['use_node_title_for_media', 'use_nid_in_media_title'\].\n$"

            with self.assertRaisesRegex(SystemExit, error_message) as exit_return:
                test_config_obj = WorkbenchConfig(args)

    def test_init_validate_invalid_mutators_02(self):
        test_file_name = 'tests/assets/WorkbenchConfig_test/config_02_03_create_short_invalid.yml'

        args = self.parser.parse_args(['--config', test_file_name])

        with patch('WorkbenchConfig.issue_request') as mocked_issue_request, \
                patch('WorkbenchConfig.logging') as mocked_logging:

            mocked_logging.return_value = None

            fake_response = namedtuple('fake_response', ['status_code'])
            fake_response.status_code = 200
            mocked_issue_request.return_value = fake_response

            # Error text should only be this line, therefore use ^ and $ at the start and end of the message respectively
            error_message = "^Error: You may only select one of \['use_node_title_for_media', "  \
                + "'use_nid_in_media_title', 'field_for_media_title'\].\n  - This config  has selected " \
                + "\['use_node_title_for_media', 'field_for_media_title'\].\n$"

            with self.assertRaisesRegex(SystemExit, error_message) as exit_return:
                test_config_obj = WorkbenchConfig(args)

