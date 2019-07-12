import unittest
import subprocess


class CheckTest(unittest.TestCase):

    def setUp(self):
        cmd = ["./workbench", "--config", "update.yml", "--check"]
        output = subprocess.check_output(cmd)
        self.output = output.decode().strip()

    def test_create_check(self):
        lines = self.output.splitlines()
        self.assertEqual(len(lines), 5)
        self.assertRegex(self.output, 'Configuration and input data appear to be valid', '')


if __name__ == '__main__':
    unittest.main()
