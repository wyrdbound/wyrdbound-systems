"""Textual-based compendium browser for GRIMOIRE systems."""

import logging
from typing import Optional, Dict, Any, List
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import (
    Header, Footer, Static, Button, Input, DataTable, 
    SelectionList, Tree, Label, Rule, Collapsible,
    TabbedContent, TabPane, TextArea
)
from textual.binding import Binding
from textual.screen import Screen

from ..models.system import System
from ..models.compendium import CompendiumDefinition

logger = logging.getLogger(__name__)


class CompendiumDetailScreen(Screen):
    """Screen for viewing detailed compendium entry information."""
    
    def __init__(self, entry_id: str, entry_data: Dict[str, Any]):
        super().__init__()
        self.entry_id = entry_id
        self.entry_data = entry_data
    
    def compose(self) -> ComposeResult:
        """Create the detail view."""
        yield Header(show_clock=True)
        
        yield Container(
            Label(f"Entry: {self.entry_id}", classes="detail-title"),
            Rule(),
            TextArea(
                self._format_entry_data(),
                read_only=True,
                id="entry-content"
            ),
            Button("Back", id="back", variant="primary"),
            classes="detail-container"
        )
        
        yield Footer()
    
    def _format_entry_data(self) -> str:
        """Format entry data for display."""
        lines = []
        
        def format_value(value, indent=0):
            prefix = "  " * indent
            if isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"{prefix}{k}:")
                    format_value(v, indent + 1)
            elif isinstance(value, list):
                for item in value:
                    lines.append(f"{prefix}- {item}")
            else:
                lines.append(f"{prefix}{value}")
        
        format_value(self.entry_data)
        return "\n".join(lines)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "back":
            self.app.pop_screen()


