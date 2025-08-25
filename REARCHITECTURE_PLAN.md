# GRIMOIRE-RUNNER REARCHITECTURE PLAN

## Overview

This document outlines the architectural issues found in the current grimoire-runner codebase and provides a comprehensive plan to separate UI concerns from engine logic, eliminate vestigial code, and establish clear architectural boundaries.

## AI Guidelines

Always remember the following points as you are working on this code base:

1. Use the virtual env in the project root (`source .venv/bin/activate && <your_command>`)

2. Prefer explicit errors over fallbacks when fallbacks would mask issues. We want to fix issues so we can have a stable system.

3. Follow good software development practices (like SOLID).

4. Simpler is better.

5. Remember GRIMOIRE aims to define Table-Top RPG (TTRPG) systems in YAML and keep the engine code generic. Avoid adding special-cases for TTRPG system-specific information (model names, model attributes, table values, system-specific information, etc) into the engine.

6. In the engine, use debug_print() liberally with --debug option to the grimoire-runner CLI tool to capture the flow of data and decisions within the code. Do not use logging, since Rich appears to silence it somehow.

## Current Architectural Problems

### 1. **UI/Engine Boundary Violations**

#### Rich TUI (`rich_tui.py`) Issues:

- **Direct Engine Management**: UI directly instantiates and manages `GrimoireEngine` instances
- **Context Manipulation**: UI directly manipulates `ExecutionContext` objects, calling methods like:
  - `context.set_variable()`, `context.set_input()`, `context.get_output()`
  - `context.initialize_output_models()`, `context.initialize_input_models()`
  - `context.initialize_model_observables()`, `context.compute_derived_fields()`
- **System Access**: UI directly accesses `System` objects and their internal models
- **Step Execution Logic**: UI contains step execution logic that should be in the engine:
  - Step-by-step flow execution in `_execute_flow()`
  - Step result processing in `_execute_single_step()`
  - Choice handling logic with direct executor calls
  - Action execution via `self.engine.action_executor.execute_actions()`
- **Template Resolution**: UI performs template resolution for success/failure messages
- **Flow State Management**: UI manages flow namespace creation and cleanup

#### Browser UI (`browser.py`, `rich_browser.py`) Issues:

- **Direct Engine Instantiation**: Browser UIs create their own `GrimoireEngine` instances
- **System Loading**: UI handles system loading and management
- **Template Context Creation**: UI creates execution contexts for template resolution

#### Interactive REPL (`interactive.py`) Issues:

- **Engine Management**: REPL directly manages engine and system instances
- **Flow Execution**: REPL performs flow execution logic that duplicates engine functionality
- **Context Creation**: Creates execution contexts for template resolution

### 2. **Duplicated Code and Vestigial Patterns**

#### Template Context Creation:

- **Multiple Implementations**: `create_template_context()` function exists in multiple files:
  - `cli.py` (lines 28-38)
  - `interactive.py` (similar pattern)
  - Pattern repeated in Rich TUI initialization
- **Redundant System Metadata Setup**: Same system metadata structure created in multiple places

#### System Loading:

- **Repeated Pattern**: Every UI component loads systems independently using the same pattern
- **No Shared System Management**: Each UI maintains its own system instance

#### Error Message Handling:

- **Step Success/Failure Messages**: Logic for step messages scattered across UI and engine
- **Inconsistent Message Resolution**: Some UIs resolve templates, others don't

### 3. **Architectural Boundary Issues**

#### Data Flow Problems:

- **UI as Orchestrator**: Rich TUI acts as flow orchestrator instead of presentation layer
- **Engine as Library**: Engine is used as a utility library rather than the primary orchestrator
- **Context Leakage**: ExecutionContext objects leak into UI layer

#### Responsibility Confusion:

- **Flow Control in UI**: UI determines next steps and manages flow progression
- **Input Processing**: UI handles user input processing and validation
- **Result Interpretation**: UI interprets step results and determines success/failure

