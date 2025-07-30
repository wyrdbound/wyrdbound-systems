"""Observable pattern implementation for reactive model attributes."""

import re
from typing import Any, Callable, Dict, List, Set, Optional, TYPE_CHECKING
from dataclasses import dataclass, field
import logging

if TYPE_CHECKING:
    from .context_data import ExecutionContext
    from .model import ModelDefinition

logger = logging.getLogger(__name__)


@dataclass
class DependencyInfo:
    """Information about a derived field's dependencies."""
    derived: str  # The Jinja2 template expression
    dependencies: Set[str] = field(default_factory=set)


class ObservableValue:
    """A value that can be observed for changes."""
    
    def __init__(self, field_name: str, initial_value: Any = None):
        self.field_name = field_name
        self._value = initial_value
        self._observers: List[Callable[[str, Any, Any], None]] = []
    
    @property
    def value(self) -> Any:
        return self._value
    
    @value.setter
    def value(self, new_value: Any) -> None:
        old_value = self._value
        self._value = new_value
        logger.debug(f"ObservableValue.value setter: {self.field_name} changed from {old_value} to {new_value}, observers: {len(self._observers)}")
        if old_value != new_value:
            for observer in self._observers:
                logger.debug(f"Calling observer for {self.field_name}: {observer}")
                observer(self.field_name, old_value, new_value)
    
    def add_observer(self, observer: Callable[[str, Any, Any], None]) -> None:
        """Add an observer that will be called when the value changes."""
        self._observers.append(observer)


