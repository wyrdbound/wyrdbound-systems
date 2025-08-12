"""Roll result models for structured dice roll data."""

from dataclasses import dataclass
from typing import Any


@dataclass
class RollResult:
    """Structured result from a dice roll operation."""

    total: int
    """Final numeric result of the roll."""

    detail: str
    """Detailed string representation of the roll (e.g., '11 = 11 (1d20: 11) + 0')."""

    expression: str
    """The dice expression that was rolled (e.g., '1d20 + 0')."""

    # Optional fields for advanced dice information
    breakdown: dict[str, Any] | None = None
    """Detailed breakdown of the roll from wyrdbound-dice."""

    individual_rolls: list | None = None
    """List of individual die results."""

    @property
    def description(self) -> str:
        """Alias for detail to support legacy template usage."""
        return self.detail

    def __str__(self) -> str:
        """String representation shows the detailed result."""
        return self.detail

    def __int__(self) -> int:
        """Integer representation returns the total."""
        return self.total

    def __lt__(self, other) -> bool:
        """Less than comparison based on total."""
        if isinstance(other, int | float):
            return self.total < other
        elif isinstance(other, RollResult):
            return self.total < other.total
        return NotImplemented

    def __le__(self, other) -> bool:
        """Less than or equal comparison based on total."""
        if isinstance(other, int | float):
            return self.total <= other
        elif isinstance(other, RollResult):
            return self.total <= other.total
        return NotImplemented

    def __gt__(self, other) -> bool:
        """Greater than comparison based on total."""
        if isinstance(other, int | float):
            return self.total > other
        elif isinstance(other, RollResult):
            return self.total > other.total
        return NotImplemented

    def __ge__(self, other) -> bool:
        """Greater than or equal comparison based on total."""
        if isinstance(other, int | float):
            return self.total >= other
        elif isinstance(other, RollResult):
            return self.total >= other.total
        return NotImplemented

    def __eq__(self, other) -> bool:
        """Equality comparison based on total."""
        if isinstance(other, int | float):
            return self.total == other
        elif isinstance(other, RollResult):
            return self.total == other.total
        return NotImplemented

    def __ne__(self, other) -> bool:
        """Inequality comparison based on total."""
        return not self.__eq__(other)
