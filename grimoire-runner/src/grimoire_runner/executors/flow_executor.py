"""Flow control step executor for completion and flow calls."""

import logging
from typing import TYPE_CHECKING

from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System
    from .action_executor import ActionExecutor

logger = logging.getLogger(__name__)


class FlowExecutor(BaseStepExecutor):
    """Executor for flow control steps like completion and flow calls."""

    def __init__(self, action_executor: "ActionExecutor" = None):
        if action_executor is None:
            # Fallback to direct creation for backward compatibility
            from .action_executor import ActionExecutor

            action_executor = ActionExecutor()
        self.action_executor = action_executor

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
                self.action_executor.execute_actions(step.actions, context, {})

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
