"""Comprehensive factory system for creating all types of executors."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from .executor_factory import StepExecutorInterface

if TYPE_CHECKING:
    from ..core.engine import GrimoireEngine
    from ..models.context_data import ExecutionContext
    from ..models.system import System


class ActionExecutorFactory(ABC):
    """Abstract factory for creating action executors."""

    @abstractmethod
    def create_action_executor(self) -> "ActionExecutor":
        """Create an action executor instance."""


class DefaultActionExecutorFactory(ActionExecutorFactory):
    """Default factory for creating action executors."""

    def __init__(self, table_executor_factory: Optional["TableExecutorFactory"] = None):
        """Initialize with optional table executor factory for dependency injection."""
        self.table_executor_factory = table_executor_factory

    def create_action_executor(self) -> "ActionExecutor":
        """Create an action executor instance."""
        from .action_executor import ActionExecutor
        return ActionExecutor(table_executor_factory=self.table_executor_factory)


class TableExecutorFactory(ABC):
    """Abstract factory for creating table executors."""

    @abstractmethod
    def create_table_executor(self) -> "TableExecutor":
        """Create a table executor instance."""


class DefaultTableExecutorFactory(TableExecutorFactory):
    """Default factory for creating table executors."""

    def create_table_executor(self) -> "TableExecutor":
        """Create a table executor instance."""
        from .table_executor import TableExecutor
        return TableExecutor()


class ExecutorRegistry:
    """Central registry for all executor factories, implementing the Abstract Factory pattern."""

    def __init__(
        self,
        step_executor_factory: Optional["StepExecutorFactory"] = None,
        action_executor_factory: Optional[ActionExecutorFactory] = None,
        table_executor_factory: Optional[TableExecutorFactory] = None,
    ):
        """Initialize the executor registry with factories."""
        # Import here to avoid circular imports
        from .executor_factory import DefaultExecutorFactory
        
        self.table_executor_factory = table_executor_factory or DefaultTableExecutorFactory()
        self.action_executor_factory = action_executor_factory or DefaultActionExecutorFactory(self.table_executor_factory)
        
        # Initialize the step executor factory with self-reference for dependency injection
        if step_executor_factory is None:
            step_executor_factory = DefaultExecutorFactory(executor_registry=self)
        self.step_executor_factory = step_executor_factory

    def create_step_executor(self, step_type: str, engine: "GrimoireEngine") -> StepExecutorInterface:
        """Create a step executor for the given type."""
        return self.step_executor_factory.create_executor(step_type, engine)

    def create_action_executor(self) -> "ActionExecutor":
        """Create an action executor."""
        return self.action_executor_factory.create_action_executor()

    def create_table_executor(self) -> "TableExecutor":
        """Create a table executor."""
        return self.table_executor_factory.create_table_executor()

    def get_supported_step_types(self) -> list[str]:
        """Get all supported step types."""
        return self.step_executor_factory.get_supported_step_types()

    def set_step_executor_factory(self, factory: "StepExecutorFactory") -> None:
        """Set a custom step executor factory."""
        self.step_executor_factory = factory

    def set_action_executor_factory(self, factory: ActionExecutorFactory) -> None:
        """Set a custom action executor factory."""
        self.action_executor_factory = factory

    def set_table_executor_factory(self, factory: TableExecutorFactory) -> None:
        """Set a custom table executor factory."""
        self.table_executor_factory = factory


# Import types for the protocol (delayed to avoid circular imports)
if TYPE_CHECKING:
    from .action_executor import ActionExecutor
    from .executor_factory import ExecutorFactory as StepExecutorFactory
    from .table_executor import TableExecutor
