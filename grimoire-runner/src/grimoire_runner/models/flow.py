"""Flow definition models for GRIMOIRE runner."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepType(Enum):
    """Types of flow steps."""

    DICE_ROLL = "dice_roll"
    DICE_SEQUENCE = "dice_sequence"
    PLAYER_CHOICE = "player_choice"
    PLAYER_INPUT = "player_input"
    TABLE_ROLL = "table_roll"
    LLM_GENERATION = "llm_generation"
    COMPLETION = "completion"
    FLOW_CALL = "flow_call"
    CONDITIONAL = "conditional"


@dataclass
class InputDefinition:
    """Flow input parameter definition."""

    type: str
    id: str
    required: bool = True
    description: str | None = None
    enum: list[str] | None = None


@dataclass
class OutputDefinition:
    """Flow output parameter definition."""

    type: str
    id: str
    validate: bool = False
    description: str | None = None


@dataclass
@dataclass
class VariableDefinition:
    """Flow variable definition."""

    id: str
    type: str = "unknown"
    description: str | None = None
    default: Any = None  # Default value for the variable


@dataclass
class ChoiceDefinition:
    """Player choice option."""

    id: str
    label: str
    next_step: str | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
    reset_outputs: bool = False
    description: str | None = None


@dataclass
class ActionDefinition:
    """Action that can be performed during step execution."""

    type: str  # set_value, get_value, etc.
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class TableRollDefinition:
    """Table roll configuration."""

    table: str
    count: int = 1
    actions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DiceSequenceDefinition:
    """Dice sequence configuration."""

    items: list[str]
    roll: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    display_as: str | None = None


@dataclass
class LLMSettingsDefinition:
    """LLM configuration settings."""

    provider: str = "anthropic"
    model: str = "claude-3-haiku"
    max_tokens: int = 200
    temperature: float = 0.7


@dataclass
class StepDefinition:
    """Base flow step definition."""

    id: str
    name: str | None = None
    type: StepType | None = None
    prompt: str | None = None
    condition: str | None = None
    result_message: str | None = (
        None  # Custom result message (emoji will be auto-prepended)
    )
    parallel: bool = False
    actions: list[dict[str, Any]] = field(default_factory=list)
    next_step: str | None = None
    output: str | None = None  # Variable name to store step result

    # Step-specific fields
    # For dice_roll
    roll: str | None = None
    modifiers: dict[str, Any] | None = None

    # For dice_sequence
    sequence: DiceSequenceDefinition | None = None

    # For player_choice
    choices: list[ChoiceDefinition] = field(default_factory=list)
    choice_source: str | None = None
    pre_actions: list[dict[str, Any]] = field(default_factory=list)

    # For table_roll
    tables: list[TableRollDefinition] = field(default_factory=list)

    # For llm_generation
    prompt_id: str | None = None
    prompt_data: dict[str, Any] = field(default_factory=dict)
    llm_settings: LLMSettingsDefinition | None = None

    # For conditional
    if_condition: str | None = None  # Condition to evaluate (alias for condition)
    then_actions: list[dict[str, Any]] = field(
        default_factory=list
    )  # Actions to execute if condition is true
    else_actions: dict[str, Any] | None = (
        None  # Actions to execute if condition is false (can be nested conditional)
    )

    # For flow_call
    flow: str | None = None  # Target flow ID to call
    inputs: dict[str, Any] = field(default_factory=dict)  # Inputs to pass to sub-flow
    result: str | None = None  # Where to store sub-flow result (variable path)


@dataclass
class FlowDefinition:
    """Complete flow definition."""

    id: str
    name: str
    type: str = "flow"
    description: str | None = None
    version: str | None = None

    inputs: list[InputDefinition] = field(default_factory=list)
    outputs: list[OutputDefinition] = field(default_factory=list)
    variables: list[VariableDefinition] = field(default_factory=list)
    steps: list[StepDefinition] = field(default_factory=list)
    resume_points: list[str] = field(default_factory=list)

    def get_step(self, step_id: str) -> StepDefinition | None:
        """Get a step definition by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_step_index(self, step_id: str) -> int | None:
        """Get the index of a step by ID."""
        for i, step in enumerate(self.steps):
            if step.id == step_id:
                return i
        return None

    def get_next_step_id(self, current_step_id: str) -> str | None:
        """Get the next step ID in the flow."""
        current_step = self.get_step(current_step_id)
        if not current_step:
            return None

        # Check if step has explicit next_step
        if current_step.next_step:
            return current_step.next_step

        # If no explicit next_step, go to the next step in sequence
        try:
            current_index = next(
                i for i, step in enumerate(self.steps) if step.id == current_step_id
            )
            if current_index + 1 < len(self.steps):
                return self.steps[current_index + 1].id
        except (StopIteration, IndexError):
            pass

        return None

    def get_variables_dict(self) -> dict[str, Any]:
        """Convert variables list to dictionary format for initialization."""
        variables_dict = {}
        for var_def in self.variables:
            # Use default value if specified, otherwise use appropriate type default
            if var_def.default is not None:
                variables_dict[var_def.id] = var_def.default
            elif var_def.type == "bool":
                variables_dict[var_def.id] = False
            elif var_def.type == "int":
                variables_dict[var_def.id] = 0
            elif var_def.type == "str":
                variables_dict[var_def.id] = ""
            elif var_def.type == "dict":
                variables_dict[var_def.id] = {}
            elif var_def.type == "list":
                variables_dict[var_def.id] = []
            else:
                # Default to empty string for unknown types
                variables_dict[var_def.id] = ""
        return variables_dict

    def resolve_description(self, context) -> str:
        """Resolve the flow description using the provided context."""
        if not self.description:
            return ""

        try:
            return context.resolve_template(self.description)
        except Exception:
            # If template resolution fails, return the original description
            return self.description

    def validate(self) -> list[str]:
        """Validate the flow definition and return any errors."""
        errors = []

        # Validate required fields
        if not self.id:
            errors.append("Flow ID is required")
        if not self.name:
            errors.append("Flow name is required")
        if self.type != "flow":
            errors.append(f"Flow type must be 'flow', got '{self.type}'")
        if not self.steps:
            errors.append("Flow must have at least one step")

        # Validate step IDs are unique
        step_ids = [step.id for step in self.steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Step IDs must be unique within flow")

        # Validate step references
        for step in self.steps:
            if step.next_step and step.next_step not in step_ids:
                errors.append(
                    f"Step '{step.id}' references unknown next_step '{step.next_step}'"
                )

        # Validate resume points
        for resume_point in self.resume_points:
            if resume_point not in step_ids:
                errors.append(f"Resume point '{resume_point}' references unknown step")

        return errors


@dataclass
class StepResult:
    """Result of executing a flow step."""

    step_id: str
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    requires_input: bool = False
    prompt: str | None = None
    choices: list[ChoiceDefinition] = field(default_factory=list)
    next_step_id: str | None = None


@dataclass
class FlowResult:
    """Result of executing a complete flow."""

    flow_id: str
    success: bool
    outputs: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    step_results: list[StepResult] = field(default_factory=list)
    error: str | None = None
    completed_at_step: str | None = None
