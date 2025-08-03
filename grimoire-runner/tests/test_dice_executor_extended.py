"""
Additional tests for dice executor functionality.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.executors.dice_executor import DiceExecutor
from grimoire_runner.models.flow import StepDefinition, StepResult


class TestDiceExecutorExtended:
    """Extended tests for DiceExecutor to improve coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = DiceExecutor()
        self.context = Mock()

    def test_dice_executor_initialization(self):
        """Test dice executor initialization."""
        executor = DiceExecutor()
        assert executor.dice_integration is not None

    def test_execute_unsupported_step_type(self):
        """Test execution with unsupported step type."""
        step = Mock()
        step.id = "test_step"
        step.type = "unsupported_type"

        result = self.executor.execute(step, self.context, Mock())

        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
        assert result.success is False
        assert "cannot handle step type" in result.error

    def test_execute_dice_roll_missing_roll_param(self):
        """Test dice roll execution with missing roll parameter."""
        step = Mock()
        step.id = "test_step"
        step.type = "dice_roll"
        step.roll = None

        result = self.executor.execute(step, self.context, Mock())

        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
        assert result.success is False
        assert "Dice roll step requires 'roll' parameter" in result.error

    def test_execute_dice_roll_empty_roll_param(self):
        """Test dice roll execution with empty roll parameter."""
        step = Mock()
        step.id = "test_step"
        step.type = "dice_roll"
        step.roll = ""

        result = self.executor.execute(step, self.context, Mock())

        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
        assert result.success is False
        assert "Dice roll step requires 'roll' parameter" in result.error

    @patch('grimoire_runner.executors.dice_executor.DiceIntegration')
    def test_execute_dice_roll_success(self, mock_dice_integration_class):
        """Test successful dice roll execution."""
        # Mock the dice integration
        mock_integration = Mock()
        mock_result = Mock()
        mock_result.total = 15
        mock_result.breakdown = "3d6: [4, 5, 6] = 15"
        mock_integration.roll_expression.return_value = mock_result
        mock_dice_integration_class.return_value = mock_integration

        executor = DiceExecutor()

        step = Mock()
        step.id = "test_step"
        step.type = "dice_roll"
        step.roll = "3d6"
        step.modifiers = None
        step.prompt = None

        # Mock context to resolve template
        self.context.resolve_template.return_value = "3d6"

        result = executor.execute(step, self.context, Mock())

        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
        assert result.success is True
        assert result.data["result"] == 15
        mock_integration.roll_expression.assert_called_once_with("3d6", {})

    @patch('grimoire_runner.executors.dice_executor.DiceIntegration')
    def test_execute_dice_roll_with_output_variable(self, mock_dice_integration_class):
        """Test dice roll execution with output variable."""
        # Mock the dice integration
        mock_integration = Mock()
        mock_result = Mock()
        mock_result.total = 12
        mock_result.breakdown = "2d6: [6, 6] = 12"
        mock_integration.roll_expression.return_value = mock_result
        mock_dice_integration_class.return_value = mock_integration

        executor = DiceExecutor()

        step = Mock()
        step.id = "test_step"
        step.type = "dice_roll"
        step.roll = "2d6"
        step.modifiers = None
        step.prompt = None

        result = executor.execute(step, self.context, Mock())

        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
        assert result.success is True
        assert result.data["result"] == 12

    @patch('grimoire_runner.executors.dice_executor.DiceIntegration')
    def test_execute_dice_roll_integration_error(self, mock_dice_integration_class):
        """Test dice roll execution when integration throws error."""
        # Mock the dice integration to throw error
        mock_integration = Mock()
        mock_integration.roll_expression.side_effect = Exception("Invalid dice expression")
        mock_dice_integration_class.return_value = mock_integration

        executor = DiceExecutor()

        step = Mock()
        step.id = "test_step"
        step.type = "dice_roll"
        step.roll = "invalid"
        step.modifiers = None

        result = executor.execute(step, self.context, Mock())

        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
        assert result.success is False
        assert "Dice roll failed" in result.error

    def test_execute_dice_sequence_not_implemented(self):
        """Test dice sequence execution (not implemented)."""
        step = Mock()
        step.id = "test_step"
        step.type = "dice_sequence"

        result = self.executor.execute(step, self.context, Mock())

        # Should return error for unimplemented feature
        assert isinstance(result, StepResult)
        assert result.step_id == "test_step"
        assert result.success is False

    def test_can_execute_dice_roll(self):
        """Test that executor can handle dice_roll type."""
        step = Mock()
        step.type = "dice_roll"
        assert self.executor.can_execute(step)

    def test_can_execute_dice_sequence(self):
        """Test that executor can handle dice_sequence type."""
        step = Mock()
        step.type = "dice_sequence"
        assert self.executor.can_execute(step)

    def test_can_execute_other_types(self):
        """Test that executor cannot handle other step types."""
        step1 = Mock()
        step1.type = "player_choice"
        assert not self.executor.can_execute(step1)

        step2 = Mock()
        step2.type = "text_output"
        assert not self.executor.can_execute(step2)

        step3 = Mock()
        step3.type = "unknown_type"
        assert not self.executor.can_execute(step3)


class TestDiceExecutorIntegration:
    """Integration tests with actual step definitions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.executor = DiceExecutor()
        self.context = Mock()

    @patch('grimoire_runner.executors.dice_executor.DiceIntegration')
    def test_execute_with_step_definition(self, mock_dice_integration_class):
        """Test execution with real StepDefinition object."""
        # Mock the dice integration
        mock_integration = Mock()
        mock_result = Mock()
        mock_result.total = 8
        mock_result.breakdown = "1d8: [8] = 8"
        mock_integration.roll_expression.return_value = mock_result
        mock_dice_integration_class.return_value = mock_integration

        executor = DiceExecutor()

        # Create a real StepDefinition
        step = StepDefinition(
            id="damage_roll",
            type="dice_roll",
            name="Damage Roll",
            roll="1d8"
        )

        result = executor.execute(step, self.context, Mock())

        assert isinstance(result, StepResult)
        assert result.step_id == "damage_roll"
        assert result.success is True
        assert result.data["result"] == 8

    @patch('grimoire_runner.executors.dice_executor.DiceIntegration')
    def test_execute_with_templated_roll(self, mock_dice_integration_class):
        """Test execution with templated roll expression."""
        # Mock the dice integration
        mock_integration = Mock()
        mock_result = Mock()
        mock_result.total = 20
        mock_result.breakdown = "1d20+5: [15] + 5 = 20"
        mock_integration.roll_expression.return_value = mock_result
        mock_dice_integration_class.return_value = mock_integration

        executor = DiceExecutor()

        step = Mock()
        step.id = "attack_roll"
        step.type = "dice_roll"
        step.roll = "1d20+{{strength_bonus}}"
        step.modifiers = None
        step.prompt = None

        # Mock context to resolve template
        self.context.resolve_template.return_value = "1d20+5"

        result = executor.execute(step, self.context, Mock())

        assert isinstance(result, StepResult)
        assert result.step_id == "attack_roll"
        assert result.success is True
        assert result.data["result"] == 20
        # Should resolve template first
        self.context.resolve_template.assert_called_once_with("1d20+{{strength_bonus}}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
