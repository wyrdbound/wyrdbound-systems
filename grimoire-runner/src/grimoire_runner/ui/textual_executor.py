"""Textual-based flow execution interface with rich UI components."""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container, ScrollableContainer
from textual.widgets import (
    Header, Footer, Static, Button, Input, DataTable, 
    SelectionList, ProgressBar, Log, TabbedContent, TabPane,
    Tree, Label, Rule, Collapsible, RadioSet, RadioButton,
    Select, Switch, LoadingIndicator, Pretty, Markdown
)
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.reactive import reactive
from textual import events
from textual.message import Message
from rich.text import Text
from rich.console import Console
from rich.panel import Panel
import json
import time

from ..core.engine import GrimoireEngine
from ..core.loader import SystemLoader
from ..core.context import ExecutionContext
from ..models.flow import FlowResult, StepResult

logger = logging.getLogger(__name__)


class TextualLogHandler(logging.Handler):
    """Custom logging handler that sends logs to Textual Log widget."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app
    
    def emit(self, record):
        """Emit a log record to the Textual app."""
        try:
            message = self.format(record)
            # Use call_after_refresh to ensure we're on the main thread
            if hasattr(self.app, 'log_message'):
                self.app.call_after_refresh(self.app.log_message, message)
        except Exception:
            # If we can't log to the widget, don't break everything
            pass


class ChoiceModal(ModalScreen):
    """Modal screen for user choices."""
    
    # Simplified CSS without problematic properties
    DEFAULT_CSS = """
    ChoiceModal {
        align: center middle;
    }
    
    .choice-container {
        width: 60%;
        max-width: 80;
        height: auto;
        background: black;
        border: thick white;
        padding: 2;
    }
    
    .choice-title {
        color: white;
        text-style: bold;
        margin-bottom: 1;
    }
    
    .choice-prompt {
        margin-bottom: 1;
        color: white;
    }
    
    .choice-buttons {
        margin-top: 1;
        height: auto;
    }
    """
    
    def __init__(self, step_result: StepResult, is_multiple: bool = False, selection_count: int = 1):
        super().__init__()
        self.step_result = step_result
        self.is_multiple = is_multiple
        self.selection_count = selection_count
        self.selected_choices = []
        self.current_selection = 0
        self.result = None
    
    def compose(self) -> ComposeResult:
        """Create the choice modal."""
        with Container(classes="choice-container"):
            yield Label("User Input Required", classes="choice-title")
            prompt_text = self.step_result.prompt or "Please make a choice:"
            yield Label(prompt_text, classes="choice-prompt")
            
            if self.is_multiple:
                yield Label(f"Selection {self.current_selection + 1} of {self.selection_count}")
            
            if self.step_result.choices:
                # Create radio buttons for choices
                with RadioSet(id="choices"):
                    for choice in self.step_result.choices:
                        yield RadioButton(choice.label or choice.id, value=choice.id)
            
            with Horizontal(classes="choice-buttons"):
                yield Button("Confirm", variant="primary", id="confirm")
                yield Button("Cancel", variant="error", id="cancel")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "confirm":
            radio_set = self.query_one("#choices", RadioSet)
            if radio_set.pressed_button:
                selected_id = radio_set.pressed_button.value
                selected_choice = next((c for c in self.step_result.choices if c.id == selected_id), None)
                
                if self.is_multiple:
                    self.selected_choices.append(selected_choice)
                    self.current_selection += 1
                    
                    if self.current_selection < self.selection_count:
                        # Remove selected choice and continue
                        remaining_choices = [c for c in self.step_result.choices if c not in self.selected_choices]
                        self.step_result.choices = remaining_choices
                        self.refresh()
                        return
                    else:
                        # All selections made - return list of IDs
                        self.result = [c.id for c in self.selected_choices]
                        self.dismiss(self.result)
                else:
                    # Single selection - return the ID
                    self.result = selected_choice.id
                    self.dismiss(self.result)
            else:
                # No selection made
                self.result = None
                self.dismiss(None)
        elif event.button.id == "cancel":
            self.result = None
            self.dismiss(None)


class FlowExecutionApp(App):
    """Main application for flow execution with Textual widgets."""
    
    CSS = """
    .title {
        color: white;
        text-style: bold;
        margin: 1;
    }
    
    .info-panel {
        border: round cyan;
        padding: 1;
        margin: 1;
        height: auto;
    }
    
    .progress-container {
        margin: 1;
        height: auto;
    }
    
    .step-info {
        color: white;
        margin-bottom: 1;
    }
    
    .success {
        color: green;
        text-style: bold;
    }
    
    .error {
        color: red;
        text-style: bold;
    }
    
    .results-container {
        border: round green;
        padding: 1;
        margin: 1;
        display: none;
    }
    
    .log-container {
        border: round blue;
        max-height: 20;
        margin: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("s", "save", "Save Results"),
        Binding("r", "restart", "Restart Flow"),
    ]
    
    def __init__(self, system_path: Path, flow_id: str, output_path: Optional[Path] = None, interactive: bool = True):
        super().__init__()
        self.system_path = system_path
        self.flow_id = flow_id
        self.output_path = output_path
        self.interactive = interactive
        self.engine = GrimoireEngine()
        self.system = None
        self.flow_obj = None
        self.context = None
        self.current_result = None
        self.step_results = []
        self.current_step = 0
        self.total_steps = 0
    
    def compose(self) -> ComposeResult:
        """Create the main application layout."""
        yield Header(show_clock=True)
        
        with ScrollableContainer():
            # System and flow info
            with Vertical(classes="info-panel"):
                yield Label("GRIMOIRE Flow Execution", classes="title")
                yield Static("", id="system-info")
                yield Static("", id="flow-info")
            
            # Progress tracking
            with Vertical(classes="progress-container"):
                yield Label("Execution Progress", classes="title")
                yield ProgressBar(id="progress", show_percentage=True)
                yield Static("Initializing...", id="step-info", classes="step-info")
            
            # Execution log
            with Vertical(classes="log-container"):
                yield Label("Execution Log", classes="title")
                yield Log(id="execution-log")
            
            # Results section (initially hidden)
            with Vertical(classes="results-container", id="results-section"):
                yield Label("Results", classes="title")
                yield TabbedContent(id="results-tabs")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application."""
        # Set up logging redirection to capture logs in our widget
        self.log_handler = TextualLogHandler(self)
        self.log_handler.setLevel(logging.INFO)
        
        # Add our handler to relevant loggers
        grimoire_logger = logging.getLogger('grimoire_runner')
        grimoire_logger.addHandler(self.log_handler)
        grimoire_logger.setLevel(logging.INFO)
        
        # Prevent logs from going to console
        grimoire_logger.propagate = False
        
        self.call_after_refresh(self.load_system)
    
    async def load_system(self) -> None:
        """Load the system and flow."""
        try:
            # Update UI
            self.query_one("#step-info").update("Loading system...")
            
            # Load system
            self.system = self.engine.load_system(self.system_path)
            self.flow_obj = self.system.get_flow(self.flow_id)
            
            if not self.flow_obj:
                self.query_one("#step-info").update(Text("Flow not found!", style="bold red"))
                return
            
            # Update system info
            system_info = f"System: {self.system.name} ({self.system.id})"
            self.query_one("#system-info").update(system_info)
            
            # Update flow info
            # Create temporary context for resolving description templates
            temp_context = self.engine.create_execution_context()
            temp_context.system_metadata = {
                'id': self.system.id,
                'name': self.system.name,
                'description': self.system.description,
                'version': self.system.version,
                'currency': getattr(self.system, 'currency', {}),
                'credits': getattr(self.system, 'credits', {})
            }
            
            flow_info = f"Flow: {self.flow_obj.name}\nSteps: {len(self.flow_obj.steps)}"
            if self.flow_obj.description:
                resolved_description = self.flow_obj.resolve_description(temp_context)
                flow_info += f"\nDescription: {resolved_description}"
            self.query_one("#flow-info").update(flow_info)
            
            # Initialize execution
            self.context = self.engine.create_execution_context()
            self.total_steps = len(self.flow_obj.steps)
            
            # Start execution
            await self.execute_flow()
            
        except Exception as e:
            self.query_one("#step-info").update(Text(f"Error: {str(e)}", style="bold red"))
            self.log_message(f"[red]Error loading system: {str(e)}[/red]")
    
    async def execute_flow(self) -> None:
        """Execute the flow with step-by-step progress."""
        self.log_message("[cyan]Starting flow execution...[/cyan]")
        
        try:
            # Initialize flow variables
            for var_name, var_value in self.flow_obj.variables.items():
                self.context.set_variable(var_name, var_value)
            
            current_step_id = self.flow_obj.steps[0].id if self.flow_obj.steps else None
            step_num = 0
            
            while current_step_id:
                step = self.flow_obj.get_step(current_step_id)
                if not step:
                    self.log_message(f"[red]Step not found: {current_step_id}[/red]")
                    break
                
                step_num += 1
                step_name = step.name if step else current_step_id
                
                # Update progress and step info
                progress = (step_num / self.total_steps) * 100
                self.query_one("#progress").update(progress=progress)
                self.query_one("#step-info").update(Text(f"Step {step_num}/{self.total_steps}: {step_name}", style="cyan"))
                
                # Log step start
                self.log_message(f"[cyan]▶[/cyan] Starting Step {step_num}: {step_name}")
                
                # Update context
                self.context.current_step = current_step_id
                self.context.step_history.append(current_step_id)
                
                # Execute the step and wait for completion
                try:
                    success, next_step_id = await self.execute_single_step(step, step_num, step_name)
                    
                    if not success:
                        self.log_message(f"[red]Flow execution stopped due to step failure[/red]")
                        break
                    
                    # Determine next step - use the returned next_step_id if available
                    if next_step_id:
                        current_step_id = next_step_id
                    else:
                        current_step_id = self.flow_obj.get_next_step_id(current_step_id)
                
                except Exception as e:
                    self.log_message(f"[red]Error executing step {current_step_id}: {e}[/red]")
                    step_result = StepResult(
                        step_id=current_step_id,
                        success=False,
                        error=str(e)
                    )
                    self.step_results.append(step_result)
                    break
                
                # Small delay for visual effect
                await asyncio.sleep(0.2)
            
            # Create final result
            success = all(sr.success for sr in self.step_results) and step_num >= self.total_steps
            
            # Extract outputs
            outputs = {}
            for output_def in self.flow_obj.outputs:
                output_value = self.context.get_output(output_def.id)
                if output_value is not None:
                    outputs[output_def.id] = output_value
            
            self.current_result = FlowResult(
                flow_id=self.flow_id,
                success=success,
                outputs=outputs,
                variables=self.context.variables.copy(),
                step_results=self.step_results,
                error=self.step_results[-1].error if self.step_results and not self.step_results[-1].success else None,
                completed_at_step=self.step_results[-1].step_id if self.step_results and not self.step_results[-1].success else None
            )
            
            # Display results
            await self.display_results()
            
        except Exception as e:
            self.log_message(f"[red]Execution error: {str(e)}[/red]")
            self.query_one("#step-info").update(Text(f"Execution failed: {str(e)}", style="bold red"))
    
    async def execute_single_step(self, step, step_num: int, step_name: str) -> tuple[bool, Optional[str]]:
        """Execute a single step and return (success, next_step_id)."""
        step_result = self.engine._execute_step(step, self.context, self.system)
        
        self.log_message(f"[dim]Step result - requires_input: {step_result.requires_input}, success: {step_result.success}[/dim]")
        
        # Handle user input if needed - THIS BLOCKS UNTIL INPUT IS COMPLETE
        if step_result.requires_input and self.interactive:
            self.log_message(f"[yellow]Step requires user input - showing modal[/yellow]")
            
            # Wait for user input - this will block until modal is completed
            await self.handle_user_input(step_result, step)
            
            # Mark step as successful after user input
            step_result.success = True
            self.log_message(f"[yellow]User input completed for step[/yellow]")
            
        elif step_result.requires_input and not self.interactive:
            self.log_message(f"[yellow]⚠[/yellow] Step '{step_name}' requires user input (skipped in non-interactive mode)")
            step_result.success = False
            step_result.error = "User input required but not available in non-interactive mode"
        
        # Log step completion
        if step_result.success:
            self.log_message(f"[green]✓[/green] Completed Step {step_num}: {step_name}")
            self.query_one("#step-info").update(Text(f"✓ Step {step_num}/{self.total_steps}: {step_name}", style="green"))
        else:
            self.log_message(f"[red]✗[/red] Failed Step {step_num}: {step_name} - {step_result.error}")
            self.query_one("#step-info").update(Text(f"✗ Step {step_num}/{self.total_steps}: {step_name}", style="red"))
        
        self.step_results.append(step_result)
        
        # Return success and next_step_id from the step_result
        return step_result.success, step_result.next_step_id
    
    async def handle_user_input(self, step_result: StepResult, step) -> None:
        """Handle user input for interactive steps."""
        if step_result.choices:
            selection_count = step_result.data.get('selection_count', 1)
            is_multiple = selection_count > 1
            
            # Update step info to show we're waiting for user input
            self.query_one("#step-info").update(Text(f"⏳ Waiting for user input: {step.name or step.id}", style="yellow"))
            
            if is_multiple:
                # Handle multiple selections
                self.log_message(f"[cyan]Please select {selection_count} choices:[/cyan]")
                for i, choice in enumerate(step_result.choices, 1):
                    self.log_message(f"  {i}. {choice.label}")
                
                # Create modal for multiple selection
                modal = ChoiceModal(step_result, True, selection_count)
                
                # Push the modal and WAIT for it to complete
                try:
                    selected_choices = await self.push_screen_wait(modal)
                except Exception as e:
                    self.log_message(f"[red]Error in modal: {e}[/red]")
                    return
                
                if selected_choices is None:
                    self.log_message("[yellow]User cancelled selection[/yellow]")
                    return
                
                # Process the selections
                selected_ids = selected_choices if isinstance(selected_choices, list) else [selected_choices]
                
                # Store selections and execute actions
                self.context.set_variable('selected_items', selected_ids)
                self.context.set_variable('user_choices', selected_ids)
                
                if step.actions:
                    for action in step.actions:
                        self.engine._execute_single_action(action, self.context, {'selected_items': selected_ids})
                
                selected_labels = [choice.label for choice in step_result.choices if choice.id in selected_ids]
                self.log_message(f"[green]Selected: {', '.join(selected_labels)}[/green]")
                
            else:
                # Single selection
                self.log_message(f"[cyan]Please select one choice:[/cyan]")
                for i, choice in enumerate(step_result.choices, 1):
                    self.log_message(f"  {i}. {choice.label}")
                
                # Create modal for single selection
                modal = ChoiceModal(step_result, False, 1)
                
                # Push the modal and WAIT for it to complete
                try:
                    selected_choice = await self.push_screen_wait(modal)
                except Exception as e:
                    self.log_message(f"[red]Error in modal: {e}[/red]")
                    return
                
                if selected_choice is None:
                    self.log_message("[yellow]User cancelled selection[/yellow]")
                    return
                
                # Process the choice
                from ..executors.choice_executor import ChoiceExecutor
                choice_executor = ChoiceExecutor()
                choice_result = choice_executor.process_choice(selected_choice, step, self.context)
                
                # Update step result with next_step_id if available
                if choice_result and choice_result.next_step_id:
                    step_result.next_step_id = choice_result.next_step_id
                
                selected_label = next((choice.label for choice in step_result.choices if choice.id == selected_choice), selected_choice)
                self.log_message(f"[green]Selected: {selected_label}[/green]")
            
            # Update step info to show choice was made
            self.query_one("#step-info").update(Text(f"✓ Choice made for: {step.name or step.id}", style="green"))
    
    async def push_screen_wait(self, modal):
        """Push a modal screen and wait for its result."""
        self.log_message(f"[dim]Pushing modal screen...[/dim]")
        # This ensures we properly wait for the modal to complete
        result = await self.push_screen(modal)
        self.log_message(f"[dim]Modal completed with result: {result}[/dim]")
        return result
    
    async def display_results(self) -> None:
        """Display the execution results in tabs."""
        if not self.current_result:
            return
        
        results_tabs = self.query_one("#results-tabs", TabbedContent)
        
        # Clear existing tabs
        results_tabs.clear_panes()
        
        if self.current_result.success:
            self.query_one("#step-info").update(Text("✓ Flow execution completed successfully!", style="bold green"))
            
            # Summary tab
            summary_text = f"""# Flow Execution Complete

