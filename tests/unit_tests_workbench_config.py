import unittest
from unittest.mock import patch
import argparse

from WorkbenchConfig import WorkbenchConfig


class Test(unittest.TestCase):

    def test_path_check_valid_file(self):
        test_file_name = '/file/does/not/exist.yml'
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', required=True, help='Configuration file to use.')
        args = parser.parse_args(['--config', test_file_name])

        with self.assertRaises(SystemExit) as exit_return,\
                patch('WorkbenchConfig.logging') as mocked_logging:

            mocked_logging.return_value = None

            WorkbenchConfig(args)

        error_message = 'Error: Configuration file "' + test_file_name + '" not found.'
        self.assertEqual(exit_return.exception.code, error_message)

        # TODO: check values sent to logger

    # def test_path_check_fail(self):
    #     test_file_name = 'tests/assets/execute_bootstrap_script_test/config.yml'
    #     parser = argparse.ArgumentParser()
    #     parser.add_argument('--config', required=True, help='Configuration file to use.')
    #     args = parser.parse_args(['--config', test_file_name], '--check')
    #
    #     with self.assertRaises(SystemExit) as exit_return:
    #         WorkbenchConfig(args)
    #
    #     error_message = 'Error: Configuration file "' + test_file_name + '" not found.'
    #     self.assertEqual(exit_return.exception.code, error_message)

    def test_get_config(self):
        test_file_name = 'tests/assets/execute_bootstrap_script_test/config.yml'
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', required=True, help='Configuration file to use.')
        parser.add_argument('--check', help='Check input data and exit without creating/updating/etc.',
                            action='store_true')
        parser.add_argument('--get_csv_template',
                            help='Generate a CSV template using the specified configuration file.', action='store_true')

        args = parser.parse_args(['--config', test_file_name])

        with patch('WorkbenchConfig.WorkbenchConfig.validate') as mocked_validate,\
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
            self.assertEqual(test_config_dict['media_type'], 'document')

        # TODO: check values sent to logger

