import os
import tempfile
import unittest
import subprocess


class CreateTest(unittest.TestCase):

    def setUp(self):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        create_config_file_path = os.path.join(self.current_dir, 'assets', 'createtest', 'create.yml')
        self.create_cmd = ["./workbench", "--config", create_config_file_path]

        self.temp_dir = tempfile.gettempdir()
        self.nid_file = os.path.join(self.temp_dir, 'workbenchcreatetestnids.txt')

    def test_create_check(self):
        nids = list()
        create_output = subprocess.check_output(self.create_cmd)
        create_output = create_output.decode().strip()
        create_lines = create_output.splitlines()
        with open(self.nid_file, "a") as fh:
            fh.write("node_id\n")
            for line in create_lines:
                if 'created at' in line:
                    nid = line.rsplit('/', 1)[-1]
                    nid = nid.strip('.')
                    nids.append(nid)
                    fh.write(nid + "\n")

        self.assertEqual(len(nids), 5)

    def tearDown(self):
        delete_config_file_path = os.path.join(self.current_dir, 'assets', 'createtest', 'delete.yml')
        delete_cmd = ["./workbench", "--config", delete_config_file_path]
        delete_output = subprocess.check_output(delete_cmd)
        delete_output = delete_output.decode().strip()
        delete_lines = delete_output.splitlines()
        os.remove(self.nid_file)


if __name__ == '__main__':
    unittest.main()
