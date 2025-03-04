"""unittest tests that require a live Drupal at https://islandora.dev. In most cases, the host URL,
credentials, etc. are in a configuration file referenced in the test.

This test file contains tests for --check. Files islandora_tests.py, islandora_tests_paged_content.py,
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


class TestFailToConnect(unittest.TestCase):

    def test_failed_to_connect(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "check_test", "fail_to_connect.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            self.assertRegex(
                output, "Workbench can't connect to https://somebadhost.org", ""
            )
        except subprocess.CalledProcessError as err:
            pass


class TestCreateCheck(unittest.TestCase):

    def setUp(self):

        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "check_test", "create.yml"
        )

        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_check(self):
        self.assertRegex(
            self.output, "Configuration and input data appear to be valid", ""
        )


class TestCheckFromGoogleSpreadsheetCheck(unittest.TestCase):
    """Note: This test fetches data from https://docs.google.com/spreadsheets/d/13Mw7gtBy1A3ZhYEAlBzmkswIdaZvX18xoRBxfbgxqWc/edit#gid=0."""

    def setUp(self):

        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "check_test", "google_sheet.yml"
        )

        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_from_google_spreadsheet_check(self):
        self.assertRegex(
            self.output, "Extracting CSV data from https://docs.google.com", ""
        )
        self.assertRegex(
            self.output, "Configuration and input data appear to be valid", ""
        )


class TestUpdateCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "check_test", "update.yml"
        )
        self.temp_dir = "/tmp"

        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_update_check(self):
        self.assertRegex(
            self.output, "Configuration and input data appear to be valid", ""
        )

    def tearDown(self):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "update.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestDeleteCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "check_test", "delete.yml"
        )
        self.temp_dir = "/tmp"

        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_delete_check(self):
        self.assertRegex(
            self.output, "Configuration and input data appear to be valid", ""
        )

    def tearDown(self):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "delete.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestAddMediaCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "check_test", "add_media.yml"
        )
        self.temp_dir = "/tmp"

        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_add_media_check(self):
        self.assertRegex(
            self.output, "Configuration and input data appear to be valid", ""
        )

    def tearDown(self):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "add_media.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestCreateMaxNodeTitleLengthCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "max_node_title_length_test", "create.yml"
        )
        self.temp_dir = "/tmp"

        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_for_too_long_titles(self):
        self.assertRegex(
            self.output,
            'CSV field "title" in record with ID 03 contains a value that is longer .32 characters',
            "",
        )
        self.assertRegex(
            self.output,
            'CSV field "title" in record with ID 04 contains a value that is longer .34 characters',
            "",
        )
        self.assertRegex(
            self.output,
            'CSV field "title" in record with ID 05 contains a value that is longer .36 characters',
            "",
        )

    def tearDown(self):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "create_max_node_title_length.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestUpdateWithMaxNodeTitleLengthCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        # First, we create some nodes so we have the node IDs for the update CSV file. We are
        # reusing the CSV data used by the TestCreateWithMaxNodeTitleLength test class.
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
        self.update_cmd = [
            "./workbench",
            "--config",
            self.update_config_file_path,
            "--check",
        ]

        self.temp_dir = "/tmp"

    def test_for_too_long_titles(self):
        create_output = subprocess.check_output(self.create_cmd)
        self.create_output = create_output.decode().strip()

        create_lines = self.create_output.splitlines()
        for line in create_lines:
            if "created at" in line:
                nid = line.rsplit("/", 1)[-1]
                nid = nid.strip(".")
                self.nids.append(nid)

        self.assertEqual(len(self.nids), 6)

        # Now that we have our node IDs, we write out the CSV file used in --check.
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

        check_output = subprocess.check_output(self.update_cmd)
        self.check_output = check_output.decode().strip()

        self.assertRegex(
            self.check_output, "contains a value that is longer .37 characters.", ""
        )
        self.assertRegex(
            self.check_output, "contains a value that is longer .39 characters.", ""
        )
        self.assertRegex(
            self.check_output, "contains a value that is longer .42 characters.", ""
        )
        self.assertRegex(
            self.check_output, "contains a value that is longer .44 characters.", ""
        )

    def tearDown(self):
        # Delete our test nodes we created.
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                "https://islandora.dev/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "max_node_title_length_test", "rollback.csv"
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        self.preprocessed_create_file_path = os.path.join(
            self.temp_dir, "create_max_node_title_length.csv.preprocessed"
        )
        if os.path.exists(self.preprocessed_create_file_path):
            os.remove(self.preprocessed_create_file_path)

        self.preprocessed_create_file_path = os.path.join(
            self.temp_dir, "update_max_node_title_length.csv.preprocessed"
        )
        if os.path.exists(self.preprocessed_create_file_path):
            os.remove(self.preprocessed_create_file_path)

        if os.path.exists(self.update_csv_file_path):
            os.remove(self.update_csv_file_path)


