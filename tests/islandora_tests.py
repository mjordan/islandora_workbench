"""unittest tests that require a live Drupal at https://islandora.traefik.me. In most cases, the host URL,
   credentials, etc. are in a configuration file referenced in the test.

   Files islandora_tests_check.py, islandora_tests_paged_content.py, and islandora_tests_hooks.py also
   contain tests that interact with an Islandora instance.
"""

import sys
import os
import glob
from ruamel.yaml import YAML
import tempfile
import subprocess
import argparse
import requests
import json
import urllib.parse
import unittest
import time
import copy

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils
from WorkbenchConfig import WorkbenchConfig


class TestCreate(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir, "assets", "create_test", "create.yml"
        )
        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]

    def test_create(self):
        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 2)

    def tearDown(self):
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                "https://islandora.traefik.me/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "create_test", "rollback.csv"
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        self.preprocessed_file_path = os.path.join(
            self.current_dir, "assets", "create_test", "metadata.csv.preprocessed"
        )
        if os.path.exists(self.preprocessed_file_path):
            os.remove(self.preprocessed_file_path)


class TestCreateFromFiles(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir, "assets", "create_from_files_test", "create.yml"
        )
        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]

    def test_create_from_files(self):
        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 3)

    def tearDown(self):
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                "https://islandora.traefik.me/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        self.rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "create_from_files_test",
            "files",
            "rollback.csv",
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)


class TestCreateWithMaxNodeTitleLength(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir, "assets", "max_node_title_length_test", "create.yml"
        )
        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]
        self.nids = list()
        self.output_lines = ""

        self.temp_dir = tempfile.gettempdir()

    def test_create(self):
        create_output = subprocess.check_output(self.create_cmd)
        self.create_output = create_output.decode().strip()
        self.output_lines = copy.copy(self.create_output)

        self.assertRegex(
            self.output_lines, '"This here title is 32 chars lo" .record 03', ""
        )
        self.assertRegex(
            self.output_lines, '"This here title is 34 chars lo" .record 04', ""
        )
        self.assertRegex(
            self.output_lines, '"This here title is 36 chars lo" .record 05', ""
        )
        self.assertRegex(
            self.output_lines, '"This title is 28 chars long." .record 06', ""
        )

        create_lines = self.create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 6)

    def tearDown(self):
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                "https://islandora.traefik.me/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "max_node_title_length_test", "rollback.csv"
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        self.preprocessed_file_path = os.path.join(
            self.temp_dir, "create_max_node_title_length.csv.preprocessed"
        )
        if os.path.exists(self.preprocessed_file_path):
            os.remove(self.preprocessed_file_path)


