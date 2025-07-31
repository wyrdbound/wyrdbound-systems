"""Command-line interface for GRIMOIRE runner."""

import typer
import logging
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.columns import Columns
from rich.text import Text
from rich.tree import Tree
from rich.live import Live
from rich.align import Align
from rich.markup import escape
import json
import time

from ..core.engine import GrimoireEngine
from ..models.context_data import ExecutionContext
from .textual_app import run_textual_app
from .textual_browser import run_compendium_browser

# Setup console (Rich is used by Textual)
console = Console()
app = typer.Typer(name="grimoire-runner", help="Interactive GRIMOIRE system runner")

# Global engine instance
engine = GrimoireEngine()


def create_template_context(system):
    """Create a temporary context for resolving templates with system metadata."""
    temp_context = engine.create_execution_context()
    temp_context.system_metadata = {
        'id': system.id,
        'name': system.name,
        'description': system.description,
        'version': system.version,
        'currency': getattr(system, 'currency', {}),
        'credits': getattr(system, 'credits', {})
    }
    return temp_context


@app.command()
def validate(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Validate a GRIMOIRE system definition."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    console.print(f"[bold blue]Validating GRIMOIRE system:[/bold blue] {system_path}")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Loading system...", total=None)
            system = engine.load_system(system_path)
            
            progress.update(task, description="Validating system...")
            errors = system.validate()
            
            progress.update(task, description="Validating flows...")
            flow_errors = []
            for flow_id, flow in system.flows.items():
                flow_validation = flow.validate()
                if flow_validation:
                    flow_errors.extend([f"Flow {flow_id}: {error}" for error in flow_validation])
            
            progress.update(task, description="Validation complete")
        
        # Display results
        if not errors and not flow_errors:
            console.print(f"[bold green]✓ System validation passed[/bold green]")
            console.print(f"  System: {system.name} ({system.id})")
            console.print(f"  Flows: {len(system.flows)}")
            console.print(f"  Models: {len(system.models)}")
            console.print(f"  Compendiums: {len(system.compendiums)}")
            console.print(f"  Tables: {len(system.tables)}")
        else:
            console.print(f"[bold red]✗ System validation failed[/bold red]")
            
            if errors:
                console.print("\n[red]System errors:[/red]")
                for error in errors:
                    console.print(f"  • {error}")
            
            if flow_errors:
                console.print("\n[red]Flow errors:[/red]")
                for error in flow_errors:
                    console.print(f"  • {error}")
                    
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[bold red]Error loading system:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def execute(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    flow: str = typer.Option(..., "--flow", "-f", help="Flow ID to execute"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save results to file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="Enable interactive mode for user choices"),
    use_textual: bool = typer.Option(True, "--textual/--no-textual", help="Use Textual interface (default) or fallback to Rich console"),
    no_progress: bool = typer.Option(False, "--no-progress", help="Disable step-by-step progress display (Rich mode only)")
):
    """Execute a complete flow with enhanced visual output."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Use Textual interface by default
    if use_textual:
        try:
            from .simple_textual import run_simple_textual_executor
            run_simple_textual_executor(system_path, flow)
            return
        except ImportError as e:
            console.print(f"[yellow]Textual interface not available: {e}[/yellow]")
            console.print("[yellow]Falling back to Rich console interface...[/yellow]")
        except Exception as e:
            console.print(f"[red]Textual interface error: {e}[/red]")
            console.print("[yellow]Falling back to Rich console interface...[/yellow]")

    # Fallback to Rich console interface
    _execute_with_rich_console(system_path, flow, output, verbose, interactive, no_progress)


def _execute_with_rich_console(system_path: Path, flow: str, output: Optional[Path], verbose: bool, interactive: bool, no_progress: bool):
    """Execute flow using the Rich console interface (original implementation)."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        # Create a nice header
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]GRIMOIRE Flow Execution[/bold cyan]\n"
            f"[dim]System: {system_path}[/dim]\n"
            f"[dim]Flow: {flow}[/dim]",
            border_style="cyan"
        ))
        console.print()

        # Load system with spinner
        with console.status("[bold blue]Loading system...", spinner="dots"):
            system = engine.load_system(system_path)
        
        # System info panel
        flow_obj = system.get_flow(flow)
        if not flow_obj:
            console.print(Panel(
                f"[bold red]Flow '{flow}' not found[/bold red]\n\n"
                f"Available flows:\n" + 
                "\n".join([f"  • {f}" for f in system.list_flows()]),
                title="Error",
                border_style="red"
            ))
            raise typer.Exit(1)

        # Display system and flow information
        # Create a temporary context to resolve templates in flow description
        temp_context = engine.create_execution_context()
        temp_context.system_metadata = {
            'id': system.id,
            'name': system.name,
            'description': system.description,
            'version': system.version,
            'currency': getattr(system, 'currency', {}),
            'credits': getattr(system, 'credits', {})
        }
        
        info_table = Table(show_header=False, box=None, padding=(0, 2))
        info_table.add_row("[bold]System:[/bold]", system.name)
        info_table.add_row("[bold]Flow:[/bold]", flow_obj.name)
        info_table.add_row("[bold]Description:[/bold]", flow_obj.resolve_description(temp_context) or "[dim]No description[/dim]")
        info_table.add_row("[bold]Steps:[/bold]", str(len(flow_obj.steps)))
        
        console.print(Panel(info_table, title="Execution Details", border_style="blue"))
        console.print()

        # Execute flow with enhanced progress
        context = engine.create_execution_context()
        
        if no_progress:
            # Simple execution without step tracking
            with console.status("[bold green]Executing flow...", spinner="aesthetic"):
                result = engine.execute_flow(flow, context, system)
        else:
            # Step-by-step execution with visual progress
            result = _execute_flow_with_progress(engine, flow, context, system, interactive)
        
        console.print()
        
        # Display results with enhanced formatting
        if result.success:
            _display_success_results(result, system, flow_obj)
            
            # Save to file if requested
            if output:
                _save_results_to_file(result, output)
                
        else:
            _display_failure_results(result)
            raise typer.Exit(1)
            
    except Exception as e:
        console.print()
        console.print(Panel(
            f"[bold red]Execution Error[/bold red]\n\n{str(e)}",
            border_style="red"
        ))
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


