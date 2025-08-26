"""unittest tests that require a live Drupal at https://islandora.dev. In most cases, the host URL,
credentials, etc. are in a configuration file referenced in the test.

This test file contains tests for creating content using "recovery mode".
"""

import os
import subprocess
import tempfile

import pytest
import requests
import json
import shutil

from workbench_test_class import (
    WorkbenchTest,
    collect_nids_from_create_output,
    cleanup_paths,
)


class TestCreateRecoveryMode(WorkbenchTest):

    @pytest.fixture
    def setup_test(self):

        empty_db_path = os.path.join(
            self.current_dir,
            "assets",
            "recovery_mode_test",
            "recovery_mode_tests_csv_to_node_id_map.db.empty",
        )
        test_db_path = tempfile.mkstemp(
            dir=self.temp_dir, suffix="_recovery_mode_tests_csv_to_node_id_map.db"
        )[1]
        shutil.copyfile(empty_db_path, test_db_path)

        yield {"test_db_path": test_db_path}

        cleanup_paths(test_db_path)

    def test_create_single_items(self, setup_test, workbench_user):
        requests.packages.urllib3.disable_warnings()

        # First create 10 "stale" nodes to populate the CSV ID to node ID map with IDs
        # that will be duplicates of ones created in the next block.
        part_configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/recovery_mode_test",
            "input_csv": "recovery_mode_single_part.csv",
            "csv_id_to_node_id_map_path": setup_test["test_db_path"],
            "rollback_config_file_path": "tests/assets/recovery_mode_test/rollback_part_single.yml",
            "rollback_csv_file_path": "tests/assets/recovery_mode_test/rollback_part_single.csv",
            "include_password_in_rollback_config_file": True,
            "secure_ssl_only": False,
            "nodes_only": True,
        }
        part_configuration = workbench_user.alter_configuration(part_configuration)
        create_stale_config_file_path = self.write_config_and_get_path(
            part_configuration
        )
        stale_create_cmd = [
            "./workbench",
            "--config",
            create_stale_config_file_path,
        ]

        stale_create_output = subprocess.check_output(
            stale_create_cmd, cwd=self.workbench_dir
        )
        stale_create_output = stale_create_output.decode().strip()

        stale_nids = collect_nids_from_create_output(stale_create_output)

        # These are variables we need in the "finally" block below, which might not be set in the try block.
        part_nids = []
        create_full_config_file_path = ""
        full_nids = []
        try:
            assert len(stale_nids) == 10

            # Create 10 nodes to simulate the nodes that were successfully created before
            # the create task got "interrupted". This uses exact same configuration as above.
            part_create_cmd = [
                "./workbench",
                "--config",
                create_stale_config_file_path,
            ]

            part_create_output = subprocess.check_output(
                part_create_cmd, cwd=self.workbench_dir
            )
            part_create_output = part_create_output.decode().strip()

            part_nids = collect_nids_from_create_output(part_create_output)

            assert len(part_nids) == 10

            # Then create 12 more nodes in recovery mode from the same input CSV.
            full_configuration = {
                "task": "create",
                "host": "https://islandora.dev",
                "input_dir": "tests/assets/recovery_mode_test",
                "input_csv": "recovery_mode_single_full.csv",
                "csv_id_to_node_id_map_path": setup_test["test_db_path"],
                "rollback_config_file_path": "tests/assets/recovery_mode_test/rollback_full_single.yml",
                "rollback_csv_file_path": "tests/assets/recovery_mode_test/rollback_full_single.csv",
                "include_password_in_rollback_config_file": True,
                "secure_ssl_only": False,
                "nodes_only": True,
            }
            full_configuration = workbench_user.alter_configuration(full_configuration)
            create_full_config_file_path = self.write_config_and_get_path(
                full_configuration
            )

            full_create_cmd = [
                "./workbench",
                "--config",
                create_full_config_file_path,
                "--recovery_mode_starting_from_node_id",
                part_nids[0],
            ]

            full_create_output = subprocess.check_output(
                full_create_cmd, cwd=self.workbench_dir
            )
            full_create_output = full_create_output.decode().strip()
            full_nids = collect_nids_from_create_output(full_create_output)

            # If only 12 nodes were created, recovery mode worked.
            assert len(full_nids) == 12
        finally:

            for nid in stale_nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_stale_config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            for nid in part_nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_stale_config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd)

            for nid in full_nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_full_config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_part_single.yml",
                ),
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_part_single.csv",
                ),
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_full_single.yml",
                ),
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_full_single.csv",
                ),
                create_stale_config_file_path,
                create_full_config_file_path,
            )

    def test_create_single_with_parent_id(self, setup_test, workbench_user):
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/recovery_mode_test",
            "input_csv": "recovery_mode_single_part_with_parent_id.csv",
            "csv_id_to_node_id_map_path": setup_test["test_db_path"],
            "rollback_config_file_path": "tests/assets/recovery_mode_test/rollback_part_single_id.yml",
            "rollback_csv_file_path": "tests/assets/recovery_mode_test/rollback_part_single_id.csv",
            "include_password_in_rollback_config_file": True,
            "secure_ssl_only": False,
            "nodes_only": True,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_stale_config_file_path = self.write_config_and_get_path(configuration)

        # First create 10 "stale" nodes to populate the CSV ID to node ID map with IDs
        # that will be duplicates of ones created in the next block.
        stale_create_cmd = [
            "./workbench",
            "--config",
            create_stale_config_file_path,
        ]

        stale_create_output = subprocess.check_output(
            stale_create_cmd, cwd=self.workbench_dir
        )
        stale_create_output = stale_create_output.decode().strip()
        stale_nids = collect_nids_from_create_output(stale_create_output)

        # These are variables we need in the "finally" block below, which might not be set in the try block.
        part_nids = []
        create_full_config_file_path = ""
        full_nids = []
        try:
            assert len(stale_nids) == 10

            # Create 10 nodes to simulate the nodes that were successfully created before
            # the create task got "interrupted". Uses exact same configuration as above.
            part_create_cmd = [
                "./workbench",
                "--config",
                create_stale_config_file_path,
            ]

            part_create_output = subprocess.check_output(
                part_create_cmd, cwd=self.workbench_dir
            )
            part_create_output = part_create_output.decode().strip()
            part_nids = collect_nids_from_create_output(part_create_output)

            assert len(part_nids) == 10

            # Then create 12 more nodes in recovery mode from the same input CSV.
            full_configuration = {
                "task": "create",
                "host": "https://islandora.dev",
                "input_dir": "tests/assets/recovery_mode_test",
                "input_csv": "recovery_mode_single_full_with_parent_id.csv",
                "csv_id_to_node_id_map_path": setup_test["test_db_path"],
                "rollback_config_file_path": "tests/assets/recovery_mode_test/rollback_full_single_id.yml",
                "rollback_csv_file_path": "tests/assets/recovery_mode_test/rollback_full_single_id.csv",
                "include_password_in_rollback_config_file": True,
                "secure_ssl_only": False,
                "nodes_only": True,
            }
            full_configuration = workbench_user.alter_configuration(full_configuration)
            create_full_config_file_path = self.write_config_and_get_path(
                full_configuration
            )

            full_create_cmd = [
                "./workbench",
                "--config",
                create_full_config_file_path,
                "--recovery_mode_starting_from_node_id",
                part_nids[0],
            ]

            full_create_output = subprocess.check_output(
                full_create_cmd, cwd=self.workbench_dir
            )
            full_create_output = full_create_output.decode().strip()
            full_nids = collect_nids_from_create_output(full_create_output)

            # If only 12 nodes were created, recovery mode worked.
            assert len(full_nids) == 12

            # Test that the correct parent node ID was assigned to children.
            node_with_children_nid = None
            for node_id in part_nids:
                node_url = (
                    "https://islandora.dev/node/" + str(node_id) + "?_format=json"
                )
                node_response = requests.get(node_url, verify=False)
                node = json.loads(node_response.text)
                if node["title"][0]["value"].endswith("is parent"):
                    node_with_children_nid = node["nid"][0]["value"]

            for node_id in full_nids:
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
                    assert (
                        node["field_member_of"][0]["target_id"]
                        == node_with_children_nid
                    )
                else:
                    assert len(node["field_member_of"]) == 0
        finally:
            for nid in stale_nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_stale_config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            for nid in part_nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_stale_config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            for nid in full_nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_full_config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_part_single_id.yml",
                ),
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_part_single_id.csv",
                ),
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_full_single_id.csv",
                ),
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_full_single_id.yml",
                ),
                create_stale_config_file_path,
                create_full_config_file_path,
            )

    def test_create_paged_items_from_directories(self, setup_test, workbench_user):
        requests.packages.urllib3.disable_warnings()

        configuration = {
            "paged_content_from_directories": True,
            "paged_content_page_model_tid": "http://id.loc.gov/ontologies/bibframe/part",
            "paged_content_sequence_separator": "_",
            "paged_content_image_file_extension": "gif",
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/recovery_mode_test/pages_from_directories_full",
            "csv_id_to_node_id_map_path": setup_test["test_db_path"],
            "rollback_config_file_path": "tests/assets/recovery_mode_test/rollback_paged_full.yml",
            "rollback_csv_file_path": "tests/assets/recovery_mode_test/rollback_paged_full.csv",
            "include_password_in_rollback_config_file": True,
            "standalone_media_url": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_stale_config_file_path = self.write_config_and_get_path(configuration)

        # First create 2 books, each with 10 pages. to populate the map with "stale" nodes
        # that will be duplicates of ones created in the next block.
        stale_create_cmd = [
            "./workbench",
            "--config",
            create_stale_config_file_path,
        ]

        stale_create_output = subprocess.check_output(
            stale_create_cmd, cwd=self.workbench_dir
        )
        stale_create_output = stale_create_output.decode().strip()
        stale_nids = collect_nids_from_create_output(stale_create_output)

        # These are variables we need in the "finally" block below, which might not be set in the try block.
        create_part_config_file_path = ""
        try:
            assert len(stale_nids) == 22

            # Delete these nodes and media. We need to use the rollback.yml here because
            # Drupal may return a node's path, not its node ID.
            rollback_stale_config_file_path = os.path.join(
                self.current_dir,
                "assets",
                "recovery_mode_test",
                "rollback_paged_full.yml",
            )
            rollback_stale_cmd = [
                "./workbench",
                "--config",
                rollback_stale_config_file_path,
            ]
            subprocess.check_output(rollback_stale_cmd, cwd=self.workbench_dir)

            # Then load the "part" content - 1 book node and 6 page nodes.
            part_configuration = {
                "paged_content_from_directories": True,
                "paged_content_page_model_tid": "http://id.loc.gov/ontologies/bibframe/part",
                "paged_content_sequence_separator": "_",
                "paged_content_image_file_extension": "gif",
                "task": "create",
                "host": "https://islandora.dev",
                "input_dir": "tests/assets/recovery_mode_test/pages_from_directories_part",
                "csv_id_to_node_id_map_path": setup_test["test_db_path"],
                "rollback_config_file_path": "tests/assets/recovery_mode_test/rollback_paged_part.yml",
                "rollback_csv_file_path": "tests/assets/recovery_mode_test/rollback_paged_part.csv",
                "include_password_in_rollback_config_file": True,
                "standalone_media_url": True,
                "secure_ssl_only": False,
            }
            part_configuration = workbench_user.alter_configuration(part_configuration)
            create_part_config_file_path = self.write_config_and_get_path(
                part_configuration
            )
            create_part_cmd = [
                "./workbench",
                "--config",
                create_part_config_file_path,
            ]

            part_create_output = subprocess.check_output(
                create_part_cmd, cwd=self.workbench_dir
            )
            part_create_output = part_create_output.decode().strip()
            part_nids = collect_nids_from_create_output(part_create_output)

            assert len(part_nids) == 7

            # Get the 4th line of the rollback_paged_part.csv, which will be the highest node ID created
            # in the "part" ingest (the first line is 'node_id', then 2 lines of comments). We use this to
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
            recovery_mode_create_configuration = {
                "paged_content_from_directories": True,
                "paged_content_page_model_tid": "http://id.loc.gov/ontologies/bibframe/part",
                "paged_content_sequence_separator": "_",
                "paged_content_image_file_extension": "gif",
                "task": "create",
                "host": "https://islandora.dev",
                "input_dir": "tests/assets/recovery_mode_test/pages_from_directories_full",
                "csv_id_to_node_id_map_path": setup_test["test_db_path"],
                "rollback_config_file_path": "tests/assets/recovery_mode_test/rollback_paged_full.yml",
                "rollback_csv_file_path": "tests/assets/recovery_mode_test/rollback_paged_full.csv",
                "include_password_in_rollback_config_file": True,
                "standalone_media_url": True,
                "secure_ssl_only": False,
            }
            recovery_mode_create_configuration = workbench_user.alter_configuration(
                recovery_mode_create_configuration
            )
            recovery_mode_create_config_file_path = self.write_config_and_get_path(
                recovery_mode_create_configuration
            )
            recovery_mode_create_cmd = [
                "./workbench",
                "--config",
                recovery_mode_create_config_file_path,
                "--recovery_mode_starting_from_node_id",
                recovery_mode_start_from_node_id,
            ]

            recovery_mode_create_output = subprocess.check_output(
                recovery_mode_create_cmd, cwd=self.workbench_dir
            )
            recovery_mode_create_output = recovery_mode_create_output.decode().strip()
            recovery_mode_create_nids = collect_nids_from_create_output(
                recovery_mode_create_output
            )

            # If recovery mode worked, only 15 nodes are created.
            assert len(recovery_mode_create_nids) == 15

            # Even though we know the expected number of nodes were created in the part and full
            # create tasks, we need to confirm that the field_member_of in each child node was
            # populated correctly, like we did in TestCreateRecoveryModeSingleItemsWithParentId().

            # Get the lines in the part and full rollback CSV files. These are the
            # node IDs (the *_nids lists above may contain URL aliases, not node IDs).
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

            # Get the two book nodes' node IDs.
            for node_id in all_node_ids:
                node_url = (
                    "https://islandora.dev/node/"
                    + str(node_id).strip()
                    + "?_format=json"
                )
                node_response = requests.get(node_url, verify=False)

                assert node_response.status_code == 200

                node = json.loads(node_response.text)
                if node["title"][0]["value"].endswith("book 1 (parent)"):
                    book_1_node_id = node_id
                elif node["title"][0]["value"].endswith("book 2 (parent)"):
                    book_2_node_id = node_id
                try:
                    x = book_1_node_id
                    y = book_2_node_id
                    # If we got both node IDs, no need to keep looping.
                    break
                except UnboundLocalError:
                    pass

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
                    assert len(node["field_member_of"]) == book_1_node_id
                if (
                    "book 2" in node["title"][0]["value"]
                    and "book 2 (parent)" not in node["title"][0]["value"]
                ):
                    assert len(node["field_member_of"]) == book_2_node_id
        finally:
            # Delete the nodes and media created during the "part" ingest.
            rollback_part_config_file_path = os.path.join(
                self.current_dir,
                "assets",
                "recovery_mode_test",
                "rollback_paged_part.yml",
            )
            rollback_part_cmd = [
                "./workbench",
                "--config",
                rollback_part_config_file_path,
            ]
            subprocess.check_output(rollback_part_cmd, cwd=self.workbench_dir)

            # Delete the nodes and media created during the "full" ingest.
            rollback_full_config_file_path = os.path.join(
                self.current_dir,
                "assets",
                "recovery_mode_test",
                "rollback_paged_full.yml",
            )
            rollback_full_cmd = [
                "./workbench",
                "--config",
                rollback_full_config_file_path,
            ]
            subprocess.check_output(rollback_full_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_paged_part.yml",
                ),
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_paged_part.csv",
                ),
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_paged_full.yml",
                ),
                os.path.join(
                    self.current_dir,
                    "assets/recovery_mode_test/rollback_paged_full.csv",
                ),
                create_stale_config_file_path,
                create_part_config_file_path,
            )
