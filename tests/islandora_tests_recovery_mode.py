"""unittest tests that require a live Drupal at https://islandora.dev. In most cases, the host URL,
   credentials, etc. are in a configuration file referenced in the test.

   This test file contains tests for creating content using "recovery mode".
"""

import sys
import os
from ruamel.yaml import YAML
import requests
import subprocess
import requests
import json
import unittest
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils


class TestCreateRecoveryModeSingleItems(unittest.TestCase):
    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        self.empty_db_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_tests_csv_to_node_id_map.db.empty",
        )
        self.test_db_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_tests_csv_to_node_id_map.db",
        )
        shutil.copyfile(self.empty_db_path, self.test_db_path)

    def test_create(self):
        requests.packages.urllib3.disable_warnings()

        # First create 10 "stale" nodes to populate the CSV ID to node ID map with IDs
        # that will be duplicates of ones created in the next block.
        self.create_stale_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_part.yml",
        )
        self.stale_create_cmd = [
            "./workbench",
            "--config",
            self.create_stale_config_file_path,
        ]

        self.stale_nids = list()
        stale_create_output = subprocess.check_output(self.stale_create_cmd)
        stale_create_output = stale_create_output.decode().strip()
        stale_create_lines = stale_create_output.splitlines()
        for line in stale_create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.stale_nids.append(nid)

        self.assertEqual(len(self.stale_nids), 10)

        # Create 10 nodes to simulate the nodes that were successfully created before
        # the create task got "interruped".
        self.create_part_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_part.yml",
        )
        self.part_create_cmd = [
            "./workbench",
            "--config",
            self.create_part_config_file_path,
        ]

        self.part_nids = list()
        part_create_output = subprocess.check_output(self.part_create_cmd)
        part_create_output = part_create_output.decode().strip()
        part_create_lines = part_create_output.splitlines()
        for line in part_create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.part_nids.append(nid)

        self.assertEqual(len(self.part_nids), 10)

        # Then create 12 more nodes in recovery mode from the same input CSV.
        self.create_full_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_full.yml",
        )
        self.full_create_cmd = [
            "./workbench",
            "--config",
            self.create_full_config_file_path,
            "--recovery_mode_starting_from_node_id",
            self.part_nids[0],
        ]

        self.full_nids = list()
        full_create_output = subprocess.check_output(self.full_create_cmd)
        full_create_output = full_create_output.decode().strip()
        full_create_lines = full_create_output.splitlines()
        for line in full_create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.full_nids.append(nid)

        # If only 12 nodes werer created, recovery mode worked.
        self.assertEqual(len(self.full_nids), 12)

    def tearDown(self):
        for nid in self.stale_nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_part_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        for nid in self.part_nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_part_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        for nid in self.full_nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_full_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        self.preprocessed_part_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_part.csv.preprocessed",
        )
        if os.path.exists(self.preprocessed_part_file_path):
            os.remove(self.preprocessed_part_file_path)

        self.preprocessed_full_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_full.csv.preprocessed",
        )
        if os.path.exists(self.preprocessed_full_file_path):
            os.remove(self.preprocessed_full_file_path)

        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        self.rollback_part_csv_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_part.csv"
        )
        if os.path.exists(self.rollback_part_csv_file_path):
            os.remove(self.rollback_part_csv_file_path)
        self.rollback_part_config_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_part.yml"
        )
        if os.path.exists(self.rollback_part_config_file_path):
            os.remove(self.rollback_part_config_file_path)

        self.rollback_full_csv_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_full.csv"
        )
        if os.path.exists(self.rollback_full_csv_file_path):
            os.remove(self.rollback_full_csv_file_path)
        self.rollback_full_config_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_full.yml"
        )
        if os.path.exists(self.rollback_full_config_file_path):
            os.remove(self.rollback_full_config_file_path)


