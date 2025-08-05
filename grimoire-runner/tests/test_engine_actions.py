"""Additional tests for GrimoireEngine step execution and actions."""

from unittest.mock import Mock, patch

from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.executors.base import BaseStepExecutor
from grimoire_runner.models.context_data import ExecutionContext
from grimoire_runner.models.flow import FlowDefinition, StepDefinition, StepResult
from grimoire_runner.models.system import System


class TestGrimoireEngineStepExecution:
    """Tests for step execution with conditions and actions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = GrimoireEngine()

    def test_execute_step_with_condition_true(self):
        """Test step execution when condition is true."""
        # Register a mock executor
        mock_executor = Mock(spec=BaseStepExecutor)
        mock_executor.can_execute.return_value = True
        mock_executor.validate_step.return_value = []
        mock_executor.execute.return_value = StepResult(
            step_id="test_step", success=True
        )

        self.engine.register_executor("test_type", mock_executor)

        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"
        mock_step.id = "test_step"
        mock_step.condition = "{{ true }}"
        mock_step.output_variable = None
        mock_step.actions = []

        context = Mock(spec=ExecutionContext)
        context.resolve_template.return_value = True
        system = Mock(spec=System)

        result = self.engine._execute_step(mock_step, context, system)

        assert result.success
        mock_executor.execute.assert_called_once()

    def test_execute_step_with_condition_false(self):
        """Test step execution when condition is false (should skip)."""
        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"
        mock_step.id = "test_step"
        mock_step.condition = "{{ false }}"

        context = Mock(spec=ExecutionContext)
        context.resolve_template.return_value = False
        system = Mock(spec=System)

        result = self.engine._execute_step(mock_step, context, system)

        assert result.success
        assert result.data["skipped"] is True
        assert result.data["reason"] == "condition_false"

    def test_execute_step_condition_evaluation_error(self):
        """Test step execution when condition evaluation fails."""
        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"
        mock_step.id = "test_step"
        mock_step.condition = "{{ invalid_template }}"

        context = Mock(spec=ExecutionContext)
        context.resolve_template.side_effect = ValueError("Template error")
        system = Mock(spec=System)

        result = self.engine._execute_step(mock_step, context, system)

        assert not result.success
        assert "Condition evaluation failed" in result.error

    def test_execute_step_with_output_variable_result_key(self):
        """Test step execution with output variable using 'result' key."""
        # Register a mock executor
        mock_executor = Mock(spec=BaseStepExecutor)
        mock_executor.can_execute.return_value = True
        mock_executor.validate_step.return_value = []
        mock_executor.execute.return_value = StepResult(
            step_id="test_step", success=True, data={"result": "test_value"}
        )

        self.engine.register_executor("test_type", mock_executor)

        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"
        mock_step.id = "test_step"
        mock_step.condition = None
        mock_step.output = "output_var"
        mock_step.actions = []

        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)

        result = self.engine._execute_step(mock_step, context, system)

        assert result.success
        context.set_variable.assert_called_once_with("output_var", "test_value")

    def test_execute_step_with_output_variable_first_value(self):
        """Test step execution with output variable using first available value."""
        # Register a mock executor
        mock_executor = Mock(spec=BaseStepExecutor)
        mock_executor.can_execute.return_value = True
        mock_executor.validate_step.return_value = []
        mock_executor.execute.return_value = StepResult(
            step_id="test_step",
            success=True,
            data={"other_key": "other_value", "second": "second_value"},
        )

        self.engine.register_executor("test_type", mock_executor)

        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"
        mock_step.id = "test_step"
        mock_step.condition = None
        mock_step.output = "output_var"
        mock_step.actions = []

        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)

        result = self.engine._execute_step(mock_step, context, system)

        assert result.success
        # Should use the first value from the data dict
        context.set_variable.assert_called_once_with("output_var", "other_value")

    def test_execute_step_with_actions(self):
        """Test step execution with post-step actions."""
        # Register a mock executor
        mock_executor = Mock(spec=BaseStepExecutor)
        mock_executor.can_execute.return_value = True
        mock_executor.validate_step.return_value = []
        mock_executor.execute.return_value = StepResult(
            step_id="test_step", success=True, data={"result": "test_value"}
        )

        self.engine.register_executor("test_type", mock_executor)

        mock_actions = [{"set_value": {"path": "test_path", "value": "test_value"}}]

        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "test_type"
        mock_step.id = "test_step"
        mock_step.condition = None
        mock_step.output = None
        mock_step.actions = mock_actions

        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)

        with patch.object(self.engine, "_execute_actions") as mock_execute_actions:
            result = self.engine._execute_step(mock_step, context, system)

            assert result.success
            mock_execute_actions.assert_called_once_with(
                mock_actions, context, {"result": "test_value"}, system
            )

    def test_execute_step_skip_actions_for_choice_requiring_input(self):
        """Test that actions are skipped for choice steps that require input."""
        # Register a mock executor
        mock_executor = Mock(spec=BaseStepExecutor)
        mock_executor.can_execute.return_value = True
        mock_executor.validate_step.return_value = []
        mock_executor.execute.return_value = StepResult(
            step_id="test_step",
            success=True,
            requires_input=True,
            data={"result": "test_value"},
        )

        self.engine.register_executor("player_choice", mock_executor)

        mock_actions = [{"set_value": {"path": "test_path", "value": "test_value"}}]

        mock_step = Mock(spec=StepDefinition)
        mock_step.type = "player_choice"
        mock_step.id = "test_step"
        mock_step.condition = None
        mock_step.output = None
        mock_step.actions = mock_actions

        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)

        with patch.object(self.engine, "_execute_actions") as mock_execute_actions:
            result = self.engine._execute_step(mock_step, context, system)

            assert result.success
            mock_execute_actions.assert_not_called()


class TestGrimoireEngineActions:
    """Tests for action execution functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = GrimoireEngine()

    def test_execute_actions_multiple(self):
        """Test executing multiple actions."""
        actions = [
            {"set_value": {"path": "outputs.test1", "value": "value1"}},
            {"set_value": {"path": "variables.test2", "value": "value2"}},
        ]

        context = Mock(spec=ExecutionContext)
        context.resolve_template.side_effect = lambda x: x  # Return as-is
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        with patch.object(self.engine, "_execute_single_action") as mock_single:
            self.engine._execute_actions(actions, context, step_data, system)

            assert mock_single.call_count == 2

    def test_execute_actions_with_exception(self):
        """Test that action execution continues even if one action fails."""
        actions = [
            {"set_value": {"path": "outputs.test1", "value": "value1"}},
            {"set_value": {"path": "outputs.test2", "value": "value2"}},
        ]

        context = Mock(spec=ExecutionContext)
        step_data = {}
        system = Mock(spec=System)

        with patch.object(self.engine, "_execute_single_action") as mock_single:
            mock_single.side_effect = [Exception("First action failed"), None]

            # Should not raise exception
            self.engine._execute_actions(actions, context, step_data, system)

            assert mock_single.call_count == 2

    def test_execute_single_action_set_value_outputs(self):
        """Test set_value action targeting outputs."""
        action = {"set_value": {"path": "outputs.test_output", "value": "test_value"}}

        context = Mock(spec=ExecutionContext)
        context.resolve_template.return_value = "resolved_value"
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        self.engine._execute_single_action(action, context, step_data, system)

        context.set_output.assert_called_once_with("test_output", "resolved_value")

    def test_execute_single_action_set_value_variables(self):
        """Test set_value action targeting variables."""
        action = {"set_value": {"path": "variables.test_var", "value": "test_value"}}

        context = Mock(spec=ExecutionContext)
        context.resolve_template.return_value = "resolved_value"
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        self.engine._execute_single_action(action, context, step_data, system)

        context.set_variable.assert_called_once_with("test_var", "resolved_value")

    def test_execute_single_action_set_value_default_outputs(self):
        """Test set_value action with default path (outputs)."""
        action = {"set_value": {"path": "test_path", "value": "test_value"}}

        context = Mock(spec=ExecutionContext)
        context.resolve_template.return_value = "resolved_value"
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        self.engine._execute_single_action(action, context, step_data, system)

        context.set_output.assert_called_once_with("test_path", "resolved_value")

    def test_execute_single_action_display_value(self):
        """Test display_value action."""
        action = {"display_value": {"path": "outputs.test_value"}}

        context = Mock(spec=ExecutionContext)
        context.resolve_path_value.return_value = "displayed_value"
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        # Should not raise exception
        self.engine._execute_single_action(action, context, step_data, system)

        context.resolve_path_value.assert_called_once_with("outputs.test_value")

    def test_execute_single_action_display_value_string_path(self):
        """Test display_value action with string path."""
        action = {"display_value": "outputs.test_value"}

        context = Mock(spec=ExecutionContext)
        context.resolve_path_value.return_value = "displayed_value"
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        # Should not raise exception
        self.engine._execute_single_action(action, context, step_data, system)

        context.resolve_path_value.assert_called_once_with("outputs.test_value")

    def test_execute_single_action_display_value_error(self):
        """Test display_value action with path resolution error."""
        action = {"display_value": {"path": "invalid.path"}}

        context = Mock(spec=ExecutionContext)
        context.resolve_path_value.side_effect = ValueError("Invalid path")
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        # Should not raise exception, just log warning
        self.engine._execute_single_action(action, context, step_data, system)

    def test_execute_single_action_log_event(self):
        """Test log_event action."""
        action = {"log_event": {"type": "test_event", "data": {"key": "value"}}}

        context = Mock(spec=ExecutionContext)
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        # Should not raise exception
        self.engine._execute_single_action(action, context, step_data, system)

    def test_execute_single_action_swap_values(self):
        """Test swap_values action."""
        action = {"swap_values": {"path1": "outputs.var1", "path2": "outputs.var2"}}

        context = Mock(spec=ExecutionContext)
        context.resolve_template.side_effect = lambda x: x  # Return as-is
        context.resolve_path_value.side_effect = ["value1", "value2"]
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        with patch.object(self.engine, "_set_value_at_path") as mock_set:
            self.engine._execute_single_action(action, context, step_data, system)

            # Should set value2 at path1 and value1 at path2
            mock_set.assert_any_call(context, "outputs.var1", "value2")
            mock_set.assert_any_call(context, "outputs.var2", "value1")

    def test_execute_single_action_swap_values_error(self):
        """Test swap_values action with error."""
        action = {"swap_values": {"path1": "invalid.path1", "path2": "outputs.var2"}}

        context = Mock(spec=ExecutionContext)
        context.resolve_template.side_effect = lambda x: x  # Return as-is
        context.resolve_path_value.side_effect = ValueError("Invalid path")
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        # Should not raise exception, just log error
        self.engine._execute_single_action(action, context, step_data, system)

    def test_execute_single_action_flow_call(self):
        """Test flow_call action."""
        action = {
            "flow_call": {
                "flow": "sub_flow",
                "inputs": {"input1": "{{ outputs.value1 }}", "input2": "literal_value"},
            }
        }

        context = Mock(spec=ExecutionContext)
        context.resolve_template.return_value = "resolved_value"
        context.resolve_path_value.return_value = "path_value"
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        with patch(
            "grimoire_runner.executors.table_executor.TableExecutor"
        ) as MockTableExecutor:
            mock_executor = Mock()
            MockTableExecutor.return_value = mock_executor

            self.engine._execute_single_action(action, context, step_data, system)

            mock_executor._execute_sub_flow.assert_called_once()

    def test_execute_single_action_flow_call_no_system(self):
        """Test flow_call action without system."""
        action = {"flow_call": {"flow": "sub_flow", "inputs": {}}}

        context = Mock(spec=ExecutionContext)
        context.get_variable.return_value = None
        step_data = {}
        system = None  # No system

        # Should not raise exception, just log error
        self.engine._execute_single_action(action, context, step_data, system)

    def test_execute_single_action_unknown_action(self):
        """Test unknown action type."""
        action = {"unknown_action": {"data": "test"}}

        context = Mock(spec=ExecutionContext)
        context.get_variable.return_value = None
        step_data = {}
        system = Mock(spec=System)

        # Should not raise exception, just log warning
        self.engine._execute_single_action(action, context, step_data, system)

    def test_execute_single_action_with_step_data(self):
        """Test action execution with step data temporarily added to context."""
        action = {"set_value": {"path": "test_path", "value": "{{ step_var }}"}}

        context = Mock(spec=ExecutionContext)
        context.resolve_template.return_value = "resolved_from_step_data"
        context.get_variable.side_effect = [
            None,
            "step_value",
        ]  # Original value, then step value
        # Mock the variables dict for pop operation
        context.variables = {}
        step_data = {"step_var": "step_value"}
        system = Mock(spec=System)

        self.engine._execute_single_action(action, context, step_data, system)

        # Should restore original value after action
        context.set_variable.assert_any_call("step_var", "step_value")

    def test_set_value_at_path_outputs(self):
        """Test setting value at outputs path."""
        context = Mock(spec=ExecutionContext)

        self.engine._set_value_at_path(context, "outputs.test_var", "test_value")

        context.set_output.assert_called_once_with("test_var", "test_value")

    def test_set_value_at_path_variables(self):
        """Test setting value at variables path."""
        context = Mock(spec=ExecutionContext)

        self.engine._set_value_at_path(context, "variables.test_var", "test_value")

        context.set_variable.assert_called_once_with("test_var", "test_value")

    def test_set_value_at_path_default(self):
        """Test setting value at default path (outputs)."""
        context = Mock(spec=ExecutionContext)

        self.engine._set_value_at_path(context, "test_var", "test_value")

        context.set_output.assert_called_once_with("test_var", "test_value")


