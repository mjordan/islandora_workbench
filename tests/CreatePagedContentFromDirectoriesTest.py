import os
import tempfile
import unittest
import json
import requests
import subprocess
from ruamel.yaml import YAML


class CreatePagedContentFromDirectoriesTest (unittest.TestCase):

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


if __name__ == '__main__':
    unittest.main()