class DerivedFieldManager:
    """Manages derived fields and their dependencies using the Observer pattern."""
    
    def __init__(self, execution_context: "ExecutionContext", template_resolver: Callable[[str], Any]):
        self.execution_context = execution_context
        self.template_resolver = template_resolver
        self.current_instance_id = None  # Track the current model instance being processed
        
        # Track derived fields and their dependencies
        self.fields: Dict[str, Dict[str, Any]] = {}  # field_name -> {derived: template, dependencies: set}
        self.derived_fields: Dict[str, DependencyInfo] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}  # field -> set of fields that depend on it
        self.observable_values: Dict[str, ObservableValue] = {}
        self._computing: Set[str] = set()  # Prevent circular dependencies
    
    def _extract_dependencies(self, expression: str) -> Set[str]:
        """Extract variable dependencies from a Jinja2 expression."""
        dependencies = set()
        
        # First handle $. references by replacing with current instance ID
        if self.current_instance_id and '$.' in expression:
            expression = expression.replace('$.', f'${self.current_instance_id}.')
        
        # Find all variable references like {{ variable }} or {{ object.attribute }}
        pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}'
        matches = re.findall(pattern, expression)
        dependencies.update(matches)
        
        # Find variables in expressions like {{ variable + 1 }} or {{ object.method() }}
        # More complex pattern to catch variables in expressions
        pattern = r'\{\{[^}]*?\b([a-zA-Z_][a-zA-Z0-9_.]*)\b[^}]*?\}\}'
        matches = re.findall(pattern, expression)
        dependencies.update(matches)
        
        # Find $ syntax variables like $abilities.str.bonus
        pattern = r'\$([a-zA-Z_][a-zA-Z0-9_.]*)'
        matches = re.findall(pattern, expression)
        dependencies.update(matches)
        
        return dependencies
    
    def register_derived_field(self, field_name: str, derived_expression: str) -> None:
        """Register a field that should be computed from other fields."""
        logger.debug(f"Registering derived field: {field_name} = {derived_expression}")
        
        # Extract dependencies from the Jinja2 template
        dependencies = self._extract_dependencies(derived_expression)
        logger.debug(f"Dependencies for {field_name}: {dependencies}")
        
        # Store field info
        self.fields[field_name] = {
            'derived': derived_expression,
            'dependencies': dependencies
        }
        
        # Update dependency graph
        for dep in dependencies:
            if dep not in self.dependency_graph:
                self.dependency_graph[dep] = set()
            self.dependency_graph[dep].add(field_name)
            logger.debug(f"Added dependency: {dep} → {field_name}")
    
    def set_field_value(self, field_name: str, value: Any) -> None:
        """Set a value and trigger recomputation of dependent fields."""
        logger.debug(f"Setting observable value: {field_name} = {value}")
        
        # First, set the value in the execution context so it's available for template resolution
        self.execution_context.set_output(field_name, value)
        
        # Then create/update observable which will trigger recomputation
        if field_name not in self.observable_values:
            logger.debug(f"Creating new ObservableValue for {field_name}")
            # Create with None first, then set the value to trigger observers
            self.observable_values[field_name] = ObservableValue(field_name, None)
            # Add observer to trigger recomputation
            self.observable_values[field_name].add_observer(self._on_value_changed)
            logger.debug(f"Added observer to {field_name}, observers: {len(self.observable_values[field_name]._observers)}")
            # Now set the actual value (this will trigger observers)
            self.observable_values[field_name].value = value
        else:
            # Update existing observable (this will trigger observers)
            logger.debug(f"Updating existing ObservableValue for {field_name}")
            self.observable_values[field_name].value = value
    
    def _on_value_changed(self, field: str, old_value: Any, new_value: Any) -> None:
        """Called when a value changes."""
        logger.debug(f"Observable: {field} changed from {old_value} to {new_value}")
        self._recompute_dependent_fields(field)
    
    def _recompute_dependent_fields(self, changed_field: str) -> None:
        """Recompute all fields that depend on the changed field."""
        logger.debug(f"Field '{changed_field}' changed, checking dependencies...")
        
        if changed_field not in self.dependency_graph:
            logger.debug(f"No dependent fields found for '{changed_field}'")
            return
        
        # Get all dependent fields
        dependent_fields = self.dependency_graph[changed_field].copy()
        logger.debug(f"Found dependent fields for '{changed_field}': {dependent_fields}")
        
        # Sort by dependency order to handle chains (A->B->C)
        ordered_fields = self._topological_sort(dependent_fields)
        logger.debug(f"Ordered dependent fields: {ordered_fields}")
        
        for field in ordered_fields:
            if field not in self._computing:  # Prevent circular dependencies
                logger.debug(f"Recomputing dependent field: {field}")
                self._recompute_field(field)
    
    def _recompute_field(self, field: str) -> None:
        """Recompute a specific field."""
        logger.debug(f"Recomputing field: {field}")
        
        if field not in self.fields:
            logger.debug(f"Field {field} not registered for recomputation")
            return
        
        self._computing.add(field)
        try:
            template_expr = self.fields[field]['derived']
            # Convert $variable syntax to {{ variable }} syntax for Jinja2
            jinja_expr = self._convert_to_jinja_syntax(template_expr)
            logger.debug(f"Converting template: '{template_expr}' -> '{jinja_expr}'")
            
            result = self.template_resolver(jinja_expr)
            logger.debug(f"Field {field} computed to: {result}")
            
            # Store the result in the correct namespace
            storage_path = field
            if self.current_instance_id and not field.startswith(f"{self.current_instance_id}."):
                storage_path = f"{self.current_instance_id}.{field}"
            
            self.execution_context.set_output(storage_path, result)
            
            # Trigger any dependent fields
            self._recompute_dependent_fields(field)
        except Exception as e:
            logger.debug(f"Error computing field {field}: {e}")
        finally:
            self._computing.discard(field)
    
    def _convert_to_jinja_syntax(self, expression: str) -> str:
        """Convert $variable syntax to {{ variable }} Jinja2 syntax."""
        import re
        
        # For mathematical expressions like "10 + $.abilities.strength.bonus", 
        # we want to create "{{ 10 + knave.abilities.strength.bonus }}" so it evaluates the math
        
        # First handle $. references (current model instance)
        if self.current_instance_id and '$.' in expression:
            # Replace $. with the current instance ID
            expression = expression.replace('$.', f'${self.current_instance_id}.')
        
        # Check if this is a simple variable reference or a mathematical expression
        if expression.startswith('$') and not any(op in expression for op in ['+', '-', '*', '/', '(', ')']):
            # Simple variable reference: $variable -> {{ variable }}
            return re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_.]*)', r'{{ \1 }}', expression)
        else:
            # Mathematical expression: wrap the whole thing after converting variables
            # First convert $variable to variable
            converted = re.sub(r'\$([a-zA-Z_][a-zA-Z0-9_.]*)', r'\1', expression)
            # Then wrap in {{ }} for evaluation
            return f"{{{{ {converted} }}}}"
    
    def _topological_sort(self, fields: Set[str]) -> List[str]:
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
            dependencies = field_info.get('dependencies', set())
            
            for dep in dependencies:
                if dep in fields:  # Only consider fields in our current set
                    visit(dep)
            
            temp_visited.remove(field)
            visited.add(field)
            result.append(field)
        
        for field in fields:
            if field not in visited:
                visit(field)
        
        return result
    
    def register_model_attributes(self, model_def: "ModelDefinition", instance_data: Dict[str, Any]) -> None:
        """Register all attributes from a model, including derived fields."""
        logger.debug(f"Registering model attributes for: {model_def.name}")
        
        # Register all attributes recursively
        self._register_attributes_recursive(model_def.attributes, "")
        
        logger.debug(f"Dependency graph after registration: {dict(self.dependency_graph)}")
    
    def initialize_from_model(self, model_def: "ModelDefinition", instance_id: str = None) -> None:
        """Initialize observable system from a model definition."""
        self.current_instance_id = instance_id
        self.register_model_attributes(model_def, {})
    
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
        
        for field in ordered_fields:
            if field not in self._computing:  # Prevent circular dependencies
                logger.debug(f"Computing derived field: {field}")
                self._recompute_field(field)
    
    def _register_attributes_recursive(self, attributes: Dict[str, Any], path_prefix: str) -> None:
        """Recursively register attributes and their derived fields."""
        logger.debug(f"Registering attributes at path '{path_prefix}': {list(attributes.keys())}")
        
        for attr_name, attr_config in attributes.items():
            full_path = f"{path_prefix}.{attr_name}" if path_prefix else attr_name
            logger.debug(f"Processing attribute: {full_path} = {attr_config}")
            
            # Handle AttributeDefinition objects
            if hasattr(attr_config, 'derived') and attr_config.derived:
                logger.debug(f"Found derived field: {full_path} = {attr_config.derived}")
                self.register_derived_field(full_path, attr_config.derived)
            # Handle nested attributes (dictionaries)
            elif isinstance(attr_config, dict):
                if 'derived' in attr_config:
                    # This is a derived field in dict format
                    logger.debug(f"Found derived field: {full_path} = {attr_config['derived']}")
                    self.register_derived_field(full_path, attr_config['derived'])
                elif 'attributes' in attr_config:
                    # This is a nested object
                    logger.debug(f"Descending into nested object: {full_path}")
                    self._register_attributes_recursive(attr_config['attributes'], full_path)
                else:
                    # Check if any values are nested dictionaries or AttributeDefinitions
                    for key, value in attr_config.items():
                        sub_path = f"{full_path}.{key}"
                        if hasattr(value, 'derived') and value.derived:
                            logger.debug(f"Found nested derived field: {sub_path} = {value.derived}")
                            self.register_derived_field(sub_path, value.derived)
                        elif isinstance(value, dict):
                            if 'derived' in value:
                                logger.debug(f"Found nested derived field: {sub_path} = {value['derived']}")
                                self.register_derived_field(sub_path, value['derived'])
                            elif 'attributes' in value:
                                logger.debug(f"Descending into nested nested object: {sub_path}")
                                self._register_attributes_recursive(value['attributes'], sub_path)
                            else:
                                # Regular nested attributes case
                                logger.debug(f"Checking nested dict: {sub_path} = {value}")
                                self._register_attributes_recursive({key: value}, full_path)
