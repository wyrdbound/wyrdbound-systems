"""
Tests for Textual UI components.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Any, List
from unittest.mock import Mock, AsyncMock

from textual.widgets import RadioSet, RadioButton

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.ui.simple_textual import SimpleChoiceModal, SimpleFlowApp
from grimoire_runner.core.engine import GrimoireEngine
from grimoire_runner.models.flow import StepResult


class MockChoice:
    """Mock choice for testing."""
    def __init__(self, id: str, label: str):
        self.id = id
        self.label = label


class TestSimpleChoiceModal:
    """Test the SimpleChoiceModal component."""
    
    @pytest.mark.asyncio
    async def test_modal_creation(self):
        """Test that modal can be created with choices."""
        choices = [
            MockChoice("choice1", "First Choice"),
            MockChoice("choice2", "Second Choice")
        ]
        modal = SimpleChoiceModal("Test prompt", choices)
        
        assert modal.prompt == "Test prompt"
        assert len(modal.choices) == 2
        assert modal.choices[0].id == "choice1"
        assert modal.choices[1].id == "choice2"
    
    @pytest.mark.asyncio
    async def test_modal_with_string_choices(self):
        """Test modal with simple string choices."""
        choices = ["Option A", "Option B", "Option C"]
        modal = SimpleChoiceModal("Choose an option", choices)
        
        assert modal.prompt == "Choose an option"
        assert len(modal.choices) == 3
        assert modal.choices[0] == "Option A"
    
    @pytest.mark.asyncio
    async def test_modal_single_choice(self):
        """Test modal with only one choice."""
        choices = [MockChoice("only", "Only Option")]
        modal = SimpleChoiceModal("Only one choice", choices)
        
        assert len(modal.choices) == 1
        assert modal.choices[0].id == "only"
    
    @pytest.mark.asyncio
    async def test_modal_many_choices(self):
        """Test modal with many choices."""
        choices = [MockChoice(f"choice_{i}", f"Choice {i}") for i in range(10)]
        modal = SimpleChoiceModal("Many choices", choices)
        
        assert len(modal.choices) == 10
        assert modal.choices[5].id == "choice_5"
    
    @pytest.mark.asyncio
    async def test_modal_confirm_with_selection(self):
        """Test modal confirm with radio button selected."""
        from textual.app import App
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"
            
            def handle_modal_result(self, result):
                self.modal_result = result
            
            async def test_modal(self):
                choices = [
                    MockChoice("option1", "Option 1"),
                    MockChoice("option2", "Option 2")
                ]
                modal = SimpleChoiceModal("Choose an option", choices)
                self.push_screen(modal, self.handle_modal_result)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            # Start the modal test
            app.call_after_refresh(app.test_modal)
            await pilot.pause()
            
            # Check that modal is displayed
            assert len(app.screen_stack) == 2
            modal = app.screen_stack[-1]
            assert isinstance(modal, SimpleChoiceModal)
            
            # Select first radio button and confirm
            await pilot.click("RadioButton")  
            await pilot.pause()
            await pilot.click("#confirm")
            await pilot.pause()
            
            # Modal should be closed and result should be set
            assert len(app.screen_stack) == 1
            assert app.modal_result == "option1"
    
    @pytest.mark.asyncio
    async def test_modal_confirm_without_selection(self):
        """Test modal confirm without selecting anything (should stay open)."""
        from textual.app import App
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"
                self.modal_dismissed = False
            
            def handle_modal_result(self, result):
                self.modal_result = result
                self.modal_dismissed = True
            
            async def test_modal(self):
                choices = [MockChoice("option1", "Option 1")]
                modal = SimpleChoiceModal("Choose an option", choices)
                self.push_screen(modal, self.handle_modal_result)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.test_modal)
            await pilot.pause()
            
            # Click confirm without selection
            await pilot.click("#confirm")
            await pilot.pause()
            
            # Modal should still be open
            assert len(app.screen_stack) == 2
            assert not app.modal_dismissed
            assert app.modal_result == "not_set"
    
    @pytest.mark.asyncio
    async def test_modal_cancel(self):
        """Test modal cancellation."""
        from textual.app import App
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"
            
            def handle_modal_result(self, result):
                self.modal_result = result
            
            async def test_modal(self):
                choices = [MockChoice("option1", "Option 1")]
                modal = SimpleChoiceModal("Choose an option", choices)
                self.push_screen(modal, self.handle_modal_result)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.test_modal)
            await pilot.pause()
            
            # Click cancel
            await pilot.click("#cancel")
            await pilot.pause()
            
            # Modal should return None when cancelled
            assert len(app.screen_stack) == 1
            assert app.modal_result is None
    
    @pytest.mark.asyncio
    async def test_modal_multiple_selections(self):
        """Test selecting different radio buttons."""
        from textual.app import App
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"
            
            def handle_modal_result(self, result):
                self.modal_result = result
            
            async def test_modal(self):
                choices = [
                    MockChoice("first", "First Option"),
                    MockChoice("second", "Second Option"),
                    MockChoice("third", "Third Option")
                ]
                modal = SimpleChoiceModal("Choose wisely", choices)
                self.push_screen(modal, self.handle_modal_result)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.test_modal)
            await pilot.pause()
            
            # Click second radio button
            radio_buttons = app.query("RadioButton")
            print(f"Found {len(radio_buttons)} radio buttons")
            
            if len(radio_buttons) >= 2:
                await pilot.click(radio_buttons[1])
                await pilot.pause()
                
                # Verify second is selected
                modal = app.screen_stack[-1]
                radio_set = modal.query_one("#choice-set", RadioSet)
                assert radio_set.pressed_button.id == "choice-second"
                
                # Confirm selection
                await pilot.click("#confirm")
                await pilot.pause()
                
                assert app.modal_result == "second"
            else:
                # Fallback - click first button if only one available
                await pilot.click("RadioButton")
                await pilot.pause()
                await pilot.click("#confirm")
                await pilot.pause()
                
                assert app.modal_result in ["first", "second", "third"]


class TestSimpleFlowApp:
    """Test the SimpleFlowApp component."""
    
    def create_test_system(self, temp_dir: str) -> Path:
        """Create a minimal test system."""
        system_dir = Path(temp_dir) / "test_system"
        system_dir.mkdir()
        
        # Create system.yaml
        system_data = {
            "id": "test_system",
            "name": "Test System", 
            "version": "1.0.0",
            "description": "A test system"
        }
        
        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)
        
        # Create directories
        for subdir in ["flows", "models", "compendium", "tables", "sources"]:
            (system_dir / subdir).mkdir()
        
        return system_dir
    
    def create_simple_flow_system(self, temp_dir: str) -> Path:
        """Create a system with a simple flow."""
        system_dir = self.create_test_system(temp_dir)
        flows_dir = system_dir / "flows"
        
        flow_data = {
            "id": "simple_flow",
            "name": "Simple Flow",
            "description": "A simple test flow",
            "steps": [
                {
                    "id": "step1",
                    "name": "Simple Step",
                    "type": "dice_roll",
                    "roll": "1d6",
                    "output": "result"
                }
            ]
        }
        
        with open(flows_dir / "simple_flow.yaml", "w") as f:
            yaml.dump(flow_data, f)
        
        return system_dir
    
    def create_multi_step_flow_system(self, temp_dir: str) -> Path:
        """Create a system with multiple steps."""
        system_dir = self.create_test_system(temp_dir)
        flows_dir = system_dir / "flows"
        
        flow_data = {
            "id": "multi_flow",
            "name": "Multi Step Flow",
            "description": "A flow with multiple steps",
            "steps": [
                {
                    "id": "roll_stats",
                    "name": "Roll Stats",
                    "type": "dice_roll",
                    "roll": "3d6",
                    "output": "strength"
                },
                {
                    "id": "roll_hp",
                    "name": "Roll Hit Points",
                    "type": "dice_roll",
                    "roll": "1d8",
                    "output": "hp"
                },
                {
                    "id": "final_step",
                    "name": "Complete",
                    "type": "text",
                    "text": "Character complete!"
                }
            ]
        }
        
        with open(flows_dir / "multi_flow.yaml", "w") as f:
            yaml.dump(flow_data, f)
        
        return system_dir
    
    @pytest.mark.asyncio
    async def test_app_creation(self):
        """Test that the flow app can be created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_simple_flow_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "simple_flow")
            
            assert app.system_path == system_path
            assert app.flow_id == "simple_flow"
            assert app.engine is not None
            assert app.current_step == 0
    
    @pytest.mark.asyncio
    async def test_app_invalid_flow(self):
        """Test app with non-existent flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_simple_flow_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "nonexistent_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause(1.0)
                
                # Should show error in log
                log_widget = app.query_one("#log")
                log_content = str(log_widget.lines)
                assert "ERROR" in log_content or "not found" in log_content
    
    @pytest.mark.asyncio
    async def test_app_ui_structure(self):
        """Test that the app UI composes correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_simple_flow_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "simple_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause()
                
                # Check that key UI elements exist
                assert app.query_one("#system-info") is not None
                assert app.query_one("#flow-info") is not None
                assert app.query_one("#progress") is not None
                assert app.query_one("#status") is not None
                assert app.query_one("#log") is not None
    
    @pytest.mark.asyncio
    async def test_app_system_loading(self):
        """Test that the app loads system correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_simple_flow_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "simple_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause(1.0)
                
                # Check that system info is displayed
                system_info = app.query_one("#system-info")
                assert "Test System" in str(system_info.renderable)
                
                flow_info = app.query_one("#flow-info")
                assert "Simple Flow" in str(flow_info.renderable)
    
    @pytest.mark.asyncio
    async def test_app_progress_updates(self):
        """Test that progress bar updates during execution."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_multi_step_flow_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "multi_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause(2.0)  # Let execution progress
                
                # Progress should have updated
                progress_bar = app.query_one("#progress")
                assert progress_bar.progress > 0
    
    @pytest.mark.asyncio
    async def test_app_key_bindings(self):
        """Test that app responds to key bindings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_simple_flow_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "simple_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause()
                
                # Test restart key
                await pilot.press("r")
                await pilot.pause()
                
                # App should still be running after restart
                assert app.is_running
                
                # Test quit key
                await pilot.press("q")
                await pilot.pause()
                
                # App should exit
                assert not app.is_running
    
    @pytest.mark.asyncio
    async def test_app_restart_functionality(self):
        """Test that restart clears state properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_simple_flow_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "simple_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause(1.0)  # Let initial execution start
                
                # Trigger restart
                await pilot.press("r")
                await pilot.pause()
                
                # Check that state was reset
                assert app.current_step == 0
                assert len(app.step_results) == 0
                
                # Progress should be reset
                progress_bar = app.query_one("#progress")
                assert progress_bar.progress == 0
    
    @pytest.mark.asyncio
    async def test_step_execution_logging(self):
        """Test that step execution is logged correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_simple_flow_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "simple_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause(1.5)
                
                # Check that log contains expected messages
                log_widget = app.query_one("#log")
                log_content = str(log_widget.lines)
                
                assert "Loading system" in log_content
                assert "Starting step" in log_content
                assert "Completed step" in log_content or "Step result" in log_content


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_modal_with_empty_choices(self):
        """Test modal behavior with empty choices list."""
        modal = SimpleChoiceModal("No choices", [])
        
        assert modal.prompt == "No choices"
        assert len(modal.choices) == 0
    
    @pytest.mark.asyncio
    async def test_modal_with_none_choice(self):
        """Test modal behavior with None in choices."""
        choices = [None, MockChoice("valid", "Valid Choice")]
        modal = SimpleChoiceModal("Mixed choices", choices)
        
        # Should handle None gracefully
        assert len(modal.choices) == 2
    
    @pytest.mark.asyncio
    async def test_app_with_invalid_system_path(self):
        """Test app with invalid system path."""
        invalid_path = Path("/nonexistent/path")
        app = SimpleFlowApp(invalid_path, "some_flow")
        
        async with app.run_test() as pilot:
            await pilot.pause(1.0)
            
            # Should handle error gracefully
            log_widget = app.query_one("#log")
            log_content = str(log_widget.lines)
            assert "ERROR" in log_content


class TestUIInteractions:
    """Test complex UI interaction scenarios."""
    
    @pytest.mark.asyncio
    async def test_rapid_button_clicks(self):
        """Test rapid clicking of modal buttons."""
        from textual.app import App
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_results = []
            
            def handle_modal_result(self, result):
                self.modal_results.append(result)
            
            async def test_modal(self):
                choices = [MockChoice("option1", "Option 1")]
                modal = SimpleChoiceModal("Rapid test", choices)
                self.push_screen(modal, self.handle_modal_result)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.test_modal)
            await pilot.pause()
            
            # Select option
            await pilot.click("RadioButton")
            await pilot.pause(0.1)
            
            # Rapid clicks on confirm
            for _ in range(3):
                await pilot.click("#confirm")
                await pilot.pause(0.1)
            
            # Should only get one result
            assert len(app.modal_results) == 1
            assert app.modal_results[0] == "option1"
    
    @pytest.mark.asyncio
    async def test_keyboard_navigation(self):
        """Test keyboard navigation in modal."""
        from textual.app import App
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"
            
            def handle_modal_result(self, result):
                self.modal_result = result
            
            async def test_modal(self):
                choices = [
                    MockChoice("first", "First"),
                    MockChoice("second", "Second")
                ]
                modal = SimpleChoiceModal("Keyboard test", choices)
                self.push_screen(modal, self.handle_modal_result)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.test_modal)
            await pilot.pause()
            
            # Use tab to navigate and space to select
            await pilot.press("tab")  # Focus first radio
            await pilot.pause()
            await pilot.press("space")  # Select first radio
            await pilot.pause()
            await pilot.press("tab", "tab", "tab")  # Navigate to confirm button
            await pilot.pause()
            await pilot.press("enter")  # Press confirm
            await pilot.pause()
            
            assert app.modal_result == "first"


class TestModalStates:
    """Test different modal state scenarios."""
    
    @pytest.mark.asyncio
    async def test_modal_long_prompt(self):
        """Test modal with very long prompt text."""
        long_prompt = "This is a very long prompt that should test how the modal handles " * 10
        choices = [MockChoice("choice1", "Choice 1")]
        modal = SimpleChoiceModal(long_prompt, choices)
        
        assert len(modal.prompt) > 500
        assert modal.prompt == long_prompt
    
    @pytest.mark.asyncio
    async def test_modal_long_choice_labels(self):
        """Test modal with very long choice labels."""
        long_label = "This is an extremely long choice label that should test wrapping " * 5
        choices = [MockChoice("choice1", long_label)]
        modal = SimpleChoiceModal("Test", choices)
        
        assert len(modal.choices[0].label) > 300
    
    @pytest.mark.asyncio
    async def test_modal_special_characters(self):
        """Test modal with special characters in text."""
        special_prompt = "Choose: émojis 🎮, symbols ★☆, and unicode ñáéí"
        choices = [
            MockChoice("emoji", "🎮 Gaming Choice"),
            MockChoice("symbol", "★ Special Symbol"),
            MockChoice("unicode", "ñáéí Unicode")
        ]
        modal = SimpleChoiceModal(special_prompt, choices)
        
        assert "🎮" in modal.prompt
        assert "★" in modal.choices[1].label
        assert "ñáéí" in modal.choices[2].label


if __name__ == "__main__":
    pytest.main([__file__])
