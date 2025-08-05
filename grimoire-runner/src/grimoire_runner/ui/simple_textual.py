"""Simple Textual-based flow execution interface."""

import asyncio
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Label,
    Log,
    ProgressBar,
    RadioButton,
    RadioSet,
    Static,
)

from ..core.engine import GrimoireEngine


class SimpleChoiceModal(ModalScreen[str | None]):
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

    def __init__(self, prompt: str, choices: list[Any]):
        super().__init__()
        self.prompt = prompt
        self.choices = choices
        print(
            f"[DEBUG] Modal created with {len(choices)} choices: {[str(c) for c in choices]}"
        )

    def compose(self) -> ComposeResult:
        with Container(classes="modal-container"):
            yield Label("User Input Required", classes="modal-title")
            yield Label(self.prompt)

            with RadioSet(id="choice-set"):
                for i, choice in enumerate(self.choices):
                    label = choice.label if hasattr(choice, "label") else str(choice)
                    choice_id = choice.id if hasattr(choice, "id") else str(choice)
                    print(
                        f"[DEBUG] Adding radio button {i}: label='{label}', id='{choice_id}'"
                    )
                    yield RadioButton(label, id=f"choice-{choice_id}")

            with Horizontal(classes="modal-buttons"):
                yield Button("Confirm", variant="primary", id="confirm")
                yield Button("Cancel", variant="error", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        print(f"[DEBUG] Button pressed: {event.button.id}")
        if event.button.id == "confirm":
            radio_set = self.query_one("#choice-set", RadioSet)
            print(f"[DEBUG] Radio set pressed_button: {radio_set.pressed_button}")
            if radio_set.pressed_button:
                # Extract choice ID from button ID (format: "choice-{choice_id}")
                button_id = radio_set.pressed_button.id
                if button_id and button_id.startswith("choice-"):
                    selected_value = button_id[7:]  # Remove "choice-" prefix
                    print(f"[DEBUG] Dismissing with value: {selected_value}")
                    self.dismiss(selected_value)
                else:
                    print(f"[DEBUG] Invalid button ID format: {button_id}")
            else:
                print("[DEBUG] No radio button selected, staying open")
                # User clicked confirm without selecting anything - keep modal open
                pass
        elif event.button.id == "cancel":
            print("[DEBUG] Dismissing with None (cancelled)")
            self.dismiss(None)

    def on_unmount(self) -> None:
        print("[DEBUG] Modal unmounted")


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
            self.write_log("Loading system...")

            # Load system
            self.system = self.engine.load_system(self.system_path)
            self.flow_obj = self.system.get_flow(self.flow_id)

            if not self.flow_obj:
                self.write_log("ERROR: Flow not found!")
                return

            # Update UI
            self.query_one("#system-info").update(f"System: {self.system.name}")
            self.query_one("#flow-info").update(
                f"Flow: {self.flow_obj.name} ({len(self.flow_obj.steps)} steps)"
            )
            self.total_steps = len(self.flow_obj.steps)

            # Initialize context
            self.context = self.engine.create_execution_context()

            # Set system metadata in context for templating
            self.context.system_metadata = {
                "id": self.system.id,
                "name": self.system.name,
                "description": self.system.description,
                "version": self.system.version,
                "currency": getattr(self.system, "currency", {}),
                "credits": getattr(self.system, "credits", {}),
            }

            # Initialize flow variables
            for var_name, var_value in self.flow_obj.variables.items():
                self.context.set_variable(var_name, var_value)

            # Initialize observable derived fields from output models
            for output_def in self.flow_obj.outputs:
                if output_def.type in self.system.models:
                    model = self.system.models[output_def.type]
                    self.write_log(
                        f"Initializing model observables for {output_def.type} ({output_def.id})"
                    )
                    self.context.initialize_model_observables(model, output_def.id)

            # Execute flow step by step
            await self.execute_flow_steps()

        except Exception as e:
            self.write_log(f"ERROR: {str(e)}")

    async def execute_flow_steps(self) -> None:
        """Execute flow steps one by one."""
        current_step_id = self.flow_obj.steps[0].id if self.flow_obj.steps else None
        step_num = 0

        while current_step_id:
            step = self.flow_obj.get_step(current_step_id)
            if not step:
                self.write_log(f"ERROR: Step not found: {current_step_id}")
                break

            step_num += 1

            # Update progress
            progress = (step_num / self.total_steps) * 100
            self.query_one("#progress").update(progress=progress)
            self.query_one("#status").update(
                f"Step {step_num}/{self.total_steps}: {step.name or step.id}"
            )

            self.write_log(f"▶ Starting step {step_num}: {step.name or step.id}")

            # Update context
            self.context.current_step = current_step_id
            self.context.step_history.append(current_step_id)

            # Execute step
            try:
                success, next_step_id = await self.execute_single_step(step, step_num)

                if not success:
                    self.write_log("❌ Flow execution stopped due to step failure")
                    break

                # Determine next step
                if next_step_id:
                    current_step_id = next_step_id
                else:
                    current_step_id = self.flow_obj.get_next_step_id(current_step_id)

            except Exception as e:
                self.write_log(f"ERROR in step {current_step_id}: {str(e)}")
                break

            # Small delay
            await asyncio.sleep(0.5)

        self.write_log("✅ Flow execution completed!")
        self.query_one("#status").update("Flow completed")

    async def execute_single_step(self, step, step_num: int) -> tuple[bool, str | None]:
        """Execute a single step."""
        # Execute the step through the engine
        step_result = self.engine._execute_step(step, self.context, self.system)

        self.write_log(
            f"Step result: requires_input={step_result.requires_input}, success={step_result.success}"
        )

        # Handle user input if needed
        if step_result.requires_input:
            self.write_log("⏳ Step requires user input...")
            self.write_log(
                f"DEBUG: step_result.requires_input={step_result.requires_input}, step.type={step.type}"
            )

            if step_result.choices:
                # Show choice modal
                prompt = step_result.prompt or "Please make a choice:"
                modal = SimpleChoiceModal(prompt, step_result.choices)

                self.write_log(f"Showing modal with {len(step_result.choices)} choices")

                # Use callback pattern with asyncio.Event for synchronization
                selected_choice = await self._show_modal_and_wait(modal)

                self.write_log(f"Modal returned: {selected_choice}")

                if selected_choice is None:
                    self.write_log("❌ User cancelled input")
                    step_result.success = False
                    step_result.error = "User cancelled input"
                else:
                    self.write_log(f"✅ User selected: {selected_choice}")

                    # Process the choice
                    from ..executors.choice_executor import ChoiceExecutor

                    self.write_log(
                        "DEBUG: About to process choice with choice_executor"
                    )
                    choice_executor = ChoiceExecutor()
                    choice_result = choice_executor.process_choice(
                        selected_choice, step, self.context
                    )
                    self.write_log(f"DEBUG: choice_result = {choice_result}")

                    if choice_result and choice_result.next_step_id:
                        step_result.next_step_id = choice_result.next_step_id

                    step_result.success = True

                    # Execute step-level actions after choice is processed
                    self.write_log(f"DEBUG: step.actions = {step.actions}")
                    if step.actions:
                        self.write_log(
                            f"Executing {len(step.actions)} step actions after choice"
                        )
                        try:
                            self.engine._execute_actions(
                                step.actions,
                                self.context,
                                choice_result.data if choice_result else {},
                                self.system,
                            )
                            self.write_log("✅ Step actions executed successfully")
                        except Exception as e:
                            self.write_log(f"❌ Error executing step actions: {e}")
                            step_result.success = False
                            step_result.error = f"Step action execution failed: {e}"
                    else:
                        self.write_log("DEBUG: No step actions to execute")

        # Log completion
        if step_result.success:
            self.write_log(f"✅ Completed Step {step_num}")
        else:
            self.write_log(f"❌ Failed Step {step_num}: {step_result.error}")

        self.step_results.append(step_result)
        return step_result.success, step_result.next_step_id

    async def _show_modal_and_wait(self, modal: SimpleChoiceModal) -> str | None:
        """Show modal and wait for result using callback pattern."""
        # Create an asyncio Event to wait for the result
        result_event = asyncio.Event()
        modal_result = None

        def handle_modal_result(result):
            nonlocal modal_result
            modal_result = result
            result_event.set()

        # Show modal with callback
        self.push_screen(modal, handle_modal_result)

        # Wait for the result
        await result_event.wait()

        return modal_result

    def write_log(self, message: str) -> None:
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
