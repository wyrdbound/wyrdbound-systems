"""Simple test to check pytest discovery."""

def test_simple():
    """Simple test that should always pass."""
    assert True

def test_choice_executor_exists():
    """Test that we can import the choice executor."""
    from grimoire_runner.executors.choice_executor import ChoiceExecutor
    executor = ChoiceExecutor()
    assert executor is not None
