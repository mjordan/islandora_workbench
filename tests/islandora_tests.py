"""unittest tests that require a live Drupal. In most cases, the URL, credentials, etc.
   are in a configuration file referenced in the test.
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

    def setUp(self):
        cmd = ["./workbench", "--config", "google_spreadsheet.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Saving data from https://docs.google.com', '')
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestCheckUpdate(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "update.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestCheckDelete(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "delete.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestCheckAddMedia(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "add_media.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


class TestTypedRelationBadRelatorCheck(unittest.TestCase):

    def test_bad_relator_check_fail(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'typed_relation_test', 'bad_relator.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'does not use the pattern required for typed relation fields', '')
        except subprocess.CalledProcessError as err:
            pass


class TestTypedRelationBadUriCheck(unittest.TestCase):

    def test_bad_uri_check_fail(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'typed_relation_test', 'bad_uri.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'example.com', '')
        except subprocess.CalledProcessError as err:
            pass


class TestTypedRelationNewTypedRelationCheck(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'typed_relation_test', 'add_new_typed_relation.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_new_typed_relation_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'and new terms will be created as noted', '')


class TestTypedRelationNoNamespaceCheck(unittest.TestCase):

    def test_no_namespace_check_fail(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'typed_relation_test', 'no_namespace.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'require a vocabulary namespace', '')
        except subprocess.CalledProcessError as err:
            pass


class TestGeolocationCheck(unittest.TestCase):

    def test_create_check_fail(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'geolocation_test', 'bad_geocoordinates.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, r'+43.45-123.17', '')
        except subprocess.CalledProcessError as err:
            pass


class TestHeaderColumnMismatch(unittest.TestCase):

    def test_header_column_mismatch_fail(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'header_column_mismatch_test', 'create.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'Row 2 of your CSV file does not', '')
        except subprocess.CalledProcessError as err:
            pass


class TestExecuteBootstrapScript(unittest.TestCase):

    def setUp(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))

        self.script_path = os.path.join(dir_path, 'assets', 'execute_bootstrap_script_test', 'script.py')
        self.config_file_path = os.path.join(dir_path, 'assets', 'execute_bootstrap_script_test', 'config.yml')

    def test_python_script(self):
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


class TestCreate(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatetestnids.txt')

    def test_create_check(self):
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


class TestCreateWithFieldTemplatesCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'create_with_field_templates_test', 'create.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertRegex(self.output, 'all 3 rows in the CSV file have the same number of columns as there are headers .6.', '')

    def tearDown(self):
        templated_csv_path = os.path.join(self.current_dir, 'assets', 'create_with_field_templates_test', 'metadata.csv.with_templates')
        os.remove(templated_csv_path)


class TestCreateFromFiles(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatefromfilestestnids.txt')

        self.rollback_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'files', 'rollback.csv')
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

    def test_create_check(self):
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

        self.assertEqual(len(nids), 2)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_from_files_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        os.remove(self.nid_file)

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)


class TestCreateWithNewTypedRelation(unittest.TestCase):
    # Note: You can't run this test class on its own, e.g.,
    # python3 tests/islandora_tests.py TestCreateWithNewTypedRelation.

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'typed_relation_test', 'create_with_new_typed_relation.yml')
        self.create_cmd = ["./workbench", "--config", config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatewithnewtypedrelationtestnids.txt')

        parser = argparse.ArgumentParser()
        parser.add_argument('--config')
        parser.add_argument('--check')
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

    def test_delete_check(self):
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


class TestCreatePagedContentFromDirectories (unittest.TestCase):

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

        # Test that the 'field_weight' value of the second node is 2.
        self.assertEqual(2, node_json['field_weight'][0]['value'])

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'create_paged_content_from_directories_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)


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


class TestTermFromUri(unittest.TestCase):
    # Note: You can't run this test class on its own, e.g.,
    # python3 tests/islandora_tests.py TestTermFromUri.

    def test_term_from_uri(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'create_test', 'create.yml')

        parser = argparse.ArgumentParser()
        parser.add_argument('--config')
        parser.add_argument('--check')
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

    def test_create_check(self):
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

        url = self.islandora_host + '/solr-search/content?search_api_fulltext=一九二四年六月十二日'
        response = requests.get(url)
        self.assertIn('一九二四年六月十二日', response.text)

        url = self.islandora_host + '/solr-search/content?search_api_fulltext=ᐊᑕᐅᓯᖅ ᓄᓇ, ᐅᓄᖅᑐᑦ ᓂᐲᑦ'
        response = requests.get(url)
        self.assertIn('ᐊᑕᐅᓯᖅ ᓄᓇ, ᐅᓄᖅᑐᑦ ᓂᐲᑦ', response.text)

        url = self.islandora_host + '/solr-search/content?search_api_fulltext=सरकारी दस्तावेज़'
        response = requests.get(url)
        self.assertIn('सरकारी दस्तावेज़', response.text)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'non_latin_text_test', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)


if __name__ == '__main__':
    unittest.main()
