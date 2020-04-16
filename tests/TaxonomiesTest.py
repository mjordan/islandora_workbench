import os
import tempfile
import unittest
import json
import requests
import subprocess
from ruamel.yaml import YAML

# Note: This test suite requires the target Islandora to have the Islandora Workbench Integration module enabled.

class TaxonomiesTest (unittest.TestCase):

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
        vocab_url = self.islandora_host + '/vocabulary?_format=json&vid=genre'
        response = requests.get(vocab_url)
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


if __name__ == '__main__':
    unittest.main()
