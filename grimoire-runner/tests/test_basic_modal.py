"""
Test the most basic modal functionality.
"""

import sys
from pathlib import Path

import pytest
from textual.app import App
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class SimpleTestModal(ModalScreen[str]):
    """Most basic test modal."""

    def compose(self):
        with Container():
            yield Label("Test Modal")
            with Horizontal():
                yield Button("OK", id="ok")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            self.dismiss("ok_result")
        elif event.button.id == "cancel":
            self.dismiss("cancel_result")


class TestBasicModal:
    """Test the most basic modal behavior."""

    @pytest.mark.asyncio
    async def test_basic_modal(self):
        """Test basic modal with push_screen."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"

            def handle_modal_result(self, result):
                self.modal_result = result

            async def show_modal(self):
                modal = SimpleTestModal()
                # Try using callback instead of await
                self.push_screen(modal, self.handle_modal_result)

        app = TestApp()

        async with app.run_test() as pilot:
            # Start modal
            app.call_after_refresh(app.show_modal)
            await pilot.pause()

            # Should have modal in stack
            assert len(app.screen_stack) == 2
            assert isinstance(app.screen_stack[-1], SimpleTestModal)

            # Click OK
            await pilot.click("#ok")
            await pilot.pause()

            # Modal should be dismissed with result
            assert len(app.screen_stack) == 1
            assert app.modal_result == "ok_result"

    @pytest.mark.asyncio
    async def test_basic_modal_cancel(self):
        """Test basic modal cancellation."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"

            def handle_modal_result(self, result):
                self.modal_result = result

            async def show_modal(self):
                modal = SimpleTestModal()
                self.push_screen(modal, self.handle_modal_result)

        app = TestApp()

        async with app.run_test() as pilot:
            app.call_after_refresh(app.show_modal)
            await pilot.pause()

            # Click Cancel
            await pilot.click("#cancel")
            await pilot.pause()

            # Modal should be dismissed with cancel result
            assert len(app.screen_stack) == 1
            assert app.modal_result == "cancel_result"

    @pytest.mark.asyncio
    async def test_await_pattern_comparison(self):
        """Test comparison between await and callback patterns."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.await_result = "not_set"
                self.callback_result = "not_set"

            def handle_callback_result(self, result):
                self.callback_result = result

            async def test_await_pattern(self):
                """Test the await pattern (which we expect might fail)."""
                modal = SimpleTestModal()
                try:
                    self.await_result = await self.push_screen(modal)
                except Exception as e:
                    self.await_result = f"error: {e}"

            async def test_callback_pattern(self):
                """Test the callback pattern (which should work)."""
                modal = SimpleTestModal()
                self.push_screen(modal, self.handle_callback_result)

        app = TestApp()

        async with app.run_test() as pilot:
            # Test callback pattern first
            app.call_after_refresh(app.test_callback_pattern)
            await pilot.pause()

            # Interact with modal
            await pilot.click("#ok")
            await pilot.pause()

            # Callback should have worked
            assert app.callback_result == "ok_result"

            # Now test await pattern
            app.call_after_refresh(app.test_await_pattern)
            await pilot.pause()

            # May need to interact again if modal appears
            if len(app.screen_stack) > 1:
                await pilot.click("#ok")
                await pilot.pause()

            # Document what we find - this is exploratory
            # We expect await might return None or have issues
            print(f"Await result: {app.await_result}")
            print(f"Callback result: {app.callback_result}")

    @pytest.mark.asyncio
    async def test_multiple_modals_sequence(self):
        """Test multiple modals in sequence."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.results = []
                self.modal_count = 0

            def handle_modal_result(self, result):
                self.results.append(result)
                self.modal_count += 1

                # Show another modal if this was the first
                if self.modal_count == 1:
                    self.call_later(self.show_second_modal)

            def show_second_modal(self):
                modal = SimpleTestModal()
                self.push_screen(modal, self.handle_modal_result)

            async def show_first_modal(self):
                modal = SimpleTestModal()
                self.push_screen(modal, self.handle_modal_result)

        app = TestApp()

        async with app.run_test() as pilot:
            # Start first modal
            app.call_after_refresh(app.show_first_modal)
            await pilot.pause()

            # Click OK on first modal
            await pilot.click("#ok")
            await pilot.pause()

            # Second modal should appear
            assert len(app.screen_stack) == 2

            # Click Cancel on second modal
            await pilot.click("#cancel")
            await pilot.pause()

            # Both results should be recorded
            assert len(app.results) == 2
            assert app.results[0] == "ok_result"
            assert app.results[1] == "cancel_result"

    @pytest.mark.asyncio
    async def test_modal_escape_key(self):
        """Test modal behavior with escape key."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"

            def handle_modal_result(self, result):
                self.modal_result = result

            async def show_modal(self):
                modal = SimpleTestModal()
                self.push_screen(modal, self.handle_modal_result)

        app = TestApp()

        async with app.run_test() as pilot:
            app.call_after_refresh(app.show_modal)
            await pilot.pause()

            # Try escape key
            await pilot.press("escape")
            await pilot.pause()

            # Check if modal was dismissed (behavior may vary)
            print(f"Modal stack after escape: {len(app.screen_stack)}")
            print(f"Result after escape: {app.modal_result}")

    @pytest.mark.asyncio
    async def test_modal_button_focus(self):
        """Test button focus behavior in modal."""

        class TestApp(App):
            def __init__(self):
                super().__init__()
                self.modal_result = "not_set"

            def handle_modal_result(self, result):
                self.modal_result = result

            async def show_modal(self):
                modal = SimpleTestModal()
                self.push_screen(modal, self.handle_modal_result)

        app = TestApp()

        async with app.run_test() as pilot:
            app.call_after_refresh(app.show_modal)
            await pilot.pause()

            # Use tab to navigate between buttons
            await pilot.press("tab")
            await pilot.pause()
            await pilot.press("tab")
            await pilot.pause()

            # Use enter to activate focused button
            await pilot.press("enter")
            await pilot.pause()

            # Modal should be dismissed
            assert len(app.screen_stack) == 1
            # Result depends on which button had focus


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