**System:** {self.system.name if self.system else 'Unknown'}
**Flow:** {self.flow_obj.name}
**Status:** ✅ Success
**Steps Executed:** {len(self.current_result.step_results)}
**Success Rate:** {sum(1 for sr in self.current_result.step_results if sr.success)}/{len(self.current_result.step_results)}
"""
            summary_pane = TabPane("Summary", Markdown(summary_text), id="summary")
            results_tabs.add_pane(summary_pane)
            
            # Outputs tab
            if self.current_result.outputs:
                outputs_container = Vertical()
                for output_id, output_value in self.current_result.outputs.items():
                    outputs_container.mount(Label(f"{output_id}:", classes="title"))
                    if isinstance(output_value, (dict, list)):
                        outputs_container.mount(Pretty(output_value))
                    else:
                        outputs_container.mount(Static(str(output_value)))
                    outputs_container.mount(Rule())
                outputs_pane = TabPane("Outputs", outputs_container, id="outputs")
                results_tabs.add_pane(outputs_pane)
            
            # Variables tab
            if self.current_result.variables:
                variables_pane = TabPane("Variables", Pretty(self.current_result.variables), id="variables")
                results_tabs.add_pane(variables_pane)
            
        else:
            self.query_one("#step-info").update(Text("✗ Flow execution failed", style="bold red"))
            
            # Error tab
            error_text = f"""# Execution Failed

