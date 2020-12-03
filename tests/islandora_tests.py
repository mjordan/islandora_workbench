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


class TestTypedRelationCheck(unittest.TestCase):

    def test_create_check_fail(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'typed_relation_test', 'bad_typed_relation.yml')
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            lines = output.splitlines()
            self.assertRegex(output, 'does not use the pattern required for typed relation fields', '')
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
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'createtest', 'create.yml')
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
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'createtest', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)


class TestDelete(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'deletetest', 'create.yml')
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
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'deletetest', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()

        self.assertEqual(len(delete_lines), 5)

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

    def test_term_from_uri(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(current_dir, 'assets', 'createtest', 'create.yml')

        parser = argparse.ArgumentParser()
        parser.add_argument('--config')
        parser.add_argument('--check')
        # If we don't add this argument, we get an "unrecognized arguments: TestTermFromUri"
        # error when running this test class on its own, e.g., python3 tests/islandora_tests.py TestTermFromUri.
        parser.add_argument('TestTermFromUri')
        parser.set_defaults(config=config_file_path, check=False)
        args = parser.parse_args()
        config = workbench_utils.set_config_defaults(args)

        tid = workbench_utils.get_term_id_from_uri(config, 'http://mozilla.github.io/pdf.js')
        self.assertEqual(tid, 3)


if __name__ == '__main__':
    unittest.main()
