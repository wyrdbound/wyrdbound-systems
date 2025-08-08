"""GRIMOIRE system loader for reading and parsing system definitions."""

import logging
from pathlib import Path
from typing import Any

import yaml

from ..models.compendium import CompendiumDefinition
from ..models.flow import (
    ChoiceDefinition,
    DiceSequenceDefinition,
    FlowDefinition,
    InputDefinition,
    LLMSettingsDefinition,
    OutputDefinition,
    StepDefinition,
    StepType,
    TableRollDefinition,
)
from ..models.model import AttributeDefinition, ModelDefinition, ValidationRule
from ..models.prompt import PromptDefinition
from ..models.source import SourceDefinition
from ..models.system import Credits, Currency, CurrencyDenomination, System
from ..models.table import TableDefinition
from ..utils.templates import TemplateHelpers

logger = logging.getLogger(__name__)


class SystemLoader:
    """Loads GRIMOIRE systems from filesystem or URLs."""

    def __init__(self):
        self._loaded_systems: dict[str, System] = {}
        self._template_helpers = TemplateHelpers()

    def load_system(self, system_path: str | Path) -> System:
        """Load a complete GRIMOIRE system from a directory."""
        system_path = Path(system_path)

        if not system_path.exists():
            raise FileNotFoundError(f"System path does not exist: {system_path}")

        if not system_path.is_dir():
            raise ValueError(f"System path must be a directory: {system_path}")

        # Check if already loaded
        system_id = system_path.name
        if system_id in self._loaded_systems:
            return self._loaded_systems[system_id]

        logger.info(f"Loading GRIMOIRE system from {system_path}")

        # Load system.yaml first
        system_file = system_path / "system.yaml"
        if not system_file.exists():
            raise FileNotFoundError(f"system.yaml not found in {system_path}")

        system = self._load_system_definition(system_file)
        system._system_path = system_path

        # Load all other components
        self._load_sources(system_path, system)
        self._load_prompts(system_path, system)
        self._load_models(system_path, system)
        self._load_compendiums(system_path, system)
        self._load_tables(system_path, system)
        self._load_flows(system_path, system)

        # Cache the loaded system
        self._loaded_systems[system.id] = system

        logger.info(f"Successfully loaded system '{system.name}' ({system.id})")
        return system

    def _load_system_definition(self, system_file: Path) -> System:
        """Load the main system definition file."""
        with open(system_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Parse currency if present
        currency = None
        if "currency" in data:
            currency_data = data["currency"]
            denominations = {}

            if "denominations" in currency_data:
                for denom_id, denom_data in currency_data["denominations"].items():
                    denominations[denom_id] = CurrencyDenomination(**denom_data)

            currency = Currency(
                base_unit=currency_data["base_unit"], denominations=denominations
            )

        # Parse credits if present
        credits = None
        if "credits" in data:
            credits = Credits(**data["credits"])

        return System(
            id=data["id"],
            name=data["name"],
            kind=data.get("kind", "system"),
            description=data.get("description"),
            version=data.get("version"),
            default_source=data.get("default_source"),
            currency=currency,
            credits=credits,
        )

    def _load_sources(self, system_path: Path, system: System) -> None:
        """Load source definitions."""
        sources_dir = system_path / "sources"
        if not sources_dir.exists():
            return

        for source_file in sources_dir.glob("*.yaml"):
            try:
                with open(source_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                source = SourceDefinition(**data)
                # Use source ID as key, falling back to name if no ID
                source_key = source.id or source.name
                system.sources[source_key] = source
                logger.debug(f"Loaded source: {source.name} (ID: {source_key})")

            except Exception as e:
                logger.error(f"Failed to load source {source_file}: {e}")

    def _load_prompts(self, system_path: Path, system: System) -> None:
        """Load prompt definitions."""
        prompts_dir = system_path / "prompts"
        if not prompts_dir.exists():
            return

        for prompt_file in prompts_dir.glob("*.yaml"):
            try:
                with open(prompt_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                prompt = PromptDefinition(**data)
                # Use prompt ID as key, falling back to name if no ID
                prompt_key = prompt.id or prompt.name
                system.prompts[prompt_key] = prompt
                logger.debug(f"Loaded prompt: {prompt.name} (ID: {prompt_key})")

            except Exception as e:
                logger.error(f"Failed to load prompt {prompt_file}: {e}")

    def _load_models(self, system_path: Path, system: System) -> None:
        """Load model definitions."""
        models_dir = system_path / "models"
        if not models_dir.exists():
            return

        for model_file in models_dir.glob("*.yaml"):
            try:
                with open(model_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                model = self._parse_model_definition(data)
                system.models[model.id] = model
                logger.debug(f"Loaded model: {model.id}")

            except Exception as e:
                logger.error(f"Failed to load model {model_file}: {e}")

    def _parse_model_definition(self, data: dict[str, Any]) -> ModelDefinition:
        """Parse a model definition from YAML data."""
        # Parse attributes
        attributes = {}
        if "attributes" in data:
            attributes = self._parse_attributes(data["attributes"])

        # Parse validations
        validations = []
        if "validations" in data:
            for val_data in data["validations"]:
                if isinstance(val_data, str):
                    # Simple string validation rule
                    validations.append(
                        ValidationRule(
                            expression=val_data,
                            message=f"Validation failed: {val_data}",
                        )
                    )
                elif isinstance(val_data, dict):
                    # Complex validation rule with expression and message
                    validations.append(ValidationRule(**val_data))
                else:
                    logger.warning(f"Skipping invalid validation rule: {val_data}")

        return ModelDefinition(
            id=data["id"],
            name=data["name"],
            kind=data.get("kind", "model"),
            description=data.get("description"),
            version=data.get("version", 1),
            extends=data.get("extends", []),
            attributes=attributes,
            validations=validations,
        )

    def _parse_attributes(self, attrs_data: dict[str, Any]) -> dict[str, Any]:
        """Parse attribute definitions recursively."""
        parsed_attrs = {}

        for attr_name, attr_data in attrs_data.items():
            if isinstance(attr_data, dict):
                if "type" in attr_data:
                    # This is an attribute definition
                    # Derived attributes should not be required since they're calculated
                    is_derived = "derived" in attr_data
                    required = attr_data.get("required", not is_derived)

                    parsed_attrs[attr_name] = AttributeDefinition(
                        type=attr_data["type"],
                        default=attr_data.get("default"),
                        range=attr_data.get("range"),
                        enum=attr_data.get("enum"),
                        derived=attr_data.get("derived"),
                        required=required,
                        description=attr_data.get("description"),
                        of=attr_data.get("of"),
                        optional=attr_data.get("optional"),
                    )
                else:
                    # This is a nested attribute group
                    parsed_attrs[attr_name] = self._parse_attributes(attr_data)
            else:
                # Simple attribute
                parsed_attrs[attr_name] = attr_data

        return parsed_attrs

    def _load_compendiums(self, system_path: Path, system: System) -> None:
        """Load compendium definitions."""
        compendium_dir = system_path / "compendium"
        if not compendium_dir.exists():
            return

        # Load compendiums recursively from subdirectories
        for compendium_file in compendium_dir.rglob("*.yaml"):
            try:
                with open(compendium_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                compendium = CompendiumDefinition(**data)
                system.compendiums[compendium.id] = compendium
                logger.debug(
                    f"Loaded compendium: {compendium.name} (ID: {compendium.id}) ({len(compendium.entries)} entries)"
                )

            except Exception as e:
                logger.error(f"Failed to load compendium {compendium_file}: {e}")

    def _load_tables(self, system_path: Path, system: System) -> None:
        """Load table definitions."""
        tables_dir = system_path / "tables"
        if not tables_dir.exists():
            return

        # Load tables recursively from subdirectories
        for table_file in tables_dir.rglob("*.yaml"):
            try:
                with open(table_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                table = TableDefinition(**data)
                system.tables[table.id] = table
                logger.debug(
                    f"Loaded table: {table.name} (ID: {table.id}) ({len(table.entries)} entries)"
                )

            except Exception as e:
                logger.error(f"Failed to load table {table_file}: {e}")

    def _validate_system_components(self, system: System) -> None:
        """Validate system components that require cross-references."""
        # Validate tables with access to system models
        validation_errors = []

        for table_id, table in system.tables.items():
            table_errors = table.validate_with_system(system)
            for error in table_errors:
                validation_errors.append(f"Table '{table_id}': {error}")

        if validation_errors:
            error_msg = "System validation failed:\n" + "\n".join(validation_errors)
            raise ValueError(error_msg)

    def _load_flows(self, system_path: Path, system: System) -> None:
        """Load flow definitions."""
        flows_dir = system_path / "flows"
        if not flows_dir.exists():
            return

        # Load flows recursively from flows directory and subdirectories
        for flow_file in flows_dir.rglob("*.yaml"):
            try:
                with open(flow_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)

                flow = self._parse_flow_definition(data, system)
                system.flows[flow.id] = flow
                logger.debug(f"Loaded flow: {flow.id} ({len(flow.steps)} steps)")

            except Exception as e:
                logger.error(f"Failed to load flow {flow_file}: {e}")

    def _parse_flow_definition(
        self, data: dict[str, Any], system: System | None = None
    ) -> FlowDefinition:
        """Parse a flow definition from YAML data."""
        # Resolve templates if system context is available
        if system:
            context = {"system": system}
            data = self._resolve_templates_in_dict(data, context)

        # Parse inputs
        inputs = []
        if "inputs" in data:
            for input_data in data["inputs"]:
                inputs.append(InputDefinition(**input_data))

        # Parse outputs
        outputs = []
        if "outputs" in data:
            for output_data in data["outputs"]:
                outputs.append(OutputDefinition(**output_data))

        # Parse steps
        steps = []
        if "steps" in data:
            for step_data in data["steps"]:
                steps.append(self._parse_step_definition(step_data))

        return FlowDefinition(
            id=data["id"],
            name=data["name"],
            type=data.get("type", "flow"),
            description=data.get("description"),
            version=data.get("version"),
            inputs=inputs,
            outputs=outputs,
            variables=data.get("variables", {}),
            steps=steps,
            resume_points=data.get("resume_points", []),
        )

    def _parse_step_definition(self, data: dict[str, Any]) -> StepDefinition:
        """Parse a step definition from YAML data."""
        step_type = StepType(data["type"])

        # Parse choices for player_choice steps
        choices = []
        if "choices" in data:
            for choice_data in data["choices"]:
                choices.append(ChoiceDefinition(**choice_data))

        # Parse tables for table_roll steps
        tables = []
        if "tables" in data:
            for table_data in data["tables"]:
                tables.append(TableRollDefinition(**table_data))

        # Parse sequence for dice_sequence steps
        sequence = None
        if "sequence" in data:
            sequence = DiceSequenceDefinition(**data["sequence"])

        # Parse LLM settings
        llm_settings = None
        if "llm_settings" in data:
            llm_settings = LLMSettingsDefinition(**data["llm_settings"])

        return StepDefinition(
            id=data["id"],
            name=data.get("name"),  # Make name optional
            type=step_type,
            prompt=data.get("prompt"),
            condition=data.get("condition"),
            parallel=data.get("parallel", False),
            actions=data.get("actions", []),
            next_step=data.get("next_step"),
            output=data.get("output"),
            roll=data.get("roll"),
            modifiers=data.get("modifiers"),
            sequence=sequence,
            choices=choices,
            choice_source=data.get("choice_source"),
            pre_actions=data.get("pre_actions", []),
            tables=tables,
            prompt_id=data.get("prompt_id"),
            prompt_data=data.get("prompt_data", {}),
            llm_settings=llm_settings,
        )

    def reload_system(self, system_id: str) -> System | None:
        """Reload a previously loaded system."""
        if system_id not in self._loaded_systems:
            return None

        system = self._loaded_systems[system_id]
        if system._system_path:
            # Remove from cache and reload
            del self._loaded_systems[system_id]
            return self.load_system(system._system_path)

        return None

    def _resolve_templates_in_dict(
        self, data: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively resolve templates in dictionary values."""
        resolved = {}
        for key, value in data.items():
            resolved[key] = self._resolve_templates_in_value(value, context)
        return resolved

    def _resolve_templates_in_value(self, value: Any, context: dict[str, Any]) -> Any:
        """Resolve templates in a single value."""
        if isinstance(value, str):
            if self._template_helpers.is_template(value):
                try:
                    # Check if template contains execution-time variables or functions
                    variables = self._template_helpers.extract_variables(value)
                    execution_vars = {
                        "result",
                        "results",
                        "item",
                        "selected_item",
                        "selected_items",
                        "variables",
                        "llm_result",
                        "key",
                        "value",
                    }

                    # Also check for execution-time function calls
                    execution_functions = ["get_value"]
                    has_execution_functions = any(
                        func in value for func in execution_functions
                    )

                    # If template contains execution-time variables or functions, don't resolve during loading
                    if (
                        any(var in execution_vars for var in variables)
                        or has_execution_functions
                    ):
                        logger.debug(
                            f"Skipping template resolution during loading for: {value}"
                        )
                        return value

                    return self._template_helpers.render_template(value, context)
                except Exception as e:
                    logger.debug(f"Failed to resolve template '{value}': {e}")
                    return value
            return value
        elif isinstance(value, dict):
            return self._resolve_templates_in_dict(value, context)
        elif isinstance(value, list):
            return [self._resolve_templates_in_value(item, context) for item in value]
        else:
            return value

    def list_loaded_systems(self) -> list[str]:
        """Get a list of loaded system IDs."""
        return list(self._loaded_systems.keys())
