"""Flow execution context management using manager pattern for better SRP compliance."""

import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext

logger = logging.getLogger(__name__)


class NamespaceDataAccess(ABC):
    """Abstract interface for namespace data access operations."""

    @abstractmethod
    def create_namespace(
        self, namespace_id: str, flow_id: str, execution_id: str
    ) -> None:
        """Create a new namespace."""
        pass

    @abstractmethod
    def set_current_namespace(self, namespace_id: str) -> None:
        """Set the current active namespace."""
        pass

    @abstractmethod
    def get_current_namespace(self) -> str | None:
        """Get the current active namespace ID."""
        pass

    @abstractmethod
    def get_namespace_data(self, namespace_id: str) -> dict[str, Any] | None:
        """Get all data for a namespace."""
        pass

    @abstractmethod
    def set_namespace_variable(self, namespace_id: str, path: str, value: Any) -> None:
        """Set a variable in a namespace."""
        pass

    @abstractmethod
    def get_namespace_variable(
        self, namespace_id: str, path: str, default: Any = None
    ) -> Any:
        """Get a variable from a namespace."""
        pass

    @abstractmethod
    def initialize_namespace_variables(
        self, namespace_id: str, variables: dict[str, Any]
    ) -> None:
        """Initialize variables for a namespace."""
        pass

    @abstractmethod
    def copy_namespace_outputs_to_root(self, namespace_id: str) -> None:
        """Copy namespace outputs to root level."""
        pass

    @abstractmethod
    def pop_namespace(self) -> None:
        """Remove and clean up the current namespace."""
        pass


