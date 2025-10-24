"""unittest tests that require a live Drupal at https://islandora.dev. In most cases, the host URL,
credentials, etc. are in a configuration file referenced in the test.

Files islandora_tests_check.py, islandora_tests_paged_content.py, and islandora_tests_hooks.py also
contain tests that interact with an Islandora instance.
"""

import sys
import os
import csv
import glob
import tempfile

import pytest
import subprocess
import argparse
import requests
import json
import unittest
import time
import copy
import re
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils
from WorkbenchConfig import WorkbenchConfig
from workbench_test_class import (
    WorkbenchTest,
    collect_nids_from_create_output,
    cleanup_paths,
)


class TestCreate(WorkbenchTest):

    def test_create(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/create_test",
            "media_type": "image",
            "allow_missing_files": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)

        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()
        nids = collect_nids_from_create_output(create_output)

        try:
            assert len(nids) == 2
        finally:
            for nid in nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                create_config_file_path,
                os.path.join(
                    self.current_dir,
                    "assets",
                    "create_test",
                    "metadata.csv.preprocessed",
                ),
                os.path.join(self.current_dir, "assets", "create_test", "rollback.csv"),
            )


class TestCreateFromFiles(WorkbenchTest):

    def test_create_from_files(self, workbench_user):
        configuration = {
            "task": "create_from_files",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/create_from_files_test/files",
            "models": [
                {"http://purl.org/coar/resource_type/c_1843": ["zip", "tar", ""]},
                {
                    "https://schema.org/DigitalDocument": [
                        "pdf",
                        "doc",
                        "docx",
                        "ppt",
                        "pptx",
                    ]
                },
                {
                    "http://purl.org/coar/resource_type/c_c513": [
                        "tif",
                        "tiff",
                        "jp2",
                        "png",
                        "gif",
                        "jpg",
                        "jpeg",
                    ]
                },
            ],
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
            assert len(nids) == 3
        finally:
            for nid in nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                create_config_file_path,
                os.path.join(
                    self.current_dir,
                    "assets",
                    "create_from_files_test",
                    "files",
                    "rollback.csv",
                ),
            )


class TestCreateWithMaxNodeTitleLength(WorkbenchTest):

    def test_create(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/max_node_title_length_test",
            "input_csv": "create_max_node_title_length.csv",
            "nodes_only": True,
            "max_node_title_length": 30,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()
        output_lines = copy.copy(create_output)
        nids = collect_nids_from_create_output(create_output)

        try:
            assert re.search(
                '"This here title is 32 chars lo" .record 03', output_lines
            )
            assert re.search(
                '"This here title is 34 chars lo" .record 04', output_lines
            )
            assert re.search(
                '"This here title is 36 chars lo" .record 05', output_lines
            )
            assert re.search('"This title is 28 chars long." .record 06', output_lines)
            assert (
                len(nids) == 6
            ), f"Expected 6 nodes to be created, but got {len(nids)}"
        finally:
            for nid in nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    create_config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                os.path.join(
                    self.temp_dir, "create_max_node_title_length.csv.preprocessed"
                ),
                os.path.join(
                    self.current_dir,
                    "assets",
                    "max_node_title_length_test",
                    "rollback.csv",
                ),
                create_config_file_path,
            )


class TestUpdateWithMaxNodeTitleLength(WorkbenchTest):

    @pytest.fixture
    def setup_nodes(self, workbench_user):
        requests.packages.urllib3.disable_warnings()

        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/max_node_title_length_test",
            "input_csv": "create_max_node_title_length.csv",
            "nodes_only": True,
            "max_node_title_length": 30,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]

        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()
        nids = collect_nids_from_create_output(create_output)

        assert len(nids) == 6

        # Write out an update CSV file using the node IDs in self.nids.
        test_titles = [
            "This title is 37 chars___________long",
            "This title is 39 chars_____________long",
            "This title is 29 _ chars long",
            "This title is 42 chars________________long",
            "This title is 44 chars__________________long",
            "This title is 28 chars long.",
        ]

        with tempfile.NamedTemporaryFile(
            mode="wt", delete=False, suffix="_update_max_node_title_length.csv"
        ) as update_csv_file:
            update_csv_file.write("node_id,title\n")
            for i in range(0, 5):
                update_csv_file.write(f"{nids[i]},{test_titles[i]}\n")
            update_csv_file_name = update_csv_file.name

        # This is where the test runs from.
        yield {
            "update_csv_file_path": update_csv_file_name,
            "nids": nids,
            "workbench_user": workbench_user,
        }

        for nid in nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                create_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        cleanup_paths(
            update_csv_file_name,
            os.path.join(
                self.current_dir,
                "assets",
                "max_node_title_length_test",
                "rollback.csv",
            ),
            os.path.join(
                self.temp_dir, "create_max_node_title_length.csv.preprocessed"
            ),
            create_config_file_path,
        )

    def test_update(self, setup_nodes):
        configuration = {
            "task": "update",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/max_node_title_length_test",
            "input_csv": setup_nodes["update_csv_file_path"],
            "max_node_title_length": 30,
            "secure_ssl_only": False,
        }
        configuration = setup_nodes["workbench_user"].alter_configuration(configuration)
        update_config_file_path = self.write_config_and_get_path(configuration)
        update_cmd = ["./workbench", "--config", update_config_file_path]
        # Run the update command.
        subprocess.check_output(update_cmd, cwd=self.workbench_dir)

        # Fetch each node created in setup_nodes and check to see if its title is <= 30 chars long. All should be.
        try:
            for nid_to_update in setup_nodes["nids"]:
                node_url = (
                    "https://islandora.dev/node/" + str(nid_to_update) + "?_format=json"
                )
                node_response = requests.get(node_url, verify=False)
                node = json.loads(node_response.text)
                updated_title = str(node["title"][0]["value"])
                assert (
                    len(updated_title) <= 30
                ), f"Node {nid_to_update} title is longer than 30 characters: {updated_title}"
        finally:
            # delete the update .preprocessed file and config file.
            cleanup_paths(
                os.path.join(
                    self.temp_dir, "update_max_node_title_length.csv.preprocessed"
                ),
                update_config_file_path,
            )


