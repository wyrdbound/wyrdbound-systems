"""
GRIMOIRE Runner - Interactive system testing and development tool for GRIMOIRE tabletop RPG systems.
"""

from .core.context import ExecutionContext
from .core.engine import GrimoireEngine
from .models.flow import FlowDefinition, FlowResult
from .models.step import StepResult
from .models.system import System

__version__ = "0.1.0"

__all__ = [
    "GrimoireEngine",
    "ExecutionContext",
    "System",
    "FlowDefinition",
    "FlowResult",
    "StepResult",
]
