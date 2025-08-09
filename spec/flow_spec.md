# GRIMOIRE Flow Definition Specification

## Overview

GRIMOIRE Flows provide a structure for defining complex rules in tabletop RPG systems, with full support for invoking LLMs to resolve fuzzy or subjective questions. In general, Flows define those points in the game where the Game Master guides the players through a specific set of rules, such as how to create a character or perform an ability check.

Flows are defined as YAML files that describe a sequence of steps, choices, and actions that can be executed by the GRIMOIRE engine. They are designed to be system-agnostic and reusable across different tabletop RPG systems.

## File Structure

All flow definition files must follow this top-level structure:

```yaml
id: "unique_flow_identifier"
type: "flow"
name: "Human Readable Flow Name"
description: "Description of what this flow accomplishes"
version: "1.0"

inputs: []
outputs: []
variables: {}
steps: []
resume_points: []
```

### Top-Level Fields

- **`id`** (required): Unique identifier for the flow
- **`type`** (required): Must be `"flow"` to indicate this file defines a flow
- **`name`** (required): Human-readable name for the flow
- **`description`** (optional): Detailed description of the flow's purpose
- **`version`** (optional): Version number for the flow definition
- **`inputs`** (optional): Array of input parameters the flow expects
- **`outputs`** (optional): Array of output objects the flow produces
- **`variables`** (optional): Local variables used during flow execution
- **`steps`** (required): Array of steps that define the flow logic
- **`resume_points`** (optional): Array of step IDs where flow execution can be resumed

## Inputs and Outputs

### Inputs

```yaml
inputs:
  - type: "character"
    id: "existing_character"
    required: true
  - type: "string"
    id: "player_name"
    required: false
```

### Outputs

```yaml
outputs:
  - type: "character"
    id: "new_character"
    validate: true
```

Each input/output definition includes:

- **`type`**: The data type (model name, or basic types like `string`, `number`, `boolean`)
- **`id`**: Reference identifier used within the flow
- **`required`** (inputs only): Whether the input is mandatory
- **`validate`** (outputs only): Whether to run validation on the output

## Variables

Local variables provide temporary storage during flow execution:

```yaml
variables:
  hp_dice_roll: ""
  selected_items: []
  calculation_result: 0
```

Variables can be referenced using `variables.variable_name` syntax in templates.

## Steps

Steps are the core building blocks of flows. Each step has a consistent structure:

```yaml
- id: "step_identifier"
  name: "Human Readable Step Name"
  type: "step_type"
  prompt: "Text displayed to the user"
  condition: "optional_condition"
  parallel: true # optional
  actions: []
  next_step: "next_step_id" # optional
```

### Step Types

#### `dice_roll`

Performs a single dice roll.

```yaml
- id: "roll_damage"
  type: "dice_roll"
  prompt: "Roll for damage..."
  roll: "2d6+3"
  actions:
    - set_value:
        path: "outputs.damage_dealt"
        value: "{{ result }}"
```

#### `dice_sequence`

Performs multiple dice rolls in sequence.

```yaml
- id: "roll_abilities"
  type: "dice_sequence"
  sequence:
    items: ["strength", "dexterity", "constitution"]
    roll: "3d6kl1"
    actions:
      - set_value:
          path: "outputs.character.abilities.{{ item }}.bonus"
          value: "{{ result }}"
    display_as: "{{ item|title }}: {{ result }}"
```

#### `player_choice`

Presents choices to the player.

```yaml
- id: "choose_action"
  type: "player_choice"
  prompt: "What do you want to do?"
  choices:
    - id: "attack"
      label: "Attack with weapon"
      actions:
        - set_value:
            path: "variables.chosen_action"
            value: "attack"
      next_step: "resolve_attack"
    - id: "defend"
      label: "Defend and gain bonus"
      next_step: "resolve_defense"
```

Choice sources can also be dynamic:

```yaml
choice_source:
  table: "weapon_table"
  # OR
  table_from_values: "outputs.character.abilities"
  selection_count: 2
  display_format: "{{ key|title }}: +{{ value.bonus }}"
```

#### `table_roll`

Rolls on predefined tables.

```yaml
- id: "random_encounter"
  type: "table_roll"
  parallel: true
  tables:
    - table: "encounter_type_table"
      actions:
        - set_value:
            path: "variables.encounter_type"
            value: "{{ result }}"
    - table: "encounter_difficulty_table"
      count: 2 # Roll twice
      actions:
        - set_value:
            path: "variables.difficulty_modifiers"
            value: "{{ results }}"
```

#### `llm_generation`

Uses Large Language Models to generate content.

```yaml
- id: "generate_description"
  type: "llm_generation"
  condition: "llm_enabled"
  prompt_id: "character_description_prompt"
  prompt_data:
    traits: "{{ outputs.character.traits }}"
    background: "{{ outputs.character.background }}"
  llm_settings:
    provider: "anthropic"
    model: "claude-3-haiku"
    max_tokens: 200
  actions:
    - set_value:
        path: "outputs.character.description"
        value: "{{ result }}"
```

#### `player_input`

Prompts the player for text input.

```yaml
- id: "get_character_name"
  type: "player_input"
  prompt: "What is your character's name?"
  actions:
    - set_value:
        path: "outputs.character.name"
        value: "{{ result }}"
```

The player's input is available in templates as `{{ result }}`, maintaining consistency with other step types. This step type is ideal for collecting names, descriptions, or any custom text from the player.

#### `completion`

Marks the end of a flow.

