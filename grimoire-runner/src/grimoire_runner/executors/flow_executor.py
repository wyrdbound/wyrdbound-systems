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

        # Initialize template service
        from ..services.template_service import TemplateService

        self.template_service = TemplateService()

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
            logger.debug(f"Flow completion: {step.name}")
            if step.prompt:
                logger.debug(f"Completion message: {step.prompt}")

            # Execute any actions defined in the completion step
            if hasattr(step, "actions") and step.actions:
                logger.debug(
                    f"Executing {len(step.actions)} actions in completion step"
                )
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
            if not hasattr(step, "flow") or not step.flow:
                raise ValueError(
                    f"flow_call step '{step.id}' missing required 'flow' field"
                )

            if not hasattr(step, "inputs"):
                raise ValueError(f"flow_call step '{step.id}' missing 'inputs' field")

            flow_name = step.flow
            flow_inputs = step.inputs or {}

            logger.debug(f"Flow call requested: {flow_name}")
            logger.debug(f"Executing sub-flow: {flow_name}")

            # Validate that target flow exists
            target_flow = system.get_flow(flow_name)
            if not target_flow:
                raise ValueError(
                    f"Target flow '{flow_name}' not found in system '{system.id}'"
                )

            # Resolve template inputs for the sub-flow
            resolved_inputs = self._resolve_flow_call_inputs(
                flow_inputs, context, system
            )

            # Execute the sub-flow
            sub_flow_result = self._execute_sub_flow(
                flow_name, resolved_inputs, context, system
            )

            if not sub_flow_result.success:
                raise RuntimeError(
                    f"Sub-flow '{flow_name}' execution failed: {sub_flow_result.error}"
                )

            # Get sub-flow outputs
            sub_flow_outputs = sub_flow_result.outputs or {}

            logger.debug(
                f"Sub-flow {flow_name} completed with success: {sub_flow_result.success}"
            )
            logger.debug(
                f"Sub-flow outputs after completion: {list(sub_flow_outputs.keys())}"
            )

            # Log output details for debugging
            for key, value in sub_flow_outputs.items():
                logger.debug(f"Sub-flow output {key}: {type(value).__name__} = {value}")

            logger.debug(
                f"Sub-flow {flow_name} completed successfully with outputs: {list(sub_flow_outputs.keys())}"
            )

            # Execute flow_call step actions with result context
            if hasattr(step, "actions") and step.actions:
                logger.debug(f"Executing {len(step.actions)} actions in flow_call step")

                # Create action context that includes 'result' variable
                action_context = self._create_action_context_with_result(
                    context, sub_flow_outputs
                )

                # Execute actions with the enhanced context
                self.action_executor.execute_actions(
                    step.actions, action_context, {}, system
                )

            return StepResult(
                step_id=step.id,
                success=True,
                data={
                    "flow_call": True,
                    "target_flow": flow_name,
                    "sub_flow_outputs": sub_flow_outputs,
                },
                prompt=step.prompt,
            )

        except Exception as e:
            error_msg = f"Flow call step '{step.id}' failed: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _resolve_flow_call_inputs(self, flow_inputs, context, system):
        """Resolve template variables in flow_call inputs."""
        resolved_inputs = {}
        for key, value in flow_inputs.items():
            try:
                resolved_value = (
                    self.template_service.resolve_template_with_execution_context(
                        value, context, system, mode="runtime"
                    )
                )
                resolved_inputs[key] = resolved_value
                logger.debug(f"Resolved input {key}: {resolved_value}")
            except Exception as e:
                raise ValueError(
                    f"Failed to resolve flow_call input '{key}': {e}"
                ) from e

        return resolved_inputs

    def _execute_sub_flow(self, flow_name, resolved_inputs, context, system):
        """Execute the sub-flow with resolved inputs."""
        # Import inside method to avoid circular imports
        from ..core.engine import GrimoireEngine
        from ..models.context_data import ExecutionContext

        # Create a new execution context for the sub-flow
        sub_context = ExecutionContext()

        # Set the resolved inputs in the sub-flow context
        for key, value in resolved_inputs.items():
            sub_context.set_input(key, value)

        engine = GrimoireEngine()

        logger.debug(f"Starting sub-flow execution: {flow_name}")
        logger.debug(f"Sub-flow inputs: {resolved_inputs}")

        try:
            result = engine.execute_flow(flow_name, sub_context, system)
            logger.debug(f"Sub-flow result type: {type(result)}")
            if hasattr(result, "success"):
                logger.debug(f"Sub-flow success: {result.success}")
            if hasattr(result, "outputs"):
                logger.debug(f"Sub-flow outputs: {result.outputs}")
            return result
        except Exception as e:
            raise RuntimeError(f"Sub-flow '{flow_name}' execution error: {e}") from e

    def _create_action_context_with_result(self, context, sub_flow_outputs):
        """Create action execution context that includes 'result' variable."""

        class ResultObject:
            """Result object that allows dot notation access to sub-flow outputs."""

            def __init__(self, outputs):
                for key, value in outputs.items():
                    setattr(self, key, value)

        class ActionContextWithResult:
            """Context wrapper that adds 'result' variable to action execution."""

            def __init__(self, original_context, result_obj):
                self.original_context = original_context
                self.result = result_obj
                # Add result to variables for template resolution
                self.original_context.set_variable("result", result_obj)

            def __getattr__(self, name):
                # First try to get from result object
                if name == "result":
                    return self.result
                # Then delegate to original context
                return getattr(self.original_context, name)

            def get_variable(self, name):
                """Get variable with 'result' support."""
                if name == "result":
                    return self.result
                return self.original_context.get_variable(name)

        # Create result object from sub-flow outputs
        result_obj = ResultObject(sub_flow_outputs)

        # Create enhanced context
        action_context = ActionContextWithResult(context, result_obj)

        logger.debug(
            f"Created action context with result object containing: {list(sub_flow_outputs.keys())}"
        )

        return action_context

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
