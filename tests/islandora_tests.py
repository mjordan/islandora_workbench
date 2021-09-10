"""unittest tests that require a live Drupal at http://localhost:8000. In most cases, the URL, credentials,
   etc. are in a configuration file referenced in the test.
"""

import sys
import os
from ruamel.yaml import YAML
import tempfile
import subprocess
import argparse
import requests
import json
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils


class TestCheckCreate(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "create.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestCheckCreateFromGoogleSpreadsheet(unittest.TestCase):
    """Note: This test fetches data from https://docs.google.com/spreadsheets/d/13Mw7gtBy1A3ZhYEAlBzmkswIdaZvX18xoRBxfbgxqWc/edit#gid=0.
    """

    def setUp(self):
        cmd = ["./workbench", "--config", "google_spreadsheet.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_from_google_spreadsheet_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Extracting CSV data from https://docs.google.com', '')
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestCheckUpdate(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "update.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_update_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestCheckDelete(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "delete.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_delete_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestCheckAddMedia(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "add_media.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_add_media_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestTypedRelationBadRelatorCheck(unittest.TestCase):

    def test_bad_relator_check_fail(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'bad_relator.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'does not use the pattern required for typed relation fields', '')
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'input_data', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(self.current_dir, "assets", "typed_relation_test", "input_data", "bad_typed_relation_fail.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestTypedRelationBadUriCheck(unittest.TestCase):

    def test_bad_uri_check_fail(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'bad_uri.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'example.com', '')
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'input_data', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(self.current_dir, "assets", "typed_relation_test", "input_data", "bad_uri_fail.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestTypedRelationNewTypedRelationCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'add_new_typed_relation.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_new_typed_relation_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'and new terms will be created as noted', '')

    def tearDown(self):
        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'input_data', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(self.current_dir, "assets", "typed_relation_test", "input_data", "new_typed_relation.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestTypedRelationNoNamespaceCheck(unittest.TestCase):

    def test_no_namespace_check_fail(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'no_namespace.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'require a vocabulary namespace', '')
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'input_data', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(self.current_dir, "assets", "typed_relation_test", "input_data", "no_namespace.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestMissingVocabCsvCheck(unittest.TestCase):

    def test_missing_vocab_csv(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'vocab_csv_test', 'vocab_csv_missing.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'tests/assets/vocab_csv_test/assets/vocab_csv_test/person_fields_.csv not found', '')
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'assets', 'vocab_csv_test', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(self.current_dir, 'assets', 'vocab_csv_test', "metadata.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestExtraFieldInVocabCsvCheck(unittest.TestCase):

    def test_extra_field_in_vocab_csv(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'vocab_csv_test', 'extra_field_in_csv.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, '"person_fields_extra_field.csv" is not a field in the "person" vocabulary', '')
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'assets', 'vocab_csv_test', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(self.current_dir, 'assets', 'vocab_csv_test', "metadata.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestDelimiterCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'delimiter_test', 'create_tab.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_delimiter_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'input data appear to be valid', '')

    def tearDown(self):
        preprocessed_csv_file_path = os.path.join(self.current_dir, "assets", "delimiter_test", "metadata.tsv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestGeolocationCheck(unittest.TestCase):

    def test_geolocation_check(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'geolocation_test', 'bad_geocoordinates.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, r'+43.45-123.17', '')
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        preprocessed_csv_file_path = os.path.join(self.current_dir, "assets", "geolocation_test", "input_data", "bad_geocoorindates_fail.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestHeaderColumnMismatch(unittest.TestCase):

    def test_header_column_mismatch_fail(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'header_column_mismatch_test', 'create.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'Row 2 of your CSV file does not', '')
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'header_column_mismatch_test', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(self.current_dir, "assets", "header_column_mismatch_test", "metadata.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


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
        temp_dir = tempfile.gettempdir()
        self.output_file_path = os.path.join(temp_dir, 'execute_post_action_entity_script.dat')
        if os.path.exists(self.output_file_path):
            os.remove(self.output_file_path)

    def test_post_task_entity_script(self):
        cmd = ["./workbench", "--config", self.config_file_path]
        output = subprocess.check_output(cmd)
        with open(self.output_file_path, "r") as lines:
            titles = lines.readlines()

        self.assertEqual(titles[0].strip(), 'First title')
        self.assertEqual(titles[1].strip(), 'Second title')

    def tearDown(self):
        rollback_config_file_path = os.path.join(self.current_dir, 'assets', 'execute_post_action_entity_script_test', 'rollback.yml')
        cmd = ["./workbench", "--config", rollback_config_file_path]
        subprocess.check_output(cmd)

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'execute_post_action_entity_script_test', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        self.preprocessed_rollback_file_path = os.path.join(self.current_dir, 'assets', 'execute_post_action_entity_script_test', 'rollback.csv.prepocessed')
        if os.path.exists(self.preprocessed_rollback_file_path):
            os.remove(self.preprocessed_rollback_file_path)

        self.preprocessed_file_path = os.path.join(self.current_dir, 'assets', 'execute_post_action_entity_script_test', 'metadata.csv.prepocessed')
        if os.path.exists(self.preprocessed_file_path):
            os.remove(self.preprocessed_file_path)

        if os.path.exists(self.output_file_path):
            os.remove(self.output_file_path)


class TestCreate(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatetestnids.txt')

    def test_create(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 5)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_test', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        self.preprocessed_file_path = os.path.join(self.current_dir, 'assets', 'create_test', 'metadata.csv.prepocessed')
        if os.path.exists(self.preprocessed_file_path):
            os.remove(self.preprocessed_file_path)


class TestCreateWithFieldTemplatesCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'create_with_field_templates_test', 'create.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_with_field_templates_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'all 3 rows in the CSV file have the same number of columns as there are headers .6.', '')

    def tearDown(self):
        templated_csv_path = os.path.join(self.current_dir, 'assets', 'create_with_field_templates_test', 'metadata.csv.prepocessed')
        os.remove(templated_csv_path)


class TestCreateFromFiles(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatefromfilestestnids.txt')

    def test_create_from_files(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 3)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        os.remove(self.nid_file)

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'files', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)


class TestCreateFromFilesDrupal8(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'create_drupal_8.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatefromfilestestnids.txt')

    def test_create_from_files_drupal_8(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 3)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        os.remove(self.nid_file)

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'files', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)


class TestCreateWithNewTypedRelation(unittest.TestCase):
    # Note: You can't run this test class on its own, e.g.,
    # python3 tests/islandora_tests.py TestCreateWithNewTypedRelation.
    # because passing "TestCreateWithNewTypedRelation" as an argument
    # will cause the argparse parser to fail.

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'create_with_new_typed_relation.yml')
        self.create_cmd = ["./workbench", "--config", config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatewithnewtypedrelationtestnids.txt')

        parser = argparse.ArgumentParser()
        parser.add_argument('--config')
        parser.add_argument('--check')
        parser.add_argument('--get_csv_template')
        parser.set_defaults(config=config_file_path, check=False)
        args = parser.parse_args()
        config = workbench_utils.set_config_defaults(args)
        self.config = config

    def test_create_with_new_typed_relation(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 1)

        self.new_term_id = workbench_utils.find_term_in_vocab(self.config, 'person', 'Kirk, James T.')
        self.assertTrue(self.new_term_id)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'create_with_new_typed_relation_delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'input_data', 'create_with_new_typed_relation.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        term_endpoint = self.config['host'] + '/taxonomy/term/' + str(self.new_term_id) + '?_format=json'
        delete_term_response = workbench_utils.issue_request(self.config, 'DELETE', term_endpoint)


class TestDelete(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'delete_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchdeletetesttnids.txt')

        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

    def test_delete(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'delete_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()

        self.assertEqual(len(delete_lines), 6)

    def tearDown(self):
        os.remove(self.nid_file)


class TestCreatePagedContent(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_test', 'create.yml')

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config['host']

        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatepagedcontenttestnids.txt')

    def test_create_paged_content(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 6)

        # Test a page object's 'field_member_of' value to see if it matches
        # its parent's node ID. In this test, the last paged content object's
        # node ID will be the fourth node ID in nids (the previous three were
        # for the first paged content object plus its two pages). Note: the
        # metadata.csv file used to create the paged content and page objects
        # uses hard-coded term IDs from the Islandora Models taxonomy as used
        # in the Islandora Playbook. If they change or are different in the
        # Islandora this test is running against, this test will fail.
        parent_node_id_to_test = nids[3]
        # The last node to be created was a page.
        child_node_id_to_test = nids[5]
        node_url = self.islandora_host + '/node/' + child_node_id_to_test + '?_format=json'
        response = requests.get(node_url)
        node_json = json.loads(response.text)
        field_member_of = node_json['field_member_of'][0]['target_id']

        self.assertEqual(int(parent_node_id_to_test), field_member_of)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_test', 'metadata.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_test', 'rollback.csv')
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)


class TestCreatePagedContentFromDirectories(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_from_directories_test', 'books.yml')

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config['host']

        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatepagedcontentfromdirectoriestestnids.txt')

    def test_create_paged_content_from_directories(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 4)

        # Test a page object's 'field_member_of' value to see if it matches its
        # parent's node ID. In this test, we'll test the second page. Note: the
        # metadata CSV file used to create the paged content and page objects
        # uses hard-coded term IDs from the Islandora Models taxonomy as used
        # in the Islandora Playbook. If they change or are different in the
        # Islandora this test is running against, this test will fail. Also note
        # that this test creates media and does not delete them.
        parent_node_id_to_test = nids[0]
        child_node_id_to_test = nids[2]
        node_url = self.islandora_host + '/node/' + child_node_id_to_test + '?_format=json'
        response = requests.get(node_url)
        node_json = json.loads(response.text)
        field_member_of = node_json['field_member_of'][0]['target_id']

        self.assertEqual(int(parent_node_id_to_test), field_member_of)

        # Test that the 'field_weight' value of the second node is 3.
        self.assertEqual(3, node_json['field_weight'][0]['value'])

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_from_directories_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_from_directories_test', 'samplebooks', 'metadata.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_from_directories_test', 'samplebooks', 'rollback.csv')
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)


class TestCreatePagedContentFromDirectoriesDrupal8(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_from_directories_test', 'books_drupal_8.yml')

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config['host']

        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatepagedcontentfromdirectoriestestnids.txt')

    def test_create_paged_content_from_directories_drupal_8(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 4)

        # Test a page object's 'field_member_of' value to see if it matches its
        # parent's node ID. In this test, we'll test the second page. Note: the
        # metadata CSV file used to create the paged content and page objects
        # uses hard-coded term IDs from the Islandora Models taxonomy as used
        # in the Islandora Playbook. If they change or are different in the
        # Islandora this test is running against, this test will fail. Also note
        # that this test creates media and does not delete them.
        parent_node_id_to_test = nids[0]
        child_node_id_to_test = nids[2]
        node_url = self.islandora_host + '/node/' + child_node_id_to_test + '?_format=json'
        response = requests.get(node_url)
        node_json = json.loads(response.text)
        field_member_of = node_json['field_member_of'][0]['target_id']

        self.assertEqual(int(parent_node_id_to_test), field_member_of)

        # Test that the 'field_weight' value of the second node is 3.
        self.assertEqual(3, node_json['field_weight'][0]['value'])

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_from_directories_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_from_directories_test', 'samplebooks', 'metadata.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_from_directories_test', 'samplebooks', 'rollback.csv')
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)


class TestTaxonomies (unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        taxonomies_config_file_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'create.yml')

        yaml = YAML()
        with open(taxonomies_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config['host']
        self.islandora_username = config['username']
        self.islandora_password = config['password']

        self.create_cmd = ["./workbench", "--config", taxonomies_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchtaxonomiestestnids.txt')

        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

    def test_validate_term_names_exist(self):
        taxonomies_terms_exist_config_file_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'create.yml')
        cmd = ["./workbench", "--config", taxonomies_terms_exist_config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(output, 'term IDs/names in CSV file exist in their respective taxonomies', '')

    def test_validate_term_name_does_not_exist(self):
        taxonomies_term_name_does_not_exist_config_file_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'term_name_not_in_taxonomy.yml')
        cmd = ["./workbench", "--config", taxonomies_term_name_does_not_exist_config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(str(stdout), '"Posters"', '')

    def test_validate_term_id_does_not_exist(self):
        taxonomies_term_id_does_not_exist_config_file_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'term_id_not_in_taxonomy.yml')
        cmd = ["./workbench", "--config", taxonomies_term_id_does_not_exist_config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(str(stdout), '1000000', '')

    def tearDown(self):
        # Delete all terms in the genre taxonomy.
        vocab_url = self.islandora_host + '/vocabulary/genre?_format=json'
        response = requests.get(vocab_url, auth=(self.islandora_username, self.islandora_password))
        vocab_json = json.loads(response.text)
        vocab = json.loads(response.text)
        for term in vocab:
            tid = term['tid'][0]['value']
            term_url = self.islandora_host + '/taxonomy/term/' + str(tid) + '?_format=json'
            response = requests.delete(term_url, auth=(self.islandora_username, self.islandora_password))

        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        rollback_file_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'rollback.csv')
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'metadata.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'term_id_not_in_taxonomy.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'term_name_not_in_taxonomy.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)


class TestTermFromUri(unittest.TestCase):
    # Note: You can't run this test class on its own, e.g.,
    # python3 tests/islandora_tests.py TestTermFromUri.
    # because passing "TestTermFromUri" as an argument
    # will cause the argparse parser to fail.

    def test_term_from_uri(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'create_test', 'create.yml')

        parser = argparse.ArgumentParser()
        parser.add_argument('--config')
        parser.add_argument('--check')
        parser.add_argument('--get_csv_template')
        parser.set_defaults(config=config_file_path, check=False)
        args = parser.parse_args()
        config = workbench_utils.set_config_defaults(args)

        tid = workbench_utils.get_term_id_from_uri(config, 'http://mozilla.github.io/pdf.js')
        self.assertEqual(tid, 3)


class TestCreateWithNonLatinText(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'non_latin_text_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config['host']

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatenonlatintestnids.txt')
        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'non_latin_text_test', 'rollback.csv')

    def test_create_with_non_latin_text(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 3)

        url = self.islandora_host + '/node/' + str(nids[0]) + '?_format=json'
        response = requests.get(url)
        node = json.loads(response.text)
        title = str(node['title'][0]['value'])
        self.assertEqual(title, '一九二四年六月十二日')

        url = self.islandora_host + '/node/' + str(nids[1]) + '?_format=json'
        response = requests.get(url)
        node = json.loads(response.text)
        title = str(node['title'][0]['value'])
        self.assertEqual(title, 'सरकारी दस्तावेज़')

        url = self.islandora_host + '/node/' + str(nids[2]) + '?_format=json'
        response = requests.get(url)
        node = json.loads(response.text)
        title = str(node['title'][0]['value'])
        self.assertEqual(title, 'ᐊᑕᐅᓯᖅ ᓄᓇ, ᐅᓄᖅᑐᑦ ᓂᐲᑦ')

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'non_latin_text_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'non_latin_text_test', 'metadata.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)


class TestGoogleGid(unittest.TestCase):

    def test_google_gid(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'google_gid_test', 'gid_0.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        lines = output.splitlines()
        self.assertRegex(output, 'OK, all 2 rows in the CSV file')

        config_file_path = os.path.join(current_dir, 'assets', 'google_gid_test', 'gid_1867618389.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        lines = output.splitlines()
        self.assertRegex(output, 'OK, all 3 rows in the CSV file')

        config_file_path = os.path.join(current_dir, 'assets', 'google_gid_test', 'gid_390347846.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        lines = output.splitlines()
        self.assertRegex(output, 'OK, all 5 rows in the CSV file')

        config_file_path = os.path.join(current_dir, 'assets', 'google_gid_test', 'gid_953977578.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        lines = output.splitlines()
        self.assertRegex(output, 'OK, all 1 rows in the CSV file')


class TestCommentedCsvs(unittest.TestCase):

    def test_commented_csv(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))

        config_file_path = os.path.join(current_dir, "assets", "commented_csvs_test", "raw_csv.yml")
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        lines = output.splitlines()
        self.assertRegex(output, 'all 3 rows in the CSV file', '')
        preprocessed_csv_file_path = os.path.join(current_dir, "assets", "commented_csvs_test", "metadata.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)

        config_file_path = os.path.join(current_dir, "assets", "commented_csvs_test", "excel.yml")
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        lines = output.splitlines()
        self.assertRegex(output, 'all 4 rows in the CSV file', '')
        csv_file_path = os.path.join(current_dir, "assets", "commented_csvs_test", "excel.csv")
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
        preprocessed_csv_file_path = os.path.join(current_dir, "assets", "commented_csvs_test", "excel.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)

        config_file_path = os.path.join(current_dir, "assets", "commented_csvs_test", "google_sheets.yml")
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        lines = output.splitlines()
        self.assertRegex(output, 'all 5 rows in the CSV file', '')
        csv_file_path = os.path.join(current_dir, "assets", "commented_csvs_test", "google_sheet.csv")
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
        preprocessed_csv_file_path = os.path.join(current_dir, "assets", "commented_csvs_test", "google_sheet.csv.prepocessed")
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestSecondaryTask(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'create.yml')

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config['host']

        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchsecondarytasktestnids.txt')

    def test_secondary_task(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 5)

        for nid in nids:
            node_url = self.islandora_host + '/node/' + nid + '?_format=json'
            response = requests.get(node_url)
            node_json = json.loads(response.text)
            # Get the node ID of the parent node.
            if node_json['title'][0]['value'].startswith('Tester'):
                parent_nid = node_json['nid'][0]['value']
                break

        for nid in nids:
            node_url = self.islandora_host + '/node/' + nid + '?_format=json'
            response = requests.get(node_url)
            node_json = json.loads(response.text)
            if node_json['title'][0]['value'].startswith('Secondary task test child 1'):
                self.assertEqual(int(node_json['field_member_of'][0]['target_id']), int(parent_nid))
            elif node_json['title'][0]['value'].startswith('Secondary task test child 2'):
                self.assertEqual(int(node_json['field_member_of'][0]['target_id']), int(parent_nid))
            else:
                self.assertEqual(node_json['field_member_of'], [])

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'metadata.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)
        secondary_preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'secondary.csv.prepocessed')
        if os.path.exists(secondary_preprocessed_csv_path):
            os.remove(secondary_preprocessed_csv_path)

        map_file_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'id_to_node_map.tsv')
        if os.path.exists(map_file_path):
            os.remove(map_file_path)

        rollback_file_path = os.path.join(self.current_dir, 'assets', 'secondary_task_test', 'rollback.csv')
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)


class TestAdditionalFilesCreate (unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'create.yml')

        yaml = YAML()
        with open(create_config_file_path, 'r') as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        self.config = {}
        for k, v in config_data.items():
            self.config[k] = v
        self.islandora_host = self.config['host']
        self.islandora_username = self.config['username']
        self.islandora_password = self.config['password']

        self.create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'rollback.csv')
        with open(self.rollback_file_path, 'r') as rbf:
            rollback_file_contents = rbf.read()

        # There will only be one nid in the rollback.csv file.
        nid = rollback_file_contents.replace('node_id', '')
        self.nid = nid.strip()

        media_list_url = self.islandora_host + '/node/' + self.nid + '/media?_format=json'
        media_list_response = requests.get(media_list_url, auth=(self.islandora_username, self.islandora_password))
        media_list_json = json.loads(media_list_response.text)
        self.media_sizes = dict()
        self.media_use_tids = dict()
        for media in media_list_json:
            self.media_use_tids[media['mid'][0]['value']] = media['field_media_use'][0]['target_id']
            if 'field_file_size' in media:
                self.media_sizes[media['mid'][0]['value']] = media['field_file_size'][0]['value']
            # We don't use the transcript file's size here since it's not available via REST. Instead, since this
            # file will be the only media with 'field_edited_text' (the transcript), we tack its value onto media_sizes
            # for testing below.
            if 'field_edited_text' in media:
                self.media_sizes['transcript'] = media['field_edited_text'][0]['value']

    def test_media_creation(self):
        # This is the original file's size.
        self.assertTrue(217504 in self.media_sizes.values())
        # This is the preservation file's size.
        self.assertTrue(286445 in self.media_sizes.values())
        # This is the transcript.
        self.assertIn('This is a transcript.', self.media_sizes['transcript'])

    def test_media_use_tids(self):
        '''Doesn't associate media use terms to nodes, but at least it confirms that the intended
           media use tids are present in the media created by this test.
        '''
        preservation_media_use_tid = self.get_term_id_from_uri("http://pcdm.org/use#PreservationMasterFile")
        self.assertTrue(preservation_media_use_tid in self.media_use_tids.values())
        transcript_media_use_tid = self.get_term_id_from_uri("http://pcdm.org/use#Transcript")
        self.assertTrue(transcript_media_use_tid in self.media_use_tids.values())

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'rollback.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'create.csv.prepocessed')
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        rollback_csv_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'rollback.csv')
        if os.path.exists(rollback_csv_path):
            os.remove(rollback_csv_path)

        preprocessed_rollback_csv_path = os.path.join(self.current_dir, 'assets', 'additional_files_test', 'rollback.csv.prepocessed')
        if os.path.exists(preprocessed_rollback_csv_path):
            os.remove(preprocessed_rollback_csv_path)

    def get_term_id_from_uri(self, uri):
        '''We don't use get_term_from_uri() from workbench_utils because it requires a full config object.
        '''
        term_from_authority_link_url = self.islandora_host + '/term_from_uri?_format=json&uri=' + uri.replace('#', '%23')
        response = requests.get(term_from_authority_link_url, auth=(self.islandora_username, self.islandora_password))
        response_body = json.loads(response.text)
        tid = response_body[0]['tid'][0]['value']
        return tid


if __name__ == '__main__':
    unittest.main()
