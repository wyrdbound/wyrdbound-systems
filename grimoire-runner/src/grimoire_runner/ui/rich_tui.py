"""Rich-based TUI for step-by-step flow execution with accessibility in mind."""

import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..core.engine import GrimoireEngine
from ..executors.choice_executor import ChoiceExecutor


class RichTUI:
    """Rich-based TUI for accessible step-by-step flow execution."""

    def __init__(self, system_path: Path, flow_id: str):
        self.system_path = system_path
        self.flow_id = flow_id
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

        # Initialize flow variables
        for var_name, var_value in self.flow_obj.variables.items():
            self.context.set_variable(var_name, var_value)

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

        # Progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=self.console,
            transient=False,
        ) as progress:
            task = progress.add_task("Executing flow...", total=total_steps)

            while current_step_id:
                step = self.flow_obj.get_step(current_step_id)
                if not step:
                    self.console.print(
                        f"[red]Error: Step not found: {current_step_id}[/red]"
                    )
                    break

                step_num += 1

                # Update progress
                progress.update(
                    task,
                    completed=step_num - 1,
                    description=f"Step {step_num}/{total_steps}: {step.name or step.id}",
                )

                # Show step header
                self.console.print()
                step_description = getattr(step, "description", None) or ""
                description_text = (
                    f"\n[dim]Description: {step_description}[/dim]"
                    if step_description
                    else ""
                )

                self.console.print(
                    Panel(
                        f"[bold]Step {step_num}: {step.name or step.id}[/bold]\n"
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
                        current_step_id = self.flow_obj.get_next_step_id(
                            current_step_id
                        )

                except Exception as e:
                    self.console.print(
                        f"[red]Error in step {current_step_id}: {str(e)}[/red]"
                    )
                    break

                # Small delay for readability
                time.sleep(0.5)

            # Final progress update
            progress.update(task, completed=total_steps, description="Flow completed")

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
                selected_choice = self._handle_choice_input(step_result)

                if selected_choice is None:
                    self.console.print("[red]❌ Input cancelled[/red]")
                    step_result.success = False
                    step_result.error = "User cancelled input"
                else:
                    self.console.print(f"[green]✅ Selected: {selected_choice}[/green]")

                    # Process the choice
                    choice_executor = ChoiceExecutor()
                    choice_result = choice_executor.process_choice(
                        selected_choice, step, self.context
                    )

                    if choice_result and choice_result.next_step_id:
                        step_result.next_step_id = choice_result.next_step_id

                    step_result.success = True

        # Show step result
        if step_result.success:
            self.console.print(f"[green]✅ Completed step {step_num}[/green]")
        else:
            self.console.print(
                f"[red]❌ Failed step {step_num}: {step_result.error}[/red]"
            )

        self.step_results.append(step_result)
        return step_result.success, step_result.next_step_id

    def _handle_choice_input(self, step_result) -> str | None:
        """Handle user choice input using Rich prompts."""
        choices = step_result.choices
        prompt_text = step_result.prompt or "Please make a choice:"

        # Display choices in a table for better accessibility
        choices_table = Table(title="Available Choices", show_header=True)
        choices_table.add_column("Option", style="cyan", justify="right")
        choices_table.add_column("Choice", style="green")
        choices_table.add_column("Description", style="dim")

        choice_map = {}
        for i, choice in enumerate(choices, 1):
            label = choice.label if hasattr(choice, "label") else str(choice)
            choice_id = choice.id if hasattr(choice, "id") else str(choice)
            description = getattr(choice, "description", "") or ""

            choices_table.add_row(str(i), label, description)
            choice_map[str(i)] = choice_id

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


def run_rich_tui_executor(system_path: Path, flow_id: str) -> None:
    """Run the Rich TUI executor."""
    tui = RichTUI(system_path, flow_id)
    tui.run()
