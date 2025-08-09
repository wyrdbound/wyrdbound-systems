"""Rich-based compendium browser with accessibility features."""

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from ..core.engine import GrimoireEngine


class RichBrowser:
    """Rich-based compendium browser with accessibility features."""

    def __init__(self, system_path: Path):
        self.system_path = system_path
        self.console = Console()
        self.engine = GrimoireEngine()
        self.system = None
        self.current_compendium = None
        self.current_entries = []
        self.current_page = 0
        self.entries_per_page = 10

    def run(self) -> None:
        """Run the Rich browser interface."""
        try:
            self._initialize()
            self._main_loop()
        except Exception as e:
            self.console.print(f"[red]Error: {e}[/red]")

    def _initialize(self) -> None:
        """Initialize the system."""
        # Header
        self.console.print()
        self.console.print(
            Panel.fit(
                "[bold cyan]GRIMOIRE Compendium Browser[/bold cyan]\n"
                f"[dim]System: {self.system_path.name}[/dim]",
                border_style="cyan",
            )
        )

        # Load system
        with self.console.status("[bold blue]Loading system...", spinner="dots"):
            self.system = self.engine.load_system(self.system_path)

        self.console.print(f"[green]✅ Loaded system: {self.system.name}[/green]")
        if self.system.description:
            self.console.print(f"[dim]{self.system.description}[/dim]")
        self.console.print()

    def _main_loop(self) -> None:
        """Main browser loop."""
        while True:
            try:
                if self.current_compendium is None:
                    # Show compendium selection
                    if not self._select_compendium():
                        break
                else:
                    # Show entries and handle navigation
                    if not self._browse_entries():
                        self.current_compendium = None
                        self.current_entries = []
                        self.current_page = 0

            except KeyboardInterrupt:
                break

        self.console.print("[yellow]Goodbye![/yellow]")

    def _select_compendium(self) -> bool:
        """Select a compendium to browse."""
        if not self.system.compendiums:
            self.console.print("[yellow]No compendiums found in this system.[/yellow]")
            return False

        # Display available compendiums
        compendia_table = Table(title="Available Compendiums", show_header=True)
        compendia_table.add_column("Option", style="cyan", justify="right")
        compendia_table.add_column("Name", style="green")
        compendia_table.add_column("Description", style="dim")
        compendia_table.add_column("Entries", style="yellow")

        compendium_map = {}
        for i, (comp_id, compendium) in enumerate(self.system.compendiums.items(), 1):
            entry_count = (
                len(compendium.entries) if hasattr(compendium, "entries") else 0
            )
            description = getattr(compendium, "description", "") or "No description"

            compendia_table.add_row(
                str(i), compendium.name, description, str(entry_count)
            )
            compendium_map[str(i)] = comp_id

        self.console.print(compendia_table)
        self.console.print()

        # Get user selection
        choices_text = " / ".join([str(i) for i in range(1, len(compendium_map) + 1)])

        while True:
            try:
                response = Prompt.ask(
                    f"Select a compendium ({choices_text}) or 'q' to quit",
                    console=self.console,
                )

                if response.lower() == "q":
                    return False

                if response in compendium_map:
                    comp_id = compendium_map[response]
                    self.current_compendium = self.system.compendiums[comp_id]
                    self.current_entries = list(self.current_compendium.entries.items())
                    self.current_page = 0
                    return True
                else:
                    self.console.print(
                        f"[red]Invalid choice. Please enter one of: {choices_text}[/red]"
                    )

            except KeyboardInterrupt:
                return False

    def _browse_entries(self) -> bool:
        """Browse entries in the current compendium."""
        if not self.current_entries:
            self.console.print("[yellow]No entries found in this compendium.[/yellow]")
            if Confirm.ask("Return to compendium selection?", default=True):
                return False
            return True

        while True:
            # Show current page of entries
            self._show_entries_page()

            # Show navigation options
            self._show_navigation_menu()

            # Get user input
            try:
                response = Prompt.ask("Enter command", console=self.console).lower()

                if response == "q":
                    return False
                elif response == "b":
                    return False  # Back to compendium selection
                elif response == "n":
                    if self._has_next_page():
                        self.current_page += 1
                    else:
                        self.console.print("[yellow]Already on the last page.[/yellow]")
                elif response == "p":
                    if self.current_page > 0:
                        self.current_page -= 1
                    else:
                        self.console.print(
                            "[yellow]Already on the first page.[/yellow]"
                        )
                elif response.startswith("v "):
                    # View specific entry
                    try:
                        entry_num = int(response[2:])
                        self._view_entry(entry_num)
                    except ValueError:
                        self.console.print("[red]Invalid entry number.[/red]")
                elif response == "h":
                    self._show_help()
                else:
                    self.console.print("[red]Unknown command. Type 'h' for help.[/red]")

            except KeyboardInterrupt:
                return False

    def _show_entries_page(self) -> None:
        """Show the current page of entries."""
        start_idx = self.current_page * self.entries_per_page
        end_idx = min(start_idx + self.entries_per_page, len(self.current_entries))

        entries_table = Table(
            title=f"{self.current_compendium.name} - Page {self.current_page + 1}",
            show_header=True,
        )
        entries_table.add_column("Entry", style="cyan", justify="right")
        entries_table.add_column("Name", style="green")
        entries_table.add_column("Type", style="yellow")
        entries_table.add_column("Preview", style="dim")

        for i, (entry_id, entry) in enumerate(
            self.current_entries[start_idx:end_idx], 1
        ):
            entry_name = getattr(entry, "name", entry_id)
            entry_type = type(entry).__name__

            # Create a brief preview
            preview = ""
            if hasattr(entry, "description") and entry.description:
                preview = (
                    entry.description[:50] + "..."
                    if len(entry.description) > 50
                    else entry.description
                )
            elif hasattr(entry, "content") and entry.content:
                preview = (
                    str(entry.content)[:50] + "..."
                    if len(str(entry.content)) > 50
                    else str(entry.content)
                )

            entries_table.add_row(str(i), entry_name, entry_type, preview)

        self.console.print()
        self.console.print(entries_table)

        # Show page info
        total_pages = (
            len(self.current_entries) + self.entries_per_page - 1
        ) // self.entries_per_page
        self.console.print(
            f"[dim]Showing entries {start_idx + 1}-{end_idx} of {len(self.current_entries)} (Page {self.current_page + 1} of {total_pages})[/dim]"
        )

    def _show_navigation_menu(self) -> None:
        """Show navigation menu."""
        nav_table = Table(show_header=False, box=None)
        nav_table.add_column("Command", style="cyan")
        nav_table.add_column("Description", style="white")

        nav_table.add_row("v <num>", "View entry details (e.g., 'v 1')")

        if self.current_page > 0:
            nav_table.add_row("p", "Previous page")
        if self._has_next_page():
            nav_table.add_row("n", "Next page")

        nav_table.add_row("b", "Back to compendium selection")
        nav_table.add_row("h", "Show help")
        nav_table.add_row("q", "Quit")

        self.console.print()
        self.console.print(Panel(nav_table, title="Navigation", border_style="blue"))

    def _has_next_page(self) -> bool:
        """Check if there's a next page."""
        return (self.current_page + 1) * self.entries_per_page < len(
            self.current_entries
        )

    def _view_entry(self, entry_num: int) -> None:
        """View detailed information about an entry."""
        start_idx = self.current_page * self.entries_per_page
        actual_idx = start_idx + entry_num - 1

        if actual_idx < 0 or actual_idx >= len(self.current_entries):
            self.console.print(
                f"[red]Invalid entry number. Please choose 1-{min(self.entries_per_page, len(self.current_entries) - start_idx)}[/red]"
            )
            return

        entry_id, entry = self.current_entries[actual_idx]

        # Create detailed view
        self.console.print()
        self.console.print(
            Panel.fit(
                f"[bold]{getattr(entry, 'name', entry_id)}[/bold]\n"
                f"[dim]ID: {entry_id}[/dim]\n"
                f"[dim]Type: {type(entry).__name__}[/dim]",
                border_style="green",
                title="Entry Details",
            )
        )

        # Show entry data in a structured format
        details_table = Table(show_header=False)
        details_table.add_column("Property", style="cyan")
        details_table.add_column("Value", style="white", overflow="fold")

        # Iterate through entry attributes
        entry if isinstance(entry, dict) else entry.__dict__ if hasattr(
            entry, "__dict__"
        ) else {}

        # If it's a raw dict (like the compendium entries), display it directly
        if isinstance(entry, dict):
            for key, value in entry.items():
                if value is not None:
                    # Format complex values
                    if isinstance(value, dict | list):
                        value = json.dumps(value, indent=2)
                    elif isinstance(value, str) and len(value) > 100:
                        # Wrap long text
                        value = value[:200] + "..." if len(value) > 200 else value

                    details_table.add_row(key.title(), str(value))
        else:
            # For objects with attributes
            for attr_name in dir(entry):
                if not attr_name.startswith("_") and not callable(
                    getattr(entry, attr_name)
                ):
                    attr_value = getattr(entry, attr_name)
                    if attr_value is not None:
                        # Format complex values
                        if isinstance(attr_value, dict | list):
                            attr_value = json.dumps(attr_value, indent=2)
                        elif isinstance(attr_value, str) and len(attr_value) > 100:
                            # Wrap long text
                            attr_value = (
                                attr_value[:200] + "..."
                                if len(attr_value) > 200
                                else attr_value
                            )

                        details_table.add_row(attr_name.title(), str(attr_value))

        self.console.print(details_table)

        # Wait for user to continue
        self.console.print()
        Prompt.ask("Press Enter to continue", default="", show_default=False)

    def _show_help(self) -> None:
        """Show help information."""
        help_content = """
[bold cyan]GRIMOIRE Compendium Browser Help[/bold cyan]

[bold]Navigation Commands:[/bold]
• [cyan]v <num>[/cyan] - View detailed information about entry number <num>
• [cyan]n[/cyan] - Go to next page (if available)
• [cyan]p[/cyan] - Go to previous page (if available)
• [cyan]b[/cyan] - Go back to compendium selection
• [cyan]h[/cyan] - Show this help
• [cyan]q[/cyan] - Quit the browser

[bold]Tips for Accessibility:[/bold]
• All commands are single letters for quick access
• Entry details are displayed in a structured, screen-reader friendly format
• Page navigation shows clear context about current position
• Long text is automatically wrapped and truncated when needed

[bold]Example Usage:[/bold]
• Type [cyan]v 1[/cyan] to view the first entry on the current page
• Type [cyan]n[/cyan] to go to the next page
• Type [cyan]b[/cyan] to select a different compendium
"""
        self.console.print()
        self.console.print(Panel(help_content, border_style="blue"))
        self.console.print()
        Prompt.ask("Press Enter to continue", default="", show_default=False)


def run_rich_browser(system_path: Path) -> None:
    """Run the Rich compendium browser."""
    browser = RichBrowser(system_path)
    browser.run()
