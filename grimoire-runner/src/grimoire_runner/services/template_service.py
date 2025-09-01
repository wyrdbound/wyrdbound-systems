"""Unified template resolution service for GRIMOIRE runner."""

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from jinja2 import (
    BaseLoader,
    Environment,
    StrictUndefined,
    TemplateError,
    meta,
)

logger = logging.getLogger(__name__)


class ModelAwareDict:
    """A dictionary-like object that provides model-aware attribute access for templates.

    This class wraps model instance dictionaries and provides graceful handling
    of missing attributes by checking against model definitions.
    """

    def __init__(self, data: dict, model_definitions: dict, model_type: str = None):
        self._data = data
        self._models = model_definitions
        self._model_def = None

        # If we have an explicit model type, use it directly
        if model_type and model_type in self._models:
            self._model_def = self._models[model_type]
        else:
            # Fall back to inferring the model type from the data
            self._infer_model_type()

    def _infer_model_type(self):
        """Try to infer the model type from the data structure."""
        # For now, we'll use a simple heuristic based on field patterns
        # In the future, type information could be stored with the data

        # Try to match data structure against all available model definitions
        # This makes it system-agnostic by checking actual model definitions
        # rather than hardcoded assumptions about specific field names

        logger.debug(f"_infer_model_type called, _models has {len(self._models)} entries")

        best_match = None
        best_score = 0

        for _model_name, model_def in self._models.items():
            logger.debug(f"checking model {_model_name}: {model_def}")
            if model_def is None:
                logger.debug(f"skipping {_model_name} - model_def is None")
                continue

            # Calculate match score based on how many model fields are present in data
            score = 0
            total_fields = 0

            try:
                all_attrs = model_def.get_all_attributes() if hasattr(model_def, 'get_all_attributes') else {}
                total_fields = len(all_attrs)

                for attr_name in all_attrs:
                    if attr_name in self._data:
                        score += 1

                # Require at least 2 field matches and score > 50% to consider a match
                if score >= 2 and total_fields > 0 and (score / total_fields) > 0.3:
                    if score > best_score:
                        best_score = score
                        best_match = model_def

            except Exception:
                # Skip models that can't be processed
                continue

        self._model_def = best_match

    def __getattr__(self, name):
        """Handle attribute access with model-aware fallbacks."""
        # First check if the attribute exists in the data
        if name in self._data:
            return self._data[name]

        # If we have a model definition, check if this attribute is valid
        if self._model_def:
            all_attrs = self._model_def.get_all_attributes()
            if name in all_attrs:
                # Attribute exists in model but not in data - return None or default
                attr_def = all_attrs[name]
                return attr_def.default if attr_def.default is not None else None

        # If attribute doesn't exist in model or we don't have a model def,
        # return None instead of raising AttributeError
        return None

    def __getattribute__(self, name):
        """Handle attribute access - required for Jinja2 compatibility."""
        # Let Python handle special attributes normally
        if name.startswith('_') or name in ('get', 'keys', 'values', 'items', 'to_dict'):
            return object.__getattribute__(self, name)
        
        # For regular attributes, delegate to our custom __getattr__
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return self.__getattr__(name)

    def __getitem__(self, key):
        """Support dictionary-style access."""
        return self.__getattr__(key)

    def __setitem__(self, key, value):
        """Support dictionary-style assignment."""
        self._data[key] = value

    def __contains__(self, key):
        """Support 'in' operator."""
        return key in self._data

    def get(self, key, default=None):
        """Support dict.get() method."""
        result = self.__getattr__(key)
        return result if result is not None else default

    def keys(self):
        """Support dict.keys() method - returns only root-level keys in model definition order."""
        if self._model_def:
            # Get all attributes (including nested ones like 'hit_points.max')
            all_attrs = self._model_def.get_all_attributes()
            
            # Extract root-level keys from potentially dotted attribute names in definition order
            ordered_model_keys = []
            seen_keys = set()
            for key in all_attrs.keys():
                if '.' in key:
                    # For nested keys like 'hit_points.max', take the root part 'hit_points'
                    root_key = key.split('.')[0]
                    if root_key not in seen_keys:
                        ordered_model_keys.append(root_key)
                        seen_keys.add(root_key)
                else:
                    # For non-nested keys, use as-is
                    if key not in seen_keys:
                        ordered_model_keys.append(key)
                        seen_keys.add(key)
            
            # Add any data keys that aren't in the model (preserve them at the end)
            data_keys = [key for key in self._data.keys() if key not in seen_keys]
            
            return ordered_model_keys + data_keys
        return list(self._data.keys())

    def values(self):
        """Support dict.values() method."""
        return [self.__getattr__(key) for key in self.keys()]

    def items(self):
        """Support dict.items() method."""
        return [(key, self.__getattr__(key)) for key in self.keys()]

    def __str__(self):
        """String representation - return the underlying data as a string."""
        return str(self._data)

    def __repr__(self):
        """String representation for debugging."""
        return f"ModelAwareDict({self._data})"
        
    def _repr_html_(self):
        """Jupyter/HTML representation - return the underlying data."""
        return str(self._data)
        
    def __format__(self, format_spec):
        """Format method for f-strings and other formatting."""
        if format_spec:
            return format(str(self._data), format_spec)
        return str(self._data)

    def to_dict(self):
        """Convert to a plain dictionary."""
        return dict(self._data)

    def __getstate__(self):
        """Support for pickling - return the underlying data."""
        return self._data

    def __setstate__(self, state):
        """Support for unpickling - restore from underlying data."""
        self._data = state
        self._models = {}
        self._model_def = None

    def __iter__(self):
        """Support iteration over keys."""
        return iter(self._data)

    def __len__(self):
        """Support len() function."""
        return len(self._data)


