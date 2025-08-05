"""
Summary test runner for key UI functionality.
"""

import os
from pathlib import Path

import pytest


@pytest.mark.no_cover
def test_summary():
    """Run a curated set of UI tests to validate core functionality."""

    # Get the directory of this test file to construct proper paths
    test_dir = Path(__file__).parent

    # Define the tests we want to run for our summary (using absolute paths)
    test_files = [
        f"{test_dir}/test_basic_modal.py::TestBasicModal::test_basic_modal",
        f"{test_dir}/test_basic_modal.py::TestBasicModal::test_basic_modal_cancel",
    ]

    # Change to the grimoire-runner directory for the test execution
    original_cwd = os.getcwd()
    grimoire_runner_dir = test_dir.parent
    os.chdir(grimoire_runner_dir)

    try:
        # Run the tests with plugin disabled and warning filters
        exit_code = pytest.main(
            [
                "-v",
                "-p",
                # "no:textual-snapshot",
                "--disable-warnings",  # Suppress warnings to avoid deprecation warnings affecting exit code
                "--no-cov",  # Disable coverage for the nested pytest run
            ]
            + test_files
        )

        # Should return 0 for success
        assert exit_code == 0, f"Some summary tests failed with exit code {exit_code}"
    finally:
        # Always restore the original working directory
        os.chdir(original_cwd)


if __name__ == "__main__":
    test_summary()
