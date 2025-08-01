# GRIMOIRE Table Definition Specification

## Overview

Table Definition files define random generation tables for creating content in tabletop RPG systems. Tables are used to randomly select traits, generate equipment, determine outcomes, or create any other randomized content during gameplay. They support various dice types and can be referenced by flows, other tables, or directly by the game engine.

Tables provide a structured way to encode the random generation mechanics that are central to many tabletop RPGs.

## File Structure

All table definition files must follow this top-level structure:

```yaml
kind: "table"
id: "table_identifier"
name: "Human Readable Table Name"
version: "1.0"
roll: "dice_expression"
description: "Description of what this table generates"
entry_type: "armor" # Optional, specifies the type of entries (e.g., "armor", "weapon", "trait")
entries: {}
```

### Top-Level Fields

- **`kind`** (required): Must be `"table"` to indicate this file defines a table
- **`id`** (required): Unique identifier for the table within the system
- **`name`** (optional): Human-readable name for display purposes
- **`version`** (optional): Version number for the table definition
- **`roll`** (required): Dice expression that determines how to roll on this table
- **`description`** (optional): Description of what the table generates or represents
- **`entries`** (required): Map of roll results to their corresponding values

## Roll Expressions

The `roll` field specifies what dice to roll when using this table:

```yaml
# Standard dice expressions
roll: "1d6"        # Roll one six-sided die
roll: "2d10"       # Roll two ten-sided dice and sum them
roll: "1d20"       # Roll one twenty-sided die
roll: "3d6"        # Roll three six-sided dice and sum them

# Dice with modifiers
roll: "1d6+3"      # Roll 1d6 and add 3
roll: "2d4-1"      # Roll 2d4 and subtract 1

# Percentile dice
roll: "1d100"      # Roll 1d100 (1-100)
roll: "d%"         # Alternative percentile notation (rolls 2d10 and interprets as 1-100)
roll: "PERC"       # Alias for percentile roll
```

### Supported Dice Types

The system supports standard tabletop RPG dice:

- **d4**: Four-sided die (1-4)
- **d6**: Six-sided die (1-6)
- **d8**: Eight-sided die (1-8)
- **d10**: Ten-sided die (1-10)
- **d12**: Twelve-sided die (1-12)
- **d20**: Twenty-sided die (1-20)
- **d100**: Percentile die (1-100)

## Entries

The entries section maps dice roll results to their corresponding values:

```yaml
entries:
  1: "Athletic"
  2: "Brawny"
  3: "Corpulent"
  4: "Delicate"
  5: "Gaunt"
  6: "Hulking"
```

### Entry Formats

#### Simple Values

```yaml
entries:
  1: "Red"
  2: "Blue"
  3: "Green"
  4: "Yellow"
```

#### Complex Objects

```yaml
entries:
  1:
    name: "Longsword"
    cost: 15
    damage: "1d8"
  2:
    name: "Dagger"
    cost: 2
    damage: "1d4"
```

#### Range Entries

For tables with large ranges, you can specify ranges:

```yaml
entries:
  1-10: "Common"
  11-18: "Uncommon"
  19-20: "Rare"
```

### Entry Keys

Entry keys must correspond to possible results of the roll expression:

```yaml
# For 1d6 roll
entries:
  1: "Result One"
  2: "Result Two"
  3: "Result Three"
  4: "Result Four"
  5: "Result Five"
  6: "Result Six"

# For 2d6 roll (results 2-12)
entries:
  2: "Snake Eyes"
  3: "Low Roll"
  # ... entries for 4-11
  12: "Boxcars"
```

## Table Types

### Trait Tables

Generate character traits, personality aspects, or physical descriptions:

```yaml
kind: "table"
id: "personality"
name: "Personality Traits"
roll: "1d20"
description: "Random personality traits for characters"
entries:
  1: "Ambitious"
  2: "Cautious"
  3: "Cheerful"
  # ...
```

### Equipment Tables

Generate random equipment, treasure, or loot:

```yaml
kind: "table"
id: "starting-gear"
name: "Starting Equipment"
roll: "1d6"
description: "Random starting equipment for new characters"
entries:
  1: { item: "sword", quantity: 1 }
  2: { item: "bow", quantity: 1, arrows: 20 }
  3: { item: "staff", quantity: 1 }
  # ...
```

### Event Tables

Generate random encounters, weather, or story events:

```yaml
kind: "table"
id: "random-encounters"
name: "Wilderness Encounters"
roll: "1d12"
description: "Random encounters while traveling"
entries:
  1: "Pack of wolves"
  2: "Traveling merchant"
  3: "Abandoned campsite"
  # ...
```

### Nested Tables

Tables can reference other tables for complex generation:

```yaml
kind: "table"
id: "magic-item"
name: "Magic Item Generator"
roll: "1d4"
entries:
  1:
    type: "weapon"
    table: "magic-weapons"
  2:
    type: "armor"
    table: "magic-armor"
  3:
    type: "potion"
    table: "potions"
  4:
    type: "scroll"
    table: "scrolls"
```

## Weighted Tables

For non-uniform probability distributions, use different dice or multiple entries:

```yaml
# Using d100 for fine-grained probability
kind: "table"
id: "treasure-rarity"
name: "Treasure Rarity"
roll: "1d100"
entries:
  1-50: "Common" # 50% chance
  51-80: "Uncommon" # 30% chance
  81-95: "Rare" # 15% chance
  96-100: "Legendary" # 5% chance
```

## Cross-References

Tables can reference other game content:

```yaml
entries:
  1:
    item_id: "longsword" # Reference to compendium entry
    condition: "worn"
  2:
    model: "weapon" # Reference to model type
    generate: true # Indicates dynamic generation needed
```

## File Naming and Location

- **Filename**: Descriptive name with `.yaml` extension
- **Location**: `tables/` subdirectory within the system directory
- **Path Pattern**: `systems/{system_id}/tables/{category}/{filename}.yaml`
- **Subdirectories**: Recommended subcategorization (e.g., `traits/`, `gear/`, `encounters/`)

## Example

```yaml
kind: "table"
id: "character-background"
name: "Character Background"
version: "1.0"
roll: "1d10"
description: "Random backgrounds for character creation"

entries:
  1: "Blacksmith"
  2: "Farmer"
  3: "Merchant"
  4: "Scholar"
  5: "Soldier"
  6: "Thief"
  7: "Hunter"
  8: "Sailor"
  9: "Herbalist"
  10: "Entertainer"
```

## Advanced Features

### Conditional Entries

Entries can include conditions for when they apply:

```yaml
entries:
  1:
    result: "Heavy Armor"
    condition: "$character.strength >= 13"
    fallback: "Light Armor"
```

### Multi-Roll Tables

Tables can specify multiple rolls:

```yaml
roll: "2d6"
reroll_on: [2, 12] # Reroll these results
entries:
  3: "Uncommon event"
  4-10: "Normal event"
  11: "Rare event"
```

### Subtables

Tables can include nested subtables:

```yaml
entries:
  1:
    result: "Weapon"
    subtable:
      roll: "1d4"
      entries:
        1: "Sword"
        2: "Axe"
        3: "Spear"
        4: "Bow"
```

## Validation Rules

1. The `kind` field must exactly match `"table"`
2. The `id` field must be unique within the system
3. The `roll` field must be a valid dice expression
4. All entry keys must be valid results for the specified dice roll
5. Entry keys must cover all possible roll results (no gaps)
6. Range entries (e.g., "1-5") must not overlap
7. Referenced tables or content must exist
8. The file must be valid YAML syntax
