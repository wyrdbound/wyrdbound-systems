"""Command-line interface for GRIMOIRE runner."""

import typer
import logging
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..core.engine import GrimoireEngine
from ..models.context_data import ExecutionContext
from .textual_app import run_textual_app
from .textual_browser import run_compendium_browser

# Setup console (Rich is used by Textual)
console = Console()
app = typer.Typer(name="grimoire-runner", help="Interactive GRIMOIRE system runner")

# Global engine instance
engine = GrimoireEngine()


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
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
):
    """Execute a complete flow."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        # Load system
        console.print(f"[bold blue]Loading system:[/bold blue] {system_path}")
        system = engine.load_system(system_path)
        
        # Check if flow exists
        if not system.get_flow(flow):
            console.print(f"[bold red]Error:[/bold red] Flow '{flow}' not found")
            available_flows = system.list_flows()
            if available_flows:
                console.print(f"Available flows: {', '.join(available_flows)}")
            raise typer.Exit(1)
        
        # Execute flow
        console.print(f"[bold blue]Executing flow:[/bold blue] {flow}")
        context = engine.create_execution_context()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Executing flow...", total=None)
            result = engine.execute_flow(flow, context, system)
        
        # Display results
        if result.success:
            console.print(f"[bold green]✓ Flow execution completed[/bold green]")
            
            # Show outputs
            if result.outputs:
                console.print("\n[bold]Outputs:[/bold]")
                for output_id, output_value in result.outputs.items():
                    console.print(Panel(
                        str(output_value),
                        title=output_id,
                        border_style="green"
                    ))
            
            # Show step summary
            console.print(f"\n[dim]Steps executed: {len(result.step_results)}[/dim]")
            
            # Save to file if requested
            if output:
                import json
                output_data = {
                    'flow_id': result.flow_id,
                    'success': result.success,
                    'outputs': result.outputs,
                    'variables': result.variables
                }
                with open(output, 'w') as f:
                    json.dump(output_data, f, indent=2, default=str)
                console.print(f"[dim]Results saved to: {output}[/dim]")
        else:
            console.print(f"[bold red]✗ Flow execution failed[/bold red]")
            console.print(f"Error: {result.error}")
            if result.completed_at_step:
                console.print(f"Failed at step: {result.completed_at_step}")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1)


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
        # Load system and start Textual app
        run_textual_app(system_path)
            
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
                table.add_column("Steps", style="green")
                
                for flow_id in flows:
                    flow = system.get_flow(flow_id)
                    table.add_row(flow_id, flow.name, str(len(flow.steps)))
                
                console.print(table)
            else:
                console.print("[yellow]No flows found[/yellow]")
        
        elif component == "models":
            models = system.list_models()
            if models:
                table = Table(title="Available Models")
                table.add_column("ID", style="cyan")
                table.add_column("Name", style="magenta")
                table.add_column("Attributes", style="green")
                
                for model_id in models:
                    model = system.get_model(model_id)
                    attr_count = len(model.get_all_attributes())
                    table.add_row(model_id, model.name, str(attr_count))
                
                console.print(table)
            else:
                console.print("[yellow]No models found[/yellow]")
        
        elif component == "compendiums":
            compendiums = system.list_compendiums()
            if compendiums:
                table = Table(title="Available Compendiums")
                table.add_column("Name", style="cyan")
                table.add_column("Model", style="magenta")
                table.add_column("Entries", style="green")
                
                for comp_id in compendiums:
                    comp = system.get_compendium(comp_id)
                    table.add_row(comp.name, comp.model, str(len(comp.entries)))
                
                console.print(table)
            else:
                console.print("[yellow]No compendiums found[/yellow]")
        
        elif component == "tables":
            tables = system.list_tables()
            if tables:
                table = Table(title="Available Tables")
                table.add_column("Name", style="cyan")
                table.add_column("Display Name", style="magenta")
                table.add_column("Entries", style="green")
                table.add_column("Roll", style="blue")
                
                for table_id in tables:
                    tbl = system.get_table(table_id)
                    table.add_row(tbl.name, tbl.display_name or "-", str(len(tbl.entries)), tbl.roll or "-")
                
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
