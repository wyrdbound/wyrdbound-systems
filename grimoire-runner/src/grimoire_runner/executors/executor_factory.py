"""Step executor interface and factory for dependency injection."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System


class StepExecutorInterface(Protocol):
    """Protocol defining the interface that all step executors must implement."""

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a step and return the result."""
        ...

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the given step type."""
        ...

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate that a step is properly configured for this executor."""
        ...


class ExecutorFactory(ABC):
    """Abstract factory for creating step executors."""

    @abstractmethod
    def create_executor(
        self, step_type: str, engine: "GrimoireEngine"
    ) -> StepExecutorInterface:
        """Create an executor for the given step type."""

    @abstractmethod
    def get_supported_step_types(self) -> list[str]:
        """Get the list of step types this factory supports."""


class DefaultExecutorFactory(ExecutorFactory):
    """Default factory that creates the built-in step executors."""

    def __init__(self, executor_registry: "ExecutorRegistry" = None):
        """Initialize with optional executor registry for dependency injection."""
        self.executor_registry = executor_registry

    def create_executor(
        self, step_type: str, engine: "GrimoireEngine"
    ) -> StepExecutorInterface:
        """Create an executor for the given step type."""
        from ..executors.choice_executor import ChoiceExecutor
        from ..executors.conditional_executor import ConditionalExecutor
        from ..executors.dice_executor import DiceExecutor
        from ..executors.flow_executor import FlowExecutor
        from ..executors.llm_executor import LLMExecutor
        from ..executors.name_generation_executor import NameGenerationExecutor
        from ..executors.player_input_executor import PlayerInputExecutor
        from ..executors.table_executor import TableExecutor

        if step_type in ["dice_roll", "dice_sequence"]:
            # Inject action executor dependency if registry is available
            if self.executor_registry:
                action_executor = self.executor_registry.create_action_executor()
                return DiceExecutor(action_executor)
            else:
                return DiceExecutor()  # Falls back to internal creation
        elif step_type == "player_choice":
            # Inject action executor dependency if registry is available
            if self.executor_registry:
                action_executor = self.executor_registry.create_action_executor()
                return ChoiceExecutor(engine, action_executor)
            else:
                return ChoiceExecutor(engine)  # Falls back to internal creation
        elif step_type == "player_input":
            # Inject action executor dependency if registry is available
            if self.executor_registry:
                action_executor = self.executor_registry.create_action_executor()
                return PlayerInputExecutor(action_executor)
            else:
                return PlayerInputExecutor()  # Falls back to internal creation
        elif step_type == "table_roll":
            # Inject action executor dependency if registry is available
            if self.executor_registry:
                action_executor = self.executor_registry.create_action_executor()
                return TableExecutor(action_executor)
            else:
                return TableExecutor()  # Falls back to internal creation
        elif step_type == "llm_generation":
            # Inject action executor dependency if registry is available
            if self.executor_registry:
                action_executor = self.executor_registry.create_action_executor()
                return LLMExecutor(action_executor)
            else:
                return LLMExecutor()  # Falls back to internal creation
        elif step_type == "conditional":
            # Inject action executor dependency if registry is available
            if self.executor_registry:
                action_executor = self.executor_registry.create_action_executor()
                return ConditionalExecutor(action_executor)
            else:
                return ConditionalExecutor()  # Falls back to internal creation
        elif step_type == "name_generation":
            # Inject action executor dependency if registry is available
            if self.executor_registry:
                action_executor = self.executor_registry.create_action_executor()
                return NameGenerationExecutor(action_executor)
            else:
                return NameGenerationExecutor()  # Falls back to internal creation
        elif step_type in ["completion", "flow_call"]:
            # Inject action executor dependency if registry is available
            if self.executor_registry:
                action_executor = self.executor_registry.create_action_executor()
                return FlowExecutor(action_executor)
            else:
                return FlowExecutor()  # Falls back to internal creation
        else:
            raise ValueError(f"Unsupported step type: {step_type}")

    def get_supported_step_types(self) -> list[str]:
        """Get the list of step types this factory supports."""
        return [
            "dice_roll",
            "dice_sequence",
            "player_choice",
            "player_input",
            "table_roll",
            "llm_generation",
            "name_generation",
            "completion",
            "flow_call",
            "conditional",
        ]


# Import here to avoid circular imports
if TYPE_CHECKING:
    from ..core.engine import GrimoireEngine
    from .executor_factories import ExecutorRegistry
