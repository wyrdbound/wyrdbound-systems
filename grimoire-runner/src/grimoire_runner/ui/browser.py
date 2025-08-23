"""Compendium browser for exploring system content."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


class CompendiumBrowser:
    """Interactive browser for exploring compendium content."""

    def __init__(self, system):
        self.system = system

    def list_compendiums(self) -> None:
        """List all available compendiums."""
        compendiums = self.system.list_compendiums()

        if not compendiums:
            console.print("[yellow]No compendiums found in system[/yellow]")
            return

        console.print(f"[bold blue]Compendiums in {self.system.name}[/bold blue]\n")

        table = Table()
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Model", style="magenta")
        table.add_column("Entries", style="green", justify="right")
        table.add_column("Description", style="dim")

        for comp_name in compendiums:
            comp = self.system.get_compendium(comp_name)
            table.add_row(
                comp.name,
                comp.model,
                str(len(comp.entries)),
                f"Based on {comp.model} model",
            )

        console.print(table)
        console.print(
            "\n[dim]Use: grimoire-runner browse <system> --compendium <name> to explore entries[/dim]"
        )

    def browse_compendium(
        self, compendium_name: str, search_term: str | None = None
    ) -> None:
        """Browse a specific compendium."""
        compendium = self.system.get_compendium(compendium_name)

        if not compendium:
            console.print(f"[red]Compendium '{compendium_name}' not found[/red]")
            available = self.system.list_compendiums()
            if available:
                console.print(f"Available compendiums: {', '.join(available)}")
            return

        console.print(f"[bold blue]Browsing: {compendium.name}[/bold blue]")
        console.print(
            f"[dim]Model: {compendium.model} | Entries: {len(compendium.entries)}[/dim]\n"
        )

        # Filter entries if search term provided
        entries_to_show = compendium.entries
        if search_term:
            entries_to_show = compendium.search_entries(search_term)
            console.print(
                f"[yellow]Filtered by '{search_term}': {len(entries_to_show)} matches[/yellow]\n"
            )

        if not entries_to_show:
            console.print("[yellow]No entries found[/yellow]")
            return

        # Get model to understand structure
        self.system.get_model(compendium.model)

        # Create table with dynamic columns based on common attributes
        table = Table()
        table.add_column("ID", style="cyan", no_wrap=True)

        # Analyze entries to find common attributes for columns
        common_attrs = self._find_common_attributes(entries_to_show)

        for attr in common_attrs[:5]:  # Limit to 5 columns for readability
            table.add_column(attr.title(), style="magenta")

        # Add entries to table
        for entry_id, entry_data in list(entries_to_show.items())[
            :20
        ]:  # Limit to 20 entries
            row = [entry_id]

            for attr in common_attrs[:5]:
                value = entry_data.get(attr, "")
                if isinstance(value, dict | list):
                    value = (
                        str(value)[:30] + "..." if len(str(value)) > 30 else str(value)
                    )
                else:
                    value = str(value)
                row.append(value)

            table.add_row(*row)

        console.print(table)

        if len(entries_to_show) > 20:
            console.print(
                f"\n[dim]Showing first 20 of {len(entries_to_show)} entries[/dim]"
            )

        # Show detailed view option
        if len(entries_to_show) <= 10:
            self._offer_detailed_view(entries_to_show)

    def _find_common_attributes(self, entries: dict[str, Any]) -> list[str]:
        """Find the most common attributes across entries."""
        attr_counts = {}

        for entry_data in entries.values():
            for attr in entry_data.keys():
                attr_counts[attr] = attr_counts.get(attr, 0) + 1

        # Sort by frequency, prioritizing GRIMOIRE standard root-level fields
        # These are part of the GRIMOIRE specification and should be supported by UI
        grimoire_standard_fields = [
            # Universal GRIMOIRE root-level fields (from spec)
            "kind", "id", "name", "description", "version",
            # Content-type specific GRIMOIRE root-level fields
            "model", "roll", "entry_type", "entries", "attributes", "extends", "validations",
            # Common display fields that systems may choose to use
            "display_name", "title", "label", "type"
        ]

        # Sort attributes by frequency and priority
        sorted_attrs = sorted(
            attr_counts.keys(),
            key=lambda x: (
                -attr_counts[x],  # Higher frequency first
                0 if x in grimoire_standard_fields else 1,  # GRIMOIRE standard fields first
                x,  # Alphabetical as tiebreaker
            ),
        )

        return sorted_attrs

    def _offer_detailed_view(self, entries: dict[str, Any]) -> None:
        """Offer to show detailed view of entries."""
        console.print(
            "\n[dim]Would you like to see detailed views? (y/n)[/dim]", end=" "
        )

        try:
            response = input().strip().lower()
            if response in ["y", "yes"]:
                self._show_detailed_entries(entries)
        except (EOFError, KeyboardInterrupt):
            console.print()

    def _show_detailed_entries(self, entries: dict[str, Any]) -> None:
        """Show detailed view of entries."""
        for entry_id, entry_data in entries.items():
            console.print(f"\n[bold cyan]{entry_id}[/bold cyan]")

            # Create a formatted view of the entry
            content = ""
            for key, value in entry_data.items():
                if isinstance(value, dict):
                    content += f"[yellow]{key}:[/yellow]\n"
                    for sub_key, sub_value in value.items():
                        content += f"  {sub_key}: {sub_value}\n"
                elif isinstance(value, list):
                    content += f"[yellow]{key}:[/yellow] {', '.join(map(str, value))}\n"
                else:
                    content += f"[yellow]{key}:[/yellow] {value}\n"

            console.print(
                Panel(
                    content.rstrip(),
                    title=entry_id,
                    border_style="blue",
                    padding=(0, 1),
                )
            )

            # Pause between entries for large lists
            if len(entries) > 5:
                try:
                    console.print(
                        "[dim](Press Enter for next entry, Ctrl+C to stop)[/dim]"
                    )
                    input()
                except KeyboardInterrupt:
                    console.print("\n[dim]Stopped browsing entries[/dim]")
                    break

    def search_across_compendiums(self, search_term: str) -> None:
        """Search across all compendiums in the system."""
        console.print(
            f"[bold blue]Searching all compendiums for '{search_term}'[/bold blue]\n"
        )

        total_matches = 0

        for comp_name in self.system.list_compendiums():
            comp = self.system.get_compendium(comp_name)
            matches = comp.search_entries(search_term)

            if matches:
                console.print(f"[cyan]{comp.name}[/cyan]: {len(matches)} matches")

                # Show first few matches
                for entry_id, entry_data in list(matches.items())[:3]:
                    display_name = self._get_entry_display_name(entry_data, entry_id)
                    console.print(f"  • {display_name}")

                if len(matches) > 3:
                    console.print(f"  ... and {len(matches) - 3} more")

                total_matches += len(matches)
                console.print()

        if total_matches == 0:
            console.print(f"[yellow]No matches found for '{search_term}'[/yellow]")
        else:
            console.print(f"[green]Total matches: {total_matches}[/green]")

    def analyze_compendium(self, compendium_name: str) -> None:
        """Analyze and show statistics about a compendium."""
        compendium = self.system.get_compendium(compendium_name)

        if not compendium:
            console.print(f"[red]Compendium '{compendium_name}' not found[/red]")
            return

        console.print(f"[bold blue]Analysis: {compendium.name}[/bold blue]\n")

        # Basic stats
        console.print("[cyan]Basic Statistics:[/cyan]")
        console.print(f"  Total entries: {len(compendium.entries)}")
        console.print(f"  Model type: {compendium.model}")

        # Attribute analysis
        all_attrs = set()
        attr_coverage = {}

        for entry_data in compendium.entries.values():
            entry_attrs = set(entry_data.keys())
            all_attrs.update(entry_attrs)

            for attr in entry_attrs:
                attr_coverage[attr] = attr_coverage.get(attr, 0) + 1

        console.print("\n[cyan]Attribute Coverage:[/cyan]")
        for attr in sorted(all_attrs):
            coverage = attr_coverage[attr]
            percentage = (coverage / len(compendium.entries)) * 100
            console.print(
                f"  {attr}: {coverage}/{len(compendium.entries)} ({percentage:.1f}%)"
            )

        console.print(f"\n[cyan]Unique attributes:[/cyan] {len(all_attrs)}")

        # Value analysis for numeric attributes
        numeric_attrs = self._find_numeric_attributes(compendium.entries)
        if numeric_attrs:
            self._analyze_attribute_values(compendium.entries, numeric_attrs)

    def _analyze_attribute_values(
        self, entries: dict[str, Any], attributes: list[str]
    ) -> None:
        """Analyze the distribution of values for specific attributes."""
        console.print("\n[cyan]Value Analysis:[/cyan]")

        for attr in attributes:
            values = []
            for entry_data in entries.values():
                if attr in entry_data:
                    value = entry_data[attr]
                    if isinstance(value, int | float):
                        values.append(value)

            if values:
                console.print(f"  {attr}:")
                console.print(f"    Min: {min(values)}")
                console.print(f"    Max: {max(values)}")
                console.print(f"    Avg: {sum(values) / len(values):.2f}")
                console.print(f"    Count: {len(values)}")
            else:
                console.print(f"  {attr}: No numeric values found")

    def _get_entry_display_name(self, entry_data: dict[str, Any], entry_id: str) -> str:
        """Get a display name for an entry in a system-agnostic way."""
        # Try common identifying fields in order of preference
        identifier_fields = ['name', 'title', 'label', 'display_name', 'id']

        for field in identifier_fields:
            if field in entry_data and entry_data[field]:
                return str(entry_data[field])

        # Fallback to the entry ID if no identifying field is found
        return entry_id

    def _find_numeric_attributes(self, entries: dict[str, Any]) -> list[str]:
        """Find attributes that contain numeric values in a system-agnostic way."""
        numeric_attrs = []

        # Sample a few entries to check for numeric attributes
        sample_entries = list(entries.values())[:10]  # Check first 10 entries

        if not sample_entries:
            return numeric_attrs

        # Find attributes that have numeric values in most sampled entries
        potential_attrs = set()
        for entry in sample_entries:
            potential_attrs.update(entry.keys())

        for attr in potential_attrs:
            numeric_count = 0
            for entry in sample_entries:
                if attr in entry:
                    value = entry[attr]
                    # Check if the value is numeric or can be converted to numeric
                    if isinstance(value, int | float):
                        numeric_count += 1
                    elif isinstance(value, str):
                        try:
                            float(value)
                            numeric_count += 1
                        except (ValueError, TypeError):
                            pass

            # If more than 50% of samples have numeric values for this attribute, include it
            if numeric_count > len(sample_entries) * 0.5:
                numeric_attrs.append(attr)

        # Limit to most common numeric attributes to keep output manageable
        return numeric_attrs[:5]
