"""UI Service layer interfaces for clean UI/Engine separation."""

from . import event_signals
from .commands import (
    CancelExecutionCommand,
    Command,
    ContinueExecutionCommand,
    GetExecutionStatusCommand,
    ListFlowsCommand,
    LoadSystemCommand,
    MakeChoiceCommand,
    ProvideInputCommand,
    StartFlowCommand,
)
from .interfaces import (
    Choice,
    DisplayMessage,
    ExecutionProgress,
    ExecutionSession,
    ExecutionStatus,
    FlowInfo,
    InputType,
    StepInfo,
    SystemInfo,
    UIServiceInterface,
)
from .ui_service_impl import GrimoireUIService

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
    # Blinker event signals
    "event_signals",
    # Implementation
    "GrimoireUIService",
]