class TestUpdateWithMaxNodeTitleLength(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir, "assets", "max_node_title_length_test", "create.yml"
        )
        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]
        self.nids = list()

        self.update_csv_file_path = os.path.join(
            self.current_dir,
            "assets",
            "max_node_title_length_test",
            "update_max_node_title_length.csv",
        )
        self.update_config_file_path = os.path.join(
            self.current_dir, "assets", "max_node_title_length_test", "update.yml"
        )
        self.update_cmd = ["./workbench", "--config", self.update_config_file_path]

        self.temp_dir = tempfile.gettempdir()

    def test_create(self):
        requests.packages.urllib3.disable_warnings()
        create_output = subprocess.check_output(self.create_cmd)
        self.create_output = create_output.decode().strip()

        create_lines = self.create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 6)

        # Write out an update CSV file using the node IDs in self.nids.
        update_csv_file_rows = list()
        test_titles = [
            "This title is 37 chars___________long",
            "This title is 39 chars_____________long",
            "This title is 29 _ chars long",
            "This title is 42 chars________________long",
            "This title is 44 chars__________________long",
            "This title is 28 chars long.",
        ]
        update_csv_file_rows.append("node_id,title")
        i = 0
        while i <= 5:
            update_csv_file_rows.append(f"{self.nids[i]},{test_titles[i]}")
            i = i + 1
        with open(self.update_csv_file_path, mode="wt") as update_csv_file:
            update_csv_file.write("\n".join(update_csv_file_rows))

        # Run the update command.
        check_output = subprocess.check_output(self.update_cmd)

        # Fetch each node in self.nids and check to see if its title is <= 30 chars long. All should be.
        for nid_to_update in self.nids:
            node_url = (
                "https://islandora.traefik.me/node/"
                + str(self.nids[0])
                + "?_format=json"
            )
            node_response = requests.get(node_url, verify=False)
            node = json.loads(node_response.text)
            updated_title = str(node["title"][0]["value"])
            self.assertLessEqual(len(updated_title), 30, "")

    def tearDown(self):
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                "https://islandora.traefik.me/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "max_node_title_length_test", "rollback.csv"
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        self.preprocessed_file_path = os.path.join(
            self.temp_dir, "create_max_node_title_length.csv.preprocessed"
        )
        if os.path.exists(self.preprocessed_file_path):
            os.remove(self.preprocessed_file_path)

        # Update test: 1) delete the update CSV file, 2) delete the update .preprocessed file.
        if os.path.exists(self.update_csv_file_path):
            os.remove(self.update_csv_file_path)

        self.preprocessed_update_file_path = os.path.join(
            self.temp_dir, "update_max_node_title_length.csv.preprocessed"
        )
        if os.path.exists(self.preprocessed_update_file_path):
            os.remove(self.preprocessed_update_file_path)


class TestCreateWithNewTypedRelation(unittest.TestCase):
    # Note: You can't run this test class on its own, e.g., python3 tests/islandora_tests.py TestCreateWithNewTypedRelation
    # because passing "TestCreateWithNewTypedRelation" as an argument will cause the argparse parser to fail.

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "create_with_new_typed_relation.yml",
        )
        self.create_cmd = ["./workbench", "--config", self.config_file_path]

        self.temp_dir = tempfile.gettempdir()

        parser = argparse.ArgumentParser()
        parser.add_argument("--config")
        parser.add_argument("--check")
        parser.add_argument("--get_csv_template")
        parser.set_defaults(config=self.config_file_path, check=False)
        args = parser.parse_args()
        workbench_config = WorkbenchConfig(args)
        config = workbench_config.get_config()
        self.config = config

    def test_create_with_new_typed_relation(self):
        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 1)

        self.term_id = workbench_utils.find_term_in_vocab(
            self.config, "person", "Kirk, James T."
        )
        self.assertTrue(self.term_id)

    def tearDown(self):
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.config_file_path,
                "--quick_delete_node",
                self.config["host"] + "/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "create_with_new_typed_relation.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        term_endpoint = (
            self.config["host"]
            + "/taxonomy/term/"
            + str(self.term_id)
            + "?_format=json"
        )
        delete_term_response = workbench_utils.issue_request(
            self.config, "DELETE", term_endpoint
        )


class TestDelete(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(
            self.current_dir, "assets", "delete_test", "create.yml"
        )
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, "workbenchdeletetesttnids.txt")

        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if "created at" in line:
                    nid = line.rsplit("/", 1)[-1]
                    nid = nid.strip(".")
                    nids.append(nid)
                    fh.write(nid + "\n")

    def test_delete(self):
        delete_config_file_path = os.path.join(
            self.current_dir, "assets", "delete_test", "delete.yml"
        )
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()

        self.assertEqual(len(delete_lines), 5)

    def tearDown(self):
        if os.path.exists(self.nid_file):
            os.remove(self.nid_file)
        if os.path.exists(self.nid_file + ".preprocessed"):
            os.remove(self.nid_file + ".preprocessed")


