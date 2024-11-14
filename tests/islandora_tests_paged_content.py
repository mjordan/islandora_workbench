"""unittest tests that require a live Drupal at https://islandora.dev. In most cases, the host URL,
   credentials, etc. are in a configuration file referenced in the test.

   This test file contains tests for paged content. Files islandora_tests.py, islandora_tests_paged_check.py,
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


class TestCreatePagedContent(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir, "assets", "create_paged_content_test", "create.yml"
        )

        yaml = YAML()
        with open(self.create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config["host"]

        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]

        self.temp_dir = tempfile.gettempdir()

    def test_create_paged_content(self):
        requests.packages.urllib3.disable_warnings()
        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 6)

        # Test a page object's 'field_member_of' value to see if it matches
        # its parent's node ID. In this test, the last paged content object's
        # node ID will be the fourth node ID in nids (the previous three were
        # for the first paged content object plus its two pages). Note: the
        # metadata.csv file used to create the paged content and page objects
        # uses hard-coded term IDs from the Islandora Models taxonomy as used
        # in the Islandora Playbook. If they change or are different in the
        # Islandora this test is running against, this test will fail.
        parent_node_id_to_test = self.nids[3]
        # The last node to be created was a page.
        child_node_id_to_test = self.nids[5]
        node_url = (
            self.islandora_host + "/node/" + child_node_id_to_test + "?_format=json"
        )
        response = requests.get(node_url, verify=False)
        node_json = json.loads(response.text)
        field_member_of = node_json["field_member_of"][0]["target_id"]

        self.assertEqual(int(parent_node_id_to_test), field_member_of)

    def tearDown(self):
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                self.islandora_host + "/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        preprocessed_csv_path = os.path.join(self.temp_dir, "metadata.csv.preprocessed")
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        rollback_file_path = os.path.join(
            self.current_dir, "assets", "create_paged_content_test", "rollback.csv"
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)


class TestCreatePagedContentFromDirectories(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "create_paged_content_from_directories_test",
            "books.yml",
        )

        yaml = YAML()
        with open(self.create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config["host"]
        self.islandora_username = config["username"]
        self.islandora_password = config["password"]

        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]

        self.temp_dir = tempfile.gettempdir()

    def test_create_paged_content_from_directories(self):
        requests.packages.urllib3.disable_warnings()
        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                # E.g. a URL alias.
                if workbench_utils.value_is_numeric(nid) is False:
                    url = line[line.find("http") :].strip(".")
                    nid = workbench_utils.get_nid_from_url_without_config(url)
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 4)

        # Test a page object's 'field_member_of' value to see if it matches its
        # parent's node ID. In this test, we'll test the second page. Note: the
        # metadata CSV file used to create the paged content and page objects
        # uses hard-coded term IDs from the Islandora Models taxonomy as used
        # in the Islandora Playbook. If they change or are different in the
        # Islandora this test is running against, this test will fail. Also note
        # that this test creates media and does not delete them.
        parent_node_id_to_test = self.nids[0]
        # Get the REST feed for the parent node's members.
        members_url = (
            self.islandora_host
            + "/node/"
            + parent_node_id_to_test
            + "/members?_format=json"
        )
        # Need to provide credentials for this REST export.
        members_response = requests.get(
            members_url,
            auth=(self.islandora_username, self.islandora_password),
            verify=False,
        )
        members = json.loads(members_response.text)

        expected_member_weights = [1, 2, 3]
        retrieved_member_weights = list()
        for member in members:
            retrieved_member_weights.append(int(member["field_weight"][0]["value"]))
            # Test that each page indeed a member of the first node created during this test.
            self.assertEqual(
                int(parent_node_id_to_test),
                int(member["field_member_of"][0]["target_id"]),
            )

        # Test that the weights assigned to the three pages are what we expect.
        self.assertEqual(expected_member_weights, retrieved_member_weights)

    def tearDown(self):
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                f"{self.islandora_host}/node/{nid}",
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        preprocessed_csv_path = os.path.join(self.temp_dir, "metadata.csv.preprocessed")
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "create_paged_content_from_directories_test",
            "samplebooks",
            "rollback.csv",
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)


class TestCreatePagedContentFromDirectoriesPageFilesSourceDirField(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "create_paged_content_from_directories_test",
            "books_page_files_source_dir_field.yml",
        )

        yaml = YAML()
        with open(self.create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config["host"]
        self.islandora_username = config["username"]
        self.islandora_password = config["password"]

        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]

        self.temp_dir = tempfile.gettempdir()

    def test_create_paged_content_from_directories(self):
        requests.packages.urllib3.disable_warnings()
        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                # E.g. a URL alias.
                if workbench_utils.value_is_numeric(nid) is False:
                    url = line[line.find("http") :].strip(".")
                    nid = workbench_utils.get_nid_from_url_without_config(url)
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 4)

        # Test a page object's 'field_member_of' value to see if it matches its
        # parent's node ID. In this test, we'll test the second page. Note: the
        # metadata CSV file used to create the paged content and page objects
        # uses hard-coded term IDs from the Islandora Models taxonomy as used
        # in the Islandora Playbook. If they change or are different in the
        # Islandora this test is running against, this test will fail. Also note
        # that this test creates media and does not delete them.
        parent_node_id_to_test = self.nids[0]
        # Get the REST feed for the parent node's members.
        members_url = (
            self.islandora_host
            + "/node/"
            + parent_node_id_to_test
            + "/members?_format=json"
        )
        # Need to provide credentials for this REST export.
        members_response = requests.get(
            members_url,
            auth=(self.islandora_username, self.islandora_password),
            verify=False,
        )
        members = json.loads(members_response.text)

        expected_member_weights = [1, 2, 3]
        retrieved_member_weights = list()
        for member in members:
            retrieved_member_weights.append(int(member["field_weight"][0]["value"]))
            # Test that each page indeed a member of the first node created during this test.
            self.assertEqual(
                int(parent_node_id_to_test),
                int(member["field_member_of"][0]["target_id"]),
            )

        # Test that the weights assigned to the three pages are what we expect.
        self.assertEqual(expected_member_weights, retrieved_member_weights)

    def tearDown(self):
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                f"{self.islandora_host}/node/{nid}",
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "metadata_page_files_source_dir_field.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "create_paged_content_from_directories_test",
            "samplebooks",
            "rollback.csv",
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)


if __name__ == "__main__":
    unittest.main()
