"""Rich-based TUI for step-by-step flow execution with accessibility in mind."""

import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from ..core.engine import GrimoireEngine
from ..executors.choice_executor import ChoiceExecutor
from ..models.flow import StepType

logger = logging.getLogger(__name__)

# Step type emoji constants
STEP_TYPE_EMOJIS = {
    StepType.DICE_ROLL: "🎲",
    StepType.DICE_SEQUENCE: "🎲",
    StepType.PLAYER_CHOICE: "🤔",
    StepType.PLAYER_INPUT: "⌨️",
    StepType.TABLE_ROLL: "📋",
    StepType.LLM_GENERATION: "🤖",
    StepType.COMPLETION: "✅",
    StepType.FLOW_CALL: "🔗",
    StepType.CONDITIONAL: "🔀",
}


def get_step_start_message(step_type: StepType, step_prompt: str = None) -> str:
    """Get start message for a step type, prioritizing custom prompt."""
    emoji = STEP_TYPE_EMOJIS.get(step_type, "⚙️")

    if step_prompt:
        return f"{emoji} {step_prompt}"

    messages = {
        StepType.DICE_ROLL: "Rolling dice...",
        StepType.DICE_SEQUENCE: "Rolling dice sequence...",
        StepType.PLAYER_CHOICE: "Presenting choices to player...",
        StepType.PLAYER_INPUT: "Requesting player input...",
        StepType.TABLE_ROLL: "Rolling on table...",
        StepType.LLM_GENERATION: "Generating content...",
        StepType.COMPLETION: "Completing flow...",
        StepType.FLOW_CALL: "Calling sub-flow...",
        StepType.CONDITIONAL: "Evaluating conditions...",
    }

    message = messages.get(step_type, "Executing step...")
    return f"{emoji} {message}"


def get_step_success_message(step_type: StepType, custom_message: str = None) -> str:
    """Get success message for a step type, with optional custom message."""
    emoji = STEP_TYPE_EMOJIS.get(step_type, "⚙️")

    if custom_message:
        return f"{emoji} {custom_message}"

    # Default messages (without emoji since we'll prepend it)
    default_messages = {
        StepType.DICE_ROLL: "Dice rolled successfully",
        StepType.DICE_SEQUENCE: "Dice sequence completed",
        StepType.PLAYER_CHOICE: "Choice processed",
        StepType.PLAYER_INPUT: "Input processed",
        StepType.TABLE_ROLL: "Table roll completed",
        StepType.LLM_GENERATION: "Content generated",
        StepType.COMPLETION: "Flow completed",
        StepType.FLOW_CALL: "Sub-flow completed",
        StepType.CONDITIONAL: "Conditions evaluated",
    }

    default_message = default_messages.get(step_type, "Step completed successfully")
    return f"{emoji} {default_message}"


def get_step_failure_message(step_type: StepType) -> str:
    """Get generic failure message for a step type."""
    emoji = STEP_TYPE_EMOJIS.get(step_type, "⚙️")

    failure_messages = {
        StepType.DICE_ROLL: "Dice roll failed",
        StepType.DICE_SEQUENCE: "Dice sequence failed",
        StepType.PLAYER_CHOICE: "Choice processing failed",
        StepType.PLAYER_INPUT: "Input processing failed",
        StepType.TABLE_ROLL: "Table roll failed",
        StepType.LLM_GENERATION: "Content generation failed",
        StepType.COMPLETION: "Flow completion failed",
        StepType.FLOW_CALL: "Sub-flow failed",
        StepType.CONDITIONAL: "Condition evaluation failed",
    }

    message = failure_messages.get(step_type, "Step failed")
    return f"{emoji} {message}"


