"""
Comprehensive tests for UI components - textual browser and main app.
Part of Phase 2 of the test coverage improvement plan.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.models.system import System
from grimoire_runner.ui.textual_app import (
    FlowExecutionScreen,
    GrimoireApp,
    SystemExplorerScreen,
    run_textual_app,
)
from grimoire_runner.ui.textual_browser import (
    CompendiumBrowser,
    CompendiumBrowserApp,
    CompendiumDetailScreen,
    run_compendium_browser,
)


class TestCompendiumBrowserApp:
    """Test the CompendiumBrowserApp UI component."""

    def create_test_system_with_compendiums(self, temp_dir: str) -> Path:
        """Create a test system with compendiums for testing."""
        system_dir = Path(temp_dir) / "test_system"
        system_dir.mkdir()

        # Create system.yaml
        system_data = {
            "id": "test_system",
            "name": "Test System",
            "description": "A test system with compendiums",
            "version": "1.0.0"
        }

        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create compendium directory (note: singular, as expected by loader)
        compendium_dir = system_dir / "compendium"
        compendium_dir.mkdir()

        # Create a test compendium
        compendium_data = {
            "kind": "compendium",  # Required field
            "id": "items",
            "name": "Items",
            "model": "item",
            "entries": {
                "sword": {
                    "name": "Iron Sword",
                    "type": "weapon",
                    "damage": "1d8",
                    "cost": 10,
                    "tags": ["metal", "weapon"]
                },
                "potion": {
                    "name": "Health Potion",
                    "type": "consumable",
                    "effect": "heal",
                    "cost": 5,
                    "tags": ["magic", "healing"]
                }
            }
        }

        with open(compendium_dir / "items.yaml", "w") as f:
            yaml.dump(compendium_data, f)

        # Create models directory
        models_dir = system_dir / "models"
        models_dir.mkdir()

        model_data = {
            "id": "item",
            "name": "Item",
            "attributes": {
                "name": {"type": "string", "required": True},
                "type": {"type": "string", "required": True},
                "cost": {"type": "integer", "default": 0},
                "tags": {"type": "list", "default": []}
            }
        }

        with open(models_dir / "item.yaml", "w") as f:
            yaml.dump(model_data, f)

        return system_dir

    def test_browser_app_creation(self):
        """Test browser app creation with system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system_with_compendiums(temp_dir)

            from grimoire_runner.core.loader import SystemLoader
            loader = SystemLoader()
            system = loader.load_system(system_path)

            app = CompendiumBrowserApp(system)
            assert app is not None
            assert app.system == system
            assert len(app.compendiums) > 0

    @pytest.mark.asyncio
    async def test_browser_app_compose(self):
        """Test browser app UI composition."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system_with_compendiums(temp_dir)

            from grimoire_runner.core.loader import SystemLoader
            loader = SystemLoader()
            system = loader.load_system(system_path)

            app = CompendiumBrowserApp(system)

            async with app.run_test() as pilot:
                await pilot.pause(0.1)

                # Test that UI components are present
                tree = app.query_one("Tree", expect_type=None)
                assert tree is not None

                preview = app.query(".entry-preview")
                assert len(preview) > 0

    @pytest.mark.asyncio
    async def test_browser_tree_navigation(self):
        """Test browser tree navigation and entry selection."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system_with_compendiums(temp_dir)

            from grimoire_runner.core.loader import SystemLoader
            loader = SystemLoader()
            system = loader.load_system(system_path)

            app = CompendiumBrowserApp(system)

            async with app.run_test() as pilot:
                await pilot.pause(0.1)

                # Navigate tree and test selection
                tree = app.query_one("Tree")

                # Should have compendium nodes
                assert len(tree.root.children) > 0

                # Test that we can expand nodes without crashing
                for child in tree.root.children:
                    tree.select_node(child)
                    await pilot.pause(0.05)

    def test_browser_with_empty_system(self):
        """Test browser behavior with system having no compendiums."""
        # Create a mock system with no compendiums
        system = Mock(spec=System)
        system.compendiums = {}

        app = CompendiumBrowserApp(system)
        assert app is not None
        assert len(app.compendiums) == 0

    @pytest.mark.asyncio
    async def test_browser_empty_system_compose(self):
        """Test browser app composition with empty system."""
        system = Mock(spec=System)
        system.compendiums = {}

        app = CompendiumBrowserApp(system)

        async with app.run_test() as pilot:
            await pilot.pause(0.1)

            # Should show empty state message
            labels = app.query("Label")
            assert len(labels) > 0

            close_button = app.query("#close")
            assert len(close_button) > 0

    @pytest.mark.asyncio
    async def test_browser_close_functionality(self):
        """Test browser close button functionality."""
        system = Mock(spec=System)
        system.compendiums = {}

        app = CompendiumBrowserApp(system)

        async with app.run_test() as pilot:
            await pilot.pause(0.1)

            # Click close button
            await pilot.click("#close")

            # App should exit gracefully
            assert app.is_running is False

    def test_browser_entry_preview_formatting(self):
        """Test entry preview formatting logic."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system_with_compendiums(temp_dir)

            from grimoire_runner.core.loader import SystemLoader
            loader = SystemLoader()
            system = loader.load_system(system_path)

            app = CompendiumBrowserApp(system)

            # Test formatting different data types
            test_entry = {
                "name": "Test Item",
                "cost": 10,
                "tags": ["tag1", "tag2"],
                "complex_list": [1, 2, 3, 4, 5],
                "nested_dict": {"key1": "value1", "key2": "value2"}
            }

            formatted = app._format_entry_preview("test_entry", test_entry)

            assert "Test Item" in formatted
            assert "cost" in formatted
            assert "10" in formatted
            assert "tag1, tag2" in formatted

    def test_legacy_browser_compatibility(self):
        """Test legacy CompendiumBrowser class."""
        system = Mock(spec=System)
        browser = CompendiumBrowser(system=system)

        assert browser.system == system
        assert browser.compendium is None

        # Test with compendium
        compendium = Mock()
        browser = CompendiumBrowser(compendium=compendium, system=system)
        assert browser.compendium == compendium

    def test_run_compendium_browser_function(self):
        """Test run_compendium_browser function."""
        system = Mock(spec=System)
        system.compendiums = {}

        # Should not raise an exception
        with patch.object(CompendiumBrowserApp, 'run') as mock_run:
            run_compendium_browser(system)
            mock_run.assert_called_once()


class TestSystemExplorerScreen:
    """Test the SystemExplorerScreen UI component."""

    def create_comprehensive_test_system(self, temp_dir: str) -> Path:
        """Create a comprehensive test system with all components."""
        system_dir = Path(temp_dir) / "comprehensive_system"
        system_dir.mkdir()

        # Create system.yaml
        system_data = {
            "id": "comprehensive_system",
            "name": "Comprehensive Test System",
            "description": "System with all component types",
            "version": "1.0.0"
        }

        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        # Create flows
        flows_dir = system_dir / "flows"
        flows_dir.mkdir()

        flow_data = {
            "id": "test_flow",
            "name": "Test Flow",
            "description": "A test flow",
            "steps": [
                {"id": "step1", "name": "First Step", "type": "dice_roll", "roll": "1d6"}
            ]
        }

        with open(flows_dir / "test_flow.yaml", "w") as f:
            yaml.dump(flow_data, f)

        # Create models
        models_dir = system_dir / "models"
        models_dir.mkdir()

        model_data = {
            "id": "character",
            "name": "Character",
            "attributes": {
                "name": {"type": "string", "required": True},
                "level": {"type": "integer", "default": 1}
            }
        }

        with open(models_dir / "character.yaml", "w") as f:
            yaml.dump(model_data, f)

        # Create tables
        tables_dir = system_dir / "tables"
        tables_dir.mkdir()

        table_data = {
            "kind": "table",  # Required field
            "id": "test_table",
            "name": "Test Table",
            "description": "A test table",
            "entries": [
                {"range": "1-3", "result": "Low"},
                {"range": "4-6", "result": "High"}
            ]
        }

        with open(tables_dir / "test_table.yaml", "w") as f:
            yaml.dump(table_data, f)

        # Create compendium directory (note: singular, as expected by loader)
        compendium_dir = system_dir / "compendium"
        compendium_dir.mkdir()

        compendium_data = {
            "kind": "compendium",  # Required field
            "id": "items",
            "name": "Items",
            "description": "Test items",
            "model": "item",
            "entries": {
                "sword": {"name": "Sword", "type": "weapon"}
            }
        }

        with open(compendium_dir / "items.yaml", "w") as f:
            yaml.dump(compendium_data, f)

        return system_dir

    def test_explorer_screen_creation(self):
        """Test SystemExplorerScreen creation."""
        system = Mock(spec=System)
        system.flows = {"test_flow": Mock()}
        system.models = {"character": Mock()}
        system.tables = {"test_table": Mock()}
        system.compendiums = {"items": Mock()}

        engine = Mock(spec=GrimoireEngine)

        screen = SystemExplorerScreen(system, engine)
        assert screen.system == system
        assert screen.engine == engine

    @pytest.mark.asyncio
    async def test_explorer_screen_compose(self):
        """Test SystemExplorerScreen UI composition."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_comprehensive_test_system(temp_dir)

            from grimoire_runner.core.loader import SystemLoader
            loader = SystemLoader()
            system = loader.load_system(system_path)
            engine = GrimoireEngine()

            screen = SystemExplorerScreen(system, engine)

            # Create a minimal app to run the screen in context
            from grimoire_runner.ui.textual_app import GrimoireApp
            app = GrimoireApp()

            async with app.run_test() as pilot:
                await pilot.pause(0.1)
                # Test composition within app context
                app.push_screen(screen)
                await pilot.pause(0.1)
                # If we get here without exception, composition worked
                assert True

    def test_explorer_empty_flows_tab(self):
        """Test flows tab with no flows."""
        system = Mock(spec=System)
        system.flows = {}
        engine = Mock(spec=GrimoireEngine)

        screen = SystemExplorerScreen(system, engine)
        flows_tab = screen._create_flows_tab()

        assert flows_tab is not None

    def test_explorer_empty_models_tab(self):
        """Test models tab with no models."""
        system = Mock(spec=System)
        system.models = {}
        engine = Mock(spec=GrimoireEngine)

        screen = SystemExplorerScreen(system, engine)
        models_tab = screen._create_models_tab()

        assert models_tab is not None

    def test_explorer_empty_tables_tab(self):
        """Test tables tab with no tables."""
        system = Mock(spec=System)
        system.tables = {}
        engine = Mock(spec=GrimoireEngine)

        screen = SystemExplorerScreen(system, engine)
        tables_tab = screen._create_tables_tab()

        assert tables_tab is not None

    def test_explorer_empty_compendiums_tab(self):
        """Test compendiums tab with no compendiums."""
        system = Mock(spec=System)
        system.compendiums = {}
        engine = Mock(spec=GrimoireEngine)

        screen = SystemExplorerScreen(system, engine)
        compendiums_tab = screen._create_compendiums_tab()

        assert compendiums_tab is not None

    def test_explorer_flows_tab_with_data(self):
        """Test flows tab with actual flow data."""
        system = Mock(spec=System)
        system.flows = {"flow1": Mock(), "flow2": Mock()}
        engine = Mock(spec=GrimoireEngine)

        screen = SystemExplorerScreen(system, engine)
        flows_tab = screen._create_flows_tab()

        assert flows_tab is not None

    def test_explorer_models_tab_with_data(self):
        """Test models tab with actual model data."""
        system = Mock(spec=System)
        model = Mock()
        model.fields = {"name": Mock(type="string"), "level": Mock(type="integer")}
        system.models = {"character": model}
        engine = Mock(spec=GrimoireEngine)

        screen = SystemExplorerScreen(system, engine)
        models_tab = screen._create_models_tab()

        assert models_tab is not None

    def test_explorer_compendiums_tab_with_data(self):
        """Test compendiums tab with actual compendium data."""
        system = Mock(spec=System)
        compendium = Mock()
        compendium.entries = {"item1": Mock(), "item2": Mock()}
        system.compendiums = {"items": compendium}
        engine = Mock(spec=GrimoireEngine)

        screen = SystemExplorerScreen(system, engine)
        compendiums_tab = screen._create_compendiums_tab()

        assert compendiums_tab is not None


