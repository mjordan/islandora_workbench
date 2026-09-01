import json
import os

import argparse
from datetime import timedelta
from tempfile import NamedTemporaryFile
from unittest import mock

import pytest
import requests
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workbench_utils
from WorkbenchConfig import WorkbenchConfig


def mocked_module_version_requests(*args, **kwargs):
    # To handle both requests.get(url) and requests.sessions.Session.get(self, url)
    if "url" in kwargs:
        url = kwargs["url"]
    elif args:
        url = args[-1]
    else:
        url = None

    class MockResponse:
        def __init__(self, json_data, status_code, json_decode_error=False):
            self.json_data = json_data
            self.text = str(json_data) if json_data is not None else ""
            self.status_code = status_code
            self.elapsed = timedelta(seconds=0.1)
            self.json_decode_error = json_decode_error

        def json(self):
            if self.json_decode_error:
                raise requests.JSONDecodeError("Expecting value", self.text, 0)
            return self.json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(f"Received status code {self.status_code}")

    if url == "https://old.example.com/islandora_workbench_integration/version":
        return MockResponse({"integration_module_version": "1.0"}, 200)
    elif url == "https://new.example.com/islandora_workbench_integration/version":
        return MockResponse({"integration_module_version": "1.2.1"}, 200)
    elif url == "https://bad.example.com/islandora_workbench_integration/version":
        return MockResponse("some non json data", 200)
    elif url == "https://bad2.example.com/islandora_workbench_integration/version":
        return MockResponse("[[[bad json", 200, True)
    else:
        return MockResponse(None, 404)


@mock.patch(
    "requests.sessions.Session.request", side_effect=mocked_module_version_requests
)
def test_check_workbench_integration_version_bad_response(mock_get):
    """Tests that check_workbench_integration_version exits with expected message if the integration module's version endpoint doesn't return valid JSON."""
    temp_config = {
        "task": "create",
        "username": "test_user",
        "password": "test_password",
        "host": "https://bad.example.com",
        "use_workbench_permissions": True,
    }

    with NamedTemporaryFile(
        mode="w", suffix=".yml", prefix="islandora_workbench_test_config_", delete=False
    ) as temp_config_file:
        json.dump(temp_config, temp_config_file)
        config_file_path = temp_config_file.name
    args = argparse.Namespace(
        config=config_file_path,
        check=False,
        get_csv_template=False,
    )
    config_object = WorkbenchConfig(args)
    config = config_object.get_config()
    expected_message = "Unexpected error when trying to get Islandora Workbench Integration module version. Response text was: some non json data"
    with pytest.raises(ValueError, match=expected_message):
        assert workbench_utils.check_integration_module_version(config, False)
    if os.path.exists(config_file_path):
        os.remove(config_file_path)


@mock.patch(
    "requests.sessions.Session.request", side_effect=mocked_module_version_requests
)
def test_check_workbench_integration_version_bad_response_2(mock_get):
    """Tests that check_workbench_integration_version exits with expected message if the integration module's version endpoint doesn't return valid JSON."""
    temp_config = {
        "task": "create",
        "username": "test_user",
        "password": "test_password",
        "host": "https://bad2.example.com",
        "use_workbench_permissions": True,
    }

    with NamedTemporaryFile(
        mode="w", suffix=".yml", prefix="islandora_workbench_test_config_", delete=False
    ) as temp_config_file:
        json.dump(temp_config, temp_config_file)
        config_file_path = temp_config_file.name
    args = argparse.Namespace(
        config=config_file_path,
        check=False,
        get_csv_template=False,
    )
    config_object = WorkbenchConfig(args)
    config = config_object.get_config()
    expected_message = r"Unable to parse Islandora Workbench Integration module version response as JSON. Response text was: \[\[\[bad json"
    with pytest.raises(ValueError, match=expected_message):
        assert workbench_utils.check_integration_module_version(config, False)
    if os.path.exists(config_file_path):
        os.remove(config_file_path)


