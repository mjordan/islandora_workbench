import unittest
import argparse
from WorkbenchConfig import WorkbenchConfig


class Test(unittest.TestCase):

    def test_path_check_valid_file(self):
        test_file_name = '/file/does/not/exist.yml'
        parser = argparse.ArgumentParser()
        parser.add_argument('--config', required=True, help='Configuration file to use.')
        args = parser.parse_args(['--config', test_file_name])

        with self.assertRaises(SystemExit) as exit_return:
            WorkbenchConfig(args)

        error_message = 'Error: Configuration file "' + test_file_name + '" not found.'
        self.assertEqual(exit_return.exception.code, error_message)

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

    # def test_get_config(self):
    #     ...

