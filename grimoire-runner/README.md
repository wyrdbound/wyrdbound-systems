# GRIMOIRE Runner

An interactive system testing and development tool for GRIMOIRE tabletop RPG systems. This tool allows designers to execute flows, browse compendiums, test dice mechanics, and validate GRIMOIRE system definitions.

## Features

- **Flow Execution**: Run complete flows like character creation with step-by-step execution
- **Dice Integration**: Seamless integration with wyrdbound-dice for all rolling mechanics
- **Compendium Browser**: Explore and search system content with filtering
- **LLM Integration**: Use AI for content generation and rule interpretation
- **Validation**: Enhanced validation beyond basic schema checking

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Validate a system
grimoire-runner validate systems/knave_1e/

# Run a complete flow
grimoire-runner execute systems/knave_1e/ --flow character_creation

# Browse compendium content
grimoire-runner browse systems/knave_1e/ --compendium equipment

# Start interactive mode
grimoire-runner interactive systems/knave_1e/
```

## Architecture

The runner is built with a modular architecture:

- **Core Engine**: Orchestrates system loading and flow execution
- **Step Executors**: Specialized handlers for different step types (dice, choices, tables, LLM)
- **Integrations**: Clean abstractions around wyrdbound-dice, wyrdbound-rng, and LangChain
- **UI Layer**: CLI, interactive REPL, and compendium browser

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/
```

## Integration with Wyrdbound Packages

- **wyrdbound-dice**: All dice rolling operations
- **wyrdbound-rng**: Name generation during character creation
- **LangChain**: LLM-powered content generation and rule interpretation

## Usage Examples

### Programmatic Usage

```python
from grimoire_runner import GrimoireEngine

# Load system
engine = GrimoireEngine()
system = engine.load_system("systems/knave_1e/")

# Create context and run character creation
context = engine.create_execution_context()
result = engine.execute_flow("character_creation", context)

print(f"Created character: {result.outputs['knave']['name']}")
```

## License

MIT License - see LICENSE file for details.