@mock.patch(
    "requests.sessions.Session.request", side_effect=mocked_module_version_requests
)
def test_check_workbench_integration_version_missing(mock_get):
    """Tests that check_workbench_integration_version exits with expected message if the integration module is not installed (not using workbench permissions)."""
    config_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "assets",
        "config_test",
        "test_minimal_config.yml",
    )
    args = argparse.Namespace(
        config=config_file_path,
        check=False,
        get_csv_template=False,
    )
    config_object = WorkbenchConfig(args)
    config = config_object.get_config()
    expected_message = f"Error: Workbench cannot determine the Islandora Workbench Integration module's version number. It must be version 1.0 or higher."
    with pytest.raises(SystemExit, match=expected_message):
        assert workbench_utils.check_integration_module_version(config, False)


@mock.patch(
    "requests.sessions.Session.request", side_effect=mocked_module_version_requests
)
def test_check_workbench_integration_version_missing_permissions(mock_get):
    """Tests that check_workbench_integration_version exits with expected message if the integration module is not installed (using workbench permissions)."""
    temp_config = {
        "task": "create",
        "username": "test_user",
        "password": "test_password",
        "host": "https://example.com",
        "use_workbench_permissions": True,
    }

    with NamedTemporaryFile(
        mode="w", suffix=".yml", prefix="islandora_workbench_test_config_", delete=False
    ) as temp_config_file:
        json.dump(temp_config, temp_config_file)
        config_file_path = temp_config_file.name
    args = argparse.Namespace(
        config=config_file_path,
        check=False,
        get_csv_template=False,
    )
    config_object = WorkbenchConfig(args)
    config = config_object.get_config()
    expected_message = f"Error: Workbench cannot determine the Islandora Workbench Integration module's version number. It must be version 1.2 or higher."
    with pytest.raises(SystemExit, match=expected_message):
        assert workbench_utils.check_integration_module_version(config, False)
    if os.path.exists(config_file_path):
        os.remove(config_file_path)


@mock.patch(
    "requests.sessions.Session.request", side_effect=mocked_module_version_requests
)
def test_check_workbench_integration_version_to_old(mock_get):
    """Tests that check_workbench_integration_version exits specifying that the module must be upgraded because the version is too old."""
    temp_config = {
        "task": "create",
        "username": "test_user",
        "password": "test_password",
        "host": "https://old.example.com",
        "use_workbench_permissions": True,
    }

    with NamedTemporaryFile(
        mode="w", suffix=".yml", prefix="islandora_workbench_test_config_", delete=False
    ) as temp_config_file:
        json.dump(temp_config, temp_config_file)
        config_file_path = temp_config_file.name
    args = argparse.Namespace(
        config=config_file_path,
        check=False,
        get_csv_template=False,
    )
    config_object = WorkbenchConfig(args)
    config = config_object.get_config()
    expected_message = "The Islandora Workbench Integration module installed on https://old.example.com must be upgraded to version 1.2. See your Workbench log for more information."
    with pytest.raises(SystemExit, match=expected_message):
        assert workbench_utils.check_integration_module_version(config, False)
    if os.path.exists(config_file_path):
        os.remove(config_file_path)


@mock.patch(
    "requests.sessions.Session.request", side_effect=mocked_module_version_requests
)
def test_check_workbench_integration_version_ok(mock_get):
    """Tests that check_workbench_integration_version doesn't exit because the version is sufficient for needed functionality."""
    temp_config = {
        "task": "create",
        "username": "test_user",
        "password": "test_password",
        "host": "https://new.example.com",
        "use_workbench_permissions": True,
    }

    with NamedTemporaryFile(
        mode="w", suffix=".yml", prefix="islandora_workbench_test_config_", delete=False
    ) as temp_config_file:
        json.dump(temp_config, temp_config_file)
        config_file_path = temp_config_file.name
    args = argparse.Namespace(
        config=config_file_path,
        check=False,
        get_csv_template=False,
    )
    config_object = WorkbenchConfig(args)
    config = config_object.get_config()
    assert workbench_utils.check_integration_module_version(config, False) is None
    if os.path.exists(config_file_path):
        os.remove(config_file_path)
