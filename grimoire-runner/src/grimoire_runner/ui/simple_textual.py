"""Simple Textual-based flow execution interface."""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, DataTable, 
    ProgressBar, Log, Label, RadioSet, RadioButton
)
from textual.binding import Binding
from textual.screen import ModalScreen
from rich.text import Text
import json
import time

from ..core.engine import GrimoireEngine
from ..models.flow import FlowResult, StepResult


class SimpleChoiceModal(ModalScreen[Optional[str]]):
    """Simple modal for user choices."""
    
    DEFAULT_CSS = """
    SimpleChoiceModal {
        align: center middle;
    }
    
    .modal-container {
        width: 70%;
        height: auto;
        background: $surface;
        border: thick $primary;
        padding: 2;
    }
    
    .modal-title {
        text-style: bold;
        margin-bottom: 1;
    }
    
    .modal-buttons {
        margin-top: 2;
        height: auto;
    }
    """
    
    def __init__(self, prompt: str, choices: List[Any]):
        super().__init__()
        self.prompt = prompt
        self.choices = choices
    
    def compose(self) -> ComposeResult:
        with Container(classes="modal-container"):
            yield Label("User Input Required", classes="modal-title")
            yield Label(self.prompt)
            
            with RadioSet(id="choice-set"):
                for choice in self.choices:
                    label = choice.label if hasattr(choice, 'label') else str(choice)
                    value = choice.id if hasattr(choice, 'id') else str(choice)
                    yield RadioButton(label, value=value)
            
            with Horizontal(classes="modal-buttons"):
                yield Button("Confirm", variant="primary", id="confirm")
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            radio_set = self.query_one("#choice-set", RadioSet)
            if radio_set.pressed_button:
                self.dismiss(radio_set.pressed_button.value)
            else:
                self.dismiss(None)
        elif event.button.id == "cancel":
            self.dismiss(None)


