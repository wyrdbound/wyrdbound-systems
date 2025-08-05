"""Flow control step executor for completion and flow calls."""

import logging
from typing import TYPE_CHECKING

from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System

logger = logging.getLogger(__name__)


class FlowExecutor(BaseStepExecutor):
    """Executor for flow control steps like completion and flow calls."""

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a flow control step."""
        from ..models.flow import StepResult

        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)

        if step_type == "completion":
            return self._execute_completion(step, context)
        elif step_type == "flow_call":
            return self._execute_flow_call(step, context, system)
        else:
            return StepResult(
                step_id=step.id,
                success=False,
                error=f"FlowExecutor cannot handle step type: {step_type}",
            )

    def _execute_completion(
        self, step: "StepDefinition", context: "ExecutionContext"
    ) -> "StepResult":
        """Execute a completion step (marks end of flow)."""
        from ..models.flow import StepResult

        try:
            logger.info(f"Flow completion: {step.name}")
            if step.prompt:
                logger.info(f"Completion message: {step.prompt}")

            # Execute any actions defined in the completion step
            if hasattr(step, "actions") and step.actions:
                logger.info(f"Executing {len(step.actions)} actions in completion step")
                for action in step.actions:
                    self._execute_action(action, context)

            return StepResult(
                step_id=step.id,
                success=True,
                data={"completion": True, "message": step.prompt},
                prompt=step.prompt,
            )

        except Exception as e:
            logger.error(f"Error executing completion step {step.id}: {e}")
            return StepResult(
                step_id=step.id, success=False, error=f"Completion step failed: {e}"
            )

    def _execute_flow_call(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a flow call step (calls another flow as subroutine)."""
        from ..models.flow import StepResult

        try:
            # For now, just log the flow call
            # Full implementation would require access to the engine
            logger.info(f"Flow call requested: {step.name}")
            logger.warning("Flow call execution not yet fully implemented")

            return StepResult(
                step_id=step.id,
                success=True,
                data={
                    "flow_call": True,
                    "target_flow": step.name,
                    "implemented": False,
                },
                prompt=step.prompt,
            )

        except Exception as e:
            logger.error(f"Error executing flow call step {step.id}: {e}")
            return StepResult(
                step_id=step.id, success=False, error=f"Flow call step failed: {e}"
            )

    def _execute_action(self, action: dict, context: "ExecutionContext") -> None:
        """Execute a single action within a step."""
        action_type = list(action.keys())[0]  # Get the action type (first key)
        action_data = action[action_type]

        logger.info(f"Executing action: {action_type}")

        if action_type == "set_value":
            # Handle set_value actions
            path = action_data["path"]
            value_template = action_data["value"]

            logger.info(f"Action set_value: path={path}, template={value_template}")

            # Check if this is a list append operation that should be handled programmatically
            if self._is_list_append_operation(value_template):
                resolved_value = self._handle_list_append_operation(
                    value_template, context
                )
                logger.info(
                    f"Handled list append programmatically: {type(resolved_value).__name__} with {len(resolved_value) if hasattr(resolved_value, '__len__') else 'N/A'} items"
                )
            else:
                # Resolve the value template normally
                try:
                    resolved_value = context.resolve_template(value_template)
                    logger.info(
                        f"Resolved template to: {type(resolved_value).__name__} = {resolved_value}"
                    )
                except Exception as e:
                    logger.error(f"Failed to resolve template: {e}")
                    raise

            try:
                logger.info(f"Setting {path} = {resolved_value}")
                context.set_output(path, resolved_value)
                logger.info(f"Successfully set output {path}")
            except Exception as e:
                logger.error(f"Failed to set value at {path}: {e}")
                raise

        elif action_type == "log_event":
            # Handle log_event actions
            message_template = action_data.get("message", "")
            try:
                resolved_message = context.resolve_template(message_template)
                logger.info(f"Log event: {resolved_message}")
            except Exception as e:
                logger.warning(f"Failed to resolve log message: {e}")

        else:
            logger.warning(f"Unknown action type: {action_type}")

    def _is_list_append_operation(self, template: str) -> bool:
        """Check if a template represents a list append operation."""
        # Look for patterns like: (some_list | default([])) + [some_item]
        # This is a heuristic to detect list concatenation operations
        return (
            isinstance(template, str)
            and ") + [" in template
            and "default([])" in template
        )

    def _handle_list_append_operation(self, template: str, context) -> list:
        """Handle list append operations programmatically to preserve object types."""
        import re

        # Parse template like: "{{ (inputs.character.inventory | default([])) + [inputs.item] }}"
        # Extract the base list path and the item to append

        # Remove {{ }} wrappers
        inner_template = template.strip()
        if inner_template.startswith("{{") and inner_template.endswith("}}"):
            inner_template = inner_template[2:-2].strip()

        # Look for pattern: (path | default([])) + [item_path]
        pattern = r"\(([^|]+)\s*\|\s*default\(\[\]\)\)\s*\+\s*\[([^\]]+)\]"
        match = re.search(pattern, inner_template)

        if not match:
            # Fallback to normal template resolution if pattern doesn't match
            logger.warning(f"Could not parse list append pattern: {template}")
            return context.resolve_template(template)

        base_list_path = match.group(1).strip()
        item_path = match.group(2).strip()

        logger.info(
            f"Parsed list append: base_list='{base_list_path}', item='{item_path}'"
        )

        # Get the current list (or empty list if None)
        try:
            # For inventory lists, try direct access first to avoid string conversion in template resolution
            if base_list_path == "inputs.character.inventory":
                # Access the inventory directly from the context without template resolution
                character_data = context.inputs.get("character", {})
                current_list = character_data.get("inventory")
                logger.info(
                    f"Direct access to inventory: {type(current_list).__name__} with {len(current_list) if isinstance(current_list, list) else 'non-list'} items"
                )
            else:
                # For other paths, use template resolution
                current_list = context.resolve_template(f"{{{{ {base_list_path} }}}}")

            if current_list is None:
                current_list = []
            elif (
                isinstance(current_list, str)
                and current_list.startswith("[")
                and current_list.endswith("]")
            ):
                # If it's a string representation of a list, try to parse it carefully
                # But this might not work for complex objects, so we'll default to empty list
                logger.warning(
                    f"Base list is string representation, starting fresh: {current_list}"
                )
                current_list = []
            elif not isinstance(current_list, list):
                logger.warning(
                    f"Base list is not a list type ({type(current_list)}), starting fresh"
                )
                current_list = []
            else:
                # Make a copy to avoid modifying the original
                current_list = list(current_list)
        except Exception as e:
            logger.warning(
                f"Could not resolve base list '{base_list_path}': {e}, starting with empty list"
            )
            current_list = []

        # Get the item to append
        try:
            # For complex objects, avoid template resolution which converts to strings
            # Instead, access the value directly from the context
            if item_path == "inputs.item":
                # Direct access to avoid string conversion
                item_to_append = context.inputs.get("item")
                if item_to_append is None:
                    # Fallback to template resolution
                    resolved = context.resolve_template(f"{{{{ {item_path} }}}}")
                    # Check if template resolution returned the string "None" (from None value conversion)
                    if resolved == "None":
                        item_to_append = None
                    else:
                        item_to_append = resolved
                logger.info(
                    f"Item to append (direct): {type(item_to_append).__name__} = {item_to_append}"
                )
            else:
                # Use template resolution for other paths
                item_to_append = context.resolve_template(f"{{{{ {item_path} }}}}")
                # Check if template resolution returned the string "None" (from None value conversion)
                if item_to_append == "None":
                    item_to_append = None
                logger.info(
                    f"Item to append (template): {type(item_to_append).__name__} = {item_to_append}"
                )
        except Exception as e:
            logger.error(f"Could not resolve item '{item_path}': {e}")
            raise

        # Skip None items (e.g., from table rolls that resulted in "none")
        if item_to_append is None:
            logger.info("Skipping None item, not appending to list")
            return current_list

        # Append the item and return the new list
        current_list.append(item_to_append)
        logger.info(f"Created new list with {len(current_list)} items")

        # Debug: Check what types are in the final list
        for i, item in enumerate(current_list):
            logger.info(f"List item {i}: {type(item).__name__} = {item}")

        return current_list

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the step."""
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
        return step_type in ["completion", "flow_call"]

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate flow control step configuration."""
        errors = []

        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)

        if step_type == "flow_call":
            # TODO: Add validation for flow call parameters
            pass

        return errors