```yaml
- id: "finish"
  type: "completion"
  prompt: "Character creation complete!"
  actions:
    - log_event:
        type: "character_created"
        data: "{{ outputs.new_character.name }}"
```

## Actions

Actions are operations performed during step execution. All actions use generic reference-based operations to maintain system agnosticism.

### Core Actions

#### `set_value`

Sets a value at a reference path.

```yaml
- set_value:
    path: "outputs.character.level"
    value: 1
```

#### `swap_values`

Swaps values between two reference paths.

```yaml
- swap_values:
    path1: "outputs.character.abilities.strength.bonus"
    path2: "outputs.character.abilities.dexterity.bonus"
```

#### `display_value`

Displays a model or object to the user.

```yaml
- display_value: "outputs.character"
```

#### `validate_value`

Validates a model or object.

```yaml
- validate_value: "outputs.character"
```

#### `flow_call`

Calls another flow as a sub-routine.

```yaml
- flow_call:
    flow: "add_item_to_character"
    inputs:
      character_ref: "outputs.character"
      item: "{{ selected_weapon }}"
```

#### `log_event`

Logs an event for debugging or analytics.

```yaml
- log_event:
    type: "dice_rolled"
    data: "{{ result }}"
```

## Templating

Flows use Jinja2 templating syntax for dynamic content:

- **Variables**: `{{ variables.hp_dice_roll }}`
- **References**: `{{ outputs.character.name }}`
- **Filters**: `{{ item|title }}`, `{{ value|upper }}`
- **Conditionals**: `{{ outputs.character.name || 'Unnamed Character' }}`

## Flow Control

### Step Transitions

Steps can specify their next step explicitly:

```yaml
next_step: "roll_damage"
```

Or rely on sequential execution (next step in the array).

### Conditional Execution

Steps can include conditions for execution:

```yaml
condition: "llm_enabled"
condition: "previous_choice == 'advanced_rules'"
```

### Parallel Execution

Steps can execute operations in parallel:

```yaml
parallel: true
```

This is particularly useful for:

- Multiple table rolls
- Independent dice rolls
- API calls (like LLM generation)

### Resume Points

Flows can be paused and resumed at designated points:

```yaml
resume_points: ["choose_weapon", "generate_traits", "review_character"]
```

## Design Principles

### System Agnosticism

Flows should avoid assumptions about specific model structures:

✅ **Good**: `set_value: { path: "character.health", value: 10 }`  
❌ **Bad**: `set_hit_points: 10`

### Modularity

Complex operations should be extracted into separate flows:

```yaml
- flow_call:
    flow: "add_item_to_inventory" # System-specific inventory rules
    inputs:
      character_ref: "outputs.character"
      item: "sword"
```

### Reusability

Use generic step types and actions that work across different game systems.

### Error Handling

The engine handles retries and error recovery automatically. Flows should focus on the happy path.

## Example: Complete Character Creation Flow

```yaml
id: "knave_character_creation"
type: "flow"
name: "Knave 1e Character Creation"
description: "Complete character creation process for Knave 1st Edition"
version: "1.0"

inputs: []
outputs:
  - type: "character"
    id: "new_character"
    validate: true

variables:
  hp_dice_roll: ""

steps:
  - id: "roll_abilities"
    name: "Roll Ability Scores"
    type: "dice_sequence"
    prompt: "Roll 3d6 for each ability score. The lowest die becomes your bonus."
    sequence:
      items:
        [
          "strength",
          "dexterity",
          "constitution",
          "intelligence",
          "wisdom",
          "charisma",
        ]
      roll: "3d6kl1"
      actions:
        - set_ref:
            ref: "outputs.new_character.abilities.{{ item }}.bonus"
            value: "{{ result }}"
      display_as: "{{ item|title }}: {{ result }} (bonus +{{ result }}, defense {{ result + 10 }})"

  - id: "ability_swap_choice"
    name: "Optional Ability Swap"
    type: "player_choice"
    prompt: "You may optionally swap the scores of two abilities."
    choices:
      - id: "no_swap"
        label: "Keep abilities as rolled"
        next_step: "hit_points_choice"
      - id: "swap_abilities"
        label: "Swap two ability scores"
        next_step: "swap_refs_step"

  - id: "hit_points_choice"
    name: "Hit Points Rolling Method"
    type: "player_choice"
    prompt: "Choose how to roll your starting hit points:"
    choices:
      - id: "standard_roll"
        label: "Standard roll (1d8)"
        actions:
          - set_ref:
              ref: "variables.hp_dice_roll"
              value: "1d8"
        next_step: "roll_hit_points"
      - id: "house_rule"
        label: "House rule: reroll results below 5"
        actions:
          - set_ref:
              ref: "variables.hp_dice_roll"
              value: "1d8r<5"
        next_step: "roll_hit_points"

  - id: "roll_hit_points"
    name: "Roll Hit Points"
    type: "dice_roll"
    prompt: "Rolling for hit points..."
    roll: "{{ variables.hp_dice_roll }}"
    actions:
      - set_ref:
          ref: "outputs.new_character.hit_points.max"
          value: "{{ result }}"
      - set_ref:
          ref: "outputs.new_character.hit_points.current"
          value: "{{ result }}"

  - id: "finalize_character"
    name: "Character Creation Complete"
    type: "completion"
    prompt: "Your Knave is ready for adventure!"
    actions:
      - validate_ref: "outputs.new_character"
      - set_ref:
          ref: "outputs.new_character.level"
          value: 1

resume_points: ["ability_swap_choice", "hit_points_choice"]
```

This specification provides a robust foundation for defining tabletop RPG rules as executable flows while maintaining flexibility and reusability across different game systems.
