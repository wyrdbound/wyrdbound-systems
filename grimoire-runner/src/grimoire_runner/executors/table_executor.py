"""Table rolling step executor."""

import logging
from typing import TYPE_CHECKING, Any

from ..integrations.dice_integration import DiceIntegration
from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System

logger = logging.getLogger(__name__)


class TableExecutor(BaseStepExecutor):
    """Executor for table rolling steps."""

    def __init__(self):
        self.dice_integration = DiceIntegration()

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a table rolling step."""
        from ..models.flow import StepResult

        if not step.tables:
            return StepResult(
                step_id=step.id,
                success=False,
                error="Table roll step requires 'tables' parameter",
            )

        try:
            all_results = []

            if step.parallel:
                # Execute all table rolls in parallel (conceptually)
                for table_roll in step.tables:
                    result = self._execute_table_roll(table_roll, context, system)
                    all_results.append(result)
            else:
                # Execute table rolls sequentially
                for table_roll in step.tables:
                    result = self._execute_table_roll(table_roll, context, system)
                    all_results.append(result)

            logger.info(f"Table rolling completed: {len(all_results)} rolls")

            return StepResult(
                step_id=step.id,
                success=True,
                data={"table_results": all_results, "parallel": step.parallel},
                prompt=step.prompt,
            )

        except Exception as e:
            logger.error(f"Error executing table roll step {step.id}: {e}")
            return StepResult(
                step_id=step.id, success=False, error=f"Table roll failed: {e}"
            )

    def _execute_table_roll(
        self, table_roll, context: "ExecutionContext", system: "System"
    ):
        """Execute a single table roll."""
        table_name = table_roll.table
        count = table_roll.count

        # Get the table definition
        table = system.get_table(table_name)
        if not table:
            raise ValueError(f"Table '{table_name}' not found in system")

        results = []

        for _ in range(count):
            # Roll on the table
            if table.roll:
                # Use the table's dice expression
                dice_result = self.dice_integration.roll_expression(table.roll)
                roll_value = dice_result.total
            else:
                # Default to d100 if no roll specified
                dice_result = self.dice_integration.roll_expression("1d100")
                roll_value = dice_result.total

            # Get the result from the table
            table_result = table.get_entry_by_range(roll_value)
            if table_result is None:
                table_result = table.get_entry(roll_value)

            if table_result is None:
                # Fallback to random entry
                table_result = table.get_random_entry()

            result_data = {
                "table": table_name,
                "roll": roll_value,
                "result": table_result,
                "dice_expression": table.roll or "1d100",
            }

            results.append(result_data)

            # Execute table actions with result context
            if table_roll.actions:
                self._execute_table_actions(
                    table_roll.actions, context, system, table_result, results
                )

        # If only one result, return it directly, otherwise return list
        if count == 1:
            return results[0]
        else:
            return {"table": table_name, "results": results, "count": count}

    def _execute_table_actions(
        self,
        actions: list[Any],
        context: "ExecutionContext",
        system: "System",
        result: Any,
        all_results: list[Any],
    ) -> None:
        """Execute actions after a table roll."""
        # Add result to template context temporarily
        original_result = context.get_variable("result")
        original_results = context.get_variable("results")

        context.set_variable("result", result)
        context.set_variable("results", all_results)

        try:
            for action in actions:
                self._execute_table_action(action, context, system, result)
        finally:
            # Restore original values
            if original_result is not None:
                context.set_variable("result", original_result)
            if original_results is not None:
                context.set_variable("results", original_results)

    def _execute_table_action(
        self, action, context: "ExecutionContext", system: "System", result: Any
    ) -> None:
        """Execute a single table action."""
        action_type = list(action.keys())[0]
        action_data = action[action_type]

        if action_type == "set_value":
            path = action_data["path"]
            value = action_data["value"]

            # Resolve templates
            resolved_value = context.resolve_template(str(value))

            # Set the value
            if path.startswith("outputs."):
                context.set_output(path[8:], resolved_value)
            elif path.startswith("variables."):
                context.set_variable(path[10:], resolved_value)
            else:
                context.set_output(path, resolved_value)

        elif action_type == "flow_call":
            # Handle sub-flow calls
            flow_id = action_data["flow"]
            inputs = action_data.get("inputs", {})
            logger.info(f"Flow call requested: {flow_id} (inputs: {inputs})")
            
            # Check if the flow exists in the system
            flow_obj = system.get_flow(flow_id)
            if not flow_obj:
                # Get available flows for better error message
                available_flows = list(system.flows.keys()) if hasattr(system, 'flows') else []
                flow_list = ", ".join(sorted(available_flows)) if available_flows else "none"
                raise ValueError(f"Flow '{flow_id}' not found in system. Available flows: {flow_list}")
            
            # TODO: Actually execute the flow call when flow execution is implemented
            logger.warning(f"Flow calling not yet implemented for flow '{flow_id}'")

        # TODO: Add other action types as needed

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the step."""
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
        return step_type == "table_roll"

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate table roll step configuration."""
        errors = []

        if not step.tables:
            errors.append("Table roll step must have 'tables' parameter")

        for table_roll in step.tables:
            if not hasattr(table_roll, "table") or not table_roll.table:
                errors.append("Each table roll must specify a 'table'")

        return errors
