"""Dice rolling step executor using wyrdbound-dice."""

import logging
from typing import TYPE_CHECKING, Any

from ..integrations.dice_integration import DiceIntegration
from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System

logger = logging.getLogger(__name__)


class DiceExecutor(BaseStepExecutor):
    """Executor for dice rolling steps."""

    def __init__(self):
        self.dice_integration = DiceIntegration()

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a dice rolling step."""
        from ..models.flow import StepResult

        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)

        if step_type == "dice_roll":
            return self._execute_dice_roll(step, context)
        elif step_type == "dice_sequence":
            return self._execute_dice_sequence(step, context)
        else:
            return StepResult(
                step_id=step.id,
                success=False,
                error=f"DiceExecutor cannot handle step type: {step_type}",
            )

    def _execute_dice_roll(
        self, step: "StepDefinition", context: "ExecutionContext"
    ) -> "StepResult":
        """Execute a single dice roll."""
        from ..models.flow import StepResult

        if not step.roll:
            return StepResult(
                step_id=step.id,
                success=False,
                error="Dice roll step requires 'roll' parameter",
            )

        try:
            # Resolve the roll expression through templates
            roll_expression = context.resolve_template(step.roll)

            # Apply modifiers if present
            modifiers = {}
            if step.modifiers:
                for key, value in step.modifiers.items():
                    modifiers[key] = context.resolve_template(str(value))

            # Roll the dice
            result = self.dice_integration.roll_expression(
                str(roll_expression), modifiers
            )

            # Log with detailed information if available, otherwise fall back to simple format
            if result.detailed_result:
                logger.info(f"Dice roll: {result.detailed_result}")
            else:
                logger.info(f"Dice roll: {roll_expression} = {result.total}")

            # Prepare result data
            result_data = {
                "result": result.total,
                "expression": roll_expression,
                "breakdown": result.breakdown if hasattr(result, "breakdown") else None,
                "individual_rolls": result.rolls if hasattr(result, "rolls") else None,
            }

            return StepResult(
                step_id=step.id, success=True, data=result_data, prompt=step.prompt
            )

        except Exception as e:
            logger.error(f"Error rolling dice for step {step.id}: {e}")
            return StepResult(
                step_id=step.id, success=False, error=f"Dice roll failed: {e}"
            )

    def _execute_dice_sequence(
        self, step: "StepDefinition", context: "ExecutionContext"
    ) -> "StepResult":
        """Execute a sequence of dice rolls."""
        from ..models.flow import StepResult

        if not step.sequence:
            return StepResult(
                step_id=step.id,
                success=False,
                error="Dice sequence step requires 'sequence' parameter",
            )

        sequence = step.sequence
        results = {}
        all_results = []

        try:
            for item in sequence.items:
                # Resolve the roll expression
                roll_expression = context.resolve_template(sequence.roll)

                # Roll the dice
                result = self.dice_integration.roll_expression(str(roll_expression))
                results[item] = result.total

                # Prepare individual result data
                item_data = {
                    "item": item,
                    "result": result.total,
                    "expression": roll_expression,
                    "breakdown": result.breakdown
                    if hasattr(result, "breakdown")
                    else None,
                }
                all_results.append(item_data)

                # Execute item-specific actions with item context
                if sequence.actions:
                    for action in sequence.actions:
                        self._execute_sequence_action(
                            action, context, item, result.total
                        )

                # Display result if format specified (with item context)
                if sequence.display_as:
                    # Temporarily set item and result for display template
                    original_item = context.get_variable("item")
                    original_result = context.get_variable("result")

                    context.set_variable("item", item)
                    context.set_variable("result", result.total)

                    try:
                        display_text = context.resolve_template(sequence.display_as)
                        logger.info(f"Dice sequence result: {display_text}")
                    finally:
                        # Restore original values
                        if original_item is not None:
                            context.set_variable("item", original_item)
                        else:
                            context.variables.pop("item", None)
                        if original_result is not None:
                            context.set_variable("result", original_result)
                        else:
                            context.variables.pop("result", None)

            logger.info(f"Dice sequence completed: {len(results)} rolls")

            return StepResult(
                step_id=step.id,
                success=True,
                data={
                    "results": results,
                    "all_results": all_results,
                    "sequence_items": sequence.items,
                },
                prompt=step.prompt,
            )

        except Exception as e:
            logger.error(f"Error executing dice sequence for step {step.id}: {e}")
            return StepResult(
                step_id=step.id, success=False, error=f"Dice sequence failed: {e}"
            )

    def _execute_sequence_action(
        self,
        action: dict[str, Any],
        context: "ExecutionContext",
        item: str,
        result: int,
    ) -> None:
        """Execute an action within a dice sequence with item context."""
        # Add item and result to template context temporarily
        original_item = context.get_variable("item")
        original_result = context.get_variable("result")

        context.set_variable("item", item)
        context.set_variable("result", result)

        try:
            # Execute the action (simplified version)
            action_type = list(action.keys())[0]
            action_data = action[action_type]

            if action_type == "set_value":
                path = action_data["path"]
                value = action_data["value"]

                # Resolve template in path and value
                resolved_path = context.resolve_template(str(path))
                resolved_value = context.resolve_template(str(value))

                # Set the value using the unified output system
                if str(resolved_path).startswith("outputs."):
                    context.set_output(
                        str(resolved_path)[8:], resolved_value
                    )
                elif str(resolved_path).startswith("variables."):
                    context.set_variable(str(resolved_path)[10:], resolved_value)
                else:
                    context.set_output(str(resolved_path), resolved_value)

        finally:
            # Restore original values
            if original_item is not None:
                context.set_variable("item", original_item)
            else:
                context.variables.pop("item", None)
            if original_result is not None:
                context.set_variable("result", original_result)
            else:
                context.variables.pop("result", None)

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the step."""
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
        return step_type in ["dice_roll", "dice_sequence"]

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate dice step configuration."""
        errors = []
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)

        if step_type == "dice_roll":
            if not step.roll:
                errors.append("Dice roll step must have 'roll' parameter")
        elif step_type == "dice_sequence":
            if not step.sequence:
                errors.append("Dice sequence step must have 'sequence' parameter")
            elif not step.sequence.items:
                errors.append("Dice sequence must have 'items' list")
            elif not step.sequence.roll:
                errors.append("Dice sequence must have 'roll' expression")

        return errors
