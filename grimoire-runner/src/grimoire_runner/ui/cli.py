"""Command-line interface for GRIMOIRE runner."""

import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
)
from rich.table import Table

from ..core.engine import GrimoireEngine
from .rich_browser import run_rich_browser
from .rich_tui import run_rich_tui_executor

# Setup console (Rich is the primary UI library)
console = Console()
app = typer.Typer(name="grimoire-runner", help="Interactive GRIMOIRE system runner")

# Global engine instance
engine = GrimoireEngine()


def create_template_context(system):
    """Create a temporary context for resolving templates with system metadata."""
    temp_context = engine.create_execution_context()
    temp_context.system_metadata = {
        "id": system.id,
        "name": system.name,
        "description": system.description,
        "version": system.version,
        "currency": getattr(system, "currency", {}),
        "credits": getattr(system, "credits", {}),
    }
    return temp_context


@app.command()
def validate(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
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
            transient=True,
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
                    flow_errors.extend(
                        [f"Flow {flow_id}: {error}" for error in flow_validation]
                    )

            progress.update(task, description="Validation complete")

        # Display results
        if not errors and not flow_errors:
            console.print("[bold green]✓ System validation passed[/bold green]")
            console.print(f"  System: {system.name} ({system.id})")
            console.print(f"  Flows: {len(system.flows)}")
            console.print(f"  Models: {len(system.models)}")
            console.print(f"  Compendiums: {len(system.compendiums)}")
            console.print(f"  Tables: {len(system.tables)}")
        else:
            console.print("[bold red]✗ System validation failed[/bold red]")

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
        raise typer.Exit(1) from None


@app.command()
def execute(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    flow: str = typer.Option(..., "--flow", "-f", help="Flow ID to execute"),
    inputs: Path | None = typer.Option(
        None, "--inputs", "-i", help="YAML file containing input values for the flow"
    ),
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Save results to file"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
    interactive: bool = typer.Option(
        True,
        "--interactive/--no-interactive",
        help="Enable interactive mode for user choices",
    ),
):
    """Execute a complete flow with enhanced visual output."""
    # TODO: Implement interactive mode functionality
    _ = interactive  # Currently unused - planned for future implementation

    # Configure logging based on verbose flag
    if verbose:
        logging.basicConfig(
            level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s"
        )
    else:
        logging.basicConfig(
            level=logging.WARNING, format="%(levelname)s:%(name)s:%(message)s"
        )

    try:
        # Load inputs from YAML file if provided
        input_values = {}
        if inputs:
            import yaml

            try:
                with open(inputs) as f:
                    input_values = yaml.safe_load(f)
                console.print(f"[dim]Loaded inputs from {inputs}[/dim]")
            except Exception as e:
                console.print(f"[red]Error loading inputs file {inputs}: {e}[/red]")
                raise typer.Exit(1) from None

        # Use Rich TUI interface - no fallback, just fix issues in Rich TUI
        run_rich_tui_executor(system_path, flow, input_values)
    except Exception as e:
        console.print(f"[bold red]Textual interface error:[/bold red] {e}")
        raise typer.Exit(1) from None


@app.command()
def browse(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    compendium: str | None = typer.Option(
        None, "--compendium", "-c", help="Compendium to browse"
    ),
    search: str | None = typer.Option(None, "--search", "-s", help="Search term"),
):
    """Browse compendium content."""
    try:
        # Load system and run Rich browser
        run_rich_browser(system_path)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from None


@app.command()
def interactive(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    flow: str | None = typer.Option(None, "--flow", "-f", help="Flow to start with"),
):
    """Start interactive REPL mode."""
    try:
        if flow:
            # If a specific flow is requested, use Rich TUI for execution
            run_rich_tui_executor(system_path, flow, {})
        else:
            # If no flow specified, use Rich browser for system exploration
            run_rich_browser(system_path)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(1) from None


@app.command()
def list(
    system_path: Path = typer.Argument(..., help="Path to GRIMOIRE system directory"),
    component: str = typer.Option(
        "flows",
        "--type",
        "-t",
        help="Component type to list (flows, models, compendiums, tables)",
    ),
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
                    resolved_description = (
                        flow.resolve_description(temp_context)
                        if flow.description
                        else "-"
                    )
                    table.add_row(
                        flow_id, flow.name, resolved_description, str(len(flow.steps))
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
                            extended_names.append(
                                extend_id
                            )  # fallback to ID if model not found

                    extends_display = (
                        ", ".join(extended_names) if extended_names else "-"
                    )

                    table.add_row(
                        model_id,
                        model.name,
                        model.description or "-",
                        extends_display,
                        str(attr_count),
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
                    table.add_row(
                        comp.id, comp.name, model_name, str(len(comp.entries))
                    )

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
                table.add_column("Entry Type", style="red")
                table.add_column("Entries", style="green")
                table.add_column("Roll", style="blue")

                for table_id in tables:
                    tbl = system.get_table(table_id)

                    # Get the display value for entry_type
                    entry_type_display = "-"
                    if tbl.entry_type:
                        # Native types should be lowercase
                        native_types = {
                            "str",
                            "int",
                            "bool",
                            "float",
                            "list",
                            "dict",
                            "set",
                            "tuple",
                        }

                        if tbl.entry_type in native_types:
                            # Show native types in lowercase
                            entry_type_display = tbl.entry_type
                        else:
                            # For model IDs, look up the model name
                            model = system.get_model(tbl.entry_type)
                            entry_type_display = model.name if model else tbl.entry_type

                    table.add_row(
                        tbl.id or table_id,
                        tbl.name or "-",
                        tbl.description or "-",
                        entry_type_display,
                        str(len(tbl.entries)),
                        tbl.roll or "-",
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
        raise typer.Exit(1) from None


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
