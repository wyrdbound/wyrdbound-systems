"""Event data types for GRIMOIRE Engine events."""

from dataclasses import dataclass
from typing import Any


@dataclass
class EventData:
    """Base class for all event data."""
    pass


@dataclass
class ValueSetEvent(EventData):
    """Event emitted when a value is set in the context."""
    path: str
    value: Any
    old_value: Any | None = None
    context_id: str | None = None


@dataclass
class FieldComputedEvent(EventData):
    """Event emitted when a derived field is computed."""
    path: str
    computed_value: Any
    source_fields: list[str]
    context_id: str | None = None


@dataclass
class ModelUpdatedEvent(EventData):
    """Event emitted when a model instance is updated."""
    model_type: str
    instance_path: str
    fields_changed: list[str]
    context_id: str | None = None


@dataclass
class StepExecutedEvent(EventData):
    """Event emitted when a step is executed."""
    step_type: str
    step_id: str
    result: Any
    context_id: str | None = None
