"""Textual-based interactive interface for GRIMOIRE runner."""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import (
    Header, Footer, Static, Button, Input, DataTable, 
    SelectionList, ProgressBar, Log, TabbedContent, TabPane,
    Tree, Label, Rule, Collapsible
)
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from textual.screen import Screen

from ..core.engine import GrimoireEngine
from ..models.system import System
from ..models.context_data import ExecutionContext

logger = logging.getLogger(__name__)


class FlowExecutionScreen(Screen):
    """Screen for executing flows with progress tracking."""
    
    def __init__(self, system: System, flow_id: str, engine: GrimoireEngine):
        super().__init__()
        self.system = system
        self.flow_id = flow_id
        self.engine = engine
        self.context = engine.create_execution_context()
    
    def compose(self) -> ComposeResult:
        """Create the flow execution screen."""
        yield Header(show_clock=True)
        yield Container(
            Label(f"Executing flow: {self.flow_id}", classes="title"),
            ProgressBar(id="flow-progress"),
            Log(id="execution-log"),
            Static("", id="results"),
            classes="flow-container"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Execute the flow when screen mounts."""
        self.execute_flow()
    
    def execute_flow(self) -> None:
        """Execute the selected flow."""
        log = self.query_one("#execution-log", Log)
        progress = self.query_one("#flow-progress", ProgressBar)
        results = self.query_one("#results", Static)
        
        log.write_line(f"Starting execution of flow: {self.flow_id}")
        progress.update(progress=10)
        
        try:
            result = self.engine.execute_flow(self.flow_id, self.context, self.system)
            progress.update(progress=100)
            
            if result.success:
                log.write_line("✓ Flow executed successfully!")
                if result.outputs:
                    results.update(f"Results: {result.outputs}")
            else:
                log.write_line(f"✗ Flow execution failed: {result.error}")
                
        except Exception as e:
            log.write_line(f"✗ Error executing flow: {e}")
            progress.update(progress=100)


class SystemExplorerScreen(Screen):
    """Screen for exploring system components."""
    
    def __init__(self, system: System, engine: GrimoireEngine):
        super().__init__()
        self.system = system
        self.engine = engine
    
    def compose(self) -> ComposeResult:
        """Create the system explorer screen."""
        yield Header(show_clock=True)
        
        with TabbedContent(initial="flows"):
            with TabPane("Flows", id="flows"):
                yield self._create_flows_tab()
            
            with TabPane("Models", id="models"):
                yield self._create_models_tab()
            
            with TabPane("Compendiums", id="compendiums"):
                yield self._create_compendiums_tab()
            
            with TabPane("Tables", id="tables"):
                yield self._create_tables_tab()
        
        yield Footer()
    
    def _create_flows_tab(self) -> Container:
        """Create the flows exploration tab."""
        flows = list(self.system.flows.keys())
        
        if not flows:
            return Container(
                Label("No flows available in this system", classes="empty-state")
            )
        
        selection_list = SelectionList(*[(flow, flow) for flow in flows])
        selection_list.border_title = "Available Flows"
        
        return Container(
            selection_list,
            Button("Execute Selected Flow", id="execute-flow", variant="primary"),
            classes="tab-container"
        )
    
    def _create_models_tab(self) -> Container:
        """Create the models exploration tab."""
        models = list(self.system.models.keys())
        
        if not models:
            return Container(
                Label("No models available in this system", classes="empty-state")
            )
        
        tree = Tree("Models")
        for model_id in models:
            model = self.system.models[model_id]
            node = tree.root.add(model_id)
            if hasattr(model, 'fields') and model.fields:
                for field_name, field_def in model.fields.items():
                    node.add_leaf(f"{field_name}: {field_def.type}")
        
        return Container(tree, classes="tab-container")
    
    def _create_compendiums_tab(self) -> Container:
        """Create the compendiums exploration tab."""
        compendiums = list(self.system.compendiums.keys())
        
        if not compendiums:
            return Container(
                Label("No compendiums available in this system", classes="empty-state")
            )
        
        tree = Tree("Compendiums")
        for comp_id in compendiums:
            comp = self.system.compendiums[comp_id]
            node = tree.root.add(comp_id)
            if hasattr(comp, 'entries') and comp.entries:
                for entry_id in comp.entries.keys():
                    node.add_leaf(entry_id)
        
        return Container(tree, classes="tab-container")
    
    def _create_tables_tab(self) -> Container:
        """Create the tables exploration tab."""
        tables = list(self.system.tables.keys())
        
        if not tables:
            return Container(
                Label("No tables available in this system", classes="empty-state")
            )
        
        selection_list = SelectionList(*[(table, table) for table in tables])
        selection_list.border_title = "Available Tables"
        
        return Container(
            selection_list,
            Button("Roll Selected Table", id="roll-table", variant="default"),
            classes="tab-container"
        )
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "execute-flow":
            flows_tab = self.query_one("#flows")
            selection_list = flows_tab.query_one(SelectionList)
            selected = selection_list.selected
            
            if selected:
                flow_id = selected[0]
                self.app.push_screen(FlowExecutionScreen(self.system, flow_id, self.engine))
        
        elif event.button.id == "roll-table":
            tables_tab = self.query_one("#tables")
            selection_list = tables_tab.query_one(SelectionList)
            selected = selection_list.selected
            
            if selected:
                table_id = selected[0]
                # Would implement table rolling here
                self.notify(f"Rolling table: {table_id} (not implemented yet)")


class GrimoireApp(App):
    """Main Textual application for GRIMOIRE runner."""
    
    CSS = """
    .title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin: 1;
    }
    
    .tab-container {
        padding: 1;
    }
    
    .empty-state {
        text-align: center;
        color: $text-muted;
        margin: 2;
    }
    
    .flow-container {
        padding: 1;
    }
    
    #execution-log {
        height: 1fr;
        border: solid $primary;
    }
    
    #results {
        height: 4;
        border: solid $success;
        padding: 1;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "toggle_dark", "Toggle Dark Mode"),
        Binding("s", "screenshot", "Screenshot"),
    ]
    
    def __init__(self, system_path: Optional[Path] = None):
        super().__init__()
        self.system_path = system_path
        self.engine = GrimoireEngine()
        self.system: Optional[System] = None
    
    def compose(self) -> ComposeResult:
        """Create the main application layout."""
        yield Header(show_clock=True)
        
        if self.system_path:
            yield Container(
                Label("Loading GRIMOIRE system...", classes="title"),
                ProgressBar(id="loading-progress"),
                Static("", id="system-info"),
                id="main-container"
            )
        else:
            yield Container(
                Label("No system specified", classes="title"),
                Button("Load System", id="load-system", variant="primary"),
                id="main-container"
            )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the application."""
        if self.system_path:
            self.load_system(self.system_path)
    
    def load_system(self, system_path: Path) -> None:
        """Load a GRIMOIRE system."""
        progress = self.query_one("#loading-progress", ProgressBar)
        info = self.query_one("#system-info", Static)
        
        try:
            progress.update(progress=20)
            self.system = self.engine.load_system(system_path)
            progress.update(progress=100)
            
            info.update(f"Loaded: {self.system.name} ({self.system.id})")
            
            # Switch to system explorer
            self.call_after_refresh(self._show_system_explorer)
            
        except Exception as e:
            info.update(f"Error loading system: {e}")
            progress.update(progress=100)
    
    def _show_system_explorer(self) -> None:
        """Show the system explorer screen."""
        if self.system:
            self.push_screen(SystemExplorerScreen(self.system, self.engine))
    
    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark
    
    def action_screenshot(self) -> None:
        """Take a screenshot."""
        self.save_screenshot()
        self.notify("Screenshot saved!")


def run_textual_app(system_path: Optional[Path] = None) -> None:
    """Run the Textual GRIMOIRE application."""
    app = GrimoireApp(system_path)
    app.run()


# Keep the old InteractiveREPL for backwards compatibility
class InteractiveREPL:
    """Legacy REPL interface - redirects to Textual app."""
    
    def __init__(self, engine=None, system=None):
        self.engine = engine or GrimoireEngine()
        self.system = system
    
    def run(self) -> None:
        """Run the interactive interface using Textual."""
        if self.system and hasattr(self.system, '_source_path'):
            run_textual_app(Path(self.system._source_path))
        else:
            run_textual_app()