class TestUpdate(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir, "assets", "update_test", "create.yml"
        )
        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, "workbenchupdatetestnids.txt")
        self.update_metadata_file = os.path.join(
            self.current_dir, "assets", "update_test", "workbenchupdatetest.csv"
        )

        yaml = YAML()
        with open(self.create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config["host"]

        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()

        with open(self.nid_file, "a") as nids_fh:
            nids_fh.write("node_id\n")
            for line in create_lines:
                if "created at" in line:
                    nid = line.rsplit("/", 1)[-1]
                    nid = nid.strip(".")
                    nids_fh.write(nid + "\n")
                    self.nids.append(nid)

        # Add some values to the update CSV file to test against.
        with open(self.update_metadata_file, "a") as update_fh:
            update_fh.write("node_id,field_identifier,field_coordinates\n")
            update_fh.write(f'{self.nids[0]},identifier-0001,"99.1,-123.2"')

    def test_update(self):
        requests.packages.urllib3.disable_warnings()
        # Run update task.
        time.sleep(5)
        update_config_file_path = os.path.join(
            self.current_dir, "assets", "update_test", "update.yml"
        )
        self.update_cmd = ["./workbench", "--config", update_config_file_path]
        subprocess.check_output(self.update_cmd)

        # Confirm that fields have been updated.
        url = self.islandora_host + "/node/" + str(self.nids[0]) + "?_format=json"
        response = requests.get(url, verify=False)
        node = json.loads(response.text)
        identifier = str(node["field_identifier"][0]["value"])
        self.assertEqual(identifier, "identifier-0001")
        coodinates = str(node["field_coordinates"][0]["lat"])
        self.assertEqual(coodinates, "99.1")

    def tearDown(self):
        delete_config_file_path = os.path.join(
            self.current_dir, "assets", "update_test", "delete.yml"
        )
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        subprocess.check_output(delete_cmd)

        os.remove(self.nid_file)
        os.remove(self.update_metadata_file)
        nid_file_preprocessed_file = os.path.join(
            self.temp_dir, "workbenchupdatetestnids.txt.preprocessed"
        )
        if os.path.exists(nid_file_preprocessed_file):
            os.remove(nid_file_preprocessed_file)
        update_test_csv_preprocessed_file = os.path.join(
            self.temp_dir, "workbenchupdatetest.csv.preprocessed"
        )
        if os.path.exists(update_test_csv_preprocessed_file):
            os.remove(update_test_csv_preprocessed_file)
        create_csv_preprocessed_file = os.path.join(
            self.temp_dir, "create.csv.preprocessed"
        )
        if os.path.exists(create_csv_preprocessed_file):
            os.remove(create_csv_preprocessed_file)


class TestCreateWithNonLatinText(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(
            self.current_dir, "assets", "non_latin_text_test", "create.yml"
        )
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        yaml = YAML()
        with open(create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config["host"]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(
            self.temp_dir, "workbenchcreatenonlatintestnids.txt"
        )
        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "non_latin_text_test", "rollback.csv"
        )

    def test_create_with_non_latin_text(self):
        requests.packages.urllib3.disable_warnings()
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if "created at" in line:
                    nid = line.rsplit("/", 1)[-1]
                    nid = nid.strip(".")
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 3)

        url = self.islandora_host + "/node/" + str(nids[0]) + "?_format=json"
        response = requests.get(url, verify=False)
        node = json.loads(response.text)
        title = str(node["title"][0]["value"])
        self.assertEqual(title, "一九二四年六月十二日")

        url = self.islandora_host + "/node/" + str(nids[1]) + "?_format=json"
        response = requests.get(url, verify=False)
        node = json.loads(response.text)
        title = str(node["title"][0]["value"])
        self.assertEqual(title, "सरकारी दस्तावेज़")

        url = self.islandora_host + "/node/" + str(nids[2]) + "?_format=json"
        response = requests.get(url, verify=False)
        node = json.loads(response.text)
        title = str(node["title"][0]["value"])
        self.assertEqual(title, "ᐊᑕᐅᓯᖅ ᓄᓇ, ᐅᓄᖅᑐᑦ ᓂᐲᑦ")

    def tearDown(self):
        delete_config_file_path = os.path.join(
            self.current_dir, "assets", "non_latin_text_test", "delete.yml"
        )
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_path = os.path.join(
            self.current_dir,
            "assets",
            "non_latin_text_test",
            "metadata.csv.preprocessed",
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        nid_file_preprocessed_path = self.nid_file + ".preprocessed"
        if os.path.exists(nid_file_preprocessed_path):
            os.remove(nid_file_preprocessed_path)


class TestSecondaryTask(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir, "assets", "secondary_task_test", "create.yml"
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

    def test_secondary_task(self):
        requests.packages.urllib3.disable_warnings()
        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 5)

        for nid in self.nids:
            node_url = self.islandora_host + "/node/" + nid + "?_format=json"
            response = requests.get(node_url, verify=False)
            node_json = json.loads(response.text)
            # Get the node ID of the parent node.
            if node_json["title"][0]["value"].startswith("Tester"):
                parent_nid = node_json["nid"][0]["value"]
                break

        for nid in self.nids:
            node_url = self.islandora_host + "/node/" + nid + "?_format=json"
            response = requests.get(node_url, verify=False)
            node_json = json.loads(response.text)
            if node_json["title"][0]["value"].startswith("Secondary task test child 1"):
                self.assertEqual(
                    int(node_json["field_member_of"][0]["target_id"]), int(parent_nid)
                )
            elif node_json["title"][0]["value"].startswith(
                "Secondary task test child 2"
            ):
                self.assertEqual(
                    int(node_json["field_member_of"][0]["target_id"]), int(parent_nid)
                )
            else:
                self.assertEqual(node_json["field_member_of"], [])

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

        preprocessed_csv_path = os.path.join(
            self.current_dir,
            "assets",
            "secondary_task_test",
            "metadata.csv.preprocessed",
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        secondary_preprocessed_csv_path = os.path.join(
            self.temp_dir, "secondary.csv.preprocessed"
        )
        if os.path.exists(secondary_preprocessed_csv_path):
            os.remove(secondary_preprocessed_csv_path)

        map_file_path = os.path.join(
            self.current_dir, "assets", "secondary_task_test", "id_to_node_map.tsv"
        )
        if os.path.exists(map_file_path):
            os.remove(map_file_path)

        rollback_file_path = os.path.join(
            self.current_dir, "assets", "secondary_task_test", "rollback.csv"
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)


class TestSecondaryTaskWithGoogleSheets(unittest.TestCase):
    """Note: This test fetches data from https://docs.google.com/spreadsheets/d/19AxFWEFuwEoNqH8ciUo0PRAroIpNE9BuBhE5tIE6INQ/edit#gid=0"""

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "secondary_task_with_google_sheets_and_excel_test",
            "google_sheets_primary.yml",
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

    def test_secondary_task_with_google_sheet(self):
        requests.packages.urllib3.disable_warnings()
        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 8)

        for nid in self.nids:
            node_url = self.islandora_host + "/node/" + nid + "?_format=json"
            response = requests.get(node_url, verify=False)
            node_json = json.loads(response.text)
            # Get the node ID of the parent node.
            if node_json["field_local_identifier"][0]["value"] == "GSP-04":
                parent_nid = node_json["nid"][0]["value"]
                break

        for nid in self.nids:
            node_url = self.islandora_host + "/node/" + nid + "?_format=json"
            response = requests.get(node_url, verify=False)
            node_json = json.loads(response.text)
            if node_json["field_local_identifier"][0]["value"] == "GSC-03":
                self.assertEqual(
                    int(node_json["field_member_of"][0]["target_id"]), int(parent_nid)
                )
            if node_json["field_local_identifier"][0]["value"] == "GSC-04":
                self.assertEqual(
                    int(node_json["field_member_of"][0]["target_id"]), int(parent_nid)
                )

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

        rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "secondary_task_with_google_sheets_and_excel_test",
            "rollback.csv",
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)
        google_sheet_csv_path = os.path.join(self.temp_dir, "google_sheet.csv")
        if os.path.exists(google_sheet_csv_path):
            os.remove(google_sheet_csv_path)

        secondary_task_google_sheets_csv_paths = glob.glob(
            "*secondary_task_with_google_sheets_and_excel_test_google_sheets_secondary*",
            root_dir=self.temp_dir,
        )
        for secondary_csv_file_path in secondary_task_google_sheets_csv_paths:
            if os.path.exists(os.path.join(self.temp_dir, secondary_csv_file_path)):
                os.remove(os.path.join(self.temp_dir, secondary_csv_file_path))

        google_sheet_csv_preprocessed_path = os.path.join(
            self.temp_dir, "google_sheet.csv.preprocessed"
        )
        if os.path.exists(google_sheet_csv_preprocessed_path):
            os.remove(google_sheet_csv_preprocessed_path)


class TestSecondaryTaskWithExcel(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "secondary_task_with_google_sheets_and_excel_test",
            "excel_primary.yml",
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

    def test_secondary_task_with_excel(self):
        requests.packages.urllib3.disable_warnings()
        self.nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Get the node IDs of the nodes created during this test
        # so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 8)

        for nid in self.nids:
            node_url = self.islandora_host + "/node/" + nid + "?_format=json"
            response = requests.get(node_url, verify=False)
            node_json = json.loads(response.text)
            # Get the node ID of the parent node.
            if node_json["field_local_identifier"][0]["value"] == "STTP-02":
                parent_nid = node_json["nid"][0]["value"]
                break

        for nid in self.nids:
            node_url = self.islandora_host + "/node/" + nid + "?_format=json"
            response = requests.get(node_url, verify=False)
            node_json = json.loads(response.text)
            if node_json["field_local_identifier"][0]["value"] == "STTC-01":
                self.assertEqual(
                    int(node_json["field_member_of"][0]["target_id"]), int(parent_nid)
                )
            if node_json["field_local_identifier"][0]["value"] == "STTC-02":
                self.assertEqual(
                    int(node_json["field_member_of"][0]["target_id"]), int(parent_nid)
                )

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

        rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "secondary_task_with_google_sheets_and_excel_test",
            "rollback.csv",
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)
        excel_csv_path = os.path.join(self.temp_dir, "excel.csv")
        if os.path.exists(excel_csv_path):
            os.remove(excel_csv_path)

        secondary_task_excel_csv_paths = glob.glob(
            "*secondary_task_with_google_sheets_and_excel_test_excel_secondary*",
            root_dir=self.temp_dir,
        )
        for secondary_csv_file_path in secondary_task_excel_csv_paths:
            if os.path.exists(os.path.join(self.temp_dir, secondary_csv_file_path)):
                os.remove(os.path.join(self.temp_dir, secondary_csv_file_path))

        excel_csv_preprocessed_path = os.path.join(
            self.temp_dir, "excel.csv.preprocessed"
        )
        if os.path.exists(excel_csv_preprocessed_path):
            os.remove(excel_csv_preprocessed_path)


class TestAdditionalFilesCreate(unittest.TestCase):

    def setUp(self):
        requests.packages.urllib3.disable_warnings()
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(
            self.current_dir, "assets", "additional_files_test", "create.yml"
        )

        yaml = YAML()
        with open(create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        self.config = {}
        for k, v in config_data.items():
            self.config[k] = v
        self.islandora_host = self.config["host"]
        self.islandora_username = self.config["username"]
        self.islandora_password = self.config["password"]

        self.create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        self.temp_dir = tempfile.gettempdir()

        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "additional_files_test", "rollback.csv"
        )
        with open(self.rollback_file_path, "r") as rbf:
            rollback_file_contents = rbf.read()

        # There will only be one nid in the rollback.csv file.
        nid = rollback_file_contents.replace("node_id", "")
        self.nid = nid.strip()

        media_list_url = (
            self.islandora_host + "/node/" + self.nid + "/media?_format=json"
        )
        media_list_response = requests.get(
            media_list_url,
            auth=(self.islandora_username, self.islandora_password),
            verify=False,
        )
        media_list_json = json.loads(media_list_response.text)
        self.media_sizes = dict()
        self.media_use_tids = dict()
        for media in media_list_json:
            self.media_use_tids[media["mid"][0]["value"]] = media["field_media_use"][0][
                "target_id"
            ]
            if "field_file_size" in media:
                self.media_sizes[media["mid"][0]["value"]] = media["field_file_size"][
                    0
                ]["value"]
            # We don't use the transcript file's size here since it's not available via REST. Instead, since this
            # file will be the only media with 'field_edited_text' (the transcript), we tack its value onto media_sizes
            # for testing below.
            if "field_edited_text" in media:
                self.media_sizes["transcript"] = media["field_edited_text"][0]["value"]

    def test_media_creation(self):
        # This is the original file's size.
        self.assertTrue(217504 in self.media_sizes.values())
        # This is the preservation file's size.
        self.assertTrue(286445 in self.media_sizes.values())
        # This is the transcript.
        self.assertIn("This is a transcript.", self.media_sizes["transcript"])

    def test_media_use_tids(self):
        """Doesn't associate media use terms to nodes, but at least it confirms that the intended
        media use tids are present in the media created by this test.
        """
        preservation_media_use_tid = self.get_term_id_from_uri(
            "http://pcdm.org/use#PreservationMasterFile"
        )
        self.assertTrue(preservation_media_use_tid in self.media_use_tids.values())
        transcript_media_use_tid = self.get_term_id_from_uri(
            "http://pcdm.org/use#Transcript"
        )
        self.assertTrue(transcript_media_use_tid in self.media_use_tids.values())

    def tearDown(self):
        delete_config_file_path = os.path.join(
            self.current_dir, "assets", "additional_files_test", "rollback.yml"
        )
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_path = os.path.join(self.temp_dir, "create.csv.preprocessed")
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        rollback_csv_path = os.path.join(
            self.current_dir, "assets", "additional_files_test", "rollback.csv"
        )
        if os.path.exists(rollback_csv_path):
            os.remove(rollback_csv_path)

        preprocessed_rollback_csv_path = os.path.join(
            self.temp_dir, "rollback.csv.preprocessed"
        )
        if os.path.exists(preprocessed_rollback_csv_path):
            os.remove(preprocessed_rollback_csv_path)

    def get_term_id_from_uri(self, uri):
        """We don't use get_term_from_uri() from workbench_utils because it requires a full config object."""
        term_from_authority_link_url = (
            self.islandora_host
            + "/term_from_uri?_format=json&uri="
            + uri.replace("#", "%23")
        )
        response = requests.get(
            term_from_authority_link_url,
            auth=(self.islandora_username, self.islandora_password),
            verify=False,
        )
        response_body = json.loads(response.text)
        tid = response_body[0]["tid"][0]["value"]
        return tid


class TestAdditionalFilesCreateAllowMissingFilesFalse(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "create_additional_files_allow_missing_files_false.yml",
        )
        self.create_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_false.log",
        )
        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "allow_missing_files_test", "rollback.csv"
        )
        self.temp_dir = tempfile.gettempdir()
        self.nids = list()

        yaml = YAML()
        with open(self.create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        self.config = {}
        for k, v in config_data.items():
            self.config[k] = v
        self.islandora_host = self.config["host"]
        self.islandora_username = self.config["username"]
        self.islandora_password = self.config["password"]

    def test_create(self):
        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Get the node IDs of the nodes created during this test
        # so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        # Only three nodes will be created before workbench exits.
        self.assertEqual(len(self.nids), 3)

        with open(self.create_log_file_path) as log_file:
            log_data = log_file.read()
            self.assertRegex(
                log_data,
                'Media for "additional_files" CSV column "tn" in row with ID "003" .* not created because CSV field is empty',
                "",
            )
            self.assertRegex(
                log_data,
                'Media for file "https://www.lib.sfu.ca/xxxtttuuu.jpg" named in field "tn" of CSV row with ID "005" not created because file does not exist',
                "",
            )
            self.assertNotRegex(
                log_data, "Islandora Workbench successfully completed", ""
            )

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

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "metadata_additional_files_check.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        if os.path.exists(self.create_log_file_path):
            os.remove(self.create_log_file_path)


class TestAdditionalFilesCreateAllowMissingFilesTrue(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "create_additional_files_allow_missing_files_true.yml",
        )
        self.create_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_true.log",
        )
        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "allow_missing_files_test", "rollback.csv"
        )
        self.temp_dir = tempfile.gettempdir()
        self.nids = list()

        yaml = YAML()
        with open(self.create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        self.config = {}
        for k, v in config_data.items():
            self.config[k] = v
        self.islandora_host = self.config["host"]
        self.islandora_username = self.config["username"]
        self.islandora_password = self.config["password"]

    def test_create(self):
        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Get the node IDs of the nodes created during this test
        # so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 5)

        with open(self.create_log_file_path) as log_file:
            log_data = log_file.read()
            self.assertRegex(
                log_data,
                'Media for "additional_files" CSV column "tn" in row with ID "003" .* not created because CSV field is empty',
                "",
            )
            self.assertRegex(
                log_data,
                'Media for file "https://www.lib.sfu.ca/xxxtttuuu.jpg" named in field "tn" of CSV row with ID "005" not created because file does not exist',
                "",
            )
            self.assertRegex(
                log_data,
                'Media for file "additional_files_2_tn.jpg" named in field "tn" of CSV row with ID "002" not created because file does not exist',
                "",
            )
            self.assertRegex(log_data, "Islandora Workbench successfully completed", "")

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

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "metadata_additional_files_check.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        if os.path.exists(self.create_log_file_path):
            os.remove(self.create_log_file_path)


class TestAdditionalFilesAddMediaAllowMissingFilesFalse(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_create_nodes.yml",
        )
        self.create_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_create_nodes.log",
        )
        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "allow_missing_files_test", "rollback.csv"
        )
        self.add_media_csv_template_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files.csv.template",
        )
        self.add_media_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_false.yml",
        )
        self.add_media_csv_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files.csv",
        )
        self.false_with_additional_files_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_false.log",
        )
        self.temp_dir = tempfile.gettempdir()
        self.nids = list()

        yaml = YAML()
        with open(self.create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        self.config = {}
        for k, v in config_data.items():
            self.config[k] = v
        self.islandora_host = self.config["host"]
        self.islandora_username = self.config["username"]
        self.islandora_password = self.config["password"]

        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Get the node IDs of the nodes created during this test
        # so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        # Insert their node IDs in the input CSV file. First, open the CSV template.
        with open(self.add_media_csv_template_file_path) as csv_template:
            csv_template_lines = csv_template.readlines()

        # Then add a node ID to the start of each line from the template
        # and write out an add_media input CSV file.
        template_line_index = 0
        with open(self.add_media_csv_file_path, "a+") as add_media_csv:
            # The first line in the output CSV is the headers from the template.
            add_media_csv.write(csv_template_lines[template_line_index])
            # The subsequent lines should each start with a node ID from.
            for node_id in self.nids:
                template_line_index = template_line_index + 1
                add_media_csv.write(
                    f"{node_id}{csv_template_lines[template_line_index]}"
                )

    def test_false(self):
        self.add_media_cmd = [
            "./workbench",
            "--config",
            self.add_media_config_file_path,
        ]
        proc = subprocess.Popen(
            self.add_media_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        stdout, stderr = proc.communicate()
        add_media_output = str(stdout.decode().strip())
        self.assertRegex(
            add_media_output,
            'Media for node .* not created since CSV column "preservation" is empty',
            "",
        )
        self.assertRegex(
            add_media_output,
            'Media for node .* not created since CSV column "file" is empty',
            "",
        )
        self.assertRegex(
            add_media_output,
            'Additional file "add_media_transcript_x.txt" identified in CSV "transcript" column for node ID .* not found',
            "",
        )

        with open(self.false_with_additional_files_log_file_path) as log_file_false:
            log_data_false = log_file_false.read()
            self.assertRegex(
                log_data_false,
                'Media for node .* not created since CSV column "preservation" is empty',
                "",
            )
            self.assertRegex(
                log_data_false,
                'Media for node .* not created since CSV column "file" is empty',
                "",
            )
            self.assertRegex(
                log_data_false,
                'Additional file "add_media_transcript_x.txt" identified in CSV "transcript" column for node ID .* not found',
                "",
            )

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

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        if os.path.exists(self.add_media_csv_file_path):
            os.remove(self.add_media_csv_file_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "add_media_create_nodes.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "add_media_additional_files.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        if os.path.exists(self.create_log_file_path):
            os.remove(self.create_log_file_path)

        if os.path.exists(self.false_with_additional_files_log_file_path):
            os.remove(self.false_with_additional_files_log_file_path)


class TestAdditionalFilesAddMediaAllowMissingFilesTrue(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.create_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_create_nodes.yml",
        )
        self.create_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_create_nodes.log",
        )
        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "allow_missing_files_test", "rollback.csv"
        )
        self.add_media_csv_template_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files.csv.template",
        )
        self.add_media_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_true.yml",
        )
        self.add_media_csv_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files.csv",
        )
        self.true_with_additional_files_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_true.log",
        )
        self.temp_dir = tempfile.gettempdir()
        self.nids = list()

        yaml = YAML()
        with open(self.create_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        self.config = {}
        for k, v in config_data.items():
            self.config[k] = v
        self.islandora_host = self.config["host"]
        self.islandora_username = self.config["username"]
        self.islandora_password = self.config["password"]

        self.create_cmd = ["./workbench", "--config", self.create_config_file_path]
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()

        # Get the node IDs of the nodes created during this test
        # so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        # Insert their node IDs in the input CSV file. First, open the CSV template.
        with open(self.add_media_csv_template_file_path) as csv_template:
            csv_template_lines = csv_template.readlines()

        # Then add a node ID to the start of each line from the template
        # and write out an add_media input CSV file.
        template_line_index = 0
        with open(self.add_media_csv_file_path, "a+") as add_media_csv:
            # The first line in the output CSV is the headers from the template.
            add_media_csv.write(csv_template_lines[template_line_index])
            # The subsequent lines should each start with a node ID from.
            for node_id in self.nids:
                template_line_index = template_line_index + 1
                add_media_csv.write(
                    f"{node_id}{csv_template_lines[template_line_index]}"
                )

    def test_true(self):
        self.add_media_cmd = [
            "./workbench",
            "--config",
            self.add_media_config_file_path,
        ]
        add_media_output = subprocess.check_output(self.add_media_cmd)
        add_media_output = add_media_output.decode().strip()

        self.assertRegex(
            add_media_output,
            'Media for node .* not created since CSV column "preservation" is empty',
            "",
        )
        self.assertRegex(
            add_media_output,
            'Media for node .* not created since CSV column "file" is empty',
            "",
        )

        with open(self.true_with_additional_files_log_file_path) as log_file_true:
            log_data_true = log_file_true.read()
            self.assertRegex(
                log_data_true,
                'Media for node .* not created since CSV column "preservation" is empty',
                "",
            )
            self.assertRegex(
                log_data_true,
                'Media for node .* not created since CSV column "file" is empty',
                "",
            )
            self.assertRegex(
                log_data_true,
                'Additional file "add_media_transcript_x.txt" identified in CSV "transcript" column for node ID .* not found',
                "",
            )
            self.assertRegex(
                log_data_true, "Islandora Workbench successfully completed", ""
            )

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

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        if os.path.exists(self.add_media_csv_file_path):
            os.remove(self.add_media_csv_file_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "add_media_create_nodes.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "add_media_additional_files.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        if os.path.exists(self.create_log_file_path):
            os.remove(self.create_log_file_path)

        if os.path.exists(self.true_with_additional_files_log_file_path):
            os.remove(self.true_with_additional_files_log_file_path)


class TestUpdateMediaFields(unittest.TestCase):
    """Create a couple nodes plus image media, update the media's field_original_name
    and field_width fields, then confirm they were updated by GETting the media's JSON.
    """

    def SetUp():
        pass

    def TestUpdateMediaFields():
        pass

    def tearDown():
        pass


if __name__ == "__main__":
    unittest.main()
