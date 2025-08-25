"""Blinker-based event system for UI/Engine communication."""

from blinker import Namespace
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from .interfaces import Choice, StepInfo

# Create a namespace for our signals
ui_signals = Namespace()

# Define signals for each event type
system_loaded = ui_signals.signal('system-loaded')
session_created = ui_signals.signal('session-created')
flow_started = ui_signals.signal('flow-started')
step_started = ui_signals.signal('step-started')
step_completed = ui_signals.signal('step-completed')
input_required = ui_signals.signal('input-required')
choice_required = ui_signals.signal('choice-required')
flow_completed = ui_signals.signal('flow-completed')
error_occurred = ui_signals.signal('error-occurred')
flow_cancelled = ui_signals.signal('flow-cancelled')


@dataclass
class SystemLoadedData:
    """Data for system loaded events."""
    system_id: str
    system_name: str
    system_path: str
    flow_count: int
    model_count: int
    session_id: str = "system"  # SystemLoadedData doesn't have a real session_id
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class SessionCreatedData:
    """Data for session created events."""
    session_id: str
    system_id: str
    flow_id: str
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass 
class FlowStartedData:
    """Data for flow started events."""
    session_id: str
    flow_id: str
    system_id: str
    inputs: Dict[str, Any]
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class StepStartedData:
    """Data for step started events."""
    session_id: str
    step_info: StepInfo
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class StepCompletedData:
    """Data for step completed events."""
    session_id: str
    step_info: StepInfo
    step_data: Optional[Dict[str, Any]] = None
    next_step_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class InputRequiredData:
    """Data for input required events."""
    session_id: str
    step_info: StepInfo
    prompt: str
    input_type: str = "text"
    validation_rules: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ChoiceRequiredData:
    """Data for choice required events."""
    session_id: str
    step_info: StepInfo
    prompt: str
    choices: List[Choice]
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class FlowCompletedData:
    """Data for flow completed events."""
    session_id: str
    flow_id: str
    outputs: Dict[str, Any]
    variables: Dict[str, Any]
    step_count: int
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class ErrorOccurredData:
    """Data for error occurred events."""
    session_id: str
    error_message: str
    step_id: Optional[str] = None
    error_type: str = "execution_error"
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class FlowCancelledData:
    """Data for flow cancelled events."""
    session_id: str
    flow_id: str
    reason: str = "user_cancelled"
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


# Event helper functions for easy publishing
def publish_system_loaded(system_id: str, system_name: str, system_path: str, 
                         flow_count: int, model_count: int) -> None:
    """Publish a system loaded event."""
    data = SystemLoadedData(
        system_id=system_id,
        system_name=system_name,
        system_path=system_path,
        flow_count=flow_count,
        model_count=model_count
    )
    system_loaded.send(data=data)


def publish_session_created(session_id: str, system_id: str, flow_id: str) -> None:
    """Publish a session created event."""
    data = SessionCreatedData(
        session_id=session_id,
        system_id=system_id,
        flow_id=flow_id
    )
    session_created.send(data=data)


def publish_flow_started(session_id: str, flow_id: str, system_id: str, inputs: Dict[str, Any]) -> None:
    """Publish a flow started event."""
    data = FlowStartedData(
        session_id=session_id,
        flow_id=flow_id,
        system_id=system_id,
        inputs=inputs
    )
    flow_started.send(data=data)


def publish_step_started(session_id: str, step_info: StepInfo) -> None:
    """Publish a step started event."""
    data = StepStartedData(
        session_id=session_id,
        step_info=step_info
    )
    step_started.send(data=data)


def publish_step_completed(session_id: str, step_info: StepInfo, step_data: Optional[Dict[str, Any]] = None,
                          next_step_id: Optional[str] = None) -> None:
    """Publish a step completed event."""
    data = StepCompletedData(
        session_id=session_id,
        step_info=step_info,
        step_data=step_data,
        next_step_id=next_step_id
    )
    step_completed.send(data=data)


def publish_input_required(session_id: str, step_info: StepInfo, prompt: str, 
                          input_type: str = "text", validation_rules: Optional[Dict[str, Any]] = None) -> None:
    """Publish an input required event."""
    data = InputRequiredData(
        session_id=session_id,
        step_info=step_info,
        prompt=prompt,
        input_type=input_type,
        validation_rules=validation_rules
    )
    input_required.send(data=data)


def publish_choice_required(session_id: str, step_info: StepInfo, prompt: str, choices: List[Choice]) -> None:
    """Publish a choice required event."""
    data = ChoiceRequiredData(
        session_id=session_id,
        step_info=step_info,
        prompt=prompt,
        choices=choices
    )
    choice_required.send(data=data)


def publish_flow_completed(session_id: str, flow_id: str, outputs: Dict[str, Any], 
                          variables: Dict[str, Any], step_count: int) -> None:
    """Publish a flow completed event."""
    data = FlowCompletedData(
        session_id=session_id,
        flow_id=flow_id,
        outputs=outputs,
        variables=variables,
        step_count=step_count
    )
    flow_completed.send(data=data)


def publish_error_occurred(session_id: str, error_message: str, step_id: Optional[str] = None,
                          error_type: str = "execution_error") -> None:
    """Publish an error occurred event."""
    data = ErrorOccurredData(
        session_id=session_id,
        error_message=error_message,
        step_id=step_id,
        error_type=error_type
    )
    error_occurred.send(data=data)


def publish_flow_cancelled(session_id: str, flow_id: str, reason: str = "user_cancelled") -> None:
    """Publish a flow cancelled event."""
    data = FlowCancelledData(
        session_id=session_id,
        flow_id=flow_id,
        reason=reason
    )
    flow_cancelled.send(data=data)
