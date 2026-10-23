"""unittest tests for the rollback files and output CSV that Workbench writes.

These do not require a live Drupal. They characterize current behavior so that
code can be moved around (see the refactoring discussion) without changing what
ends up on disk. Where the current behavior looks accidental, the test says so.
"""

import copy
import csv
import datetime
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ruamel.yaml import YAML

sys.path.append(str(Path(os.path.abspath(__file__)).parent.parent.parent))
import workbench_utils

FIXED_START_TIME = datetime.datetime(2026, 3, 4, 5, 6, 7)


def base_config(tmp_dir: str, **overrides) -> dict:
    """The subset of config keys the rollback/output functions read."""
    config = {
        "task": "create",
        "host": "https://islandora.example",
        "username": "admin",
        "password": "s3cret",
        "use_workbench_permissions": False,
        "standalone_media_url": False,
        "secure_ssl_only": True,
        "include_password_in_rollback_config_file": False,
        "config_file": os.path.join(tmp_dir, "create.yml"),
        "current_config_file_path": os.path.join(tmp_dir, "create.yml"),
        "input_dir": tmp_dir,
        "input_csv": "metadata.csv",
        "id_field": "id",
        "csv_start_row": 0,
        "csv_stop_row": "",
        "rollback_dir": None,
        "rollback_file_include_node_info": False,
        "rollback_file_comments": None,
        "timestamp_rollback": False,
        "recovery_mode_starting_from_node_id": False,
        "output_csv": os.path.join(tmp_dir, "output.csv"),
        "output_csv_include_input_csv": False,
        "check": False,
    }
    config.update(overrides)
    return config


class TempDirTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

        patcher = mock.patch.object(
            workbench_utils, "EXECUTION_START_TIME", FIXED_START_TIME
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        # The secondary-task environment variable changes rollback file names.
        env_patcher = mock.patch.dict(os.environ, {}, clear=False)
        env_patcher.start()
        self.addCleanup(env_patcher.stop)
        os.environ.pop("ISLANDORA_WORKBENCH_SECONDARY_TASKS", None)

    def config(self, **overrides) -> dict:
        return base_config(self.tmp_dir, **overrides)

    def read(self, path: str) -> str:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()


class TestRollbackCsvFilePath(TempDirTestCase):

    def test_default_name_in_input_dir(self):
        """Test that the default rollback csv file path is in the expected location of input_dir."""
        path = workbench_utils.get_rollback_csv_filepath(self.config())
        self.assertEqual(
            path, os.path.join(os.path.abspath(self.tmp_dir), "rollback.csv")
        )

    def test_rollback_dir_takes_precedence_over_input_dir(self):
        """Test that the rollback directory takes precedence over the input directory."""
        rollback_dir = os.path.join(self.tmp_dir, "rb")
        path = workbench_utils.get_rollback_csv_filepath(
            self.config(rollback_dir=rollback_dir)
        )
        self.assertEqual(
            path, os.path.join(os.path.abspath(rollback_dir), "rollback.csv")
        )

    def test_timestamp_rollback(self):
        """Test that the timestamp is added to the rollback csv file name."""
        path = workbench_utils.get_rollback_csv_filepath(
            self.config(timestamp_rollback=True)
        )
        self.assertEqual(os.path.basename(path), "rollback.2026_03_04_05_06_07.csv")
        """Test that recovery mode adds a timestamp and recovery_mode suffix to the rollback csv file name."""
        path = workbench_utils.get_rollback_csv_filepath(
            self.config(recovery_mode_starting_from_node_id="123")
        )
        self.assertEqual(
            os.path.basename(path), "rollback.2026_03_04_05_06_07.recovery_mode.csv"
        )

    def test_non_numeric_recovery_mode_value_is_ignored(self):
        """Test that a non-numeric recovery mode value is ignored."""
        path = workbench_utils.get_rollback_csv_filepath(
            self.config(recovery_mode_starting_from_node_id="abc")
        )
        self.assertEqual(os.path.basename(path), "rollback.csv")

    def test_timestamp_wins_over_recovery_mode(self):
        """Test that the timestamp mode takes precedence over the recovery mode when naming the rollback file."""
        path = workbench_utils.get_rollback_csv_filepath(
            self.config(
                timestamp_rollback=True, recovery_mode_starting_from_node_id="123"
            )
        )
        self.assertEqual(os.path.basename(path), "rollback.2026_03_04_05_06_07.csv")

    def test_template_for_create_task(self):
        """Test that the rollback csv file name template is used for generating the rollback csv file name."""
        config = self.config(
            rollback_csv_filename_template="${input_csv_filename}_${csv_start_row}-${csv_stop_row}",
            csv_start_row=2,
            csv_stop_row=9,
        )
        path = workbench_utils.get_rollback_csv_filepath(config)
        self.assertEqual(os.path.basename(path), "metadata_2-9.csv")

    def test_template_uses_config_file_name_without_extension(self):
        """Test that the rollback csv file name template uses the config file name without the extension."""
        config = self.config(rollback_csv_filename_template="${config_filename}")
        path = workbench_utils.get_rollback_csv_filepath(config)
        self.assertEqual(path, os.path.join(self.tmp_dir, "create.csv"))

    def test_template_for_create_from_files_supports_config_filename(self):
        """Test that the rollback csv file name template for create_from_files supports the config_filename placeholder."""
        config = self.config(
            task="create_from_files",
            rollback_csv_filename_template="${config_filename}",
        )
        path = workbench_utils.get_rollback_csv_filepath(config)
        self.assertEqual(path, os.path.join(self.tmp_dir, "create.csv"))

    def test_template_with_unknown_placeholder_exits(self):
        """Test that the rollback csv file name template with an unknown placeholder exits."""
        config = self.config(
            task="create_from_files",
            rollback_csv_filename_template="${input_csv_filename}",
        )
        with self.assertRaises(SystemExit):
            workbench_utils.get_rollback_csv_filepath(config)

    def test_template_with_identifier_characters_exits(self):
        """Test that using $config_filename_x causes the string to be read as a placeholder and not the string "$config_filename_x"."""
        config = self.config(rollback_csv_filename_template="$config_filename_x")
        with self.assertRaises(SystemExit):
            workbench_utils.get_rollback_csv_filepath(config)

    def test_template_is_unsupported_for_other_tasks(self):
        # Test of what looks like an accident: only "create" and
        # "create_from_files" assign the basename, so any other task that sets a
        # template ends in an UnboundLocalError rather than a Workbench message.
        config = self.config(
            task="update", rollback_csv_filename_template="${config_filename}"
        )
        with self.assertRaises(UnboundLocalError):
            workbench_utils.get_rollback_csv_filepath(config)

    def test_secondary_task_appends_config_file_identifier(self):
        """Test that when a secondary task is running, the rollback csv file name includes the config file identifier."""
        secondary = [os.path.abspath(os.path.join(self.tmp_dir, "create.yml"))]
        os.environ["ISLANDORA_WORKBENCH_SECONDARY_TASKS"] = json.dumps(secondary)
        path = workbench_utils.get_rollback_csv_filepath(self.config())
        expected_id = workbench_utils.get_config_file_identifier(self.config())
        self.assertEqual(os.path.basename(path), f"rollback.csv.{expected_id}")

    def test_secondary_task_env_var_for_other_config_is_ignored(self):
        """Test that the secondary task environment variable for unknown config is ignored."""
        os.environ["ISLANDORA_WORKBENCH_SECONDARY_TASKS"] = json.dumps(
            ["/somewhere/else.yml"]
        )
        path = workbench_utils.get_rollback_csv_filepath(self.config())
        self.assertEqual(os.path.basename(path), "rollback.csv")

    def test_explicit_path_is_used_as_is(self):
        """Test that an explicit rollback csv file path is used as is, without any modifications."""
        explicit = os.path.join(self.tmp_dir, "custom", "my_rollback.csv")
        path = workbench_utils.get_rollback_csv_filepath(
            self.config(rollback_csv_file_path=explicit)
        )
        self.assertEqual(path, explicit)

    def test_explicit_path_with_timestamp(self):
        """Test that an explicit rollback csv file path with a timestamp is used expected."""
        explicit = os.path.join(self.tmp_dir, "my_rollback.csv")
        path = workbench_utils.get_rollback_csv_filepath(
            self.config(rollback_csv_file_path=explicit, timestamp_rollback=True)
        )
        self.assertEqual(
            path, os.path.join(self.tmp_dir, "my_rollback.2026_03_04_05_06_07.csv")
        )

    def test_empty_explicit_path_falls_back_to_default(self):
        """Test that an empty explicit rollback csv file path falls back to the default."""
        path = workbench_utils.get_rollback_csv_filepath(
            self.config(rollback_csv_file_path="")
        )
        self.assertEqual(os.path.basename(path), "rollback.csv")


class TestRollbackConfigFilePath(TempDirTestCase):

    def get_path(self, **overrides):
        return workbench_utils.get_rollback_config_filepath(self.config(**overrides))

    def test_default_name_in_workbench_dir(self):
        """Test that without "rollback_config_file_path" the file lands next to sys.path[0]."""
        path = self.get_path()
        self.assertEqual(path, os.path.join(sys.path[0], "rollback.yml"))

    def test_timestamp_rollback(self):
        """Test that the timestamp is added to the rollback config file name."""
        path = self.get_path(timestamp_rollback=True)
        self.assertEqual(os.path.basename(path), "rollback.2026_03_04_05_06_07.yml")

    def test_recovery_mode(self):
        """Test that recovery mode adds a timestamp and recovery_mode suffix to the rollback config file name."""
        path = self.get_path(recovery_mode_starting_from_node_id=45)
        self.assertEqual(
            os.path.basename(path), "rollback.2026_03_04_05_06_07.recovery_mode.yml"
        )

    def test_template(self):
        """Test that the rollback config file name template is used for generating the rollback config file name."""
        path = self.get_path(
            rollback_config_filename_template="${input_csv_filename}-${csv_start_row}"
        )
        self.assertEqual(os.path.basename(path), "metadata-0.yml")

    def test_template_with_bad_placeholder_exits(self):
        """Test that a bad placeholder in the rollback config file name template causes a SystemExit."""
        with self.assertRaises(SystemExit):
            self.get_path(
                task="create_from_files",
                rollback_config_filename_template="${csv_start_row}",
            )

    def test_explicit_path(self):
        """Test that an explicit rollback config file path is used."""
        explicit = os.path.join(self.tmp_dir, "rb_config.yml")
        self.assertEqual(self.get_path(rollback_config_file_path=explicit), explicit)

    def test_explicit_path_with_timestamp(self):
        """Test that an explicit rollback config file path with a timestamp is used."""
        explicit = os.path.join(self.tmp_dir, "rb_config.yml")
        path = self.get_path(
            rollback_config_file_path=explicit, timestamp_rollback=True
        )
        self.assertEqual(
            path, os.path.join(self.tmp_dir, "rb_config.2026_03_04_05_06_07.yml")
        )


class TestRollbackConfigComments(TempDirTestCase):

    def test_header_comment_lines(self):
        """Test that the header comment lines are correctly generated."""
        comments = workbench_utils.get_rollback_config_comments(self.config())
        lines = comments.splitlines()
        self.assertEqual(
            lines[0], '# Generated by a "create" task started 2026:03:04 05:06:07 using'
        )
        self.assertTrue(lines[1].startswith('# config file "'))
        self.assertIn('input CSV "metadata.csv".', lines[1])
        self.assertTrue(comments.endswith("\n"))

    def test_task_name_is_reported(self):
        """Test that the task name is reported in the rollback config comments."""
        comments = workbench_utils.get_rollback_config_comments(
            self.config(task="create_from_files")
        )
        self.assertIn('"create_from_files" task', comments)

    def test_user_comments_are_appended_one_per_line(self):
        """Test that user comments are appended to the rollback config comments, one per line."""
        comments = workbench_utils.get_rollback_config_comments(
            self.config(rollback_file_comments=["Batch 7", "Ingested by Jo"])
        )
        lines = comments.splitlines()
        self.assertEqual(lines[2:], ["# Batch 7", "# Ingested by Jo"])

    def test_empty_comment_list_adds_nothing(self):
        """Test that an empty list of user comments adds nothing to the rollback config comments."""
        comments = workbench_utils.get_rollback_config_comments(
            self.config(rollback_file_comments=[])
        )
        self.assertEqual(len(comments.splitlines()), 2)


class TestPrepRollbackCsv(TempDirTestCase):

    def test_header_only_node_id(self):
        """Test that the rollback CSV is created with only the node_id header when node info is not included."""
        path = os.path.join(self.tmp_dir, "rollback.csv")
        workbench_utils.prep_rollback_csv(self.config(), path)
        lines = self.read(path).splitlines()
        self.assertEqual(lines[0], "node_id")
        self.assertTrue(all(line.startswith("#") for line in lines[1:]))

    def test_header_with_node_info_uses_configured_id_field(self):
        """Test that the rollback CSV header includes the configured ID field when node info is included."""
        path = os.path.join(self.tmp_dir, "rollback.csv")
        workbench_utils.prep_rollback_csv(
            self.config(rollback_file_include_node_info=True, id_field="record_id"),
            path,
        )
        self.assertEqual(
            self.read(path).splitlines()[0],
            "node_id,record_id,title,field_member_of,file",
        )

    def test_existing_file_is_replaced(self):
        """Test that an existing rollback CSV file is replaced when prep_rollback_csv is called."""
        path = os.path.join(self.tmp_dir, "rollback.csv")
        with open(path, "w") as f:
            f.write("node_id\n999\n")
        workbench_utils.prep_rollback_csv(self.config(), path)
        self.assertNotIn("999", self.read(path))

    def test_user_comments_land_in_the_csv(self):
        """Test that user comments are included in the rollback CSV file."""
        path = os.path.join(self.tmp_dir, "rollback.csv")
        workbench_utils.prep_rollback_csv(
            self.config(rollback_file_comments=["keep me"]), path
        )
        self.assertIn("# keep me", self.read(path))

    def test_unwritable_location_exits(self):
        """Test that attempting to write the rollback CSV to an unwritable location causes a SystemExit."""
        path = os.path.join(self.tmp_dir, "no_such_dir", "rollback.csv")
        with self.assertRaises(SystemExit):
            workbench_utils.prep_rollback_csv(self.config(), path)


class TestWriteRollbackNodeId(TempDirTestCase):

    def write(self, config, rows):
        """Prep the CSV, append rows, and return the path."""
        path = workbench_utils.get_rollback_csv_filepath(config)
        workbench_utils.prep_rollback_csv(config, path)
        for node_id, csv_id, title, file_path, member_of in rows:
            workbench_utils.write_rollback_node_id(
                config, node_id, csv_id, title, file_path, member_of, path
            )
        return path

    def data_lines(self, path):
        """Return the data lines from the CSV file, excluding header and comment lines."""
        return [
            line
            for line in self.read(path).splitlines()
            if line and not line.startswith("#")
        ]

    def test_node_ids_only(self):
        """Test that the rollback CSV contains only the node ids when node info is not included."""
        path = self.write(
            self.config(),
            [(10, "a", "A", "a.tif", ""), ("11", "b", "B", "b.tif", "")],
        )
        self.assertEqual(self.data_lines(path), ["node_id", "10", "11"])

    def test_node_info_columns(self):
        """Test that the rollback CSV contains the correct columns when node info is included."""
        path = self.write(
            self.config(rollback_file_include_node_info=True),
            [(10, "a", "A title", "a.tif", "5")],
        )
        self.assertEqual(
            self.data_lines(path),
            [
                "node_id,id,title,field_member_of,file",
                "10,a,A title,5,a.tif",
            ],
        )

    def test_node_info_quotes_values_containing_commas(self):
        """Test that values containing commas are correctly quoted in the rollback CSV when node info is included."""
        path = self.write(
            self.config(rollback_file_include_node_info=True),
            [(10, "a", "Smith, John: a life", "dir/a.tif", "")],
        )
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(line for line in f if not line.startswith("#")))
        self.assertEqual(rows[0]["title"], "Smith, John: a life")

    def test_node_info_preserves_unicode_titles(self):
        """Test that Unicode titles are preserved in the rollback CSV when node info is included."""
        path = self.write(
            self.config(rollback_file_include_node_info=True),
            [(10, "a", "Œuvres complètes — 日本語", "a.tif", "")],
        )
        self.assertIn("Œuvres complètes — 日本語", self.read(path))

    def test_empty_id_for_pages_and_create_from_files(self):
        """Test that an empty id field is written for pages and create_from_files tasks when node info is included."""
        path = self.write(
            self.config(rollback_file_include_node_info=True, task="create_from_files"),
            [(10, "", "page 1", "book/001.tif", "9")],
        )
        self.assertEqual(self.data_lines(path)[1], "10,,page 1,9,book/001.tif")

    def test_path_argument_is_ignored_in_favor_of_config(self):
        """Test showing that the rollback CSV path argument is ignored in favor of the config's rollback_csv_file_path."""
        config = self.config()
        real_path = workbench_utils.get_rollback_csv_filepath(config)
        workbench_utils.prep_rollback_csv(config, real_path)
        decoy = os.path.join(self.tmp_dir, "decoy.csv")
        workbench_utils.write_rollback_node_id(config, 5, "x", "t", "f", "", decoy)
        self.assertFalse(os.path.exists(decoy))
        self.assertIn("5", self.data_lines(real_path))

    def test_secondary_task_rows_go_to_suffixed_file(self):
        """Test that when a secondary task is running, the rollback CSV rows are written to the suffixed file."""
        secondary = [os.path.abspath(os.path.join(self.tmp_dir, "create.yml"))]
        os.environ["ISLANDORA_WORKBENCH_SECONDARY_TASKS"] = json.dumps(secondary)
        path = self.write(self.config(), [(1, "a", "A", "a.tif", "")])
        self.assertNotEqual(os.path.basename(path), "rollback.csv")
        self.assertEqual(self.data_lines(path), ["node_id", "1"])