class RichTUI:
    """Rich-based TUI for accessible step-by-step flow execution."""

    def __init__(
        self,
        system_path: Path = None,
        flow_id: str = None,
        input_values: dict = None,
        interactive: bool = True,
        indent_level: int = 0,  # Add indentation for nested flows
        parent_tui: "RichTUI" = None,  # Reference to parent TUI for nested flows
        engine: "GrimoireEngine" = None,  # For nested TUI creation
        console: Console = None,  # For nested TUI creation
    ):
        # Support both original constructor and nested constructor
        if engine is not None and console is not None:
            # Nested TUI constructor
            self.engine = engine
            self.console = console
            self.system_path = None
            self.flow_id = None
            self.input_values = {}
        else:
            # Original constructor
            self.system_path = system_path
            self.flow_id = flow_id
            self.input_values = input_values or {}
            self.console = Console() if parent_tui is None else parent_tui.console
            self.engine = GrimoireEngine()

        self.interactive = interactive
        self.indent_level = indent_level
        self.parent_tui = parent_tui
        self.system = None
        self.flow_obj = None
        self.context = None
        self.step_results = []

    def _get_indent(self) -> str:
        """Get indentation string based on nesting level."""
        return "  " * self.indent_level

    def _print_indented(self, message: str, style: str = None) -> None:
        """Print a message with appropriate indentation."""
        indent = self._get_indent()
        if style:
            self.console.print(f"{indent}{message}", style=style)
        else:
            self.console.print(f"{indent}{message}")

    def _create_indented_panel(
        self, content: str, title: str = None, border_style: str = "blue"
    ) -> Panel:
        """Create a panel with indented content."""
        indent = self._get_indent()
        indented_content = "\n".join(f"{indent}{line}" for line in content.split("\n"))
        return Panel(
            indented_content,
            title=f"{self._get_indent()}{title}" if title else None,
            border_style=border_style,
        )

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
        if self.flow_obj.variables:
            for variable in self.flow_obj.variables:
                self.context.set_variable(variable.id, variable.default)

        # Initialize input values if provided
        if self.input_values:
            self.console.print("[dim]Setting input values:[/dim]")
            for input_name, input_value in self.input_values.items():
                self.context.set_input(input_name, input_value)
                self.console.print(
                    f"  [cyan]{input_name}[/cyan] = [yellow]{input_value}[/yellow]"
                )

        # Initialize observable derived fields from output models
        for output_def in self.flow_obj.outputs:
            if output_def.type in self.system.models:
                model = self.system.models[output_def.type]
                logger.debug(
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

            # Show compact step header
            step_name = step.name or step.id
            step_type = step.type.name if hasattr(step.type, "name") else str(step.type)
            self.console.print(
                f"[bold cyan]Step {step_num}/{total_steps}:[/bold cyan] [bold]{step_name}[/bold] [dim]({step_type})[/dim]"
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

        # Final completion message
        self.console.print()
        self.console.print("[bold green]✅ Flow execution completed![/bold green]")
        self._show_results_summary()

    def execute_flow(self, flow_obj, context, system) -> bool:
        """Execute a flow with the given context and system. Used for nested flow execution."""
        self.flow_obj = flow_obj
        self.context = context
        self.system = system
        self.step_results = []

        current_step_id = self.flow_obj.steps[0].id if self.flow_obj.steps else None
        step_num = 0

        while current_step_id:
            step = self.flow_obj.get_step(current_step_id)
            if not step:
                self._print_indented(
                    f"[red]Error: Step not found: {current_step_id}[/red]"
                )
                return False

            step_num += 1

            # Show compact sub-flow step header with proper indentation
            step_name = step.name or step.id
            step_type = step.type.name if hasattr(step.type, "name") else str(step.type)
            self._print_indented(
                f"[cyan]Step {step_num}/{len(self.flow_obj.steps)}:[/cyan] [bold]{step_name}[/bold] [dim]({step_type})[/dim]"
            )

            # Update context
            self.context.current_step = current_step_id
            self.context.step_history.append(current_step_id)

            # Execute step
            try:
                success, next_step_id = self._execute_single_step(step, step_num)

                if not success:
                    self._print_indented(
                        "[red]❌ Sub-flow execution stopped due to step failure[/red]"
                    )
                    return False

                # Determine next step
                if next_step_id:
                    current_step_id = next_step_id
                else:
                    current_step_id = self.flow_obj.get_next_step_id(current_step_id)

            except Exception as e:
                self._print_indented(
                    f"[red]Error in step {current_step_id}: {str(e)}[/red]"
                )
                return False

        # Success completion
        self._print_indented("[green]✅ Sub-flow completed successfully[/green]")
        return True

    def _execute_single_step(self, step, step_num: int) -> tuple[bool, str | None]:
        """Execute a single step."""
        # Special handling for flow_call steps to show sub-flow execution
        if step.type == StepType.FLOW_CALL:
            return self._execute_flow_call_step(step, step_num)

        # Show generic start message for step type (more compact)
        start_message = get_step_start_message(step.type, step.prompt)
        self._print_indented(f"{start_message}")

        # Execute the step through the engine
        step_result = self.engine._execute_step(step, self.context, self.system)

        # Handle user input if needed
        if step_result.requires_input:
            self._print_indented("[yellow]⏳ This step requires your input...[/yellow]")

            if step_result.choices:
                # Handle choices using Rich prompts
                selected_choice_result = self._handle_choice_input(step_result)

                if selected_choice_result is None:
                    self._print_indented("[red]❌ Input cancelled[/red]")
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
                        self._print_indented(
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
                        self._print_indented(
                            f"[cyan]Executing {len(step.actions)} step actions after choice...[/cyan]"
                        )
                        try:
                            self.engine.action_executor.execute_actions(
                                step.actions,
                                self.context,
                                choice_result.data if choice_result else {},
                                self.system,
                            )
                            self._print_indented(
                                "[green]✅ Step actions executed successfully[/green]"
                            )
                        except Exception as e:
                            self._print_indented(
                                f"[red]❌ Error executing step actions: {e}[/red]"
                            )
                            step_result.success = False
                            step_result.error = f"Step action execution failed: {e}"

            else:
                # Handle player input (text input)
                user_input = self._handle_player_input(step_result)

                if user_input is None:
                    self._print_indented("[red]❌ Input cancelled[/red]")
                    step_result.success = False
                    step_result.error = "User cancelled input"
                else:
                    self._print_indented(
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

        # Show step result with custom or generic messages
        if step_result.success:
            # Display any action messages that were generated during step execution
            action_messages = self.context.get_and_clear_action_messages()
            for action_message in action_messages:
                self._print_indented(f"[yellow]{action_message}[/yellow]")

            # Check if step has a custom result message
            if step.result_message:
                # Resolve any templates in the custom message
                try:
                    from ..services.template_service import TemplateService

                    template_service = TemplateService()

                    # Debug: Log current context state before template resolution
                    logger.debug(
                        f"Template resolution context - outputs.saving_throw_result: {self.context.outputs.get('saving_throw_result', 'NOT_FOUND')}"
                    )

                    # Create a temporary context that includes step result data for template resolution
                    # This makes the 'result' variable available in result_message templates
                    temp_context_data = {
                        "inputs": self.context.inputs,
                        "variables": self.context.variables,
                        "outputs": self.context.outputs,
                        "system": self.system,
                    }

                    # Add step result data if available
                    if step_result.data:
                        temp_context_data.update(step_result.data)

                    resolved_message = template_service.resolve_template(
                        step.result_message, temp_context_data
                    )

                    logger.debug(
                        f"Template '{step.result_message}' resolved to: '{resolved_message}'"
                    )
                    success_message = get_step_success_message(
                        step.type, resolved_message
                    )
                except Exception as e:
                    # If template resolution fails, fall back to generic message
                    logger.debug(f"Failed to resolve result_message template: {e}")
                    success_message = get_step_success_message(step.type)
            else:
                success_message = get_step_success_message(step.type)

            self._print_indented(f"[green]{success_message}[/green]")
        else:
            failure_message = get_step_failure_message(step.type)
            self._print_indented(f"[red]{failure_message}: {step_result.error}[/red]")

        self.step_results.append(step_result)
        return step_result.success, step_result.next_step_id

    def _execute_flow_call_step(self, step, step_num: int) -> tuple[bool, str | None]:
        """Execute a flow_call step with nested TUI display."""
        # Execute the step normally first to get the result
        step_result = self.engine._execute_step(step, self.context, self.system)

        # Show sub-flow execution details if it succeeded
        if step_result.success and hasattr(step, "flow"):
            sub_flow_name = step.flow
            self._print_indented(f"[blue]  📄 Sub-flow: {sub_flow_name}[/blue]")
            self._print_indented("[blue]  🚀 Sub-flow executed successfully[/blue]")

            # Show any outputs from the sub-flow
            if step_result.data and "sub_flow_outputs" in step_result.data:
                outputs = step_result.data["sub_flow_outputs"]
                if outputs:
                    self._print_indented(
                        f"[blue]  � Sub-flow outputs: {list(outputs.keys())}[/blue]"
                    )

        # Handle the result display
        if step_result.success:
            # Check if step has a custom result message
            if step.result_message:
                # Resolve any templates in the custom message
                try:
                    from ..services.template_service import TemplateService

                    template_service = TemplateService()
                    resolved_message = (
                        template_service.resolve_template_with_execution_context(
                            step.result_message, self.context, self.system
                        )
                    )
                    success_message = get_step_success_message(
                        step.type, resolved_message
                    )
                except Exception as e:
                    logger.debug(f"Failed to resolve result_message template: {e}")
                    success_message = get_step_success_message(step.type)
            else:
                success_message = get_step_success_message(step.type)

            self._print_indented(f"[green]{success_message}[/green]")

    def _execute_flow_call_step(self, step, step_num: int) -> tuple[bool, str | None]:
        """Execute a flow_call step with nested TUI display showing all sub-flow steps."""
        from ..models.flow import StepResult

        try:
            if not hasattr(step, "flow") or not step.flow:
                raise ValueError(
                    f"flow_call step '{step.id}' missing required 'flow' field"
                )

            sub_flow_name = step.flow
            self._print_indented(f"[blue]🔗 Starting sub-flow: {sub_flow_name}[/blue]")

            # Get the target flow
            target_flow = self.system.get_flow(sub_flow_name)
            if not target_flow:
                raise ValueError(
                    f"Target flow '{sub_flow_name}' not found in system '{self.system.id}'"
                )

            # Resolve input templates for the sub-flow
            from ..services.template_service import TemplateService

            template_service = TemplateService()

            resolved_inputs = {}
            if hasattr(step, "inputs") and step.inputs:
                for key, value in step.inputs.items():
                    try:
                        resolved_value = (
                            template_service.resolve_template_with_execution_context(
                                value, self.context, self.system, mode="runtime"
                            )
                        )
                        resolved_inputs[key] = resolved_value
                        self._print_indented(
                            f"[dim]📥 Input {key}: {resolved_value}[/dim]"
                        )
                    except Exception as e:
                        raise ValueError(
                            f"Failed to resolve flow_call input '{key}': {e}"
                        ) from e

            # Create a new execution context for the sub-flow
            from ..models.context_data import ExecutionContext

            sub_context = ExecutionContext()

            # Set the resolved inputs in the sub-flow context
            for key, value in resolved_inputs.items():
                sub_context.set_input(key, value)

            # Initialize flow variables if any
            if target_flow.variables:
                for variable in target_flow.variables:
                    sub_context.set_variable(variable.id, variable.default)

            # Initialize observable derived fields from output models
            for output_def in target_flow.outputs:
                if output_def.type in self.system.models:
                    model = self.system.models[output_def.type]
                    sub_context.initialize_model_observables(model, output_def.id)

            # Create nested TUI for sub-flow execution
            nested_tui = RichTUI(
                engine=self.engine,
                console=self.console,
                indent_level=self.indent_level + 1,
                parent_tui=self,
            )

            # Execute the sub-flow using the nested TUI - this will show all steps
            result = nested_tui.execute_flow(target_flow, sub_context, self.system)

            if result:
                # Get the sub-flow outputs
                sub_flow_outputs = sub_context.outputs

                # Store the result in the main context for template resolution
                self.context.outputs["result"] = sub_flow_outputs

                self._print_indented(
                    f"[green]🔗 Sub-flow '{sub_flow_name}' completed successfully[/green]"
                )
                if sub_flow_outputs:
                    self._print_indented(
                        f"[dim]📤 Outputs: {list(sub_flow_outputs.keys())}[/dim]"
                    )

                # Execute any flow_call step actions with result context
                if hasattr(step, "actions") and step.actions:
                    self._print_indented(
                        "[cyan]⚙️ Executing flow_call step actions...[/cyan]"
                    )

                    # Create result object for template resolution
                    class ResultObject:
                        """Result object that allows dot notation access to sub-flow outputs."""

                        def __init__(self, outputs):
                            for key, value in outputs.items():
                                setattr(self, key, value)

                    result_obj = ResultObject(sub_flow_outputs)

                    # Set result in the main context for template resolution
                    self.context.set_variable("result", result_obj)

                    try:
                        self.engine.action_executor.execute_actions(
                            step.actions, self.context, {}, self.system
                        )
                        self._print_indented("[green]✅ Step actions completed[/green]")
                    except Exception as e:
                        self._print_indented(f"[red]❌ Step action failed: {e}[/red]")
                        return False, None

                # Create step result
                step_result = StepResult(
                    step_id=step.id,
                    success=True,
                    data={
                        "flow_call": True,
                        "target_flow": sub_flow_name,
                        "sub_flow_outputs": sub_flow_outputs,
                    },
                    prompt=step.prompt,
                )
            else:
                self._print_indented(f"[red]🔗 Sub-flow '{sub_flow_name}' failed[/red]")
                step_result = StepResult(
                    step_id=step.id,
                    success=False,
                    error=f"Sub-flow '{sub_flow_name}' execution failed",
                )

        except Exception as e:
            logger.error(f"Error executing flow_call step: {e}")
            self._print_indented(f"[red]🔗 Sub-flow execution error: {e}[/red]")
            step_result = StepResult(
                step_id=step.id,
                success=False,
                error=str(e),
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
        """Show a compact summary of the execution results."""
        if not self.step_results:
            return

        success_count = sum(1 for result in self.step_results if result.success)
        total_count = len(self.step_results)

        if success_count == total_count:
            self.console.print(
                f"[green]✅ All {total_count} steps completed successfully[/green]"
            )
        else:
            failed_count = total_count - success_count
            self.console.print(
                f"[yellow]⚠️  {success_count}/{total_count} steps successful, {failed_count} failed[/yellow]"
            )

            # Show which steps failed
            for i, result in enumerate(self.step_results, 1):
                if not result.success:
                    self.console.print(f"  [red]Step {i}: {result.error}[/red]")


def run_rich_tui_executor(
    system_path: Path,
    flow_id: str,
    input_values: dict = None,
    interactive: bool = True,
) -> None:
    """Run the Rich TUI executor."""
    tui = RichTUI(system_path, flow_id, input_values)
    tui.run()