def _execute_flow_with_progress(engine, flow_id, context, system, interactive_mode=False):
    """Execute a flow with step-by-step progress visualization."""
    flow_obj = system.get_flow(flow_id)
    total_steps = len(flow_obj.steps)
    
    # Create progress tracking
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    )
    
    step_results = []
    current_step_num = 0
    
    with progress:
        task = progress.add_task("Initializing...", total=total_steps)
        
        try:
            # Use step-through execution for better control
            for step_result in engine.step_through_flow(flow_id, context, system):
                current_step_num += 1
                step = flow_obj.get_step(step_result.step_id)
                step_name = step.name if step else step_result.step_id
                
                # Update progress
                progress.update(task, 
                    description=f"[bold]Step {current_step_num}/{total_steps}:[/bold] {step_name}",
                    completed=current_step_num
                )
                
                step_results.append(step_result)
                
                # Handle user input if needed and interactive mode is enabled
                if step_result.requires_input and interactive_mode:
                    progress.stop()
                    choice_result = _handle_interactive_choice(step_result, context, engine, step)
                    # Update step_result with the choice result's next_step_id if available
                    if choice_result and choice_result.next_step_id:
                        step_result.next_step_id = choice_result.next_step_id
                    progress.start()
                elif step_result.requires_input and not interactive_mode:
                    # In non-interactive mode, show what input was needed
                    console.print(f"[yellow]⚠ Step '{step_name}' requires user input (skipped in non-interactive mode)[/yellow]")
                    break
                
                if not step_result.success:
                    break
                    
                # Small delay for visual effect (can be removed for production)
                time.sleep(0.1)
            
            progress.update(task, description="[bold green]Flow completed![/bold green]", completed=total_steps)
            
        except Exception as e:
            progress.update(task, description=f"[bold red]Error: {str(e)}[/bold red]")
            raise
    
    # Create a FlowResult-like object
    from ..models.flow import FlowResult
    
    # Determine success and error conditions
    all_completed_steps_successful = all(sr.success for sr in step_results)
    completed_all_steps = current_step_num >= total_steps
    
    # Check if we stopped due to user input requirement
    stopped_for_input = (step_results and 
                        step_results[-1].success and 
                        step_results[-1].requires_input and 
                        not interactive_mode)
    
    # Success if either all steps completed successfully OR we stopped for user input
    success = all_completed_steps_successful and (completed_all_steps or stopped_for_input)
    
    # Error message
    error = None
    if not success:
        if not all_completed_steps_successful:
            # Find the first failed step
            failed_step = next((sr for sr in step_results if not sr.success), None)
            error = failed_step.error if failed_step else "Step execution failed"
        elif not completed_all_steps and not stopped_for_input:
            error = f"Flow incomplete: {current_step_num}/{total_steps} steps completed"
    
    # Extract outputs
    outputs = {}
    for output_def in flow_obj.outputs:
        output_value = context.get_output(output_def.id)
        if output_value is not None:
            outputs[output_def.id] = output_value
    
    return FlowResult(
        flow_id=flow_id,
        success=success,
        outputs=outputs,
        variables=context.variables.copy(),
        step_results=step_results,
        error=error,
        completed_at_step=step_results[-1].step_id if step_results and not step_results[-1].success else None
    )


