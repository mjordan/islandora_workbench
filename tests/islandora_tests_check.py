"""unittest tests that require a live Drupal at http://localhost:8000. In most cases, the URL, credentials,
   etc. are in a configuration file referenced in the test.

   This test file contains tests for --check. Files islandora_tests.py, islandora_tests_paged_content.py,
   and islandora_tests_hooks.py also contain tests that interact with an Islandora instance.
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


class TestCreateCheck(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "create.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestCheckFromGoogleSpreadsheetCheck(unittest.TestCase):
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


class TestUpdateCheck(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "update.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_update_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestDeleteCheck(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "delete.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_delete_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestAddMediaCheck(unittest.TestCase):

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


class TestHeaderColumnMismatchCheck(unittest.TestCase):

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


class TestTaxonomies(unittest.TestCase):

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

        if os.path.exists(self.nid_file):
            os.remove(self.nid_file)

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
        self.assertRegex(str(stdout), '"XPosters"', '')

    def test_validate_term_id_does_not_exist(self):
        taxonomies_term_id_does_not_exist_config_file_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'term_id_not_in_taxonomy.yml')
        cmd = ["./workbench", "--config", taxonomies_term_id_does_not_exist_config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(str(stdout), '1000000', '')

    def tearDown(self):
        # Delete all terms in the genre taxonomy created by these tests.
        terms_to_delete = ['XNewspapers', 'XPostcards', 'XCartoons', 'XCertificates', 'XPosters']
        for term_name in terms_to_delete:
            get_tid_url = self.islandora_host + '/term_from_term_name?vocab=genre&name=' + urllib.parse.quote(term_name.strip()) + '&_format=json'
            get_tid_response = requests.get(get_tid_url, auth=(self.islandora_username, self.islandora_password))
            term_data = json.loads(get_tid_response.text)
            if len(term_data):
                term_to_delete_tid = term_data[0]['tid'][0]['value']
                delete_term_url = self.islandora_host + '/taxonomy/term/' + str(term_to_delete_tid) + '?_format=json'
                term_delete_response = requests.delete(delete_term_url, auth=(self.islandora_username, self.islandora_password))

        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'taxonomies_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)

        if os.path.exists(self.nid_file):
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


if __name__ == '__main__':
    unittest.main()
