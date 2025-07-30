"""
GRIMOIRE Runner - Interactive system testing and development tool for GRIMOIRE tabletop RPG systems.
"""

from .core.engine import GrimoireEngine
from .core.context import ExecutionContext
from .models.system import System
from .models.flow import FlowDefinition, FlowResult
from .models.step import StepResult

__version__ = "0.1.0"

__all__ = [
    "GrimoireEngine",
    "ExecutionContext", 
    "System",
    "FlowDefinition",
    "FlowResult",
    "StepResult",
]
