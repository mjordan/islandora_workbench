import os
import sys
import unittest
from unittest.mock import patch
import argparse
from collections import namedtuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from WorkbenchConfig import WorkbenchConfig


class TestWorkbenchConfig(unittest.TestCase):

    def setUp(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--config", required=True, help="Configuration file to use."
        )
        parser.add_argument(
            "--check",
            help="Check input data and exit without creating/updating/etc.",
            action="store_true",
        )
        parser.add_argument(
            "--get_csv_template",
            help="Generate a CSV template using the specified configuration file.",
            action="store_true",
        )
        parser.add_argument(
            "--quick_delete_node",
            help="Delete the node (and all attached media) identified by the URL).",
        )
        parser.add_argument(
            "--quick_delete_media",
            help="Delete the media (and attached file) identified by the URL).",
        )
        parser.add_argument(
            "--contactsheet", help="Generate a contact sheet.", action="store_true"
        )
        parser.add_argument(
            "--version", action="version", version="Islandora Workbench 0.0.0"
        )
        self.parser = parser

    def test_init_path_check_invalid_file(self):
        test_file_name = "/file/does/not/exist.yml"

        args = self.parser.parse_args(["--config", test_file_name])

        with (
            self.assertRaises(SystemExit) as exit_return,
            patch("WorkbenchConfig.logging") as mocked_logging,
        ):

            mocked_logging.return_value = None

            WorkbenchConfig(args)

        error_message = 'Error: Configuration file "' + test_file_name + '" not found.'
        self.assertEqual(exit_return.exception.code, error_message)

        # TODO: check values sent to logger

    def test_init_path_check_valid_file(self):
        test_file_name = "tests/assets/execute_bootstrap_script_test/config.yml"

        args = self.parser.parse_args(["--config", test_file_name])

        with (
            patch("sys.exit", side_effect=lambda x: None) as mock_exit,
            patch("WorkbenchConfig.WorkbenchConfig.path_check") as mocked_path_check,
            patch("WorkbenchConfig.logging") as mocked_logging,
        ):

            mocked_path_check.return_value = None
            mocked_logging.return_value = None

            WorkbenchConfig(args)

            mock_exit.assert_not_called()

        # TODO: check values sent to logger

    def test_get_config_valid_config_file_01(self):
        test_file_name = (
            "tests/assets/WorkbenchConfig_test/config_01_create_short_valid.yml"
        )

        args = self.parser.parse_args(["--config", test_file_name])

        with (
            patch("WorkbenchConfig.WorkbenchConfig.path_check") as mocked_path_check,
            patch("WorkbenchConfig.logging") as mocked_logging,
        ):

            mocked_path_check.return_value = None
            mocked_logging.return_value = None

            test_config_obj = WorkbenchConfig(args)

            test_config_dict = test_config_obj.get_config()

            # checking for config variables set in
            # tests/assets/execute_bootstrap_script_test/config.yml
            self.assertEqual(test_config_dict["task"], "create")
            self.assertEqual(test_config_dict["host"], "https://islandora.io")
            self.assertEqual(test_config_dict["username"], "admin")
            self.assertEqual(test_config_dict["password"], "password")
            # self.assertEqual(test_config_dict['media_type'], 'document')

        # TODO: check values sent to logger

    def test_get_config_expanduser_paths(self):
        test_file_name = (
            "tests/assets/WorkbenchConfig_test/config_03_expanduser_paths.yml"
        )

        args = self.parser.parse_args(["--config", test_file_name])

        with patch("WorkbenchConfig.logging.basicConfig"):
            test_config_obj = WorkbenchConfig(args)
            config = test_config_obj.get_config()

            for key, tilde_val in [
                ("input_dir", "~/workbench_input"),
                ("log_file_path", "~/workbench.log"),
                ("export_csv_file_path", "~/export.csv"),
                ("rollback_dir", "~/rollback"),
            ]:
                self.assertFalse(config[key].startswith("~"), f"{key} still contains ~")
                self.assertEqual(
                    os.path.normpath(config[key]),
                    os.path.normpath(os.path.expanduser(tilde_val)),
                )

            # List-based script paths.
            self.assertEqual(
                os.path.normpath(config["bootstrap"][0]),
                os.path.normpath(os.path.expanduser("~/scripts/bootstrap.sh")),
            )
            self.assertEqual(
                config["bootstrap"][1],
                "python " + os.path.expanduser("~/scripts/bootstrap.py"),
            )
            self.assertEqual(
                os.path.normpath(config["shutdown"][0]),
                os.path.normpath(os.path.expanduser("~/scripts/shutdown.sh")),
            )
            self.assertEqual(
                os.path.normpath(config["node_post_create"][0]),
                os.path.normpath(os.path.expanduser("~/scripts/post_create.sh")),
            )

            # Preprocessor dicts.
            self.assertEqual(
                os.path.normpath(config["preprocessors"][0]["field_one"]),
                os.path.normpath(os.path.expanduser("~/scripts/preprocess.sh")),
            )
            self.assertEqual(
                config["preprocessors"][1]["field_two"],
                "python " + os.path.expanduser("~/scripts/preprocess.py"),
            )


if __name__ == "__main__":
    unittest.main()
