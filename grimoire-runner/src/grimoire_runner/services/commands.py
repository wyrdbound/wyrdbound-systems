"""Command definitions for UI/Engine communication."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class Command:
    """Base class for all commands sent from UI to engine."""
    session_id: Optional[str] = None


class LoadSystemCommand(Command):
    """Command to load a GRIMOIRE system."""
    
    def __init__(self, system_path: Path):
        super().__init__(session_id=None)  # System loading is not session-specific
        self.system_path = system_path


class StartFlowCommand(Command):
    """Command to start executing a flow."""
    
    def __init__(self, session_id: str, system_id: str, flow_id: str, inputs: Dict[str, Any]):
        super().__init__(session_id)
        self.system_id = system_id
        self.flow_id = flow_id
        self.inputs = inputs


class ProvideInputCommand(Command):
    """Command to provide user input."""
    
    def __init__(self, session_id: str, input_data: Any):
        super().__init__(session_id)
        self.input_data = input_data


class MakeChoiceCommand(Command):
    """Command to make a user choice."""
    
    def __init__(self, session_id: str, choice_id: str):
        super().__init__(session_id)
        self.choice_id = choice_id


class CancelExecutionCommand(Command):
    """Command to cancel execution."""
    
    def __init__(self, session_id: str, reason: str = "user_cancelled"):
        super().__init__(session_id)
        self.reason = reason


class GetExecutionStatusCommand(Command):
    """Command to get the status of an execution session."""
    
    def __init__(self, session_id: str):
        super().__init__(session_id)


class ListFlowsCommand(Command):
    """Command to list flows in a system."""
    
    def __init__(self, system_id: str):
        super().__init__(session_id=None)  # Flow listing is not session-specific
        self.system_id = system_id


class ContinueExecutionCommand(Command):
    """Command to continue execution when no user input is required."""
    
    def __init__(self, session_id: str):
        super().__init__(session_id)


# Command type registry for easier command handling
COMMAND_TYPES = {
    "load_system": LoadSystemCommand,
    "start_flow": StartFlowCommand,
    "provide_input": ProvideInputCommand,
    "make_choice": MakeChoiceCommand,
    "cancel_execution": CancelExecutionCommand,
    "get_execution_status": GetExecutionStatusCommand,
    "list_flows": ListFlowsCommand,
    "continue_execution": ContinueExecutionCommand,
}
