import os
from abc import abstractmethod, ABC

import pytest
from ruamel.yaml import YAML
import tempfile


def get_workbench_dir(starting_path: str):
    """Get the path to the directory containing the workbench executable.
    Parameters
    ----------
    starting_path : str
        The path to the directory where the test is being run.
    Returns
    -------
    str
        The absolute path to the workbench directory.
    Raises
    ------
    FileNotFoundError:
        If the workbench executable is not found in the expected location.
    """
    parent_dir = os.path.dirname(starting_path)
    if (
        not os.path.exists(os.path.join(parent_dir, "workbench"))
        or not os.path.isfile(os.path.join(parent_dir, "workbench"))
        or not os.access(os.path.join(parent_dir, "workbench"), os.X_OK)
    ):
        raise FileNotFoundError(
            "Workbench executable not found in the expected location. "
        )
    return os.path.abspath(parent_dir)


def collect_nids_from_create_output(output: str) -> list:
    """Get the node IDs of the nodes created during this test so they can be deleted later.
    Parameters
    ----------
    output : str
        The output string from the workbench create command.
    Returns
    -------
    list
        A list of node IDs extracted from the output.
    """
    create_lines = output.splitlines()

    # for line in create_lines:
    #    if "created at" in line:
    #        nid = line.rsplit("/", 1)[-1]
    #        nid = nid.strip(".")
    #        nids.append(nid)
    return [l.rsplit("/", 1)[-1].strip(".") for l in create_lines if "created at" in l]


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

    # Class variable to hold the directory of the workbench executable
    workbench_dir = None

    # Class variable to hold the current directory of the test file
    current_dir = None

    # Class variable to hold the temporary directory path
    temp_dir = None

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
        cls.workbench_dir = get_workbench_dir(cls.current_dir)
        cls.temp_dir = tempfile.gettempdir()