class TestGrimoireApp:
    """Test the main GrimoireApp."""

    def create_test_system(self, temp_dir: str) -> Path:
        """Create a minimal test system."""
        system_dir = Path(temp_dir) / "test_system"
        system_dir.mkdir()

        system_data = {
            "id": "test_system",
            "name": "Test System",
            "description": "A minimal test system",
            "version": "1.0.0"
        }

        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)

        return system_dir

    def test_grimoire_app_creation(self):
        """Test GrimoireApp creation."""
        app = GrimoireApp()
        assert app is not None

    def test_grimoire_app_with_system_path(self):
        """Test GrimoireApp creation with system path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)

            app = GrimoireApp(system_path=system_path)
            assert app is not None
            assert app.system_path == system_path

    def test_grimoire_app_with_auto_flow(self):
        """Test GrimoireApp creation with auto flow."""
        app = GrimoireApp(auto_flow="test_flow")
        assert app is not None
        assert app.auto_flow == "test_flow"

    @pytest.mark.asyncio
    async def test_grimoire_app_compose(self):
        """Test GrimoireApp UI composition."""
        app = GrimoireApp()

        async with app.run_test() as pilot:
            await pilot.pause(0.1)

            # Should compose without errors
            assert app.is_running

    def test_run_textual_app_function(self):
        """Test run_textual_app function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_test_system(temp_dir)

            # Should not raise an exception
            with patch.object(GrimoireApp, 'run') as mock_run:
                run_textual_app(system_path=system_path, auto_flow="test_flow")
                mock_run.assert_called_once()

    def test_run_textual_app_no_params(self):
        """Test run_textual_app function with no parameters."""
        with patch.object(GrimoireApp, 'run') as mock_run:
            run_textual_app()
            mock_run.assert_called_once()