### 4. **Specific Code Issues**

#### Rich TUI Specific Problems:

```python
# PROBLEM: UI directly executing engine operations
step_result = self.engine._execute_step(step, self.context, self.system)

# PROBLEM: UI managing action execution
self.engine.action_executor.execute_actions(step.actions, self.context, choice_result.data, self.system)

# PROBLEM: UI handling template resolution
resolved_message = context.resolve_template_with_step_data(step.result_message, step_data)

# PROBLEM: UI managing model observables
self.context.initialize_model_observables(model, input_name, model_resolver)
```

#### Executor Import in UI:

```python
# PROBLEM: UI importing and using executors directly
from ..executors.player_input_executor import PlayerInputExecutor
input_executor = PlayerInputExecutor()
input_result = input_executor.process_input(user_input, step, self.context, self.system)
```

## Proposed Architecture

### 1. **Clear Separation of Concerns**

#### Engine Layer (Core Business Logic):

- **Flow Orchestration**: Engine manages complete flow execution
- **Step Execution**: Engine coordinates all step execution
- **Context Management**: Engine owns and manages execution contexts
- **Template Resolution**: Engine handles all template operations
- **System Management**: Engine manages system loading and caching

#### UI Layer (Presentation Only):

- **Display Management**: UIs only handle presentation and user interaction
- **Event Handling**: UIs capture user input and send commands to engine
- **Progress Display**: UIs show execution progress and results
- **No Business Logic**: UIs contain no flow control or data processing logic

#### Service Layer (Shared Services):

- **UI Service Interface**: Clean interface between UI and engine
- **Event/Command Pattern**: UIs send commands, engine publishes events
- **Display State Management**: Separate service for managing UI state

### 2. **New Architecture Components**

#### UI Service Interface:

```python
class UIServiceInterface:
    """Clean interface between UI and engine operations."""

    def load_system(self, system_path: Path) -> SystemInfo
    def list_flows(self, system_id: str) -> List[FlowInfo]
    def start_flow_execution(self, system_id: str, flow_id: str, inputs: dict) -> ExecutionSession
    def get_execution_status(self, session_id: str) -> ExecutionStatus
    def provide_user_input(self, session_id: str, input_data: Any) -> ExecutionStatus
    def cancel_execution(self, session_id: str) -> None
```

#### Execution Session Management:

```python
class ExecutionSession:
    """Represents an active flow execution session."""

    session_id: str
    current_step: StepInfo
    requires_input: bool
    input_prompt: str
    choices: List[Choice]
    progress: ExecutionProgress
    messages: List[DisplayMessage]
```

#### Event-Driven Updates:

```python
class ExecutionEvents:
    """Events published by engine for UI consumption."""

    StepStarted(step_info: StepInfo)
    StepCompleted(step_result: StepResult)
    InputRequired(prompt: str, input_type: InputType, choices: List[Choice])
    FlowCompleted(result: FlowResult)
    ErrorOccurred(error: ExecutionError)
```

### 3. **Implementation Plan**

#### Phase 1: Foundation & Development Tools

1. **Create Minimal `grimoire` CLI Tool**: Build basic CLI that uses existing engine directly
   - Simple wrapper around current `GrimoireEngine.execute_flow()`
   - Basic logging of step execution without events (yet)
   - Simple input prompting for player_input steps
   - Set up as separate entry point in pyproject.toml
   - **Priority**: Immediate - Can be built with existing engine architecture
2. **Define Service Interface**: Create clean contract between UI and engine
3. **Implement Engine Service**: Wrapper around existing engine with UI-friendly interface
4. **Enhance `grimoire` CLI**: Update to use new service interface and event system
5. **Create Event System**: Implement event publishing for UI updates
6. **Session Management**: Add execution session tracking

#### Phase 2: Engine Architecture Development