class TestCreateWithNewTypedRelation(WorkbenchTest):

    def test_create_with_new_typed_relation(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/typed_relation_test/input_data",
            "input_csv": "create_with_new_typed_relation.csv",
            "nodes_only": True,
            "allow_adding_terms": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        config_file_path = self.write_config_and_get_path(configuration)

        create_cmd = ["./workbench", "--config", config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()

        namespace = argparse.Namespace()
        namespace.config = config_file_path
        namespace.check = False
        namespace.get_csv_template = None
        workbench_config = WorkbenchConfig(namespace)
        config = workbench_config.get_config()

        nids = collect_nids_from_create_output(create_output)

        try:
            assert len(nids) == 1

            term_id = workbench_utils.find_term_in_vocab(
                config, "person", "Kirk, James T."
            )
            assert term_id is not False

            term_endpoint = (
                configuration["host"]
                + "/taxonomy/term/"
                + str(term_id)
                + "?_format=json"
            )
            workbench_utils.issue_request(config, "DELETE", term_endpoint)
        finally:
            for nid in nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    config_file_path,
                    "--quick_delete_node",
                    configuration["host"] + "/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                os.path.join(
                    self.temp_dir, "create_with_new_typed_relation.csv.preprocessed"
                ),
                config_file_path,
            )


class TestDelete(WorkbenchTest):

    @pytest.fixture
    def setup_nodes(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/delete_test",
            "allow_missing_files": True,
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)

        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()

        nids = collect_nids_from_create_output(create_output)

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix="_workbenchdeletetestnids.txt"
        ) as nid_file:
            nids_to_delete_file_path = nid_file.name
            nid_file.write("node_id\n")
            for nid in nids:
                if workbench_utils.value_is_numeric(nid):
                    nid_file.write(f"{nid}\n")

        yield {
            "nids_to_delete_file_path": nids_to_delete_file_path,
            "nids": nids,
            "workbench_user": workbench_user,
        }

        cleanup_paths(
            nids_to_delete_file_path,
            nids_to_delete_file_path + ".preprocessed",
            create_config_file_path,
        )

    def test_delete(self, setup_nodes):
        configuration = {
            "task": "delete",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/delete_test",
            "input_csv": setup_nodes["nids_to_delete_file_path"],
            "secure_ssl_only": False,
        }
        configuration = setup_nodes["workbench_user"].alter_configuration(configuration)
        delete_config_file_path = self.write_config_and_get_path(configuration)
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd, cwd=self.workbench_dir)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()

        try:
            assert len(delete_lines) == 5

            for nid in setup_nodes["nids"]:
                node_url = "https://islandora.dev/node/" + str(nid) + "?_format=json"
                response = requests.get(node_url, verify=False)
                assert response.status_code == 404, f"Node {nid} was not deleted."
        finally:
            cleanup_paths(delete_config_file_path)


