"""Event bus implementation using Blinker signals."""

from collections.abc import Callable
from typing import Any

from blinker import signal


class EventBus:
    """Central event bus for GRIMOIRE Engine using Blinker signals."""

    def __init__(self):
        # Core value/model events
        self.value_set = signal('value-set')
        self.field_computed = signal('field-computed')
        self.model_updated = signal('model-updated')

        # Step execution events
        self.step_executed = signal('step-executed')
        self.step_started = signal('step-started')

        # Flow events
        self.flow_started = signal('flow-started')
        self.flow_completed = signal('flow-completed')

    def emit(self, event_name: str, sender: Any = None, **kwargs):
        """Emit an event with the given name and data."""
        event_signal = getattr(self, event_name.replace('-', '_'), None)
        if event_signal:
            event_signal.send(sender or self, **kwargs)
        else:
            raise ValueError(f"Unknown event: {event_name}")

    def on(self, event_name: str, callback: Callable, sender: Any = None):
        """Register a callback for an event."""
        event_signal = getattr(self, event_name.replace('-', '_'), None)
        if event_signal:
            event_signal.connect(callback, sender=sender)
        else:
            raise ValueError(f"Unknown event: {event_name}")

    def off(self, event_name: str, callback: Callable, sender: Any = None):
        """Unregister a callback for an event."""
        event_signal = getattr(self, event_name.replace('-', '_'), None)
        if event_signal:
            event_signal.disconnect(callback, sender=sender)


# Global event bus instance
events = EventBus()
