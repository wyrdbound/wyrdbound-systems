"""
Test flow_call step functionality.

This tests the flow_call step type which allows flows to call sub-flows
and access their results through template variables.
"""

import pytest

from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.core.loader import SystemLoader
from grimoire_runner.executors.flow_executor import FlowExecutor
from grimoire_runner.models.flow import StepDefinition, StepType


@pytest.fixture
def knave_system():
    """Load the knave_1e system for testing."""
    from pathlib import Path

    loader = SystemLoader()
    system_path = Path(__file__).parent.parent.parent / "systems" / "knave_1e"
    return loader.load_system(system_path)


@pytest.fixture
def engine():
    """Create a GRIMOIRE engine for flow execution."""
    return GrimoireEngine()


@pytest.fixture
def flow_executor():
    """Create a FlowExecutor for direct testing."""
    return FlowExecutor()


class TestFlowCallBasic:
    """Test basic flow_call step functionality."""

    def test_flow_call_step_missing_flow_field(self, flow_executor, knave_system):
        """Test that flow_call step fails when 'flow' field is missing."""
        context = GrimoireEngine().create_execution_context()

        step = StepDefinition(id="test_no_flow", type=StepType.FLOW_CALL, inputs={})

        with pytest.raises(RuntimeError, match="missing required 'flow' field"):
            flow_executor.execute(step, context, knave_system)

    def test_flow_call_step_nonexistent_flow(self, flow_executor, knave_system):
        """Test that flow_call step fails when target flow doesn't exist."""
        context = GrimoireEngine().create_execution_context()

        step = StepDefinition(
            id="test_bad_flow",
            type=StepType.FLOW_CALL,
            flow="nonexistent_flow",
            inputs={},
        )

        with pytest.raises(RuntimeError, match="not found in system"):
            flow_executor.execute(step, context, knave_system)


class TestFlowCallExecution:
    """Test flow_call step execution and result handling."""

    def test_flow_call_provides_result_variable(self, engine, knave_system):
        """Test that flow_call step provides 'result' variable in actions."""
        context = engine.create_execution_context()

        # Set up inputs with correct structure
        context.set_input("actor", {"abilities": {"strength": {"bonus": 2}}})
        context.set_input("opponent", {"abilities": {"defense": {"bonus": 15}}})
        context.set_input("opposed_save_type", "basic")
        context.set_input("actor_ability", "strength")
        context.set_input("opponent_ability", "defense")

        # Execute the flow
        result = engine.execute_flow("roll_opposed_save", context, knave_system)

        # Should execute successfully
        assert result.success

        # The flow_call step should have set the saving_throw_result variable
        # from the sub-flow's outputs using the {{ result.saving_throw_result }} template
        assert "saving_throw_result" in result.variables

        # The final output should be set from the variable
        assert "opposed_save_result" in result.outputs

    def test_flow_call_executes_sub_flow(self, engine, knave_system):
        """Test that flow_call actually executes the target sub-flow."""
        context = engine.create_execution_context()

        # Set up inputs
        context.set_input("actor", {"abilities": {"strength": {"bonus": 3}}})
        context.set_input("opponent", {"abilities": {"defense": {"bonus": 12}}})
        context.set_input("opposed_save_type", "basic")
        context.set_input("actor_ability", "strength")
        context.set_input("opponent_ability", "defense")

        # Execute the flow
        result = engine.execute_flow("roll_opposed_save", context, knave_system)

        # Should execute successfully
        assert result.success

        # Should have completed both steps (roll_saving_throw and evaluate_opposed_save_result)
        assert len(result.step_results) == 2

        # Both steps should be successful
        for step_result in result.step_results:
            assert step_result.success