class CompendiumBrowserApp(App):
    """Textual application for browsing compendium content."""
    
    CSS = """
    .browser-container {
        padding: 1;
    }
    
    .category-tree {
        width: 30%;
        border: solid $primary;
    }
    
    .entry-list {
        width: 40%;
        border: solid $accent;
    }
    
    .entry-preview {
        width: 30%;
        border: solid $success;
        padding: 1;
    }
    
    .detail-container {
        padding: 1;
    }
    
    .detail-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin: 1;
    }
    
    #entry-content {
        height: 1fr;
    }
    
    .empty-state {
        text-align: center;
        color: $text-muted;
        margin: 2;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
        Binding("enter", "view_entry", "View Entry"),
    ]
    
    def __init__(self, system: System):
        super().__init__()
        self.system = system
        self.compendiums = system.compendiums
        self.current_compendium: Optional[CompendiumDefinition] = None
        self.current_category: Optional[str] = None
        self.current_entries: List[str] = []
    
    def compose(self) -> ComposeResult:
        """Create the browser layout."""
        yield Header(show_clock=True)
        
        if not self.compendiums:
            yield Container(
                Label("No compendiums available in this system", classes="empty-state"),
                Button("Close", id="close", variant="primary"),
                classes="browser-container"
            )
        else:
            yield Container(
                Horizontal(
                    self._create_category_tree(),
                    self._create_entry_list(),
                    self._create_entry_preview(),
                ),
                classes="browser-container"
            )
        
        yield Footer()
    
    def _create_category_tree(self) -> Tree:
        """Create the category tree widget."""
        tree = Tree("Compendiums", classes="category-tree")
        tree.border_title = "Categories"
        
        for comp_id, compendium in self.compendiums.items():
            comp_node = tree.root.add(comp_id, data={"type": "compendium", "id": comp_id})
            
            if hasattr(compendium, 'entries') and compendium.entries:
                # Group entries by category if they have one
                categories = {}
                for entry_id, entry_data in compendium.entries.items():
                    category = "General"
                    if isinstance(entry_data, dict) and 'category' in entry_data:
                        category = entry_data['category']
                    
                    if category not in categories:
                        categories[category] = []
                    categories[category].append(entry_id)
                
                for category, entries in categories.items():
                    cat_node = comp_node.add(
                        f"{category} ({len(entries)})",
                        data={"type": "category", "compendium": comp_id, "category": category}
                    )
                    for entry_id in entries:
                        cat_node.add_leaf(
                            entry_id,
                            data={"type": "entry", "compendium": comp_id, "entry": entry_id}
                        )
        
        return tree
    
    def _create_entry_list(self) -> SelectionList:
        """Create the entry list widget."""
        selection_list = SelectionList(classes="entry-list")
        selection_list.border_title = "Entries"
        return selection_list
    
    def _create_entry_preview(self) -> Static:
        """Create the entry preview widget."""
        preview = Static("Select an entry to view details", classes="entry-preview")
        preview.border_title = "Preview"
        return preview
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node_data = event.node.data
        
        if not node_data:
            return
        
        if node_data["type"] == "category":
            self._load_category_entries(node_data["compendium"], node_data["category"])
        elif node_data["type"] == "entry":
            self._preview_entry(node_data["compendium"], node_data["entry"])
    
    def _load_category_entries(self, comp_id: str, category: str) -> None:
        """Load entries for a specific category."""
        compendium = self.compendiums[comp_id]
        entry_list = self.query_one(SelectionList)
        
        # Clear current entries
        entry_list.clear_options()
        
        # Add entries for this category
        if hasattr(compendium, 'entries') and compendium.entries:
            for entry_id, entry_data in compendium.entries.items():
                entry_category = "General"
                if isinstance(entry_data, dict) and 'category' in entry_data:
                    entry_category = entry_data['category']
                
                if entry_category == category:
                    entry_list.add_option((entry_id, entry_id))
        
        self.current_compendium = compendium
        self.current_category = category
    
    def _preview_entry(self, comp_id: str, entry_id: str) -> None:
        """Preview an entry in the preview pane."""
        compendium = self.compendiums[comp_id]
        preview = self.query_one(".entry-preview", Static)
        
        if hasattr(compendium, 'entries') and entry_id in compendium.entries:
            entry_data = compendium.entries[entry_id]
            preview_text = self._format_entry_preview(entry_id, entry_data)
            preview.update(preview_text)
        else:
            preview.update(f"Entry '{entry_id}' not found")
    
    def _format_entry_preview(self, entry_id: str, entry_data: Any) -> str:
        """Format entry data for preview."""
        lines = [f"[bold]{entry_id}[/bold]", ""]
        
        if isinstance(entry_data, dict):
            for key, value in list(entry_data.items())[:5]:  # Show first 5 fields
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"[dim]{key}:[/dim] {value}")
                else:
                    lines.append(f"[dim]{key}:[/dim] {type(value).__name__}")
            
            if len(entry_data) > 5:
                lines.append(f"... and {len(entry_data) - 5} more fields")
        else:
            lines.append(str(entry_data))
        
        return "\n".join(lines)
    
    def on_selection_list_option_selected(self, event: SelectionList.OptionSelected) -> None:
        """Handle entry selection."""
        if self.current_compendium:
            entry_id = event.option_id
            if hasattr(self.current_compendium, 'entries') and entry_id in self.current_compendium.entries:
                entry_data = self.current_compendium.entries[entry_id]
                self._preview_entry(
                    next(k for k, v in self.compendiums.items() if v == self.current_compendium),
                    entry_id
                )
    
    def action_view_entry(self) -> None:
        """View the selected entry in detail."""
        entry_list = self.query_one(SelectionList)
        
        if entry_list.selected and self.current_compendium:
            entry_id = entry_list.selected[0]
            if hasattr(self.current_compendium, 'entries') and entry_id in self.current_compendium.entries:
                entry_data = self.current_compendium.entries[entry_id]
                self.push_screen(CompendiumDetailScreen(entry_id, entry_data))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close":
            self.exit()
    
    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "dark" if self.theme == "light" else "light"


def run_compendium_browser(system: System) -> None:
    """Run the Textual compendium browser."""
    app = CompendiumBrowserApp(system)
    app.run()


# Legacy class for backwards compatibility
class CompendiumBrowser:
    """Legacy compendium browser - redirects to Textual app."""
    
    def __init__(self, compendium=None, system=None):
        self.system = system
        self.compendium = compendium
    
    def browse(self) -> None:
        """Browse compendium using Textual interface."""
        if self.system:
            run_compendium_browser(self.system)
        else:
            print("No system available for browsing")
