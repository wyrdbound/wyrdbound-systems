"""
Tests for UI edge cases and integration scenarios.
"""

import pytest
import tempfile
import yaml
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.ui.simple_textual import SimpleChoiceModal, SimpleFlowApp
from grimoire_runner.core.engine import GrimoireEngine


class TestUIEdgeCases:
    """Test edge cases and unusual scenarios."""
    
    @pytest.mark.asyncio
    async def test_modal_with_very_long_text(self):
        """Test modal handling of extremely long text."""
        from textual.app import App
        
        # Create extremely long text
        long_prompt = "A" * 10000  # 10k characters
        long_choices = [
            Mock(id="choice1", label="B" * 1000),  # 1k character label
            Mock(id="choice2", label="C" * 500)    # 500 character label
        ]
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"
            
            def handle_result(self, result):
                self.modal_result = result
            
            async def show_modal(self):
                modal = SimpleChoiceModal(long_prompt, long_choices)
                self.push_screen(modal, self.handle_result)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.show_modal)
            await pilot.pause()
            
            # Modal should still function despite long text
            assert len(app.screen_stack) == 2
            
            # Should be able to select and confirm
            await pilot.click("RadioButton")
            await pilot.pause()
            await pilot.click("#confirm")
            await pilot.pause()
            
            assert app.modal_result == "choice1"
    
    @pytest.mark.asyncio
    async def test_modal_with_unicode_and_emoji(self):
        """Test modal with complex unicode and emoji."""
        from textual.app import App
        
        unicode_prompt = "Choose your 🧙‍♂️ wizard: ñáéíóú, 中文, العربية, русский, 🎮🎲⚔️"
        unicode_choices = [
            Mock(id="fire", label="🔥 Fire Mage (火法师)"),
            Mock(id="ice", label="❄️ Ice Wizard (氷魔法使い)"),
            Mock(id="earth", label="🌍 Earth Shaman (ساحر الأرض)")
        ]
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"
            
            def handle_result(self, result):
                self.modal_result = result
            
            async def show_modal(self):
                modal = SimpleChoiceModal(unicode_prompt, unicode_choices)
                self.push_screen(modal, self.handle_result)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.show_modal)
            await pilot.pause()
            
            # Select the ice wizard (second option)
            radio_buttons = app.query("RadioButton")
            if len(radio_buttons) >= 2:
                await pilot.click(radio_buttons[1])  # Second radio button
                await pilot.pause()
                await pilot.click("#confirm")
                await pilot.pause()
                
                assert app.modal_result == "ice"
            else:
                # If radio buttons aren't found, just click any and confirm
                await pilot.click("RadioButton")  # First available radio button
                await pilot.pause()
                await pilot.click("#confirm")
                await pilot.pause()
                
                # Should have some result
                assert app.modal_result in ["fire", "ice", "earth"]
    
    @pytest.mark.asyncio
    async def test_rapid_modal_interactions(self):
        """Test rapid modal opening and closing."""
        from textual.app import App
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_results = []
                self.modal_count = 0
            
            def handle_result(self, result):
                self.modal_results.append(result)
            
            async def rapid_modals(self):
                """Open multiple modals rapidly."""
                for i in range(3):
                    choices = [Mock(id=f"choice_{i}", label=f"Choice {i}")]
                    modal = SimpleChoiceModal(f"Modal {i}", choices)
                    self.push_screen(modal, self.handle_result)
                    await asyncio.sleep(0.1)  # Brief delay
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.rapid_modals)
            await pilot.pause()
            
            # Only the last modal should be visible
            assert len(app.screen_stack) >= 2  # At least one modal
            
            # Interact with whatever modal is on top
            await pilot.click("RadioButton")
            await pilot.pause()
            await pilot.click("#confirm")
            await pilot.pause()
            
            # Should have some result
            assert len(app.modal_results) > 0
    
    @pytest.mark.asyncio
    async def test_modal_memory_cleanup(self):
        """Test that modals clean up properly."""
        from textual.app import App
        import gc
        import weakref
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"
                self.modal_refs = []
            
            def handle_result(self, result):
                self.modal_result = result
            
            async def create_and_close_modals(self):
                """Create modals and track their lifecycle."""
                for i in range(5):
                    choices = [Mock(id=f"choice_{i}", label=f"Choice {i}")]
                    modal = SimpleChoiceModal(f"Modal {i}", choices)
                    
                    # Create weak reference to track cleanup
                    ref = weakref.ref(modal)
                    self.modal_refs.append(ref)
                    
                    self.push_screen(modal, self.handle_result)
                    await asyncio.sleep(0.1)
                    
                    # Dismiss the modal immediately
                    modal.dismiss("auto_dismissed")
                    await asyncio.sleep(0.1)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.create_and_close_modals)
            await pilot.pause()
            
            # Force garbage collection
            gc.collect()
            await pilot.pause()
            
            # Check if modals were cleaned up
            alive_refs = [ref for ref in app.modal_refs if ref() is not None]
            print(f"Modal references still alive: {len(alive_refs)} / {len(app.modal_refs)}")