class TestUpdate(WorkbenchTest):

    @pytest.fixture
    def setup_nodes(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/update_test",
            "input_csv": "create.csv",
            "allow_missing_files": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]

        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()

        nids = collect_nids_from_create_output(create_output)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix="_workbenchupdatetestnids.txt"
        ) as nids_fh:
            nid_file_path = nids_fh.name
            nids_fh.write("node_id\n")
            for nid in nids:
                if workbench_utils.value_is_numeric(nid):
                    nids_fh.write(nid + "\n")

        # Add some values to the update CSV file to test against.
        with tempfile.NamedTemporaryFile(
            mode="a", delete=False, suffix="_workbenchupdatetest.csv"
        ) as update_fh:
            update_metadata_file_path = update_fh.name
            update_fh.write("node_id,field_identifier,field_coordinates\n")
            update_fh.write(f'{nids[0]},identifier-0001,"99.1,-123.2"')

        yield {
            "update_metadata_file_path": update_metadata_file_path,
            "nids": nids,
            "workbench_user": workbench_user,
        }

        configuration = {
            "task": "delete",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/update_test",
            "input_csv": nid_file_path,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        delete_config_file_path = self.write_config_and_get_path(configuration)
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        subprocess.check_output(delete_cmd, cwd=self.workbench_dir)

        cleanup_paths(
            nid_file_path,
            update_metadata_file_path,
            os.path.join(
                self.temp_dir, os.path.basename(nid_file_path) + ".preprocessed"
            ),
            os.path.join(
                self.temp_dir,
                os.path.basename(update_metadata_file_path) + ".preprocessed",
            ),
            os.path.join(self.temp_dir, "create.csv.preprocessed"),
            os.path.join(self.current_dir, "assets", "update_test", "rollback.csv"),
            create_config_file_path,
            delete_config_file_path,
        )

    def test_update(self, setup_nodes):
        requests.packages.urllib3.disable_warnings()
        # Run update task.
        time.sleep(5)  # ??
        configuration = {
            "task": "update",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/update_test",
            "input_csv": setup_nodes["update_metadata_file_path"],
            "validate_title_length": False,
            "secure_ssl_only": False,
        }
        configuration = setup_nodes["workbench_user"].alter_configuration(configuration)
        update_config_file_path = self.write_config_and_get_path(configuration)
        update_cmd = ["./workbench", "--config", update_config_file_path]
        subprocess.check_output(update_cmd, cwd=self.workbench_dir)

        # Confirm that fields have been updated.
        url = (
            configuration["host"]
            + "/node/"
            + str(setup_nodes["nids"][0])
            + "?_format=json"
        )
        response = requests.get(url, verify=False)
        node = json.loads(response.text)
        try:
            identifier = str(node["field_identifier"][0]["value"])
            assert identifier == "identifier-0001"
            coodinates = str(node["field_coordinates"][0]["lat"])
            assert coodinates == "99.1"
        finally:
            cleanup_paths(update_config_file_path)


class TestImageAltText(WorkbenchTest):

    @pytest.fixture
    def setup_nodes(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/alt_text_test",
            "input_csv": "alt_text_test_create.csv",
            "secure_ssl_only": False,
            "standalone_media_url": True,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)

        create_cmd = ["./workbench", "--config", create_config_file_path]

        create_output = subprocess.check_output(create_cmd)
        create_output = create_output.decode().strip()

        nids = collect_nids_from_create_output(create_output)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix="_alt_text_test_update_replace.csv"
        ) as fh:
            fh.write("node_id,image_alt_text\n")
            update_csv_path = fh.name
            for nid in nids:
                if workbench_utils.value_is_numeric(nid):
                    fh.write(nid + ",A medieval cat")

        yield {
            "update_csv_path": update_csv_path,
            "nids": nids,
            "workbench_user": workbench_user,
        }

        for nid in nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                create_config_file_path,
                "--quick_delete_node",
                configuration["host"] + "/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        cleanup_paths(
            create_config_file_path,
            update_csv_path,
            os.path.join(
                TestImageAltText.current_dir,
                "assets",
                "alt_text_test",
                "rollback.csv",
            ),
        )

    @unittest.skipIf(
        "GITHUB_ACTIONS" in os.environ,
        "Passes when tests locally run but not in Github workflows.",
    )
    def test_update_alt_text(self, setup_nodes):
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "task": "update_alt_text",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/alt_text_test",
            "input_csv": setup_nodes["update_csv_path"],
            "secure_ssl_only": False,
            "standalone_media_url": True,
        }
        configuration = setup_nodes["workbench_user"].alter_configuration(configuration)
        update_config_file_path = self.write_config_and_get_path(configuration)
        update_cmd = ["./workbench", "--config", update_config_file_path]
        subprocess.check_output(update_cmd, cwd=self.workbench_dir)

        media_list_url = (
            f"{configuration['host']}/node/{setup_nodes['nids'][0]}/media?_format=json"
        )
        media_list_response = requests.get(
            media_list_url,
            auth=(configuration["username"], configuration["password"]),
            verify=False,
        )
        media_list = json.loads(media_list_response.text)

        try:
            for media in media_list:
                if media["bundle"][0]["target_id"] == "image":
                    if "field_media_image" in media:
                        alt_text = media["field_media_image"][0]["alt"]
                        assert alt_text == "A medieval cat"
        finally:
            cleanup_paths(update_config_file_path)


class TestCreateWithNonLatinText(WorkbenchTest):

    def test_create_with_non_latin_text(self, workbench_user):
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/non_latin_text_test",
            "allow_missing_files": True,
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]

        create_output = subprocess.check_output(create_cmd)
        create_output = create_output.decode().strip()

        nids = collect_nids_from_create_output(create_output)
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix="_workbenchcreatenonlatintestnids.txt"
        ) as fh:
            nid_file = fh.name
            fh.write("node_id\n")
            for nid in nids:
                if workbench_utils.value_is_numeric(nid):
                    fh.write(nid + "\n")

        try:
            assert len(nids) == 3

            url = configuration["host"] + "/node/" + str(nids[0]) + "?_format=json"
            response = requests.get(url, verify=False)
            node = json.loads(response.text)
            title = str(node["title"][0]["value"])
            assert title == "一九二四年六月十二日"

            url = configuration["host"] + "/node/" + str(nids[1]) + "?_format=json"
            response = requests.get(url, verify=False)
            node = json.loads(response.text)
            title = str(node["title"][0]["value"])
            assert title == "सरकारी दस्तावेज़"

            url = configuration["host"] + "/node/" + str(nids[2]) + "?_format=json"
            response = requests.get(url, verify=False)
            node = json.loads(response.text)
            title = str(node["title"][0]["value"])
            assert title == "ᐊᑕᐅᓯᖅ ᓄᓇ, ᐅᓄᖅᑐᑦ ᓂᐲᑦ"
        finally:
            configuration = {
                "task": "delete",
                "host": "https://islandora.dev",
                "input_dir": "tests/assets/non_latin_text_test",
                "input_csv": nid_file,
                "secure_ssl_only": False,
            }
            configuration = workbench_user.alter_configuration(configuration)
            delete_config_file_path = self.write_config_and_get_path(configuration)
            delete_cmd = ["./workbench", "--config", delete_config_file_path]
            subprocess.check_output(delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                create_config_file_path,
                delete_config_file_path,
                nid_file,
                nid_file + ".preprocessed",
                os.path.join(
                    self.current_dir,
                    "assets",
                    "non_latin_text_test",
                    "rollback.csv",
                ),
                os.path.join(
                    self.current_dir,
                    "assets",
                    "non_latin_text_test",
                    "metadata.csv.preprocessed",
                ),
            )