class TestCreateRecoveryModeSingleItemsWithParentId(unittest.TestCase):
    current_dir = os.path.dirname(os.path.abspath(__file__))

    def setUp(self):
        self.empty_db_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_tests_csv_to_node_id_map.db.empty",
        )
        self.test_db_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_tests_csv_to_node_id_map.db",
        )
        shutil.copyfile(self.empty_db_path, self.test_db_path)

    def test_create(self):
        requests.packages.urllib3.disable_warnings()

        # First create 10 "stale" nodes to populate the CSV ID to node ID map with IDs
        # that will be duplicates of ones created in the next block.
        self.create_stale_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_part_with_parent_id.yml",
        )
        self.stale_create_cmd = [
            "./workbench",
            "--config",
            self.create_stale_config_file_path,
        ]

        self.stale_nids = list()
        stale_create_output = subprocess.check_output(self.stale_create_cmd)
        stale_create_output = stale_create_output.decode().strip()
        stale_create_lines = stale_create_output.splitlines()
        for line in stale_create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.stale_nids.append(nid)

        self.assertEqual(len(self.stale_nids), 10)

        # Create 10 nodes to simulate the nodes that were successfully created before
        # the create task got "interruped".
        self.create_part_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_part_with_parent_id.yml",
        )
        self.part_create_cmd = [
            "./workbench",
            "--config",
            self.create_part_config_file_path,
        ]

        self.part_nids = list()
        part_create_output = subprocess.check_output(self.part_create_cmd)
        part_create_output = part_create_output.decode().strip()
        part_create_lines = part_create_output.splitlines()
        for line in part_create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.part_nids.append(nid)

        self.assertEqual(len(self.part_nids), 10)

        # Then create 12 more nodes in recovery mode from the same input CSV.
        self.create_full_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_full_with_parent_id.yml",
        )
        self.full_create_cmd = [
            "./workbench",
            "--config",
            self.create_full_config_file_path,
            "--recovery_mode_starting_from_node_id",
            self.part_nids[0],
        ]

        self.full_nids = list()
        full_create_output = subprocess.check_output(self.full_create_cmd)
        full_create_output = full_create_output.decode().strip()
        full_create_lines = full_create_output.splitlines()
        for line in full_create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.full_nids.append(nid)

        # If only 12 nodes werer created, recovery mode worked.
        self.assertEqual(len(self.full_nids), 12)

        # Test that the correct parent node ID was assigned to children.
        node_with_children_nid = None
        for node_id in self.part_nids:
            node_url = (
                "https://islandora.dev/node/" + str(node_id) + "?_format=json"
            )
            node_response = requests.get(node_url, verify=False)
            node = json.loads(node_response.text)
            if node["title"][0]["value"].endswith("is parent"):
                node_with_children_nid = node["nid"][0]["value"]

        for node_id in self.full_nids:
            node_url = (
                "https://islandora.dev/node/" + str(node_id) + "?_format=json"
            )
            node_response = requests.get(node_url, verify=False)
            node = json.loads(node_response.text)
            # Check to see whether nodes that are supposed to be children of node titled
            # "Recovery mode test single 008 is parent" do in fact have its node ID in their
            # field_member_of, and whether nodes that are not supposed to be children of
            # that node have nothing in field_member_of
            if node["title"][0]["value"].endswith("is child of 8"):
                self.assertEqual(
                    node["field_member_of"][0]["target_id"], node_with_children_nid
                )
            else:
                self.assertEqual(len(node["field_member_of"]), 0)

    def tearDown(self):
        for nid in self.stale_nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_stale_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        for nid in self.part_nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_part_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        for nid in self.full_nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_full_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        self.preprocessed_part_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_part_with_parent_id.csv.preprocessed",
        )
        if os.path.exists(self.preprocessed_part_file_path):
            os.remove(self.preprocessed_part_file_path)

        self.preprocessed_full_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_single_full_with_parent_id.csv.preprocessed",
        )
        if os.path.exists(self.preprocessed_full_file_path):
            os.remove(self.preprocessed_full_file_path)

        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        self.rollback_part_csv_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_part.csv"
        )
        if os.path.exists(self.rollback_part_csv_file_path):
            os.remove(self.rollback_part_csv_file_path)
        self.rollback_part_config_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_part.yml"
        )
        if os.path.exists(self.rollback_part_config_file_path):
            os.remove(self.rollback_part_config_file_path)

        self.rollback_full_csv_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_full.csv"
        )
        if os.path.exists(self.rollback_full_csv_file_path):
            os.remove(self.rollback_full_csv_file_path)
        self.rollback_full_config_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_full.yml"
        )
        if os.path.exists(self.rollback_full_config_file_path):
            os.remove(self.rollback_full_config_file_path)


