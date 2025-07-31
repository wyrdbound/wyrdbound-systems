# Code Coverage Setup

This repository includes comprehensive code coverage tracking for the GRIMOIRE Runner project.

## Quick Start

### Running Tests with Coverage

```bash
# Navigate to the grimoire-runner directory
cd grimoire-runner

# Run tests with coverage (HTML and XML reports)
python -m pytest tests/ --cov=grimoire_runner --cov-report=html --cov-report=xml

# View HTML coverage report
open htmlcov/index.html
```

### Using the Coverage Scripts

```bash
# Run coverage analysis (from repo root)
./analyze_coverage.py

# Generate coverage badge info
./coverage_badge.py

# Run tests with coverage (from grimoire-runner dir)
./coverage.sh
```

## Current Coverage Status

As of the latest run:

- **Total Coverage: ~25%**
- **135 tests passing**
- **Priority areas**: UI modules, integrations, utilities

### Coverage Breakdown

#### 🔴 No Coverage (0%)

- `ui/browser` - Compendium browsing functionality
- `ui/cli` - Command-line interface
- `ui/interactive` - REPL functionality
- `ui/textual_app` - Main Textual application
- `ui/textual_browser` - Textual-based browser
- `ui/textual_executor` - Textual-based flow executor
- `integrations/rng_integration` - Random number generation
- `utils/logging` - Logging utilities
- `utils/serialization` - YAML/JSON serialization

#### 🟠 Low Coverage (< 30%)

- `executors/choice_executor` (14%)
- `models/observable` (23%)
- `executors/table_executor` (26%)
- `models/model` (26%)
- `executors/dice_executor` (28%)

#### 🟢 Good Coverage (> 70%)

- `core/loader` (79%)
- `models/flow` (78%)
- `ui/simple_textual` (78%)
- `models/system` (73%)
- `models/source` (71%)

## GitHub Actions Integration

The repository includes automated coverage reporting via GitHub Actions:

### Workflows

1. **Test and Coverage** (`.github/workflows/test-and-coverage.yml`)

   - Runs on Python 3.11 and 3.12
   - Generates coverage reports
   - Uploads HTML coverage as artifacts
   - Posts coverage summary to PR/commit
   - Posts coverage summary to PR/commit with badges

2. **Lint and Validation**
   - Code formatting (black, isort)
   - Type checking (mypy)
   - YAML validation for system files

### Artifacts

- **Coverage Reports**: HTML coverage reports available as workflow artifacts
- **Specifications**: Spec files uploaded for reference
- **Coverage XML**: XML reports for potential future integrations

## Coverage Configuration

### Files

- `pyproject.toml` - Main pytest and coverage configuration
- `.coveragerc` - Additional coverage settings
- `coverage.xml` - XML report for potential integrations
- `htmlcov/` - HTML coverage reports

### Key Settings

- **Minimum Coverage**: 25% (current baseline)
- **Branch Coverage**: Enabled for more thorough testing
- **Exclusions**: Test files, cache files, debug code
- **Reports**: Terminal, HTML, and XML formats

## Improving Coverage

### Priority Areas

1. **UI Components** (highest impact)

   - Browser functionality
   - CLI interface
   - Interactive REPL
   - Textual applications

2. **Integration Modules**

   - RNG integration (0% coverage)
   - LLM integration improvements
   - Dice integration enhancements

3. **Utility Functions**
   - Serialization utilities
   - Logging configuration
   - Template helpers

### Testing Strategies

- **Unit Tests**: For individual functions and classes
- **Integration Tests**: For component interactions
- **UI Tests**: For user interface components
- **End-to-End Tests**: For complete workflows

### Example Test Implementation

```python
# Example test for RNG integration
def test_rng_seed_handling():
    """Test that RNG seeding works correctly."""
    from grimoire_runner.integrations.rng_integration import RNGIntegration

    rng = RNGIntegration(seed=12345)
    result1 = rng.random()

    rng2 = RNGIntegration(seed=12345)
    result2 = rng2.random()

    assert result1 == result2  # Same seed = same result
```

## Contributing

When adding new features:

1. **Write tests first** (TDD approach recommended)
2. **Aim for >80% coverage** on new code
3. **Include edge cases** and error handling
4. **Test UI interactions** where applicable
5. **Update coverage docs** if adding new modules

### Running Coverage Locally

```bash
# Full coverage run with analysis
cd grimoire-runner
python -m pytest tests/ --cov=grimoire_runner --cov-report=html --cov-branch
python ../analyze_coverage.py

# Quick test run
python -m pytest tests/ --cov=grimoire_runner --cov-report=term-missing
```

## Badge and Reporting

Coverage badges are automatically generated and can be used in README files:

```markdown
![Coverage](https://img.shields.io/badge/coverage-25.0%25-orange)
```

The badge color changes based on coverage:

- 🟢 Green: 80%+
- 🟡 Yellow: 60-79%
- 🟠 Orange: 40-59%
- 🔴 Red: <40%
