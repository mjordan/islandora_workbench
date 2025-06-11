"""unittest tests for the CSV ID to node ID map. Do not require a live Drupal."""

import os
import sys
import tempfile
import shutil
import subprocess
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils


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


class TestSelectQueriesWithHostFilters(unittest.TestCase):

    def setUp(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.asset_db_path = os.path.join(
            current_dir,
            "assets",
            "csv_id_to_node_id_map",
            "csv_id_to_node_id_map_host_query_tests.db",
        )

    def test_empty_host_filter(self):
        config = {
            "csv_id_to_node_id_map_allowed_hosts": [],
        }
        csv_id_to_node_id_map_allowed_hosts_sql = (
            workbench_utils.get_csv_id_to_node_id_map_allowed_hosts_sql(config)
        )
        query = (
            "select * from csv_id_to_node_id_map where "
            + csv_id_to_node_id_map_allowed_hosts_sql
            + " config_file = ?"
        )
        result = workbench_utils.sqlite_manager(
            config,
            operation="select",
            query=query,
            values=("/home/util/islandora_workbench/theses_to_summit.yml",),
            db_file_path=self.asset_db_path,
        )
        self.assertEqual(len(result), 49)

    def test_default_host(self):
        config = {
            "csv_id_to_node_id_map_allowed_hosts": ["", "https://foo.info"],
        }
        csv_id_to_node_id_map_allowed_hosts_sql = (
            workbench_utils.get_csv_id_to_node_id_map_allowed_hosts_sql(config)
        )
        query = (
            "select * from csv_id_to_node_id_map where "
            + csv_id_to_node_id_map_allowed_hosts_sql
            + "node_id > ?"
        )

        result = workbench_utils.sqlite_manager(
            config,
            operation="select",
            query=query,
            values=(0,),
            db_file_path=self.asset_db_path,
        )
        self.assertEqual(len(result), 49)

    def test_single_host(self):
        config = {
            "csv_id_to_node_id_map_allowed_hosts": ["https://foo.info"],
        }
        csv_id_to_node_id_map_allowed_hosts_sql = (
            workbench_utils.get_csv_id_to_node_id_map_allowed_hosts_sql(config)
        )
        query = (
            "select * from csv_id_to_node_id_map where "
            + csv_id_to_node_id_map_allowed_hosts_sql
            + "node_id > ?"
        )

        result = workbench_utils.sqlite_manager(
            config,
            operation="select",
            query=query,
            values=(0,),
            db_file_path=self.asset_db_path,
        )
        self.assertEqual(len(result), 2)

    def test_multiple_hosts(self):
        config = {
            "csv_id_to_node_id_map_allowed_hosts": [
                "https://foo.info",
                "https://secondary.info",
            ],
        }
        csv_id_to_node_id_map_allowed_hosts_sql = (
            workbench_utils.get_csv_id_to_node_id_map_allowed_hosts_sql(config)
        )
        query = (
            "select * from csv_id_to_node_id_map where "
            + csv_id_to_node_id_map_allowed_hosts_sql
            + "node_id > ?"
        )

        result = workbench_utils.sqlite_manager(
            config,
            operation="select",
            query=query,
            values=(0,),
            db_file_path=self.asset_db_path,
        )
        self.assertEqual(len(result), 13)


if __name__ == "__main__":
    unittest.main()
