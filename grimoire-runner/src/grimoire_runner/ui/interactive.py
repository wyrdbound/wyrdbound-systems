"""Interactive REPL mode for GRIMOIRE runner."""

import logging
from typing import Optional, Dict, Any
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..core.engine import GrimoireEngine

logger = logging.getLogger(__name__)
console = Console()


def create_template_context(engine, system):
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


class InteractiveREPL:
    """Interactive REPL for exploring and debugging GRIMOIRE systems."""
    
    def __init__(self, engine, system):
        self.engine = engine
        self.system = system
        self.context = None
        self.current_flow = None
        self.current_step = None
        self.debug_mode = False
    
    def run(self) -> None:
        """Start the interactive REPL."""
        console.print(Panel(
            f"[bold blue]GRIMOIRE Interactive Runner[/bold blue]\n"
            f"System: {self.system.name} ({self.system.id})\n"
            f"Type 'help' for available commands.",
            title="Welcome",
            border_style="blue"
        ))
        
        while True:
            try:
                command = Prompt.ask("\n[bold cyan]grimoire>[/bold cyan]").strip().lower()
                
                if not command:
                    continue
                
                if command == "quit" or command == "exit":
                    console.print("Goodbye!")
                    break
                elif command == "help":
                    self._show_help()
                elif command.startswith("flows"):
                    self._list_flows()
                elif command.startswith("run "):
                    flow_id = command[4:].strip()
                    self.start_flow(flow_id)
                elif command.startswith("debug "):
                    flow_id = command[6:].strip()
                    self.start_flow(flow_id, debug=True)
                elif command == "context":
                    self._show_context()
                elif command == "step":
                    self._step_forward()
                elif command == "continue":
                    self._continue_execution()
                elif command.startswith("breakpoint "):
                    parts = command.split()
                    if len(parts) >= 3:
                        flow_id, step_id = parts[1], parts[2]
                        self.engine.set_breakpoint(flow_id, step_id)
                        console.print(f"[yellow]Breakpoint set:[/yellow] {flow_id}.{step_id}")
                elif command == "models":
                    self._list_models()
                elif command == "compendiums":
                    self._list_compendiums()
                elif command == "tables":
                    self._list_tables()
                else:
                    console.print(f"[red]Unknown command:[/red] {command}")
                    console.print("Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                console.print("\nUse 'quit' to exit.")
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                logger.exception("REPL error")
    
    def start_flow(self, flow_id: str, debug: bool = False) -> None:
        """Start executing a flow."""
        flow = self.system.get_flow(flow_id)
        if not flow:
            console.print(f"[red]Flow not found:[/red] {flow_id}")
            return
        
        self.current_flow = flow_id
        self.debug_mode = debug
        self.context = self.engine.create_execution_context()
        
        console.print(f"[bold green]Starting flow:[/bold green] {flow.name}")
        
        if debug:
            console.print("[yellow]Debug mode enabled[/yellow]")
            self.engine.enable_debug_mode()
            self._execute_step_by_step()
        else:
            self._execute_full_flow()
    
    def _execute_full_flow(self) -> None:
        """Execute the complete flow."""
        try:
            result = self.engine.execute_flow(self.current_flow, self.context, self.system)
            
            if result.success:
                console.print(f"[bold green]✓ Flow completed successfully[/bold green]")
                
                if result.outputs:
                    console.print("\n[bold]Final outputs:[/bold]")
                    for output_id, output_value in result.outputs.items():
                        console.print(Panel(
                            str(output_value),
                            title=output_id,
                            border_style="green"
                        ))
            else:
                console.print(f"[bold red]✗ Flow execution failed[/bold red]")
                console.print(f"Error: {result.error}")
                
        except Exception as e:
            console.print(f"[red]Flow execution error:[/red] {e}")
            logger.exception("Flow execution failed")
    
    def _execute_step_by_step(self) -> None:
        """Execute flow step by step for debugging."""
        try:
            step_generator = self.engine.step_through_flow(self.current_flow, self.context, self.system)
            
            for step_result in step_generator:
                self.current_step = step_result.step_id
                
                console.print(f"\n[bold blue]Step:[/bold blue] {step_result.step_id}")
                
                if step_result.prompt:
                    console.print(f"[dim]{step_result.prompt}[/dim]")
                
                if step_result.success:
                    console.print(f"[green]✓ Step completed[/green]")
                    
                    if step_result.requires_input:
                        self._handle_user_input(step_result)
                    
                    if step_result.data:
                        console.print(f"[dim]Result: {step_result.data}[/dim]")
                else:
                    console.print(f"[red]✗ Step failed: {step_result.error}[/red]")
                    break
                
                # Wait for user input in debug mode
                if self.debug_mode:
                    action = Prompt.ask(
                        "\n[yellow]Next action[/yellow] (continue/step/context/quit)",
                        default="continue"
                    ).lower()
                    
                    if action == "quit":
                        break
                    elif action == "context":
                        self._show_context()
                    elif action == "step":
                        continue  # Continue to next step
                    # else continue automatically
            
            console.print(f"[bold green]Flow debugging session ended[/bold green]")
            
        except Exception as e:
            console.print(f"[red]Debug execution error:[/red] {e}")
            logger.exception("Debug execution failed")
    
    def _handle_user_input(self, step_result) -> None:
        """Handle steps that require user input."""
        if step_result.choices:
            console.print("\n[bold]Available choices:[/bold]")
            
            for i, choice in enumerate(step_result.choices, 1):
                console.print(f"  {i}. {choice.label}")
            
            while True:
                try:
                    choice_num = int(Prompt.ask("Select choice (number)"))
                    if 1 <= choice_num <= len(step_result.choices):
                        selected_choice = step_result.choices[choice_num - 1]
                        self.context.set_variable("user_choice", selected_choice.id)
                        console.print(f"[green]Selected:[/green] {selected_choice.label}")
                        break
                    else:
                        console.print(f"[red]Invalid choice. Select 1-{len(step_result.choices)}[/red]")
                except ValueError:
                    console.print("[red]Please enter a number[/red]")
    
    def _show_help(self) -> None:
        """Show available commands."""
        help_text = """
[bold]Available Commands:[/bold]

[cyan]System Exploration:[/cyan]
  flows              - List available flows
  models             - List available models
  compendiums        - List available compendiums
  tables             - List available tables

[cyan]Flow Execution:[/cyan]
  run <flow_id>      - Execute a flow
  debug <flow_id>    - Debug a flow step by step

[cyan]Debugging:[/cyan]
  context            - Show current execution context
  step               - Execute next step (debug mode)
  continue           - Continue execution
  breakpoint <flow> <step> - Set a breakpoint

[cyan]General:[/cyan]
  help               - Show this help
  quit/exit          - Exit the REPL
"""
        console.print(Panel(help_text, title="Help", border_style="yellow"))
    
    def _show_context(self) -> None:
        """Show current execution context."""
        if not self.context:
            console.print("[yellow]No active execution context[/yellow]")
            return
        
        console.print("\n[bold]Execution Context:[/bold]")
        
        if self.context.variables:
            console.print("\n[cyan]Variables:[/cyan]")
            for key, value in self.context.variables.items():
                console.print(f"  {key}: {value}")
        
        if self.context.outputs:
            console.print("\n[cyan]Outputs:[/cyan]")
            for key, value in self.context.outputs.items():
                console.print(f"  {key}: {value}")
        
        if self.context.step_history:
            console.print(f"\n[cyan]Step History:[/cyan] {' -> '.join(self.context.step_history)}")
        
        if self.current_step:
            console.print(f"[cyan]Current Step:[/cyan] {self.current_step}")
    
    def _list_flows(self) -> None:
        """List available flows."""
        flows = self.system.list_flows()
        if flows:
            table = Table(title="Available Flows")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Description", style="yellow")
            table.add_column("Steps", style="green")
            
            # Create template context for resolving descriptions
            temp_context = create_template_context(self.engine, self.system)
            
            for flow_id in flows:
                flow = self.system.get_flow(flow_id)
                resolved_description = flow.resolve_description(temp_context) if flow.description else "-"
                table.add_row(
                    flow_id,
                    flow.name,
                    resolved_description,
                    str(len(flow.steps))
                )
            
            console.print(table)
        else:
            console.print("[yellow]No flows available[/yellow]")
    
    def _list_models(self) -> None:
        """List available models."""
        models = self.system.list_models()
        if models:
            table = Table(title="Available Models")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Description", style="yellow")
            table.add_column("Extends", style="blue")
            table.add_column("Attributes", style="green")
            
            for model_id in models:
                model = self.system.get_model(model_id)
                attr_count = len(model.get_all_attributes())
                
                # Get extended model names
                extended_names = []
                for extend_id in model.extends:
                    extended_model = self.system.get_model(extend_id)
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
            console.print("[yellow]No models available[/yellow]")
    
    def _list_compendiums(self) -> None:
        """List available compendiums."""
        compendiums = self.system.list_compendiums()
        if compendiums:
            table = Table(title="Available Compendiums")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Model Name", style="yellow")
            table.add_column("Entries", style="green")
            
            for comp_id in compendiums:
                comp = self.system.get_compendium(comp_id)
                model = self.system.get_model(comp.model)
                model_name = model.name if model else comp.model
                table.add_row(comp.id, comp.name, model_name, str(len(comp.entries)))
            
            console.print(table)
        else:
            console.print("[yellow]No compendiums available[/yellow]")
    
    def _list_tables(self) -> None:
        """List available tables."""
        tables = self.system.list_tables()
        if tables:
            table = Table(title="Available Tables")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="magenta")
            table.add_column("Description", style="yellow")
            table.add_column("Entries", style="green")
            table.add_column("Roll", style="blue")
            
            for table_id in tables:
                tbl = self.system.get_table(table_id)
                table.add_row(
                    tbl.id or table_id,
                    tbl.name or "-",
                    tbl.description or "-",
                    str(len(tbl.entries)),
                    tbl.roll or "-"
                )
            
            console.print(table)
        else:
            console.print("[yellow]No tables available[/yellow]")
    
    def _step_forward(self) -> None:
        """Execute the next step in debug mode."""
        if not self.debug_mode:
            console.print("[yellow]Not in debug mode[/yellow]")
            return
        
        console.print("[cyan]Stepping forward...[/cyan]")
        # This would be implemented as part of the step-by-step execution
    
    def _continue_execution(self) -> None:
        """Continue execution until next breakpoint."""
        if not self.debug_mode:
            console.print("[yellow]Not in debug mode[/yellow]")
            return
        
        console.print("[cyan]Continuing execution...[/cyan]")
        # This would disable step-by-step mode temporarily