class TestSecondaryTask(WorkbenchTest):
    """Test the secondary task functionality in Workbench."""

    def test_secondary_task(self, workbench_user):
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/secondary_task_test",
            "nodes_only": True,
            "csv_field_templates": [
                {"field_model": "https://schema.org/DigitalDocument"}
            ],
            "input_csv": "secondary.csv",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        secondary_config_file_path = self.write_config_and_get_path(configuration)
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/secondary_task_test",
            "nodes_only": True,
            "secondary_tasks": [secondary_config_file_path],
            "csv_field_templates": [
                {"field_model": "https://schema.org/DigitalDocument"}
            ],
            "input_csv": "metadata.csv",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]

        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()

        nids = collect_nids_from_create_output(create_output)

        try:
            assert len(nids) == 5

            parent_nid = -9  # Initialize parent_nid to an invalid value.
            for nid in nids:
                node_url = configuration["host"] + "/node/" + nid + "?_format=json"
                response = requests.get(node_url, verify=False)
                node_json = json.loads(response.text)
                # Get the node ID of the parent node.
                if node_json["title"][0]["value"].startswith("Tester"):
                    parent_nid = node_json["nid"][0]["value"]
                    break

            for nid in nids:
                node_url = configuration["host"] + "/node/" + nid + "?_format=json"
                response = requests.get(node_url, verify=False)
                node_json = json.loads(response.text)
                if node_json["title"][0]["value"].startswith(
                    "Secondary task test child 1"
                ):
                    assert int(node_json["field_member_of"][0]["target_id"]) == int(
                        parent_nid
                    )
                elif node_json["title"][0]["value"].startswith(
                    "Secondary task test child 2"
                ):
                    assert int(node_json["field_member_of"][0]["target_id"]) == int(
                        parent_nid
                    )
                else:
                    assert node_json["field_member_of"] == []
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
                secondary_config_file_path,
                os.path.join(
                    self.current_dir,
                    "assets",
                    "secondary_task_test",
                    "metadata.csv.preprocessed",
                ),
                os.path.join(self.temp_dir, "secondary.csv.preprocessed"),
                os.path.join(
                    self.current_dir,
                    "assets",
                    "secondary_task_test",
                    "id_to_node_map.tsv",
                ),
                os.path.join(
                    self.current_dir,
                    "assets",
                    "secondary_task_test",
                    "rollback.csv",
                ),
            )


class TestSecondaryTaskWithGoogleSheets(WorkbenchTest):
    """Note: This test fetches data from https://docs.google.com/spreadsheets/d/19AxFWEFuwEoNqH8ciUo0PRAroIpNE9BuBhE5tIE6INQ/edit#gid=0"""

    @pytest.fixture(scope="class")
    def setup_bundle(self):
        # Temporarily disable the REQUESTS_CA_BUNDLE environment variable to avoid SSL verification issues.
        temp_bundle = os.environ.get("REQUESTS_CA_BUNDLE", None)
        if temp_bundle:
            os.environ["REQUESTS_CA_BUNDLE"] = ""

        yield "bundle altered"

        if temp_bundle:
            os.environ["REQUESTS_CA_BUNDLE"] = temp_bundle

    def test_secondary_task_with_google_sheet(self, setup_bundle, workbench_user):
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "nodes_only": True,
            "csv_field_templates": [
                {"field_model": "https://schema.org/DigitalDocument"}
            ],
            "id_field": "field_local_identifier",
            "input_csv": "https://docs.google.com/spreadsheets/d/19AxFWEFuwEoNqH8ciUo0PRAroIpNE9BuBhE5tIE6INQ/edit",
            "google_sheets_gid": 637387343,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        secondary_config_file_path = self.write_config_and_get_path(configuration)
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "nodes_only": True,
            "secondary_tasks": [secondary_config_file_path],
            "csv_field_templates": [
                {"field_model": "https://schema.org/DigitalDocument"}
            ],
            "id_field": "field_local_identifier",
            "input_csv": "https://docs.google.com/spreadsheets/d/19AxFWEFuwEoNqH8ciUo0PRAroIpNE9BuBhE5tIE6INQ/edit#gid=0",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()
        nids = collect_nids_from_create_output(create_output)

        try:
            assert len(nids) == 8

            parent_nid = -9  # Initialize parent_nid to an invalid value.
            for nid in nids:
                node_url = configuration["host"] + "/node/" + nid + "?_format=json"
                response = requests.get(node_url, verify=False)
                node_json = json.loads(response.text)
                # Get the node ID of the parent node.
                if node_json["field_local_identifier"][0]["value"] == "GSP-04":
                    parent_nid = node_json["nid"][0]["value"]
                    break

            for nid in nids:
                node_url = configuration["host"] + "/node/" + nid + "?_format=json"
                response = requests.get(node_url, verify=False)
                node_json = json.loads(response.text)
                local_id = node_json["field_local_identifier"][0]["value"]
                if local_id == "GSC-03" or local_id == "GSC-04":
                    assert int(node_json["field_member_of"][0]["target_id"]) == int(
                        parent_nid
                    )
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
                secondary_config_file_path,
                create_config_file_path,
                os.path.join(
                    self.current_dir,
                    "assets",
                    "secondary_task_with_google_sheets_and_excel_test",
                    "rollback.csv",
                ),
                os.path.join(self.temp_dir, "google_sheet.csv"),
                os.path.join(self.temp_dir, "google_sheet.csv.preprocessed"),
            )

            secondary_task_google_sheets_csv_paths = glob.glob(
                self.temp_dir
                + "/**secondary_task_with_google_sheets_and_excel_test_google_sheets_secondary*"
            )
            for secondary_csv_file_path in secondary_task_google_sheets_csv_paths:
                if os.path.exists(os.path.join(self.temp_dir, secondary_csv_file_path)):
                    os.remove(os.path.join(self.temp_dir, secondary_csv_file_path))


