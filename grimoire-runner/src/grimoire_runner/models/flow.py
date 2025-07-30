"""Flow definition models for GRIMOIRE runner."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum


class StepType(Enum):
    """Types of flow steps."""
    DICE_ROLL = "dice_roll"
    DICE_SEQUENCE = "dice_sequence"
    PLAYER_CHOICE = "player_choice"
    TABLE_ROLL = "table_roll"
    LLM_GENERATION = "llm_generation"
    COMPLETION = "completion"


@dataclass
class InputDefinition:
    """Flow input parameter definition."""
    type: str
    id: str
    required: bool = True
    description: Optional[str] = None


@dataclass
class OutputDefinition:
    """Flow output parameter definition."""
    type: str
    id: str
    validate: bool = False
    description: Optional[str] = None


@dataclass
class ChoiceDefinition:
    """Player choice option."""
    id: str
    label: str
    next_step: Optional[str] = None
    actions: List[Dict[str, Any]] = field(default_factory=list)
    reset_outputs: bool = False


@dataclass
class ActionDefinition:
    """Action that can be performed during step execution."""
    type: str  # set_value, get_value, etc.
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TableRollDefinition:
    """Table roll configuration."""
    table: str
    count: int = 1
    actions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DiceSequenceDefinition:
    """Dice sequence configuration."""
    items: List[str]
    roll: str
    actions: List[Dict[str, Any]] = field(default_factory=list)
    display_as: Optional[str] = None


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
    name: Optional[str] = None
    type: Optional[StepType] = None
    prompt: Optional[str] = None
    condition: Optional[str] = None
    parallel: bool = False
    actions: List[Dict[str, Any]] = field(default_factory=list)
    next_step: Optional[str] = None
    
    # Step-specific fields
    # For dice_roll
    roll: Optional[str] = None
    modifiers: Optional[Dict[str, Any]] = None
    
    # For dice_sequence  
    sequence: Optional[DiceSequenceDefinition] = None
    
    # For player_choice
    choices: List[ChoiceDefinition] = field(default_factory=list)
    choice_source: Optional[str] = None
    pre_actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # For table_roll
    tables: List[TableRollDefinition] = field(default_factory=list)
    
    # For llm_generation
    prompt_id: Optional[str] = None
    prompt_data: Dict[str, Any] = field(default_factory=dict)
    llm_settings: Optional[LLMSettingsDefinition] = None


@dataclass
class FlowDefinition:
    """Complete flow definition."""
    id: str
    name: str
    type: str = "flow"
    description: Optional[str] = None
    version: Optional[str] = None
    
    inputs: List[InputDefinition] = field(default_factory=list)
    outputs: List[OutputDefinition] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    steps: List[StepDefinition] = field(default_factory=list)
    resume_points: List[str] = field(default_factory=list)
    
    def get_step(self, step_id: str) -> Optional[StepDefinition]:
        """Get a step definition by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_step_index(self, step_id: str) -> Optional[int]:
        """Get the index of a step by ID."""
        for i, step in enumerate(self.steps):
            if step.id == step_id:
                return i
        return None
    
    def get_next_step_id(self, current_step_id: str) -> Optional[str]:
        """Get the next step ID in the flow."""
        current_step = self.get_step(current_step_id)
        if not current_step:
            return None
            
        # Check if step has explicit next_step
        if current_step.next_step:
            return current_step.next_step
        
        # If no explicit next_step, go to the next step in sequence
        try:
            current_index = next(i for i, step in enumerate(self.steps) if step.id == current_step_id)
            if current_index + 1 < len(self.steps):
                return self.steps[current_index + 1].id
        except (StopIteration, IndexError):
            pass
        
        return None
    
    def resolve_description(self, context) -> str:
        """Resolve the flow description using the provided context."""
        if not self.description:
            return ""
        
        try:
            return context.resolve_template(self.description)
        except Exception:
            # If template resolution fails, return the original description
            return self.description
            
        # Otherwise, get next step in sequence
        current_index = self.get_step_index(current_step_id)
        if current_index is not None and current_index + 1 < len(self.steps):
            return self.steps[current_index + 1].id
            
        return None
    
    def validate(self) -> List[str]:
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
                errors.append(f"Step '{step.id}' references unknown next_step '{step.next_step}'")
                
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
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    requires_input: bool = False
    prompt: Optional[str] = None
    choices: List[ChoiceDefinition] = field(default_factory=list)
    next_step_id: Optional[str] = None


@dataclass
class FlowResult:
    """Result of executing a complete flow."""
    flow_id: str
    success: bool
    outputs: Dict[str, Any] = field(default_factory=dict) 
    variables: Dict[str, Any] = field(default_factory=dict)
    step_results: List[StepResult] = field(default_factory=list)
    error: Optional[str] = None
    completed_at_step: Optional[str] = None
