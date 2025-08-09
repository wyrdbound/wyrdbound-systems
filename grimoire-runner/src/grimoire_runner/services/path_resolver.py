"""Centralized path resolution service using Chain of Responsibility pattern."""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext

logger = logging.getLogger(__name__)


class PathResolutionError(Exception):
    """Exception raised when path resolution fails."""

    pass


class PathResolverHandler(ABC):
    """Abstract base class for path resolution handlers in Chain of Responsibility pattern."""

    def __init__(self, next_handler: Optional["PathResolverHandler"] = None):
        self._next_handler = next_handler

    def set_next(self, handler: "PathResolverHandler") -> "PathResolverHandler":
        """Set the next handler in the chain."""
        self._next_handler = handler
        return handler

    def handle_get(self, context: "ExecutionContext", path: str) -> Any:
        """Handle path resolution for getting values."""
        try:
            result = self._handle_get(context, path)
            if result is not None:
                logger.debug(f"PathResolver: {self.__class__.__name__} resolved get '{path}' = {result}")
                return result
        except Exception as e:
            logger.debug(f"PathResolver: {self.__class__.__name__} failed to resolve get '{path}': {e}")

        if self._next_handler:
            return self._next_handler.handle_get(context, path)
        
        raise PathResolutionError(f"Cannot resolve path '{path}' for reading")

    def handle_set(self, context: "ExecutionContext", path: str, value: Any) -> bool:
        """Handle path resolution for setting values."""
        try:
            success = self._handle_set(context, path, value)
            if success:
                logger.debug(f"PathResolver: {self.__class__.__name__} handled set '{path}' = {value}")
                return True
        except Exception as e:
            logger.debug(f"PathResolver: {self.__class__.__name__} failed to handle set '{path}': {e}")

        if self._next_handler:
            return self._next_handler.handle_set(context, path, value)
        
        raise PathResolutionError(f"Cannot resolve path '{path}' for writing")

    @abstractmethod
    def _handle_get(self, context: "ExecutionContext", path: str) -> Any:
        """Implement specific get logic for this handler."""
        pass

    @abstractmethod
    def _handle_set(self, context: "ExecutionContext", path: str, value: Any) -> bool:
        """Implement specific set logic for this handler."""
        pass