class TestWriteRollbackConfig(TempDirTestCase):

    def write(self, **overrides):
        config = self.config(
            rollback_config_file_path=os.path.join(self.tmp_dir, "rb.yml"),
            **overrides,
        )
        rollback_csv = os.path.join(self.tmp_dir, "rollback.csv")
        workbench_utils.write_rollback_config(config, rollback_csv)
        path = workbench_utils.get_rollback_config_filepath(config)
        return path, rollback_csv

    def load(self, path):
        with open(path) as f:
            return YAML(typ="safe").load(f)

    def test_is_a_delete_task_config_pointing_at_the_rollback_csv(self):
        """Test the contents of the rollback config file to ensure it is a delete task pointing at the rollback CSV."""
        path, rollback_csv = self.write()
        loaded = self.load(path)
        self.assertEqual(loaded["task"], "delete")
        self.assertEqual(loaded["host"], "https://islandora.example")
        self.assertEqual(loaded["input_csv"], rollback_csv)
        self.assertEqual(loaded["input_dir"], self.tmp_dir)
        self.assertEqual(loaded["secure_ssl_only"], True)
        self.assertEqual(loaded["use_workbench_permissions"], False)
        self.assertEqual(loaded["standalone_media_url"], False)

    def test_password_is_omitted_by_default(self):
        """Test that the password is omitted from the rollback config file by default."""
        path, _ = self.write()
        loaded = self.load(path)
        self.assertEqual(loaded["username"], "admin")
        self.assertIsNone(loaded["password"])
        self.assertNotIn("s3cret", self.read(path))

    def test_password_included_when_requested(self):
        """Test that the password is included in the rollback config file when requested."""
        path, _ = self.write(include_password_in_rollback_config_file=True)
        self.assertEqual(self.load(path)["password"], "s3cret")

    def test_credentials_file_replaces_username_and_password(self):
        """Test that a credentials file replaces the username and password in the rollback config file."""
        path, _ = self.write(credentials_file_path="/etc/wb/creds.yml")
        loaded = self.load(path)
        self.assertEqual(loaded["credentials_file_path"], "/etc/wb/creds.yml")
        self.assertNotIn("username", loaded)
        self.assertNotIn("password", loaded)

    def test_comments_precede_the_yaml(self):
        """Test that comments are correctly placed before the YAML content in the rollback config file."""
        path, _ = self.write(rollback_file_comments=["Batch 7"])
        lines = self.read(path).splitlines()
        first_yaml_line = next(
            i for i, line in enumerate(lines) if not line.startswith("#")
        )
        header = lines[:first_yaml_line]
        self.assertTrue(header[0].startswith('# Generated by a "create" task'))
        self.assertIn("# Batch 7", header)
        # Every comment is in the leading block; none appear among the YAML lines.
        self.assertFalse(any(line.startswith("#") for line in lines[first_yaml_line:]))
        self.assertTrue(lines[first_yaml_line].startswith("task:"))
        # Comments are YAML comments, so the file must still load cleanly.
        self.assertEqual(self.load(path)["task"], "delete")


