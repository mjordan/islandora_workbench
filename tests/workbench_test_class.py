import unittest
import os
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


class WorkbenchTest(unittest.TestCase):
    """Base class for workbench tests."""

    # Class variable to hold the path to the workbench executable
    workbench_path = None

    # Class variable to hold the current directory of the test file
    current_dir = None

    # Class variable to hold the temporary directory path
    temp_dir = None

    @classmethod
    def setUpClass(cls):
        """Set up the test class by getting the workbench path."""
        cls.current_dir = os.path.dirname(os.path.abspath(__file__))
        cls.workbench_path = get_workbench_path(cls.current_dir)
        cls.temp_dir = tempfile.gettempdir()


if __name__ == "__main__":
    unittest.main()
