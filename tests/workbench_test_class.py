import os
from abc import abstractmethod, ABC

import pytest
from ruamel.yaml import YAML
import tempfile


def get_workbench_path(starting_path: str):
    """Get the path to the workbench executable.
    Parameters
    ----------
    starting_path : str
        The path to the directory where the test is being run.
    Returns
    -------
    str
        The absolute path to the workbench executable.
    Raises
    ------
    FileNotFoundError:
        If the workbench executable is not found in the expected location.
    """
    parent_dir = os.path.dirname(starting_path)
    if not os.path.exists(os.path.join(parent_dir, "workbench")):
        raise FileNotFoundError(
            "Workbench executable not found in the expected location. "
        )
    return os.path.abspath(os.path.join(parent_dir, "workbench"))


class TestUser(ABC):
    """Class representing a test user for workbench tests."""

    @abstractmethod
    def alter_configuration(self, config: dict) -> dict:
        """Alter the configuration to use test user credentials.
        Parameters
        ----------
        config : dict
            The configuration dictionary to be altered.
        Returns
        -------
        dict
            The altered configuration dictionary with test user credentials.
        """


class AdminUser(TestUser):
    """Class representing an admin user for workbench tests."""

    def __str__(self):
        return "AdminUser"

    def alter_configuration(self, config: dict) -> dict:
        config["username"] = "admin"
        config["password"] = "admin"
        return config


class NormalUser(TestUser):
    """Class representing a test user for workbench tests."""

    def __str__(self):
        return "NormalUser"

    def alter_configuration(self, config: dict) -> dict:
        config["username"] = "test-user"
        config["password"] = "testPassword"
        config["use_workbench_permissions"] = True
        return config


class WorkbenchTest(ABC):
    """Base class for workbench tests."""

    pytestmark = pytest.mark.parametrize(
        "workbench_user", [(NormalUser()), (AdminUser())]
    )

    # Class variable to hold the path to the workbench executable
    workbench_path = None

    # Class variable to hold the current directory of the test file
    current_dir = None

    # Class variable to hold the temporary directory path
    temp_dir = None

    # Class variable to hold the configuration for the test
    configuration = {}

    # Class variable to hold the path to the configuration file for cleanup
    config_file_path = None

    @classmethod
    def write_config_and_get_path(cls, config: dict) -> str:
        """Write the configuration to a temporary file and return the path.
        Parameters
        ----------
        config : dict
            The configuration dictionary to be written to a file.
        Returns
        -------
        str
            The path to the configuration file.
        """
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, dir=cls.temp_dir, suffix=".yml"
        ) as config_file:
            YAML().dump(config, config_file)
        return os.path.join(cls.temp_dir, config_file.name)

    @classmethod
    def setup_class(cls):
        cls.current_dir = os.path.dirname(os.path.abspath(__file__))
        cls.workbench_path = get_workbench_path(cls.current_dir)
        cls.temp_dir = tempfile.gettempdir()
