"""unittest tests that require a live Drupal at https://islandora.traefik.me. In most cases, the host URL,
   credentials, etc. are in a configuration file referenced in the test.

   This test file contains tests for Workbench's hooks. Files islandora_tests.py, islandora_tests_paged_content.py,
   and islandora_tests_checks.py also contain tests that interact with an Islandora instance.
"""

import sys
import os
from ruamel.yaml import YAML
import tempfile
import subprocess
import argparse
import requests
import json
import urllib.parse
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils


class TestExecuteBootstrapScript(unittest.TestCase):

    def setUp(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))

        self.script_path = os.path.join(dir_path, 'assets', 'execute_bootstrap_script_test', 'script.py')
        self.config_file_path = os.path.join(dir_path, 'assets', 'execute_bootstrap_script_test', 'config.yml')

    def test_execute_python_script(self):
        output, return_code = workbench_utils.execute_bootstrap_script(self.script_path, self.config_file_path)
        self.assertEqual(output.strip(), b'Hello')


class TestExecutePreprocessorScript(unittest.TestCase):

    def setUp(self):
        yaml = YAML()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.script_path = os.path.join(dir_path, 'assets', 'preprocess_field_data', 'script.py')

    def test_preprocessor_script_single_field_value(self):
        output, return_code = workbench_utils.preprocess_field_data('|', 'hello', self.script_path)
        self.assertEqual(output.strip(), b'HELLO')

    def test_preprocessor_script_multiple_field_value(self):
        output, return_code = workbench_utils.preprocess_field_data('|', 'hello|there', self.script_path)
        self.assertEqual(output.strip(), b'HELLO|THERE')


class TestExecutePostActionEntityScript(unittest.TestCase):
    '''Note: Only tests for creating nodes.
    '''

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.realpath(__file__))
        self.config_file_path = os.path.join(self.current_dir, 'assets', 'execute_post_action_entity_script_test', 'create.yml')
        self.script_path = os.path.join(self.current_dir, 'assets', 'execute_post_action_entity_script_test', 'script.py')
        self.temp_dir = tempfile.gettempdir()
        self.output_file_path = os.path.join(self.temp_dir, 'execute_post_action_entity_script.dat')
        if os.path.exists(self.output_file_path):
            os.remove(self.output_file_path)

    def test_post_task_entity_script(self):
        self.nids = list()
        create_cmd = ["./workbench", "--config", self.config_file_path]
        create_output = subprocess.check_output(create_cmd)

        # The post-action script writes the file containing the titles of the nodes just created.
        with open(self.output_file_path, "r") as lines:
            titles = lines.readlines()

        self.assertEqual(titles[0].strip(), 'First title')
        self.assertEqual(titles[1].strip(), 'Second title')

    def tearDown(self):
        for nid in self.nids:
            quick_delete_cmd = ["./workbench", "--config", self.config_file_path, '--quick_delete_node', 'https://islandora.traefik.me/node/' + nid]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'execute_post_action_entity_script_test', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        self.preprocessed_file_path = os.path.join(self.temp_dir, 'metadata.csv.preprocessed')
        if os.path.exists(self.preprocessed_file_path):
            os.remove(self.preprocessed_file_path)

        if os.path.exists(self.output_file_path):
            os.remove(self.output_file_path)


if __name__ == '__main__':
    unittest.main()