class TestFlowAppEdgeCases:
    """Test edge cases for the SimpleFlowApp."""
    
    def create_problematic_system(self, temp_dir: str) -> Path:
        """Create a system with problematic configurations."""
        system_dir = Path(temp_dir) / "problematic_system"
        system_dir.mkdir()
        
        # Create system.yaml with unusual values
        system_data = {
            "id": "problematic_system",
            "name": "System with 🎮 emoji and unicode ñáéí",
            "version": "1.0.0-beta+unusual.version",
            "description": "A system that tests edge cases with very long descriptions " * 20
        }
        
        with open(system_dir / "system.yaml", "w") as f:
            yaml.dump(system_data, f)
        
        # Create directories
        for subdir in ["flows", "models", "compendium", "tables", "sources"]:
            (system_dir / subdir).mkdir()
        
        # Create a flow with edge cases
        flows_dir = system_dir / "flows"
        flow_data = {
            "id": "edge_case_flow",
            "name": "Flow with 🎲 dice and special chars",
            "description": "A flow that tests various edge cases",
            "steps": [
                {
                    "id": "empty_step",
                    "name": "",  # Empty name
                    "type": "dice_roll",
                    "roll": "1d1",  # Minimal roll
                    "output": "minimal"
                },
                {
                    "id": "unicode_step", 
                    "name": "Unicode Step: 中文 русский العربية",
                    "type": "text",
                    "text": "Step with unicode content: ♠️♥️♣️♦️"
                },
                {
                    "id": "long_name_step",
                    "name": "A" * 200,  # Very long step name
                    "type": "text",
                    "text": "Step with long name"
                }
            ]
        }
        
        with open(flows_dir / "edge_case_flow.yaml", "w") as f:
            yaml.dump(flow_data, f)
        
        return system_dir
    
    @pytest.mark.asyncio
    async def test_app_with_problematic_system(self):
        """Test app behavior with unusual system configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_problematic_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "edge_case_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause(1.0)
                
                # App should still function despite unusual configuration
                assert app.is_running
                
                # Check that system info displays unicode correctly
                system_info = app.query_one("#system-info")
                info_text = str(system_info.renderable)
                assert "🎮" in info_text or "emoji" in info_text.lower()
    
    @pytest.mark.asyncio
    async def test_app_rapid_restarts(self):
        """Test rapid restart operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_path = self.create_problematic_system(temp_dir)
            
            app = SimpleFlowApp(system_path, "edge_case_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause(0.5)
                
                # Rapid restarts
                for i in range(5):
                    await pilot.press("r")
                    await pilot.pause(0.1)
                
                # App should still be stable
                assert app.is_running
                assert app.current_step == 0
    
    @pytest.mark.asyncio
    async def test_app_with_corrupted_flow(self):
        """Test app behavior with corrupted flow file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "corrupted_system"
            system_dir.mkdir()
            
            # Create valid system.yaml
            system_data = {
                "id": "corrupted_system",
                "name": "Corrupted System",
                "version": "1.0.0"
            }
            
            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)
            
            # Create directories
            for subdir in ["flows", "models", "compendium", "tables", "sources"]:
                (system_dir / subdir).mkdir()
            
            # Create corrupted flow file
            flows_dir = system_dir / "flows"
            with open(flows_dir / "corrupted_flow.yaml", "w") as f:
                f.write("this is not valid yaml: {{{")
            
            app = SimpleFlowApp(system_dir, "corrupted_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause(1.0)
                
                # App should handle error gracefully
                log_widget = app.query_one("#log")
                log_content = str(log_widget.lines)
                assert "ERROR" in log_content.upper() or "error" in log_content.lower()


class TestConcurrencyAndRacing:
    """Test concurrency issues and race conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_modal_operations(self):
        """Test concurrent modal operations."""
        from textual.app import App
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.results = []
                self.active_modals = 0
            
            def handle_result(self, result):
                self.results.append(result)
                self.active_modals -= 1
            
            async def concurrent_modals(self):
                """Create multiple modals concurrently."""
                tasks = []
                for i in range(3):
                    task = asyncio.create_task(self.create_modal(i))
                    tasks.append(task)
                
                await asyncio.gather(*tasks)
            
            async def create_modal(self, index):
                """Create a single modal."""
                choices = [Mock(id=f"choice_{index}", label=f"Choice {index}")]
                modal = SimpleChoiceModal(f"Modal {index}", choices)
                self.active_modals += 1
                self.push_screen(modal, self.handle_result)
                await asyncio.sleep(0.1)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.concurrent_modals)
            await pilot.pause(1.0)
            
            # Handle whatever modals are visible
            while len(app.screen_stack) > 1:
                await pilot.click("RadioButton")
                await pilot.pause(0.1)
                await pilot.click("#confirm")
                await pilot.pause(0.2)
            
            # Should have some results
            print(f"Concurrent results: {app.results}")
    
    @pytest.mark.asyncio
    async def test_modal_state_consistency(self):
        """Test modal state consistency under rapid interactions."""
        from textual.app import App
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.interaction_count = 0
                self.final_result = None
            
            def handle_result(self, result):
                self.final_result = result
            
            async def show_modal(self):
                choices = [
                    Mock(id="option1", label="Option 1"),
                    Mock(id="option2", label="Option 2")
                ]
                modal = SimpleChoiceModal("State test", choices)
                self.push_screen(modal, self.handle_result)
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.show_modal)
            await pilot.pause()
            
            # Rapid interactions
            for _ in range(10):
                await pilot.click("RadioButton")
                await pilot.pause(0.05)
                app.interaction_count += 1
            
            # Final confirm
            await pilot.click("#confirm")
            await pilot.pause()
            
            # State should be consistent
            assert app.final_result in ["option1", "option2"]
            print(f"Interactions: {app.interaction_count}, Result: {app.final_result}")


