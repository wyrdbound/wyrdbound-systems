"""Concrete implementation of UIServiceInterface wrapping GrimoireEngine."""

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from threading import Thread, Lock
import time

from ..core.engine import GrimoireEngine
from ..models.system import System
from ..models.flow import FlowDefinition
from .ui_service import (
    UIServiceInterface,
    SystemInfo,
    FlowInfo,
    ExecutionSession,
    ExecutionStatus,
    ExecutionProgress,
    StepInfo,
    Choice,
    InputType,
    # Events
    SystemLoadedEvent,
    SessionCreatedEvent,
    FlowStartedEvent,
    StepStartedEvent,
    StepCompletedEvent,
    InputRequiredEvent,
    ChoiceRequiredEvent,
    FlowCompletedEvent,
    ErrorOccurredEvent,
    FlowCancelledEvent,
)
from ..utils.debug import debug_print


class GrimoireUIService(UIServiceInterface):
    """Concrete implementation of UI service interface."""
    
    def __init__(self):
        self.engine = GrimoireEngine()
        self.loaded_systems: Dict[str, System] = {}
        self.active_sessions: Dict[str, ExecutionSession] = {}
        self.event_subscribers: List[Callable] = []
        self._session_lock = Lock()
        
        debug_print("[UI_SERVICE] GrimoireUIService initialized")
    
    def load_system(self, system_path: Path) -> SystemInfo:
        """Load a GRIMOIRE system and return system information."""
        debug_print(f"[UI_SERVICE] Loading system from {system_path}")
        
        try:
            system = self.engine.load_system(system_path)
            self.loaded_systems[system.id] = system
            
            system_info = SystemInfo(
                id=system.id,
                name=system.name,
                description=system.description,
                version=system.version,
                flow_count=len(system.flows),
                model_count=len(system.models),
                compendium_count=len(system.compendiums),
                table_count=len(system.tables)
            )
            
            # Publish system loaded event
            event = SystemLoadedEvent(
                system_id=system.id,
                system_name=system.name,
                system_path=str(system_path),
                flow_count=len(system.flows),
                model_count=len(system.models)
            )
            self._publish_event(event)
            
            debug_print(f"[UI_SERVICE] System loaded: {system.name} ({system.id})")
            return system_info
            
        except Exception as e:
            debug_print(f"[UI_SERVICE] Error loading system: {e}")
            raise
    
    def list_flows(self, system_id: str) -> List[FlowInfo]:
        """List all flows available in a system."""
        debug_print(f"[UI_SERVICE] Listing flows for system {system_id}")
        
        if system_id not in self.loaded_systems:
            raise ValueError(f"System '{system_id}' not loaded")
        
        system = self.loaded_systems[system_id]
        flows = []
        
        for flow_id, flow in system.flows.items():
            flow_info = FlowInfo(
                id=flow_id,
                name=flow.name,
                description=flow.description,
                step_count=len(flow.steps),
                requires_inputs=len(flow.inputs) > 0 if flow.inputs else False,
                produces_outputs=len(flow.outputs) > 0 if flow.outputs else False
            )
            flows.append(flow_info)
        
        debug_print(f"[UI_SERVICE] Found {len(flows)} flows in system {system_id}")
        return flows
    
    def start_flow_execution(
        self, 
        system_id: str, 
        flow_id: str, 
        inputs: Optional[Dict[str, Any]] = None
    ) -> ExecutionSession:
        """Start executing a flow and return the session."""
        debug_print(f"[UI_SERVICE] Starting flow execution: {system_id}.{flow_id}")
        
        if system_id not in self.loaded_systems:
            raise ValueError(f"System '{system_id}' not loaded")
        
        system = self.loaded_systems[system_id]
        if flow_id not in system.flows:
            raise ValueError(f"Flow '{flow_id}' not found in system '{system_id}'")
        
        # Create execution session
        session = ExecutionSession.create(system_id, flow_id)
        session.status = ExecutionStatus.STARTING
        
        with self._session_lock:
            self.active_sessions[session.session_id] = session
        
        # Publish session created event
        event = SessionCreatedEvent(
            session_id=session.session_id,
            system_id=system_id,
            flow_id=flow_id
        )
        self._publish_event(event)
        
        # Start flow execution in background
        inputs = inputs or {}
        session.variables.update(inputs)
        
        # Start execution thread
        execution_thread = Thread(
            target=self._execute_flow_async,
            args=(session, system, flow_id, inputs),
            daemon=True
        )
        execution_thread.start()
        
        debug_print(f"[UI_SERVICE] Started execution session {session.session_id}")
        return session
    
    def get_execution_status(self, session_id: str) -> ExecutionSession:
        """Get the current status of an execution session."""
        debug_print(f"[UI_SERVICE] Getting status for session {session_id}")
        
        with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session '{session_id}' not found")
            return self.active_sessions[session_id]
    
    def provide_user_input(
        self, 
        session_id: str, 
        input_data: Any
    ) -> ExecutionSession:
        """Provide user input to continue execution."""
        debug_print(f"[UI_SERVICE] Providing input for session {session_id}: {input_data}")
        
        with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session '{session_id}' not found")
            
            session = self.active_sessions[session_id]
            if not session.requires_input:
                raise ValueError(f"Session '{session_id}' is not waiting for input")
            
            # Store the input and mark as no longer requiring input
            session.variables['user_input'] = input_data
            session.requires_input = False
            session.input_prompt = None
            session.status = ExecutionStatus.RUNNING
            
            debug_print(f"[UI_SERVICE] Input provided for session {session_id}")
            return session
    
    def make_choice(
        self, 
        session_id: str, 
        choice_id: str
    ) -> ExecutionSession:
        """Make a choice to continue execution."""
        debug_print(f"[UI_SERVICE] Making choice for session {session_id}: {choice_id}")
        
        with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session '{session_id}' not found")
            
            session = self.active_sessions[session_id]
            if not session.requires_choice:
                raise ValueError(f"Session '{session_id}' is not waiting for a choice")
            
            # Find the selected choice
            selected_choice = None
            for choice in session.choices:
                if choice.id == choice_id:
                    selected_choice = choice
                    break
            
            if not selected_choice:
                raise ValueError(f"Choice '{choice_id}' not found in session '{session_id}'")
            
            # Store the choice and mark as no longer requiring choice
            session.variables['user_choice'] = selected_choice
            session.requires_choice = False
            session.choice_prompt = None
            session.choices = []
            session.status = ExecutionStatus.RUNNING
            
            debug_print(f"[UI_SERVICE] Choice made for session {session_id}: {selected_choice.label}")
            return session
    
    def cancel_execution(self, session_id: str) -> None:
        """Cancel an active execution session."""
        debug_print(f"[UI_SERVICE] Cancelling session {session_id}")
        
        with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session '{session_id}' not found")
            
            session = self.active_sessions[session_id]
            session.status = ExecutionStatus.CANCELLED
            
            # Publish cancellation event
            event = FlowCancelledEvent(
                session_id=session_id,
                flow_id=session.flow_id,
                reason="user_cancelled"
            )
            self._publish_event(event)
            
            debug_print(f"[UI_SERVICE] Session {session_id} cancelled")
    
    def subscribe_to_events(self, handler: Callable) -> None:
        """Subscribe to execution events."""
        debug_print(f"[UI_SERVICE] Adding event subscriber: {handler}")
        self.event_subscribers.append(handler)
    
    def unsubscribe_from_events(self, handler: Callable) -> None:
        """Unsubscribe from execution events."""
        debug_print(f"[UI_SERVICE] Removing event subscriber: {handler}")
        if handler in self.event_subscribers:
            self.event_subscribers.remove(handler)
    
    def _publish_event(self, event) -> None:
        """Publish an event to all subscribers."""
        debug_print(f"[UI_SERVICE] Publishing event: {event.__class__.__name__}")
        for handler in self.event_subscribers:
            try:
                handler(event)
            except Exception as e:
                debug_print(f"[UI_SERVICE] Error in event handler: {e}")
    
    def _execute_flow_async(
        self, 
        session: ExecutionSession, 
        system: System, 
        flow_id: str, 
        inputs: Dict[str, Any]
    ) -> None:
        """Execute a flow asynchronously, updating session state and publishing events."""
        debug_print(f"[UI_SERVICE] Starting async execution for session {session.session_id}")
        
        try:
            session.status = ExecutionStatus.RUNNING
            
            # Publish flow started event
            event = FlowStartedEvent(
                session_id=session.session_id,
                flow_id=flow_id,
                system_id=system.id,
                inputs=inputs
            )
            self._publish_event(event)
            
            # Create execution context
            context = self.engine.create_execution_context(system, **inputs)
            
            # Use step_through_flow for interactive execution
            step_count = 0
            for step_result in self.engine.step_through_flow(flow_id, context, system):
                step_count += 1
                
                # Update session progress
                session.progress = ExecutionProgress(
                    current_step=step_result.step_id,
                    step_number=step_count,
                    completed_steps=context.step_history.copy()
                )
                
                # Get step info
                flow = system.get_flow(flow_id)
                step = flow.get_step(step_result.step_id)
                step_info = StepInfo(
                    id=step.id,
                    name=getattr(step, 'name', None),
                    type=str(step.type.value if hasattr(step.type, 'value') else step.type),
                    description=getattr(step, 'description', None),
                    prompt=getattr(step, 'prompt', None)
                )
                
                # Publish step started event
                event = StepStartedEvent(session.session_id, step_info)
                self._publish_event(event)
                
                if not step_result.success:
                    session.status = ExecutionStatus.FAILED
                    session.error = step_result.error
                    
                    event = ErrorOccurredEvent(
                        session_id=session.session_id,
                        error_message=step_result.error,
                        step_id=step_result.step_id
                    )
                    self._publish_event(event)
                    return
                
                # Handle input/choice requirements
                if step_result.requires_input:
                    session.status = ExecutionStatus.WAITING_FOR_INPUT
                    session.requires_input = True
                    session.input_prompt = step_result.prompt
                    session.current_step = step_info
                    
                    # Determine input type based on step type and data
                    input_type = InputType.TEXT  # Default
                    if hasattr(step_result, 'data') and step_result.data:
                        if 'choices' in step_result.data:
                            session.status = ExecutionStatus.WAITING_FOR_CHOICE
                            session.requires_input = False
                            session.requires_choice = True
                            session.choice_prompt = step_result.prompt
                            
                            # Convert choices from step result
                            choices = []
                            for i, choice_data in enumerate(step_result.data['choices']):
                                if isinstance(choice_data, dict):
                                    choice = Choice(
                                        id=str(i),
                                        label=choice_data.get('label', f'Choice {i+1}'),
                                        description=choice_data.get('description'),
                                        next_step=choice_data.get('next_step')
                                    )
                                else:
                                    choice = Choice(
                                        id=str(i),
                                        label=str(choice_data),
                                        description=None,
                                        next_step=None
                                    )
                                choices.append(choice)
                            
                            session.choices = choices
                            
                            event = ChoiceRequiredEvent(
                                session_id=session.session_id,
                                step_info=step_info,
                                prompt=step_result.prompt or "Make a choice:",
                                choices=choices
                            )
                            self._publish_event(event)
                        else:
                            event = InputRequiredEvent(
                                session_id=session.session_id,
                                step_info=step_info,
                                prompt=step_result.prompt or "Enter input:",
                                input_type=input_type.value
                            )
                            self._publish_event(event)
                    
                    # Wait for user input/choice
                    while session.requires_input or session.requires_choice:
                        if session.status == ExecutionStatus.CANCELLED:
                            return
                        time.sleep(0.1)  # Small delay to prevent busy waiting
                    
                    # Continue with the provided input/choice
                    continue
                
                # Publish step completed event
                event = StepCompletedEvent(
                    session_id=session.session_id,
                    step_info=step_info,
                    step_data=step_result.data,
                    next_step_id=step_result.next_step_id
                )
                self._publish_event(event)
            
            # Flow completed successfully
            session.status = ExecutionStatus.COMPLETED
            session.outputs = context.outputs.copy()
            session.variables.update(context.variables)
            
            event = FlowCompletedEvent(
                session_id=session.session_id,
                flow_id=flow_id,
                outputs=session.outputs,
                variables=session.variables,
                step_count=step_count
            )
            self._publish_event(event)
            
            debug_print(f"[UI_SERVICE] Flow execution completed for session {session.session_id}")
            
        except Exception as e:
            debug_print(f"[UI_SERVICE] Error in flow execution: {e}")
            session.status = ExecutionStatus.FAILED
            session.error = str(e)
            
            event = ErrorOccurredEvent(
                session_id=session.session_id,
                error_message=str(e),
                error_type="execution_error"
            )
            self._publish_event(event)