**Error:** {self.current_result.error or 'Unknown error'}
**Failed at step:** {self.current_result.completed_at_step or 'Unknown'}
**Steps completed:** {len(self.current_result.step_results)}
"""
            error_pane = TabPane("Error", Markdown(error_text), id="error")
            results_tabs.add_pane(error_pane)
        
        # Step details tab
        step_table = DataTable()
        step_table.add_columns("Step", "Status", "Details")
        
        for sr in self.current_result.step_results:
            status = "✅ Success" if sr.success else "❌ Failed"
            details = sr.error if sr.error else "OK"
            step_table.add_row(sr.step_id, status, details)
        
        steps_pane = TabPane("Step Details", step_table, id="steps")
        results_tabs.add_pane(steps_pane)
        
        # Show results section
        self.query_one("#results-section").styles.display = "block"
    
    async def _wait_for_modal_result(self, modal):
        """Wait for modal to provide a result."""
        # Simple approach: check if modal has been dismissed and get result
        while modal.parent is not None:  # Modal is still active
            await asyncio.sleep(0.1)
        return getattr(modal, 'result', None)
    
    def log_message(self, message: str) -> None:
        """Add a message to the execution log."""
        try:
            log_widget = self.query_one("#execution-log", Log)
            log_widget.write_line(message)
        except Exception:
            # Fallback to console if widget not available
            print(message)
    
    def on_unmount(self) -> None:
        """Clean up when the app unmounts."""
        if hasattr(self, 'log_handler'):
            grimoire_logger = logging.getLogger('grimoire_runner')
            grimoire_logger.removeHandler(self.log_handler)
            grimoire_logger.propagate = True
    
    def action_save(self) -> None:
        """Save results to file."""
        if not self.current_result or not self.output_path:
            self.log_message("[yellow]No results to save or output path not specified[/yellow]")
            return
        
        try:
            output_data = {
                'flow_id': self.current_result.flow_id,
                'success': self.current_result.success,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'outputs': self.current_result.outputs,
                'variables': self.current_result.variables,
                'step_results': [
                    {
                        'step_id': sr.step_id,
                        'success': sr.success,
                        'error': sr.error,
                        'data': sr.data
                    }
                    for sr in self.current_result.step_results
                ],
                'execution_summary': {
                    'total_steps': len(self.current_result.step_results),
                    'successful_steps': sum(1 for sr in self.current_result.step_results if sr.success),
                    'failed_steps': sum(1 for sr in self.current_result.step_results if not sr.success)
                }
            }
            
            with open(self.output_path, 'w') as f:
                json.dump(output_data, f, indent=2, default=str)
            
            self.log_message(f"[green]Results saved to: {self.output_path}[/green]")
            
        except Exception as e:
            self.log_message(f"[red]Failed to save results: {str(e)}[/red]")
    
    def action_restart(self) -> None:
        """Restart the flow execution."""
        self.step_results.clear()
        self.current_step = 0
        self.current_result = None
        self.context = self.engine.create_execution_context()
        
        # Reset UI
        self.query_one("#progress").update(progress=0)
        self.query_one("#step-info").update("Restarting...")
        self.query_one("#execution-log", Log).clear()
        self.query_one("#results-section").styles.display = "none"
        
        # Start execution again
        self.call_after_refresh(self.execute_flow)


def run_textual_executor(system_path: Path, flow_id: str, output_path: Optional[Path] = None, interactive: bool = True) -> None:
    """Run the Textual-based flow executor."""
    app = FlowExecutionApp(system_path, flow_id, output_path, interactive)
    app.run()
