"""Shared flow execution helper for executors."""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.system import System

logger = logging.getLogger(__name__)


class FlowExecutionHelper:
    """Helper class for executing flow calls consistently across executors."""

    def __init__(self, engine=None):
        """Initialize with optional engine reference."""
        self.engine = engine

    def execute_flow_call_action(
        self,
        action: dict[str, Any],
        context: "ExecutionContext",
        system: "System",
        step_result_data: dict[str, Any] = None,
    ) -> None:
        """Execute a flow_call action with proper object handling."""
        flow_call_data = action["flow_call"]
        flow_name = flow_call_data["flow"]
        flow_inputs = flow_call_data.get("inputs", {})

        logger.debug(f"Executing flow call: {flow_name}")

        # Resolve flow inputs with special handling for object types
        resolved_inputs = {}
        for input_name, input_template in flow_inputs.items():
            resolved_value = self._resolve_flow_input(
                input_template, context, step_result_data
            )
            resolved_inputs[input_name] = resolved_value
            logger.debug(
                f"Flow input {input_name}: {type(resolved_value).__name__} = {resolved_value}"
            )

        # Execute the sub-flow if engine is available
        if self.engine:
            self._execute_subflow(flow_name, resolved_inputs, context, system)
        else:
            logger.warning(
                f"Flow call to '{flow_name}' not executed - no engine reference available"
            )

    def _resolve_flow_input(
        self,
        input_template: str,
        context: "ExecutionContext",
        step_result_data: dict[str, Any] = None,
    ) -> Any:
        """Resolve a flow input template with proper object handling."""
        if not isinstance(input_template, str):
            # Already resolved or is a literal value
            return input_template

        # Handle special templates that should preserve object types
        if input_template == "{{ result }}":
            # Direct access to result from step data to avoid string conversion
            if step_result_data and "result" in step_result_data:
                result = step_result_data["result"]
                logger.debug(
                    f"Flow input {{ result }}: Using direct access = {type(result).__name__}"
                )
                return result

        elif input_template == "{{ selected_item }}":
            # Handle selected_item from choice steps
            selected_item = context.get_variable("selected_item")
            if selected_item is not None:
                # If it's a string representation, try to convert back to typed object
                if isinstance(selected_item, str) and selected_item.startswith("{"):
                    typed_item = self._try_parse_structured_data(selected_item)
                    if typed_item is not None:
                        logger.debug(
                            f"Flow input {{ selected_item }}: Parsed from string to {type(typed_item).__name__}"
                        )
                        return typed_item
                logger.debug(
                    f"Flow input {{ selected_item }}: Using direct value = {type(selected_item).__name__}"
                )
                return selected_item

        elif input_template == "{{ results }}":
            # Handle results from table rolls with multiple items
            if step_result_data and "results" in step_result_data:
                results = step_result_data["results"]
                logger.debug(
                    f"Flow input {{ results }}: Using direct access = {type(results).__name__}"
                )
                return results

        # For path-based templates like "outputs.knave", resolve normally
        # but check if we can avoid template conversion for complex objects
        if input_template.startswith("outputs.") and not (
            "{{" in input_template and "}}" in input_template
        ):
            # Direct path access for outputs
            path = input_template[8:]  # Remove "outputs." prefix
            value = context.get_output(path)
            logger.debug(
                f"Flow input {input_template}: Direct path access = {type(value).__name__}"
            )
            return value

        # Fall back to template resolution for other cases
        try:
            resolved = context.resolve_template(input_template)
            logger.debug(
                f"Flow input {input_template}: Template resolved = {type(resolved).__name__}"
            )
            return resolved
        except Exception as e:
            logger.error(
                f"Failed to resolve flow input template '{input_template}': {e}"
            )
            raise

    def _try_parse_structured_data(self, value: str) -> Any:
        """Try to parse a string as structured data."""
        if not isinstance(value, str):
            return None

        # Only try parsing if it looks like structured data
        if not (
            value.strip().startswith(("{", "[")) and value.strip().endswith(("}", "]"))
        ):
            return None

        # Try JSON first (double quotes)
        try:
            import json

            parsed = json.loads(value)
            if isinstance(parsed, list | dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Try Python literal evaluation (single quotes)
        try:
            import ast

            parsed = ast.literal_eval(value)
            if isinstance(parsed, list | dict):
                return parsed
        except (ValueError, SyntaxError):
            pass

        return None

    def _execute_subflow(
        self,
        flow_name: str,
        flow_inputs: dict[str, Any],
        context: "ExecutionContext",
        system: "System",
    ) -> None:
        """Execute a sub-flow with the given inputs."""
        # Get the target flow
        target_flow = system.get_flow(flow_name)
        if not target_flow:
            logger.error(f"Flow '{flow_name}' not found in system")
            return

        # Create new execution context for sub-flow
        from ..models.context_data import ExecutionContext

        sub_context = ExecutionContext()

        # Copy system metadata
        sub_context.system_metadata = context.system_metadata.copy()

        # Set flow inputs
        for input_name, input_value in flow_inputs.items():
            sub_context.set_input(input_name, input_value)

        # Initialize flow variables
        if target_flow.variables:
            for variable in target_flow.variables:
                sub_context.set_variable(variable.id, variable.default)

        # Execute the sub-flow
        logger.debug(
            f"Executing sub-flow '{flow_name}' with inputs: {list(flow_inputs.keys())}"
        )
        result = self.engine.execute_flow(flow_name, sub_context, system)

        if result.success:
            logger.debug(f"Sub-flow '{flow_name}' completed successfully")

            # Copy sub-flow outputs back to main context
            # This allows the main flow to access results from the sub-flow
            for output_key, output_value in sub_context.outputs.items():
                # Only copy outputs that don't already exist in main context
                # to avoid overwriting main flow data
                if not context.outputs.get(output_key):
                    context.set_output(output_key, output_value)
                    logger.debug(f"Copied sub-flow output: {output_key}")
        else:
            logger.error(f"Sub-flow '{flow_name}' failed: {result.error}")


def create_flow_helper(engine=None) -> FlowExecutionHelper:
    """Factory function to create a flow execution helper."""
    return FlowExecutionHelper(engine)
