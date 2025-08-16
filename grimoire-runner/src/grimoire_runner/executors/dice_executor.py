"""Dice rolling step executor using wyrdbound-dice."""

import logging
from typing import TYPE_CHECKING, Any

from ..integrations.dice_integration import DiceIntegration
from ..models.roll_result import RollResult
from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System

# Import StepType and StepResult for runtime use
from ..models.flow import StepResult, StepType

logger = logging.getLogger(__name__)


class DiceExecutor(BaseStepExecutor):
    """Executor for dice rolling steps."""

    def __init__(self):
        """Initialize the DiceExecutor."""
        super().__init__()
        self.action_executor = None  # Will be lazily initialized
        self.dice_integration = DiceIntegration()

    def execute(self, step, context, system) -> StepResult:
        """Execute a dice-related step."""
        if step.type == StepType.DICE_ROLL:
            return self._execute_dice_roll(step, context, system)
        elif step.type == StepType.DICE_SEQUENCE:
            return self._execute_dice_sequence(step, context, system)
        else:
            return StepResult(
                step_id=step.id,
                success=False,
                error=f"Unsupported step type: {step.type}",
            )

    def _roll_dice_and_create_result(
        self, expression: str, modifier: int = 0, context=None, system=None
    ) -> RollResult:
        """Shared method to roll dice and create a consistent RollResult object."""
        dice_integration = DiceIntegration()

        # Apply modifiers if needed (for now, we'll handle them in the expression)
        if modifier != 0:
            if modifier > 0:
                expression = f"{expression}+{modifier}"
            else:
                expression = f"{expression}{modifier}"  # modifier is already negative

        result = dice_integration.roll_expression(expression)

        return RollResult(
            total=result.total,
            detail=result.detailed_result or f"{result.total}",
            expression=result.expression,
            breakdown=result.breakdown,
            individual_rolls=result.rolls,
        )

    def _execute_dice_roll(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a single dice roll."""
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
            modifier = 0
            if step.modifiers:
                # For simplicity, we'll handle modifiers by applying them to the roll expression
                # The dice integration should handle this, but we can prepare it here if needed
                pass  # Modifiers are handled by the dice integration

            # Use shared dice rolling method
            roll_result = self._roll_dice_and_create_result(
                str(roll_expression), modifier, context
            )

            # Log with detailed information
            if roll_result.detail:
                logger.debug(f"Dice roll: {roll_result.detail}")
            else:
                logger.debug(f"Dice roll: {roll_expression} = {roll_result.total}")

            # Prepare result data with both the structured object and legacy fields
            result_data = {
                "result": roll_result,  # New structured result
                "expression": roll_result.expression,
                "breakdown": roll_result.breakdown,
                "individual_rolls": roll_result.individual_rolls,
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
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a sequence of dice rolls."""
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

                # Use shared dice rolling method to get consistent RollResult
                roll_result = self._roll_dice_and_create_result(
                    str(roll_expression), 0, context
                )

                # Store both the total (for backwards compatibility) and the full RollResult
                results[item] = roll_result.total

                # Prepare individual result data
                item_data = {
                    "item": item,
                    "result": roll_result,  # Full RollResult object
                    "total": roll_result.total,  # For backwards compatibility
                    "expression": roll_result.expression,
                    "breakdown": roll_result.breakdown,
                    "individual_rolls": roll_result.individual_rolls,
                }
                all_results.append(item_data)

                # Execute item-specific actions with item context
                if sequence.actions:
                    for action in sequence.actions:
                        self._execute_sequence_action(
                            action, item, roll_result, context, system
                        )

            logger.debug(f"Dice sequence completed: {len(results)} rolls")

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
        item: str,
        dice_result: RollResult,
        context: "ExecutionContext",
        system: "System",
    ) -> None:
        """Execute a single action within a dice sequence with proper action executor support."""
        # Initialize action executor if needed
        if not hasattr(self, "action_executor") or self.action_executor is None:
            from .action_executor import ActionExecutor

            self.action_executor = ActionExecutor()

        # Prepare step data for the action executor with item and result
        step_data = {"item": item, "result": dice_result}

        logger.debug(
            f"Executing dice sequence action with step_data: item={item}, result={type(dice_result)}"
        )

        try:
            # Execute the action with step_data containing item and result
            logger.debug(f"Executing dice sequence action: {action}")
            logger.debug(f"Step data being passed: {step_data}")
            logger.debug(
                f"Context variables before action: {list(context.variables.keys())}"
            )
            self.action_executor.execute_actions([action], context, step_data, system)
        except Exception as e:
            logger.error(f"Error executing dice sequence action: {e}")
            logger.error(f"Action was: {action}")
            logger.error(f"Step data: {step_data}")
            logger.error(f"Context type: {type(context)}")
            logger.error(f"Result type: {type(dice_result)}")
            raise

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