class TestSecondaryTaskWithExcel(WorkbenchTest):
    """Test the secondary task functionality with Excel files."""

    def test_secondary_task_with_excel(self, workbench_user):
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "nodes_only": True,
            "csv_field_templates": [
                {"field_model": "https://schema.org/DigitalDocument"}
            ],
            "id_field": "field_local_identifier",
            "input_dir": "tests/assets/secondary_task_with_google_sheets_and_excel_test",
            "input_csv": "secondary_task_with_excel.xlsx",
            "excel_worksheet": "secondary",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        secondary_config_file_path = self.write_config_and_get_path(configuration)
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "nodes_only": True,
            "secondary_tasks": [secondary_config_file_path],
            "csv_field_templates": [
                {"field_model": "https://schema.org/DigitalDocument"}
            ],
            "id_field": "field_local_identifier",
            "input_dir": "tests/assets/secondary_task_with_google_sheets_and_excel_test",
            "input_csv": "secondary_task_with_excel.xlsx",
            "excel_worksheet": "primary",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()

        nids = collect_nids_from_create_output(create_output)

        try:
            assert len(nids) == 8

            parent_nid = -9  # Initialize parent_nid to an invalid value.
            for nid in nids:
                node_url = configuration["host"] + "/node/" + nid + "?_format=json"
                response = requests.get(node_url, verify=False)
                node_json = json.loads(response.text)
                # Get the node ID of the parent node.
                if node_json["field_local_identifier"][0]["value"] == "STTP-02":
                    parent_nid = node_json["nid"][0]["value"]
                    break

            for nid in nids:
                node_url = configuration["host"] + "/node/" + nid + "?_format=json"
                response = requests.get(node_url, verify=False)
                node_json = json.loads(response.text)
                local_id = node_json["field_local_identifier"][0]["value"]
                if local_id == "STTC-01" or local_id == "STTC-02":
                    assert int(node_json["field_member_of"][0]["target_id"]) == int(
                        parent_nid
                    )
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
                secondary_config_file_path,
                create_config_file_path,
                os.path.join(
                    self.current_dir,
                    "assets",
                    "secondary_task_with_google_sheets_and_excel_test",
                    "rollback.csv",
                ),
                os.path.join(self.temp_dir, "excel.csv"),
                os.path.join(self.temp_dir, "excel.csv.preprocessed"),
            )

            secondary_task_excel_csv_paths = glob.glob(
                "/**secondary_task_with_google_sheets_and_excel_test_google_sheets_secondary*"
            )
            for secondary_csv_file_path in secondary_task_excel_csv_paths:
                if os.path.exists(os.path.join(self.temp_dir, secondary_csv_file_path)):
                    os.remove(os.path.join(self.temp_dir, secondary_csv_file_path))


