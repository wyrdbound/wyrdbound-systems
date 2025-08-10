"""Test the conditional executor functionality."""

import pytest

from grimoire_runner.executors.conditional_executor import ConditionalExecutor
from grimoire_runner.models.context_data import ExecutionContext
from grimoire_runner.models.flow import StepDefinition, StepType


class TestConditionalExecutor:
    """Test the ConditionalExecutor functionality."""

    @pytest.fixture
    def conditional_executor(self):
        """Create a conditional executor instance."""
        return ConditionalExecutor()

    @pytest.fixture
    def context(self):
        """Create a test execution context."""
        context = ExecutionContext()
        context.inputs = {
            "saving_throw_type": "basic",
            "saving_throw_dc": 15,
            "saving_throw_modifier": 0,
        }
        context.variables = {"base_dice_roll": None, "roll_result": None}
        context.outputs = {}
        return context

    def test_can_execute_conditional(self, conditional_executor):
        """Test that the executor can handle conditional steps."""
        step = StepDefinition(
            id="test_conditional", type=StepType.CONDITIONAL, if_condition="true"
        )
        assert conditional_executor.can_execute(step)

    def test_cannot_execute_other_types(self, conditional_executor):
        """Test that the executor cannot handle other step types."""
        step = StepDefinition(id="test_step", type=StepType.DICE_ROLL, roll="1d6")
        assert not conditional_executor.can_execute(step)

    def test_basic_conditional_true(self, conditional_executor, context):
        """Test a basic conditional that evaluates to true."""
        step = StepDefinition(
            id="test_conditional",
            type=StepType.CONDITIONAL,
            if_condition="'{{ inputs.saving_throw_type }}' == 'basic'",
            then_actions=[
                {"set_value": {"path": "variables.base_dice_roll", "value": "1d20"}}
            ],
        )

        result = conditional_executor.execute(step, context, None)

        assert result.success
        assert result.data["condition_result"] is True
        # Check that the action was executed (variable should be set)
        assert context.variables["base_dice_roll"] == "1d20"

    def test_basic_conditional_false(self, conditional_executor, context):
        """Test a basic conditional that evaluates to false."""
        # Change input to make condition false
        context.inputs["saving_throw_type"] = "advantage"

        step = StepDefinition(
            id="test_conditional",
            type=StepType.CONDITIONAL,
            if_condition="'{{ inputs.saving_throw_type }}' == 'basic'",
            else_actions={
                "if": "'{{ inputs.saving_throw_type }}' == 'advantage'",
                "then": [
                    {
                        "set_value": {
                            "path": "variables.base_dice_roll",
                            "value": "2d20kh1",
                        }
                    }
                ],
            },
        )

        result = conditional_executor.execute(step, context, None)

        print(f"DEBUG: condition_result = {result.data['condition_result']}")
        print(f"DEBUG: context.inputs = {context.inputs}")
        print(f"DEBUG: context.variables after = {context.variables}")

        assert result.success
        assert result.data["condition_result"] is False
        # Check that the nested conditional was executed
        assert context.variables["base_dice_roll"] == "2d20kh1"

    def test_validate_step_missing_condition(self, conditional_executor):
        """Test validation of step missing condition."""
        step = StepDefinition(
            id="test_conditional",
            type=StepType.CONDITIONAL,
            then_actions=[{"set_value": {"path": "test", "value": "test"}}],
            # Missing condition but has actions
        )

        errors = conditional_executor.validate_step(step)
        assert len(errors) == 1
        assert "must have either 'if' or 'condition' field" in errors[0]

    def test_validate_step_missing_actions(self, conditional_executor):
        """Test validation of step missing actions."""
        step = StepDefinition(
            id="test_conditional",
            type=StepType.CONDITIONAL,
            if_condition="true",
            # Missing both then_actions and else_actions
        )

        errors = conditional_executor.validate_step(step)
        assert len(errors) == 1
        assert "must have at least 'then' or 'else' actions" in errors[0]

    def test_condition_evaluation_logic(self, conditional_executor):
        """Test different condition evaluation scenarios."""
        # Test boolean values
        assert conditional_executor._evaluate_condition(True) is True
        assert conditional_executor._evaluate_condition(False) is False

        # Test string values
        assert conditional_executor._evaluate_condition("true") is True
        assert conditional_executor._evaluate_condition("false") is False
        assert conditional_executor._evaluate_condition("yes") is True
        assert conditional_executor._evaluate_condition("no") is False
        assert conditional_executor._evaluate_condition("1") is True
        assert conditional_executor._evaluate_condition("0") is False
        assert conditional_executor._evaluate_condition("") is False

        # Test expressions
        assert conditional_executor._evaluate_condition("5 > 3") is True
        assert conditional_executor._evaluate_condition("'basic' == 'basic'") is True
        assert (
            conditional_executor._evaluate_condition("'basic' == 'advantage'") is False
        )
