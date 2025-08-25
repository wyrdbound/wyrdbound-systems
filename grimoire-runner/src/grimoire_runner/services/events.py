"""Event definitions for UI/Engine communication."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .interfaces import Choice, StepInfo


@dataclass
class ExecutionEvent:
    """Base class for all execution events."""
    session_id: str
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class StepStartedEvent(ExecutionEvent):
    """Event published when a step starts executing."""
    
    def __init__(self, session_id: str, step_info: StepInfo, timestamp: Optional[datetime] = None):
        super().__init__(session_id, timestamp)
        self.step_info = step_info


class StepCompletedEvent(ExecutionEvent):
    """Event published when a step completes successfully."""
    
    def __init__(self, session_id: str, step_info: StepInfo, step_data: Optional[Dict[str, Any]] = None, 
                 next_step_id: Optional[str] = None, timestamp: Optional[datetime] = None):
        super().__init__(session_id, timestamp)
        self.step_info = step_info
        self.step_data = step_data
        self.next_step_id = next_step_id


class InputRequiredEvent(ExecutionEvent):
    """Event published when user input is required."""
    
    def __init__(self, session_id: str, step_info: StepInfo, prompt: str, 
                 input_type: str = "text", validation_rules: Optional[Dict[str, Any]] = None,
                 timestamp: Optional[datetime] = None):
        super().__init__(session_id, timestamp)
        self.step_info = step_info
        self.prompt = prompt
        self.input_type = input_type
        self.validation_rules = validation_rules


class ChoiceRequiredEvent(ExecutionEvent):
    """Event published when user choice is required."""
    
    def __init__(self, session_id: str, step_info: StepInfo, prompt: str, choices: List[Choice],
                 timestamp: Optional[datetime] = None):
        super().__init__(session_id, timestamp)
        self.step_info = step_info
        self.prompt = prompt
        self.choices = choices


class FlowCompletedEvent(ExecutionEvent):
    """Event published when a flow completes successfully."""
    
    def __init__(self, session_id: str, flow_id: str, outputs: Dict[str, Any], 
                 variables: Dict[str, Any], step_count: int, timestamp: Optional[datetime] = None):
        super().__init__(session_id, timestamp)
        self.flow_id = flow_id
        self.outputs = outputs
        self.variables = variables
        self.step_count = step_count


class ErrorOccurredEvent(ExecutionEvent):
    """Event published when an error occurs during execution."""
    
    def __init__(self, session_id: str, error_message: str, step_id: Optional[str] = None,
                 error_type: str = "execution_error", timestamp: Optional[datetime] = None):
        super().__init__(session_id, timestamp)
        self.error_message = error_message
        self.step_id = step_id
        self.error_type = error_type

    
class FlowStartedEvent(ExecutionEvent):
    """Event published when a flow starts executing."""
    
    def __init__(self, session_id: str, flow_id: str, system_id: str, inputs: Dict[str, Any],
                 timestamp: Optional[datetime] = None):
        super().__init__(session_id, timestamp)
        self.flow_id = flow_id
        self.system_id = system_id
        self.inputs = inputs


class FlowCancelledEvent(ExecutionEvent):
    """Event published when a flow execution is cancelled."""
    
    def __init__(self, session_id: str, flow_id: str, reason: str = "user_cancelled",
                 timestamp: Optional[datetime] = None):
        super().__init__(session_id, timestamp)
        self.flow_id = flow_id
        self.reason = reason


class SessionCreatedEvent(ExecutionEvent):
    """Event published when a new execution session is created."""
    
    def __init__(self, session_id: str, system_id: str, flow_id: str,
                 timestamp: Optional[datetime] = None):
        super().__init__(session_id, timestamp)
        self.system_id = system_id
        self.flow_id = flow_id


class SystemLoadedEvent(ExecutionEvent):
    """Event published when a system is successfully loaded."""
    
    def __init__(self, system_id: str, system_name: str, system_path: str, 
                 flow_count: int, model_count: int, timestamp: Optional[datetime] = None):
        # SystemLoadedEvent doesn't have a session_id since it's not session-specific
        super().__init__(session_id="system", timestamp=timestamp)
        self.system_id = system_id
        self.system_name = system_name
        self.system_path = system_path
        self.flow_count = flow_count
        self.model_count = model_count
# Event type registry for easier event handling
EVENT_TYPES = {
    "step_started": StepStartedEvent,
    "step_completed": StepCompletedEvent,
    "input_required": InputRequiredEvent,
    "choice_required": ChoiceRequiredEvent,
    "flow_completed": FlowCompletedEvent,
    "flow_started": FlowStartedEvent,
    "flow_cancelled": FlowCancelledEvent,
    "error_occurred": ErrorOccurredEvent,
    "session_created": SessionCreatedEvent,
    "system_loaded": SystemLoadedEvent,
}