class TemplateResolutionStrategy(ABC):
    """Abstract base class for template resolution strategies."""

    @abstractmethod
    def resolve_template(self, template_str: str, context_data: Any) -> Any:
        """Resolve a template string with the given context."""
        pass

    @abstractmethod
    def is_template(self, text: str) -> bool:
        """Check if a string contains template syntax."""
        pass


class RuntimeTemplateStrategy(TemplateResolutionStrategy):
    """Template resolution strategy for runtime execution context."""

    def __init__(self):
        self._jinja_env = Environment(undefined=StrictUndefined)
        self._setup_template_functions()

    def _setup_template_functions(self):
        """Setup custom functions available in runtime templates."""
        self._jinja_env.globals.update(
            {
                "get_value": self._template_get_value,
                "has_value": self._template_has_value,
            }
        )

        # Add standard Python functions
        self._jinja_env.globals.update(
            {
                "range": range,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
            }
        )

    def resolve_template(self, template_str: str, context_data: Any) -> Any:
        """Resolve a template using runtime execution context."""
        if not isinstance(template_str, str):
            return template_str

        # Skip if no template syntax
        if not self.is_template(template_str):
            return template_str

        try:
            template = self._jinja_env.from_string(template_str)

            # context_data should be a dict with all template variables
            if not isinstance(context_data, dict):
                raise TypeError(
                    f"Runtime template resolution requires dict context, got {type(context_data)}. "
                    f"Template: '{template_str}'"
                )

            # Enhance context with roll_result attribute access
            enhanced_context = self._enhance_context_for_objects(context_data)

            # Check for simple variable reference that should preserve object type
            template_str_stripped = template_str.strip()
            if (
                template_str_stripped.startswith("{{")
                and template_str_stripped.endswith("}}")
                and template_str_stripped.count("{{") == 1
                and template_str_stripped.count("}}") == 1
            ):
                # Extract variable name from {{ variable_name }}
                var_content = template_str_stripped[2:-2].strip()
                if "." not in var_content and " " not in var_content:
                    # Simple variable reference like {{ result }}
                    if var_content in enhanced_context:
                        original_obj = enhanced_context[var_content]
                        # If we have the original object, return it to preserve type
                        if (
                            isinstance(original_obj, dict)
                            and "_original" in original_obj
                        ):
                            logger.debug(
                                f"Preserving original object type for variable: {var_content}"
                            )
                            return original_obj["_original"]
                        # For other simple objects, return as-is
                        logger.debug(f"Returning simple variable as-is: {var_content}")
                        return original_obj

            # NO FALLBACKS - template resolution must be explicit about missing variables
            # This will cause Jinja2 to raise UndefinedError for missing variables
            
            # For complex expressions, try to evaluate them to preserve object types
            if self._is_complex_expression(template_str_stripped):
                try:
                    # Use Jinja2's native environment to get actual Python objects
                    from jinja2.nativetypes import NativeEnvironment
                    native_env = NativeEnvironment(
                        undefined=StrictUndefined,
                        trim_blocks=True,
                        lstrip_blocks=True,
                    )
                    native_template = native_env.from_string(template_str)
                    native_result = native_template.render(enhanced_context)
                    logger.debug(f"Native template result: {type(native_result)} = {native_result}")
                    return native_result
                except Exception as native_e:
                    logger.debug(f"Native template evaluation failed: {native_e}, falling back to regular rendering")
            
            result = template.render(enhanced_context)

            # Try to parse as structured data if it looks like it
            parsed_result = self._try_parse_structured_data(result)
            if parsed_result is not None:
                return parsed_result

            return result

        except Exception as e:
            # Create explicit error with full context for debugging
            try:
                if isinstance(context_data, dict):
                    context_info = f"Available context keys: {list(context_data.keys())}"
                else:
                    context_info = f"Context data type: {type(context_data).__name__}"
            except Exception:
                context_info = "Context data could not be analyzed"
            
            error_msg = (
                f"Runtime template resolution failed for '{template_str}': {e}. "
                f"{context_info}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _is_complex_expression(self, template_str: str) -> bool:
        """Determine if a template string contains complex expressions that should preserve object types."""
        # Strip {{ }} to get the inner expression
        if template_str.startswith('{{') and template_str.endswith('}}'):
            inner = template_str[2:-2].strip()
            # Check for operations that create new data structures or access object properties
            return any(op in inner for op in ['+', '-', '*', '/', '|', '[', ']', '(', ')', '.'])
        return False

    def _enhance_context_for_objects(self, context_data: dict) -> dict:
        """Enhance context to provide better object attribute access."""
        enhanced_context = context_data.copy()

        # Make RollResult objects more accessible in templates
        from ..models.roll_result import RollResult

        def make_object_accessible(obj):
            """Convert objects to be more accessible in Jinja2 templates."""
            # Skip System objects and other complex objects that shouldn't be processed
            from ..models.system import System
            from ..models.model import ModelDefinition
            
            if isinstance(obj, (System, ModelDefinition)):
                logger.debug(f"[TEMPLATE_SERVICE] Skipping {type(obj).__name__} object in template context")
                return obj  # Return as-is, don't process these objects
                
            if isinstance(obj, RollResult):
                # Convert RollResult to a dict-like object that preserves all attributes
                return {
                    "total": obj.total,
                    "detail": obj.detail,
                    "description": obj.description,  # Alias for detail
                    "expression": obj.expression,
                    "breakdown": obj.breakdown,
                    "individual_rolls": obj.individual_rolls,
                    # Also preserve the original object for methods
                    "_original": obj,
                }
            elif isinstance(obj, dict):
                # Don't re-process ModelAwareDict objects
                if isinstance(obj, ModelAwareDict):
                    logger.debug(f"[TEMPLATE_SERVICE] Skipping ModelAwareDict re-processing")
                    return obj
                    
                # Check if this looks like a model instance by checking for type information
                # Model instances typically come with metadata about their type
                try:
                    if self._is_model_instance_dict(obj, enhanced_context):
                        # Get models from system context (always a dictionary in template context)
                        system_dict = enhanced_context.get("system", {})
                        logger.debug(f"system_dict type: {type(system_dict)}, keys: {list(system_dict.keys()) if system_dict else 'None'}")
                        logger.debug(f"full system_dict content: {system_dict}")
                        models = system_dict.get("models", {})
                        logger.debug(f"models type: {type(models)}, keys: {list(models.keys()) if models else 'None'}")
                        
                        # Check what's actually in the models dict
                        if models:
                            for name, model_def in models.items():
                                logger.debug(f"model '{name}' type: {type(model_def)}, has get_all_attributes: {hasattr(model_def, 'get_all_attributes')}")
                                if hasattr(model_def, 'get_all_attributes'):
                                    try:
                                        attrs = model_def.get_all_attributes()
                                        logger.debug(f"model '{name}' attributes: {list(attrs.keys())}")
                                    except Exception as e:
                                        logger.debug(f"model '{name}' get_all_attributes() failed: {e}")
                        else:
                            logger.debug(f"models dict is empty!")
                        
                        # Ensure models has dictionary-like interface for ModelAwareDict
                        if not hasattr(models, 'keys') or not hasattr(models, 'get'):
                            logger.debug(f"models is not dict-like (type: {type(models)}), using empty dict")
                            models = {}
                        
                        # Check if we can determine model type from context structure
                        # Look for type hints in the context path or object metadata
                        model_type = self._determine_model_type_from_context(obj, enhanced_context)
                        return ModelAwareDict(obj, models, model_type)
                    else:
                        # Recursively process dict values
                        return {k: make_object_accessible(v) for k, v in obj.items()}
                except Exception as e:
                    logger.debug(f"[TEMPLATE_SERVICE] Harmless error in _is_model_instance_dict for obj type {type(obj)}: {e}")
                    logger.debug(f"[TEMPLATE_SERVICE] Obj content: {str(obj)[:200]}...")  # Truncated for brevity
                    # Fall back to simple dict processing
                    try:
                        return {k: make_object_accessible(v) for k, v in obj.items()}
                    except Exception as e2:
                        logger.debug(f"[TEMPLATE_SERVICE] Error in fallback dict processing: {e2}")
                        return obj
            elif isinstance(obj, list):
                # Recursively process list items, but be careful about ModelAwareDict objects
                return [make_object_accessible(item) for item in obj]
            else:
                return obj

        # Process all context values
        for key, value in enhanced_context.items():
            enhanced_context[key] = make_object_accessible(value)

        return enhanced_context

    def _is_model_instance_dict(self, obj: dict, context: dict) -> bool:
        """Check if a dictionary appears to be a model instance."""
        # Safety check: ensure obj is actually a dict
        if not isinstance(obj, dict):
            logger.warning(f"[TEMPLATE_SERVICE] _is_model_instance_dict called with non-dict: {type(obj)}")
            return False
        
        # Safety check: ensure context is actually a dict
        if not isinstance(context, dict):
            logger.warning(f"[TEMPLATE_SERVICE] _is_model_instance_dict called with non-dict context: {type(context)}")
            return False
            
        # Don't treat top-level context containers as model instances
        try:
            if obj is context.get("variables") or obj is context.get("inputs") or obj is context.get("outputs") or obj is context.get("system"):
                return False
        except (AttributeError, TypeError):
            logger.warning(f"[TEMPLATE_SERVICE] Error checking context objects in _is_model_instance_dict")
            return False
        
        # Don't treat converted RollResult objects as model instances
        try:
            if obj.get("_original") or "total" in obj or "expression" in obj or "breakdown" in obj:
                return False
        except AttributeError:
            # If obj doesn't have .get() method, it's not a dict we should be processing
            logger.warning(f"[TEMPLATE_SERVICE] Object in _is_model_instance_dict doesn't have .get() method: {type(obj)}")
            return False
        
        # This is a heuristic - we could improve this by checking against known model definitions
        # For now, assume any dict that comes from outputs/inputs in a flow context is likely a model instance
        return isinstance(obj, dict) and len(obj) > 1

    def _determine_model_type_from_context(self, obj: dict, context: dict) -> str | None:
        """Try to determine the model type from context clues."""
        # Strategy 1: Check if the object has explicit type information
        if isinstance(obj, dict) and "type" in obj:
            return obj["type"]
        
        # Strategy 2: Check context for type hints
        # Look through the context to see if this object appears in a typed location
        system_dict = context.get("system", {})
        
        # Strategy 3: For now, assume character type if it has character-like fields
        # This is a fallback heuristic - in a better implementation we'd track object types
        if isinstance(obj, dict):
            character_like_fields = {"abilities", "traits", "inventory", "armor"}
            obj_fields = set(obj.keys())
            if len(character_like_fields & obj_fields) >= 2:
                return "character"
        
        return None

    def is_template(self, text: str) -> bool:
        """Check if a string contains template syntax."""
        if not isinstance(text, str):
            return False
        return "{{" in text or "{%" in text

    def _try_parse_structured_data(self, result: str) -> Any:
        """Try to parse template result as structured data."""
        import ast
        import json

        import yaml

        result = result.strip()

        # Try to parse as number first
        try:
            if "." in result:
                return float(result)
            else:
                return int(result)
        except ValueError:
            pass

        # Explicitly handle boolean strings
        if result.lower() == "true":
            return True
        elif result.lower() == "false":
            return False

        # Try JSON for clearly JSON-formatted results
        if (result.startswith("{") and result.endswith("}")) or (
            result.startswith("[") and result.endswith("]")
        ):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                pass

        # Try Python literal evaluation for Python representations like "['a', 'b', 'c']"
        try:
            parsed = ast.literal_eval(result)
            # Only return if it's actually structured data (not a simple string or number)
            if isinstance(parsed, list | dict | tuple | set):
                return parsed
        except (ValueError, SyntaxError):
            pass

        # Try YAML - but be more selective to avoid parsing display text
        # Only parse multi-line YAML or clearly structured single-line YAML
        if result.count("\n") > 0 or (
            result.startswith("- ") or result.startswith("  ")
        ):
            try:
                parsed = yaml.safe_load(result)
                if parsed != result and not isinstance(
                    parsed, str
                ):  # If YAML parsing changed something meaningful, use it
                    return parsed
            except yaml.YAMLError:
                pass

        # Special handling for single-line YAML that might be intentional structured data
        # but not simple display text like "Strength: +2" or log messages
        if ":" in result and (
            result.count("\n") > 0
            and not any(
                phrase in result.lower()
                for phrase in [
                    "saving throw",
                    "justification",
                    "ability",
                    "type",
                    "roll",
                    "dice",
                    "damage",
                ]
            )
        ):
            try:
                parsed = yaml.safe_load(result)
                if parsed != result and isinstance(
                    parsed, dict
                ):  # Only use parsed dict if it's actually structured
                    return parsed
            except yaml.YAMLError:
                pass

        return None

    def _template_get_value(self, path: str, default: Any = None) -> Any:
        """Template function to get values by path."""
        # This will be bound to the actual context during template resolution
        # For now, return the default - the actual implementation will be injected
        return default

    def _template_has_value(self, path: str) -> bool:
        """Template function to check if a path has a value."""
        # This will be bound to the actual context during template resolution
        return False


class LoadTimeTemplateStrategy(TemplateResolutionStrategy):
    """Template resolution strategy for system loading time."""

    def __init__(self):
        self.loader = StringTemplateLoader()
        self.env = Environment(
            loader=self.loader,
            undefined=StrictUndefined,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._setup_custom_functions()

    def _setup_custom_functions(self) -> None:
        """Setup custom Jinja2 functions and filters for load time."""
        # Custom filters
        self.env.filters["title_case"] = lambda x: str(x).title()
        self.env.filters["snake_case"] = lambda x: re.sub(
            r"[^a-zA-Z0-9]", "_", str(x)
        ).lower()
        self.env.filters["kebab_case"] = lambda x: re.sub(
            r"[^a-zA-Z0-9]", "-", str(x)
        ).lower()
        self.env.filters["upper_first"] = (
            lambda x: str(x)[:1].upper() + str(x)[1:] if x else ""
        )

        # Dice-related filters
        self.env.filters["dice_modifier"] = self._format_dice_modifier
        self.env.filters["signed_number"] = self._format_signed_number

        # Custom globals
        self.env.globals["range"] = range
        self.env.globals["len"] = len
        self.env.globals["str"] = str
        self.env.globals["int"] = int
        self.env.globals["float"] = float

    def _format_dice_modifier(self, value: Any) -> str:
        """Format a number as a dice modifier (+3, -1, etc.)."""
        try:
            num = int(value)
            if num >= 0:
                return f"+{num}"
            else:
                return str(num)  # Already has minus sign
        except (ValueError, TypeError):
            return str(value)

    def _format_signed_number(self, value: Any) -> str:
        """Format a number with explicit sign."""
        try:
            num = float(value)
            if num >= 0:
                return f"+{num:g}"
            else:
                return f"{num:g}"
        except (ValueError, TypeError):
            return str(value)

    def resolve_template(self, template_str: str, context_data: Any) -> Any:
        """Resolve a template using load time context."""
        if not isinstance(template_str, str):
            return template_str

        try:
            template = self.env.from_string(template_str)

            # Ensure context_data is a dict
            if not isinstance(context_data, dict):
                context_data = {"value": context_data}

            return template.render(context_data)
        except TemplateError as e:
            logger.error(f"Load time template rendering error: {e}")
            raise ValueError(f"Template error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected load time template error: {e}")
            raise ValueError(f"Template processing failed: {e}") from e

    def is_template(self, text: str) -> bool:
        """Check if a string contains template syntax."""
        if not isinstance(text, str):
            return False
        return "{{" in text or "{%" in text or "{#" in text

    def add_template(self, name: str, template_str: str) -> None:
        """Add a named template that can be referenced later."""
        self.loader.add_template(name, template_str)

    def render_named_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a previously added named template."""
        try:
            template = self.env.get_template(template_name)
            return template.render(context)
        except TemplateError as e:
            logger.error(f"Named template rendering error: {e}")
            raise ValueError(f"Template '{template_name}' error: {e}") from e

    def validate_template(self, template_str: str) -> str | None:
        """Validate a template string and return error message if invalid."""
        try:
            self.env.from_string(template_str)
            return None
        except TemplateError as e:
            return str(e)

    def extract_variables(self, template_str: str) -> set[str]:
        """Extract variable names used in a template."""
        try:
            ast = self.env.parse(template_str)
            return set(meta.find_undeclared_variables(ast))
        except Exception as e:
            logger.warning(f"Could not extract variables from template: {e}")
            return set()

    def escape_for_template(self, text: str) -> str:
        """Escape text so it can be safely included in a template."""
        # Escape template delimiters
        text = text.replace("{{", r"\{\{")
        text = text.replace("}}", r"\}\}")
        text = text.replace("{%", r"\{\%")
        text = text.replace("%}", r"\%\}")
        text = text.replace("{#", r"\{\#")
        text = text.replace("#}", r"\#\}")
        return text


class StringTemplateLoader(BaseLoader):
    """Custom Jinja2 loader for string templates."""

    def __init__(self):
        self.templates: dict[str, str] = {}

    def get_source(self, environment: Environment, template: str) -> tuple:
        # environment parameter required by Jinja2 interface but not used in this implementation
        _ = environment
        if template in self.templates:
            source = self.templates[template]
            return source, None, lambda: True
        raise TemplateError(f"Template '{template}' not found")

    def add_template(self, name: str, source: str) -> None:
        """Add a template to the loader."""
        self.templates[name] = source


class TemplateService:
    """Unified template resolution service with strategy pattern."""

    def __init__(self):
        self._strategies = {
            "runtime": RuntimeTemplateStrategy(),
            "loadtime": LoadTimeTemplateStrategy(),
        }

    def resolve_template(
        self, template_str: str, context_data: Any, mode: str = "runtime"
    ) -> Any:
        """Resolve a template using the specified strategy."""
        if mode not in self._strategies:
            raise ValueError(f"Unknown template resolution mode: {mode}")

        return self._strategies[mode].resolve_template(template_str, context_data)

    def resolve_template_with_execution_context(
        self, template_str: str, execution_context, system=None, mode: str = "runtime"
    ) -> Any:
        """Resolve a template using ExecutionContext, automatically converting to dict format."""
        # Debug logging for template resolution
        import logging

        logger = logging.getLogger(__name__)

        # Let's check the actual ExecutionContext outputs before conversion
        logger.debug(
            f"BEFORE dict conversion - execution_context.outputs type: {type(execution_context.outputs)}"
        )
        logger.debug(
            f"BEFORE dict conversion - execution_context.outputs content: {execution_context.outputs}"
        )
        if hasattr(execution_context.outputs, "items"):
            for key, value in execution_context.outputs.items():
                logger.debug(
                    f"BEFORE dict conversion - outputs[{key}] = {value} (type: {type(value)})"
                )

        # Convert ExecutionContext to dict for template resolution
        context_dict = {
            "inputs": dict(execution_context.inputs),
            "variables": dict(execution_context.variables),
            "outputs": dict(execution_context.outputs),
        }

        logger.debug(f"Template resolution input: '{template_str}'")
        logger.debug(f"Context dict outputs: {context_dict['outputs']}")
        if "outputs" in context_dict:
            for key, value in context_dict["outputs"].items():
                logger.debug(
                    f"AFTER dict conversion - outputs[{key}] = {value} (type: {type(value)})"
                )

        # Add system metadata if available
        if system:
            logger.debug(f"System object type: {type(system)}")
            logger.debug(f"System object: {system}")
            
            # Convert system.models to a simple dict format to avoid complex object processing
            models_dict = {}
            if hasattr(system, 'models') and system.models:
                for model_id, model_def in system.models.items():
                    if hasattr(model_def, '__dict__'):
                        # Convert ModelDefinition to a simple dict
                        models_dict[model_id] = model_def.__dict__
                    else:
                        models_dict[model_id] = model_def
            
            context_dict["system"] = {
                "id": system.id,
                "name": system.name,
                "description": system.description,
                "version": system.version,
                "currency": getattr(system, "currency", {}),
                "credits": getattr(system, "credits", {}),
                "models": models_dict,  # Use the converted dict instead of system.models directly
            }
            logger.debug(f"Context dict system: {context_dict['system']}")

        result = self.resolve_template(template_str, context_dict, mode)
        logger.debug(f"Template resolution result: '{result}'")
        return result

    def is_template(self, text: str, mode: str = "runtime") -> bool:
        """Check if a string contains template syntax."""
        if mode not in self._strategies:
            raise ValueError(f"Unknown template resolution mode: {mode}")

        return self._strategies[mode].is_template(text)

    def get_strategy(self, mode: str) -> TemplateResolutionStrategy:
        """Get a specific template resolution strategy."""
        if mode not in self._strategies:
            raise ValueError(f"Unknown template resolution mode: {mode}")

        return self._strategies[mode]

    # Convenience methods for backward compatibility
    def add_template(self, name: str, template_str: str) -> None:
        """Add a named template (loadtime strategy)."""
        loadtime_strategy = self._strategies["loadtime"]
        if hasattr(loadtime_strategy, "add_template"):
            loadtime_strategy.add_template(name, template_str)

    def render_named_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a named template (loadtime strategy)."""
        loadtime_strategy = self._strategies["loadtime"]
        if hasattr(loadtime_strategy, "render_named_template"):
            return loadtime_strategy.render_named_template(template_name, context)
        raise ValueError("Named template rendering not supported in runtime mode")

    def validate_template(
        self, template_str: str, mode: str = "loadtime"
    ) -> str | None:
        """Validate a template string."""
        strategy = self._strategies[mode]
        if hasattr(strategy, "validate_template"):
            return strategy.validate_template(template_str)
        return None

    def extract_variables(self, template_str: str, mode: str = "loadtime") -> set[str]:
        """Extract variable names used in a template."""
        strategy = self._strategies[mode]
        if hasattr(strategy, "extract_variables"):
            return strategy.extract_variables(template_str)
        return set()

    def escape_for_template(self, text: str, mode: str = "loadtime") -> str:
        """Escape text for template inclusion."""
        strategy = self._strategies[mode]
        if hasattr(strategy, "escape_for_template"):
            return strategy.escape_for_template(text)
        return text
