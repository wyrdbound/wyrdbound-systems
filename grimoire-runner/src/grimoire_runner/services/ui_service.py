"""UI Service layer interfaces for clean UI/Engine separation."""

from .interfaces import (
    UIServiceInterface,
    SystemInfo,
    FlowInfo,
    ExecutionSession,
    ExecutionStatus,
    ExecutionProgress,
    DisplayMessage,
    StepInfo,
    Choice,
    InputType,
)
from .events import (
    ExecutionEvent,
    StepStartedEvent,
    StepCompletedEvent,
    InputRequiredEvent,
    ChoiceRequiredEvent,
    FlowCompletedEvent,
    ErrorOccurredEvent,
    FlowStartedEvent,
    FlowCancelledEvent,
    SessionCreatedEvent,
    SystemLoadedEvent,
)
from .commands import (
    Command,
    LoadSystemCommand,
    StartFlowCommand,
    ProvideInputCommand,
    MakeChoiceCommand,
    CancelExecutionCommand,
    GetExecutionStatusCommand,
    ListFlowsCommand,
    ContinueExecutionCommand,
)

__all__ = [
    # Interfaces
    "UIServiceInterface",
    "SystemInfo",
    "FlowInfo", 
    "ExecutionSession",
    "ExecutionStatus",
    "ExecutionProgress",
    "DisplayMessage",
    "StepInfo",
    "Choice",
    "InputType",
    # Events
    "ExecutionEvent",
    "StepStartedEvent",
    "StepCompletedEvent",
    "InputRequiredEvent",
    "ChoiceRequiredEvent",
    "FlowCompletedEvent",
    "ErrorOccurredEvent",
    "FlowStartedEvent",
    "FlowCancelledEvent",
    "SessionCreatedEvent",
    "SystemLoadedEvent",
    # Commands
    "Command",
    "LoadSystemCommand",
    "StartFlowCommand",
    "ProvideInputCommand",
    "MakeChoiceCommand",
    "CancelExecutionCommand",
    "GetExecutionStatusCommand",
    "ListFlowsCommand",
    "ContinueExecutionCommand",
]