def _handle_interactive_choice(step_result, context, engine, step):
    """Handle interactive user choice in execute mode."""
    console.print()
    console.print(Panel(
        f"[bold yellow]User Input Required[/bold yellow]\n\n"
        f"{step_result.prompt or 'Please make a choice:'}",
        border_style="yellow"
    ))
    
    if step_result.choices:
        # Check if we need multiple selections
        selection_count = step_result.data.get('selection_count', 1)
        
        if selection_count > 1:
            # Multiple selections with separate prompts
            selected_choices = []
            selected_ids = []
            available_choices = step_result.choices.copy()  # Make a copy
            
            try:
                for selection_num in range(selection_count):
                    console.print(f"\n[bold cyan]Selection {selection_num + 1} of {selection_count}:[/bold cyan]")
                    
                    # Show remaining choices
                    choice_table = Table(show_header=True, header_style="bold magenta")
                    choice_table.add_column("Option", style="cyan")
                    choice_table.add_column("Description")
                    
                    for i, choice in enumerate(available_choices, 1):
                        choice_table.add_row(str(i), choice.label or choice.id)
                    
                    console.print(choice_table)
                    
                    # Show previously selected items
                    if selected_choices:
                        console.print(f"\n[dim]Already selected: {', '.join(c.label for c in selected_choices)}[/dim]")
                    
                    console.print()
                    
                    while True:
                        try:
                            user_input = typer.prompt(f"Enter choice number for selection {selection_num + 1}")
                            choice_num = int(user_input) - 1
                            
                            if 0 <= choice_num < len(available_choices):
                                selected_choice = available_choices[choice_num]
                                selected_choices.append(selected_choice)
                                selected_ids.append(selected_choice.id)
                                
                                console.print(f"[green]✓ Selected: {selected_choice.label}[/green]")
                                
                                # Remove the selected choice from available choices
                                available_choices.remove(selected_choice)
                                break
                            else:
                                console.print("[red]Invalid choice number. Please try again.[/red]")
                        except (ValueError, typer.Abort):
                            console.print("[red]Please enter a valid number.[/red]")
                
                # Show final selection summary
                console.print(f"\n[bold green]Final Selections:[/bold green]")
                for i, choice in enumerate(selected_choices, 1):
                    console.print(f"  {i}. {choice.label}")
                
                # Store the multiple selections in context
                context.set_variable('selected_items', selected_ids)
                context.set_variable('user_choices', selected_ids)  # Alternative name
                
                # Now execute the step's actions with the user selections
                if step.actions:
                    for action in step.actions:
                        engine._execute_single_action(action, context, {'selected_items': selected_ids})
                
                return None  # Multiple selections don't override next_step
            
            except Exception as e:
                console.print(f"[red]Error during selection: {e}[/red]")
                console.print("[yellow]Continuing with default behavior...[/yellow]")
                # Fall back to empty selection
                context.set_variable('selected_items', [])
                context.set_variable('user_choices', [])
                return None
        
        else:
            # Single selection (original logic)
            choice_table = Table(show_header=True, header_style="bold magenta")
            choice_table.add_column("Option", style="cyan")
            choice_table.add_column("Description")
            
            for i, choice in enumerate(step_result.choices, 1):
                choice_table.add_row(str(i), choice.label or choice.id)
            
            console.print(choice_table)
            console.print()
            
            while True:
                try:
                    user_input = typer.prompt("Enter your choice number")
                    choice_num = int(user_input) - 1
                    if 0 <= choice_num < len(step_result.choices):
                        selected_choice = step_result.choices[choice_num]
                        # Process the choice using the executor
                        from ..executors.choice_executor import ChoiceExecutor
                        choice_executor = ChoiceExecutor()
                        choice_result = choice_executor.process_choice(selected_choice.id, step, context)
                        console.print(f"[green]✓ Selected: {selected_choice.label}[/green]")
                        return choice_result  # Return the choice result
                    else:
                        console.print("[red]Invalid choice number. Please try again.[/red]")
                except (ValueError, typer.Abort):
                    console.print("[red]Please enter a valid number.[/red]")
    else:
        # Simple text input
        user_input = typer.prompt("Enter your input")
        context.set_variable('user_input', user_input)
    
    console.print()
    return None  # Return None if no choice was made


