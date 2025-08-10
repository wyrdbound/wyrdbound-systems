"""Observable pattern implementation for reactive model attributes."""

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .context_data import ExecutionContext
    from .model import ModelDefinition

logger = logging.getLogger(__name__)


@dataclass
class DependencyInfo:
    """Information about a derived field's dependencies."""

    derived: str  # The Jinja2 template expression
    dependencies: set[str] = field(default_factory=set)


class ObservableValue:
    """A value that can be observed for changes."""

    def __init__(self, field_name: str, initial_value: Any = None):
        self.field_name = field_name
        self._value = initial_value
        self._observers: list[Callable[[str, Any, Any], None]] = []

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, new_value: Any) -> None:
        old_value = self._value
        self._value = new_value
        logger.debug(
            f"ObservableValue.value setter: {self.field_name} changed from {old_value} to {new_value}, observers: {len(self._observers)}"
        )
        if old_value != new_value:
            for observer in self._observers:
                logger.debug(f"Calling observer for {self.field_name}: {observer}")
                observer(self.field_name, old_value, new_value)

    def add_observer(self, observer: Callable[[str, Any, Any], None]) -> None:
        """Add an observer that will be called when the value changes."""
        self._observers.append(observer)


class DerivedFieldManager:
    """Manages derived fields and their dependencies using the Observer pattern."""

    def __init__(
        self,
        execution_context: "ExecutionContext",
        template_resolver: Callable[[str], Any],
    ):
        self.execution_context = execution_context
        self.template_resolver = template_resolver
        self.current_instance_id = (
            None  # Track the current model instance being processed
        )

        # Track derived fields and their dependencies
        self.fields: dict[
            str, dict[str, Any]
        ] = {}  # field_name -> {derived: template, dependencies: set}
        self.derived_fields: dict[str, DependencyInfo] = {}
        self.dependency_graph: dict[
            str, set[str]
        ] = {}  # field -> set of fields that depend on it
        self.observable_values: dict[str, ObservableValue] = {}
        self._computing: set[str] = set()  # Prevent circular dependencies

    def _extract_dependencies(self, expression: str) -> set[str]:
        """Extract variable dependencies from a Jinja2 expression."""
        dependencies = set()

        # First handle $. references by replacing with current instance ID
        if self.current_instance_id and "$." in expression:
            expression = expression.replace("$.", f"${self.current_instance_id}.")

        # Find all variable references like {{ variable }} or {{ object.attribute }}
        pattern = r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}"
        matches = re.findall(pattern, expression)
        dependencies.update(matches)

        # Find variables in expressions like {{ variable + 1 }} or {{ object.method() }}
        # More complex pattern to catch variables in expressions
        pattern = r"\{\{[^}]*?\b([a-zA-Z_][a-zA-Z0-9_.]*)\b[^}]*?\}\}"
        matches = re.findall(pattern, expression)
        dependencies.update(matches)

        # Find $ syntax variables like $abilities.str.bonus
        pattern = r"\$([a-zA-Z_][a-zA-Z0-9_.]*)"
        matches = re.findall(pattern, expression)
        dependencies.update(matches)

        return dependencies

    def register_derived_field(self, field_name: str, expression: str) -> None:
        """Register a derived field with its template expression."""
        logger.debug(f"Registering derived field: {field_name} = '{expression}'")

        # Build qualified field name if we have an instance ID
        qualified_field_name = (
            f"{self.current_instance_id}.{field_name}"
            if self.current_instance_id
            else field_name
        )

        # Extract dependencies from the expression
        dependencies = self._extract_dependencies(expression)

        # Convert relative dependencies to qualified names
        qualified_dependencies = set()
        for dep in dependencies:
            if dep.startswith("$."):
                # Convert $. to the current instance scope
                instance_dep = dep[2:]  # Remove $.
                qualified_dep = (
                    f"{self.current_instance_id}.{instance_dep}"
                    if self.current_instance_id
                    else instance_dep
                )
                qualified_dependencies.add(qualified_dep)
            else:
                qualified_dependencies.add(dep)

        # Store field info
        self.fields[qualified_field_name] = {
            "derived": expression,
            "dependencies": qualified_dependencies,
        }

        # Update dependency graph (reverse mapping: dependency -> fields that depend on it)
        for dep in qualified_dependencies:
            if dep not in self.dependency_graph:
                self.dependency_graph[dep] = set()
            self.dependency_graph[dep].add(qualified_field_name)

        logger.debug(
            f"Derived field '{qualified_field_name}' depends on: {qualified_dependencies}"
        )

    def set_field_value(self, field_name: str, value: Any) -> None:
        """Set a value and trigger recomputation of dependent fields."""
        logger.debug(f"Observable: Setting field {field_name} = {value}")

        # First, set the value directly in the execution context outputs to avoid recursion
        # We use _set_nested_value directly instead of set_output to prevent circular calls
        self.execution_context._set_nested_value(
            self.execution_context.outputs, field_name, value
        )

        # Then create/update observable which will trigger recomputation
        if field_name not in self.observable_values:
            logger.debug(f"Observable: Creating new ObservableValue for {field_name}")
            # Create with None first, then set the value to trigger observers
            self.observable_values[field_name] = ObservableValue(field_name, None)
            # Add observer to trigger recomputation
            self.observable_values[field_name].add_observer(self._on_value_changed)
            logger.debug(
                f"Observable: Added observer to {field_name}, observers: {len(self.observable_values[field_name]._observers)}"
            )
            # Now set the actual value (this will trigger observers)
            self.observable_values[field_name].value = value
        else:
            # Update existing observable (this will trigger observers)
            logger.debug(
                f"Observable: Updating existing ObservableValue for {field_name}"
            )
            self.observable_values[field_name].value = value

    def _on_value_changed(self, field: str, old_value: Any, new_value: Any) -> None:
        """Called when a value changes."""
        logger.debug(f"Observable: {field} changed from {old_value} to {new_value}")
        self._recompute_dependent_fields(field)

    def _recompute_dependent_fields(self, changed_field: str) -> None:
        """Recompute all fields that depend on the changed field."""
        logger.debug(f"Recomputing fields that depend on: {changed_field}")

        # Check if any derived fields depend on this field
        if changed_field in self.dependency_graph:
            dependent_fields = self.dependency_graph[changed_field]
            logger.debug(
                f"Found {len(dependent_fields)} dependent fields: {dependent_fields}"
            )

            for dependent_field in dependent_fields:
                if (
                    dependent_field not in self._computing
                ):  # Prevent circular dependencies
                    logger.debug(f"Recomputing dependent field: {dependent_field}")
                    self._recompute_field(dependent_field)
        else:
            logger.debug(f"No dependent fields found for: {changed_field}")
        logger.debug(f"Field '{changed_field}' changed, checking dependencies...")

        if changed_field not in self.dependency_graph:
            logger.debug(f"No dependent fields found for '{changed_field}'")
            return

        # Get all dependent fields
        dependent_fields = self.dependency_graph[changed_field].copy()
        logger.debug(
            f"Found dependent fields for '{changed_field}': {dependent_fields}"
        )

        # Sort by dependency order to handle chains (A->B->C)
        ordered_fields = self._topological_sort(dependent_fields)
        logger.debug(f"Ordered dependent fields: {ordered_fields}")

        for field_name in ordered_fields:
            if field_name not in self._computing:  # Prevent circular dependencies
                logger.debug(f"Recomputing dependent field: {field_name}")
                self._recompute_field(field_name)

    def _recompute_field(self, field: str) -> None:
        """Recompute a single derived field."""
        logger.debug(f"_recompute_field called for: {field}")

        # The field is already qualified (e.g., "knave.abilities.strength.defense")
        # Look for it directly in the fields registry
        logger.debug(f"_recompute_field: looking for qualified field = {field}")
        logger.debug(f"_recompute_field: registered fields = {list(self.fields.keys())}")

        if field not in self.fields:
            logger.debug(f"Qualified field {field} not registered for recomputation")
            return

        self._computing.add(field)
        try:
            template_expr = self.fields[field]["derived"]
            # Convert $variable syntax to {{ variable }} syntax for Jinja2
            jinja_expr = self._convert_to_jinja_syntax(template_expr)
            logger.debug(f"Computing field {field}: '{template_expr}' -> '{jinja_expr}'")

            result = self.template_resolver(jinja_expr)
            logger.debug(f"Field {field} computed to: {result}")

            # Store the result directly in outputs to avoid circular calls to set_output
            self.execution_context._set_nested_value(
                self.execution_context.outputs, field, result
            )

            # Create/update observable for this computed field
            if field not in self.observable_values:
                logger.debug(
                    f"Creating observable for computed field {field} = {result}"
                )
                self.observable_values[field] = ObservableValue(field, None)
                self.observable_values[field].add_observer(self._on_value_changed)
                # Set the value, which will trigger observers naturally
                self.observable_values[field].value = result
            else:
                logger.debug(
                    f"Updating observable for computed field {field} = {result}"
                )
                old_value = self.observable_values[field].value
                self.observable_values[field].value = result
                # If the value didn't change but this is a computed field, still trigger dependencies
                # in case this is the first time dependent fields need to be computed
                if old_value == result:
                    logger.debug(
                        f"Computed field {field} value unchanged ({result}), but triggering dependent field recomputation"
                    )
                    self._recompute_dependent_fields(field)
        except Exception as e:
            logger.error(f"Error computing field {field}: {e}")
        finally:
            self._computing.discard(field)

    def _convert_to_jinja_syntax(self, expression: str) -> str:
        """Convert $variable syntax to {{ variable }} Jinja2 syntax."""
        import re

        # For mathematical expressions like "10 + $.abilities.strength.bonus",
        # we want to create "{{ 10 + knave.abilities.strength.bonus }}" so it evaluates the math

        # First handle $. references (current model instance)
        if self.current_instance_id and "$." in expression:
            # Replace $. with the current instance ID
            expression = expression.replace("$.", f"${self.current_instance_id}.")

        # Check if this is a simple variable reference or a mathematical expression
        if expression.startswith("$") and not any(
            op in expression for op in ["+", "-", "*", "/", "(", ")"]
        ):
            # Simple variable reference: $variable -> {{ variable }}
            return re.sub(r"\$([a-zA-Z_][a-zA-Z0-9_.]*)", r"{{ \1 }}", expression)
        else:
            # Mathematical expression: wrap the whole thing after converting variables
            # First convert $variable to variable
            converted = re.sub(r"\$([a-zA-Z_][a-zA-Z0-9_.]*)", r"\1", expression)
            # Then wrap in {{ }} for evaluation
            return f"{{{{ {converted} }}}}"

    def _topological_sort(self, fields: set[str]) -> list[str]:
        """Sort fields in dependency order."""
        result = []
        visited = set()
        temp_visited = set()

        def visit(field: str):
            if field in temp_visited:
                # Circular dependency - just add to result
                return
            if field in visited:
                return

            temp_visited.add(field)

            # Visit dependencies first (fields this field depends on)
            field_info = self.fields.get(field, {})
            dependencies = field_info.get("dependencies", set())

            for dep in dependencies:
                if dep in fields:  # Only consider fields in our current set
                    visit(dep)

            temp_visited.remove(field)
            visited.add(field)
            result.append(field)

        for field_name in fields:
            if field_name not in visited:
                visit(field_name)

        return result

    def register_model_attributes(self, model_def: "ModelDefinition") -> None:
        """Register all attributes from a model, including derived fields."""
        logger.debug(f"Registering model attributes for: {model_def.name}")

        # Register all attributes recursively
        self._register_attributes_recursive(model_def.attributes, "")

        logger.debug(
            f"Dependency graph after registration: {dict(self.dependency_graph)}"
        )

    def initialize_from_model(
        self, model_def: "ModelDefinition", instance_id: str = None
    ) -> None:
        """Initialize observable system from a model definition."""
        logger.debug(
            f"Initializing observable system for model {getattr(model_def, 'id', 'unknown')} with instance_id: {instance_id}"
        )
        self.current_instance_id = instance_id
        self.register_model_attributes(model_def)

    def compute_all_derived_fields(self) -> None:
        """Compute all registered derived fields based on current context values."""
        logger.debug(f"Computing all derived fields: {list(self.fields.keys())}")

        # Get all derived fields and sort them by dependency order
        all_derived_fields = set(self.fields.keys())
        if not all_derived_fields:
            logger.debug("No derived fields to compute")
            return

        ordered_fields = self._topological_sort(all_derived_fields)
        logger.debug(f"Computing derived fields in order: {ordered_fields}")

        for field_name in ordered_fields:
            if field_name not in self._computing:  # Prevent circular dependencies
                logger.debug(f"Computing derived field: {field_name}")
                self._recompute_field(field_name)

    def get_computed_values_for_instance(self, instance_id: str) -> dict[str, Any]:
        """Get all computed values (including derived fields) for a specific instance."""
        computed_values = {}

        # Get the prefix for this instance
        prefix = f"{instance_id}."

        logger.debug(
            f"get_computed_values_for_instance({instance_id}): observable_values keys = {list(self.observable_values.keys())}"
        )

        for field_name, observable_value in self.observable_values.items():
            if field_name.startswith(prefix):
                # Remove the instance prefix to get the relative field path
                relative_path = field_name[len(prefix) :]
                value_type = type(observable_value.value).__name__
                value_preview = (
                    str(observable_value.value)[:100] + "..."
                    if len(str(observable_value.value)) > 100
                    else str(observable_value.value)
                )
                logger.debug(
                    f"get_computed_values_for_instance({instance_id}): {field_name} -> {relative_path} = {value_type}: {value_preview}"
                )

                # Set the value in the nested structure
                # If the value is a string that looks like serialized structured data, parse it
                if (
                    isinstance(observable_value.value, str)
                    and len(observable_value.value) > 10
                ):
                    logger.debug(
                        f"Checking if {relative_path} value is serialized data: {observable_value.value[:50]}..."
                    )
                final_value = self._try_parse_structured_data(observable_value.value)
                if final_value is not None:
                    logger.debug(
                        f"Parsed serialized data for {relative_path}: {type(final_value).__name__}"
                    )
                    self._set_nested_value_in_dict(
                        computed_values, relative_path, final_value
                    )
                else:
                    self._set_nested_value_in_dict(
                        computed_values, relative_path, observable_value.value
                    )

        logger.debug(
            f"get_computed_values_for_instance({instance_id}): final computed_values = {computed_values}"
        )
        return computed_values

    def _set_nested_value_in_dict(
        self, target_dict: dict[str, Any], path: str, value: Any
    ) -> None:
        """Set a nested value in a dictionary using dot notation."""
        parts = path.split(".")
        current = target_dict

        # Navigate to the parent of the target key
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the final value - use generic type-based priority for conflicts
        final_key = parts[-1]
        if final_key in current:
            existing_value = current[final_key]
            # Generic rule: preserve structured data (lists, dicts) over serialized strings
            if isinstance(existing_value, list | dict) and isinstance(value, str):
                logger.debug(
                    f"_set_nested_value_in_dict: Preserving existing structured data for {path}, ignoring string value"
                )
                return
            # Replace strings with structured data when available
            elif isinstance(existing_value, str) and isinstance(value, list | dict):
                logger.debug(
                    f"_set_nested_value_in_dict: Replacing string with structured data for {path}"
                )

        current[final_key] = value

    def _try_parse_structured_data(self, value: Any) -> Any:
        """Try to parse a value as structured data. Returns None if not valid or not structured."""
        if not isinstance(value, str):
            return None

        # Only try parsing if it looks like structured data
        if not (
            value.strip().startswith(("[", "{")) and value.strip().endswith(("]", "}"))
        ):
            return None

        # Try JSON first (double quotes)
        try:
            import json

            parsed = json.loads(value)
            # Only return if it's actually structured data (list or dict)
            if isinstance(parsed, list | dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Try Python literal evaluation (single quotes)
        try:
            import ast

            parsed = ast.literal_eval(value)
            # Only return if it's actually structured data (list or dict)
            if isinstance(parsed, list | dict):
                return parsed
        except (ValueError, SyntaxError):
            pass

        return None

    def _register_attributes_recursive(
        self, attributes: dict[str, Any], path_prefix: str
    ) -> None:
        """Recursively register attributes and their derived fields."""
        logger.debug(
            f"Registering attributes at path '{path_prefix}': {list(attributes.keys())}"
        )

        for attr_name, attr_config in attributes.items():
            full_path = f"{path_prefix}.{attr_name}" if path_prefix else attr_name
            logger.debug(f"Processing attribute: {full_path} = {attr_config}")

            # Handle AttributeDefinition objects
            if hasattr(attr_config, "derived") and attr_config.derived:
                logger.debug(
                    f"Found derived field: {full_path} = {attr_config.derived}"
                )
                self.register_derived_field(full_path, attr_config.derived)
            # Handle nested attributes (dictionaries)
            elif isinstance(attr_config, dict):
                if "derived" in attr_config:
                    # This is a derived field in dict format
                    logger.debug(
                        f"Found derived field: {full_path} = {attr_config['derived']}"
                    )
                    self.register_derived_field(full_path, attr_config["derived"])
                elif "attributes" in attr_config:
                    # This is a nested object
                    logger.debug(f"Descending into nested object: {full_path}")
                    self._register_attributes_recursive(
                        attr_config["attributes"], full_path
                    )
                else:
                    # Check if any values are nested dictionaries or AttributeDefinitions
                    for key, value in attr_config.items():
                        sub_path = f"{full_path}.{key}"
                        if hasattr(value, "derived") and value.derived:
                            logger.debug(
                                f"Found nested derived field: {sub_path} = {value.derived}"
                            )
                            self.register_derived_field(sub_path, value.derived)
                        elif isinstance(value, dict):
                            if "derived" in value:
                                logger.debug(
                                    f"Found nested derived field: {sub_path} = {value['derived']}"
                                )
                                self.register_derived_field(sub_path, value["derived"])
                            elif "attributes" in value:
                                logger.debug(
                                    f"Descending into nested nested object: {sub_path}"
                                )
                                self._register_attributes_recursive(
                                    value["attributes"], sub_path
                                )
                            else:
                                # Regular nested attributes case
                                logger.debug(
                                    f"Checking nested dict: {sub_path} = {value}"
                                )
                                self._register_attributes_recursive(
                                    {key: value}, full_path
                                )
