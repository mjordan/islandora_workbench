"""unittest tests that require a live Drupal at https://islandora.dev. In most cases, the host URL,
credentials, etc. are in a configuration file referenced in the test.

This test file contains tests for --check. Files islandora_tests.py, islandora_tests_paged_content.py,
and islandora_tests_hooks.py also contain tests that interact with an Islandora instance.
"""

import sys
import os
import tempfile

import subprocess
import re
import requests
import json
import urllib.parse
import unittest

from workbench_test_class import WorkbenchTest, AdminUser

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFailToConnect(WorkbenchTest):
    """Test that the workbench fails to connect to a bad host URL."""

    def test_failed_to_connect(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://somebadhost.org",
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            assert re.search(
                "Workbench can't connect to https://somebadhost.org", output
            )
        except subprocess.CalledProcessError as err:
            pass
        finally:
            if os.path.exists(config_file_path):
                os.remove(config_file_path)


class TestCreateCheck(WorkbenchTest):
    """Test that the workbench can check the configuration for a create action."""

    def test_create_check(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        config_file_path = self.write_config_and_get_path(configuration)

        cmd = [self.workbench_path, "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        try:
            assert re.search("Configuration and input data appear to be valid", output)
        finally:
            if os.path.exists(config_file_path):
                os.remove(config_file_path)


@unittest.skipIf(
    "GITHUB_ACTIONS" in os.environ,
    "Passes when tests locally run but not in Github workflows.",
)
class TestCheckFromGoogleSpreadsheetCheck(WorkbenchTest):
    """Note: This test fetches data from https://docs.google.com/spreadsheets/d/13Mw7gtBy1A3ZhYEAlBzmkswIdaZvX18xoRBxfbgxqWc/edit#gid=0."""

    temp_bundle = None

    default_config = {
        "task": "create",
        "host": "https://islandora.dev",
        "input_csv": "https://docs.google.com/spreadsheets/d/13Mw7gtBy1A3ZhYEAlBzmkswIdaZvX18xoRBxfbgxqWc/edit#gid=0",
        "nodes_only": True,
        "secure_ssl_only": False,
    }

    def setup_method(self, method):
        # Temporarily disable the REQUESTS_CA_BUNDLE environment variable to avoid SSL verification issues.
        self.temp_bundle = os.environ.get("REQUESTS_CA_BUNDLE", None)
        if self.temp_bundle:
            os.environ["REQUESTS_CA_BUNDLE"] = ""

    def teardown_method(self, method):
        # Restore the REQUESTS_CA_BUNDLE environment variable if it was set.
        if self.temp_bundle:
            os.environ["REQUESTS_CA_BUNDLE"] = self.temp_bundle

        csv_path = os.path.join(self.temp_dir, "google_sheet.csv")
        if os.path.exists(csv_path):
            os.remove(csv_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "google_sheet.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)

    def test_create_from_google_spreadsheet_check(self, workbench_user):
        configuration = self.default_config
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)

        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search("Extracting CSV data from https://docs.google.com", output)
        assert re.search("Configuration and input data appear to be valid", output)
        assert re.search("OK, all 2 rows in the CSV file", output)

    def test_google_gid_1(self, workbench_user):
        configuration = self.default_config
        configuration["google_sheets_gid"] = 1867618389
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search("OK, all 3 rows in the CSV file", output)

    def test_google_gid_2(self, workbench_user):
        configuration = self.default_config
        configuration["google_sheets_gid"] = 390347846
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()

        assert re.search("OK, all 5 rows in the CSV file", output)

    def test_google_gid_3(self, workbench_user):
        configuration = self.default_config
        configuration["google_sheets_gid"] = 953977578
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()

        assert re.search("OK, all 1 rows in the CSV file", output)


class TestUpdateCheck(WorkbenchTest):

    def test_update_check(self, workbench_user):
        configuration = {
            "task": "update",
            "host": "https://islandora.dev",
            "secure_ssl_only": False,
            "input_csv": "update.csv",
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search("Configuration and input data appear to be valid", output)

    def teardown_method(self, method):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "update.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestDeleteCheck(WorkbenchTest):

    def test_delete_check(self, workbench_user):
        configuration = {
            "task": "delete",
            "host": "https://islandora.dev",
            "secure_ssl_only": False,
            "input_csv": "delete.csv",
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search("Configuration and input data appear to be valid", output)

    def teardown_method(self, method_name):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "delete.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestAddMediaCheck(WorkbenchTest):

    def test_add_media_check(self, workbench_user):
        configuration = {
            "task": "add_media",
            "host": "https://islandora.dev",
            "secure_ssl_only": False,
            "input_csv": "add_media.csv",
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()

        assert re.search("Configuration and input data appear to be valid", output)

    def teardown_method(self, method_name):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "add_media.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestCreateMaxNodeTitleLengthCheck(WorkbenchTest):

    def test_for_too_long_titles(self, workbench_user):
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
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            'CSV field "title" in record with ID 03 contains a value that is longer .32 characters',
            output,
        )
        assert re.search(
            'CSV field "title" in record with ID 04 contains a value that is longer .34 characters',
            output,
        )
        assert re.search(
            'CSV field "title" in record with ID 05 contains a value that is longer .36 characters',
            output,
        )

    def teardown_method(self, method_name):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "create_max_node_title_length.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestUpdateWithMaxNodeTitleLengthCheck(WorkbenchTest):

    # Path to the config to create the nodes we will later update.
    create_config_file_path = None

    # List of node ids created by this test for cleanup.
    nids = []

    def test_for_too_long_titles(self, workbench_user):
        # First, we create some nodes so we have the node IDs for the update CSV file. We are
        # reusing the CSV data used by the TestCreateWithMaxNodeTitleLength test class.
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
        self.create_config_file_path = self.write_config_and_get_path(configuration)

        configuration = {
            "task": "update",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/max_node_title_length_test",
            "input_csv": "update_max_node_title_length.csv",
            "max_node_title_length": 30,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)

        create_cmd = [self.workbench_path, "--config", self.create_config_file_path]
        create_output = subprocess.check_output(create_cmd)
        create_output = create_output.decode().strip()

        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        assert len(self.nids) == 6

        # Now that we have our node IDs, we write out the CSV file used in --check.
        update_csv_file_path = os.path.join(
            self.current_dir,
            "assets",
            "max_node_title_length_test",
            "update_max_node_title_length.csv",
        )
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
        with open(update_csv_file_path, mode="wt") as update_csv_file:
            update_csv_file.write("\n".join(update_csv_file_rows))

        update_cmd = [
            self.workbench_path,
            "--config",
            self.config_file_path,
            "--check",
        ]

        check_output = subprocess.check_output(update_cmd)
        check_output = check_output.decode().strip()

        assert re.search(
            "contains a value that is longer .37 characters.", check_output
        )
        assert re.search(
            "contains a value that is longer .39 characters.", check_output
        )
        assert re.search(
            "contains a value that is longer .42 characters.", check_output
        )
        assert re.search(
            "contains a value that is longer .44 characters.", check_output
        )

    def teardown_method(self, method_name):
        # Delete our test nodes we created.
        for nid in self.nids:
            quick_delete_cmd = [
                self.workbench_path,
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        rollback_file_path = os.path.join(
            self.current_dir, "assets", "max_node_title_length_test", "rollback.csv"
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        preprocessed_create_file_path = os.path.join(
            self.temp_dir, "create_max_node_title_length.csv.preprocessed"
        )
        if os.path.exists(preprocessed_create_file_path):
            os.remove(preprocessed_create_file_path)

        preprocessed_create_file_path = os.path.join(
            self.temp_dir, "update_max_node_title_length.csv.preprocessed"
        )
        if os.path.exists(preprocessed_create_file_path):
            os.remove(preprocessed_create_file_path)

        if os.path.exists(self.create_config_file_path):
            os.remove(self.create_config_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestTypedRelationBadRelatorCheck(WorkbenchTest):

    def test_bad_relator_check_fail(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/typed_relation_test/input_data",
            "input_csv": "bad_typed_relation_fail.csv",
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            assert re.search(
                "does not use the structure required for typed relation fields", output
            )
        except subprocess.CalledProcessError as err:
            pass

    def teardown_method(self, method_name):
        rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "input_data",
            "rollback.csv",
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "bad_typed_relation_fail.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestTypedRelationBadUriCheck(WorkbenchTest):

    def test_bad_uri_check_fail(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/typed_relation_test/input_data",
            "input_csv": "bad_uri_fail.csv",
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            assert re.search("example.com", output)
        except subprocess.CalledProcessError as err:
            pass

    def teardown_method(self, method_name):
        rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "input_data",
            "rollback.csv",
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "bad_uri_fail.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestTypedRelationNewTypedRelationCheck(WorkbenchTest):

    def test_new_typed_relation_check(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/typed_relation_test/input_data",
            "input_csv": "new_typed_relation.csv",
            "nodes_only": True,
            "allow_adding_terms": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()

        assert re.search("new terms will be created as noted", output)

    def teardown_method(self, method_name):
        rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "input_data",
            "rollback.csv",
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "new_typed_relation.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestTypedRelationNoNamespaceCheck(WorkbenchTest):

    def test_no_namespace_check_fail(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/typed_relation_test/input_data",
            "input_csv": "no_namespace.csv",
            "nodes_only": True,
            "allow_adding_terms": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            assert re.search("require a vocabulary namespace", output)
        except subprocess.CalledProcessError as err:
            pass

    def teardown_method(self, method_name):
        rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "input_data",
            "rollback.csv",
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "no_namespace.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestDelimiterCheck(WorkbenchTest):

    def test_delimiter_check(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/typed_relation_test/input_data",
            "media_type": "image",
            "input_csv": "metadata.tsv",
            "delimiter": "\\t",
            "allow_missing_files": True,
            "exit_on_first_missing_file_during_check": False,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search("input data appear to be valid", output)

    def teardown_method(self, method_name):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "metadata.tsv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestGeolocationCheck(WorkbenchTest):

    def test_geolocation_check(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/geolocation_test/input_data",
            "input_csv": "bad_geocoorindates_fail.csv",
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            assert re.search(r"\+43\.45-123\.17", output)
        except subprocess.CalledProcessError as err:
            pass

    def teardown_method(self, method_name):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "bad_geocoorindates_fail.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestHeaderColumnMismatchCheck(WorkbenchTest):

    def test_header_column_mismatch_fail(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/header_column_mismatch_test",
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            assert re.search("Row 2 of your CSV file does not", output)
        except subprocess.CalledProcessError as err:
            pass

    def teardown_method(self, method_name):
        rollback_file_path = os.path.join(
            self.current_dir, "assets", "header_column_mismatch_test", "rollback.csv"
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "metadata.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)

        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestCreateWithFieldTemplatesCheck(WorkbenchTest):

    def test_create_with_field_templates_check(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/create_with_field_templates_test",
            "nodes_only": True,
            "csv_field_templates": {
                "field_rights": "This test is in the public domain.",
                "field_description": "Testing CSV field templates.",
                "field_model": "Image",
            },
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()

        assert re.search(
            "all 3 rows in the CSV file have the same number of columns as there are headers .6.",
            output,
        )

    def teardown_method(self, method_name):
        templated_csv_path = os.path.join(self.temp_dir, "metadata.csv.preprocessed")
        if os.path.exists(templated_csv_path):
            os.remove(templated_csv_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestTaxonomies(WorkbenchTest):

    # Path to the taxonomy create configuration file.
    taxonomies_config_file_path = None

    # List of nodes ids created by this test for cleanup.
    nids = []

    # Credentials to handle cleanup, this might not work now that each test is run twice.
    islandora_host = None
    islandora_username = None
    islandora_password = None

    def setup_method(self, method_name):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "allow_adding_terms": True,
            "allow_missing_files": True,
            "input_dir": "tests/assets/taxonomies_test",
            "media_type": "image",
            "exit_on_first_missing_file_during_check": False,
            "secure_ssl_only": False,
        }
        workbench_user = AdminUser()
        configuration = workbench_user.alter_configuration(configuration)
        self.taxonomies_config_file_path = self.write_config_and_get_path(configuration)

        self.islandora_host = configuration["host"]
        self.islandora_username = configuration["username"]
        self.islandora_password = configuration["password"]

        create_cmd = [
            self.workbench_path,
            "--config",
            self.taxonomies_config_file_path,
        ]

        create_output = subprocess.check_output(create_cmd)
        create_output = create_output.decode().strip()

        # Write a file to the system's temp directory containing the node IDs of the
        # nodes created during this test so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

    def test_validate_term_names_exist(self, workbench_user):
        # Using the same create configuration used in the setup.
        cmd = [
            self.workbench_path,
            "--config",
            self.taxonomies_config_file_path,
            "--check",
        ]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            "term IDs/names in CSV file exist in their respective taxonomies",
            output,
        )

    def test_validate_term_name_does_not_exist(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "allow_adding_terms": False,
            "allow_missing_files": True,
            "input_dir": "tests/assets/taxonomies_test",
            "input_csv": "term_name_not_in_taxonomy.csv",
            "media_type": "image",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [
            self.workbench_path,
            "--config",
            self.config_file_path,
            "--check",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        assert re.search('"XPosters"', str(stdout))

    def test_validate_term_id_does_not_exist(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "allow_adding_terms": False,
            "allow_missing_files": True,
            "input_dir": "tests/assets/taxonomies_test",
            "input_csv": "term_id_not_in_taxonomy.csv",
            "media_type": "image",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [
            self.workbench_path,
            "--config",
            self.config_file_path,
            "--check",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        assert re.search("1000000", str(stdout))

    def teardown_method(self, method_name):
        requests.packages.urllib3.disable_warnings()
        # Delete all terms in the genre taxonomy created by these tests.
        terms_to_delete = [
            "XNewspapers",
            "XPostcards",
            "XCartoons",
            "XCertificates",
            "XPosters",
        ]
        for term_name in terms_to_delete:
            get_tid_url = (
                self.islandora_host
                + "/term_from_term_name?vocab=genre&name="
                + urllib.parse.quote(term_name.strip())
                + "&_format=json"
            )
            get_tid_response = requests.get(
                get_tid_url,
                auth=(self.islandora_username, self.islandora_password),
                verify=False,
            )
            term_data = json.loads(get_tid_response.text)
            if len(term_data):
                term_to_delete_tid = term_data[0]["tid"][0]["value"]
                delete_term_url = (
                    self.islandora_host
                    + "/taxonomy/term/"
                    + str(term_to_delete_tid)
                    + "?_format=json"
                )
                requests.delete(
                    delete_term_url,
                    auth=(self.islandora_username, self.islandora_password),
                    verify=False,
                )

        for nid in self.nids:
            quick_delete_cmd = [
                self.workbench_path,
                "--config",
                self.taxonomies_config_file_path,
                "--quick_delete_node",
                self.islandora_host + "/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        rollback_file_path = os.path.join(
            self.current_dir, "assets", "taxonomies_test", "rollback.csv"
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        preprocessed_csv_path = os.path.join(self.temp_dir, "metadata.csv.preprocessed")
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "term_id_not_in_taxonomy.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "term_name_not_in_taxonomy.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)
        if os.path.exists(self.taxonomies_config_file_path):
            os.remove(self.taxonomies_config_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestParentsPrecedeChildren(WorkbenchTest):

    def test_good_csv(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/parents_precede_children_test",
            "input_csv": "good.csv",
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search("Configuration and input data appear to be valid", output)

    def test_bad_csv(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/parents_precede_children_test",
            "input_csv": "bad.csv",
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        assert re.search('"c2p2" must come after', str(stdout))

    def teardown_method(self, method_name):
        preprocessed_csv_path = os.path.join(self.temp_dir, "good.csv.preprocessed")
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(self.temp_dir, "bad.csv.preprocessed")
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestCreateAllowMissingFiles(WorkbenchTest):

    # Path to the log file used for the tests.
    log_file_path = None

    def test_false(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "metadata_check.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/allow_missing_files_false.log",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        assert re.search(
            'identified in CSV "file" column for row with ID "03" not found',
            str(stdout),
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "allow_missing_files_false.log",
        )
        with open(self.log_file_path) as log_file_false:
            log_data_false = log_file_false.read()
        assert re.search('ID "03" not found', log_data_false)

    def test_true(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "metadata_check.csv",
            "standalone_media_url": True,
            "allow_missing_files": True,
            "log_file_path": "tests/assets/allow_missing_files_test/allow_missing_files_true.log",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            'Warning: "allow_missing_files" configuration setting is set to "true", and CSV "file" column values',
            output,
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "allow_missing_files_true.log",
        )
        with open(self.log_file_path) as log_file_true:
            log_data_true = log_file_true.read()
        assert re.search('row with ID "06" not found or not accessible', log_data_true)

    def test_false_with_soft_checks(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "metadata_check.csv",
            "standalone_media_url": True,
            "perform_soft_checks": True,
            "log_file_path": "tests/assets/allow_missing_files_test/allow_missing_files_false_with_soft_checks.log",
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            'Warning: "perform_soft_checks" configuration setting is set to "true" and some values in the "file" column were not found',
            output,
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "allow_missing_files_false_with_soft_checks.log",
        )
        with open(self.log_file_path) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
        assert re.search(
            'row with ID "03" not found', log_file_false_with_soft_checks_data
        )
        assert re.search(
            'row with ID "06" not found or not accessible',
            log_file_false_with_soft_checks_data,
        )

    def teardown_method(self, method_name):
        if os.path.exists(self.log_file_path):
            os.remove(self.log_file_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "metadata_check.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestCreateAllowMissingFilesWithAdditionalFiles(WorkbenchTest):

    # Path to the config file used for the tests.
    log_file_path = None

    def test_false(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "metadata_additional_files_check.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/additional_files_allow_missing_files_false.log",
            "additional_files": {"tn": "http://pcdm.org/use#ThumbnailImage"},
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        assert re.search(
            'Additional file "https://www.lib.sfu.ca/xxxtttuuu.jpg" in CSV column "tn" in row with ID 005 not found',
            str(stdout),
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_false.log",
        )
        with open(self.log_file_path) as log_file_false:
            log_data_false = log_file_false.read()
        assert re.search(
            'CSV row with ID 003 contains an empty value in its "tn" column',
            log_data_false,
        )
        assert re.search(
            'Additional file "https://www.lib.sfu.ca/xxxtttuuu.jpg" in CSV column "tn" in row with ID 005 not found or not accessible',
            log_data_false,
        )

    def test_true(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "metadata_additional_files_check.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/additional_files_allow_missing_files_true.log",
            "additional_files": {"tn": "http://pcdm.org/use#ThumbnailImage"},
            "allow_missing_files": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            '"allow_missing_files" configuration setting is set to "true", and "additional_files" CSV columns',
            output,
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_true.log",
        )
        with open(self.log_file_path) as log_file_true:
            log_data_true = log_file_true.read()
        assert re.search(
            'Additional file "additional_files_2_tn.jpg" in CSV column "tn" in row with ID 002 not found',
            log_data_true,
        )
        assert re.search(
            'Additional file "https://www.lib.sfu.ca/xxxtttuuu.jpg" in CSV column "tn" in row with ID 005 not found',
            log_data_true,
        )

    def test_false_with_soft_checks(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "metadata_additional_files_check.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/additional_files_allow_missing_files_false_with_soft_checks.log",
            "additional_files": {"tn": "http://pcdm.org/use#ThumbnailImage"},
            "perform_soft_checks": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            'The "perform_soft_checks" configuration setting is set to "true"', output
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_false_with_soft_checks.log",
        )
        with open(self.log_file_path) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
        assert re.search(
            'Additional file "additional_files_2_tn.jpg" in CSV column "tn" in row with ID 002 not found',
            log_file_false_with_soft_checks_data,
        )
        assert re.search(", no problems found", log_file_false_with_soft_checks_data)

    def teardown_method(self, method_name):
        if os.path.exists(self.log_file_path):
            os.remove(self.log_file_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "metadata_additional_files_check.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestAddMediaAllowMissingFiles(WorkbenchTest):

    # Path to the log file used for the tests.
    log_file_path = None

    # List of node IDs created by this test for cleanup.
    nids = []

    # Path to the config file used for the setup of tests.
    create_config_file_path = None

    # Path to the log file used for the setup of tests.
    create_log_file_path = None

    # Path to the CSV file of Node IDs created for the setup of tests.
    add_media_csv_file_path = None

    # Current test host
    islandora_host = "https://islandora.dev"

    def setup_method(self, method_name):
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
        workbench_user = AdminUser()
        configuration = workbench_user.alter_configuration(configuration)
        self.create_config_file_path = self.write_config_and_get_path(configuration)
        self.create_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_create_nodes.log",
        )
        create_cmd = [
            self.workbench_path,
            "--config",
            self.create_config_file_path,
        ]
        create_output = subprocess.check_output(create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        add_media_csv_template_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media.csv.template",
        )
        # Insert their node IDs in the input CSV file. First, open the CSV template.
        with open(add_media_csv_template_file_path) as csv_template:
            csv_template_lines = csv_template.readlines()

        # Then add a node ID to the start of each line from the template
        # and write out an add_media input CSV file.
        template_line_index = 0
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix="add_media.csv"
        ) as add_media_csv:
            # Use a real temp file to store generated data.
            self.add_media_csv_file_path = os.path.join(
                self.temp_dir, add_media_csv.name
            )
            # The first line in the output CSV is the headers from the template.
            add_media_csv.write(csv_template_lines[template_line_index])
            # The subsequent lines should each start with a node ID from.
            for node_id in self.nids:
                template_line_index = template_line_index + 1
                add_media_csv.write(
                    f"{node_id}{csv_template_lines[template_line_index]}"
                )

    def test_false(self, workbench_user):
        configuration = {
            "task": "add_media",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "add_media.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/add_media_allow_missing_files_false.log",
            "media_use_tid": "http://pcdm.org/use#Transcript",
            "secure_ssl_only": False,
            "media_type": "file",
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        assert re.search(
            'File ".*missing_transcript.txt" identified in CSV "file" column for row with ID .* not found',
            str(stdout),
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_allow_missing_files_false.log",
        )
        with open(self.log_file_path) as log_file_false:
            log_data_false = log_file_false.read()
        assert re.search(
            'CSV row with ID .* contains an empty "file" value', log_data_false
        )
        assert re.search(
            'File ".*missing_transcript.txt" identified in CSV "file" column for row with ID .* not found',
            log_data_false,
        )

    def test_true(self, workbench_user):
        configuration = {
            "task": "add_media",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "add_media.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/add_media_allow_missing_files_false.log",
            "media_use_tid": "http://pcdm.org/use#Transcript",
            "allow_missing_files": True,
            "secure_ssl_only": False,
            "media_type": "file",
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            'Warning: "allow_missing_files" configuration setting is set to "true", and CSV "file" column values containing missing',
            output,
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_allow_missing_files_true.log",
        )
        with open(self.log_file_path) as log_file_true:
            log_data_true = log_file_true.read()
        assert re.search(
            'CSV row with ID .* contains an empty "file" value', log_data_true
        )
        assert re.search("INFO - .*no problems found", log_data_true)

    def test_false_with_soft_checks(self, workbench_user):
        configuration = {
            "task": "add_media",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "add_media.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/add_media_allow_missing_files_false.log",
            "media_use_tid": "http://pcdm.org/use#Transcript",
            "perform_soft_checks": True,
            "secure_ssl_only": False,
            "media_type": "file",
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            'Warning: "perform_soft_checks" configuration setting is set to "true" and some values in the "file" column',
            output,
        )
        assert re.search("Configuration and input data appear to be valid", output)

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_allow_missing_files_false_with_soft_checks.log",
        )
        with open(self.log_file_path) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
        assert re.search(
            'CSV row with ID .* contains an empty "file" value',
            log_file_false_with_soft_checks_data,
        )
        assert re.search(
            'File ".*missing_transcript.txt" identified in CSV "file" column for row with ID .* not found',
            log_file_false_with_soft_checks_data,
        )
        assert re.search(
            "INFO - .*no problems found", log_file_false_with_soft_checks_data
        )

    def teardown_method(self, method_name):
        # Delete the nodes created in setUp.
        for nid in self.nids:
            quick_delete_cmd = [
                self.workbench_path,
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                self.islandora_host + "/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        if os.path.exists(self.add_media_csv_file_path):
            os.remove(self.add_media_csv_file_path)

        rollback_file_path = os.path.join(
            self.current_dir, "assets", "allow_missing_files_test", "rollback.csv"
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "add_media_create_nodes.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "add_media.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "metadata_check.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        if os.path.exists(self.create_log_file_path):
            os.remove(self.create_log_file_path)

        if os.path.exists(self.log_file_path):
            os.remove(self.log_file_path)


@unittest.skip("See https://github.com/mjordan/islandora_workbench/issues/561")
class TestAddMediaAllowMissingWithAdditionalFiles(WorkbenchTest):

    # Path to the configuration file for setting up the test objects.
    create_config_file_path = None

    # Path to the log file for the setup of tests.
    create_log_file_path = None

    # Path to the log file for the tests.
    log_file_path = None

    # Path to the CSV file of generated nodes
    add_media_csv_file_path = None

    # Host for the tests.
    islandora_host = "https://islandora.dev"

    # List of node IDs created by this test for cleanup.
    nids = []

    def setup_method(self, method_name):
        # Create nodes to use in add_media task.
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
        workbench_user = AdminUser()
        configuration = workbench_user.alter_configuration(configuration)
        self.create_config_file_path = self.write_config_and_get_path(configuration)

        self.create_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_create_nodes.log",
        )

        create_cmd = [
            self.workbench_path,
            "--config",
            self.create_config_file_path,
        ]
        create_output = subprocess.check_output(create_cmd)
        create_output = create_output.decode().strip()

        # Get the node IDs of the nodes created during this test
        # so they can be deleted in tearDown().
        create_lines = create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        add_media_csv_template_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files.csv.template",
        )
        # Insert their node IDs in the `add_media` input CSV file. First, open the CSV template.
        with open(add_media_csv_template_file_path) as csv_template:
            csv_template_lines = csv_template.readlines()

        # Then add a node ID to the start of each line from the template
        # and write out an add_media input CSV file.
        template_line_index = 0
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix="add_media_create_nodes.csv.preprocessed"
        ) as add_media_csv:
            # Use a tempfile in a temporary directory to avoid putting files in our current directory.
            self.add_media_csv_file_path = os.path.join(
                self.temp_dir, add_media_csv.name
            )
            # The first line in the output CSV is the headers from the template.
            add_media_csv.write(csv_template_lines[template_line_index])
            # The subsequent lines should each start with a node ID from.
            for node_id in self.nids:
                template_line_index = template_line_index + 1
                add_media_csv.write(
                    f"{node_id}{csv_template_lines[template_line_index]}"
                )

    def test_false(self, workbench_user):
        configuration = {
            "task": "add_media",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "add_media_additional_files.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/add_media_additional_files_allow_missing_files_false.log",
            "additional_files": {
                "preservation": "http://pcdm.org/use#PreservationMasterFile",
                "transcript": "http://pcdm.org/use#Transcript",
            },
            "secure_ssl_only": False,
            "media_type": "file",
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        assert re.search(
            'Additional file "add_media_transcript_x.txt" in CSV column "transcript" in row with ID .* not found',
            str(stdout),
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_false.log",
        )
        with open(self.log_file_path) as log_file_false:
            log_data_false = log_file_false.read()
        assert re.search(
            'CSV row with ID .* contains an empty "file" value', log_data_false
        )
        assert re.search(
            'CVS row with ID .* contains an empty value in its "preservation" column',
            log_data_false,
        )
        assert re.search(
            'Additional file "add_media_transcript_x.txt" in CSV column "transcript" in row with ID .* not found',
            log_data_false,
        )

    def test_true(self, workbench_user):
        configuration = {
            "task": "add_media",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "add_media_additional_files.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/add_media_additional_files_allow_missing_files_false.log",
            "additional_files": {
                "preservation": "http://pcdm.org/use#PreservationMasterFile",
                "transcript": "http://pcdm.org/use#Transcript",
            },
            "allow_missing_files": True,
            "secure_ssl_only": False,
            "media_type": "file",
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            'Warning: "allow_missing_files" configuration setting is set to "true", and "additional_files" CSV columns containing missing',
            output,
        )

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_true.log",
        )
        with open(self.log_file_path) as log_file_true:
            log_data_true = log_file_true.read()
        assert re.search(
            'CSV row with ID .* contains an empty "file" value', log_data_true
        )
        assert re.search(
            'CVS row with ID .* contains an empty value in its "preservation" column',
            log_data_true,
        )
        assert re.search("INFO - .*no problems found", log_data_true)

    def test_false_with_soft_checks(self, workbench_user):
        configuration = {
            "task": "add_media",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/allow_missing_files_test",
            "input_csv": "add_media_additional_files.csv",
            "standalone_media_url": True,
            "log_file_path": "tests/assets/allow_missing_files_test/add_media_additional_files_allow_missing_files_false.log",
            "additional_files": {
                "preservation": "http://pcdm.org/use#PreservationMasterFile",
                "transcript": "http://pcdm.org/use#Transcript",
            },
            "secure_ssl_only": False,
            "perform_soft_checks": True,
            "media_type": "file",
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search(
            '"perform_soft_checks" configuration setting is set to "true"', output
        )
        assert re.search("Configuration and input data appear to be valid", output)

        self.log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_false_with_soft_checks.log",
        )
        with open(self.log_file_path) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
        assert re.search(
            'CSV row with ID .* contains an empty "file" value',
            log_file_false_with_soft_checks_data,
        )
        assert re.search(
            'CVS row with ID .* contains an empty value in its "preservation" column',
            log_file_false_with_soft_checks_data,
        )
        assert re.search(
            'Additional file "add_media_transcript_x.txt" in CSV column "transcript" in row with ID .* not found',
            log_file_false_with_soft_checks_data,
        )
        assert re.search(
            "INFO - .*no problems found", log_file_false_with_soft_checks_data
        )

    def teardown_method(self):
        # Delete the nodes created in setUp.
        for nid in self.nids:
            quick_delete_cmd = [
                self.workbench_path,
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                self.islandora_host + "/node/" + nid,
            ]
            subprocess.check_output(quick_delete_cmd)

        if os.path.exists(self.add_media_csv_file_path):
            os.remove(self.add_media_csv_file_path)

        rollback_file_path = os.path.join(
            self.current_dir, "assets", "allow_missing_files_test", "rollback.csv"
        )
        if os.path.exists(rollback_file_path):
            os.remove(rollback_file_path)

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

        if os.path.exists(self.log_file_path):
            os.remove(self.log_file_path)

        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)

        if os.path.exists(self.add_media_csv_file_path):
            os.remove(self.add_media_csv_file_path)


@unittest.skipIf(
    "GITHUB_ACTIONS" in os.environ,
    "Passes when tests locally run but not in Github workflows.",
)
class TestCommentedCsvs(WorkbenchTest):

    def test_commented_csv(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/commented_csvs_test",
            "nodes_only": True,
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search("all 3 rows in the CSV file", output)
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "metadata.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)

        configuration["input_csv"] = "test_excel_file_commented_row.xlsx"
        self.config_file_path = self.write_config_and_get_path(configuration)
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        assert re.search("all 4 rows in the CSV file", output)

        csv_file_path = os.path.join(self.temp_dir, "excel.csv")
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "excel.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)

        configuration["input_csv"] = (
            "https://docs.google.com/spreadsheets/d/13Mw7gtBy1A3ZhYEAlBzmkswIdaZvX18xoRBxfbgxqWc/edit#gid=0"
        )
        configuration["google_sheets_gid"] = 2133768507
        self.config_file_path = self.write_config_and_get_path(configuration)

        temp_bundle = os.environ.get("REQUESTS_CA_BUNDLE", None)
        if temp_bundle is not None:
            os.environ["REQUESTS_CA_BUNDLE"] = ""
        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        if temp_bundle is not None:
            os.environ["REQUESTS_CA_BUNDLE"] = temp_bundle
        output = output.decode().strip()
        assert re.search("all 5 rows in the CSV file", output)
        csv_file_path = os.path.join(
            self.current_dir, "assets", "commented_csvs_test", "google_sheet.csv"
        )
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "google_sheet.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


class TestCsvRowFilters(WorkbenchTest):

    def test_update_check(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_csv": "csv_row_filters_test.csv",
            "nodes_only": True,
            "input_dir": "tests/assets/csv_row_filters_test",
            "secure_ssl_only": False,
            "csv_row_filters": [
                "field_model:isnot:Digital document",
                "field_edtf_date:is:2020-01-01",
                "field_edtf_date:is:2000",
            ],
        }
        configuration = workbench_user.alter_configuration(configuration)
        self.config_file_path = self.write_config_and_get_path(configuration)
        self.preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "csv_row_filters_test.csv.preprocessed"
        )

        cmd = [self.workbench_path, "--config", self.config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()

        with open(self.preprocessed_csv_file_path, "r") as file:
            csv_rows = file.readlines()

        assert len(csv_rows) == 3
        assert csv_rows[1].strip() == ",issue_812_001,Issue 812 item 1,Image,2020-01-01"
        assert (
            csv_rows[2].strip()
            == "noo.jpg,issue_812_003,Issue 812 item 3,Binary,1999-01-01|2000"
        )

    def teardown_method(self, method_name):
        if os.path.exists(self.preprocessed_csv_file_path):
            os.remove(self.preprocessed_csv_file_path)
        if os.path.exists(self.config_file_path):
            os.remove(self.config_file_path)


if __name__ == "__main__":
    unittest.main()