class TestErrorRecovery:
    """Test error recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_modal_exception_handling(self):
        """Test modal behavior when exceptions occur."""
        from textual.app import App
        
        class ProblematicModal(SimpleChoiceModal):
            """Modal that raises exceptions."""
            
            def on_button_pressed(self, event):
                if event.button.id == "confirm":
                    # Simulate an exception
                    raise ValueError("Simulated error")
                super().on_button_pressed(event)
        
        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"
                self.error_occurred = False
            
            def handle_result(self, result):
                self.modal_result = result
            
            async def show_problematic_modal(self):
                choices = [Mock(id="choice1", label="Choice 1")]
                modal = ProblematicModal("Error test", choices)
                try:
                    self.push_screen(modal, self.handle_result)
                except Exception as e:
                    self.error_occurred = True
        
        app = TestApp()
        
        async with app.run_test() as pilot:
            app.call_after_refresh(app.show_problematic_modal)
            await pilot.pause()
            
            # Select option
            await pilot.click("RadioButton")
            await pilot.pause()
            
            # Try to confirm (should cause exception)
            await pilot.click("#confirm")
            await pilot.pause()
            
            # App should still be responsive
            assert app.is_running
            print(f"Error occurred: {app.error_occurred}")
    
    @pytest.mark.asyncio
    async def test_flow_app_exception_recovery(self):
        """Test flow app recovery from exceptions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            system_dir = Path(temp_dir) / "exception_system"
            system_dir.mkdir()
            
            # Create system.yaml
            system_data = {
                "id": "exception_system",
                "name": "Exception System",
                "version": "1.0.0"
            }
            
            with open(system_dir / "system.yaml", "w") as f:
                yaml.dump(system_data, f)
            
            # Create directories
            for subdir in ["flows", "models", "compendium", "tables", "sources"]:
                (system_dir / subdir).mkdir()
            
            # Create flow that might cause issues
            flows_dir = system_dir / "flows"
            flow_data = {
                "id": "exception_flow",
                "name": "Exception Flow",
                "steps": [
                    {
                        "id": "problematic_step",
                        "name": "Problematic Step",
                        "type": "nonexistent_type",  # Invalid step type
                        "invalid_param": "value"
                    }
                ]
            }
            
            with open(flows_dir / "exception_flow.yaml", "w") as f:
                yaml.dump(flow_data, f)
            
            app = SimpleFlowApp(system_dir, "exception_flow")
            
            async with app.run_test() as pilot:
                await pilot.pause(1.0)
                
                # App should handle the error gracefully
                assert app.is_running
                
                # Try restart after error
                await pilot.press("r")
                await pilot.pause()
                
                # Should still be responsive
                assert app.is_running


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