class TestAdditionalFilesCreate(WorkbenchTest):

    @pytest.fixture(scope="function")
    def setup_nodes(self, workbench_user):
        """This fixture calls the workbench_user fixture to ensure the user does the actual creation."""
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_csv": "create.csv",
            "input_dir": "tests/assets/additional_files_test",
            "additional_files": [
                {"preservation": "http://pcdm.org/use#PreservationMasterFile"},
                {"transcript": "http://pcdm.org/use#Transcript"},
            ],
            "standalone_media_url": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        subprocess.check_output(create_cmd, cwd=self.workbench_dir)

        rollback_file_path = os.path.join(
            self.current_dir, "assets", "additional_files_test", "rollback.csv"
        )
        # There will only be one nid in the rollback.csv file.
        with open(rollback_file_path, "r") as rbf:
            nid = rbf.readlines()[-1].strip()

        media_list_url = configuration["host"] + "/node/" + nid + "/media?_format=json"
        media_list_response = requests.get(
            media_list_url,
            auth=(configuration["username"], configuration["password"]),
            verify=False,
        )

        assert (
            media_list_response.status_code == 200
        ), f"Failed to fetch media list for node {nid}."

        media_list_json = json.loads(media_list_response.text)
        media_sizes = dict()
        media_use_tids = dict()
        for media in media_list_json:
            media_use_tids[media["mid"][0]["value"]] = media["field_media_use"][0][
                "target_id"
            ]
            if "field_file_size" in media:
                media_sizes[media["mid"][0]["value"]] = media["field_file_size"][0][
                    "value"
                ]
            # We don't use the transcript file's size here since it's not available via REST. Instead, since this
            # file will be the only media with 'field_edited_text' (the transcript), we tack its value onto media_sizes
            # for testing below.
            if "field_edited_text" in media:
                media_sizes["transcript"] = media["field_edited_text"][0]["value"]

        yield {
            "media_sizes": media_sizes,
            "media_use_tids": media_use_tids,
            "configuration": configuration,
        }

        configuration = {
            "task": "delete",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/additional_files_test",
            "input_csv": "rollback.csv",
            "standalone_media_url": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        delete_config_file_path = self.write_config_and_get_path(configuration)
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        subprocess.check_output(delete_cmd, cwd=self.workbench_dir)

        cleanup_paths(
            create_config_file_path,
            rollback_file_path,
            delete_config_file_path,
            os.path.join(self.temp_dir, "create.csv.preprocessed"),
            os.path.join(
                self.current_dir, "assets", "additional_files_test", "rollback.csv"
            ),
            os.path.join(self.temp_dir, "rollback.csv.preprocessed"),
        )

    def test_media_creation_and_media_use_tids(self, setup_nodes):
        # This is the original file's size.
        assert 217504 in setup_nodes["media_sizes"].values()
        # This is the preservation file's size.
        assert 286445 in setup_nodes["media_sizes"].values()
        # This is the transcript.
        assert "This is a transcript." in setup_nodes["media_sizes"]["transcript"]

        """Doesn't associate media use terms to nodes, but at least it confirms that the intended
        media use tids are present in the media created by this test.
        """
        preservation_media_use_tid = self.get_term_id_from_uri(
            "http://pcdm.org/use#PreservationMasterFile",
            setup_nodes["configuration"],
        )
        assert preservation_media_use_tid in setup_nodes["media_use_tids"].values()
        transcript_media_use_tid = self.get_term_id_from_uri(
            "http://pcdm.org/use#Transcript", setup_nodes["configuration"]
        )
        assert transcript_media_use_tid in setup_nodes["media_use_tids"].values()

    @staticmethod
    def get_term_id_from_uri(uri: str, config: dict):
        """We don't use get_term_from_uri() from workbench_utils because it requires a full config object."""
        term_from_authority_link_url = (
            config["host"]
            + "/term_from_uri?_format=json&uri="
            + uri.replace("#", "%23")
        )
        response = requests.get(
            term_from_authority_link_url,
            auth=(config["username"], config["password"]),
            verify=False,
        )
        response_body = json.loads(response.text)
        tid = response_body[0]["tid"][0]["value"]
        return tid


class TestAdditionalFilesCreateAllowMissingFilesFalse(WorkbenchTest):
    """Test the creation of additional files with allow_missing_files set to False."""

    def test_create(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "metadata_additional_files_check.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/additional_files_allow_missing_files_false.log",
            "additional_files": [{"tn": "http://pcdm.org/use#ThumbnailImage"}],
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()

        create_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_false.log",
        )

        nids = collect_nids_from_create_output(create_output)

        try:
            # Only three nodes will be created before workbench exits.
            assert len(nids) == 3

            with open(create_log_file_path) as log_file:
                log_data = log_file.read()
            assert re.search(
                'Media for "additional_files" CSV column "tn" in row with ID "003" .* not created because CSV field is empty',
                log_data,
            )
            assert re.search(
                'Media for file "https://www.lib.sfu.ca/xxxtttuuu.jpg" named in field "tn" of CSV row with ID "005" not created because file does not exist',
                log_data,
            )
            assert not re.search("Islandora Workbench successfully completed", log_data)
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
                os.path.join(
                    self.current_dir,
                    "assets",
                    "allow_missing_files_test",
                    "rollback.csv",
                ),
                os.path.join(
                    self.temp_dir,
                    "metadata_additional_files_check.csv.preprocessed",
                ),
                create_log_file_path,
            )


class TestAdditionalFilesCreateAllowMissingFilesTrue(WorkbenchTest):
    """Test the creation of additional files with allow_missing_files set to True."""

    def test_create(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "metadata_additional_files_check.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/additional_files_allow_missing_files_true.log",
            "additional_files": [{"tn": "http://pcdm.org/use#ThumbnailImage"}],
            "allow_missing_files": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd)
        create_output = create_output.decode().strip()

        nids = collect_nids_from_create_output(create_output)

        create_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_true.log",
        )

        try:
            assert len(nids) == 5

            with open(create_log_file_path) as log_file:
                log_data = log_file.read()
            assert re.search(
                'Media for "additional_files" CSV column "tn" in row with ID "003" .* not created because CSV field is empty',
                log_data,
            )
            assert re.search(
                'Media for file "additional_files_2_tn.jpg" named in field "tn" of CSV row with ID "002" not created because file does not exist',
                log_data,
            )
            assert re.search(
                'Media for file "https://www.lib.sfu.ca/xxxtttuuu.jpg" named in field "tn" of CSV row with ID "005" not created because file does not exist',
                log_data,
            )
            assert re.search("Islandora Workbench successfully completed", log_data)
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
                os.path.join(
                    self.current_dir,
                    "assets",
                    "allow_missing_files_test",
                    "rollback.csv",
                ),
                os.path.join(
                    self.temp_dir,
                    "metadata_additional_files_check.csv.preprocessed",
                ),
                create_log_file_path,
            )


