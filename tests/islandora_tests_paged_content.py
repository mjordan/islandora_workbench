"""unittest tests that require a live Drupal at https://islandora.dev. In most cases, the host URL,
credentials, etc. are in a configuration file referenced in the test.

This test file contains tests for paged content. Files islandora_tests.py, islandora_tests_paged_check.py,
and islandora_tests_hooks.py also contain tests that interact with an Islandora instance.
"""

import os
import subprocess
import requests
import json

from workbench_test_class import (
    WorkbenchTest,
    collect_nids_from_create_output,
    cleanup_paths,
)


class TestCreatePagedContent(WorkbenchTest):

    def test_create_paged_content(self, workbench_user):
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/create_paged_content_test",
            "nodes_only": True,
            "id_field": "field_local_identifier",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()
        nids = collect_nids_from_create_output(create_output)

        try:
            assert len(nids) == 6

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
            node_url = (
                configuration["host"]
                + "/node/"
                + child_node_id_to_test
                + "?_format=json"
            )
            response = requests.get(node_url, verify=False)
            node_json = json.loads(response.text)
            field_member_of = node_json["field_member_of"][0]["target_id"]

            assert int(parent_node_id_to_test) == field_member_of
        finally:

            for nid in nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_config_file_path,
                    "--quick_delete_node",
                    configuration["host"] + "/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                create_config_file_path,
                os.path.join(self.temp_dir, "metadata.csv.preprocessed"),
                os.path.join(
                    self.current_dir,
                    "assets",
                    "create_paged_content_test",
                    "rollback.csv",
                ),
            )


class TestCreatePagedContentFromDirectories(WorkbenchTest):

    def test_create_paged_content_from_directories(self, workbench_user):
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "paged_content_from_directories": True,
            "paged_content_page_model_tid": "http://id.loc.gov/ontologies/bibframe/part",
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/create_paged_content_from_directories_test/samplebooks",
            "standalone_media_url": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()
        nids = collect_nids_from_create_output(create_output)

        try:
            assert len(nids) == 4

            # Test a page object's 'field_member_of' value to see if it matches its
            # parent's node ID. In this test, we'll test the second page. Note: the
            # metadata CSV file used to create the paged content and page objects
            # uses hard-coded term IDs from the Islandora Models taxonomy as used
            # in the Islandora Playbook. If they change or are different in the
            # Islandora this test is running against, this test will fail. Also note
            # that this test creates media and does not delete them.
            parent_node_id_to_test = nids[0]
            # Get the REST feed for the parent node's members.
            members_url = (
                configuration["host"]
                + "/node/"
                + parent_node_id_to_test
                + "/members?_format=json"
            )
            # Need to provide credentials for this REST export.
            members_response = requests.get(
                members_url,
                auth=(configuration["username"], configuration["password"]),
                verify=False,
            )
            members = json.loads(members_response.text)

            expected_member_weights = [1, 2, 3]
            retrieved_member_weights = list()
            for member in members:
                retrieved_member_weights.append(int(member["field_weight"][0]["value"]))
                # Test that each page indeed a member of the first node created during this test.
                assert int(parent_node_id_to_test) == int(
                    member["field_member_of"][0]["target_id"]
                )

            # Test that the weights assigned to the three pages are what we expect.
            assert expected_member_weights == retrieved_member_weights
        finally:

            for nid in nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_config_file_path,
                    "--quick_delete_node",
                    f"{configuration['host']}/node/{nid}",
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                create_config_file_path,
                os.path.join(self.temp_dir, "metadata.csv.preprocessed"),
                os.path.join(
                    self.current_dir,
                    "assets",
                    "create_paged_content_from_directories_test",
                    "samplebooks",
                    "rollback.csv",
                ),
            )


class TestCreatePagedContentFromDirectoriesPageFilesSourceDirField(WorkbenchTest):

    def test_create_paged_content_from_directories(self, workbench_user):
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "paged_content_from_directories": True,
            "paged_content_page_model_tid": "http://id.loc.gov/ontologies/bibframe/part",
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/create_paged_content_from_directories_test/samplebooks",
            "input_csv": "metadata_page_files_source_dir_field.csv",
            "standalone_media_url": True,
            "secure_ssl_only": False,
            "page_files_source_dir_field": "directory",
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()
        nids = collect_nids_from_create_output(create_output)

        try:
            assert len(nids) == 4

            # Test a page object's 'field_member_of' value to see if it matches its
            # parent's node ID. In this test, we'll test the second page. Note: the
            # metadata CSV file used to create the paged content and page objects
            # uses hard-coded term IDs from the Islandora Models taxonomy as used
            # in the Islandora Playbook. If they change or are different in the
            # Islandora this test is running against, this test will fail. Also note
            # that this test creates media and does not delete them.
            parent_node_id_to_test = nids[0]
            # Get the REST feed for the parent node's members.
            members_url = (
                configuration["host"]
                + "/node/"
                + parent_node_id_to_test
                + "/members?_format=json"
            )
            # Need to provide credentials for this REST export.
            members_response = requests.get(
                members_url,
                auth=(configuration["username"], configuration["password"]),
                verify=False,
            )
            members = json.loads(members_response.text)

            expected_member_weights = [1, 2, 3]
            retrieved_member_weights = list()
            for member in members:
                retrieved_member_weights.append(int(member["field_weight"][0]["value"]))
                # Test that each page indeed a member of the first node created during this test.
                assert int(parent_node_id_to_test) == int(
                    member["field_member_of"][0]["target_id"]
                )

            # Test that the weights assigned to the three pages are what we expect.
            assert expected_member_weights == retrieved_member_weights
        finally:

            for nid in nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_config_file_path,
                    "--quick_delete_node",
                    f"{configuration['host']}/node/{nid}",
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                create_config_file_path,
                os.path.join(
                    self.temp_dir,
                    "metadata_page_files_source_dir_field.csv.preprocessed",
                ),
                os.path.join(
                    self.current_dir,
                    "assets",
                    "create_paged_content_from_directories_test",
                    "samplebooks",
                    "rollback.csv",
                ),
            )
