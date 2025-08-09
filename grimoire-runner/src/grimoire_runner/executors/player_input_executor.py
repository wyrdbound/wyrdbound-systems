"""Player input step executor."""

import logging
from typing import TYPE_CHECKING

from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System

logger = logging.getLogger(__name__)


class PlayerInputExecutor(BaseStepExecutor):
    """Executor for player input steps."""

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a player input step."""
        from ..models.flow import StepResult

        try:
            step_name = getattr(step, "name", None) or step.id if step else "unknown"
            logger.info(f"Player input step: {step_name}")
            if step and step.prompt:
                logger.info(f"Prompt: {step.prompt}")

            return StepResult(
                step_id=step.id if step else "unknown",
                success=True,
                requires_input=True,
                prompt=step.prompt if step else None,
                data={
                    "input_type": "text",  # Default to text input
                    "validation": getattr(step, "validation", None) if step else None,
                },
            )

        except Exception as e:
            step_id = step.id if step and hasattr(step, "id") else "unknown"
            logger.error(f"Error executing player input step {step_id}: {e}")
            return StepResult(
                step_id=step_id, success=False, error=f"Player input step failed: {e}"
            )

    def process_input(
        self,
        user_input: str,
        step: "StepDefinition",
        context: "ExecutionContext",
        system: "System" = None,
    ) -> "StepResult":
        """Process user input for a player input step."""
        from ..models.flow import StepResult

        try:
            # Store the input result in the context
            context.set_variable("result", user_input)

            # Execute step actions if present
            if step.actions:
                for action in step.actions:
                    self._execute_action(action, context, user_input)

            logger.info(f"User input processed: '{user_input}'")

            return StepResult(
                step_id=step.id,
                success=True,
                data={"result": user_input, "user_input": user_input},
            )

        except Exception as e:
            logger.error(f"Error processing user input for step {step.id}: {e}")
            return StepResult(
                step_id=step.id,
                success=False,
                error=f"Input processing failed: {e}",
            )

    def _execute_action(self, action, context: "ExecutionContext", result: str) -> None:
        """Execute an action associated with player input."""
        # Handle both old format (key as action type) and new format (type field)
        if "type" in action and "data" in action:
            action_type = action["type"]
            action_data = action["data"]
        else:
            # Fallback to old format
            action_type = list(action.keys())[0]
            action_data = action[action_type]

        if action_type == "set_value":
            path = action_data["path"]
            value = action_data["value"]

            # Resolve templates in the value
            # Note: {{ result }} should resolve to the user's input
            resolved_value = context.resolve_template(str(value))

            # Get current flow namespace for proper isolation
            current_namespace = context.get_current_flow_namespace()

            if current_namespace:
                # Use namespaced path to avoid collision
                if path.startswith("outputs."):
                    namespaced_path = f"{current_namespace}.outputs.{path[8:]}"
                elif path.startswith("variables."):
                    namespaced_path = f"{current_namespace}.variables.{path[10:]}"
                else:
                    # Default to outputs
                    namespaced_path = f"{current_namespace}.outputs.{path}"

                context.set_namespaced_value(namespaced_path, resolved_value)
                logger.info(
                    f"Set namespaced value: {namespaced_path} = {resolved_value}"
                )
            else:
                # Fallback to original behavior for backward compatibility
                if path.startswith("outputs."):
                    context.set_output(path[8:], resolved_value)
                elif path.startswith("variables."):
                    context.set_variable(path[10:], resolved_value)
                else:
                    context.set_output(path, resolved_value)

        else:
            logger.warning(f"Unknown action type in player input step: {action_type}")

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the step."""
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
        return step_type == "player_input"

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate player input step configuration."""
        errors = []

        if not step.prompt:
            errors.append("Player input step must have a 'prompt'")

        return errors