1. **Test with `grimoire` CLI**: Use the simple CLI to validate engine changes
2. **Refine Event/Command System**: Iterate on event publishing and command processing
3. **Session State Management**: Implement robust session lifecycle management
4. **Engine Service Completion**: Complete the UIService interface implementation

#### Phase 3: Rich TUI Refactor

1. **Remove Engine Dependencies**: Extract all engine logic from Rich TUI
2. **Implement Event Handlers**: Subscribe to engine events for UI updates
3. **Simplify Flow Control**: Replace UI flow control with service calls
4. **Clean Input Handling**: Use service interface for user input processing
5. **Test Rich TUI Changes**: Validate that Rich TUI provides same functionality via new architecture

#### Phase 4: Other UI Refactors

1. **Browser UIs**: Remove direct engine usage, use service interface
2. **Interactive REPL**: Refactor to use service interface
3. **CLI**: Update grimoire-runner CLI to use new service interface
4. **Deprecate `grimoire` CLI**: Once grimoire-runner is updated, the simple CLI can be removed

#### Phase 5: Cleanup & Polish

1. **Remove Vestigial Code**: Eliminate duplicated functions and dead imports
2. **Consolidate System Loading**: Single system management service
3. **Clean Import Dependencies**: Remove unnecessary imports between layers
4. **Add Missing Abstractions**: Display state service, configuration service, etc.

#### When to Use `grimoire` CLI:

- **Immediately**: As soon as Phase 1 is complete, use for all engine development
- **Testing New Features**: Every engine change should be tested with `grimoire` first
- **Debugging Events**: Use event logging to debug and refine the event system
- **Parallel Development**: Continue using while Rich TUI is being refactored
- **Until Completion**: Keep using until grimoire-runner CLI is fully updated in Phase 4

## Detailed Refactoring Tasks

### 1. **Rich TUI Refactoring**

#### Remove Direct Engine Calls:

- Replace `self.engine.load_system()` with `ui_service.load_system()`
- Replace `self.engine.create_execution_context()` with session management
- Replace `self.engine.action_executor.execute_actions()` with service calls
- Remove all direct `ExecutionContext` manipulation

#### Simplify Flow Execution:

```python
# BEFORE (in UI):
def _execute_flow(self):
    current_step_id = self.flow_obj.steps[0].id
    while current_step_id:
        step = self.flow_obj.get_step(current_step_id)
        step_result = self._execute_single_step(step, step_num)
        # Complex step execution logic...

# AFTER (in UI):
def execute_flow(self):
    session = self.ui_service.start_flow_execution(self.system_id, self.flow_id, self.inputs)
    self._handle_execution_session(session)
```

#### Event-Driven Display Updates:

```python
# AFTER (in UI):
def _handle_execution_session(self, session):
    while not session.is_complete:
        if session.requires_input:
            user_input = self._get_user_input(session.input_prompt, session.choices)
            session = self.ui_service.provide_user_input(session.session_id, user_input)
        else:
            session = self.ui_service.continue_execution(session.session_id)
        self._update_display(session.progress, session.messages)
```

### 2. **Engine Refactoring**

#### Add UI Service Layer:

```python
class GrimoireUIService:
    """Service layer for UI interactions with the engine."""

    def __init__(self):
        self.engine = GrimoireEngine()
        self.active_sessions = {}
        self.event_subscribers = []

    def start_flow_execution(self, system_id: str, flow_id: str, inputs: dict) -> ExecutionSession:
        session = ExecutionSession(
            session_id=str(uuid.uuid4()),
            system_id=system_id,
            flow_id=flow_id,
            inputs=inputs
        )
        self.active_sessions[session.session_id] = session
        self._begin_async_execution(session)
        return session
```

#### Event Publishing:

