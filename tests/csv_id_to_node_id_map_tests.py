"""unittest tests for the CSV ID to node ID map. Do not require a live Drupal."""

import os
import tempfile
import shutil
import subprocess
import unittest


class TestDumpCsv(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.script_path = os.path.join("scripts", "manage_csv_to_node_id_map.py")
        self.asset_db_path = os.path.join(
            current_dir, "assets", "csv_id_to_node_id_map", "csv_id_to_node_id_map.db"
        )
        self.dump_db_path = os.path.join(
            tempfile.gettempdir(), "csv_id_to_node_id_map_dump.db"
        )
        shutil.copyfile(self.asset_db_path, self.dump_db_path)

    def test_dump_csv(self):
        self.output_csv_path = os.path.join(
            tempfile.gettempdir(), "testing_csv_id_to_node_id_map_dump.csv"
        )
        self.cmd = [
            self.script_path,
            "--db_path",
            self.dump_db_path,
            "--csv_path",
            self.output_csv_path,
        ]
        script_output = subprocess.check_output(self.cmd).decode().strip()
        self.assertRegex(
            script_output, f"Dumped 60 rows into CSV file {self.output_csv_path}", ""
        )

    def tearDown(self):
        if os.path.exists(self.output_csv_path):
            os.remove(self.output_csv_path)

        if os.path.exists(self.dump_db_path):
            os.remove(self.dump_db_path)


if __name__ == "__main__":
    unittest.main()
