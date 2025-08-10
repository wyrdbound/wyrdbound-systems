"""Rich-based TUI for step-by-step flow execution with accessibility in mind."""

import logging
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..core.engine import GrimoireEngine
from ..executors.choice_executor import ChoiceExecutor

logger = logging.getLogger(__name__)


class RichTUI:
    """Rich-based TUI for accessible step-by-step flow execution."""

    def __init__(self, system_path: Path, flow_id: str, input_values: dict = None):
        self.system_path = system_path
        self.flow_id = flow_id
        self.input_values = input_values or {}
        self.console = Console()
        self.engine = GrimoireEngine()
        self.system = None
        self.flow_obj = None
        self.context = None
        self.step_results = []

    def run(self) -> None:
        """Run the Rich TUI interface."""
        try:
            self._initialize()
            self._execute_flow()
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def _initialize(self) -> None:
        """Initialize the system and flow."""
        # Header
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]GRIMOIRE Flow Execution[/bold cyan]\n"
                f"[dim]System: {self.system_path.name}[/dim]\n"
                f"[dim]Flow: {self.flow_id}[/dim]",
                border_style="cyan",
            )
        )

        # Load system
        with self.console.status("[bold blue]Loading system...", spinner="dots"):
            self.system = self.engine.load_system(self.system_path)

        # Get flow
        self.flow_obj = self.system.get_flow(self.flow_id)
        if not self.flow_obj:
            available_flows = list(self.system.flows.keys())
            raise ValueError(
                f"Flow '{self.flow_id}' not found. Available flows: {available_flows}"
            )

        # Create execution context
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

        # Initialize input values if provided
        if self.input_values:
            self.console.print(f"[dim]Setting input values:[/dim]")
            for input_name, input_value in self.input_values.items():
                self.context.set_input(input_name, input_value)
                self.console.print(f"  [cyan]{input_name}[/cyan] = [yellow]{input_value}[/yellow]")

        # Initialize observable derived fields from output models
        for output_def in self.flow_obj.outputs:
            if output_def.type in self.system.models:
                model = self.system.models[output_def.type]
                logger.info(
                    f"Rich TUI: Initializing model observables for {output_def.type} ({output_def.id})"
                )
                self.context.initialize_model_observables(model, output_def.id)

        # Show flow info
        self._show_flow_info()

    def _show_flow_info(self) -> None:
        """Display flow information."""
        info_table = Table(title="Flow Information", show_header=False)
        info_table.add_column("Property", style="cyan")
        info_table.add_column("Value", style="green")

        info_table.add_row("Name", self.flow_obj.name or self.flow_id)
        if self.flow_obj.description:
            info_table.add_row("Description", self.flow_obj.description)
        info_table.add_row("Steps", str(len(self.flow_obj.steps)))

        self.console.print()
        self.console.print(info_table)
        self.console.print()

        # Ask for confirmation to proceed
        try:
            if not Confirm.ask("Ready to start flow execution?", default=True):
                self.console.print("[yellow]Flow execution cancelled.[/yellow]")
                return
        except (EOFError, KeyboardInterrupt):
            # Handle piped input or Ctrl+C gracefully
            self.console.print("[yellow]Starting flow execution...[/yellow]")

    def _execute_flow(self) -> None:
        """Execute the flow step by step."""
        current_step_id = self.flow_obj.steps[0].id if self.flow_obj.steps else None
        step_num = 0
        total_steps = len(self.flow_obj.steps)

        # Simple progress tracking without Rich Progress widget to avoid line conflicts
        self.console.print("[bold cyan]Starting flow execution...[/bold cyan]")
        self.console.print()

        while current_step_id:
            step = self.flow_obj.get_step(current_step_id)
            if not step:
                self.console.print(
                    f"[red]Error: Step not found: {current_step_id}[/red]"
                )
                break

            step_num += 1

            # Show step header with progress info
            progress_text = f"[bold cyan]Step {step_num}/{total_steps}[/bold cyan]"
            step_description = getattr(step, "description", None) or ""
            description_text = (
                f"\n[dim]Description: {step_description}[/dim]"
                if step_description
                else ""
            )

            self.console.print(
                Panel(
                    f"{progress_text}: [bold]{step.name or step.id}[/bold]\n"
                    f"[dim]Type: {step.type}[/dim]" + description_text,
                    border_style="blue",
                    title="Current Step",
                )
            )

            # Update context
            self.context.current_step = current_step_id
            self.context.step_history.append(current_step_id)

            # Execute step
            try:
                success, next_step_id = self._execute_single_step(step, step_num)

                if not success:
                    self.console.print(
                        "[red]❌ Flow execution stopped due to step failure[/red]"
                    )
                    break

                # Determine next step
                if next_step_id:
                    current_step_id = next_step_id
                else:
                    current_step_id = self.flow_obj.get_next_step_id(current_step_id)

            except Exception as e:
                self.console.print(
                    f"[red]Error in step {current_step_id}: {str(e)}[/red]"
                )
                break

            # Small delay for readability
            time.sleep(0.5)

        # Final completion message
        self.console.print()
        self.console.print(
            Panel(
                "[bold green]✅ Flow execution completed![/bold green]",
                border_style="green",
            )
        )
        self._show_results_summary()

    def _execute_single_step(self, step, step_num: int) -> tuple[bool, str | None]:
        """Execute a single step."""
        # Execute the step through the engine
        step_result = self.engine._execute_step(step, self.context, self.system)

        # Handle user input if needed
        if step_result.requires_input:
            self.console.print("[yellow]⏳ This step requires your input...[/yellow]")

            if step_result.choices:
                # Handle choices using Rich prompts
                selected_choice_result = self._handle_choice_input(step_result)

                if selected_choice_result is None:
                    self.console.print("[red]❌ Input cancelled[/red]")
                    step_result.success = False
                    step_result.error = "User cancelled input"
                else:
                    # Extract choice ID and label from result
                    if isinstance(selected_choice_result, tuple):
                        selected_choice_id, selected_choice_label = (
                            selected_choice_result
                        )
                    else:
                        # Backward compatibility - just the ID
                        selected_choice_id = selected_choice_result
                        selected_choice_label = selected_choice_result

                    # Only show selection confirmation for single choices
                    # Multi-selection already shows "Final Selections" summary
                    selection_count = (
                        step_result.data.get("selection_count", 1)
                        if step_result.data
                        else 1
                    )
                    if selection_count == 1:
                        self.console.print(
                            f"[green]✅ Selected: {selected_choice_label}[/green]"
                        )

                    # Process the choice
                    choice_executor = ChoiceExecutor()

                    # For choice_source cases, we need to use the generated choices from step_result
                    # rather than the original step definition
                    if step.choice_source and step_result.choices:
                        # Find the selected choice in the step result's generated choices
                        selected_choice = None
                        for choice in step_result.choices:
                            if choice.id == selected_choice_id:
                                selected_choice = choice
                                break

                        if selected_choice and selected_choice.actions:
                            # Execute the choice actions directly since process_choice won't find them in step.choices
                            for action in selected_choice.actions:
                                choice_executor._execute_choice_action(
                                    action, self.context
                                )

                            # Set standard choice variables
                            self.context.set_variable("user_choice", selected_choice_id)
                            self.context.set_variable(
                                "choice_label", selected_choice.label
                            )

                            choice_result = type(
                                "StepResult",
                                (),
                                {
                                    "step_id": step.id,
                                    "success": True,
                                    "data": {
                                        "choice_id": selected_choice_id,
                                        "choice_label": selected_choice.label,
                                    },
                                    "next_step_id": selected_choice.next_step,
                                },
                            )()
                        else:
                            choice_result = choice_executor.process_choice(
                                selected_choice_id, step, self.context
                            )
                    else:
                        choice_result = choice_executor.process_choice(
                            selected_choice_id, step, self.context
                        )

                    if choice_result and choice_result.next_step_id:
                        step_result.next_step_id = choice_result.next_step_id

                    step_result.success = True

                    # Execute step-level actions after choice is processed
                    if step.actions:
                        self.console.print(
                            f"[cyan]Executing {len(step.actions)} step actions after choice...[/cyan]"
                        )
                        try:
                            self.engine.action_executor.execute_actions(
                                step.actions,
                                self.context,
                                choice_result.data if choice_result else {},
                                self.system,
                            )
                            self.console.print(
                                "[green]✅ Step actions executed successfully[/green]"
                            )
                        except Exception as e:
                            self.console.print(
                                f"[red]❌ Error executing step actions: {e}[/red]"
                            )
                            step_result.success = False
                            step_result.error = f"Step action execution failed: {e}"

            else:
                # Handle player input (text input)
                user_input = self._handle_player_input(step_result)

                if user_input is None:
                    self.console.print("[red]❌ Input cancelled[/red]")
                    step_result.success = False
                    step_result.error = "User cancelled input"
                else:
                    self.console.print(
                        f"[green]✅ Input received: {user_input}[/green]"
                    )

                    # Process the input using PlayerInputExecutor
                    from ..executors.player_input_executor import PlayerInputExecutor

                    input_executor = PlayerInputExecutor()
                    input_result = input_executor.process_input(
                        user_input, step, self.context, self.system
                    )

                    if input_result.success:
                        step_result.success = True
                        step_result.data = input_result.data
                    else:
                        step_result.success = False
                        step_result.error = input_result.error

        # Show step result
        if step_result.success:
            self.console.print(f"[green]✅ Completed Step {step_num}[/green]")
        else:
            self.console.print(
                f"[red]❌ Failed Step {step_num}: {step_result.error}[/red]"
            )

        self.step_results.append(step_result)
        return step_result.success, step_result.next_step_id

    def _handle_choice_input(self, step_result) -> tuple[str, str] | None:
        """Handle user choice input using Rich prompts."""
        choices = step_result.choices
        prompt_text = step_result.prompt or "Please make a choice:"

        # Check if this requires multiple selections
        selection_count = (
            step_result.data.get("selection_count", 1) if step_result.data else 1
        )

        if selection_count > 1:
            return self._handle_multiple_choice_input(
                step_result, choices, prompt_text, selection_count
            )
        else:
            return self._handle_single_choice_input(choices, prompt_text)

    def _handle_single_choice_input(
        self, choices, prompt_text
    ) -> tuple[str, str] | None:
        """Handle single choice input."""
        # Check if any choices have descriptions
        has_descriptions = any(getattr(choice, "description", "") for choice in choices)

        # Display choices in a table for better accessibility
        choices_table = Table(title="Available Choices", show_header=True)
        choices_table.add_column("Option", style="cyan", justify="right")
        choices_table.add_column("Choice", style="green")

        # Only add description column if at least one choice has a description
        if has_descriptions:
            choices_table.add_column("Description", style="dim")

        choice_map = {}
        for i, choice in enumerate(choices, 1):
            label = choice.label if hasattr(choice, "label") else str(choice)
            choice_id = choice.id if hasattr(choice, "id") else str(choice)
            description = getattr(choice, "description", "") or ""

            if has_descriptions:
                choices_table.add_row(str(i), label, description)
            else:
                choices_table.add_row(str(i), label)
            choice_map[str(i)] = (choice_id, label)

        self.console.print()
        self.console.print(choices_table)
        self.console.print()

        # Create choices text for prompt
        choices_text = " / ".join([f"{i}" for i in choice_map.keys()])

        while True:
            try:
                # Use Rich.prompt for accessible input
                response = Prompt.ask(
                    f"{prompt_text}\nEnter your choice ({choices_text}) or 'q' to quit",
                    console=self.console,
                )

                if response.lower() == "q":
                    return None

                if response in choice_map:
                    return choice_map[response]
                else:
                    self.console.print(
                        f"[red]Invalid choice. Please enter one of: {choices_text}[/red]"
                    )

            except (KeyboardInterrupt, EOFError):
                # Handle automated input or interruption gracefully
                self.console.print("[yellow]Using default choice (1)[/yellow]")
                if "1" in choice_map:
                    return choice_map["1"]
                return None

    def _handle_multiple_choice_input(
        self, step_result, choices, prompt_text, selection_count
    ) -> tuple[str, str] | None:
        """Handle multiple choice selection (like ability swapping)."""
        selected_choices = []
        selected_ids = []
        selected_labels = []
        available_choices = choices.copy()  # Make a copy

        try:
            for selection_num in range(selection_count):
                self.console.print(
                    f"\n[bold cyan]Selection {selection_num + 1} of {selection_count}:[/bold cyan]"
                )

                # Check if any remaining choices have descriptions
                has_descriptions = any(
                    getattr(choice, "description", "") for choice in available_choices
                )

                # Show remaining choices
                choices_table = Table(show_header=True, header_style="bold magenta")
                choices_table.add_column("Option", style="cyan", justify="right")
                choices_table.add_column("Choice", style="green")

                # Only add description column if at least one choice has a description
                if has_descriptions:
                    choices_table.add_column("Description", style="dim")

                choice_map = {}
                for i, choice in enumerate(available_choices, 1):
                    label = choice.label if hasattr(choice, "label") else str(choice)
                    choice_id = choice.id if hasattr(choice, "id") else str(choice)
                    description = getattr(choice, "description", "") or ""

                    if has_descriptions:
                        choices_table.add_row(str(i), label, description)
                    else:
                        choices_table.add_row(str(i), label)
                    choice_map[str(i)] = (choice_id, choice)

                self.console.print(choices_table)

                # Show previously selected items
                if selected_choices:
                    selected_labels = [
                        c.label if hasattr(c, "label") else str(c)
                        for c in selected_choices
                    ]
                    self.console.print(
                        f"\n[dim]Already selected: {', '.join(selected_labels)}[/dim]"
                    )

                self.console.print()

                # Create choices text for prompt
                choices_text = " / ".join(
                    [str(i) for i in range(1, len(available_choices) + 1)]
                )

                while True:
                    try:
                        response = Prompt.ask(
                            f"Enter choice number for selection {selection_num + 1} ({choices_text}) or 'q' to quit",
                            console=self.console,
                        )

                        if response.lower() == "q":
                            return None

                        if response in choice_map:
                            choice_id, choice_obj = choice_map[response]
                            selected_choices.append(choice_obj)
                            selected_ids.append(choice_id)

                            choice_label = (
                                choice_obj.label
                                if hasattr(choice_obj, "label")
                                else str(choice_obj)
                            )
                            selected_labels.append(choice_label)
                            self.console.print(
                                f"[green]✅ Selected: {choice_label}[/green]"
                            )

                            # Remove the selected choice from available choices
                            available_choices.remove(choice_obj)
                            break
                        else:
                            self.console.print(
                                f"[red]Invalid choice number. Please choose from: {choices_text}[/red]"
                            )

                    except (KeyboardInterrupt, EOFError):
                        # Handle automated input gracefully
                        if choice_map:
                            # Use first available choice
                            choice_id, choice_obj = choice_map["1"]
                            selected_choices.append(choice_obj)
                            selected_ids.append(choice_id)
                            choice_label = (
                                choice_obj.label
                                if hasattr(choice_obj, "label")
                                else str(choice_obj)
                            )
                            selected_labels.append(choice_label)
                            self.console.print(
                                f"[yellow]Using default choice: {choice_label}[/yellow]"
                            )
                            available_choices.remove(choice_obj)
                            break
                        else:
                            return None

            # Show final selection summary
            self.console.print("\n[bold green]Final Selections:[/bold green]")
            for i, choice in enumerate(selected_choices, 1):
                choice_label = choice.label if hasattr(choice, "label") else str(choice)
                self.console.print(f"  {i}. {choice_label}")

            # Store the multiple selections in context (like the original console interface)
            self.context.set_variable("selected_items", selected_ids)
            self.context.set_variable("user_choices", selected_ids)  # Alternative name

            # Return the first selection ID and label (for compatibility)
            if selected_ids and selected_labels:
                return (selected_ids[0], selected_labels[0])
            else:
                return None

        except Exception as e:
            self.console.print(f"[red]Error during selection: {e}[/red]")
            self.console.print("[yellow]Continuing with default behavior...[/yellow]")
            # Fall back to empty selection
            self.context.set_variable("selected_items", [])
            self.context.set_variable("user_choices", [])
            return None

    def _handle_player_input(self, step_result) -> str | None:
        """Handle player text input using Rich prompts."""
        prompt_text = step_result.prompt or "Please enter your input:"

        try:
            # Use Rich.prompt for accessible text input
            user_input = Prompt.ask(prompt_text, console=self.console)
            return user_input.strip() if user_input else None

        except (KeyboardInterrupt, EOFError):
            # Handle automated input or interruption gracefully
            try:
                import sys

                if not sys.stdin.isatty():
                    # We're reading from a pipe/redirect, try to read one line
                    line = sys.stdin.readline()
                    if line:
                        self.console.print(
                            f"[yellow]Using piped input: {line.strip()}[/yellow]"
                        )
                        return line.strip()
            except (EOFError, OSError, UnicodeDecodeError):
                pass

            self.console.print("[yellow]Input cancelled or unavailable[/yellow]")
            return None

    def _show_results_summary(self) -> None:
        """Show a summary of the execution results."""
        if not self.step_results:
            return

        summary_table = Table(title="Execution Summary", show_header=True)
        summary_table.add_column("Step", style="cyan")
        summary_table.add_column("Status", style="green")
        summary_table.add_column("Details", style="dim")

        for i, result in enumerate(self.step_results, 1):
            status = "✅ Success" if result.success else "❌ Failed"
            details = result.error if not result.success else ""
            summary_table.add_row(str(i), status, details)

        self.console.print()
        self.console.print(summary_table)


def run_rich_tui_executor(system_path: Path, flow_id: str, input_values: dict = None) -> None:
    """Run the Rich TUI executor."""
    tui = RichTUI(system_path, flow_id, input_values)
    tui.run()
