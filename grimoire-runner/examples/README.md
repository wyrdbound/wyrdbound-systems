# GRIMOIRE Runner Examples

This directory contains example scripts demonstrating how to use the GRIMOIRE runner tool.

## Examples

### 1. Basic Flow Test (`basic_flow_test.py`)

Simple example showing how to load a GRIMOIRE system and execute a flow.

```bash
cd grimoire-runner/examples
python basic_flow_test.py
```

### 2. Interactive REPL (`interactive_repl.py`)

Starts an interactive REPL session for exploring GRIMOIRE systems.

```bash
cd grimoire-runner/examples
python interactive_repl.py
```

Commands available in the REPL:

- `load <system_path>` - Load a GRIMOIRE system
- `execute <flow_id>` - Execute a flow
- `context` - Show current context
- `flows` - List available flows
- `help` - Show help
- `quit` - Exit REPL

### 3. Browse Compendium (`browse_compendium.py`)

Interactive browser for exploring system compendium content.

```bash
cd grimoire-runner/examples
python browse_compendium.py
```

### 4. Advanced Flow (`advanced_flow.py`)

Advanced example showing custom context variables and detailed execution results.

```bash
cd grimoire-runner/examples
python advanced_flow.py
```

## Using with the Knave 1e System

All examples are configured to work with the Knave 1e system in the parent `wyrdbound-systems` repository. The examples assume the following directory structure:

```
wyrdbound-systems/
├── systems/
│   └── knave_1e/
│       ├── system.yaml
│       ├── flows/
│       ├── models/
│       └── compendium/
└── grimoire-runner/
    └── examples/
        ├── basic_flow_test.py
        ├── interactive_repl.py
        ├── browse_compendium.py
        └── advanced_flow.py
```

## Error Handling

The examples include proper error handling and will display helpful messages if:

- The system path is not found
- Required files are missing
- Flow execution fails
- Other runtime errors occur

## Extending the Examples

Feel free to modify these examples to:

- Use different GRIMOIRE systems
- Execute different flows
- Add custom context variables
- Implement additional functionality

Each example is self-contained and can be used as a starting point for your own applications.