class TestAdditionalFilesAddMediaAllowMissingFiles(WorkbenchTest):

    @pytest.fixture(scope="function")
    def setup_nodes(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "add_media_create_nodes.csv",
            "standalone_media_url": True,
            "allow_missing_files": True,
            "log_file_path": "tests/assets/allow_missing_files_test/add_media_create_nodes.log",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_create_nodes.log",
        )
        rollback_file_path = os.path.join(
            self.current_dir, "assets", "allow_missing_files_test", "rollback.csv"
        )
        add_media_csv_template_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files.csv.template",
        )

        create_cmd = ["./workbench", "--config", create_config_file_path]
        create_output = subprocess.check_output(create_cmd)
        create_output = create_output.decode().strip()

        nids = collect_nids_from_create_output(create_output)

        # Insert their node IDs in the input CSV file. First, open the CSV template.
        with open(add_media_csv_template_file_path) as csv_template:
            csv_template_lines = csv_template.readlines()

        # Then add a node ID to the start of each line from the template
        # and write out an add_media input CSV file.
        template_line_index = 0
        with tempfile.NamedTemporaryFile(
            mode="a+", delete=False, suffix="_add_media_additional_files.csv"
        ) as add_media_csv:
            add_media_csv_file_path = add_media_csv.name
            # The first line in the output CSV is the headers from the template.
            add_media_csv.write(csv_template_lines[template_line_index])
            # The subsequent lines should each start with a node ID from.
            for node_id in nids:
                template_line_index = template_line_index + 1
                add_media_csv.write(
                    f"{node_id}{csv_template_lines[template_line_index]}"
                )

        yield {
            "add_media_csv_file_path": add_media_csv_file_path,
            "workbench_user": workbench_user,
        }

        for nid in nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                create_config_file_path,
                "--quick_delete_node",
                configuration["host"] + "/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        cleanup_paths(
            create_config_file_path,
            create_log_file_path,
            rollback_file_path,
            add_media_csv_file_path,
            os.path.join(self.temp_dir, "add_media_create_nodes.csv.preprocessed"),
            os.path.join(self.temp_dir, "add_media_additional_files.csv.preprocessed"),
        )

    def test_false(self, setup_nodes):
        """Test the addition of additional files with allow_missing_files set to False."""
        false_with_additional_files_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_false.log",
        )

        configuration = {
            "task": "add_media",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": setup_nodes["add_media_csv_file_path"],
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/add_media_additional_files_allow_missing_files_false.log",
            "additional_files": [
                {"preservation": "http://pcdm.org/use#PreservationMasterFile"},
                {"transcript": "http://pcdm.org/use#Transcript"},
            ],
            "secure_ssl_only": False,
            "media_type": "file",
        }
        configuration = setup_nodes["workbench_user"].alter_configuration(configuration)
        add_media_config_file_path = self.write_config_and_get_path(configuration)
        add_media_cmd = [
            "./workbench",
            "--config",
            add_media_config_file_path,
        ]
        proc = subprocess.Popen(
            add_media_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self.workbench_dir,
        )
        stdout, stderr = proc.communicate()
        add_media_output = str(stdout.decode().strip())

        try:
            assert re.search(
                r'Media for node "?\d+"? not created since CSV column "preservation" is empty',
                add_media_output,
            )
            assert re.search(
                r'Media for node "?\d+"? not created since CSV column "file" is empty',
                add_media_output,
            )
            assert re.search(
                r'Additional file "add_media_transcript_x.txt" identified in CSV "transcript" column for node ID \d+ not found',
                add_media_output,
            )

            with open(false_with_additional_files_log_file_path) as log_file_false:
                log_data_false = log_file_false.read()

            assert re.search(
                r'Media for node "?\d+"? not created since CSV column "preservation" is empty',
                log_data_false,
            )
            assert re.search(
                r'Media for node "?\d+"? not created since CSV column "file" is empty',
                log_data_false,
            )
            assert re.search(
                r'Additional file "add_media_transcript_x.txt" identified in CSV "transcript" column for node ID \d+ not found',
                log_data_false,
            )

        finally:
            cleanup_paths(
                add_media_config_file_path,
                false_with_additional_files_log_file_path,
            )

    def test_true(self, setup_nodes):
        """Test the addition of additional files with allow_missing_files set to True."""
        true_with_additional_files_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_true.log",
        )

        configuration = {
            "task": "add_media",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": setup_nodes["add_media_csv_file_path"],
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/add_media_additional_files_allow_missing_files_true.log",
            "allow_missing_files": True,
            "additional_files": [
                {"preservation": "http://pcdm.org/use#PreservationMasterFile"},
                {"transcript": "http://pcdm.org/use#Transcript"},
            ],
            "secure_ssl_only": False,
            "media_type": "file",
        }
        configuration = setup_nodes["workbench_user"].alter_configuration(configuration)
        add_media_config_file_path = self.write_config_and_get_path(configuration)
        add_media_cmd = [
            "./workbench",
            "--config",
            add_media_config_file_path,
        ]
        add_media_output = subprocess.check_output(
            add_media_cmd, cwd=self.workbench_dir
        )
        add_media_output = add_media_output.decode().strip()

        try:
            assert re.search(
                r'Media for node "?\d+"? not created since CSV column "preservation" is empty',
                add_media_output,
            )
            assert re.search(
                r'Media for node "?\d+"? not created since CSV column "file" is empty',
                add_media_output,
            )

            with open(true_with_additional_files_log_file_path) as log_file_true:
                log_data_true = log_file_true.read()

            assert re.search(
                r'Media for node "?\d+"? not created since CSV column "preservation" is empty',
                log_data_true,
            )
            assert re.search(
                r'Media for node "?\d+"? not created since CSV column "file" is empty',
                log_data_true,
            )
            assert re.search(
                r'Additional file "add_media_transcript_x.txt" identified in CSV "transcript" column for node ID \d+ not found',
                log_data_true,
            )
            assert re.search(
                "Islandora Workbench successfully completed", log_data_true
            )
        finally:
            cleanup_paths(
                add_media_config_file_path,
                true_with_additional_files_log_file_path,
            )


