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

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertRegex(lines[6], 'their respective taxonomies', '')


if __name__ == '__main__':
    unittest.main()
