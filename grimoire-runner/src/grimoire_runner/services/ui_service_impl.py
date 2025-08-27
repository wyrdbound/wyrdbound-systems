"""
Clean UI Service Implementation - focusing only on UI concerns.

This implementation removes all flow control logic from the UI service,
letting the engine handle all flow control while the UI service only handles:
1. User input collection
2. Event publishing
3. Session management
"""
import uuid
import time
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..core.engine import GrimoireEngine
from ..utils.debug import debug_print
from .ui_service import (
    UIServiceInterface,
    SystemInfo,
    FlowInfo,
    ExecutionSession,
    ExecutionStatus,
    ExecutionProgress,
    StepInfo,
    Choice,
    InputType
)
from ..models.flow import StepDefinition, StepResult
from ..models.system import System
from ..services import event_signals


class GrimoireUIService(UIServiceInterface):
    """Clean UI Service implementation without flow control logic."""
    
    def __init__(self):
        self.engine = GrimoireEngine()
        self.active_sessions: Dict[str, ExecutionSession] = {}
        self._session_lock = threading.Lock()
        self.loaded_systems: Dict[str, System] = {}
    
    def load_system(self, system_path) -> SystemInfo:
        """Load a GRIMOIRE system and return system information."""
        debug_print(f"[UI_SERVICE] Loading system from {system_path}")
        
        # Use the engine to load the system
        system = self.engine.load_system(system_path)
        
        # Store the loaded system
        self.loaded_systems[system.id] = system
        
        # Return system info
        return SystemInfo(
            id=system.id,
            name=system.name or system.id,
            description=system.description,
            version=getattr(system, 'version', None),
            flow_count=len(system.flows),
            model_count=len(getattr(system, 'models', [])),
            compendium_count=len(getattr(system, 'compendiums', [])),
            table_count=len(getattr(system, 'tables', []))
        )
    
    def list_flows(self, system_id: str) -> List[FlowInfo]:
        """List all flows available in a system."""
        debug_print(f"[UI_SERVICE] Listing flows for system {system_id}")
        
        if system_id not in self.loaded_systems:
            raise ValueError(f"System '{system_id}' not found")
        
        system = self.loaded_systems[system_id]
        flow_infos = []
        
        for flow_id, flow in system.flows.items():
            flow_info = FlowInfo(
                id=flow_id,
                name=getattr(flow, 'name', flow_id),
                description=getattr(flow, 'description', None),
                step_count=len(flow.steps),
                requires_inputs=bool(getattr(flow, 'inputs', [])),
                produces_outputs=bool(getattr(flow, 'outputs', []))
            )
            flow_infos.append(flow_info)
        
        return flow_infos
    
    def start_flow_execution(
        self,
        system_id: str,
        flow_id: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> ExecutionSession:
        """Start executing a flow and return the session."""
        debug_print(f"[UI_SERVICE] Starting flow execution: {system_id}/{flow_id}")
        
        if system_id not in self.loaded_systems:
            raise ValueError(f"System '{system_id}' not found")
        
        system = self.loaded_systems[system_id]
        return self.start_execution(system, flow_id, inputs)
    
    def get_execution_status(self, session_id: str) -> ExecutionSession:
        """Get the current status of an execution session."""
        return self.get_session(session_id)
    
    def provide_user_input(
        self, 
        session_id: str, 
        input_data: Any
    ) -> ExecutionSession:
        """Provide user input to continue execution."""
        return self.provide_input(session_id, str(input_data))
    
    def start_execution(
        self,
        system: System,
        flow_id: str,
        inputs: Optional[Dict[str, Any]] = None
    ) -> ExecutionSession:
        """Start a new flow execution session."""
        debug_print(f"[UI_SERVICE] Starting execution for flow {flow_id}")
        
        session_id = str(uuid.uuid4())
        session = ExecutionSession(
            session_id=session_id,
            system_id=system.id,
            flow_id=flow_id,
            status=ExecutionStatus.STARTING,
            variables=inputs or {}
        )
        
        with self._session_lock:
            self.active_sessions[session_id] = session
        
        # Start async execution
        thread = threading.Thread(
            target=self._execute_flow_async,
            args=(session, system, flow_id, inputs),
            daemon=True
        )
        thread.start()
        
        return session
    
    def get_session(self, session_id: str) -> ExecutionSession:
        """Get a session by ID."""
        with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session '{session_id}' not found")
            return self.active_sessions[session_id]
    
    def list_sessions(self) -> List[ExecutionSession]:
        """List all active sessions."""
        with self._session_lock:
            return list(self.active_sessions.values())
    
    def make_choice(self, session_id: str, choice_id: str) -> ExecutionSession:
        """Make a choice to continue execution."""
        debug_print(f"[UI_SERVICE] Making choice for session {session_id}: {choice_id}")
        
        with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session '{session_id}' not found")
            
            session = self.active_sessions[session_id]
            if not session.requires_choice:
                raise ValueError(f"Session '{session_id}' is not waiting for a choice")
            
            # Validate choice ID
            available_choice_ids = {choice.id for choice in session.choices}
            if choice_id not in available_choice_ids:
                raise ValueError(f"Choice '{choice_id}' not found in session '{session_id}'")
            
            # Store the choice for engine processing
            session._user_choice_id = choice_id
            
            session.requires_choice = False
            session.choice_prompt = None
            session.choices = []
            session.status = ExecutionStatus.RUNNING
            
            debug_print(f"[UI_SERVICE] Choice made for session {session_id}: {choice_id}")
            return session
    
    def make_multiple_choices(
        self, 
        session_id: str, 
        choice_ids: List[str]
    ) -> ExecutionSession:
        """Make multiple choices to continue execution."""
        debug_print(f"[UI_SERVICE] Making multiple choices for session {session_id}: {choice_ids}")
        
        with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session '{session_id}' not found")
            
            session = self.active_sessions[session_id]
            if not session.requires_choice:
                raise ValueError(f"Session '{session_id}' is not waiting for a choice")
            
            # Validate all choice IDs
            available_choice_ids = {choice.id for choice in session.choices}
            for choice_id in choice_ids:
                if choice_id not in available_choice_ids:
                    raise ValueError(f"Choice '{choice_id}' not found in session '{session_id}'")
            
            # Store the choice IDs for engine processing
            session._user_choice_ids = choice_ids
            
            session.requires_choice = False
            session.choice_prompt = None
            session.choices = []
            session.status = ExecutionStatus.RUNNING
            
            debug_print(f"[UI_SERVICE] Multiple choices made for session {session_id}: {choice_ids}")
            return session
    
    def provide_input(self, session_id: str, input_value: str) -> ExecutionSession:
        """Provide input to continue execution."""
        debug_print(f"[UI_SERVICE] Providing input for session {session_id}: {input_value}")
        
        with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session '{session_id}' not found")
            
            session = self.active_sessions[session_id]
            if not session.requires_input:
                raise ValueError(f"Session '{session_id}' is not waiting for input")
            
            # Store the input in session variables for engine access
            session.variables['user_input'] = input_value
            
            session.requires_input = False
            session.input_prompt = None
            session.status = ExecutionStatus.RUNNING
            
            debug_print(f"[UI_SERVICE] Input provided for session {session_id}: {input_value}")
            return session
    
    def cancel_execution(self, session_id: str) -> None:
        """Cancel an active execution session."""
        debug_print(f"[UI_SERVICE] Cancelling session {session_id}")
        
        with self._session_lock:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session '{session_id}' not found")
            
            session = self.active_sessions[session_id]
            session.status = ExecutionStatus.CANCELLED
            
            # Publish cancellation event using blinker
            event_signals.publish_flow_cancelled(
                session_id=session_id,
                flow_id=session.flow_id,
                reason="user_cancelled"
            )
    
    def cleanup_session(self, session_id: str) -> None:
        """Remove a completed or cancelled session."""
        debug_print(f"[UI_SERVICE] Cleaning up session {session_id}")
        
        with self._session_lock:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    def subscribe_to_events(self, callback) -> None:
        """Subscribe to execution events (legacy - blinker signals are used instead)."""
        debug_print(f"[UI_SERVICE] Legacy event subscription - use blinker signals directly")
        pass
    
    def unsubscribe_from_events(self, callback) -> None:
        """Unsubscribe from execution events (legacy - blinker signals are used instead)."""
        debug_print(f"[UI_SERVICE] Legacy event unsubscription - use blinker signals directly")
        pass
    
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
            
            # Publish flow started event using blinker
            event_signals.publish_flow_started(
                session_id=session.session_id,
                flow_id=flow_id,
                system_id=system.id,
                inputs=inputs or {}
            )
            
            # Create execution context
            context = self.engine.create_execution_context(system, **inputs)
            
            # Execute the flow step by step, letting the engine handle all logic
            step_count = 0
            flow = system.get_flow(flow_id)
            step_generator = self.engine.step_through_flow(flow_id, context, system)
            current_step_result = None
            
            while True:
                try:
                    # Only get next step result if we don't already have one from a flow jump
                    if current_step_result is None:
                        current_step_result = next(step_generator)
                        step_count += 1
                    
                    # Update session progress
                    session.progress = ExecutionProgress(
                        current_step=current_step_result.step_id,
                        step_number=step_count,
                        completed_steps=context.step_history.copy()
                    )
                    
                    # Get step info
                    step = flow.get_step(current_step_result.step_id)
                    step_info = StepInfo(
                        id=step.id,
                        name=getattr(step, 'name', None),
                        type=str(step.type.value if hasattr(step.type, 'value') else step.type),
                        description=getattr(step, 'description', None),
                        prompt=getattr(step, 'prompt', None),
                        step_number=step_count
                    )
                    
                    # Publish step started event using blinker
                    event_signals.publish_step_started(
                        session_id=session.session_id,
                        step_info=step_info,
                        step_number=step_count
                    )
                    
                    # Check if step requires user input
                    if current_step_result.requires_input:
                        debug_print(f"[UI_SERVICE] Step {current_step_result.step_id} requires user input")
                        
                        # Handle choice input
                        if hasattr(current_step_result, 'choices') and current_step_result.choices:
                            session.status = ExecutionStatus.WAITING_FOR_CHOICE
                            session.requires_choice = True
                            session.choice_prompt = current_step_result.prompt
                            
                            # Convert choices from step result
                            choices = []
                            for i, choice_def in enumerate(current_step_result.choices):
                                choice = Choice(
                                    id=getattr(choice_def, 'id', str(i)),
                                    label=getattr(choice_def, 'label', f'Choice {i+1}'),
                                    description=getattr(choice_def, 'description', None),
                                    next_step=getattr(choice_def, 'next_step', None)
                                )
                                choices.append(choice)
                            
                            session.choices = choices
                            
                            # Get selection count from step result data
                            selection_count = current_step_result.data.get("selection_count", 1) if current_step_result.data else 1
                            
                            # Publish choice required event using blinker
                            event_signals.publish_choice_required(
                                session_id=session.session_id,
                                step_info=step_info,
                                prompt=current_step_result.prompt or "Make a choice:",
                                choices=choices,
                                selection_count=selection_count
                            )
                            
                            # Wait for user choice
                            while session.requires_choice:
                                if session.status == ExecutionStatus.CANCELLED:
                                    return
                                time.sleep(0.1)  # Small delay to prevent busy waiting
                            
                            # User choice is now available in session
                            # Put it in the context for the engine to process
                            if hasattr(session, '_user_choice_id'):
                                context.set_variable("pending_user_choice_id", session._user_choice_id)
                                delattr(session, '_user_choice_id')
                            elif hasattr(session, '_user_choice_ids'):
                                context.set_variable("pending_user_choice_ids", session._user_choice_ids)
                                delattr(session, '_user_choice_ids')
                            
                            # Re-execute the step with user input available
                            debug_print(f"[UI_SERVICE] Re-executing step {current_step_result.step_id} with user input")
                            current_step_result = self.engine._execute_step(step, context, system)
                            
                            # If the step result has a next_step_id, we need to force the step generator to jump
                            if current_step_result.next_step_id and current_step_result.next_step_id != step.next_step:
                                debug_print(f"[UI_SERVICE] Flow jump from choice: {current_step_result.step_id} -> {current_step_result.next_step_id}")
                                
                                # Skip steps in the generator until we reach the target step
                                try:
                                    while True:
                                        peek_result = next(step_generator)
                                        step_count += 1
                                        debug_print(f"[UI_SERVICE] Flow jump: found step {peek_result.step_id}, requires_input={peek_result.requires_input}")
                                        if peek_result.step_id == current_step_result.next_step_id:
                                            # Found the target step, replace current_step_result
                                            current_step_result = peek_result
                                            debug_print(f"[UI_SERVICE] Flow jump: target step found, requires_input={current_step_result.requires_input}")
                                            
                                            # Update session progress for the jumped-to step
                                            session.progress = ExecutionProgress(
                                                current_step=current_step_result.step_id,
                                                step_number=step_count,
                                                completed_steps=context.step_history.copy()
                                            )
                                            
                                            # Get new step info
                                            step = flow.get_step(current_step_result.step_id)
                                            step_info = StepInfo(
                                                id=step.id,
                                                name=getattr(step, 'name', None),
                                                type=str(step.type.value if hasattr(step.type, 'value') else step.type),
                                                description=getattr(step, 'description', None),
                                                prompt=getattr(step, 'prompt', None),
                                                step_number=step_count
                                            )
                                            break
                                except StopIteration:
                                    # Reached end of flow while looking for target step
                                    break
                            
                            # After flow jump, check if the jumped-to step requires input
                            debug_print(f"[UI_SERVICE] Jumped-to step details: step_id={current_step_result.step_id}, requires_input={current_step_result.requires_input}, has_choices={hasattr(current_step_result, 'choices') and bool(current_step_result.choices)}")
                            if current_step_result.requires_input:
                                debug_print(f"[UI_SERVICE] Jumped-to step {current_step_result.step_id} requires input")
                                # Check if it's a choice step or regular input step
                                if hasattr(current_step_result, 'choices') and current_step_result.choices:
                                    debug_print(f"[UI_SERVICE] Jumped-to step is a choice step with {len(current_step_result.choices)} choices")
                                    # This is a choice step - restart the loop to handle the choices
                                    continue
                                else:
                                    debug_print(f"[UI_SERVICE] Jumped-to step is a regular input step")
                                    # This is a regular input step - restart the loop to handle the input
                                    continue
                            else:
                                debug_print(f"[UI_SERVICE] Jumped-to step {current_step_result.step_id} is complete")
                        else:
                            # This is a regular input step
                            session.status = ExecutionStatus.WAITING_FOR_INPUT
                            session.requires_input = True
                            session.input_prompt = current_step_result.prompt
                            
                            # Determine input type based on step type
                            step_type = str(step.type.value if hasattr(step.type, 'value') else step.type)
                            input_type = InputType.TEXT  # Default
                            if step_type == "player_input":
                                input_type = InputType.TEXT
                            elif step_type == "dice_roll":
                                input_type = InputType.NUMBER
                            
                            # Publish input required event using blinker
                            event_signals.publish_input_required(
                                session_id=session.session_id,
                                step_info=step_info,
                                prompt=current_step_result.prompt or "Enter input:",
                                input_type=input_type.value
                            )
                            
                            # Wait for user input
                            while session.requires_input:
                                if session.status == ExecutionStatus.CANCELLED:
                                    return
                                time.sleep(0.1)  # Small delay to prevent busy waiting
                            
                            # Input should be processed by the engine - continue with next iteration
                            continue
                    
                    # Publish step completed event using blinker
                    event_signals.publish_step_completed(
                        session_id=session.session_id,
                        step_info=step_info,
                        step_number=step_count,
                        step_data=current_step_result.data,
                        next_step_id=current_step_result.next_step_id
                    )
                    
                    # Clear current_step_result so next iteration will advance the generator
                    current_step_result = None
                    
                except StopIteration:
                    # Flow completed successfully
                    break
            
            # Flow completed successfully
            session.status = ExecutionStatus.COMPLETED
            session.outputs = context.outputs.copy()
            session.variables.update(context.variables)
            
            # Publish flow completed event using blinker
            event_signals.publish_flow_completed(
                session_id=session.session_id,
                flow_id=flow_id,
                outputs=session.outputs,
                variables=session.variables,
                step_count=step_count
            )
            
            debug_print(f"[UI_SERVICE] Flow execution completed for session {session.session_id}")
            
        except Exception as e:
            debug_print(f"[UI_SERVICE] Error in flow execution: {e}")
            session.status = ExecutionStatus.FAILED
            session.error = str(e)
            
            # Publish error occurred event using blinker
            event_signals.publish_error_occurred(
                session_id=session.session_id,
                error_message=str(e),
                error_type="execution_error"
            )
