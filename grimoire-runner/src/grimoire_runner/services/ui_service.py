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
from . import event_signals
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
