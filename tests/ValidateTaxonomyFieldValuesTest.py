import os
import unittest
import subprocess


class ValidateTaxonomyFieldValuesTest(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'validate_taxonomy_fields_test', 'create.yml')
        create_cmd = ["./workbench", "--config", config_file_path, "--check"]
        output = subprocess.check_output(create_cmd)
        self.output = output.decode().strip()

    def test_validate_term_ids(self):
        lines = self.output.splitlines()
        # We don't test for "OK, term IDs in CSV file exist in their respective taxonomies."
        # because the target Islandora might not have the Islandora Workbench Integration
        # module installed. So in effect, this test doesn't even test the term ID validation
        # feature. Issue about the best test here is at https://github.com/mjordan/islandora_workbench/issues/91.
        self.assertRegex(lines[-1], 'Configuration and input data appear to be valid', '')


if __name__ == '__main__':
    unittest.main()