class TestExportCSVWithAdditionalFiles(WorkbenchTest):

    @pytest.fixture(scope="function")
    def setup_nodes(self, workbench_user):
        """Create nodes with additional files for testing export."""
        test_assets_dir = os.path.join(
            self.current_dir, "assets", "additional_files_test"
        )

        # Create nodes using the existing additional files test infrastructure
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/additional_files_test",
            "input_csv": "create.csv",
            "standalone_media_url": True,
            "additional_files": [
                {"preservation": "http://pcdm.org/use#PreservationMasterFile"},
                {"transcript": "http://pcdm.org/use#Transcript"},
            ],
            "standalone_media": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        create_config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", create_config_file_path]
        subprocess.check_output(create_cmd, cwd=self.workbench_dir)

        # Get node IDs from rollback.csv generated by create task
        rollback_csv = os.path.join(test_assets_dir, "rollback.csv")
        with open(rollback_csv, "r") as f:
            nids = [
                line.strip() for line in f.readlines()[3:]
            ]  # Skip header and comments

        # Setup export directory relative to test assets
        export_dir = os.path.join(test_assets_dir, "exported_files")
        os.makedirs(export_dir, exist_ok=True)

        yield {
            "nids": nids,
            "export_dir": export_dir,
            "workbench_user": workbench_user,
        }

        """Cleanup created nodes and exported files."""
        for nid in nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                create_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

        # Cleanup export directory
        if os.path.exists(export_dir):
            shutil.rmtree(export_dir)

        # Remove generated files
        cleanup_paths(
            create_config_file_path,
            rollback_csv,
        )

    def test_export_additional_files_as_urls(self, setup_nodes):
        """Test exporting additional files as URLs."""
        requests.packages.urllib3.disable_warnings()
        configuration = {
            "task": "export_csv",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/additional_files_test",
            "input_csv": "rollback.csv",
            "export_csv_field_list": ["field_model"],
            "export_csv_file_path": "tests/assets/additional_files_test/exported_files/export_urls.csv",
            "export_file_url_instead_of_download": True,
            "additional_files": [
                {"preservation": "http://pcdm.org/use#PreservationMasterFile"},
                {"transcript": "http://pcdm.org/use#Transcript"},
            ],
            "secure_ssl_only": False,
        }
        configuration = setup_nodes["workbench_user"].alter_configuration(configuration)
        export_config = self.write_config_and_get_path(configuration)
        export_cmd = ["./workbench", "--config", export_config]
        subprocess.check_output(export_cmd, cwd=self.workbench_dir)

        exported_csv = os.path.join(setup_nodes["export_dir"], "export_urls.csv")

        try:
            assert os.path.exists(exported_csv)

            with open(exported_csv, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Verify main fields, file and additional files columns\
                    assert "node_id" in row
                    assert "title" in row
                    assert "field_model" in row
                    assert "file" in row
                    assert "preservation" in row
                    assert "transcript" in row

                    # Verify that columns not in the field list are not included.
                    assert "field_abstract" not in row

                    # Check URLs are valid and accessible
                    for url_field in ["file", "preservation", "transcript"]:
                        if row[url_field]:  # Handle empty fields
                            response = requests.head(row[url_field], verify=False)
                            assert (
                                response.status_code == 200
                            ), f"Failed to access {url_field} URL: {row[url_field]}"
        finally:
            cleanup_paths(
                exported_csv,
                export_config,
            )

    def test_export_additional_files_as_files(self, setup_nodes, workbench_user):
        """Test exporting additional files as downloaded files."""
        configuration = {
            "task": "export_csv",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/additional_files_test",
            "input_csv": "rollback.csv",
            "export_csv_file_path": "tests/assets/additional_files_test/exported_files/export_files.csv",
            "export_file_directory": "tests/assets/additional_files_test/exported_files/",
            "additional_files": [
                {"preservation": "http://pcdm.org/use#PreservationMasterFile"},
                {"transcript": "http://pcdm.org/use#Transcript"},
            ],
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        export_config = self.write_config_and_get_path(configuration)
        export_cmd = ["./workbench", "--config", export_config]
        subprocess.check_output(export_cmd, cwd=self.workbench_dir)

        exported_csv = os.path.join(setup_nodes["export_dir"], "export_files.csv")
        try:
            assert os.path.exists(exported_csv)

            with open(exported_csv, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Check all file fields exist in export directory
                    for field in ["file", "preservation", "transcript"]:
                        if row[field]:  # Handle empty fields
                            file_path = os.path.join(
                                setup_nodes["export_dir"], row[field]
                            )
                            assert os.path.exists(
                                file_path
                            ), f"File {row[field]} not found in export directory"
        finally:
            cleanup_paths(
                exported_csv,
                export_config,
            )


# TODO: Implement TestUpdateMediaFields to update media fields and verify changes
class TestUpdateMediaFields:
    """Create a couple nodes plus image media, update the media's field_original_name
    and field_width fields, then confirm they were updated by GETting the media's JSON.
    """