def _display_success_results(result, system, flow_obj):
    """Display successful execution results with enhanced formatting."""
    # Success header
    console.print(Panel.fit(
        "[bold green]✓ Flow Execution Completed Successfully![/bold green]",
        border_style="green"
    ))
    console.print()
    
    # Execution summary
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_row("[bold]Flow:[/bold]", flow_obj.name)
    summary_table.add_row("[bold]Steps Executed:[/bold]", str(len(result.step_results)))
    summary_table.add_row("[bold]Success Rate:[/bold]", f"{sum(1 for sr in result.step_results if sr.success)}/{len(result.step_results)}")
    
    console.print(Panel(summary_table, title="Execution Summary", border_style="green"))
    console.print()
    
    # Display outputs with better formatting
    if result.outputs:
        console.print("[bold cyan]Generated Outputs:[/bold cyan]")
        console.print()
        
        for output_id, output_value in result.outputs.items():
            # Debug the output value type
            try:
                # Try to format the output nicely
                if isinstance(output_value, dict):
                    # Create a tree view for complex objects
                    tree = Tree(f"[bold]{output_id}[/bold]")
                    _add_dict_to_tree(tree, output_value)
                    console.print(Panel(tree, border_style="cyan"))
                else:
                    # Simple value display
                    console.print(Panel(
                        str(output_value),
                        title=f"[bold]{output_id}[/bold]",
                        border_style="cyan"
                    ))
            except Exception as e:
                # Fallback display for problematic outputs
                console.print(Panel(
                    f"[red]Error displaying output: {str(e)}[/red]\n"
                    f"Output type: {type(output_value)}\n"
                    f"Output repr: {repr(output_value)}",
                    title=f"[bold]{output_id}[/bold] [red](Error)[/red]",
                    border_style="red"
                ))
            console.print()
    else:
        console.print("[dim]No outputs generated[/dim]")
        console.print()
    
    # Show step details if there were any interesting results
    if result.step_results:
        console.print("[bold cyan]Step Details:[/bold cyan]")
        step_table = Table(show_header=True, header_style="bold cyan")
        step_table.add_column("Step", style="yellow")
        step_table.add_column("Result", style="green")
        step_table.add_column("Details", style="dim")
        
        for sr in result.step_results:
            if sr.success:
                result_status = "[green]✓ Success[/green]"
            else:
                result_status = "[red]✗ Failed[/red]"
            
            details = ""
            if sr.data:
                details = ", ".join([f"{k}: {v}" for k, v in sr.data.items() if k not in ['skipped']])
            
            step_table.add_row(
                sr.step_id,
                result_status,
                details[:50] + "..." if len(details) > 50 else details
            )
        
        console.print(Panel(step_table, title="Step Results", border_style="cyan"))
        console.print()