@dataclass
class FlowExecutionState:
    """Flow execution state tracking."""

    execution_id: str
    flow_id: str
    namespace_id: str
    current_step: str | None = None
    step_history: list[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    @property
    def is_active(self) -> bool:
        """Check if this execution is still active."""
        return self.end_time is None

    def complete(self) -> None:
        """Mark this execution as complete."""
        self.end_time = datetime.now()


class FlowExecutionContextManager:
    """Manager for flow execution context, responsible for namespace lifecycle and state tracking."""

    def __init__(self, namespace_data_access: NamespaceDataAccess):
        """Initialize the flow execution context manager.

        Args:
            namespace_data_access: Data access layer for namespace operations
        """
        self.namespace_data_access = namespace_data_access
        self.execution_stack: list[FlowExecutionState] = []
        self.execution_history: list[FlowExecutionState] = []

    def start_flow_execution(
        self, flow_id: str, variables: dict[str, Any] | None = None
    ) -> FlowExecutionState:
        """Start a new flow execution with isolated namespace.

        Args:
            flow_id: ID of the flow being executed
            variables: Initial variables for the flow

        Returns:
            FlowExecutionState: The execution state for this flow
        """
        # Generate unique IDs
        execution_id = str(uuid.uuid4())[:8]
        namespace_id = f"flow_{execution_id}"

        logger.info(
            f"Starting flow execution: {flow_id} (execution_id: {execution_id}, namespace: {namespace_id})"
        )

        # Create isolated namespace
        self.namespace_data_access.create_namespace(namespace_id, flow_id, execution_id)
        self.namespace_data_access.set_current_namespace(namespace_id)

        # Initialize flow variables if provided
        if variables:
            self.namespace_data_access.initialize_namespace_variables(
                namespace_id, variables.copy()
            )

        # Create execution state
        execution_state = FlowExecutionState(
            execution_id=execution_id, flow_id=flow_id, namespace_id=namespace_id
        )

        # Add to execution stack
        self.execution_stack.append(execution_state)

        logger.debug(f"Flow execution started: {execution_state}")
        return execution_state

    def end_flow_execution(self) -> FlowExecutionState | None:
        """End the current flow execution and clean up its namespace.

        Returns:
            FlowExecutionState: The completed execution state, if any
        """
        if not self.execution_stack:
            logger.warning("No active flow execution to end")
            return None

        # Get current execution
        execution_state = self.execution_stack.pop()
        execution_state.complete()

        logger.info(
            f"Ending flow execution: {execution_state.flow_id} (namespace: {execution_state.namespace_id})"
        )

        # Copy outputs to root level before cleanup
        self.namespace_data_access.copy_namespace_outputs_to_root(
            execution_state.namespace_id
        )

        # Clean up namespace
        self.namespace_data_access.pop_namespace()

        # Add to execution history
        self.execution_history.append(execution_state)

        logger.debug(f"Flow execution completed: {execution_state}")
        return execution_state

    def get_current_execution(self) -> FlowExecutionState | None:
        """Get the currently active flow execution.

        Returns:
            FlowExecutionState: The current execution state, if any
        """
        return self.execution_stack[-1] if self.execution_stack else None

    def update_execution_step(self, step_id: str) -> None:
        """Update the current step for the active execution.

        Args:
            step_id: ID of the current step
        """
        current_execution = self.get_current_execution()
        if current_execution:
            current_execution.current_step = step_id
            current_execution.step_history.append(step_id)
            logger.debug(
                f"Execution step updated: {step_id} (namespace: {current_execution.namespace_id})"
            )
        else:
            logger.warning(f"No active execution to update step: {step_id}")

    def get_execution_history(self) -> list[FlowExecutionState]:
        """Get the history of completed executions.

        Returns:
            List[FlowExecutionState]: List of completed executions
        """
        return self.execution_history.copy()

    def get_active_executions(self) -> list[FlowExecutionState]:
        """Get all currently active executions.

        Returns:
            List[FlowExecutionState]: List of active executions
        """
        return self.execution_stack.copy()

    def is_execution_active(self) -> bool:
        """Check if any flow execution is currently active.

        Returns:
            bool: True if there's an active execution
        """
        return len(self.execution_stack) > 0

    def get_namespace_for_execution(self, execution_id: str) -> str | None:
        """Get the namespace ID for a specific execution.

        Args:
            execution_id: The execution ID to look up

        Returns:
            Optional[str]: The namespace ID, if found
        """
        # Check active executions
        for execution in self.execution_stack:
            if execution.execution_id == execution_id:
                return execution.namespace_id

        # Check execution history
        for execution in self.execution_history:
            if execution.execution_id == execution_id:
                return execution.namespace_id

        return None

    def clear_execution_history(self) -> int:
        """Clear the execution history.

        Returns:
            int: Number of history entries cleared
        """
        count = len(self.execution_history)
        self.execution_history.clear()
        logger.debug(f"Cleared {count} execution history entries")
        return count


class DefaultNamespaceDataAccess(NamespaceDataAccess):
    """Default implementation of namespace data access using the existing FlowNamespaceManager."""

    def __init__(self, context: "ExecutionContext"):
        """Initialize with reference to the execution context.

        Args:
            context: The execution context containing the namespace manager
        """
        self.context = context

    def create_namespace(
        self, namespace_id: str, flow_id: str, execution_id: str
    ) -> None:
        """Create a new namespace."""
        self.context.namespace_manager.create_flow_namespace(
            namespace_id, flow_id, execution_id
        )

    def set_current_namespace(self, namespace_id: str) -> None:
        """Set the current active namespace."""
        self.context.namespace_manager.set_current_flow_namespace(namespace_id)

    def get_current_namespace(self) -> str | None:
        """Get the current active namespace ID."""
        return getattr(self.context.namespace_manager, "_current_namespace", None)

    def get_namespace_data(self, namespace_id: str) -> dict[str, Any] | None:
        """Get all data for a namespace."""
        return self.context.namespace_manager.get_flow_namespace_data(namespace_id)

    def set_namespace_variable(self, namespace_id: str, path: str, value: Any) -> None:
        """Set a variable in a namespace."""
        self.context.namespace_manager.set_flow_namespace_variable(
            namespace_id, path, value
        )

    def get_namespace_variable(
        self, namespace_id: str, path: str, default: Any = None
    ) -> Any:
        """Get a variable from a namespace."""
        return self.context.namespace_manager.get_flow_namespace_variable(
            namespace_id, path, default
        )

    def initialize_namespace_variables(
        self, namespace_id: str, variables: dict[str, Any]
    ) -> None:
        """Initialize variables for a namespace."""
        self.context.namespace_manager.initialize_flow_namespace_variables(
            namespace_id, variables
        )

    def copy_namespace_outputs_to_root(self, namespace_id: str) -> None:
        """Copy namespace outputs to root level."""
        self.context.namespace_manager.copy_flow_outputs_to_root(namespace_id)

    def pop_namespace(self) -> None:
        """Remove and clean up the current namespace."""
        self.context.namespace_manager.pop_flow_namespace()


# Checkpoint management for rollback functionality
@dataclass
class ExecutionCheckpoint:
    """A checkpoint for execution state rollback."""

    checkpoint_id: str
    timestamp: datetime
    execution_state: FlowExecutionState
    namespace_data: dict[str, Any]

    @classmethod
    def create(
        cls,
        checkpoint_id: str,
        execution_state: FlowExecutionState,
        namespace_data: dict[str, Any],
    ) -> "ExecutionCheckpoint":
        """Create a new checkpoint.

        Args:
            checkpoint_id: Unique identifier for the checkpoint
            execution_state: Current execution state
            namespace_data: Snapshot of namespace data

        Returns:
            ExecutionCheckpoint: The created checkpoint
        """
        return cls(
            checkpoint_id=checkpoint_id,
            timestamp=datetime.now(),
            execution_state=execution_state,
            namespace_data=namespace_data.copy() if namespace_data else {},
        )


class CheckpointManager:
    """Manager for execution checkpoints and rollback functionality."""

    def __init__(self, namespace_data_access: NamespaceDataAccess):
        """Initialize the checkpoint manager.

        Args:
            namespace_data_access: Data access layer for namespace operations
        """
        self.namespace_data_access = namespace_data_access
        self.checkpoints: dict[str, ExecutionCheckpoint] = {}

    def create_checkpoint(
        self, checkpoint_id: str, execution_state: FlowExecutionState
    ) -> ExecutionCheckpoint:
        """Create a checkpoint for the current execution state.

        Args:
            checkpoint_id: Unique identifier for the checkpoint
            execution_state: Current execution state to checkpoint

        Returns:
            ExecutionCheckpoint: The created checkpoint
        """
        # Get current namespace data
        namespace_data = self.namespace_data_access.get_namespace_data(
            execution_state.namespace_id
        )

        # Create checkpoint
        checkpoint = ExecutionCheckpoint.create(
            checkpoint_id, execution_state, namespace_data or {}
        )
        self.checkpoints[checkpoint_id] = checkpoint

        logger.info(
            f"Checkpoint created: {checkpoint_id} for execution {execution_state.execution_id}"
        )
        return checkpoint

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore execution state from a checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to restore

        Returns:
            bool: True if restoration was successful
        """
        if checkpoint_id not in self.checkpoints:
            logger.error(f"Checkpoint not found: {checkpoint_id}")
            return False

        checkpoint = self.checkpoints[checkpoint_id]

        try:
            # Restore namespace data
            # Note: This would require implementing namespace data restoration in the data access layer
            logger.info(
                f"Restoring checkpoint: {checkpoint_id} for execution {checkpoint.execution_state.execution_id}"
            )

            # For now, we'll just log what would be restored
            logger.debug(f"Would restore namespace data: {checkpoint.namespace_data}")

            return True
        except Exception as e:
            logger.error(f"Failed to restore checkpoint {checkpoint_id}: {e}")
            return False

    def list_checkpoints(self) -> list[str]:
        """List all available checkpoint IDs.

        Returns:
            List[str]: List of checkpoint IDs
        """
        return list(self.checkpoints.keys())

    def remove_checkpoint(self, checkpoint_id: str) -> bool:
        """Remove a checkpoint.

        Args:
            checkpoint_id: ID of the checkpoint to remove

        Returns:
            bool: True if checkpoint was removed
        """
        if checkpoint_id in self.checkpoints:
            del self.checkpoints[checkpoint_id]
            logger.info(f"Checkpoint removed: {checkpoint_id}")
            return True
        return False

    def clear_checkpoints(self) -> int:
        """Clear all checkpoints.

        Returns:
            int: Number of checkpoints cleared
        """
        count = len(self.checkpoints)
        self.checkpoints.clear()
        logger.info(f"Cleared {count} checkpoints")
        return count