class OutputsPathHandler(PathResolverHandler):
    """Handler for paths starting with 'outputs.'"""

    def _handle_get(self, context: "ExecutionContext", path: str) -> Any:
        if not path.startswith("outputs."):
            return None
        
        # Remove 'outputs.' prefix and resolve in outputs dict
        output_path = path[8:]  # len("outputs.") = 8
        return self._get_nested_value(context.outputs, output_path)

    def _handle_set(self, context: "ExecutionContext", path: str, value: Any) -> bool:
        if not path.startswith("outputs."):
            return False
        
        # Remove 'outputs.' prefix and set in outputs dict
        output_path = path[8:]  # len("outputs.") = 8
        
        # Use the derived field manager if available for observable updates
        if hasattr(context, '_derived_field_manager') and context._derived_field_manager:
            context._derived_field_manager.set_field_value(output_path, value)
        else:
            self._set_nested_value(context.outputs, output_path, value)
        
        return True

    def _get_nested_value(self, obj: dict[str, Any], path: str) -> Any:
        """Get a nested value by dot-separated path."""
        if not path:
            return obj

        parts = path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Path '{path}' not found")

        return current

    def _set_nested_value(self, obj: dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value by dot-separated path, creating intermediate dicts as needed."""
        if not path:
            raise ValueError("Path cannot be empty")

        parts = path.split(".")
        current = obj

        # Navigate to parent of target
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise ValueError(f"Cannot set nested value: '{part}' is not a dict")
            current = current[part]

        # Set the final value
        final_key = parts[-1]
        current[final_key] = value


class VariablesPathHandler(PathResolverHandler):
    """Handler for paths starting with 'variables.'"""

    def _handle_get(self, context: "ExecutionContext", path: str) -> Any:
        if not path.startswith("variables."):
            return None
        
        # Remove 'variables.' prefix and resolve in variables dict
        var_path = path[10:]  # len("variables.") = 10
        return self._get_nested_value(context.variables, var_path)

    def _handle_set(self, context: "ExecutionContext", path: str, value: Any) -> bool:
        if not path.startswith("variables."):
            return False
        
        # Remove 'variables.' prefix and set in variables dict
        var_path = path[10:]  # len("variables.") = 10
        self._set_nested_value(context.variables, var_path, value)
        return True

    def _get_nested_value(self, obj: dict[str, Any], path: str) -> Any:
        """Get a nested value by dot-separated path."""
        if not path:
            return obj

        parts = path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Path '{path}' not found")

        return current

    def _set_nested_value(self, obj: dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value by dot-separated path, creating intermediate dicts as needed."""
        if not path:
            raise ValueError("Path cannot be empty")

        parts = path.split(".")
        current = obj

        # Navigate to parent of target
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise ValueError(f"Cannot set nested value: '{part}' is not a dict")
            current = current[part]

        # Set the final value
        final_key = parts[-1]
        current[final_key] = value


class InputsPathHandler(PathResolverHandler):
    """Handler for paths starting with 'inputs.'"""

    def _handle_get(self, context: "ExecutionContext", path: str) -> Any:
        if not path.startswith("inputs."):
            return None
        
        # Remove 'inputs.' prefix and resolve in inputs dict
        input_path = path[7:]  # len("inputs.") = 7
        return self._get_nested_value(context.inputs, input_path)

    def _handle_set(self, context: "ExecutionContext", path: str, value: Any) -> bool:
        if not path.startswith("inputs."):
            return False
        
        # Remove 'inputs.' prefix and set in inputs dict
        input_path = path[7:]  # len("inputs.") = 7
        self._set_nested_value(context.inputs, input_path, value)
        return True

    def _get_nested_value(self, obj: dict[str, Any], path: str) -> Any:
        """Get a nested value by dot-separated path."""
        if not path:
            return obj

        parts = path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Path '{path}' not found")

        return current

    def _set_nested_value(self, obj: dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value by dot-separated path, creating intermediate dicts as needed."""
        if not path:
            raise ValueError("Path cannot be empty")

        parts = path.split(".")
        current = obj

        # Navigate to parent of target
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise ValueError(f"Cannot set nested value: '{part}' is not a dict")
            current = current[part]

        # Set the final value
        final_key = parts[-1]
        current[final_key] = value


class SystemPathHandler(PathResolverHandler):
    """Handler for paths starting with 'system.'"""

    def _handle_get(self, context: "ExecutionContext", path: str) -> Any:
        if not path.startswith("system."):
            return None
        
        # Remove 'system.' prefix and resolve in system_metadata dict
        system_path = path[7:]  # len("system.") = 7
        return self._get_nested_value(context.system_metadata, system_path)

    def _handle_set(self, context: "ExecutionContext", path: str, value: Any) -> bool:
        if not path.startswith("system."):
            return False
        
        # Remove 'system.' prefix and set in system_metadata dict
        system_path = path[7:]  # len("system.") = 7
        self._set_nested_value(context.system_metadata, system_path, value)
        return True

    def _get_nested_value(self, obj: dict[str, Any], path: str) -> Any:
        """Get a nested value by dot-separated path."""
        if not path:
            return obj

        parts = path.split(".")
        current = obj

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                raise KeyError(f"Path '{path}' not found")

        return current

    def _set_nested_value(self, obj: dict[str, Any], path: str, value: Any) -> None:
        """Set a nested value by dot-separated path, creating intermediate dicts as needed."""
        if not path:
            raise ValueError("Path cannot be empty")

        parts = path.split(".")
        current = obj

        # Navigate to parent of target
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                raise ValueError(f"Cannot set nested value: '{part}' is not a dict")
            current = current[part]

        # Set the final value
        final_key = parts[-1]
        current[final_key] = value


class DirectVariableHandler(PathResolverHandler):
    """Handler for direct variable names (no prefix) - variables dict fallback."""

    def _handle_get(self, context: "ExecutionContext", path: str) -> Any:
        # Only handle simple names without dots
        if "." in path:
            return None
        
        # Try direct lookup in variables
        if path in context.variables:
            return context.variables[path]
        
        return None

    def _handle_set(self, context: "ExecutionContext", path: str, value: Any) -> bool:
        # Only handle simple names without dots
        if "." in path:
            return False
        
        # Set directly in variables
        context.variables[path] = value
        return True


class PathResolver:
    """Centralized path resolution service using Chain of Responsibility pattern."""

    def __init__(self):
        """Initialize the path resolver with the default handler chain."""
        # Build the chain of responsibility
        self.handler_chain = OutputsPathHandler()
        self.handler_chain.set_next(
            VariablesPathHandler()
        ).set_next(
            InputsPathHandler()
        ).set_next(
            SystemPathHandler()
        ).set_next(
            DirectVariableHandler()
        )

    def get_value(self, context: "ExecutionContext", path: str, default: Any = None) -> Any:
        """Get a value at the specified path."""
        try:
            return self.handler_chain.handle_get(context, path)
        except PathResolutionError:
            return default

    def set_value(self, context: "ExecutionContext", path: str, value: Any) -> None:
        """Set a value at the specified path."""
        try:
            self.handler_chain.handle_set(context, path, value)
        except PathResolutionError as e:
            raise ValueError(str(e))

    def has_value(self, context: "ExecutionContext", path: str) -> bool:
        """Check if a value exists at the specified path."""
        try:
            self.handler_chain.handle_get(context, path)
            return True
        except PathResolutionError:
            return False

    def add_handler(self, handler: PathResolverHandler) -> None:
        """Add a custom handler to the end of the chain."""
        # Find the end of the current chain
        current = self.handler_chain
        while current._next_handler is not None:
            current = current._next_handler
        
        # Add the new handler
        current.set_next(handler)
