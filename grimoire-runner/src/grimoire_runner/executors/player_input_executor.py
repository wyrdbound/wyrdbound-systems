"""Player input step executor."""

import logging
from typing import TYPE_CHECKING

from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System
    from .action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class PlayerInputExecutor(BaseStepExecutor):
    """Executor for player input steps."""

    def __init__(self, action_executor: "ActionExecutor" = None):
        if action_executor is None:
            # Fallback to direct creation for backward compatibility
            from .action_executor import ActionExecutor

            action_executor = ActionExecutor()
        self.action_executor = action_executor

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a player input step."""
        from ..models.flow import StepResult

        try:
            step_name = getattr(step, "name", None) or step.id if step else "unknown"
            logger.debug(f"Player input step: {step_name}")
            if step and step.prompt:
                logger.debug(f"Prompt: {step.prompt}")

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

            # Execute step actions if present using the centralized ActionExecutor
            if step.actions:
                step_data = {"result": user_input, "user_input": user_input}
                self.action_executor.execute_actions(
                    step.actions, context, step_data, system
                )

            logger.debug(f"User input processed: '{user_input}'")

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
