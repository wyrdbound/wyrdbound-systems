"""Textual-based compendium browser for GRIMOIRE systems."""

import logging
from typing import Optional, Dict, Any, List
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import (
    Header, Footer, Static, Button, Input, DataTable, 
    Tree, Label, Rule, Collapsible,
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
        width: 50%;
        border: solid $primary;
    }
    
    .entry-preview {
        width: 50%;
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
        
        if node_data["type"] == "entry":
            self._preview_entry(node_data["compendium"], node_data["entry"])
    
    def _preview_entry(self, comp_id: str, entry_id: str) -> None:
        """Preview an entry in the preview pane."""
        compendium = self.compendiums[comp_id]
        preview = self.query_one(".entry-preview", Static)
        
        if hasattr(compendium, 'entries') and entry_id in compendium.entries:
            entry_data = compendium.entries[entry_id]
            # Try to get resolved entry data with model defaults
            resolved_data = self._resolve_entry_with_model(compendium, entry_data)
            preview_text = self._format_entry_preview(entry_id, resolved_data)
            preview.update(preview_text)
        else:
            preview.update(f"Entry '{entry_id}' not found")
    
    def _resolve_entry_with_model(self, compendium: CompendiumDefinition, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve entry data with model defaults and inherited attributes."""
        # Start with the original entry data
        resolved_data = entry_data.copy()
        
        # Try to get the model definition for this compendium
        if hasattr(compendium, 'model') and compendium.model in self.system.models:
            # Get all inherited attributes by resolving the model hierarchy
            all_attributes = self._resolve_model_attributes(compendium.model)
            
            # Add any default values from the model hierarchy that aren't in the entry
            for attr_name, attr_def in all_attributes.items():
                if attr_name not in resolved_data:
                    # Handle both AttributeDefinition objects and dict representations
                    if hasattr(attr_def, 'default') and attr_def.default is not None:
                        resolved_data[attr_name] = attr_def.default
                    elif isinstance(attr_def, dict) and 'default' in attr_def and attr_def['default'] is not None:
                        resolved_data[attr_name] = attr_def['default']
        
        return resolved_data
    
    def _resolve_model_attributes(self, model_id: str, visited: set = None) -> Dict[str, Any]:
        """Resolve model attributes including inheritance hierarchy."""
        if visited is None:
            visited = set()
        
        # Prevent infinite recursion
        if model_id in visited:
            return {}
        visited.add(model_id)
        
        if model_id not in self.system.models:
            return {}
        
        model = self.system.models[model_id]
        all_attributes = {}
        
        # First, resolve parent models (depth-first)
        if hasattr(model, 'extends') and model.extends:
            for parent_model in model.extends:
                parent_attributes = self._resolve_model_attributes(parent_model, visited)
                all_attributes.update(parent_attributes)
        
        # Then add/override with this model's attributes
        all_attributes.update(model.attributes)
        
        return all_attributes
    
    def _format_entry_preview(self, entry_id: str, entry_data: Any) -> str:
        """Format entry data for preview."""
        lines = [f"[bold]{entry_id}[/bold]", ""]
        
        if isinstance(entry_data, dict):
            for key, value in entry_data.items():  # Show all fields
                if isinstance(value, (str, int, float, bool)):
                    lines.append(f"[dim]{key}:[/dim] {value}")
                elif isinstance(value, list):
                    # Special handling for tags - show as sorted, comma-separated
                    if key.lower() == 'tags':
                        if len(value) == 0:
                            lines.append(f"[dim]{key}:[/dim] (none)")
                        else:
                            # Sort tags and join with commas
                            sorted_tags = sorted(str(tag) for tag in value)
                            tags_str = ", ".join(sorted_tags)
                            lines.append(f"[dim]{key}:[/dim] {tags_str}")
                    else:
                        # Show actual list contents for other lists
                        if len(value) == 0:
                            lines.append(f"[dim]{key}:[/dim] []")
                        elif len(value) <= 3:
                            # Show short lists in full
                            list_str = ", ".join(str(item) for item in value)
                            lines.append(f"[dim]{key}:[/dim] [{list_str}]")
                        else:
                            # Show first few items for longer lists
                            preview_items = ", ".join(str(item) for item in value[:3])
                            lines.append(f"[dim]{key}:[/dim] [{preview_items}, ...{len(value)-3} more]")
                elif isinstance(value, dict):
                    if len(value) == 0:
                        lines.append(f"[dim]{key}:[/dim] {{}}")
                    else:
                        # Show first key-value pair as preview
                        first_key = next(iter(value))
                        preview = f"{first_key}: {value[first_key]}"
                        if len(value) > 1:
                            lines.append(f"[dim]{key}:[/dim] {{{preview}, ...{len(value)-1} more}}")
                        else:
                            lines.append(f"[dim]{key}:[/dim] {{{preview}}}")
                else:
                    lines.append(f"[dim]{key}:[/dim] {type(value).__name__}")
        else:
            lines.append(str(entry_data))
        
        return "\n".join(lines)
    
    def action_view_entry(self) -> None:
        """View the selected entry in detail."""
        tree = self.query_one(Tree)
        
        if tree.cursor_node and tree.cursor_node.data:
            node_data = tree.cursor_node.data
            if node_data["type"] == "entry":
                comp_id = node_data["compendium"]
                entry_id = node_data["entry"]
                compendium = self.compendiums[comp_id]
                
                if hasattr(compendium, 'entries') and entry_id in compendium.entries:
                    entry_data = compendium.entries[entry_id]
                    self.push_screen(CompendiumDetailScreen(entry_id, entry_data))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close":
            self.exit()
    
    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.theme = "textual-light" if self.theme == "textual-dark" else "textual-dark"


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