def make_node_json(**overrides) -> str:
    """A reduced version of the JSON Drupal returns when a node is created."""
    node = {
        "nid": [{"value": 321}],
        "uuid": [{"value": "0f9c5d0e-1111-2222-3333-444455556666"}],
        "vid": [{"value": 400}],
        "langcode": [{"value": "en"}],
        "published": [{"value": True}],
        "type": [{"target_id": "islandora_object"}],
        "status": [{"value": True}],
        "title": [{"value": "A test node"}],
        "created": [{"value": 1700000000}],
        "promote": [{"value": False}],
        "sticky": [{"value": False}],
    }
    node.update(overrides)
    return json.dumps(node)


class TestWriteToOutputCsv(TempDirTestCase):

    def rows(self, config):
        with open(config["output_csv"], newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_header_and_first_row(self):
        """Test that the output CSV is created with the correct header and first row based on the node JSON."""
        config = self.config()
        workbench_utils.write_to_output_csv(config, "rec-1", make_node_json())
        rows = self.rows(config)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["id"], "rec-1")
        self.assertEqual(row["node_id"], "321")
        self.assertEqual(row["uuid"], "0f9c5d0e-1111-2222-3333-444455556666")
        self.assertEqual(row["title"], "A test node")
        self.assertEqual(row["content_type"], "islandora_object")
        self.assertEqual(row["langcode"], "en")

    def test_id_field_is_first_column(self):
        """Test that the configured id_field is used as the ID in the output CSV."""
        config = self.config(id_field="record_id")
        workbench_utils.write_to_output_csv(config, "r1", make_node_json())
        with open(config["output_csv"], encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        self.assertEqual(header[0], "record_id")

    def test_true_and_false_are_written_as_0_or_1(self):
        """Test that boolean values in the node JSON are written as "0" or "1" in the output CSV."""
        config = self.config()
        workbench_utils.write_to_output_csv(
            config,
            "a",
            make_node_json(status=[{"value": True}], promote=[{"value": False}]),
        )
        workbench_utils.write_to_output_csv(
            config,
            "b",
            make_node_json(status=[{"value": False}], promote=[{"value": True}]),
        )
        a, b = self.rows(config)
        self.assertEqual((a["published"], a["promote"]), ("1", "0"))
        self.assertEqual((b["published"], b["promote"]), ("0", "1"))

    def test_header_is_written_only_once(self):
        """Test that the node_id header is only written once."""
        config = self.config()
        for i in range(3):
            workbench_utils.write_to_output_csv(config, f"r{i}", make_node_json())
        text = self.read(config["output_csv"])
        self.assertEqual(text.count("node_id"), 1)
        self.assertEqual([r["id"] for r in self.rows(config)], ["r0", "r1", "r2"])

    def test_rows_are_appended_to_an_existing_file_with_header(self):
        """Test that a secondary call appends rows to the existing output CSV file without duplicating the header."""
        config = self.config()
        workbench_utils.write_to_output_csv(config, "r0", make_node_json())
        # A later run (i.e. a secondary task or recovery mode) appends.
        workbench_utils.write_to_output_csv(config, "r1", make_node_json())
        self.assertEqual(len(self.rows(config)), 2)
        text = self.read(config["output_csv"])
        # Still only one header line.
        self.assertEqual(text.count("node_id"), 1)

    def test_internal_drupal_fields_are_not_written(self):
        """Test that internal Drupal fields are not included in the output CSV."""
        config = self.config()
        workbench_utils.write_to_output_csv(config, "a", make_node_json())
        with open(config["output_csv"], encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        for removed in ["nid", "vid", "type", "status", "created", "sticky"]:
            self.assertNotIn(removed, header)

    def test_unicode_title_round_trips(self):
        """Test that a Unicode title is preserved when written to the output CSV."""
        config = self.config()
        workbench_utils.write_to_output_csv(
            config, "a", make_node_json(title=[{"value": "Ça va, 日本語"}])
        )
        self.assertEqual(self.rows(config)[0]["title"], "Ça va, 日本語")

    def test_create_from_files_forces_id_field_to_ID(self):
        """Test that when the task is "create_from_files", the id_field is forced to "ID" in the output CSV."""
        config = self.config(task="create_from_files", id_field="filename")
        workbench_utils.write_to_output_csv(config, "scan01.tif", make_node_json())
        self.assertEqual(config["id_field"], "ID")
        self.assertEqual(self.rows(config)[0]["ID"], "scan01.tif")

    def test_unix_line_endings(self):
        """Test that the output CSV uses Unix line endings."""
        config = self.config()
        workbench_utils.write_to_output_csv(config, "a", make_node_json())
        self.assertNotIn("\r", self.read(config["output_csv"]))


class TestWriteToOutputCsvIncludingInputCsv(TempDirTestCase):
    """Behavior when output_csv_include_input_csv is true."""

    FIELD_DEFS = {"field_description": {"field_type": "text"}}

    def write(self, config, row_id, input_row, node_json=None):
        node_json = node_json or make_node_json(
            field_description=[{"value": "from drupal"}]
        )
        with (
            # When calling workbench_utils.get_field_definitions, return FIELD_DEFS
            mock.patch.object(
                workbench_utils, "get_field_definitions", return_value=self.FIELD_DEFS
            ),
            # When calling workbench_utils.serialize_field_json, return a fixed string
            mock.patch.object(
                workbench_utils, "serialize_field_json", return_value="SERIALIZED"
            ),
        ):
            workbench_utils.write_to_output_csv(
                config, row_id, node_json, copy.deepcopy(input_row)
            )

    def rows(self, config):
        """Return the rows of the output CSV as a list of dictionaries."""
        with open(config["output_csv"], newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_input_columns_are_added_after_node_columns(self):
        """Test that when output_csv_include_input_csv is true, the input CSV columns are added after the node columns in the output CSV."""
        config = self.config(output_csv_include_input_csv=True)
        self.write(config, "a", {"id": "a", "title": "T", "extra_note": "hello"})
        with open(config["output_csv"], encoding="utf-8") as f:
            header = f.readline().strip().split(",")
        self.assertIn("extra_note", header)
        self.assertGreater(header.index("extra_note"), header.index("title"))
        self.assertEqual(self.rows(config)[0]["extra_note"], "hello")

    def test_reserved_input_columns_are_dropped(self):
        """Test that reserved input CSV columns are dropped from the output CSV when output_csv_include_input_csv is true."""
        config = self.config(output_csv_include_input_csv=True)
        input_row = {
            "id": "a",
            "title": "T",
            "file": "a.tif",
            "parent_id": "p",
            "url_alias": "/a",
            "image_alt_text": "alt",
            "checksum": "abc",
        }
        self.write(config, "a", input_row)
        row = self.rows(config)[0]
        for reserved in [
            "file",
            "parent_id",
            "url_alias",
            "image_alt_text",
            "checksum",
        ]:
            self.assertNotIn(reserved, row)

    def test_additional_files_columns_are_dropped(self):
        """Test that additional files columns are dropped from the output CSV when output_csv_include_input_csv is true."""
        config = self.config(
            output_csv_include_input_csv=True,
            additional_files=[{"transcript": "http://pcdm.org/use#Transcript"}],
        )
        self.write(config, "a", {"id": "a", "title": "T", "transcript": "t.txt"})
        self.assertNotIn("transcript", self.rows(config)[0])

    def test_drupal_field_values_are_serialized_into_field_columns(self):
        """Test that Drupal field values are serialized into the corresponding field columns in the output CSV when output_csv_include_input_csv is true."""
        config = self.config(output_csv_include_input_csv=True)
        self.write(config, "a", {"id": "a", "title": "T"})
        self.assertEqual(self.rows(config)[0]["field_description"], "SERIALIZED")

    def test_input_value_overrides_serialized_value_for_same_column(self):
        """Test that when output_csv_include_input_csv is true, the input CSV value overrides the serialized Drupal field value for the same column in the output CSV."""
        config = self.config(output_csv_include_input_csv=True)
        self.write(config, "a", {"id": "a", "field_description": "typed in CSV"})
        self.assertEqual(self.rows(config)[0]["field_description"], "typed in CSV")

    def test_published_and_langcode_come_from_drupal_not_input(self):
        """Test that the published and langcode values come from Drupal and not the input CSV when output_csv_include_input_csv is true."""
        config = self.config(output_csv_include_input_csv=True)
        self.write(
            config, "a", {"id": "a", "published": "0", "langcode": "fr", "promote": "1"}
        )
        row = self.rows(config)[0]
        self.assertEqual(row["published"], "1")
        self.assertEqual(row["langcode"], "en")
        self.assertEqual(row["promote"], "0")

    def test_input_row_none_writes_only_node_data(self):
        """Test that when output_csv_include_input_csv is true and the input row is None, only the node data is written to the output CSV."""
        config = self.config(output_csv_include_input_csv=True)
        workbench_utils.write_to_output_csv(config, "a", make_node_json(), None)
        row = self.rows(config)[0]
        self.assertEqual(row["node_id"], "321")

    def test_flag_off_ignores_input_row(self):
        """Test that when output_csv_include_input_csv is false, the input row is ignored and not included in the output CSV."""
        config = self.config(output_csv_include_input_csv=False)
        self.write(config, "a", {"id": "a", "extra_note": "hello"})
        self.assertNotIn("extra_note", self.rows(config)[0])

    def test_callers_row_is_not_mutated_when_deep_copied(self):
        """Test that when output_csv_include_input_csv is true, the input row passed to write_to_output_csv is not changed if it is deep copied."""
        # Documented requirement in the docstring: callers pass a deepcopy
        # because the function deletes reserved columns from the row it is given.
        config = self.config(output_csv_include_input_csv=True)
        original = {"id": "a", "title": "T", "file": "a.tif"}
        passed = copy.deepcopy(original)
        with (
            mock.patch.object(
                workbench_utils, "get_field_definitions", return_value=self.FIELD_DEFS
            ),
            mock.patch.object(
                workbench_utils, "serialize_field_json", return_value="S"
            ),
        ):
            workbench_utils.write_to_output_csv(config, "a", make_node_json(), passed)
        self.assertNotIn("file", passed)
        self.assertIn("file", original)


class TestCheckRollbackFilePathDirectories(TempDirTestCase):

    def test_writable_directories_pass(self):
        """Test that when the directories for the rollback config file path exist and are writable, no exception is raised."""
        config = self.config(
            rollback_config_file_path=os.path.join(self.tmp_dir, "rb.yml"),
        )
        workbench_utils.check_rollback_file_path_directories(config)

    def test_missing_rollback_config_directory_exits(self):
        """Test that when the directory for the rollback config file path does not exist, a SystemExit is raised."""
        config = self.config(
            rollback_config_file_path=os.path.join(self.tmp_dir, "nope", "rb.yml"),
        )
        with self.assertRaises(SystemExit) as cm:
            workbench_utils.check_rollback_file_path_directories(config)
        self.assertIn("rollback configuration file path", str(cm.exception))

    def test_missing_rollback_csv_directory_exits(self):
        """Test that when the directory for the rollback CSV file path does not exist, a SystemExit is raised."""
        config = self.config(
            rollback_config_file_path=os.path.join(self.tmp_dir, "rb.yml"),
            rollback_csv_file_path=os.path.join(self.tmp_dir, "nope", "rb.csv"),
        )
        with self.assertRaises(SystemExit) as cm:
            workbench_utils.check_rollback_file_path_directories(config)
        self.assertIn("rollback CSV file path", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
