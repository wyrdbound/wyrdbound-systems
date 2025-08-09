"""Base step executor interface."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System


class BaseStepExecutor(ABC):
    """Base class for all step executors."""

    @abstractmethod
    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a step and return the result."""

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the given step type."""
        return True

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate that a step is properly configured for this executor."""
        return []