class TestGrimoireEngineBreakpoints:
    """Tests for breakpoint functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.engine = GrimoireEngine()

    def test_remove_breakpoint(self):
        """Test removing a specific breakpoint."""
        self.engine.set_breakpoint("test_flow", "step1")
        self.engine.set_breakpoint("test_flow", "step2")

        self.engine.remove_breakpoint("test_flow", "step1")

        assert "step1" not in self.engine.breakpoints["test_flow"]
        assert "step2" in self.engine.breakpoints["test_flow"]

    def test_remove_breakpoint_nonexistent_flow(self):
        """Test removing breakpoint from nonexistent flow."""
        # Should not raise exception
        self.engine.remove_breakpoint("nonexistent_flow", "step1")

    def test_remove_breakpoint_nonexistent_step(self):
        """Test removing nonexistent breakpoint."""
        self.engine.set_breakpoint("test_flow", "step1")

        # Should not raise exception
        self.engine.remove_breakpoint("test_flow", "nonexistent_step")

    def test_has_breakpoint_public_method(self):
        """Test public has_breakpoint method."""
        self.engine.set_breakpoint("test_flow", "step1")

        assert self.engine.has_breakpoint("test_flow", "step1")
        assert not self.engine.has_breakpoint("test_flow", "step2")

    def test_set_debug_mode(self):
        """Test set_debug_mode convenience method."""
        self.engine.set_debug_mode(True)
        assert self.engine._debug_mode

        self.engine.set_debug_mode(False)
        assert not self.engine._debug_mode

    def test_set_breakpoints_multiple(self):
        """Test setting multiple breakpoints at once."""
        step_ids = ["step1", "step2", "step3"]

        self.engine.set_breakpoints("test_flow", step_ids)

        assert self.engine.breakpoints["test_flow"] == step_ids

    def test_set_breakpoints_overwrites_existing(self):
        """Test that set_breakpoints overwrites existing breakpoints."""
        self.engine.set_breakpoint("test_flow", "old_step")

        new_steps = ["step1", "step2"]
        self.engine.set_breakpoints("test_flow", new_steps)

        assert self.engine.breakpoints["test_flow"] == new_steps
        assert "old_step" not in self.engine.breakpoints["test_flow"]

    def test_execute_flow_steps_alias(self):
        """Test that execute_flow_steps is an alias for step_through_flow."""
        context = Mock(spec=ExecutionContext)
        system = Mock(spec=System)

        with patch.object(self.engine, "step_through_flow") as mock_step_through:
            mock_step_through.return_value = iter([])

            self.engine.execute_flow_steps("test_flow", context, system)

            mock_step_through.assert_called_once_with("test_flow", context, system)

    def test_get_available_flows_with_system(self):
        """Test getting available flows with provided system."""
        mock_flow1 = Mock(spec=FlowDefinition)
        mock_flow2 = Mock(spec=FlowDefinition)

        mock_system = Mock(spec=System)
        mock_system.flows = {"flow1": mock_flow1, "flow2": mock_flow2}

        flows = self.engine.get_available_flows(mock_system)

        assert len(flows) == 2
        assert mock_flow1 in flows
        assert mock_flow2 in flows

    def test_get_available_flows_no_system_no_loaded(self):
        """Test getting available flows without system when none loaded."""
        with patch.object(self.engine.loader, "list_loaded_systems") as mock_list:
            mock_list.return_value = []

            flows = self.engine.get_available_flows()

            assert flows == []

    def test_get_available_flows_no_system_with_loaded(self):
        """Test getting available flows without system but with loaded system."""
        mock_flow = Mock(spec=FlowDefinition)
        mock_system = Mock(spec=System)
        mock_system.flows = {"flow1": mock_flow}

        with patch.object(self.engine.loader, "list_loaded_systems") as mock_list:
            with patch.object(
                self.engine.loader, "_loaded_systems", {"system1": mock_system}
            ):
                mock_list.return_value = ["system1"]

                flows = self.engine.get_available_flows()

                assert len(flows) == 1
                assert mock_flow in flows
