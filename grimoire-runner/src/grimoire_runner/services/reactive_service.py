"""Reactive field service that uses the event system to trigger derived field computation."""

import logging
from typing import TYPE_CHECKING

from . import event_signals
from .event_signals import ValueSetData, FieldComputedData

if TYPE_CHECKING:
    from ..models.observable import DerivedFieldManager

logger = logging.getLogger(__name__)


class ReactiveFieldService:
    """Service that listens to value change events and triggers derived field computation."""

    def __init__(self):
        self.field_managers: dict[str, DerivedFieldManager] = {}
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """Setup event listeners for reactive field computation."""
        # Listen for value set events to trigger derived field computation
        event_signals.value_set.connect(self._on_value_set)

        # Listen for field computed events for logging/debugging
        event_signals.field_computed.connect(self._on_field_computed)

    def register_field_manager(self, context_id: str, field_manager: 'DerivedFieldManager'):
        """Register a field manager for a specific context."""
        logger.debug(f"Registering field manager for context: {context_id}")
        self.field_managers[context_id] = field_manager

    def unregister_field_manager(self, context_id: str):
        """Unregister a field manager for a specific context."""
        logger.debug(f"Unregistering field manager for context: {context_id}")
        if context_id in self.field_managers:
            del self.field_managers[context_id]

    def _on_value_set(self, sender, **kwargs):
        """Handle value set events."""
        event_data: ValueSetData = kwargs.get('data')
        if not event_data:
            return

        logger.debug(f"ReactiveFieldService: Value set event - {event_data.path} = {event_data.value}")

        # Find the appropriate field manager
        context_id = event_data.context_id or 'default'
        field_manager = self.field_managers.get(context_id)

        if not field_manager:
            logger.debug(f"No field manager found for context: {context_id}")
            return

        # Check if the sender is the field manager itself to avoid loops
        # If the event came from the field manager, the observables will handle recomputation
        if sender == field_manager:
            logger.debug("Event came from field manager itself, observables will handle recomputation")
            return

        # For external value sets, trigger recomputation of dependent fields
        field_manager._recompute_dependent_fields(event_data.path)

    def _on_field_computed(self, sender, **kwargs):
        """Handle field computed events for logging."""
        event_data: FieldComputedData = kwargs.get('data')
        if not event_data:
            return

        logger.debug(
            f"ReactiveFieldService: Field computed - {event_data.path} = {event_data.computed_value} "
            f"(from {event_data.source_fields})"
        )


# Global reactive field service instance
reactive_service = ReactiveFieldService()
