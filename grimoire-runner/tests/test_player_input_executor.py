"""Tests for the PlayerInputExecutor."""

from unittest.mock import patch

import pytest

from grimoire_runner.executors.player_input_executor import PlayerInputExecutor
from grimoire_runner.models.context_data import ExecutionContext
from grimoire_runner.models.flow import StepDefinition, StepType
from grimoire_runner.models.system import System


@pytest.fixture
def player_input_executor():
    """Create a PlayerInputExecutor instance."""
    return PlayerInputExecutor()


@pytest.fixture
def context():
    """Create an ExecutionContext instance."""
    return ExecutionContext()


@pytest.fixture
def mock_system():
    """Create a mock System instance."""
    return System(
        id="test_system",
        name="Test System",
        version="1.0",
        models={},
        compendiums={},
        tables={},
        flows={},
    )


class TestPlayerInputExecutor:
    """Test PlayerInputExecutor functionality."""

    def test_can_execute_player_input(self, player_input_executor):
        """Test that the executor can handle player_input steps."""
        step = StepDefinition(
            id="test_step", type=StepType.PLAYER_INPUT, prompt="Enter text"
        )
        assert player_input_executor.can_execute(step)

    def test_cannot_execute_other_types(self, player_input_executor):
        """Test that the executor cannot handle other step types."""
        step = StepDefinition(id="test_step", type=StepType.DICE_ROLL, roll="1d6")
        assert not player_input_executor.can_execute(step)

    def test_execute_returns_requires_input(
        self, player_input_executor, context, mock_system
    ):
        """Test that execute returns a result requiring user input."""
        step = StepDefinition(
            id="test_step", type=StepType.PLAYER_INPUT, prompt="Enter your name"
        )
        result = player_input_executor.execute(step, context, mock_system)

        assert result.success
        assert result.requires_input
        assert result.prompt == "Enter your name"
        assert result.data["input_type"] == "text"

    def test_execute_without_prompt(self, player_input_executor, context, mock_system):
        """Test execution without a prompt."""
        step = StepDefinition(id="test_step", type=StepType.PLAYER_INPUT, prompt=None)
        result = player_input_executor.execute(step, context, mock_system)

        assert result.success
        assert result.requires_input

    def test_process_input_basic(self, player_input_executor, context, mock_system):
        """Test basic input processing."""
        step = StepDefinition(
            id="test_step",
            type=StepType.PLAYER_INPUT,
            prompt="Enter your name",
            actions=[
                {
                    "set_value": {
                        "path": "outputs.character.name",
                        "value": "{{ result }}",
                    }
                }
            ],
        )

        result = player_input_executor.process_input(
            "Alice", step, context, mock_system
        )

        assert result.success
        assert result.data["result"] == "Alice"
        assert result.data["user_input"] == "Alice"

        # Check that the action was executed
        assert context.get_output("character.name") == "Alice"

    def test_process_input_with_template_resolution(
        self, player_input_executor, context, mock_system
    ):
        """Test input processing with template resolution."""
        context.set_variable("prefix", "Mr.")

        step = StepDefinition(
            id="test_step",
            type=StepType.PLAYER_INPUT,
            prompt="Enter your name",
            actions=[
                {
                    "set_value": {
                        "path": "outputs.character.full_name",
                        "value": "{{ variables.prefix }} {{ result }}",
                    }
                }
            ],
        )

        result = player_input_executor.process_input(
            "Smith", step, context, mock_system
        )

        assert result.success
        assert context.get_output("character.full_name") == "Mr. Smith"

    def test_process_input_empty_string(
        self, player_input_executor, context, mock_system
    ):
        """Test processing empty string input."""
        step = StepDefinition(
            id="test_step",
            type=StepType.PLAYER_INPUT,
            prompt="Enter something",
            actions=[
                {"set_value": {"path": "outputs.result", "value": "{{ result }}"}}
            ],
        )

        result = player_input_executor.process_input("", step, context, mock_system)

        assert result.success
        assert result.data["result"] == ""

    def test_validate_step_no_prompt(self, player_input_executor):
        """Test step validation when prompt is missing."""
        step = StepDefinition(id="test_step", type=StepType.PLAYER_INPUT, prompt=None)
        errors = player_input_executor.validate_step(step)

        assert len(errors) == 1
        assert "prompt" in errors[0]

    def test_validate_step_with_prompt(self, player_input_executor):
        """Test step validation when prompt is present."""
        step = StepDefinition(
            id="test_step", type=StepType.PLAYER_INPUT, prompt="Enter text"
        )
        errors = player_input_executor.validate_step(step)

        assert len(errors) == 0

    def test_process_input_with_namespaced_context(
        self, player_input_executor, context, mock_system
    ):
        """Test input processing with a namespaced context."""
        # Create a flow namespace
        context.create_flow_namespace("test_flow", "test_flow_id", "test_exec_id")
        context.set_current_flow_namespace("test_flow")

        step = StepDefinition(
            id="test_step",
            type=StepType.PLAYER_INPUT,
            prompt="Enter your name",
            actions=[
                {
                    "set_value": {
                        "path": "outputs.character.name",
                        "value": "{{ result }}",
                    }
                }
            ],
        )

        result = player_input_executor.process_input("Bob", step, context, mock_system)

        assert result.success
        assert result.data["result"] == "Bob"

        # Check that the value was set in the namespaced context
        namespace_data = context.get_flow_namespace_data("test_flow")
        assert namespace_data["outputs"]["character"]["name"] == "Bob"

    def test_execute_handles_exception(
        self, player_input_executor, context, mock_system
    ):
        """Test that execute handles exceptions gracefully."""
        # Mock logger to raise an exception to simulate an error
        with patch(
            "grimoire_runner.executors.player_input_executor.logger"
        ) as mock_logger:
            mock_logger.debug.side_effect = RuntimeError("Simulated error")

            step = StepDefinition(id="test_step", type=StepType.PLAYER_INPUT)
            result = player_input_executor.execute(step, context, mock_system)

            assert not result.success
            assert "Player input step failed" in result.error

    def test_process_input_handles_action_exception(
        self, player_input_executor, context, mock_system
    ):
        """Test that process_input handles action execution exceptions gracefully."""
        step = StepDefinition(
            id="test_step",
            type=StepType.PLAYER_INPUT,
            prompt="Enter your name",
            actions=[
                {
                    "invalid_action": {
                        "path": "outputs.character.name",
                        "value": "{{ result }}",
                    }
                }
            ],
        )

        result = player_input_executor.process_input(
            "Alice", step, context, mock_system
        )

        # The executor should handle unknown action types gracefully
        # It logs a warning but continues processing
        assert result.success
        assert result.data["result"] == "Alice"


class TestPlayerInputExecutorIntegration:
    """Integration tests for PlayerInputExecutor with the engine."""

    def test_engine_integration(self):
        """Test that the engine properly integrates the PlayerInputExecutor."""
        from grimoire_runner.core.engine import GrimoireEngine

        engine = GrimoireEngine()

        # Check that the executor is registered
        assert "player_input" in engine.executors
        assert isinstance(engine.executors["player_input"], PlayerInputExecutor)

    def test_step_type_enum_includes_player_input(self):
        """Test that the StepType enum includes PLAYER_INPUT."""
        from grimoire_runner.models.flow import StepType

        assert hasattr(StepType, "PLAYER_INPUT")
        assert StepType.PLAYER_INPUT.value == "player_input"
