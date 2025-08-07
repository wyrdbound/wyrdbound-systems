"""Table rolling step executor."""

import logging
from typing import TYPE_CHECKING, Any

from ..integrations.dice_integration import DiceIntegration
from .base import BaseStepExecutor

if TYPE_CHECKING:
    from ..models.context_data import ExecutionContext
    from ..models.flow import StepDefinition, StepResult
    from ..models.system import System

logger = logging.getLogger(__name__)


class TableExecutor(BaseStepExecutor):
    """Executor for table rolling steps."""

    def __init__(self):
        self.dice_integration = DiceIntegration()

    def execute(
        self, step: "StepDefinition", context: "ExecutionContext", system: "System"
    ) -> "StepResult":
        """Execute a table rolling step."""
        from ..models.flow import StepResult

        if not step.tables:
            return StepResult(
                step_id=step.id,
                success=False,
                error="Table roll step requires 'tables' parameter",
            )

        try:
            all_results = []

            if step.parallel:
                # Execute all table rolls in parallel (conceptually)
                for table_roll in step.tables:
                    result = self._execute_table_roll(table_roll, context, system)
                    all_results.append(result)
            else:
                # Execute table rolls sequentially
                for table_roll in step.tables:
                    result = self._execute_table_roll(table_roll, context, system)
                    all_results.append(result)

            logger.info(f"Table rolling completed: {len(all_results)} rolls")

            return StepResult(
                step_id=step.id,
                success=True,
                data={"table_results": all_results, "parallel": step.parallel},
                prompt=step.prompt,
            )

        except Exception as e:
            logger.error(f"Error executing table roll step {step.id}: {e}")
            return StepResult(
                step_id=step.id, success=False, error=f"Table roll failed: {e}"
            )

    def _execute_table_roll(
        self, table_roll, context: "ExecutionContext", system: "System"
    ):
        """Execute a single table roll."""
        table_name = table_roll.table
        count = table_roll.count

        # Get the table definition
        table = system.get_table(table_name)
        if not table:
            raise ValueError(f"Table '{table_name}' not found in system")

        results = []

        for _ in range(count):
            # Roll on the table
            if table.roll:
                # Use the table's dice expression
                dice_result = self.dice_integration.roll_expression(table.roll)
                roll_value = dice_result.total
            else:
                # Default to d100 if no roll specified
                dice_result = self.dice_integration.roll_expression("1d100")
                roll_value = dice_result.total

            # Get the result from the table
            table_result = table.get_entry_by_range(roll_value)
            if table_result is None:
                table_result = table.get_entry(roll_value)

            if table_result is None:
                # Fallback to random entry
                table_result = table.get_random_entry()

            # Convert string result to typed object if table has entry_type
            typed_result = self._create_typed_object(table_result, table, system)
            logger.info(
                f"table_result={table_result}, typed_result type={type(typed_result).__name__}"
            )

            result_data = {
                "table": table_name,
                "roll": roll_value,
                "result": typed_result,
                "dice_expression": table.roll or "1d100",
            }

            results.append(result_data)

            # Log the individual table roll result
            logger.info(
                f"Table roll result: {table_name.title()}: {table_result} (rolled {roll_value})"
            )

            # Execute table actions with result context
            if table_roll.actions:
                logger.info(
                    f"Executing table actions with typed_result: {type(typed_result).__name__}"
                )
                self._execute_table_actions(
                    table_roll.actions, context, system, typed_result, results
                )

        # If only one result, return it directly, otherwise return list
        if count == 1:
            return results[0]
        else:
            return {"table": table_name, "results": results, "count": count}

    def _execute_table_actions(
        self,
        actions: list[Any],
        context: "ExecutionContext",
        system: "System",
        result: Any,
        all_results: list[Any],
    ) -> None:
        """Execute actions after a table roll."""
        # Skip actions if result is None (from "none" table entries)
        if result is None:
            logger.info(
                "Skipping table actions because result is None (table rolled 'none')"
            )
            return

        # Add result to template context temporarily
        original_result = context.get_variable("result")
        original_results = context.get_variable("results")

        logger.info(f"Setting context result to: {type(result).__name__} = {result}")
        context.set_variable("result", result)
        context.set_variable("results", all_results)

        try:
            for action in actions:
                self._execute_table_action(action, context, system, result)
        finally:
            # Restore original values
            if original_result is not None:
                context.set_variable("result", original_result)
            if original_results is not None:
                context.set_variable("results", original_results)

    def _execute_table_action(
        self, action, context: "ExecutionContext", system: "System", result: Any
    ) -> None:
        """Execute a single table action."""
        # Handle both old format (key as action type) and new format (type field)
        if "type" in action and "data" in action:
            action_type = action["type"]
            action_data = action["data"]
        else:
            # Fallback to old format
            action_type = list(action.keys())[0]
            action_data = action[action_type]

        if action_type == "set_value":
            path = action_data["path"]
            value = action_data["value"]

            # Resolve templates
            resolved_value = context.resolve_template(str(value))

            # Get current flow namespace for proper isolation
            current_namespace = context.get_current_flow_namespace()

            if current_namespace:
                # Use namespaced path to avoid collision
                if path.startswith("outputs."):
                    namespaced_path = f"{current_namespace}.outputs.{path[8:]}"
                elif path.startswith("variables."):
                    namespaced_path = f"{current_namespace}.variables.{path[10:]}"
                else:
                    # Default to outputs if no prefix specified
                    namespaced_path = f"{current_namespace}.outputs.{path}"

                context.set_namespaced_value(namespaced_path, resolved_value)
            else:
                # Fallback to original behavior for backward compatibility
                if path.startswith("outputs."):
                    context.set_output(path[8:], resolved_value)
                elif path.startswith("variables."):
                    context.set_variable(path[10:], resolved_value)
                else:
                    context.set_output(path, resolved_value)
                logger.info(f"Set non-namespaced value: {path} = {resolved_value}")

        elif action_type == "flow_call":
            # Handle sub-flow calls
            flow_id = action_data["flow"]
            inputs = action_data.get("inputs", {})
            logger.info(f"Flow call requested: {flow_id} (inputs: {inputs})")

            # Check if the flow exists in the system
            flow_obj = system.get_flow(flow_id)
            if not flow_obj:
                # Get available flows for better error message
                available_flows = (
                    list(system.flows.keys()) if hasattr(system, "flows") else []
                )
                flow_list = (
                    ", ".join(sorted(available_flows)) if available_flows else "none"
                )
                raise ValueError(
                    f"Flow '{flow_id}' not found in system. Available flows: {flow_list}"
                )

            # Execute the sub-flow
            self._execute_sub_flow(flow_id, inputs, context, system, inputs)

        # TODO: Add other action types as needed

    def _execute_sub_flow(
        self,
        flow_id: str,
        inputs: dict[str, Any],
        context: "ExecutionContext",
        system: "System",
        original_inputs: dict[str, Any] = None,
    ) -> None:
        """Execute a sub-flow call from within a table action."""
        from ..models.context_data import ExecutionContext

        logger.info(f"Executing sub-flow: {flow_id}")

        # Create a new execution context for the sub-flow
        sub_context = ExecutionContext()

        # Resolve input values from the current context
        resolved_inputs = {}
        for input_key, input_value in inputs.items():
            if (
                isinstance(input_value, str)
                and input_value.startswith("{{")
                and input_value.endswith("}}")
            ):
                # This is a template expression, resolve it
                try:
                    # Debug: Check what's available in context
                    if input_value == "{{ result }}":
                        current_result = context.get_variable("result")
                        logger.info(
                            f"Context result variable: {type(current_result).__name__} = {current_result}"
                        )

                        # For "result" variable, use direct access to avoid string conversion
                        if current_result is not None and isinstance(
                            current_result, dict
                        ):
                            resolved_value = current_result
                            logger.info(
                                f"Used direct result access: {type(resolved_value).__name__}"
                            )
                        else:
                            resolved_value = context.resolve_template(input_value)
                            logger.info(
                                f"Used template resolution for result: {type(resolved_value).__name__}"
                            )
                    elif input_value == "{{ selected_item }}":
                        # Special handling for selected_item - convert string to typed object if needed
                        selected_item = context.get_variable("selected_item")
                        logger.info(
                            f"Context selected_item variable: {type(selected_item).__name__} = {selected_item}"
                        )

                        if isinstance(selected_item, str) and selected_item:
                            # Try to convert the string to a typed object using the same logic as table rolls
                            # We need to guess the entry_type based on context or use a default
                            # For weapon choices, we can assume it's a weapon type
                            typed_result = self._convert_string_to_typed_object(
                                selected_item, "weapon", system
                            )
                            if typed_result:
                                resolved_value = typed_result
                                logger.info(
                                    f"Converted selected_item string to typed object: {type(resolved_value).__name__}"
                                )
                            else:
                                resolved_value = selected_item
                                logger.info(
                                    f"Could not convert selected_item, using string: {selected_item}"
                                )
                        else:
                            resolved_value = context.resolve_template(input_value)
                            logger.info(
                                f"Used template resolution for selected_item: {type(resolved_value).__name__}"
                            )
                    else:
                        resolved_value = context.resolve_template(input_value)

                    resolved_inputs[input_key] = resolved_value
                    logger.info(
                        f"Resolved input {input_key}: {input_value} -> {type(resolved_value).__name__}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to resolve input {input_key}: {input_value} - {e}"
                    )
                    # Use the literal value as fallback
                    resolved_inputs[input_key] = input_value
            elif isinstance(input_value, str) and "outputs." in input_value:
                # This is a direct reference to an output, resolve it
                try:
                    resolved_value = context.resolve_path_value(input_value)
                    resolved_inputs[input_key] = resolved_value
                    logger.info(
                        f"Resolved output reference {input_key}: {input_value} -> {type(resolved_value).__name__}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to resolve output reference {input_key}: {input_value} - {e}"
                    )
                    resolved_inputs[input_key] = input_value
            else:
                resolved_inputs[input_key] = input_value

        # Set the resolved inputs in the sub-flow context
        for input_key, input_value in resolved_inputs.items():
            sub_context.set_input(input_key, input_value)

        # Import the engine to execute the flow
        from ..core.engine import GrimoireEngine

        # Create an engine instance and execute the sub-flow
        engine = GrimoireEngine()
        try:
            flow_result = engine.execute_flow(flow_id, sub_context, system)
            logger.info(
                f"Sub-flow {flow_id} completed with success: {flow_result.success}"
            )

            # Debug: Log what the sub-flow produced after completion
            logger.info(
                f"Sub-flow outputs after completion: {list(sub_context.outputs.keys())}"
            )
            for key, value in sub_context.outputs.items():
                logger.info(f"Sub-flow output {key}: {type(value).__name__} = {value}")

            # Merge the sub-flow outputs back into the main context
            for output_key, output_value in sub_context.outputs.items():
                logger.info(
                    f"Merging sub-flow output: {output_key} = {type(output_value).__name__}"
                )

                # Intelligently map sub-flow outputs back to main context
                # If an input was passed from a main context output, map the sub-flow output back to that location
                target_output_key = output_key
                if original_inputs:
                    for input_key, original_input_value in original_inputs.items():
                        if (
                            input_key == output_key
                            and isinstance(original_input_value, str)
                            and original_input_value.startswith("outputs.")
                        ):
                            # Extract the output key from the path (e.g., "outputs.knave" -> "knave")
                            target_output_key = original_input_value[
                                8:
                            ]  # Remove "outputs." prefix
                            logger.info(
                                f"Mapping sub-flow output '{output_key}' back to main context '{target_output_key}' based on input mapping"
                            )
                            break

                if target_output_key in context.outputs:
                    # Update existing output
                    logger.info(
                        f"Updating output {target_output_key} with sub-flow result"
                    )

                    # Merge dictionaries if both are dicts, otherwise replace
                    if isinstance(output_value, dict) and isinstance(
                        context.outputs.get(target_output_key), dict
                    ):
                        # For dictionary updates, merge the new data into the existing data
                        existing_data = context.outputs[target_output_key]
                        updated_data = {**existing_data, **output_value}
                        context.outputs[target_output_key] = updated_data
                        logger.info(
                            f"Merged data to {target_output_key}: {updated_data}"
                        )
                    else:
                        context.outputs[target_output_key] = output_value
                else:
                    # Create new output
                    logger.info(f"Creating new output {target_output_key}")
                    context.outputs[target_output_key] = output_value

                # Update observables if available
                logger.info(
                    f"Checking if observable update needed for {target_output_key}: has_derived_field_manager={hasattr(context, '_derived_field_manager')}"
                )
                if (
                    hasattr(context, "_derived_field_manager")
                    and context._derived_field_manager
                ):
                    logger.info(
                        f"Output value type: {type(output_value)}, existing type: {type(context.outputs.get(target_output_key))}"
                    )
                    if isinstance(output_value, dict) and isinstance(
                        context.outputs.get(target_output_key), dict
                    ):
                        # Update observables for any dictionary data
                        logger.info(f"Updating observables for {target_output_key}")
                        self._update_observables_from_dict(
                            context, "", output_value, instance_id=target_output_key
                        )
                    else:
                        logger.info("Skipping observable update - not both dicts")
                else:
                    logger.info("No derived field manager available")

        except Exception as e:
            logger.error(f"Sub-flow {flow_id} execution failed: {e}")
            raise

    def _update_observables_from_dict(
        self,
        context: "ExecutionContext",
        base_key: str,
        new_data: dict,
        instance_id: str = None,
    ) -> None:
        """Update observable values from a nested dictionary (like updated character data)."""

        def update_recursive(data: dict, path_prefix: str = ""):
            for key, value in data.items():
                full_path = f"{path_prefix}.{key}" if path_prefix else key

                # Build qualified path for observable system
                if instance_id:
                    # Use the specific instance ID for character data
                    qualified_path = f"{instance_id}.{full_path}"
                elif base_key:
                    qualified_path = f"{base_key}.{full_path}"
                else:
                    qualified_path = full_path

                if isinstance(value, dict):
                    # Recursively handle nested dictionaries
                    update_recursive(value, full_path)
                elif isinstance(value, list):
                    # Handle lists specially to preserve them as lists, not strings
                    try:
                        logger.info(
                            f"_update_observables_from_dict: Processing list for {qualified_path} = {type(value).__name__} with {len(value)} items"
                        )
                        context._derived_field_manager.set_field_value(
                            qualified_path, value
                        )
                        logger.info(
                            f"Updated observable field {qualified_path} = {type(value).__name__} with {len(value)} items"
                        )
                    except Exception as e:
                        logger.debug(
                            f"Could not update observable for {qualified_path}: {e}"
                        )
                else:
                    # This is a leaf value, update it through the observable system
                    # Generic handling: if this looks like serialized structured data, try to parse it
                    if (
                        isinstance(value, str)
                        and value.startswith(("[", "{"))
                        and value.endswith(("]", "}"))
                    ):
                        logger.debug(
                            f"_update_observables_from_dict: Detected potential serialized data for {qualified_path}, attempting to parse"
                        )
                        try:
                            import json

                            parsed_value = json.loads(value)
                            if isinstance(parsed_value, list | dict):
                                logger.debug(
                                    f"Successfully parsed serialized data for {qualified_path}, using structured data instead of string"
                                )
                                context._derived_field_manager.set_field_value(
                                    qualified_path, parsed_value
                                )
                            else:
                                # Not structured data after parsing, use original string
                                context._derived_field_manager.set_field_value(
                                    qualified_path, value
                                )
                        except json.JSONDecodeError:
                            logger.debug(
                                f"Failed to parse potential serialized data for {qualified_path}, using original string"
                            )
                            context._derived_field_manager.set_field_value(
                                qualified_path, value
                            )
                    else:
                        context._derived_field_manager.set_field_value(
                            qualified_path, value
                        )
                    logger.info(f"Updated observable field {qualified_path} = {value}")
                    try:
                        pass
                    except Exception as e:
                        logger.debug(
                            f"Could not update observable for {qualified_path}: {e}"
                        )

        update_recursive(new_data)

    def _convert_string_to_typed_object(
        self, entry_name: str, entry_type: str, system: "System"
    ) -> Any:
        """Convert a string entry name to a typed object (used for selected_item handling)."""
        try:
            # Use the same logic as _create_typed_object
            return self._create_typed_object(
                entry_name, type("MockTable", (), {"entry_type": entry_type})(), system
            )
        except Exception as e:
            logger.warning(
                f"Could not convert string '{entry_name}' to {entry_type} object: {e}"
            )
            return None

    def _create_typed_object(self, entry_result, table, system: "System") -> Any:
        """Create a typed object from a table entry based on the table's entry_type or entry-specific type override."""

        # Handle dictionary entries with type overrides and other metadata
        if isinstance(entry_result, dict):
            # Extract the actual entry name/id
            entry_name = entry_result.get("id")

            # Determine the type to use (entry-specific type or table's entry_type)
            entry_type = entry_result.get("type", table.entry_type if hasattr(table, "entry_type") else "str")

            # Handle generation flag
            if entry_result.get("generate", False):
                # TODO: Implement dynamic generation
                logger.info(f"Generation requested for type '{entry_type}' - not yet implemented")
                return f"Generated {entry_type}"

            # Handle type-only entries (no specific id)
            if not entry_name:
                # TODO: Implement random selection from compendium
                logger.info(f"Random selection requested for type '{entry_type}' - not yet implemented")
                return f"Random {entry_type}"
        else:
            # Simple string entry
            entry_name = entry_result
            entry_type = table.entry_type if hasattr(table, "entry_type") else "str"

        # Handle "none" as a special case - return None instead of creating an object
        if entry_name == "none":
            logger.info(
                "_create_typed_object: entry_name is 'none', returning None (no item)"
            )
            return None

        # If the entry type is "str", return the string as-is
        if not entry_type or entry_type == "str":
            logger.info(
                f"_create_typed_object: entry_type is str or empty, returning string: {entry_name}"
            )
            return entry_name

        logger.info(f"Creating {entry_type} object for entry: {entry_name}")

        # Find the specific compendium that contains this entry
        compendium = self._find_compendium_with_entry(entry_name, entry_type, system)
        if not compendium:
            logger.warning(
                f"No compendium found for entry '{entry_name}' of type '{entry_type}', creating minimal object"
            )
            # Create a minimal typed object with reasonable defaults for the missing entry
            # This ensures consistent object structure even for undefined entries
            entry_data = self._create_minimal_object_for_type(
                entry_type, entry_name, system
            )
            if not entry_data:
                logger.info(
                    f"_create_typed_object: could not create minimal object, returning string: {entry_name}"
                )
                return entry_name
        else:
            # Get the entry definition from the compendium
            entry_data = compendium.get_entry(entry_name)

        # Create the typed object with the entry data
        # Add the id field for reference
        typed_object = {"id": entry_name, **entry_data}

        # Apply model inheritance and defaults
        typed_object = self._apply_model_inheritance(typed_object, entry_type, system)

        logger.info(
            f"Created {entry_type} object: {entry_name} with attributes: {list(typed_object.keys())}"
        )
        logger.info(
            f"_create_typed_object returning: {type(typed_object).__name__} = {typed_object}"
        )
        return typed_object

    def _find_compendium_for_type(self, entry_type: str, system: "System"):
        """Find a compendium that matches the given entry type."""
        # Search through all compendiums to find one with the matching model type
        for compendium_id, compendium in system.compendiums.items():
            if hasattr(compendium, "model") and compendium.model == entry_type:
                logger.info(
                    f"Found compendium '{compendium_id}' for type '{entry_type}'"
                )
                return compendium

        # If no exact match, try to find a compendium with a name that suggests it contains this type
        # This is a fallback for cases where the model field might not be set correctly
        for compendium_id, compendium in system.compendiums.items():
            if (
                entry_type.lower() in compendium_id.lower()
                or entry_type.lower() in compendium.name.lower()
            ):
                logger.info(
                    f"Found compendium '{compendium_id}' for type '{entry_type}' by name matching"
                )
                return compendium

        return None

    def _find_compendium_with_entry(
        self, entry_name: str, entry_type: str, system: "System"
    ):
        """Find the specific compendium that contains the given entry."""
        # Search through all compendiums of the correct type to find the one with this entry
        for compendium_id, compendium in system.compendiums.items():
            if hasattr(compendium, "model") and compendium.model == entry_type:
                # Check if this compendium has the entry
                entry_data = compendium.get_entry(entry_name)
                if entry_data:
                    logger.info(
                        f"Found entry '{entry_name}' in compendium '{compendium_id}' for type '{entry_type}'"
                    )
                    return compendium

        # Fallback: search by name matching
        for compendium_id, compendium in system.compendiums.items():
            if (
                entry_type.lower() in compendium_id.lower()
                or entry_type.lower() in compendium.name.lower()
            ):
                entry_data = compendium.get_entry(entry_name)
                if entry_data:
                    logger.info(
                        f"Found entry '{entry_name}' in compendium '{compendium_id}' for type '{entry_type}' by name matching"
                    )
                    return compendium

        return None

    def _apply_model_inheritance(
        self, obj: dict, model_type: str, system: "System"
    ) -> dict:
        """Apply model inheritance and defaults to a typed object."""
        # Get the model definition
        model = system.get_model(model_type)
        if not model:
            logger.warning(f"Model '{model_type}' not found, skipping inheritance")
            return obj

        # Create a copy to avoid modifying the original
        result = dict(obj)

        # Apply inheritance from extended models first (recursive)
        if hasattr(model, "extends") and model.extends:
            for parent_model_id in model.extends:
                result = self._apply_model_inheritance(result, parent_model_id, system)

        # Apply defaults from this model's attributes
        if hasattr(model, "attributes") and model.attributes:
            for attr_name, attr_def in model.attributes.items():
                # Only set default if the attribute is not already present
                if attr_name not in result:
                    if hasattr(attr_def, "default") and attr_def.default is not None:
                        result[attr_name] = attr_def.default
                        logger.debug(
                            f"Applied default {attr_name}={attr_def.default} from model {model_type}"
                        )

        return result

    def _create_minimal_object_for_type(
        self, entry_type: str, entry_name: str, system: "System"
    ) -> dict:
        """Create a minimal object with reasonable defaults for a missing compendium entry."""
        # This provides system-agnostic fallback objects to ensure consistent typing
        # System designers should define proper compendium entries, but this prevents runtime errors

        base_object = {
            "id": entry_name,
            "name": entry_name.replace("_", " ").title(),
        }

        # Apply model inheritance and defaults if the model exists
        try:
            base_object = self._apply_model_inheritance(base_object, entry_type, system)
            logger.info(
                f"Applied model inheritance for minimal {entry_type} object '{entry_name}'"
            )
        except Exception as e:
            logger.warning(f"Could not apply model inheritance for {entry_type}: {e}")
            # Fall back to manual defaults
            self._add_fallback_defaults(base_object, entry_type, entry_name)

        logger.info(
            f"Created minimal {entry_type} object for '{entry_name}' with attributes: {list(base_object.keys())}"
        )
        return base_object

    def _add_fallback_defaults(
        self, base_object: dict, entry_type: str, entry_name: str
    ) -> None:
        """Add fallback defaults when model inheritance is not available."""
        # Add type-specific defaults based on common patterns
        if entry_type == "item":
            base_object.update(
                {
                    "slot_cost": 0,  # Default to no inventory slots for unknown items
                    "cost": 0,
                    "description": f"Unknown item: {entry_name}",
                }
            )
        elif entry_type == "armor":
            base_object.update(
                {
                    "armor_bonus": 0,  # Default to no armor bonus for unknown armor
                    "slot_cost": 0,
                    "cost": 0,
                    "description": f"Unknown armor: {entry_name}",
                }
            )
        elif entry_type == "weapon":
            base_object.update(
                {
                    "damage": "1d4",  # Default minimal damage
                    "slot_cost": 1,
                    "cost": 0,
                    "description": f"Unknown weapon: {entry_name}",
                }
            )
        else:
            # Generic object for unknown types
            base_object.update(
                {
                    "description": f"Unknown {entry_type}: {entry_name}",
                }
            )

    def can_execute(self, step: "StepDefinition") -> bool:
        """Check if this executor can handle the step."""
        step_type = step.type.value if hasattr(step.type, "value") else str(step.type)
        return step_type == "table_roll"

    def validate_step(self, step: "StepDefinition") -> list[str]:
        """Validate table roll step configuration."""
        errors = []

        if not step.tables:
            errors.append("Table roll step must have 'tables' parameter")

        for table_roll in step.tables:
            if not hasattr(table_roll, "table") or not table_roll.table:
                errors.append("Each table roll must specify a 'table'")

        return errors