class TestFlowExecutionScreen:
    """Test the FlowExecutionScreen component."""

    def test_flow_execution_screen_creation(self):
        """Test FlowExecutionScreen creation."""
        system = Mock(spec=System)
        engine = Mock(spec=GrimoireEngine)
        flow_id = "test_flow"

        screen = FlowExecutionScreen(system, flow_id, engine)
        assert screen.system == system
        assert screen.flow_id == flow_id
        assert screen.engine == engine

    @pytest.mark.asyncio
    async def test_flow_execution_screen_compose(self):
        """Test FlowExecutionScreen UI composition."""
        system = Mock(spec=System)
        engine = Mock(spec=GrimoireEngine)
        flow_id = "test_flow"

        screen = FlowExecutionScreen(system, flow_id, engine)

        # Test composition doesn't crash
        widgets = list(screen.compose())
        assert len(widgets) > 0


class TestCompendiumDetailScreen:
    """Test the CompendiumDetailScreen component."""

    def test_detail_screen_creation(self):
        """Test CompendiumDetailScreen creation."""
        entry_id = "test_entry"
        entry_data = {"name": "Test Entry", "type": "test"}

        screen = CompendiumDetailScreen(entry_id, entry_data)
        assert screen.entry_id == entry_id
        assert screen.entry_data == entry_data

    @pytest.mark.asyncio
    async def test_detail_screen_compose(self):
        """Test CompendiumDetailScreen UI composition."""
        entry_id = "test_entry"
        entry_data = {"name": "Test Entry", "type": "test"}

        screen = CompendiumDetailScreen(entry_id, entry_data)

        # Test composition doesn't crash
        widgets = list(screen.compose())
        assert len(widgets) > 0

    def test_detail_screen_with_complex_data(self):
        """Test CompendiumDetailScreen with complex entry data."""
        entry_id = "complex_entry"
        entry_data = {
            "name": "Complex Entry",
            "type": "test",
            "nested": {"key": "value"},
            "list_data": [1, 2, 3],
            "description": "A complex test entry with multiple data types"
        }

        screen = CompendiumDetailScreen(entry_id, entry_data)
        assert screen.entry_id == entry_id
        assert screen.entry_data == entry_data

    def test_detail_screen_format_entry_content(self):
        """Test detail screen entry content formatting."""
        entry_id = "test_entry"
        entry_data = {
            "name": "Test Entry",
            "cost": 10,
            "tags": ["tag1", "tag2"],
            "description": "A test entry"
        }

        screen = CompendiumDetailScreen(entry_id, entry_data)
        content = screen._format_entry_data()  # Correct method name

        assert "Test Entry" in content
        assert "10" in content
        assert "tag1" in content
        assert "A test entry" in content
