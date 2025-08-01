"""
Focused test to debug modal behavior.
"""

import sys
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Button, RadioButton, RadioSet

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grimoire_runner.ui.simple_textual import SimpleChoiceModal


class MockChoice:
    """Mock choice for testing."""

    def __init__(self, id: str, label: str):
        self.id = id
        self.label = label


class DebugModalApp(App):
    """Debug app to test modal behavior."""

    def __init__(self):
        super().__init__()
        self.modal_result = "not_set"
        self.modal_shown = False

    async def on_mount(self):
        """Show modal on mount."""
        await self.show_test_modal()

    async def show_test_modal(self):
        """Show a test modal."""
        choices = [
            MockChoice("keep", "Keep abilities as rolled"),
            MockChoice("swap", "Swap two ability scores"),
        ]
        modal = SimpleChoiceModal("Test modal prompt", choices)
        self.modal_shown = True

        # This should block until user makes a choice
        print("[DEBUG] About to push_screen")
        self.modal_result = await self.push_screen(modal)
        print(f"[DEBUG] push_screen returned: {self.modal_result}")


class TestModalDebug:
    """Debug tests for modal behavior."""

    @pytest.mark.asyncio
    async def test_modal_lifecycle(self):
        """Test the complete modal lifecycle."""
        app = DebugModalApp()

        async with app.run_test() as pilot:
            # Wait for modal to appear
            await pilot.pause(0.5)

            # Check that modal was shown
            assert app.modal_shown

            # Check if modal is in screen stack
            print(f"Screen stack length: {len(app.screen_stack)}")
            print(f"Screen stack: {[type(s).__name__ for s in app.screen_stack]}")

            if len(app.screen_stack) > 1:
                modal = app.screen_stack[-1]
                print(f"Top screen type: {type(modal).__name__}")

                if isinstance(modal, SimpleChoiceModal):
                    print("Modal is properly displayed")

                    # Check RadioSet state
                    try:
                        radio_set = modal.query_one("#choice-set", RadioSet)
                        print(
                            f"RadioSet found, pressed_button: {radio_set.pressed_button}"
                        )

                        # Try to click first radio button
                        radio_buttons = modal.query("RadioButton")
                        print(f"Found {len(radio_buttons)} radio buttons")

                        if radio_buttons:
                            await pilot.click("RadioButton")
                            await pilot.pause()

                            # Check state after click
                            radio_set = modal.query_one("#choice-set", RadioSet)
                            print(
                                f"After click, pressed_button: {radio_set.pressed_button}"
                            )

                            # Try to confirm
                            await pilot.click("#confirm")
                            await pilot.pause()

                            print(f"After confirm, modal_result: {app.modal_result}")
                            print(
                                f"Screen stack length after confirm: {len(app.screen_stack)}"
                            )

                    except Exception as e:
                        print(f"Error testing RadioSet: {e}")
            else:
                print("Modal not found in screen stack")
                print(f"Modal result: {app.modal_result}")

    @pytest.mark.asyncio
    async def test_simple_radio_set(self):
        """Test RadioSet behavior in isolation."""
        from textual.containers import Container

        class SimpleRadioApp(App):
            def compose(self):
                with Container():
                    with RadioSet(id="test-radio"):
                        yield RadioButton("Option 1", id="opt1")
                        yield RadioButton("Option 2", id="opt2")
                    yield Button("Test", id="test-button")

        app = SimpleRadioApp()

        async with app.run_test() as pilot:
            await pilot.pause()

            # Check initial state
            radio_set = app.query_one("#test-radio", RadioSet)
            print(f"Initial pressed_button: {radio_set.pressed_button}")

            # Click first radio button
            await pilot.click("RadioButton")
            await pilot.pause()

            # Check state after click
            radio_set = app.query_one("#test-radio", RadioSet)
            print(f"After click pressed_button: {radio_set.pressed_button}")
            print(
                f"Pressed button ID: {radio_set.pressed_button.id if radio_set.pressed_button else None}"
            )

            # This should work correctly
            assert radio_set.pressed_button is not None
            assert radio_set.pressed_button.id == "opt1"

    @pytest.mark.asyncio
    async def test_modal_without_push_screen(self):
        """Test modal component directly without push_screen."""

        class DirectModalApp(App):
            def compose(self):
                choices = [
                    MockChoice("option1", "Option 1"),
                    MockChoice("option2", "Option 2"),
                ]
                yield SimpleChoiceModal("Direct modal test", choices)

        app = DirectModalApp()

        async with app.run_test() as pilot:
            await pilot.pause()

            # Test direct interaction with modal
            modal = app.query_one(SimpleChoiceModal)
            print(f"Modal prompt: {modal.prompt}")
            print(f"Modal choices: {len(modal.choices)}")

            # Try clicking radio button
            await pilot.click("RadioButton")
            await pilot.pause()

            # Check radio set state
            radio_set = modal.query_one("#choice-set", RadioSet)
            print(f"RadioSet pressed_button: {radio_set.pressed_button}")

            if radio_set.pressed_button:
                print(f"Selected value: {radio_set.pressed_button.value}")

                # Try confirm button
                await pilot.click("#confirm")
                await pilot.pause()

                print("Confirm button clicked")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to see print output