class TestCreateRecoveryModePagedItemsFromDirectories(unittest.TestCase):
    current_dir = os.path.dirname(os.path.abspath(__file__))

    empty_db_path = os.path.join(
        current_dir,
        "assets",
        "recovery_mode_test",
        "recovery_mode_tests_csv_to_node_id_map.db.empty",
    )
    test_db_path = os.path.join(
        current_dir,
        "assets",
        "recovery_mode_test",
        "recovery_mode_tests_csv_to_node_id_map.db",
    )

    rollback_part_config_file_path = os.path.join(
        current_dir,
        "assets",
        "recovery_mode_test",
        "rollback_paged_part.yml",
    )
    rollback_full_config_file_path = os.path.join(
        current_dir,
        "assets",
        "recovery_mode_test",
        "rollback_paged_full.yml",
    )

    def setUp(self):
        shutil.copyfile(self.empty_db_path, self.test_db_path)

    def test_create(self):
        requests.packages.urllib3.disable_warnings()

        # First create 2 books, each with 10 pages. to populat the map with  "stale" nodes
        # that will be duplicates of ones created in the next block.
        self.create_stale_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_paged_content_full.yml",
        )
        self.stale_create_cmd = [
            "./workbench",
            "--config",
            self.create_stale_config_file_path,
        ]

        self.stale_nids = list()
        stale_create_output = subprocess.check_output(self.stale_create_cmd)
        stale_create_output = stale_create_output.decode().strip()
        stale_create_lines = stale_create_output.splitlines()
        for line in stale_create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.stale_nids.append(nid)

        self.assertEqual(len(self.stale_nids), 22)

        # Delete these nodes and media. We need to use the rollback.yml here because
        # Drupal may return a node's path, not its node ID.
        self.rollback_stale_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "rollback_paged_full.yml",
        )
        self.rollback_stale_cmd = [
            "./workbench",
            "--config",
            self.rollback_stale_config_file_path,
        ]
        subprocess.check_output(self.rollback_stale_cmd)

        # Then load the "part" content - 1 book node and 6 page nodes.
        self.create_part_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_paged_content_part.yml",
        )
        self.create_part_cmd = [
            "./workbench",
            "--config",
            self.create_part_config_file_path,
        ]

        self.part_nids = list()
        part_create_output = subprocess.check_output(self.create_part_cmd)
        part_create_output = part_create_output.decode().strip()
        part_create_lines = part_create_output.splitlines()
        for line in part_create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.part_nids.append(nid)

        self.assertEqual(len(self.part_nids), 7)

        # Get the 4th line of the rollback_paged_part.csv, which will be the highest node ID created
        # in the "part" ingest (the first line is 'node_id', the 2 lines of comments). We use this to
        # populate the "--recovery_mode_starting_from_node_id" argument.
        rollback_part_csv_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "rollback_paged_part.csv",
        )
        with open(rollback_part_csv_file_path, "r") as f:
            recovery_mode_start_from_node_id = f.readlines()[3].strip()

        # Load all pages in recovery mode.
        recovery_mode_create_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_paged_content_full.yml",
        )
        recovery_mode_create_cmd = [
            "./workbench",
            "--config",
            recovery_mode_create_config_file_path,
            "--recovery_mode_starting_from_node_id",
            recovery_mode_start_from_node_id,
        ]

        recovery_mode_create_nids = list()
        recovery_mode_create_output = subprocess.check_output(recovery_mode_create_cmd)
        recovery_mode_create_output = recovery_mode_create_output.decode().strip()
        recovery_mode_create_lines = recovery_mode_create_output.splitlines()
        for line in recovery_mode_create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                recovery_mode_create_nids.append(nid)

        # If recovery mode worked, only 15 nodes are created.
        self.assertEqual(len(recovery_mode_create_nids), 15)

        # Even though we know the expected number of nodes were created in the part and full
        # create tasks, we need to confirm that the field_member_of in each child node was
        # populated correctly, like we did in TestCreateRecoveryModeSingleItemsWithParentId.

        # Get the lines in the part and full rollback CSV files. These are the
        # node IDs (the *_nids lists above may contain paths, not node ID.).
        with open(rollback_part_csv_file_path, "r") as f:
            rollback_part_csv_file_lines = f.readlines()
            part_nodes_nids = rollback_part_csv_file_lines[3:]

        rollback_full_csv_file_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "rollback_paged_full.csv",
        )
        with open(rollback_full_csv_file_path, "r") as f:
            rollback_fullt_csv_file_lines = f.readlines()
            full_nodes_nids = rollback_fullt_csv_file_lines[3:]

        all_node_ids = part_nodes_nids + full_nodes_nids

        # Get the book node's node IDs
        for node_id in all_node_ids:
            node_url = (
                "https://islandora.dev/node/"
                + str(node_id).strip()
                + "?_format=json"
            )
            node_response = requests.get(node_url, verify=False)
            node = json.loads(node_response.text)
            if node["title"][0]["value"].endswith("book 1 (parent)"):
                book_1_node_id = node_id
            if node["title"][0]["value"].endswith("book 2 (parent)"):
                book_2_node_id = node_id

        for node_id in all_node_ids:
            node_url = (
                "https://islandora.dev/node/"
                + str(node_id).strip()
                + "?_format=json"
            )
            node_response = requests.get(node_url, verify=False)
            node = json.loads(node_response.text)
            # Check to see whether nodes that are supposed to be children of the books
            # do in fact have its node ID in their field_member_of.
            if (
                "book 1" in node["title"][0]["value"]
                and "book 1 (parent)" not in node["title"][0]["value"]
            ):
                self.assertEqual(len(node["field_member_of"]), book_1_node_id)
            if (
                "book 2" in node["title"][0]["value"]
                and "book 2 (parent)" not in node["title"][0]["value"]
            ):
                self.assertEqual(len(node["field_member_of"]), book_2_node_id)

        # Delete the nodes and media created during the "part" ingest.
        rollback_part_cmd = [
            "./workbench",
            "--config",
            self.rollback_part_config_file_path,
        ]
        subprocess.check_output(rollback_part_cmd)

        # Delete the nodes and media created during the "full" ingest.
        rollback_full_cmd = [
            "./workbench",
            "--config",
            self.rollback_full_config_file_path,
        ]
        subprocess.check_output(rollback_full_cmd)

    def tearDown(self):
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

        if os.path.exists(self.rollback_part_config_file_path):
            os.remove(self.rollback_part_config_file_path)

        if os.path.exists(self.rollback_full_config_file_path):
            os.remove(self.rollback_full_config_file_path)

        rollback_part_csv_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_paged_part.csv"
        )
        if os.path.exists(rollback_part_csv_file_path):
            os.remove(rollback_part_csv_file_path)

        rollback_full_csv_file_path = os.path.join(
            self.current_dir, "assets", "recovery_mode_test", "rollback_paged_full.csv"
        )
        if os.path.exists(rollback_full_csv_file_path):
            os.remove(rollback_full_csv_file_path)


if __name__ == "__main__":
    unittest.main()
