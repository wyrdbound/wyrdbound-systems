"""Strategy pattern implementation for different action types."""

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.system import System
    from .executor_factories import TableExecutorFactory

logger = logging.getLogger(__name__)


class ActionStrategy(ABC):
    """Abstract base class for action execution strategies."""

    @abstractmethod
    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute the action with the given data."""

    @abstractmethod
    def get_action_type(self) -> str:
        """Get the action type this strategy handles."""


class SetValueActionStrategy(ActionStrategy):
    """Strategy for handling set_value actions."""

    def get_action_type(self) -> str:
        return "set_value"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a set_value action."""
        path = action_data["path"]
        value = action_data["value"]

        # Resolve templates in the path (e.g., "outputs.character.abilities.{{ item }}.bonus" -> "outputs.character.abilities.strength.bonus")
        resolved_path = context.resolve_template(path)
        logger.debug(
            f"Action set_value: Resolved path from '{path}' to '{resolved_path}'"
        )

        # Resolve the value to append
        if isinstance(value, dict):
            # Use dictionary directly without template resolution to preserve ModelAwareDict
            resolved_value = value
            logger.debug(f"Action set_value: Using dict directly for {resolved_path}")
            print(f"[DEBUG] SetValueActionStrategy: Using dict directly for {resolved_path}")
        elif isinstance(value, bool):
            # Preserve boolean values without template resolution
            resolved_value = value
            logger.debug(
                f"Action set_value: Using boolean directly for {resolved_path}"
            )
            print(f"[DEBUG] SetValueActionStrategy: Using boolean directly for {resolved_path}")
        else:
            # Check if this is a variable assignment and if we can preserve object types
            resolved_value = self._resolve_value_with_type_preservation(
                value, resolved_path, context, system
            )
            logger.debug(f"Action set_value: Resolved value for {resolved_path}")
            print(f"[DEBUG] SetValueActionStrategy: Template resolved value for {resolved_path}")
            print(f"[DEBUG] SetValueActionStrategy: Original value type: {type(value)}")
            print(f"[DEBUG] SetValueActionStrategy: Resolved value type: {type(resolved_value)}")
            print(f"[DEBUG] SetValueActionStrategy: Resolved value preview: {str(resolved_value)[:100]}...")

        # Use path resolver as the primary mechanism
        try:
            context.path_resolver.set_value(context, resolved_path, resolved_value)
            logger.debug(f"Successfully set {resolved_path} using path resolver")
        except Exception as e:
            logger.error(f"Path resolver failed for {resolved_path}: {e}")
            # Use namespaced paths to avoid collision during flow execution
            current_namespace = context.get_current_flow_namespace()

            if current_namespace:
                # Use namespaced path to avoid collision
                try:
                    if resolved_path.startswith("outputs."):
                        namespaced_path = f"{current_namespace}.outputs.{resolved_path[8:]}"
                    elif resolved_path.startswith("variables."):
                        namespaced_path = f"{current_namespace}.variables.{resolved_path[10:]}"
                    else:
                        # Default to outputs if no prefix specified
                        namespaced_path = f"{current_namespace}.outputs.{resolved_path}"

                    context.set_namespaced_value(namespaced_path, resolved_value)
                except Exception as e2:
                    logger.debug(f"Namespace operation also failed: {e2}")
                    raise e  # Re-raise original error
            else:
                # Fallback to original behavior for backward compatibility
                if resolved_path.startswith("outputs."):
                    context.set_output(resolved_path[8:], resolved_value)
                elif resolved_path.startswith("variables."):
                    context.set_variable(resolved_path[10:], resolved_value)
                else:
                    # Default to outputs
                    context.set_output(resolved_path, resolved_value)

    def _resolve_value_with_type_preservation(
        self,
        value: Any,
        path: str,
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> Any:
        """Resolve template value while preserving object types for typed variables."""
        # Get the expected variable type if this is a variable assignment
        expected_type = None
        if path.startswith("variables.") and system:
            variable_name = path[10:]  # Remove "variables." prefix
            expected_type = self._get_variable_type(variable_name, context, system)
            logger.debug(f"Variable {variable_name} has expected type: {expected_type}")

        logger.debug(
            f"Resolving value for {path}: {repr(value)} (type: {type(value).__name__})"
        )

        # First resolve the template to get the actual value
        print(f"[DEBUG] _resolve_value_with_type_preservation: About to resolve template: {value}")
        resolved_value = context.resolve_template(str(value))
        print(f"[DEBUG] _resolve_value_with_type_preservation: Template resolved to type: {type(resolved_value)}")
        print(f"[DEBUG] _resolve_value_with_type_preservation: Template resolved to preview: {str(resolved_value)[:100]}...")
        logger.debug(
            f"Template resolved to: {repr(resolved_value)} (type: {type(resolved_value).__name__})"
        )

        # For roll_result type variables, try to preserve RollResult objects
        if expected_type == "roll_result":
            # Check if the resolved value is already a RollResult object
            from ..models.roll_result import RollResult

            if isinstance(resolved_value, RollResult):
                logger.debug(f"Template resolved to RollResult object for {path}")
                return resolved_value

        # Post-processing: if we expected a roll_result but got a string, try to convert
        if expected_type == "roll_result" and isinstance(resolved_value, str):
            converted_result = self._convert_string_to_roll_result(resolved_value)
            if converted_result:
                logger.debug(f"Converted string to RollResult for {path}")
                return converted_result

        return resolved_value

    def _get_variable_type(
        self,
        variable_name: str,
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> str | None:
        """Get the expected type for a variable from the flow definition."""
        if not system:
            return None

        # Try to get the current flow definition to find variable type
        current_execution = context.get_current_execution()
        if current_execution and hasattr(current_execution, "flow_id"):
            flow_id = current_execution.flow_id
            if flow_id in system.flows:
                flow_def = system.flows[flow_id]
                for var_def in flow_def.variables:
                    if var_def.id == variable_name:
                        return var_def.type
        return None

    def _convert_string_to_roll_result(self, value_str: str) -> Any:
        """Try to convert a string back to a RollResult object if it looks like one."""
        from ..models.roll_result import RollResult

        # This is a simple heuristic - in practice, once we preserve the object properly,
        # this shouldn't be needed, but it's here as a fallback
        if not isinstance(value_str, str):
            return None

        # Look for patterns like "15 = 15 (1d20: 15) + 0" which indicate a dice roll result
        import re

        pattern = r"^(\d+)\s*=.*\(1d\d+.*\).*$"
        match = re.match(pattern, value_str.strip())

        if match:
            try:
                total = int(match.group(1))
                # Create a basic RollResult from the parsed information
                return RollResult(
                    total=total,
                    detail=value_str,
                    expression="unknown",  # We'd need more parsing to get this
                )
            except (ValueError, AttributeError):
                pass

        return None


class AppendItemActionStrategy(ActionStrategy):
    """Strategy for handling append_item actions."""

    def get_action_type(self) -> str:
        return "append_item"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute an append_item action."""
        path = action_data["path"]
        value = action_data["value"]

        # Resolve templates in the path
        resolved_path = context.resolve_template(path)
        logger.debug(
            f"Action append_item: Resolved path from '{path}' to '{resolved_path}'"
        )

        # Resolve the value to append
        if isinstance(value, dict):
            # Use dictionary directly without template resolution to preserve ModelAwareDict
            resolved_value = value
            logger.debug(f"Action append_item: Using dict directly for {resolved_path}")
        else:
            resolved_value = context.resolve_template(str(value))
            logger.debug(f"Action append_item: Resolved value for {resolved_path}")

        # Get the current list value
        try:
            current_list = context.path_resolver.get_value(context, resolved_path, [])
            if not isinstance(current_list, list):
                current_list = []
            
            # Append the new item to the list
            updated_list = current_list + [resolved_value]
            
            # Set the updated list back
            context.path_resolver.set_value(context, resolved_path, updated_list)
            logger.debug(f"Successfully appended item to {resolved_path}")
        except Exception as e:
            logger.error(f"Failed to append item to {resolved_path}: {e}")
            raise


class DisplayValueActionStrategy(ActionStrategy):
    """Strategy for handling display_value actions."""

    def get_action_type(self) -> str:
        return "display_value"

    def execute(
        self,
        action_data: dict[str, Any] | str,
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a display_value action."""
        path = (
            action_data if isinstance(action_data, str) else action_data.get("path", "")
        )
        try:
            # For simple variable names (no dots), check step data first
            if "." not in path and context.current_step:
                step_data = context.step_data.get(context.current_step, {})
                if path in step_data:
                    value = step_data[path]
                else:
                    # Fall back to path resolution
                    value = context.resolve_path_value(path)
            else:
                # For complex paths, use path resolution
                value = context.resolve_path_value(path)

            # Format the value for user-friendly display
            formatted_value = self._format_value_for_display(value, path)
            
            # Debug: Add print statements to understand what's happening
            print(f"[DEBUG] Displaying {path}")
            print(f"[DEBUG] Value type: {type(value)}")
            print(f"[DEBUG] Value preview: {str(value)[:200]}...")
            
            display_value = value

            # Handle RollResult objects specially with table display
            from ..models.roll_result import RollResult
            if isinstance(display_value, RollResult):
                # Use Rich console directly for proper color rendering
                from rich.console import Console

                console = Console()

                # Print the header with colored path
                console.print("📋 Display Value: ", style="bold", end="")
                console.print(path, style="bold cyan")

                # Print the roll result as a table
                self._print_roll_result_table(display_value, console)

            # For Rich-formatted content, we need to handle it specially
            # Check for dict-like objects (including ModelAwareDict and other custom dict subclasses)
            elif hasattr(display_value, 'keys') and hasattr(display_value, '__getitem__'):
                # Check if it has content (safely handle objects that don't support len())
                try:
                    has_content = len(display_value) > 0
                except (TypeError, AttributeError):
                    # For objects that don't support len(), check if keys() returns anything
                    has_content = bool(list(display_value.keys()) if hasattr(display_value, 'keys') else False)

                if has_content:
                    # Use Rich console directly for proper color rendering
                    from rich.console import Console

                    console = Console()

                    # Print the header with colored path
                    console.print("📋 Display Value: ", style="bold", end="")
                    console.print(path, style="bold cyan")

                    # Print the table with proper Rich rendering
                    self._print_table_for_dict(display_value, path, console)
                else:
                    # Empty dict-like object
                    context.add_action_message(f"📋 Display Value: [bold cyan]{path}[/bold cyan]\n(empty)")
            else:
                # For simple values, use the regular message system
                context.add_action_message(f"📋 Display Value: [bold cyan]{path}[/bold cyan]\n{formatted_value}")

            # Also log it for debugging
            logger.debug(f"Display: {path} = {value}")
        except Exception as e:
            error_msg = f"Could not display value at path {path}: {e}"
            context.add_action_message(f"⚠️ {error_msg}")
            logger.warning(error_msg)

    def _format_path_for_display(self, path: str) -> str:
        """Format a path for user-friendly display."""
        # Convert technical paths to more readable names
        if path.startswith('inputs.'):
            return f"Input: {path[7:].replace('_', ' ').title()}"
        elif path.startswith('outputs.'):
            return f"Output: {path[8:].replace('_', ' ').title()}"
        elif path.startswith('variables.'):
            return f"Variable: {path[10:].replace('_', ' ').title()}"
        else:
            return path.replace('_', ' ').title()

    def _format_value_for_display(self, value: Any, path: str) -> str:
        """Format a value for user-friendly display."""
        if value is None:
            return "None"

        # Handle RollResult objects specially
        from ..models.roll_result import RollResult
        if isinstance(value, RollResult):
            return self._format_roll_result_for_display(value)

        # Handle dictionaries (like character objects)
        if isinstance(value, dict):
            return self._format_dict_for_display(value, path)

        # Handle lists
        if isinstance(value, list):
            if not value:
                return "(empty list)"
            elif len(value) == 1:
                item_desc = self._format_value_for_display(value[0], f'{path}[0]')
                return f"[1 item: {item_desc}]"
            else:
                # Show summary for multiple items
                sample_items = []
                for _i, item in enumerate(value[:2]):
                    if isinstance(item, dict):
                        # Try to find an identifying field in a system-agnostic way
                        item_name = self._get_display_identifier(item)
                        if item_name:
                            sample_items.append(item_name)
                        else:
                            sample_items.append(f"dict({len(item)} keys)")
                    else:
                        sample_items.append(str(item))

                sample_str = ", ".join(sample_items)
                if len(value) > 2:
                    return f"[{len(value)} items: {sample_str}, ...]"
                else:
                    return f"[{len(value)} items: {sample_str}]"

        # Handle strings
        if isinstance(value, str):
            return f'"{value}"' if len(value) < 50 else f'"{value[:47]}..."'

        # Handle numbers and booleans
        if isinstance(value, int | float | bool):
            return str(value)

        # Handle objects with a display-friendly representation
        if hasattr(value, '__dict__'):
            return self._format_object_for_display(value)

        # Fallback to string representation
        return str(value)

    def _format_dict_for_display(self, data: dict, path: str) -> str:
        """Format a dictionary for user-friendly display using tables."""
        if not data:
            return "  (empty)"

        # Use table format for dictionaries
        return self._create_table_for_dict(data, path)

    def _print_table_for_dict(self, data: dict, path: str, console) -> None:
        """Print a table representation of a dictionary directly to console."""
        from rich.table import Table

        # Create table with styling and left-justified title for accessibility
        table = Table(show_header=True, header_style="bold blue", show_lines=True, title_justify="left")
        table.add_column("Property", style="cyan", width=18, no_wrap=True)
        table.add_column("Value", style="white", width=60)

        # Add rows for each key-value pair
        for key, value in data.items():
            formatted_value = self._format_value_for_table(value, f"{path}.{key}")
            table.add_row(str(key), formatted_value)

        # Print table directly to console
        console.print(table)

    def _create_table_for_dict(self, data: dict, path: str) -> str:
        """Create a table representation of a dictionary."""
        from io import StringIO

        from rich.console import Console
        from rich.table import Table

        # Create a console that writes to a string with color support
        console = Console(file=StringIO(), width=100, legacy_windows=False, force_terminal=True)

        # Create table with styling and left-justified title for accessibility
        table = Table(show_header=True, header_style="bold blue", show_lines=True, title_justify="left")
        table.add_column("Property", style="cyan", width=18, no_wrap=True)
        table.add_column("Value", style="white", width=60)

        # Add rows for each key-value pair
        for key, value in data.items():
            formatted_value = self._format_value_for_table(value, f"{path}.{key}")
            table.add_row(str(key), formatted_value)

        # Render table to string
        console.print(table)
        output = console.file.getvalue()
        console.file.close()

        return output.strip()

    def _format_value_for_table(self, value: Any, path: str) -> str:
        """Format a value specifically for table display with Rich markup."""
        if value is None:
            return "[dim]None[/dim]"

        # Handle nested dictionaries
        if isinstance(value, dict):
            if not value:
                return "[dim](empty dict)[/dim]"
            elif len(value) <= 3:
                # Small dict - show content details with styling
                pairs = []
                for k, v in value.items():
                    if isinstance(v, int | float):
                        pairs.append(f"[cyan]{k}[/cyan]: [magenta]{v}[/magenta]")
                    elif isinstance(v, str) and len(v) < 20:
                        pairs.append(f"[cyan]{k}[/cyan]: [green]'{v}'[/green]")
                    else:
                        pairs.append(f"[cyan]{k}[/cyan]: [yellow]{type(v).__name__}[/yellow]")
                return "{" + ", ".join(pairs) + "}"
            else:
                return f"[yellow]Dict with [bold]{len(value)}[/bold] properties[/yellow]"

        # Handle lists
        if isinstance(value, list):
            if not value:
                return "[dim](empty list)[/dim]"
            elif len(value) == 1:
                if isinstance(value[0], dict):
                    item_name = self._get_display_identifier(value[0]) or 'item'
                    return f"[[green]{item_name}[/green]]"
                else:
                    return f"[[yellow]{value[0]}[/yellow]]"
            else:
                # Show summary for multiple items
                item_descriptions = []
                for item in value[:3]:
                    if isinstance(item, dict):
                        name = self._get_display_identifier(item) or 'item'
                        item_descriptions.append(f"[green]{name}[/green]")
                    else:
                        item_descriptions.append(f"[yellow]{str(item)}[/yellow]")

                result = ", ".join(item_descriptions)
                if len(value) > 3:
                    result += f", [dim]... ([bold]{len(value)}[/bold] total)[/dim]"
                return f"[{result}]"

        # Handle strings
        if isinstance(value, str):
            if len(value) == 0:
                return "[dim](empty string)[/dim]"
            elif len(value) < 40:
                return f'[green]"{value}"[/green]'
            else:
                return f'[green]"{value[:37]}..."[/green]'

        # Handle numbers and booleans
        if isinstance(value, bool):
            return f"[{'green' if value else 'red'}]{value}[/{'green' if value else 'red'}]"
        elif isinstance(value, int | float):
            return f"[magenta]{value}[/magenta]"

        # Handle objects with a display-friendly representation
        if hasattr(value, '__dict__'):
            return self._format_object_for_table(value)

        # Fallback to string representation
        str_value = str(value)
        if len(str_value) > 50:
            str_value = str_value[:47] + "..."
        return f"[white]{str_value}[/white]"

    def _format_object_for_table(self, obj: Any) -> str:
        """Format an object for table display with Rich styling."""
        class_name = obj.__class__.__name__

        # Try to find meaningful attributes to display in a system-agnostic way
        attrs = []
        identifying_attrs = self._get_identifying_attributes(obj)
        for attr_name, attr_value in identifying_attrs.items():
            attrs.append(f"[cyan]{attr_name}[/cyan]: [yellow]{attr_value}[/yellow]")

        if attrs:
            return f"[bold blue]{class_name}[/bold blue]({', '.join(attrs)})"
        else:
            return f"[bold blue]{class_name}[/bold blue]([dim]...[/dim])"

    def _format_object_for_display(self, obj: Any) -> str:
        """Format an object for display."""
        class_name = obj.__class__.__name__

        # Try to find meaningful attributes to display in a system-agnostic way
        attrs = []
        identifying_attrs = self._get_identifying_attributes_from_object(obj)
        for attr_name, attr_value in identifying_attrs.items():
            attrs.append(f"{attr_name}: {attr_value}")

        if attrs:
            return f"{class_name}({', '.join(attrs)})"
        else:
            return f"{class_name}(...)"

    def _get_display_identifier(self, obj: dict) -> str | None:
        """Get a display identifier from a dictionary object using GRIMOIRE field conventions."""
        # Try GRIMOIRE standard identifying fields in order of preference
        # This follows the GRIMOIRE specification for standard field names
        grimoire_identifier_fields = ['name', 'id', 'title', 'label', 'display_name']

        for field in grimoire_identifier_fields:
            if field in obj and obj[field]:
                return str(obj[field])

        return None

    def _get_identifying_attributes(self, obj: Any) -> dict[str, Any]:
        """Get identifying attributes from an object using GRIMOIRE field conventions."""
        attrs = {}
        # Try GRIMOIRE standard identifying attributes in order of preference
        grimoire_identifier_attrs = ['name', 'id', 'title', 'label', 'value', 'total']

        for attr_name in grimoire_identifier_attrs:
            if hasattr(obj, attr_name):
                attr_value = getattr(obj, attr_name)
                if attr_value is not None:
                    attrs[attr_name] = attr_value
                    # Limit to first 3 meaningful attributes to keep display manageable
                    if len(attrs) >= 3:
                        break

        return attrs

    def _get_identifying_attributes_from_object(self, obj: Any) -> dict[str, Any]:
        """Get identifying attributes from an object using GRIMOIRE field conventions."""
        attrs = {}
        # Try GRIMOIRE standard identifying attributes in order of preference
        grimoire_identifier_attrs = ['name', 'id', 'title', 'label', 'value', 'total']

        for attr_name in grimoire_identifier_attrs:
            if hasattr(obj, attr_name):
                attr_value = getattr(obj, attr_name)
                if attr_value is not None:
                    attrs[attr_name] = attr_value
                    # Limit to first 3 meaningful attributes to keep display manageable
                    if len(attrs) >= 3:
                        break

        return attrs

    def _format_roll_result_for_display(self, roll_result) -> str:
        """Format a RollResult object for display as a simple string."""
        return f"🎲 {roll_result.total} ({roll_result.expression})"

    def _print_roll_result_table(self, roll_result, console) -> None:
        """Print a RollResult as a table directly to console."""
        from rich.table import Table

        # Create table with styling and left-justified title for accessibility
        table = Table(show_header=True, header_style="bold blue", show_lines=True,
                     title="🎲 Dice Roll Result", title_justify="left")
        table.add_column("Property", style="cyan", width=12, no_wrap=True)
        table.add_column("Value", style="white", width=50)

        # Add rows for roll result properties
        table.add_row("Total", f"[bold magenta]{roll_result.total}[/bold magenta]")
        table.add_row("Expression", f"[yellow]{roll_result.expression}[/yellow]")
        table.add_row("Detail", f"[green]{roll_result.detail}[/green]")

        # Print table directly to console
        console.print(table)


class LogEventActionStrategy(ActionStrategy):
    """Strategy for handling log_event actions."""

    def get_action_type(self) -> str:
        return "log_event"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a log_event action."""
        event_type = action_data.get("type", "unknown")
        event_data = action_data.get("data", {})

        # Resolve templates in event_data if it's a string
        if isinstance(event_data, str):
            resolved_event_data = context.resolve_template(event_data)
        else:
            resolved_event_data = event_data

        logger.debug(f"Event: {event_type} - {resolved_event_data}")


class LogMessageActionStrategy(ActionStrategy):
    """Strategy for handling log_message actions."""

    def get_action_type(self) -> str:
        return "log_message"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a log_message action."""
        message = action_data.get("message", "")

        # Resolve templates in the message
        resolved_message = context.resolve_template(str(message))

        # Add the message to the execution context for UI display
        context.add_action_message(f"📝 {resolved_message}")

        # Also log it for debugging
        logger.debug(f"Action log_message: {resolved_message}")


class SwapValuesActionStrategy(ActionStrategy):
    """Strategy for handling swap_values actions."""

    def get_action_type(self) -> str:
        return "swap_values"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a swap_values action."""
        # Swap values between two paths
        path1 = action_data.get("path1", "")
        path2 = action_data.get("path2", "")

        # Resolve templates in the paths
        path1 = context.resolve_template(path1)
        path2 = context.resolve_template(path2)

        try:
            # Get values from both paths
            value1 = context.resolve_path_value(path1)
            value2 = context.resolve_path_value(path2)

            # Swap them
            self._set_value_at_path(context, path1, value2)
            self._set_value_at_path(context, path2, value1)

            logger.debug(f"Swapped values: {path1} <-> {path2}")

        except Exception as e:
            logger.error(f"Error swapping values between {path1} and {path2}: {e}")

    def _set_value_at_path(
        self, context: "ExecutionContext", path: str, value: Any
    ) -> None:
        """Set a value at a specific path in the context."""
        if path.startswith("outputs."):
            context.set_output(path[8:], value)
        elif path.startswith("variables."):
            context.set_variable(path[10:], value)
        else:
            # Default to outputs
            context.set_output(path, value)


class FlowCallActionStrategy(ActionStrategy):
    """Strategy for handling flow_call actions."""

    def __init__(self, table_executor_factory: "TableExecutorFactory" = None):
        """Initialize with optional table executor factory for dependency injection."""
        self.table_executor_factory = table_executor_factory

    def get_action_type(self) -> str:
        return "flow_call"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a flow_call action."""
        # Handle sub-flow calls
        flow_id = action_data["flow"]
        raw_inputs = action_data.get("inputs", {})
        logger.debug(f"Engine action flow_call: {flow_id} (raw inputs: {raw_inputs})")

        # Resolve input templates using the current context
        resolved_inputs = {}
        for input_key, input_value in raw_inputs.items():
            if isinstance(input_value, str):
                # Resolve any templates in the input value
                try:
                    if input_value.startswith("{{") and input_value.endswith("}}"):
                        # This is a template, resolve it while preserving object types
                        resolved_value = context.resolve_template(input_value)
                        logger.debug(
                            f"Resolved template {input_key}: {input_value} -> {type(resolved_value).__name__}"
                        )
                    elif "outputs." in input_value:
                        # This is a path reference, resolve it
                        resolved_value = context.resolve_path_value(input_value)
                        logger.debug(
                            f"Resolved path {input_key}: {input_value} -> {type(resolved_value).__name__}"
                        )
                    else:
                        # Plain string, use as-is
                        resolved_value = input_value
                    resolved_inputs[input_key] = resolved_value
                except Exception as e:
                    logger.error(
                        f"Failed to resolve input {input_key}: {input_value} - {e}"
                    )
                    resolved_inputs[input_key] = input_value
            else:
                # Non-string values, use as-is
                resolved_inputs[input_key] = input_value

        logger.debug(f"Engine action flow_call resolved inputs: {resolved_inputs}")

        # Create table executor using factory or fallback to direct creation
        if self.table_executor_factory:
            table_executor = self.table_executor_factory.create_table_executor()
        else:
            # Fallback to direct import and creation for backward compatibility
            from ..executors.table_executor import TableExecutor

            table_executor = TableExecutor()

        # Use the table executor's sub-flow execution logic
        # since it already handles the template resolution and typing correctly
        try:
            if system:
                table_executor._execute_sub_flow(
                    flow_id, resolved_inputs, context, system, raw_inputs
                )
                logger.debug(f"Successfully executed sub-flow: {flow_id}")
            else:
                logger.error(f"No system available for sub-flow execution: {flow_id}")
        except Exception as e:
            logger.error(f"Error executing sub-flow {flow_id}: {e}")


class GetValueActionStrategy(ActionStrategy):
    """Strategy for handling get_value actions (typically used in templates)."""

    def get_action_type(self) -> str:
        return "get_value"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a get_value action (no-op as it's used in templates)."""
        # This is typically used in templates, not as a standalone action
        pass


class ValidateValueActionStrategy(ActionStrategy):
    """Strategy for handling validate_value actions."""

    def get_action_type(self) -> str:
        return "validate_value"

    def execute(
        self,
        action_data: dict[str, Any],
        context: "ExecutionContext",
        system: "System | None" = None,
    ) -> None:
        """Execute a validate_value action."""
        # TODO: Implement validation
        logger.debug(
            f"Validate value action called - not yet implemented: {action_data}"
        )


class ActionStrategyRegistry:
    """Registry for managing action strategies."""

    def __init__(self, table_executor_factory: "TableExecutorFactory" = None):
        self._strategies: dict[str, ActionStrategy] = {}
        self.table_executor_factory = table_executor_factory
        self._register_default_strategies()

    def _register_default_strategies(self) -> None:
        """Register the default action strategies."""
        default_strategies = [
            SetValueActionStrategy(),
            AppendItemActionStrategy(),
            DisplayValueActionStrategy(),
            LogEventActionStrategy(),
            LogMessageActionStrategy(),
            SwapValuesActionStrategy(),
            FlowCallActionStrategy(self.table_executor_factory),
            GetValueActionStrategy(),
            ValidateValueActionStrategy(),
        ]

        for strategy in default_strategies:
            self.register_strategy(strategy)

    def register_strategy(self, strategy: ActionStrategy) -> None:
        """Register an action strategy."""
        action_type = strategy.get_action_type()
        self._strategies[action_type] = strategy
        logger.debug(f"Registered action strategy for: {action_type}")

    def get_strategy(self, action_type: str) -> ActionStrategy | None:
        """Get a strategy for the given action type."""
        return self._strategies.get(action_type)

    def get_supported_action_types(self) -> list[str]:
        """Get all supported action types."""
        return list(self._strategies.keys())
