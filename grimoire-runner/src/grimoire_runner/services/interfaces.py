"""Service interface definitions for UI/Engine separation."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class InputType(Enum):
    """Types of user input."""

    TEXT = "text"
    NUMBER = "number"
    CHOICE = "choice"
    BOOLEAN = "boolean"


@dataclass
class SystemInfo:
    """Information about a loaded system."""

    id: str
    name: str
    description: str | None = None
    version: str | None = None
    flow_count: int = 0
    model_count: int = 0
    compendium_count: int = 0
    table_count: int = 0


@dataclass
class FlowInfo:
    """Information about a flow."""

    id: str
    name: str
    description: str | None = None
    step_count: int = 0
    requires_inputs: bool = False
    produces_outputs: bool = False


@dataclass
class Choice:
    """A choice option for user selection."""

    id: str
    label: str
    description: str | None = None
    next_step: str | None = None


@dataclass
class StepInfo:
    """Information about a step being executed."""

    id: str
    name: str | None = None
    type: str = "unknown"
    description: str | None = None
    prompt: str | None = None
    step_number: int | None = None  # Execution order number (1-based)


@dataclass
class DisplayMessage:
    """A message to display to the user."""

    level: str  # "info", "warning", "error", "success"
    message: str
    timestamp: str | None = None


@dataclass
class ExecutionProgress:
    """Progress information for flow execution."""

    current_step: str
    step_number: int
    total_steps: int | None = None
    completed_steps: list[str] = field(default_factory=list)

    @property
    def progress_percentage(self) -> float | None:
        """Calculate progress as percentage if total steps known."""
        if self.total_steps and self.total_steps > 0:
            return (self.step_number / self.total_steps) * 100
        return None


class ExecutionStatus(Enum):
    """Status of flow execution."""

    STARTING = "starting"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    WAITING_FOR_CHOICE = "waiting_for_choice"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionSession:
    """Represents an active flow execution session."""

    session_id: str
    system_id: str
    flow_id: str
    status: ExecutionStatus
    current_step: StepInfo | None = None
    progress: ExecutionProgress | None = None

    # Input/Choice requirements
    requires_input: bool = False
    input_prompt: str | None = None
    input_type: InputType = InputType.TEXT

    requires_choice: bool = False
    choice_prompt: str | None = None
    choices: list[Choice] = field(default_factory=list)

    # Results and messages
    messages: list[DisplayMessage] = field(default_factory=list)
    outputs: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @classmethod
    def create(cls, system_id: str, flow_id: str) -> "ExecutionSession":
        """Create a new execution session."""
        return cls(
            session_id=str(uuid.uuid4()),
            system_id=system_id,
            flow_id=flow_id,
            status=ExecutionStatus.STARTING,
        )

    @property
    def is_complete(self) -> bool:
        """Check if execution is complete (success or failure)."""
        return self.status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        ]

    @property
    def needs_user_action(self) -> bool:
        """Check if session is waiting for user action."""
        return self.status in [
            ExecutionStatus.WAITING_FOR_INPUT,
            ExecutionStatus.WAITING_FOR_CHOICE,
        ]


class UIServiceInterface(ABC):
    """Abstract interface between UI and engine operations."""

    @abstractmethod
    def load_system(self, system_path: Path) -> SystemInfo:
        """Load a GRIMOIRE system and return system information."""
        pass

    @abstractmethod
    def list_flows(self, system_id: str) -> list[FlowInfo]:
        """List all flows available in a system."""
        pass

    @abstractmethod
    def start_flow_execution(
        self, system_id: str, flow_id: str, inputs: dict[str, Any] | None = None
    ) -> ExecutionSession:
        """Start executing a flow and return the session."""
        pass

    @abstractmethod
    def get_execution_status(self, session_id: str) -> ExecutionSession:
        """Get the current status of an execution session."""
        pass

    @abstractmethod
    def provide_user_input(self, session_id: str, input_data: Any) -> ExecutionSession:
        """Provide user input to continue execution."""
        pass

    @abstractmethod
    def make_choice(self, session_id: str, choice_id: str) -> ExecutionSession:
        """Make a choice to continue execution."""
        pass

    @abstractmethod
    def make_multiple_choices(
        self, session_id: str, choice_ids: list[str]
    ) -> ExecutionSession:
        """Make multiple choices to continue execution."""
        pass

    @abstractmethod
    def cancel_execution(self, session_id: str) -> None:
        """Cancel an active execution session."""
        pass

    @abstractmethod
    def subscribe_to_events(self, handler: callable) -> None:
        """Subscribe to execution events."""
        pass

    @abstractmethod
    def unsubscribe_from_events(self, handler: callable) -> None:
        """Unsubscribe from execution events."""
        pass
