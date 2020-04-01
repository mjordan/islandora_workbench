import unittest
import subprocess


class ValidateTaxonomyFieldValuesTest(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(self.current_dir, 'assets', 'validate_taxonomy_fields_test', 'create.yml')
        self.create_cmd = ["./workbench", "--config", config_file_path, "--check"]

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertEqual(len(lines), 8)
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


if __name__ == '__main__':
    unittest.main()
