"""Integration with wyrdbound-dice package for dice rolling."""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

try:
    import wyrdbound_dice

    DICE_AVAILABLE = True
except ImportError:
    DICE_AVAILABLE = False
    logger.warning("wyrdbound-dice package not available, using fallback dice rolling")


@dataclass
class DiceResult:
    """Result of a dice roll."""

    total: int
    expression: str
    breakdown: dict[str, Any] | None = None
    rolls: list | None = None


class DiceIntegration:
    """Integration with wyrdbound-dice package."""

    def __init__(self):
        if DICE_AVAILABLE:
            try:
                self.dice = wyrdbound_dice.Dice()
                self._available = True
                logger.debug("wyrdbound-dice integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize wyrdbound-dice: {e}")
                self._available = False
        else:
            self._available = False
            logger.warning("Using fallback dice implementation")

    def is_available(self) -> bool:
        """Check if wyrdbound-dice is available."""
        return self._available

    def roll_expression(
        self, expression: str, modifiers: dict | None = None
    ) -> DiceResult:
        """Roll a dice expression and return the result."""
        if self._available:
            return self._roll_with_wyrdbound(expression, modifiers)
        else:
            return self._roll_fallback(expression, modifiers)

    def _roll_with_wyrdbound(
        self, expression: str, modifiers: dict | None = None
    ) -> DiceResult:
        """Roll using wyrdbound-dice package."""
        try:
            # Use wyrdbound-dice to roll
            result = self.dice.roll(expression, modifiers or {})

            return DiceResult(
                total=result.total if hasattr(result, "total") else int(result),
                expression=expression,
                breakdown=self._get_roll_breakdown(result),
                rolls=self._get_individual_rolls(result),
            )
        except Exception as e:
            logger.error(f"Error rolling with wyrdbound-dice: {e}")
            # Fall back to simple implementation
            return self._roll_fallback(expression, modifiers)

    def _roll_fallback(
        self, expression: str, modifiers: dict | None = None
    ) -> DiceResult:
        """Fallback dice rolling implementation."""
        import random
        import re

        try:
            # Simple parser for basic dice expressions like "3d6", "1d20+5", etc.
            # This is a very basic implementation for testing

            # Clean up the expression
            expr = expression.lower().strip()

            # Handle simple cases
            if "d" not in expr:
                # Plain number
                return DiceResult(total=int(expr), expression=expression)

            # Basic dice parsing (e.g., "3d6", "1d20+5")
            match = re.match(r"(\d*)d(\d+)([+-]\d+)?", expr)
            if not match:
                # Fallback to 1
                logger.warning(f"Could not parse dice expression: {expression}")
                return DiceResult(total=1, expression=expression)

            num_dice = int(match.group(1)) if match.group(1) else 1
            die_size = int(match.group(2))
            modifier = int(match.group(3)) if match.group(3) else 0

            # Roll the dice
            rolls = []
            for _ in range(num_dice):
                roll = random.randint(1, die_size)
                rolls.append(roll)

            total = sum(rolls) + modifier

            return DiceResult(
                total=total,
                expression=expression,
                breakdown={
                    "num_dice": num_dice,
                    "die_size": die_size,
                    "modifier": modifier,
                    "base_total": sum(rolls),
                },
                rolls=rolls,
            )

        except Exception as e:
            logger.error(f"Error in fallback dice rolling: {e}")
            return DiceResult(total=1, expression=expression)

    def _get_roll_breakdown(self, result) -> dict[str, Any] | None:
        """Extract roll breakdown from wyrdbound-dice result."""
        try:
            if hasattr(result, "breakdown"):
                return result.breakdown
            elif hasattr(result, "__dict__"):
                return {
                    k: v for k, v in result.__dict__.items() if not k.startswith("_")
                }
        except Exception:
            pass
        return None

    def _get_individual_rolls(self, result) -> list | None:
        """Extract individual roll results from wyrdbound-dice result."""
        try:
            if hasattr(result, "rolls"):
                return result.rolls
            elif hasattr(result, "individual_rolls"):
                return result.individual_rolls
        except Exception:
            pass
        return None

    def get_roll_breakdown(self, result: DiceResult) -> dict:
        """Return detailed breakdown for debugging."""
        return {
            "total": result.total,
            "expression": result.expression,
            "breakdown": result.breakdown,
            "individual_rolls": result.rolls,
            "using_wyrdbound": self._available,
        }
