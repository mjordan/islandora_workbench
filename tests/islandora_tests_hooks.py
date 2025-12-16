"""unittest tests that require a live Drupal at https://islandora.dev. In most cases, the host URL,
credentials, etc. are in a configuration file referenced in the test.

This test file contains tests for Workbench's hooks. Files islandora_tests.py, islandora_tests_paged_content.py,
and islandora_tests_checks.py also contain tests that interact with an Islandora instance.
"""

import sys
import os
import subprocess
import tempfile

from workbench_test_class import (
    WorkbenchTest,
    collect_nids_from_create_output,
    cleanup_paths,
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils


class TestExecuteBootstrapScript:

    def test_execute_python_script(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))

        script_path = os.path.join(
            dir_path, "assets", "execute_bootstrap_script_test", "script.py"
        )
        config_file_path = os.path.join(
            dir_path, "assets", "execute_bootstrap_script_test", "config.yml"
        )

        output, return_code = workbench_utils.execute_bootstrap_script(
            script_path, config_file_path
        )
        assert output.strip() == "Hello"


class TestExecutePreprocessorScript:

    def test_preprocessor_script_single_field_value(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        script_path = os.path.join(
            dir_path, "assets", "preprocess_field_data", "script.py"
        )
        output, return_code = workbench_utils.preprocess_field_data(
            "|", "hello", script_path
        )
        assert output.strip() == "HELLO"

    def test_preprocessor_script_multiple_field_value(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        script_path = os.path.join(
            dir_path, "assets", "preprocess_field_data", "script.py"
        )
        output, return_code = workbench_utils.preprocess_field_data(
            "|", "hello|there", script_path
        )
        assert output.strip() == "HELLO|THERE"


class TestExecutePostActionEntityScript(WorkbenchTest):
    """Note: Only tests for creating nodes."""

    def test_post_task_entity_script(self, workbench_user):
        configuration = {
            "task": "create",
            "host": "https://islandora.dev",
            "input_dir": "tests/assets/execute_post_action_entity_script_test",
            "nodes_only": True,
            "node_post_create": [
                "tests/assets/execute_post_action_entity_script_test/script.py"
            ],
            "secure_ssl_only": False,
        }
        configuration = workbench_user.alter_configuration(configuration)
        config_file_path = self.write_config_and_get_path(configuration)
        create_cmd = ["./workbench", "--config", config_file_path]
        create_output = subprocess.check_output(create_cmd, cwd=self.workbench_dir)
        create_output = create_output.decode().strip()
        nids = collect_nids_from_create_output(create_output)

        # The post-action script writes the file containing the titles of the nodes just created.
        output_file_path = os.path.join(
            tempfile.gettempdir(), "execute_post_action_entity_script.dat"
        )
        with open(output_file_path, "r") as lines:
            titles = lines.readlines()
        try:
            assert titles[0].strip() == "First title"
            assert titles[1].strip() == "Second title"
        finally:

            for nid in nids:
                quick_delete_cmd = [
                    "./workbench",
                    "--config",
                    config_file_path,
                    "--quick_delete_node",
                    "https://islandora.dev/node/" + nid,
                ]
                subprocess.check_output(quick_delete_cmd, cwd=self.workbench_dir)

            cleanup_paths(
                config_file_path,
                output_file_path,
                os.path.join(
                    self.current_dir,
                    "assets",
                    "execute_post_action_entity_script_test",
                    "rollback.csv",
                ),
                os.path.join(self.temp_dir, "metadata.csv.preprocessed"),
            )
