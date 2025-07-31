# wyrdbound-systems

[![Test and Coverage](https://github.com/wyrdbound/wyrdbound-systems/actions/workflows/test-and-coverage.yml/badge.svg)](https://github.com/wyrdbound/wyrdbound-systems/actions/workflows/test-and-coverage.yml)

This repository contains the **GRIMOIRE** specification and reference system implementations for public tabletop RPG rule definitions. GRIMOIRE (Generic Rule Implementation Model for Omniversal Interactive Roleplaying Engines) is designed to encode tabletop RPG systems in structured, machine-readable files that can be interpreted by AI Game Masters and automated tools.

## Repository Purpose

The `wyrdbound-systems` repository serves as the central hub for:

- **GRIMOIRE Specification**: The formal specification for encoding tabletop RPG systems
- **Reference Implementations**: Complete tabletop RPG systems defined in GRIMOIRE format
- **Development Tools**: Validation and utility tools for working with GRIMOIRE files
- **System Loader**: _(planned)_ Code for loading and using GRIMOIRE systems in applications

This repository supports the [Wyrdbound](https://github.com/wyrdbound/wyrdbound) AI Game Master system and other compatible engines that use GRIMOIRE-defined systems to run tabletop RPG sessions.

## Repository Structure

- **[`spec/`](spec/)** - The GRIMOIRE format specification and documentation
- **[`systems/`](systems/)** - Complete system implementations in GRIMOIRE format (typically CC or open-source systems)
- **[`tools/`](tools/)** - Validation tools and utilities for working with GRIMOIRE files
- **`src/`** - _(planned)_ Source code for loading and using GRIMOIRE systems
- **`tests/`** - _(planned)_ Test suite for the GRIMOIRE implementation

## Status

⚠️ **This repository is under active development** ⚠️

Both the GRIMOIRE specification (v0) and the system implementations are evolving. The format may change as we refine the design and gather feedback from the community.

## GRIMOIRE Specification

GRIMOIRE enables tabletop RPG systems to be defined using structured YAML files that support:

- **System Definition**: Core metadata, currency systems, and game configuration
- **Data Models**: Flexible structures for characters, items, weapons, and other game entities
- **Compendiums**: Organized collections of items, spells, monsters, and other concrete game content
- **Rule Flows**: Step-by-step mechanics for character creation, ability checks, combat resolution, and other interactions, with support for invoking Large Language Models (LLMs) for subjective decisions, dice rolling, and random generation
- **Random Tables**: Table definitions that can be either chosen from or rolled on, useful for character traits, equipment, encounters, and more
- **Source Integration**: Attribution and licensing for published materials
- **AI Prompts**: Prompt templates for LLM-assisted content generation and rule interpretation

### Specification Documentation

Detailed specifications for each component of the GRIMOIRE format can be found in the [`spec/`](spec/) directory:

- [System Definition](spec/system_spec.md) - Core system metadata and configuration
- [Model Definition](spec/model_spec.md) - Data structures for game entities
- [Flow Definition](spec/flow_spec.md) - Rule sequences and mechanics
- [Compendium Definition](spec/compendium_spec.md) - Content libraries and collections
- [Table Definition](spec/table_spec.md) - Random generation systems
- [Source Definition](spec/source_spec.md) - Attribution and licensing

## System Implementations

This repository includes reference implementations of tabletop RPG systems in GRIMOIRE format:

### **Knave 1st Edition** ([`systems/knave_1e/`](systems/knave_1e/))

A work-in-progress implementation featuring:

- Character creation flow _(complete)_
- Equipment and inventory systems _(planned)_
- Random generation tables _(in progress)_
- Content organization _(planned)_
- Combat mechanics and other flows _(planned)_

Additional systems are planned and community contributions are welcome.

## Development Tools

The repository includes validation tools to ensure GRIMOIRE files conform to the specification:

```bash
pip install -e .
grimoire-validate systems/knave_1e/
```

## Usage

GRIMOIRE systems defined in this repository can be loaded and used by compatible engines:

- **[Wyrdbound](https://github.com/wyrdbound/wyrdbound)** - Text-based AI Game Master for solo or multiplayer sessions
- **Custom implementations** - Build your own tools using the GRIMOIRE specification and system loader
- **Community engines** - Various community-developed systems that support GRIMOIRE

Systems can be distributed via:

- Local file systems (like the `systems/` folder in this repo)
- Public URLs pointing to GRIMOIRE system definitions
- Cloud storage services (e.g., S3 buckets) with appropriate access controls

## Development

### Testing and Coverage

The GRIMOIRE runner includes comprehensive test coverage to ensure reliability:

```bash
# Run tests with coverage
cd grimoire-runner
python -m pytest tests/ --cov=grimoire_runner --cov-report=html

# View HTML coverage report
open htmlcov/index.html
```

For detailed coverage information, testing strategies, and contribution guidelines, see [COVERAGE.md](COVERAGE.md).

### Key Testing Areas

- **Core Engine**: Template processing, flow execution, system loading
- **Executors**: Dice rolling, choice handling, LLM integration, table lookups
- **Models**: System validation, data structures, observable patterns
- **UI Components**: Modal interactions, browser functionality, CLI interface
- **Integration**: End-to-end system loading and execution

Current coverage areas to improve:

- UI modules (browser, CLI, interactive components)
- Integration modules (LLM, RNG integrations)
- Serialization utilities
- Logging and utility functions

### Running Tests Locally

```bash
# Install development dependencies
cd grimoire-runner
pip install -e ".[dev]"

# Run all tests
python -m pytest tests/

# Run tests with coverage and generate HTML report
python -m pytest tests/ --cov=grimoire_runner --cov-report=html --cov-report=xml

# Run specific test files
python -m pytest tests/test_templates.py -v
```

## Contributing

This repository welcomes contributions in several areas:

- **System Implementations**: Contribute new tabletop RPG systems in GRIMOIRE format
- **Specification Development**: Help refine and extend the GRIMOIRE format itself
- **Tools and Utilities**: Build better validation, conversion, or authoring tools
- **Documentation**: Improve examples, tutorials, and guides
- **Test Coverage**: Help improve test coverage in underrepresented areas

Please see our contribution guidelines and join the discussion in our community forums.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