def _display_failure_results(result):
    """Display failure results with enhanced formatting."""
    console.print(Panel.fit(
        "[bold red]✗ Flow Execution Failed[/bold red]",
        border_style="red"
    ))
    console.print()
    
    # Error details
    error_table = Table(show_header=False, box=None, padding=(0, 2))
    error_table.add_row("[bold]Error:[/bold]", result.error or "Unknown error")
    if result.completed_at_step:
        error_table.add_row("[bold]Failed at step:[/bold]", result.completed_at_step)
    error_table.add_row("[bold]Steps completed:[/bold]", f"{len(result.step_results)}")
    
    console.print(Panel(error_table, title="Error Details", border_style="red"))
    console.print()
    
    # Show all executed steps
    if result.step_results:
        console.print("[bold cyan]Executed Steps:[/bold cyan]")
        
        step_table = Table(show_header=True, header_style="bold cyan")
        step_table.add_column("Step", style="yellow")
        step_table.add_column("Status", style="green")
        step_table.add_column("Error", style="dim")
        
        for sr in result.step_results:
            if sr.success:
                status = "[green]✓ Success[/green]"
            else:
                status = "[red]✗ Failed[/red]"
            error = sr.error or ""
            step_table.add_row(sr.step_id, status, error[:50] + "..." if len(error) > 50 else error)
        
        console.print(Panel(step_table, title="Execution Steps", border_style="cyan"))