class TestTypedRelationBadRelatorCheck(unittest.TestCase):

    def setUp(self):
        self.temp_dir = "/tmp"

    def test_bad_relator_check_fail(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "typed_relation_test", "bad_relator.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            self.assertRegex(
                output,
                "does not use the structure required for typed relation fields",
                "",
            )
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "input_data",
            "rollback.csv",
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "bad_typed_relation_fail.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestTypedRelationBadUriCheck(unittest.TestCase):

    def setUp(self):
        self.temp_dir = "/tmp"

    def test_bad_uri_check_fail(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "typed_relation_test", "bad_uri.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            self.assertRegex(output, "example.com", "")
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "input_data",
            "rollback.csv",
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "bad_uri_fail.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestTypedRelationNewTypedRelationCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "add_new_typed_relation.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()
        self.temp_dir = "/tmp"

    def test_new_typed_relation_check(self):
        self.assertRegex(self.output, "new terms will be created as noted", "")

    def tearDown(self):
        self.rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "input_data",
            "rollback.csv",
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "new_typed_relation.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestTypedRelationNoNamespaceCheck(unittest.TestCase):

    def setUp(self):
        self.temp_dir = "/tmp"

    def test_no_namespace_check_fail(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "typed_relation_test", "no_namespace.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            self.assertRegex(output, "require a vocabulary namespace", "")
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(
            self.current_dir,
            "assets",
            "typed_relation_test",
            "input_data",
            "rollback.csv",
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "no_namespace.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestDelimiterCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "delimiter_test", "create_tab.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()
        self.temp_dir = "/tmp"

    def test_delimiter_check(self):
        self.assertRegex(self.output, "input data appear to be valid", "")

    def tearDown(self):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "metadata.tsv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestGeolocationCheck(unittest.TestCase):

    def setUp(self):
        self.temp_dir = "/tmp"

    def test_geolocation_check(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "geolocation_test", "bad_geocoordinates.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            self.assertRegex(output, r"+43.45-123.17", "")
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "bad_geocoorindates_fail.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestHeaderColumnMismatchCheck(unittest.TestCase):

    def setUp(self):
        self.temp_dir = "/tmp"

    def test_header_column_mismatch_fail(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "header_column_mismatch_test", "create.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        try:
            output = subprocess.check_output(cmd)
            output = output.decode().strip()
            self.assertRegex(output, "Row 2 of your CSV file does not", "")
        except subprocess.CalledProcessError as err:
            pass

    def tearDown(self):
        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "header_column_mismatch_test", "rollback.csv"
        )
        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "metadata.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestCreateWithFieldTemplatesCheck(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir, "assets", "create_with_field_templates_test", "create.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()
        self.temp_dir = "/tmp"

    def test_create_with_field_templates_check(self):
        self.assertRegex(
            self.output,
            "all 3 rows in the CSV file have the same number of columns as there are headers .6.",
            "",
        )

    def tearDown(self):
        templated_csv_path = os.path.join(self.temp_dir, "metadata.csv.preprocessed")
        os.remove(templated_csv_path)


class TestCommentedCsvs(unittest.TestCase):

    def test_commented_csv(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.temp_dir = "/tmp"

        config_file_path = os.path.join(
            current_dir, "assets", "commented_csvs_test", "raw_csv.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(output, "all 3 rows in the CSV file", "")
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "metadata.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)

        config_file_path = os.path.join(
            current_dir, "assets", "commented_csvs_test", "excel.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(output, "all 4 rows in the CSV file", "")
        csv_file_path = os.path.join(self.temp_dir, "excel.csv")
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "excel.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)

        config_file_path = os.path.join(
            current_dir, "assets", "commented_csvs_test", "google_sheets.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(output, "all 5 rows in the CSV file", "")
        csv_file_path = os.path.join(
            current_dir, "assets", "commented_csvs_test", "google_sheet.csv"
        )
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)
        preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "google_sheet.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_file_path):
            os.remove(preprocessed_csv_file_path)


class TestTaxonomies(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.taxonomies_config_file_path = os.path.join(
            self.current_dir, "assets", "taxonomies_test", "create.yml"
        )

        yaml = YAML()
        with open(self.taxonomies_config_file_path, "r") as f:
            config_file_contents = f.read()
        config_data = yaml.load(config_file_contents)
        config = {}
        for k, v in config_data.items():
            config[k] = v
        self.islandora_host = config["host"]
        self.islandora_username = config["username"]
        self.islandora_password = config["password"]

        self.create_cmd = ["./workbench", "--config", self.taxonomies_config_file_path]

        self.temp_dir = "/tmp"
        self.nids = list()

        nids = list()
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

    def test_validate_term_names_exist(self):
        taxonomies_terms_exist_config_file_path = os.path.join(
            self.current_dir, "assets", "taxonomies_test", "create.yml"
        )
        cmd = [
            "./workbench",
            "--config",
            taxonomies_terms_exist_config_file_path,
            "--check",
        ]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(
            output,
            "term IDs/names in CSV file exist in their respective taxonomies",
            "",
        )

    def test_validate_term_name_does_not_exist(self):
        taxonomies_term_name_does_not_exist_config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "taxonomies_test",
            "term_name_not_in_taxonomy.yml",
        )
        cmd = [
            "./workbench",
            "--config",
            taxonomies_term_name_does_not_exist_config_file_path,
            "--check",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(str(stdout), '"XPosters"', "")

    def test_validate_term_id_does_not_exist(self):
        taxonomies_term_id_does_not_exist_config_file_path = os.path.join(
            self.current_dir, "assets", "taxonomies_test", "term_id_not_in_taxonomy.yml"
        )
        cmd = [
            "./workbench",
            "--config",
            taxonomies_term_id_does_not_exist_config_file_path,
            "--check",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(str(stdout), "1000000", "")

    def tearDown(self):
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
                term_delete_response = requests.delete(
                    delete_term_url,
                    auth=(self.islandora_username, self.islandora_password),
                    verify=False,
                )

        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.taxonomies_config_file_path,
                "--quick_delete_node",
                self.islandora_host + "/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

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


class TestGoogleGid(unittest.TestCase):

    def setUp(self):
        self.temp_dir = "/tmp"

    def test_google_gid(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            current_dir, "assets", "google_gid_test", "gid_0.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(output, "OK, all 2 rows in the CSV file")

        config_file_path = os.path.join(
            current_dir, "assets", "google_gid_test", "gid_1867618389.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(output, "OK, all 3 rows in the CSV file")

        config_file_path = os.path.join(
            current_dir, "assets", "google_gid_test", "gid_390347846.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(output, "OK, all 5 rows in the CSV file")

        config_file_path = os.path.join(
            current_dir, "assets", "google_gid_test", "gid_953977578.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(output, "OK, all 1 rows in the CSV file")

    def tearDown(self):
        csv_path = os.path.join(self.temp_dir, "google_sheet.csv")
        if os.path.exists(csv_path):
            os.remove(csv_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "google_sheet.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)


class TestParentsPrecedeChildren(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.temp_dir = "/tmp"

    def test_good_csv(self):
        config_file_path = os.path.join(
            self.current_dir, "assets", "parents_precede_children_test", "good.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(output, "Configuration and input data appear to be valid")

    def test_bad_csv(self):
        config_file_path = os.path.join(
            self.current_dir, "assets", "parents_precede_children_test", "bad.yml"
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(str(stdout), '"c2p2" must come after', "")

    def tearDown(self):
        preprocessed_csv_path = os.path.join(self.temp_dir, "good.csv.preprocessed")
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)

        preprocessed_csv_path = os.path.join(self.temp_dir, "bad.csv.preprocessed")
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)


class TestCreateAllowMissingFiles(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.temp_dir = "/tmp"
        self.false_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "allow_missing_files_false.log",
        )
        self.true_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "allow_missing_files_true.log",
        )
        self.false_with_soft_checks_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "allow_missing_files_false_with_soft_checks.log",
        )

    def test_false(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "create_allow_missing_files_false.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(
            str(stdout),
            'identified in CSV "file" column for row with ID "03" not found',
            "",
        )

        with open(self.false_log_file_path) as log_file_false:
            log_data_false = log_file_false.read()
            self.assertRegex(log_data_false, 'ID "03" not found')

    def test_true(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "create_allow_missing_files_true.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(
            output,
            'Warning: "allow_missing_files" configuration setting is set to "true", and CSV "file" column values',
        )

        with open(self.true_log_file_path) as log_file_true:
            log_data_true = log_file_true.read()
            self.assertRegex(
                log_data_true, 'row with ID "06" not found or not accessible'
            )

    def test_false_with_soft_checks(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "create_allow_missing_files_false_with_soft_checks.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(
            output,
            'Warning: "perform_soft_checks" configuration setting is set to "true" and some values in the "file" column were not found',
        )

        with open(
            self.false_with_soft_checks_log_file_path
        ) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data, 'row with ID "03" not found'
            )

        with open(
            self.false_with_soft_checks_log_file_path
        ) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data,
                'row with ID "06" not found or not accessible',
            )

    def tearDown(self):
        if os.path.exists(self.false_log_file_path):
            os.remove(self.false_log_file_path)

        if os.path.exists(self.true_log_file_path):
            os.remove(self.true_log_file_path)

        if os.path.exists(self.false_with_soft_checks_log_file_path):
            os.remove(self.false_with_soft_checks_log_file_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "metadata_check.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)


class TestCreateAllowMissingFilesWithAdditionalFiles(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.temp_dir = "/tmp"
        self.false_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_false.log",
        )
        self.true_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_true.log",
        )
        self.false_with_soft_checks_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "additional_files_allow_missing_files_false_with_soft_checks.log",
        )

    def test_false(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "create_additional_files_allow_missing_files_false.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(
            str(stdout),
            'Additional file "https://www.lib.sfu.ca/xxxtttuuu.jpg" in CSV column "tn" in row with ID 005 not found',
            "",
        )

        with open(self.false_log_file_path) as log_file_false:
            log_data_false = log_file_false.read()
            self.assertRegex(
                log_data_false,
                'CVS row with ID 003 contains an empty value in its "tn" column',
            )
            self.assertRegex(
                log_data_false,
                'Additional file "https://www.lib.sfu.ca/xxxtttuuu.jpg" in CSV column "tn" in row with ID 005 not found or not accessible',
            )

    def test_true(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "create_additional_files_allow_missing_files_true.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(
            output,
            '"allow_missing_files" configuration setting is set to "true", and "additional_files" CSV columns',
            "",
        )

        with open(self.true_log_file_path) as log_file_true:
            log_data_true = log_file_true.read()
            self.assertRegex(
                log_data_true,
                'Additional file "additional_files_2_tn.jpg" in CSV column "tn" in row with ID 002 not found',
                "",
            )
            self.assertRegex(
                log_data_true,
                'Additional file "https://www.lib.sfu.ca/xxxtttuuu.jpg" in CSV column "tn" in row with ID 005 not found',
                "",
            )

    def test_false_with_soft_checks(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "create_additional_files_allow_missing_files_false_with_soft_checks.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(
            output, 'The "perform_soft_checks" configuration setting is set to "true"'
        )

        with open(
            self.false_with_soft_checks_log_file_path
        ) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data,
                'Additional file "additional_files_2_tn.jpg" in CSV column "tn" in row with ID 002 not found',
            )

        with open(
            self.false_with_soft_checks_log_file_path
        ) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data, ", no problems found"
            )

    def tearDown(self):
        if os.path.exists(self.false_log_file_path):
            os.remove(self.false_log_file_path)

        if os.path.exists(self.true_log_file_path):
            os.remove(self.true_log_file_path)

        if os.path.exists(self.false_with_soft_checks_log_file_path):
            os.remove(self.false_with_soft_checks_log_file_path)

        preprocessed_csv_path = os.path.join(
            self.temp_dir, "metadata_additional_files_check.csv.preprocessed"
        )
        if os.path.exists(preprocessed_csv_path):
            os.remove(preprocessed_csv_path)


class TestAddMediaAllowMissingFiles(unittest.TestCase):

    def setUp(self):
        # Create nodes to use in add_media task.
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
        self.false_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_allow_missing_files_false.log",
        )
        self.false_with_soft_checks_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_allow_missing_files_false_with_soft_checks.log",
        )
        self.true_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_allow_missing_files_true.log",
        )
        self.rollback_file_path = os.path.join(
            self.current_dir, "assets", "allow_missing_files_test", "rollback.csv"
        )
        self.add_media_csv_template_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media.csv.template",
        )
        self.add_media_csv_file_path = os.path.join(
            self.current_dir, "assets", "allow_missing_files_test", "add_media.csv"
        )
        self.temp_dir = "/tmp"
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
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_allow_missing_files_false.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(
            str(stdout),
            'File ".*missing_transcript.txt" identified in CSV "file" column for row with ID .* not found',
            "",
        )

        with open(self.false_log_file_path) as log_file_false:
            log_data_false = log_file_false.read()
            self.assertRegex(
                log_data_false, 'CSV row with ID .* contains an empty "file" value'
            )
            self.assertRegex(
                log_data_false,
                'File ".*missing_transcript.txt" identified in CSV "file" column for row with ID .* not found',
                "",
            )

    def test_true(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_allow_missing_files_true.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(
            output,
            'Warning: "allow_missing_files" configuration setting is set to "true", and CSV "file" column values containing missing',
        )

        with open(self.true_log_file_path) as log_file_true:
            log_data_true = log_file_true.read()
            self.assertRegex(
                log_data_true, 'CSV row with ID .* contains an empty "file" value', ""
            )
            # self.assertRegex(log_data_true, 'CVS row with ID .* contains an empty value in its "preservation" column', '')
            self.assertRegex(log_data_true, "INFO - .*no problems found", "")

    def test_false_with_soft_checks(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_allow_missing_files_false_with_soft_checks.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(
            output,
            'Warning: "perform_soft_checks" configuration setting is set to "true" and some values in the "file" column',
        )
        self.assertRegex(output, "Configuration and input data appear to be valid")

        with open(
            self.false_with_soft_checks_log_file_path
        ) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data,
                'CSV row with ID .* contains an empty "file" value',
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data,
                'File ".*missing_transcript.txt" identified in CSV "file" column for row with ID .* not found',
                "",
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data, "INFO - .*no problems found", ""
            )

    def tearDown(self):
        # Delete the nodes created in setUp.
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                self.islandora_host + "/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        if os.path.exists(self.add_media_csv_file_path):
            os.remove(self.add_media_csv_file_path)

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

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

        if os.path.exists(self.false_log_file_path):
            os.remove(self.false_log_file_path)

        if os.path.exists(self.false_with_soft_checks_log_file_path):
            os.remove(self.false_with_soft_checks_log_file_path)

        if os.path.exists(self.true_log_file_path):
            os.remove(self.true_log_file_path)


class TestAddMediaAllowMissingWithAdditionalFiles(unittest.TestCase):

    def setUp(self):
        # Create nodes to use in add_media task.
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
        self.false_with_additional_files_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_false.log",
        )
        self.false_with_soft_checks_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_false_with_soft_checks.log",
        )
        self.true_log_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_true.log",
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
        self.add_media_csv_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files.csv",
        )
        self.temp_dir = "/tmp"
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
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_false.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        stdout, stderr = proc.communicate()
        self.assertRegex(
            str(stdout),
            'Additional file "add_media_transcript_x.txt" in CSV column "transcript" in row with ID .* not found',
            "",
        )

        with open(self.false_with_additional_files_log_file_path) as log_file_false:
            log_data_false = log_file_false.read()
            self.assertRegex(
                log_data_false, 'CSV row with ID .* contains an empty "file" value'
            )
            self.assertRegex(
                log_data_false,
                'CVS row with ID .* contains an empty value in its "preservation" column',
            )
            self.assertRegex(
                log_data_false,
                'Additional file "add_media_transcript_x.txt" in CSV column "transcript" in row with ID .* not found',
                "",
            )

    def test_true(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_true.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(
            output,
            'Warning: "allow_missing_files" configuration setting is set to "true", and "additional_files" CSV columns containing missing',
        )

        with open(self.true_log_file_path) as log_file_true:
            log_data_true = log_file_true.read()
            self.assertRegex(
                log_data_true, 'CSV row with ID .* contains an empty "file" value', ""
            )
            self.assertRegex(
                log_data_true,
                'CVS row with ID .* contains an empty value in its "preservation" column',
                "",
            )
            self.assertRegex(log_data_true, "INFO - .*no problems found", "")

    def test_false_with_soft_checks(self):
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "allow_missing_files_test",
            "add_media_additional_files_allow_missing_files_false_with_soft_checks.yml",
        )
        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        output = output.decode().strip()
        self.assertRegex(
            output, '"perform_soft_checks" configuration setting is set to "true"', ""
        )
        self.assertRegex(output, "Configuration and input data appear to be valid", "")

        with open(
            self.false_with_soft_checks_log_file_path
        ) as log_file_false_with_soft_checks:
            log_file_false_with_soft_checks_data = (
                log_file_false_with_soft_checks.read()
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data,
                'CSV row with ID .* contains an empty "file" value',
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data,
                'CVS row with ID .* contains an empty value in its "preservation" column',
                "",
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data,
                'Additional file "add_media_transcript_x.txt" in CSV column "transcript" in row with ID .* not found',
                "",
            )
            self.assertRegex(
                log_file_false_with_soft_checks_data, "INFO - .*no problems found", ""
            )

    def tearDown(self):
        # Delete the nodes created in setUp.
        for nid in self.nids:
            quick_delete_cmd = [
                "./workbench",
                "--config",
                self.create_config_file_path,
                "--quick_delete_node",
                self.islandora_host + "/node/" + nid,
            ]
            quick_delete_output = subprocess.check_output(quick_delete_cmd)

        if os.path.exists(self.add_media_csv_file_path):
            os.remove(self.add_media_csv_file_path)

        if os.path.exists(self.rollback_file_path):
            os.remove(self.rollback_file_path)

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

        if os.path.exists(self.false_with_soft_checks_log_file_path):
            os.remove(self.false_with_soft_checks_log_file_path)

        if os.path.exists(self.true_log_file_path):
            os.remove(self.true_log_file_path)


class TestCsvRowFilters(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(
            self.current_dir,
            "assets",
            "csv_row_filters_test",
            "csv_row_filters_test.yml",
        )
        self.temp_dir = "/tmp"
        self.preprocessed_csv_file_path = os.path.join(
            self.temp_dir, "csv_row_filters_test.csv.preprocessed"
        )

        cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_update_check(self):
        file = open(self.preprocessed_csv_file_path)
        csv_rows = file.readlines()
        file.close()

        self.assertEqual(len(csv_rows), 3, "")
        self.assertEqual(
            csv_rows[1].strip(), ",issue_812_001,Issue 812 item 1,Image,2020-01-01", ""
        )
        self.assertEqual(
            csv_rows[2].strip(),
            "noo.jpg,issue_812_003,Issue 812 item 3,Binary,1999-01-01|2000",
            "",
        )

    def tearDown(self):
        if os.path.exists(self.preprocessed_csv_file_path):
            os.remove(self.preprocessed_csv_file_path)


if __name__ == "__main__":
    unittest.main()
