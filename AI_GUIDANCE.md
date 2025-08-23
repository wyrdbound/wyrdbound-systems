# Guidelines

Always remember the following points as you are working on this code base:

1. Use the virtual env in the project root (`source .venv/bin/activate && <your_command>`)

2. Keep the engine generic. This means do not add specific information (model names, model attributes, table values, system-specific information, etc) from the specific TTRPG systems we are implementing in GRIMOIRE to the grimoire-runner.

3. Prefer to raise explicit errors when hitting issues. Do not implement fallbacks as these made the code more convoluted and tend to silence real errors.

4. Try to follow good software development practices (like SOLID). Keep things small and modular.

5. Simpler is better.

6. Use prints liberally to capture the flow of data and decisions within the code. Do not use logging, since Rich redirects stdout/stderr.
