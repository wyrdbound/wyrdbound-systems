"""Tests for the CLI interface."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer
from typer.testing import CliRunner

from grimoire_runner.ui.cli import app, main


class TestCLICommands:
    """Test the main CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_main_entry_point(self):
        """Test that main() executes without error."""
        # Test that main() can be imported and called
        assert callable(main)
        
        # Test help command through main
        with patch('sys.argv', ['grimoire-runner', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            # Help command should exit with code 0
            assert exc_info.value.code == 0
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "grimoire-runner" in result.stdout
        assert "Interactive GRIMOIRE system runner" in result.stdout
    
    def test_cli_version_info(self):
        """Test CLI shows available commands."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        
        # Check that all expected commands are listed
        expected_commands = ["validate", "execute", "browse", "list"]
        for command in expected_commands:
            assert command in result.stdout


class TestValidateCommand:
    """Test the validate command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_validate_success(self, mock_load_system):
        """Test successful system validation."""
        # Mock a valid system
        mock_system = Mock()
        mock_system.name = "Test System"
        mock_system.id = "test-system"
        mock_system.validate.return_value = []  # No errors
        mock_system.flows = {"test_flow": Mock()}
        mock_system.models = {}
        mock_system.compendiums = {}
        mock_system.tables = {}
        
        # Mock flow validation
        mock_system.flows["test_flow"].validate.return_value = []
        
        mock_load_system.return_value = mock_system
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["validate", temp_dir])
            
        assert result.exit_code == 0
        assert "System validation passed" in result.stdout
        assert "Test System" in result.stdout
        mock_load_system.assert_called_once()
    
    def test_validate_with_errors(self):
        """Test validate command when system has validation errors."""
        with patch('grimoire_runner.ui.cli.engine.load_system') as mock_load:
            mock_system = Mock()
            mock_system.name = "Test System"
            mock_system.id = "test-system"
            mock_system.validate.return_value = ["Error 1", "Error 2"]
            mock_system.flows = {}
            mock_load.return_value = mock_system
            
            result = self.runner.invoke(app, ['validate', '/fake/path'])
            
            assert result.exit_code == 1  # Command fails with validation errors
            assert "System validation failed" in result.stdout
            assert "Error 1" in result.stdout
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_validate_with_flow_errors(self, mock_load_system):
        """Test validation with flow errors."""
        # Mock a system with flow validation errors
        mock_system = Mock()
        mock_system.name = "Test System"
        mock_system.id = "test-system"
        mock_system.validate.return_value = []
        mock_system.flows = {"bad_flow": Mock()}
        
        # Mock flow with errors
        mock_system.flows["bad_flow"].validate.return_value = ["Invalid step type"]
        
        mock_load_system.return_value = mock_system
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["validate", temp_dir])
            
        assert result.exit_code == 1  # Command fails with flow validation errors
        assert "System validation failed" in result.stdout
        assert "Flow bad_flow: Invalid step type" in result.stdout
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_validate_load_error(self, mock_load_system):
        """Test validation when system loading fails."""
        mock_load_system.side_effect = Exception("System not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["validate", temp_dir])
            
        assert result.exit_code == 1
        assert "Error loading system" in result.stdout
    
    def test_validate_missing_path(self):
        """Test validation command without system path."""
        result = self.runner.invoke(app, ["validate"])
        assert result.exit_code == 2  # Typer returns exit code 2 for missing arguments
        # CliRunner with Typer doesn't always capture stderr, so just check exit code
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_validate_verbose_mode(self, mock_load_system):
        """Test validation with verbose output."""
        mock_system = Mock()
        mock_system.name = "Test System"
        mock_system.id = "test-system"
        mock_system.validate.return_value = []
        mock_system.flows = {}
        mock_system.models = {}
        mock_system.compendiums = {}
        mock_system.tables = {}
        
        mock_load_system.return_value = mock_system
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["validate", temp_dir, "--verbose"])
            
        assert result.exit_code == 0
        mock_load_system.assert_called_once()


