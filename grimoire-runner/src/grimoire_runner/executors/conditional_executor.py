"""Conditional step executor."""

import logging
from typing import TYPE_CHECKING

from .action_executor import ActionExecutor
from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System

logger = logging.getLogger(__name__)


class ConditionalExecutor(BaseStepExecutor):
    """Executor for conditional steps."""

    def __init__(self, action_executor: ActionExecutor = None):
        """Initialize with an action executor for performing actions."""
        self.action_executor = action_executor or ActionExecutor()

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a conditional step."""
        from ..models.flow import StepResult

        logger.debug(f"Executing conditional step: {step.id}")

        # Get condition from either 'if' or 'condition' field
        condition = getattr(step, "if_condition", None) or step.condition

        if not condition:
            return StepResult(
                step_id=step.id,
                success=False,
                error="No condition specified for conditional step",
            )

        # Evaluate the condition using template service
        from ..services.template_service import TemplateService

        template_service = TemplateService()

        # Create template context for evaluation
        template_context = {
            "inputs": context.inputs,
            "outputs": context.outputs,
            "variables": context.variables,
            "system": context.system_metadata
            if hasattr(context, "system_metadata")
            else {},
        }

        try:
            logger.debug(f"Evaluating condition template: '{condition}'")
            condition_result = template_service.resolve_template(
                condition, template_context, "runtime"
            )
            logger.debug(f"Condition after template resolution: '{condition_result}'")
            # Convert to boolean
            is_true = self._evaluate_condition(condition_result)
            logger.debug(
                f"Condition '{condition}' -> '{condition_result}' -> {is_true}"
            )

        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return StepResult(
                step_id=step.id,
                success=False,
                error=f"Condition evaluation failed: {e}",
            )

        # Execute appropriate branch
        if is_true and step.then_actions:
            logger.debug("Executing 'then' branch")
            if isinstance(step.then_actions, list):
                self._execute_action_list(step.then_actions, context, system)
        elif not is_true and step.else_actions:
            logger.debug("Executing 'else' branch")
            if isinstance(step.else_actions, list):
                self._execute_action_list(step.else_actions, context, system)
            else:
                # Handle nested conditional in else block
                self._execute_nested_conditional(step.else_actions, context, system)

        return StepResult(
            step_id=step.id,
            success=True,
            data={"condition_result": is_true},
            next_step_id=step.next_step,
        )

    def _evaluate_condition(self, condition_str: str) -> bool:
        """Evaluate a condition string to boolean."""
        if isinstance(condition_str, bool):
            return condition_str

        if isinstance(condition_str, str):
            lower_str = condition_str.lower().strip()
            if lower_str in ["true", "yes", "1"]:
                return True
            elif lower_str in ["false", "no", "0", ""]:
                return False
            # Try to evaluate as Python expression (simple comparisons)
            try:
                return bool(eval(condition_str))
            except Exception:
                return bool(condition_str)

        return bool(condition_str)

    def _execute_action_list(
        self, actions: list[dict], context: "ExecutionContext", system: "System"
    ):
        """Execute a list of actions from the conditional branch."""
        for action_dict in actions:
            self.action_executor.execute_single_action(action_dict, context, {}, system)

    def _execute_nested_conditional(
        self, conditional_data: dict, context: "ExecutionContext", system: "System"
    ):
        """Execute a nested conditional structure."""
        from ..services.template_service import TemplateService

        template_service = TemplateService()

        # Create template context for evaluation
        template_context = {
            "inputs": context.inputs,
            "outputs": context.outputs,
            "variables": context.variables,
            "system": context.system_metadata
            if hasattr(context, "system_metadata")
            else {},
        }

        # Check if this is a nested conditional
        if "if" in conditional_data:
            condition = conditional_data["if"]
            try:
                logger.debug(f"Evaluating nested condition template: '{condition}'")
                condition_result = template_service.resolve_template(
                    condition, template_context, "runtime"
                )
                logger.debug(
                    f"Nested condition after template resolution: '{condition_result}'"
                )
                is_true = self._evaluate_condition(condition_result)
                logger.debug(
                    f"Nested condition '{condition}' -> '{condition_result}' -> {is_true}"
                )

                if is_true and "then" in conditional_data:
                    then_actions = conditional_data["then"]
                    if isinstance(then_actions, list):
                        self._execute_action_list(then_actions, context, system)
                elif not is_true and "else" in conditional_data:
                    else_actions = conditional_data["else"]
                    if isinstance(else_actions, list):
                        self._execute_action_list(else_actions, context, system)
                    elif isinstance(else_actions, dict):
                        self._execute_nested_conditional(else_actions, context, system)

            except Exception as e:
                logger.error(f"Error evaluating nested condition '{condition}': {e}")

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the given step."""
        from ..models.flow import StepType

        return step.type == StepType.CONDITIONAL

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate a conditional step definition."""
        errors = []

        # Check that we have a condition
        condition = getattr(step, "if_condition", None) or step.condition
        if not condition:
            errors.append("Conditional step must have either 'if' or 'condition' field")

        # Check that we have at least one branch
        if not step.then_actions and not step.else_actions:
            errors.append(
                "Conditional step must have at least 'then' or 'else' actions"
            )

        return errors
