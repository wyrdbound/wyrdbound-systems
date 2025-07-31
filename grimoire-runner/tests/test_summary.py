"""
Summary test runner for key UI functionality.
"""

import pytest


def test_summary():
    """Run a curated set of UI tests to validate core functionality."""
    
    # Define the tests we want to run for our summary
    test_files = [
        "tests/test_basic_modal.py::TestBasicModal::test_basic_modal",
        "tests/test_basic_modal.py::TestBasicModal::test_basic_modal_cancel",
        "tests/test_textual_ui.py::TestSimpleChoiceModal::test_modal_creation",
        "tests/test_textual_ui.py::TestSimpleChoiceModal::test_modal_confirm_with_selection",
        "tests/test_textual_ui.py::TestSimpleFlowApp::test_app_creation",
        "tests/test_textual_ui.py::TestSimpleFlowApp::test_app_ui_structure",
    ]
    
    # Run the tests
    exit_code = pytest.main(["-v"] + test_files)
    
    # Should return 0 for success
    assert exit_code == 0, f"Some summary tests failed with exit code {exit_code}"


if __name__ == "__main__":
    test_summary()