class TestExecuteCommand:
    """Test the execute command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('grimoire_runner.ui.simple_textual.run_simple_textual_executor')
    def test_execute_basic(self, mock_textual):
        """Test basic execute command."""
        # Mock textual executor to complete successfully
        mock_textual.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, [
                "execute", temp_dir, "--flow", "test_flow"
            ])
            
        assert result.exit_code == 0
        mock_textual.assert_called_once_with(Path(temp_dir), "test_flow")
    
    def test_execute_missing_flow(self):
        """Test execution without specifying flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["execute", temp_dir])
            
        assert result.exit_code == 2  # Typer returns exit code 2 for missing required options
        # CliRunner with Typer doesn't always capture stderr, so just check exit code
    
    @patch('grimoire_runner.ui.simple_textual.run_simple_textual_executor')
    def test_execute_with_output_file(self, mock_textual):
        """Test execution with output file."""
        mock_textual.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = Path(temp_dir) / "results.json"
            result = self.runner.invoke(app, [
                "execute", temp_dir, "--flow", "test_flow", "--output", str(output_file)
            ])
            
        assert result.exit_code == 0
        mock_textual.assert_called_once_with(Path(temp_dir), "test_flow")
    
    @patch('grimoire_runner.ui.simple_textual.run_simple_textual_executor')
    def test_execute_non_interactive(self, mock_textual):
        """Test non-interactive execution."""
        mock_textual.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, [
                "execute", temp_dir, "--flow", "test_flow", "--no-interactive"
            ])
            
        assert result.exit_code == 0
        mock_textual.assert_called_once_with(Path(temp_dir), "test_flow")
    
    @patch('grimoire_runner.ui.simple_textual.run_simple_textual_executor')
    def test_execute_with_error(self, mock_textual):
        """Test execution with flow error."""
        mock_textual.side_effect = Exception("Flow execution failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, [
                "execute", temp_dir, "--flow", "bad_flow"
            ])
            
        assert result.exit_code == 1
        assert "Textual interface error" in result.stdout


