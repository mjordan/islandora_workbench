"""unittest tests for the recursive include_members feature added to
export_csv and get_data_from_view (the "Round 3" simplified design):
RecursiveMembersMixin itself, and the extended CSVExporter._process_nodes()/
ViewExporter._process_view_pages(). Does not require a live Drupal; all
Drupal-facing calls are mocked.

Companion to tests/unit_tests_export_member_media.py's conventions.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, call

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_export
from workbench_export import CSVExporter, ViewExporter, RecursiveMembersMixin


def make_config(**overrides):
    config = {
        "host": "https://example.com",
        "username": "test",
        "password": "test",
        "content_type": "islandora_object",
        "enable_http_cache": False,
        "progress_bar": False,
        "export_csv_include_members": False,
        "csv_member_max_depth": None,
        "get_data_from_view_include_members": False,
        "view_member_max_depth": None,
    }
    config.update(overrides)
    return config


def make_csv_exporter(**config_overrides):
    """Build a CSVExporter WITHOUT calling its real __init__() (which
    makes live calls to get_field_definitions()/get_csv_data()). Only the
    attributes the methods under test actually read are set.
    """
    exporter = CSVExporter.__new__(CSVExporter)
    exporter.config = make_config(**config_overrides)
    exporter.args = None
    exporter.seen_nids = set()
    exporter.pbar = None
    return exporter


def make_view_exporter(**config_overrides):
    """Same idea as make_csv_exporter(), for ViewExporter -- bypasses
    __init__() (which calls initialize_view_config(), also a live call).
    """
    exporter = ViewExporter.__new__(ViewExporter)
    exporter.config = make_config(**config_overrides)
    exporter.args = None
    exporter.seen_nids = set()
    exporter.pbar = None
    return exporter


class TestGetMemberNodeIds(unittest.TestCase):
    """RecursiveMembersMixin.get_member_node_ids() -- ported logic,
    re-tested here against the mixin directly rather than
    MemberMediaExporter, since it's now shared, independent code.
    """

    @patch("workbench_export.issue_request")
    def test_single_page_returns_all_members(self, mock_issue_request):
        response = MagicMock(status_code=200)
        response.json.return_value = [
            {"nid": "1332", "field_weight_value": "1"},
            {"nid": "1333", "field_weight_value": "2"},
        ]
        mock_issue_request.return_value = response

        exporter = make_csv_exporter()
        with patch.object(
            exporter, "parse_json_response", return_value=response.json.return_value
        ):
            result = exporter.get_member_node_ids("1162")

        self.assertEqual(
            result,
            [
                {"nid": "1332", "weight": "1"},
                {"nid": "1333", "weight": "2"},
            ],
        )

    @patch("workbench_export.issue_request")
    def test_pagination_across_multiple_pages(self, mock_issue_request):
        exporter = make_csv_exporter()
        full_page = [{"nid": str(n), "field_weight_value": str(n)} for n in range(50)]
        short_page = [{"nid": "9999", "field_weight_value": "99"}]

        responses = [MagicMock(status_code=200) for _ in range(2)]
        mock_issue_request.side_effect = responses

        with patch.object(
            exporter, "parse_json_response", side_effect=[full_page, short_page]
        ):
            result = exporter.get_member_node_ids("1162")

        self.assertEqual(len(result), 51)
        self.assertEqual(mock_issue_request.call_count, 2)

    @patch("workbench_export.issue_request")
    def test_malformed_row_is_skipped_not_fatal(self, mock_issue_request):
        exporter = make_csv_exporter()
        response = MagicMock(status_code=200)
        mock_issue_request.return_value = response

        with patch.object(
            exporter,
            "parse_json_response",
            return_value=[
                {"nid": "1332", "field_weight_value": "1"},
                {"no_nid": "oops"},
            ],
        ):
            result = exporter.get_member_node_ids("1162")

        self.assertEqual(result, [{"nid": "1332", "weight": "1"}])

    @patch("workbench_export.issue_request")
    def test_non_200_response_returns_empty_list(self, mock_issue_request):
        exporter = make_csv_exporter()
        mock_issue_request.return_value = MagicMock(status_code=500)

        result = exporter.get_member_node_ids("1162")
        self.assertEqual(result, [])

    @patch("workbench_export.issue_request")
    def test_empty_response_returns_empty_list(self, mock_issue_request):
        exporter = make_csv_exporter()
        response = MagicMock(status_code=200)
        mock_issue_request.return_value = response

        with patch.object(exporter, "parse_json_response", return_value=[]):
            result = exporter.get_member_node_ids("1162")

        self.assertEqual(result, [])


class TestCollectNodeAndMembers(unittest.TestCase):
    """RecursiveMembersMixin.collect_node_and_members() -- recursion,
    weight propagation, cycle protection, max_depth.
    """

    def test_single_leaf_node_gets_root_weight(self):
        exporter = make_csv_exporter()
        with patch.object(exporter, "get_member_node_ids", return_value=[]):
            result = exporter.collect_node_and_members("1332")
        self.assertEqual(result, {"1332": "root"})

    def test_one_level_of_members_gets_their_own_weight(self):
        exporter = make_csv_exporter()

        def fake_members(parent_nid):
            if parent_nid == "1162":
                return [{"nid": "1332", "weight": "1"}, {"nid": "1333", "weight": "2"}]
            return []

        with patch.object(exporter, "get_member_node_ids", side_effect=fake_members):
            result = exporter.collect_node_and_members("1162")

        self.assertEqual(result, {"1162": "root", "1332": "1", "1333": "2"})

    def test_multi_level_recursion_propagates_weight_at_each_level(self):
        exporter = make_csv_exporter()

        def fake_members(parent_nid):
            return {
                "1162": [{"nid": "1332", "weight": "1"}],
                "1332": [{"nid": "9001", "weight": "1"}],
            }.get(parent_nid, [])

        with patch.object(exporter, "get_member_node_ids", side_effect=fake_members):
            result = exporter.collect_node_and_members("1162")

        self.assertEqual(result, {"1162": "root", "1332": "1", "9001": "1"})

    def test_cycle_is_detected_and_does_not_infinite_loop(self):
        exporter = make_csv_exporter()

        def fake_members(parent_nid):
            return {
                "1162": [{"nid": "1332", "weight": "1"}],
                "1332": [{"nid": "1162", "weight": "1"}],
            }.get(parent_nid, [])

        with patch.object(exporter, "get_member_node_ids", side_effect=fake_members):
            result = exporter.collect_node_and_members("1162")

        self.assertEqual(result, {"1162": "root", "1332": "1"})

    def test_max_depth_zero_excludes_all_members(self):
        exporter = make_csv_exporter()

        def fake_members(parent_nid):
            return [{"nid": "1332", "weight": "1"}] if parent_nid == "1162" else []

        with patch.object(exporter, "get_member_node_ids", side_effect=fake_members):
            result = exporter.collect_node_and_members("1162", max_depth=0)

        self.assertEqual(result, {"1162": "root"})

    def test_max_depth_one_excludes_grandchildren_but_not_children(self):
        exporter = make_csv_exporter()

        def fake_members(parent_nid):
            return {
                "1162": [{"nid": "1332", "weight": "1"}],
                "1332": [{"nid": "9001", "weight": "1"}],
            }.get(parent_nid, [])

        with patch.object(exporter, "get_member_node_ids", side_effect=fake_members):
            result = exporter.collect_node_and_members("1162", max_depth=1)

        self.assertEqual(result, {"1162": "root", "1332": "1"})

    def test_shared_across_multiple_starting_nodes_in_one_run(self):
        # collect_node_and_members() shares self.seen_nids across calls --
        # confirms a second, independent starting node that overlaps with
        # an already-processed tree is correctly deduplicated, matching
        # what was manually confirmed with export_member_media's input_csv
        # precedence test earlier in this project.
        exporter = make_csv_exporter()

        def fake_members(parent_nid):
            return [{"nid": "1332", "weight": "1"}] if parent_nid == "1162" else []

        with patch.object(exporter, "get_member_node_ids", side_effect=fake_members):
            first = exporter.collect_node_and_members("1162")
            second = exporter.collect_node_and_members("1332")

        self.assertEqual(first, {"1162": "root", "1332": "1"})
        self.assertEqual(second, {})  # already seen; correctly empty, not re-processed


class TestCSVExporterProcessNodes(unittest.TestCase):
    """CSVExporter._process_nodes() -- confirms include_members=False
    preserves EXACT existing behavior (regression protection), and
    include_members=True correctly expands each row and reuses the
    unchanged per-node pipeline (fetch_node_json/validate_content_type/
    process_node_row/writer.writerow) for every discovered node.
    """

    def test_include_members_false_processes_only_the_starting_node(self):
        exporter = make_csv_exporter(export_csv_include_members=False)
        exporter.csv_data = [{"node_id": "1162"}]
        writer = MagicMock()

        with (
            patch.object(exporter, "validate_and_get_node_id", return_value="1162"),
            patch.object(
                exporter,
                "fetch_node_json",
                return_value={"type": [{"target_id": "islandora_object"}]},
            ) as mock_fetch,
            patch.object(exporter, "validate_content_type", return_value=True),
            patch.object(exporter, "process_node_row", return_value={"title": "Test"}),
            patch.object(exporter, "row_log_suffix", return_value=""),
            patch.object(exporter, "log_progress"),
        ):
            exporter._process_nodes(writer, ["title"])

        mock_fetch.assert_called_once_with("1162")
        writer.writerow.assert_called_once_with({"title": "Test"})

    def test_include_members_true_expands_and_processes_every_discovered_node(self):
        exporter = make_csv_exporter(
            export_csv_include_members=True, csv_member_max_depth=5
        )
        exporter.csv_data = [{"node_id": "1162"}]
        writer = MagicMock()

        with (
            patch.object(exporter, "validate_and_get_node_id", return_value="1162"),
            patch.object(
                exporter,
                "collect_node_and_members",
                return_value={"1162": "root", "1332": "1"},
            ) as mock_collect,
            patch.object(
                exporter,
                "fetch_node_json",
                return_value={"type": [{"target_id": "islandora_object"}]},
            ) as mock_fetch,
            patch.object(exporter, "validate_content_type", return_value=True),
            patch.object(exporter, "process_node_row", return_value={"title": "Test"}),
            patch.object(exporter, "row_log_suffix", return_value=""),
            patch.object(exporter, "log_progress"),
        ):
            exporter._process_nodes(writer, ["title"])

        mock_collect.assert_called_once_with("1162", max_depth=5)
        self.assertEqual(mock_fetch.call_count, 2)
        self.assertEqual(writer.writerow.call_count, 2)

    def test_member_of_non_matching_content_type_is_skipped_not_fatal(self):
        # validate_content_type() -- completely unchanged, untouched code
        # -- returning False for one discovered member must not stop
        # processing of the rest, and must not write a row for that one.
        exporter = make_csv_exporter(export_csv_include_members=True)
        exporter.csv_data = [{"node_id": "1162"}]
        writer = MagicMock()

        with (
            patch.object(exporter, "validate_and_get_node_id", return_value="1162"),
            patch.object(
                exporter,
                "collect_node_and_members",
                return_value={"1162": "root", "1332": "1"},
            ),
            patch.object(
                exporter,
                "fetch_node_json",
                return_value={"type": [{"target_id": "page"}]},
            ),
            patch.object(exporter, "validate_content_type", side_effect=[True, False]),
            patch.object(exporter, "process_node_row", return_value={"title": "Test"}),
            patch.object(exporter, "row_log_suffix", return_value=""),
            patch.object(exporter, "log_progress"),
        ):
            exporter._process_nodes(writer, ["title"])

        writer.writerow.assert_called_once()  # only the matching node was written


class TestViewExporterFetchNodeJson(unittest.TestCase):

    @patch("workbench_export.issue_request")
    def test_success_returns_parsed_json(self, mock_issue_request):
        response = MagicMock(status_code=200, text='{"nid": [{"value": "1332"}]}')
        mock_issue_request.return_value = response

        exporter = make_view_exporter()
        result = exporter.fetch_node_json("1332")
        self.assertEqual(result, {"nid": [{"value": "1332"}]})

    @patch("workbench_export.issue_request")
    def test_non_200_returns_none(self, mock_issue_request):
        mock_issue_request.return_value = MagicMock(status_code=404)

        exporter = make_view_exporter()
        result = exporter.fetch_node_json("9999")
        self.assertIsNone(result)


class TestViewExporterProcessViewPages(unittest.TestCase):
    """ViewExporter._process_view_pages() -- confirms include_members=False
    preserves exact existing behavior, and include_members=True correctly
    expands each View result using the View's own JSON for the starting
    node (no extra fetch) and fetch_node_json() for each member.
    """

    def test_include_members_false_processes_view_results_directly(self):
        exporter = make_view_exporter(get_data_from_view_include_members=False)
        exporter.view_config = {
            "base_url": "https://example.com/view",
            "parameters": "",
        }
        starting_node = {
            "nid": [{"value": "1162"}],
            "type": [{"target_id": "islandora_object"}],
        }

        responses = [
            MagicMock(status_code=200),
            MagicMock(status_code=200),
        ]

        with (
            patch("workbench_export.issue_request", side_effect=responses),
            patch.object(
                exporter, "parse_json_response", side_effect=[[starting_node], []]
            ),
            patch.object(exporter, "extract_node_id", return_value="1162"),
            patch.object(exporter, "validate_content_type", return_value=True),
            patch.object(exporter, "process_node_row", return_value={"title": "Test"}),
            patch.object(exporter, "row_log_suffix", return_value=""),
            patch.object(exporter, "execute_post_export_script"),
            patch.object(exporter, "fetch_node_json") as mock_fetch,
            patch.object(exporter, "log_progress"),
        ):
            writer = MagicMock()
            exporter._process_view_pages(writer, ["title"])

        mock_fetch.assert_not_called()  # starting node's own JSON is used directly
        writer.writerow.assert_called_once_with({"title": "Test"})

    def test_include_members_true_expands_starting_node_and_fetches_members(self):
        exporter = make_view_exporter(
            get_data_from_view_include_members=True, view_member_max_depth=5
        )
        exporter.view_config = {
            "base_url": "https://example.com/view",
            "parameters": "",
        }
        starting_node = {
            "nid": [{"value": "1162"}],
            "type": [{"target_id": "islandora_object"}],
        }
        member_node = {
            "nid": [{"value": "1332"}],
            "type": [{"target_id": "islandora_object"}],
        }

        responses = [MagicMock(status_code=200), MagicMock(status_code=200)]

        with (
            patch("workbench_export.issue_request", side_effect=responses),
            patch.object(
                exporter, "parse_json_response", side_effect=[[starting_node], []]
            ),
            patch.object(exporter, "extract_node_id", return_value="1162"),
            patch.object(
                exporter,
                "collect_node_and_members",
                return_value={"1162": "root", "1332": "1"},
            ) as mock_collect,
            patch.object(
                exporter, "fetch_node_json", return_value=member_node
            ) as mock_fetch,
            patch.object(exporter, "validate_content_type", return_value=True),
            patch.object(exporter, "process_node_row", return_value={"title": "Test"}),
            patch.object(exporter, "row_log_suffix", return_value=""),
            patch.object(exporter, "execute_post_export_script"),
            patch.object(exporter, "log_progress"),
        ):
            writer = MagicMock()
            exporter._process_view_pages(writer, ["title"])

        mock_collect.assert_called_once_with("1162", max_depth=5)
        mock_fetch.assert_called_once_with(
            "1332"
        )  # only the member, not the starting node
        self.assertEqual(writer.writerow.call_count, 2)

    def test_already_seen_starting_node_is_skipped(self):
        exporter = make_view_exporter()
        exporter.seen_nids = {"1162"}
        exporter.view_config = {
            "base_url": "https://example.com/view",
            "parameters": "",
        }
        starting_node = {"nid": [{"value": "1162"}]}

        responses = [MagicMock(status_code=200), MagicMock(status_code=200)]

        with (
            patch("workbench_export.issue_request", side_effect=responses),
            patch.object(
                exporter, "parse_json_response", side_effect=[[starting_node], []]
            ),
            patch.object(exporter, "extract_node_id", return_value="1162"),
            patch.object(exporter, "validate_content_type") as mock_validate,
            patch.object(exporter, "log_progress"),
        ):
            writer = MagicMock()
            exporter._process_view_pages(writer, ["title"])

        mock_validate.assert_not_called()
        writer.writerow.assert_not_called()


if __name__ == "__main__":
    unittest.main()