```python
class ExecutionEventPublisher:
    """Publishes execution events for UI consumption."""

    def publish_step_started(self, session_id: str, step_info: StepInfo):
        event = StepStartedEvent(session_id, step_info)
        self._notify_subscribers(event)

    def publish_input_required(self, session_id: str, prompt: str, input_type: InputType):
        event = InputRequiredEvent(session_id, prompt, input_type)
        self._notify_subscribers(event)
```

### 3. **Vestigial Code Cleanup**

#### Files to Remove/Consolidate:

- Remove duplicate `create_template_context()` functions
- Consolidate system loading logic into single service
- Remove unused Textual references in CLI
- Clean up duplicate browser functionality
- Remove dead imports and unused classes

#### Code Patterns to Eliminate:

- Direct `ExecutionContext` creation in UI layers
- Template resolution in UI components
- System metadata setup in multiple places
- Duplicate error message handling logic

## Success Metrics

### 1. **Architectural Boundaries**

- ✅ UI code contains no imports from `..executors`, `..models.context_data`, or direct engine operations
- ✅ Engine code publishes events instead of requiring UI callbacks
- ✅ Clear service interface defines all UI/engine interactions

### 2. **Code Quality**

- ✅ No duplicated template context creation functions
- ✅ Single system loading and management service
- ✅ Consistent error handling across all UIs
- ✅ Removed all vestigial code and dead imports

### 3. **Maintainability**

- ✅ UI changes don't require engine code modifications
- ✅ Engine changes don't break UI implementations
- ✅ New UIs can be added without duplicating engine logic
- ✅ Clear separation allows independent testing of UI and engine

### 4. **Functionality**

- ✅ All existing UI functionality preserved
- ✅ Performance maintained or improved
- ✅ Better error handling and user experience
- ✅ Consistent behavior across all UI interfaces

## Implementation Approach

### Agentic Development Strategy

This rearchitecture will be implemented through iterative, atomic changes using AI-assisted development:

1. **Atomic Changes**: Each change will be a single, focused refactoring that moves us one step closer to the target architecture
2. **Test & Iterate**: After each atomic change, manual testing ensures the system still functions correctly
3. **Commit & Continue**: Successful changes are committed before moving to the next atomic refactoring
4. **Incremental Progress**: This approach ensures the system remains functional throughout the entire rearchitecture

### Test Suite Evolution

As we rearchitecture, the test suite will need significant updates:

#### Tests to Remove/Obsolete:

- **UI Integration Tests**: Tests that directly test UI components interacting with engine internals
- **Direct Engine Access Tests**: Tests in UI modules that directly call engine methods
- **Context Manipulation Tests**: Tests that verify UI components can manipulate ExecutionContext objects
- **Step Execution Tests in UI**: Tests for step execution logic that will move to the engine

#### New Tests to Add:

- **Service Interface Tests**: Comprehensive tests for the UIServiceInterface contract
- **Event Publishing Tests**: Tests to ensure engine publishes correct events at the right times
- **Command Processing Tests**: Tests to verify the engine correctly processes UI commands
- **Session Management Tests**: Tests for execution session lifecycle and state management
- **Client-Server Communication Tests**: Tests for network communication between engine server and UI clients

#### Test Refactoring Patterns:

```python
# BEFORE (Testing UI with Engine):
def test_rich_tui_executes_flow():
    tui = RichTUI(system_path, flow_id)
    tui.run()  # This tests UI+Engine together
    assert tui.step_results[-1].success

# AFTER (Separate UI and Engine Testing):
def test_ui_service_executes_flow():
    service = UIService()
    session = service.start_flow_execution(system_id, flow_id, inputs)
    assert isinstance(session, ExecutionSession)

def test_rich_tui_handles_events():
    tui = RichTUI()
    event = StepStartedEvent(session_id="test", step_info=mock_step)
    tui.handle_event(event)
    assert tui.current_display_state.current_step == mock_step
```

### Client-Server Architecture (Long-term Vision)

The final architecture will support both local and remote execution:

#### Local Mode:

- **Single Binary**: Both engine server and UI client run in the same process
- **In-Memory Communication**: Events and commands passed via direct method calls
- **Development/Solo Play**: Optimal for development and single-player scenarios

#### Network Mode:

- **Dedicated Server**: GrimoireEngine runs as a standalone server process
- **Remote Clients**: UI clients connect over network (WebSocket/HTTP)
- **Multi-player Support**: Multiple players can connect to the same game session
- **Resource Distribution**: Heavy LLM processing happens on server, lightweight UIs run on client devices

#### Network Architecture Components:

```python
class GrimoireServer:
    """Standalone server running GrimoireEngine with network interface."""

    def start_server(self, host: str, port: int):
        # Start WebSocket server for client connections

    def handle_client_command(self, client_id: str, command: Command):
        # Process command and publish events to relevant clients

    def broadcast_event(self, event: Event, session_id: str):
        # Send event to all clients subscribed to session

class GrimoireClient:
    """Network client that communicates with remote GrimoireServer."""

    def connect(self, server_url: str):
        # Establish WebSocket connection to server

    def send_command(self, command: Command):
        # Send command to server over network

    def subscribe_to_events(self, handler: Callable[[Event], None]):
        # Register event handler for server events
```

### Simple Event-Logging CLI Tool (`grimoire`)

To accelerate engine development, we'll create a separate minimal CLI tool:

#### Purpose:

- **Engine Development**: Focus on engine/service layer without UI complexity
- **Event Debugging**: Log all events to see exactly what the engine publishes
- **Input Testing**: Simple prompts for required user input without Rich formatting
- **Rapid Iteration**: Quickly test engine changes without rebuilding complex UIs
- **Clean Separation**: Avoid adding complexity to existing grimoire-runner CLI during transition

#### Implementation:

```python
# New file: grimoire-runner/src/grimoire_runner/simple_cli.py
class SimpleEventCLI:
    """Minimal CLI that logs events and prompts for input."""

    def __init__(self):
        self.ui_service = UIService()
        self.ui_service.subscribe_to_events(self._log_event)

    def _log_event(self, event: Event):
        print(f"[EVENT] {event.__class__.__name__}: {event}")

        if isinstance(event, InputRequiredEvent):
            self._handle_input_required(event)

    def _handle_input_required(self, event: InputRequiredEvent):
        if event.choices:
            print(f"Choices: {[c.label for c in event.choices]}")
            choice = input("Enter choice number: ")
            self.ui_service.provide_user_input(event.session_id, choice)
        else:
            user_input = input(f"{event.prompt}: ")
            self.ui_service.provide_user_input(event.session_id, user_input)

# New entry point in pyproject.toml:
# [project.scripts]
# grimoire = "grimoire_runner.simple_cli:main"

# Usage:
# grimoire system.yaml flow_name
```

#### Benefits of Separate Tool:

- **No Complexity in Main CLI**: Existing grimoire-runner remains unchanged during transition
- **Pure Engine Testing**: Clean environment for testing new architecture without legacy UI code
- **Independent Development**: Can be developed and tested without affecting existing functionality
- **Easy Removal**: Can be removed once rearchitecture is complete
- **Clear Purpose**: Dedicated tool for engine development and event debugging

This separate CLI tool will allow rapid development and testing of the engine layer while keeping the existing grimoire-runner CLI stable during the rearchitecture process.

## Benefits of This Approach

1. **Risk Mitigation**: Small atomic changes reduce the chance of breaking the system
2. **Continuous Validation**: Manual testing after each change ensures functionality is preserved
3. **Easier Debugging**: Issues can be traced to specific atomic changes
4. **Parallel Development**: Simple CLI enables engine work while UI refactoring continues
5. **Future-Proof**: Client-server architecture supports both local and networked use cases

This rearchitecture will create a clean, maintainable separation between the presentation layer (UI) and business logic (engine), while eliminating the significant amount of duplicated and vestigial code that currently exists in the system.