def _save_results_to_file(result, output_path):
    """Save results to file with enhanced data."""
    try:
        output_data = {
            'flow_id': result.flow_id,
            'success': result.success,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'outputs': result.outputs,
            'variables': result.variables,
            'step_results': [
                {
                    'step_id': sr.step_id,
                    'success': sr.success,
                    'error': sr.error,
                    'data': sr.data
                }
                for sr in result.step_results
            ],
            'execution_summary': {
                'total_steps': len(result.step_results),
                'successful_steps': sum(1 for sr in result.step_results if sr.success),
                'failed_steps': sum(1 for sr in result.step_results if not sr.success)
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)
        
        console.print(Panel.fit(
            f"[bold green]Results saved to:[/bold green] {output_path}",
            border_style="green"
        ))
    except Exception as e:
        console.print(Panel.fit(
            f"[bold red]Failed to save results:[/bold red] {str(e)}",
            border_style="red"
        ))


def _add_dict_to_tree(tree, data, max_depth=3, current_depth=0):
    """Recursively add dictionary data to a Rich tree."""
    if current_depth >= max_depth:
        tree.add("[dim]...[/dim]")
        return
    
    for key, value in data.items():
        try:
            # Use duck typing instead of isinstance to avoid type checking issues
            if hasattr(value, 'items'):  # Dictionary-like
                branch = tree.add(f"[bold]{key}[/bold]")
                _add_dict_to_tree(branch, value, max_depth, current_depth + 1)
            elif hasattr(value, '__iter__') and not isinstance(value, str):  # List-like but not string
                branch = tree.add(f"[bold]{key}[/bold] [dim](list)[/dim]")
                try:
                    items = list(value)[:5]  # Convert to list and take first 5
                    for i, item in enumerate(items):
                        try:
                            if hasattr(item, 'items'):  # Dictionary-like
                                item_branch = branch.add(f"[dim]{i}:[/dim]")
                                _add_dict_to_tree(item_branch, item, max_depth, current_depth + 2)
                            else:
                                branch.add(f"[dim]{i}:[/dim] {str(item)}")
                        except Exception as e:
                            branch.add(f"[dim]{i}:[/dim] [red]Error: {str(e)}[/red]")
                    if len(items) > 5:
                        branch.add(f"[dim]... and {len(items) - 5} more items[/dim]")
                except Exception as e:
                    branch.add(f"[red]Error iterating: {str(e)}[/red]")
            else:
                tree.add(f"[bold]{key}:[/bold] {str(value)}")
        except Exception as e:
            tree.add(f"[bold]{key}:[/bold] [red]Error: {str(e)}[/red]")


@app.command()
def browse(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    compendium: Optional[str] = typer.Option(None, "--compendium", "-c", help="Compendium to browse"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search term")
):
    """Browse compendium content."""
    try:
        # Load system
        system = engine.load_system(system_path)
        run_compendium_browser(system)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def interactive(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    flow: Optional[str] = typer.Option(None, "--flow", "-f", help="Flow to start with")
):
    """Start interactive REPL mode."""
    try:
        if flow:
            # If a specific flow is requested, use the same execution engine as the execute command
            # This provides full step-by-step execution with user interaction
            from .simple_textual import run_simple_textual_executor
            run_simple_textual_executor(system_path, flow)
        else:
            # If no flow specified, show the system explorer for browsing
            run_textual_app(system_path, flow)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def debug(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    flow: str = typer.Option(..., "--flow", "-f", help="Flow ID to debug"),
    breakpoint: Optional[List[str]] = typer.Option(None, "--breakpoint", "-b", help="Step IDs to break at")
):
    """Debug a flow with breakpoints."""
    try:
        # Load system
        system = engine.load_system(system_path)
        
        # Enable debug mode
        engine.enable_debug_mode()
        
        # Set breakpoints
        if breakpoint:
            for bp in breakpoint:
                engine.set_breakpoint(flow, bp)
                console.print(f"[yellow]Breakpoint set:[/yellow] {flow}.{bp}")
        
        # Start interactive debugging via Textual app
        run_textual_app(system_path)
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


@app.command()
def list(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    component: str = typer.Option("flows", "--type", "-t", help="Component type to list (flows, models, compendiums, tables)")
):
    """List system components."""
    try:
        # Load system
        system = engine.load_system(system_path)
        
        console.print(f"[bold blue]{system.name}[/bold blue] ({system.id})")
        console.print(f"[dim]{system.description or 'No description'}[/dim]\n")
        
        if component == "flows":
            flows = system.list_flows()
            if flows:
                table = Table(title="Available Flows")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Description", style="yellow")
                table.add_column("Steps", style="green")
                
                # Create template context for resolving descriptions
                temp_context = create_template_context(system)
                
                for flow_id in flows:
                    flow = system.get_flow(flow_id)
                    resolved_description = flow.resolve_description(temp_context) if flow.description else "-"
                    table.add_row(
                        flow_id, 
                        flow.name, 
                        resolved_description, 
                        str(len(flow.steps))
                    )
                
                console.print(table)
            else:
                console.print("[yellow]No flows found[/yellow]")
        
        elif component == "models":
            models = system.list_models()
            if models:
                table = Table(title="Available Models")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Description", style="yellow")
                table.add_column("Extends", style="blue")
                table.add_column("Attributes", style="green")
                
                for model_id in models:
                    model = system.get_model(model_id)
                    attr_count = len(model.get_all_attributes())
                    
                    # Get extended model names
                    extended_names = []
                    for extend_id in model.extends:
                        extended_model = system.get_model(extend_id)
                        if extended_model:
                            extended_names.append(extended_model.name)
                        else:
                            extended_names.append(extend_id)  # fallback to ID if model not found
                    
                    extends_display = ", ".join(extended_names) if extended_names else "-"
                    
                    table.add_row(
                        model_id, 
                        model.name, 
                        model.description or "-", 
                        extends_display,
                        str(attr_count)
                    )
                
                console.print(table)
            else:
                console.print("[yellow]No models found[/yellow]")
        
        elif component == "compendiums":
            compendiums = system.list_compendiums()
            if compendiums:
                table = Table(title="Available Compendiums")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Model Name", style="yellow")
                table.add_column("Entries", style="green")
                
                for comp_id in compendiums:
                    comp = system.get_compendium(comp_id)
                    model = system.get_model(comp.model)
                    model_name = model.name if model else comp.model
                    table.add_row(comp.id, comp.name, model_name, str(len(comp.entries)))
                
                console.print(table)
            else:
                console.print("[yellow]No compendiums found[/yellow]")
        
        elif component == "tables":
            tables = system.list_tables()
            if tables:
                table = Table(title="Available Tables")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Description", style="yellow")
                table.add_column("Entries", style="green")
                table.add_column("Roll", style="blue")
                
                for table_id in tables:
                    tbl = system.get_table(table_id)
                    table.add_row(
                        tbl.id or table_id, 
                        tbl.name or "-", 
                        tbl.description or "-", 
                        str(len(tbl.entries)), 
                        tbl.roll or "-"
                    )
                
                console.print(table)
            else:
                console.print("[yellow]No tables found[/yellow]")
                
        else:
            console.print(f"[red]Unknown component type: {component}[/red]")
            console.print("Available types: flows, models, compendiums, tables")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