class SimpleFlowApp(App):
    """Simple flow execution app."""
    
    CSS = """
    .container {
        padding: 1;
        margin: 1;
    }
    
    .info-box {
        border: round cyan;
        padding: 1;
        margin-bottom: 1;
    }
    
    .progress-box {
        border: round yellow;
        padding: 1;
        margin-bottom: 1;
    }
    
    .log-box {
        border: round green;
        height: 20;
        padding: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "restart", "Restart"),
    ]
    
    def __init__(self, system_path: Path, flow_id: str):
        super().__init__()
        self.system_path = system_path
        self.flow_id = flow_id
        self.engine = GrimoireEngine()
        self.system = None
        self.flow_obj = None
        self.context = None
        self.current_step = 0
        self.total_steps = 0
        self.step_results = []
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with ScrollableContainer():
            with Vertical(classes="container"):
                # System info
                with Vertical(classes="info-box"):
                    yield Label("GRIMOIRE Flow Execution")
                    yield Static("", id="system-info")
                    yield Static("", id="flow-info")
                
                # Progress
                with Vertical(classes="progress-box"):
                    yield Label("Progress")
                    yield ProgressBar(id="progress", show_percentage=True)
                    yield Static("Initializing...", id="status")
                
                # Log
                with Vertical(classes="log-box"):
                    yield Label("Execution Log")
                    yield Log(id="log")
        
        yield Footer()
    
    def on_mount(self) -> None:
        self.call_after_refresh(self.start_execution)
    
    async def start_execution(self) -> None:
        """Start the flow execution."""
        try:
            self.log("Loading system...")
            
            # Load system
            self.system = self.engine.load_system(self.system_path)
            self.flow_obj = self.system.get_flow(self.flow_id)
            
            if not self.flow_obj:
                self.log("ERROR: Flow not found!")
                return
            
            # Update UI
            self.query_one("#system-info").update(f"System: {self.system.name}")
            self.query_one("#flow-info").update(f"Flow: {self.flow_obj.name} ({len(self.flow_obj.steps)} steps)")
            self.total_steps = len(self.flow_obj.steps)
            
            # Initialize context
            self.context = self.engine.create_execution_context()
            
            # Initialize flow variables
            for var_name, var_value in self.flow_obj.variables.items():
                self.context.set_variable(var_name, var_value)
            
            # Execute flow step by step
            await self.execute_flow_steps()
            
        except Exception as e:
            self.log(f"ERROR: {str(e)}")
    
    async def execute_flow_steps(self) -> None:
        """Execute flow steps one by one."""
        current_step_id = self.flow_obj.steps[0].id if self.flow_obj.steps else None
        step_num = 0
        
        while current_step_id:
            step = self.flow_obj.get_step(current_step_id)
            if not step:
                self.log(f"ERROR: Step not found: {current_step_id}")
                break
            
            step_num += 1
            
            # Update progress
            progress = (step_num / self.total_steps) * 100
            self.query_one("#progress").update(progress=progress)
            self.query_one("#status").update(f"Step {step_num}/{self.total_steps}: {step.name or step.id}")
            
            self.log(f"▶ Starting step {step_num}: {step.name or step.id}")
            
            # Update context
            self.context.current_step = current_step_id
            self.context.step_history.append(current_step_id)
            
            # Execute step
            try:
                success, next_step_id = await self.execute_single_step(step, step_num)
                
                if not success:
                    self.log("❌ Flow execution stopped due to step failure")
                    break
                
                # Determine next step
                if next_step_id:
                    current_step_id = next_step_id
                else:
                    current_step_id = self.flow_obj.get_next_step_id(current_step_id)
            
            except Exception as e:
                self.log(f"ERROR in step {current_step_id}: {str(e)}")
                break
            
            # Small delay
            await asyncio.sleep(0.5)
        
        self.log("✅ Flow execution completed!")
        self.query_one("#status").update("Flow completed")
    
    async def execute_single_step(self, step, step_num: int) -> tuple[bool, Optional[str]]:
        """Execute a single step."""
        # Execute the step through the engine
        step_result = self.engine._execute_step(step, self.context, self.system)
        
        self.log(f"Step result: requires_input={step_result.requires_input}, success={step_result.success}")
        
        # Handle user input if needed
        if step_result.requires_input:
            self.log("⏳ Step requires user input...")
            
            if step_result.choices:
                # Show choice modal
                prompt = step_result.prompt or "Please make a choice:"
                modal = SimpleChoiceModal(prompt, step_result.choices)
                
                # This will block until user makes a choice
                selected_choice = await self.push_screen(modal)
                
                if selected_choice is None:
                    self.log("❌ User cancelled input")
                    step_result.success = False
                    step_result.error = "User cancelled input"
                else:
                    self.log(f"✅ User selected: {selected_choice}")
                    
                    # Process the choice
                    from ..executors.choice_executor import ChoiceExecutor
                    choice_executor = ChoiceExecutor()
                    choice_result = choice_executor.process_choice(selected_choice, step, self.context)
                    
                    if choice_result and choice_result.next_step_id:
                        step_result.next_step_id = choice_result.next_step_id
                    
                    step_result.success = True
        
        # Log completion
        if step_result.success:
            self.log(f"✅ Completed step {step_num}")
        else:
            self.log(f"❌ Failed step {step_num}: {step_result.error}")
        
        self.step_results.append(step_result)
        return step_result.success, step_result.next_step_id
    
    def log(self, message: str) -> None:
        """Add message to log."""
        try:
            log_widget = self.query_one("#log", Log)
            log_widget.write_line(message)
        except Exception:
            print(message)
    
    def action_restart(self) -> None:
        """Restart execution."""
        self.step_results.clear()
        self.current_step = 0
        self.context = self.engine.create_execution_context()
        
        self.query_one("#progress").update(progress=0)
        self.query_one("#status").update("Restarting...")
        self.query_one("#log", Log).clear()
        
        self.call_after_refresh(self.start_execution)


def run_simple_textual_executor(system_path: Path, flow_id: str) -> None:
    """Run the simple Textual executor."""
    app = SimpleFlowApp(system_path, flow_id)
    app.run()