class TestBrowseCommand:
    """Test the browse command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('grimoire_runner.ui.cli.run_compendium_browser')
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_browse_basic(self, mock_load_system, mock_run_browser):
        """Test basic browse command."""
        mock_system = Mock()
        mock_load_system.return_value = mock_system
        mock_run_browser.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["browse", temp_dir])
            
        assert result.exit_code == 0
        mock_load_system.assert_called_once()
        mock_run_browser.assert_called_once()
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_browse_load_error(self, mock_load_system):
        """Test browse command with system load error."""
        mock_load_system.side_effect = Exception("System not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["browse", temp_dir])
            
        assert result.exit_code == 1
        assert "Error:" in result.stdout  # The actual error message format


class TestListCommand:
    """Test the list command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_list_flows(self, mock_load_system):
        """Test listing flows."""
        mock_system = Mock()
        mock_system.name = "Test System"
        mock_system.id = "test-system"
        mock_system.description = "Test system description"
        
        # Mock list_flows method
        mock_system.list_flows.return_value = ["flow1", "flow2"]
        
        # Mock individual flows
        mock_flow1 = Mock()
        mock_flow1.name = "First Flow"
        mock_flow1.description = "First flow description"
        mock_flow1.steps = ["step1", "step2"]
        mock_flow1.resolve_description.return_value = "First flow description"
        
        mock_flow2 = Mock()
        mock_flow2.name = "Second Flow"
        mock_flow2.description = "Second flow description"
        mock_flow2.steps = ["step1"]
        mock_flow2.resolve_description.return_value = "Second flow description"
        
        mock_system.get_flow.side_effect = lambda flow_id: {
            "flow1": mock_flow1,
            "flow2": mock_flow2
        }[flow_id]
        
        mock_load_system.return_value = mock_system
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["list", temp_dir, "--type", "flows"])
            
        assert result.exit_code == 0
        assert "flow1" in result.stdout
        assert "flow2" in result.stdout
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_list_models(self, mock_load_system):
        """Test listing models."""
        mock_system = Mock()
        mock_system.name = "Test System"
        mock_system.id = "test-system"
        mock_system.description = "Test system description"
        
        # Mock list_models method
        mock_system.list_models.return_value = ["character", "weapon"]
        
        # Mock individual models
        mock_character = Mock()
        mock_character.name = "Character"
        mock_character.description = "Character model"
        mock_character.extends = []
        mock_character.get_all_attributes.return_value = {"name": "string", "level": "int"}
        
        mock_weapon = Mock()
        mock_weapon.name = "Weapon"
        mock_weapon.description = "Weapon model"
        mock_weapon.extends = []
        mock_weapon.get_all_attributes.return_value = {"damage": "int"}
        
        mock_system.get_model.side_effect = lambda model_id: {
            "character": mock_character,
            "weapon": mock_weapon
        }[model_id]
        
        mock_load_system.return_value = mock_system
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["list", temp_dir, "--type", "models"])
            
        assert result.exit_code == 0
        assert "character" in result.stdout
        assert "weapon" in result.stdout
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_list_tables(self, mock_load_system):
        """Test listing tables."""
        mock_system = Mock()
        mock_system.name = "Test System"
        mock_system.id = "test-system"
        mock_system.description = "Test system description"
        
        # Mock list_tables method
        mock_system.list_tables.return_value = ["encounters", "treasure"]
        
        # Mock individual tables
        mock_encounters = Mock()
        mock_encounters.id = "encounters"
        mock_encounters.name = "Encounters"
        mock_encounters.description = "Random encounters"
        mock_encounters.entries = [{"weight": 1, "result": "Goblin"}]
        mock_encounters.roll = "1d20"
        
        mock_treasure = Mock()
        mock_treasure.id = "treasure"
        mock_treasure.name = "Treasure"
        mock_treasure.description = "Treasure table"
        mock_treasure.entries = [{"weight": 1, "result": "Gold"}]
        mock_treasure.roll = "1d100"
        
        mock_system.get_table.side_effect = lambda table_id: {
            "encounters": mock_encounters,
            "treasure": mock_treasure
        }[table_id]
        
        mock_load_system.return_value = mock_system
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["list", temp_dir, "--type", "tables"])
            
        assert result.exit_code == 0
        assert "encounters" in result.stdout
        assert "treasure" in result.stdout
    
    def test_list_invalid_type(self):
        """Test listing with invalid type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["list", temp_dir, "--type", "invalid"])
            
        assert result.exit_code == 1  # Manual validation returns exit code 1
        # Test would need mocking to avoid actual system loading
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_list_load_error(self, mock_load_system):
        """Test list command with system load error."""
        mock_load_system.side_effect = Exception("System not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["list", temp_dir, "--type", "flows"])
            
        assert result.exit_code == 1
        assert "Error:" in result.stdout


class TestCLIErrorHandling:
    """Test CLI error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_invalid_command(self):
        """Test handling of invalid commands."""
        result = self.runner.invoke(app, ["invalid-command"])
        assert result.exit_code == 2  # Typer exits with 2 for unknown commands
    
    def test_missing_arguments(self):
        """Test handling of missing required arguments."""
        # Most commands require a system path
        result = self.runner.invoke(app, ["validate"])
        assert result.exit_code != 0
    
    def test_invalid_path(self):
        """Test handling of invalid system paths."""
        result = self.runner.invoke(app, ["validate", "/nonexistent/path"])
        assert result.exit_code == 1
    
    @patch('grimoire_runner.ui.cli.engine.load_system')
    def test_engine_initialization_error(self, mock_load_system):
        """Test handling of engine initialization errors."""
        mock_load_system.side_effect = RuntimeError("Engine failed to initialize")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(app, ["validate", temp_dir])
            
        assert result.exit_code == 1


class TestCLIIntegration:
    """Integration tests for CLI functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_command_chaining_compatibility(self):
        """Test that commands can be called in sequence."""
        # This tests that the CLI maintains proper state between commands
        with patch('grimoire_runner.ui.cli.engine.load_system') as mock_load:
            mock_system = Mock()
            mock_system.name = "Test System"
            mock_system.id = "test-system"
            mock_system.description = "Test system description"
            mock_system.validate.return_value = []
            mock_system.flows = {}
            mock_system.models = {}
            mock_system.compendiums = {}
            mock_system.tables = {}
            
            # Add required methods for list command
            mock_system.list_flows.return_value = []
            
            mock_load.return_value = mock_system
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Validate first
                result1 = self.runner.invoke(app, ["validate", temp_dir])
                assert result1.exit_code == 0
                
                # Then list flows
                result2 = self.runner.invoke(app, ["list", temp_dir, "--type", "flows"])
                assert result2.exit_code == 0
    
    @patch('grimoire_runner.ui.cli.console')
    def test_rich_console_integration(self, mock_console):
        """Test that Rich console integration works properly."""
        mock_console.print = Mock()
        
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        # Verify that Rich formatting is preserved in help output


if __name__ == "__main__":
    pytest.main([__file__])
