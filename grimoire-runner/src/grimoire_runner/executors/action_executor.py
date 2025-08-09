"""Action execution utilities for handling step actions."""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.system import System

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Handles execution of step actions, separated from main flow execution."""

    def execute_actions(
        self,
        actions: list[dict[str, Any]],
        context: "ExecutionContext",
        step_data: dict[str, Any],
        system: "System | None" = None,
    ) -> None:
        """Execute a list of actions."""
        for action in actions:
            try:
                self.execute_single_action(action, context, step_data, system)
            except Exception as e:
                logger.error(f"Error executing action {action}: {e}")

    def execute_single_action(
        self,
        action: dict[str, Any],
        context: "ExecutionContext",
        step_data: dict[str, Any],
        system: "System | None" = None,
    ) -> None:
        """Execute a single action."""
        # Handle both old format (key as action type) and new format (type field)
        if "type" in action and "data" in action:
            action_type = action["type"]
            action_data = action["data"]
        else:
            # Fallback to old format
            action_type = list(action.keys())[0]
            action_data = action[action_type]

        # Temporarily add step_data to context for template resolution
        original_values = {}
        if step_data:
            for key, value in step_data.items():
                original_values[key] = context.get_variable(key)
                context.set_variable(key, value)

        try:
            if action_type == "set_value":
                self._execute_set_value_action(action_data, context)
            elif action_type == "get_value":
                # This is typically used in templates, not as a standalone action
                pass
            elif action_type == "display_value":
                self._execute_display_value_action(action_data, context)
            elif action_type == "validate_value":
                # TODO: Implement validation
                pass
            elif action_type == "log_event":
                self._execute_log_event_action(action_data, context)
            elif action_type == "swap_values":
                self._execute_swap_values_action(action_data, context)
            elif action_type == "flow_call":
                self._execute_flow_call_action(action_data, context, system)
            else:
                logger.warning(f"Unknown action type: {action_type}")

        finally:
            # Restore original values
            if step_data:
                for key in step_data.keys():
                    if original_values[key] is not None:
                        context.set_variable(key, original_values[key])
                    else:
                        context.variables.pop(key, None)

    def _execute_set_value_action(
        self, action_data: dict[str, Any], context: "ExecutionContext"
    ) -> None:
        """Execute a set_value action."""
        path = action_data["path"]
        value = action_data["value"]

        # Handle dictionary values specially to avoid string conversion
        if isinstance(value, dict):
            # Use dictionary directly without template resolution
            resolved_value = value
            logger.info(f"Action set_value: Using dict directly for {path}")
        else:
            # Resolve template in value for non-dict values
            resolved_value = context.resolve_template(str(value))
            logger.info(f"Action set_value: Resolved template for {path}")

        # Use namespaced paths to avoid collision during flow execution
        current_namespace = context.get_current_flow_namespace()

        if current_namespace:
            # Use namespaced path to avoid collision
            if path.startswith("outputs."):
                namespaced_path = f"{current_namespace}.outputs.{path[8:]}"
            elif path.startswith("variables."):
                namespaced_path = f"{current_namespace}.variables.{path[10:]}"
            else:
                # Default to outputs if no prefix specified
                namespaced_path = f"{current_namespace}.outputs.{path}"

            context.set_namespaced_value(namespaced_path, resolved_value)
        else:
            # Fallback to original behavior for backward compatibility
            if path.startswith("outputs."):
                context.set_output(path[8:], resolved_value)
            elif path.startswith("variables."):
                context.set_variable(path[10:], resolved_value)
            else:
                # Default to outputs
                context.set_output(path, resolved_value)

    def _execute_display_value_action(
        self, action_data: dict[str, Any] | str, context: "ExecutionContext"
    ) -> None:
        """Execute a display_value action."""
        # For now, just log the value
        path = action_data if isinstance(action_data, str) else action_data.get("path", "")
        try:
            value = context.resolve_path_value(path)
            logger.info(f"Display: {path} = {value}")
        except Exception as e:
            logger.warning(f"Could not display value at path {path}: {e}")

    def _execute_log_event_action(
        self, action_data: dict[str, Any], context: "ExecutionContext"
    ) -> None:
        """Execute a log_event action."""
        event_type = action_data.get("type", "unknown")
        event_data = action_data.get("data", {})
        logger.info(f"Event: {event_type} - {event_data}")

    def _execute_swap_values_action(
        self, action_data: dict[str, Any], context: "ExecutionContext"
    ) -> None:
        """Execute a swap_values action."""
        # Swap values between two paths
        path1 = action_data.get("path1", "")
        path2 = action_data.get("path2", "")

        # Resolve templates in the paths
        path1 = context.resolve_template(path1)
        path2 = context.resolve_template(path2)

        try:
            # Get values from both paths
            value1 = context.resolve_path_value(path1)
            value2 = context.resolve_path_value(path2)

            # Swap them
            self._set_value_at_path(context, path1, value2)
            self._set_value_at_path(context, path2, value1)

            logger.info(f"Swapped values: {path1} <-> {path2}")

        except Exception as e:
            logger.error(f"Error swapping values between {path1} and {path2}: {e}")

    def _execute_flow_call_action(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None",
    ) -> None:
        """Execute a flow_call action."""
        # Handle sub-flow calls
        flow_id = action_data["flow"]
        raw_inputs = action_data.get("inputs", {})
        logger.info(f"Engine action flow_call: {flow_id} (raw inputs: {raw_inputs})")

        # Resolve input templates using the current context
        resolved_inputs = {}
        for input_key, input_value in raw_inputs.items():
            if isinstance(input_value, str):
                # Resolve any templates in the input value
                try:
                    if input_value.startswith("{{") and input_value.endswith("}}"):
                        # This is a template, resolve it while preserving object types
                        resolved_value = context.resolve_template(input_value)
                        logger.info(
                            f"Resolved template {input_key}: {input_value} -> {type(resolved_value).__name__}"
                        )
                    elif "outputs." in input_value:
                        # This is a path reference, resolve it
                        resolved_value = context.resolve_path_value(input_value)
                        logger.info(
                            f"Resolved path {input_key}: {input_value} -> {type(resolved_value).__name__}"
                        )
                    else:
                        # Plain string, use as-is
                        resolved_value = input_value
                    resolved_inputs[input_key] = resolved_value
                except Exception as e:
                    logger.error(
                        f"Failed to resolve input {input_key}: {input_value} - {e}"
                    )
                    resolved_inputs[input_key] = input_value
            else:
                # Non-string values, use as-is
                resolved_inputs[input_key] = input_value

        logger.info(f"Engine action flow_call resolved inputs: {resolved_inputs}")

        # Import here to avoid circular imports
        from .table_executor import TableExecutor

        # Use the table executor's sub-flow execution logic
        # since it already handles the template resolution and typing correctly
        table_executor = TableExecutor()
        try:
            if system:
                table_executor._execute_sub_flow(
                    flow_id, resolved_inputs, context, system, raw_inputs
                )
                logger.info(f"Successfully executed sub-flow: {flow_id}")
            else:
                logger.error(f"No system available for sub-flow execution: {flow_id}")
        except Exception as e:
            logger.error(f"Error executing sub-flow {flow_id}: {e}")

    def _set_value_at_path(
        self, context: "ExecutionContext", path: str, value: Any
    ) -> None:
        """Set a value at a specific path in the context."""
        if path.startswith("outputs."):
            context.set_output(path[8:], value)
        elif path.startswith("variables."):
            context.set_variable(path[10:], value)
        else:
            # Default to outputs
            context.set_output(path, value)
