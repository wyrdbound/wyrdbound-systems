"""Test log_event template resolution."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import logging

# Add src to path for imports
sys.path.append("src")

from grimoire_runner.executors.action_strategies import LogEventActionStrategy
from grimoire_runner.models.context_data import ExecutionContext


def test_log_event_template_resolution():
    """Test that log_event action resolves templates correctly."""
    
    # Create a mock execution context
    context = MagicMock()
    context.resolve_template.return_value = "Input: Hello World, Variable: test_value, Result: success"
    
    # Create the action strategy
    strategy = LogEventActionStrategy()
    
    # Mock the logger to capture the output
    with patch.object(logging.getLogger('grimoire_runner.executors.action_strategies'), 'debug') as mock_logger:
        # Execute the action with template strings
        action_data = {
            "type": "test_event",
            "data": "Input: {{ inputs.test_input }}, Variable: {{ variables.test_var }}, Result: {{ result }}"
        }
        
        strategy.execute(action_data, context)
        
        # Verify template resolution was called
        context.resolve_template.assert_called_once_with("Input: {{ inputs.test_input }}, Variable: {{ variables.test_var }}, Result: {{ result }}")
        
        # Verify the logger was called with the resolved template
        mock_logger.assert_called_once_with("Event: test_event - Input: Hello World, Variable: test_value, Result: success")


def test_log_event_non_string_data():
    """Test that log_event action handles non-string data without template resolution."""
    
    # Create a mock execution context
    context = MagicMock()
    
    # Create the action strategy
    strategy = LogEventActionStrategy()
    
    # Mock the logger to capture the output
    with patch.object(logging.getLogger('grimoire_runner.executors.action_strategies'), 'debug') as mock_logger:
        # Execute the action with dict data (should not be template resolved)
        action_data = {
            "type": "test_event",
            "data": {"key": "value", "number": 42}
        }
        
        strategy.execute(action_data, context)
        
        # Verify template resolution was NOT called for dict data
        context.resolve_template.assert_not_called()
        
        # Verify the logger was called with the original dict
        mock_logger.assert_called_once_with("Event: test_event - {'key': 'value', 'number': 42}")


if __name__ == "__main__":
    test_log_event_template_resolution()
    test_log_event_non_string_data()
    print("All log_event template resolution tests passed!")
