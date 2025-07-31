# Comprehensive UI Test Suite Documentation

## Overview

This directory contains a comprehensive test suite for the GRIMOIRE Runner UI components, covering different scenarios, edge cases, and performance testing. The tests are organized into multiple files, each focusing on specific aspects of the UI functionality.

## Test Files

### 1. `test_basic_modal.py`

**Purpose**: Basic modal functionality testing  
**Focus**: Core modal behavior patterns

**Key Tests**:

- Basic modal with callback pattern
- Modal cancellation
- Await vs callback pattern comparison
- Multiple modals in sequence
- Keyboard interactions (escape, tab navigation)
- Button focus behavior

**Coverage**: Fundamental modal operations and interaction patterns

### 2. `test_textual_ui.py`

**Purpose**: Comprehensive UI component testing  
**Focus**: All major UI components and their interactions

**Key Test Classes**:

- `TestSimpleChoiceModal`: Complete modal component testing

  - Modal creation with different choice types
  - String vs object choices
  - Single vs multiple choices
  - Confirmation with/without selection
  - Cancellation behavior
  - Multiple selection scenarios

- `TestSimpleFlowApp`: Flow application testing
  - App creation and initialization
  - UI structure validation
  - System loading and display
  - Key bindings (restart, quit)
  - Step execution and logging
  - Progress tracking
  - Restart functionality

**Coverage**: End-to-end UI component functionality

### 3. `test_ui_edge_cases.py`

**Purpose**: Edge cases and unusual scenarios  
**Focus**: Stress testing and error conditions

**Key Test Classes**:

- `TestUIEdgeCases`: Unusual input and boundary conditions

  - Very long text handling (10k+ characters)
  - Unicode and emoji support
  - Rapid modal interactions
  - Memory cleanup validation
  - Complex character sets (Chinese, Arabic, Russian)

- `TestFlowAppEdgeCases`: Flow app stress testing

  - Problematic system configurations
  - Unicode in system names
  - Rapid restart operations
  - Corrupted flow file handling

- `TestConcurrencyAndRacing`: Concurrency testing

  - Concurrent modal operations
  - State consistency under rapid interactions
  - Race condition detection

- `TestErrorRecovery`: Error handling scenarios

  - Exception handling in modals
  - Flow app recovery from errors
  - Graceful degradation

- `TestUIInteractions`: Complex interaction patterns

  - Rapid button clicking
  - Keyboard navigation testing

- `TestModalStates`: Various modal state scenarios
  - Long prompts and choice labels
  - Special characters and symbols
  - Empty and null conditions

**Coverage**: Boundary conditions, error handling, internationalization

### 4. `test_ui_performance.py`

**Purpose**: Performance and scalability testing  
**Focus**: UI performance under load

**Key Test Classes**:

- `TestUIPerformance`: Load and performance testing

  - Modal with 100+ choices
  - Rapid modal creation/destruction
  - Flow app with 50+ steps
  - Log widget with 1000+ entries
  - Memory usage tracking

- `TestUIResponseTimes`: Response time measurement

  - Button click response times
  - Keyboard navigation speed
  - Interaction latency measurement

- `TestConcurrentUIOperations`: Concurrent operation testing
  - Concurrent log writing
  - Threading and async behavior
  - UI stability under load

**Coverage**: Performance metrics, scalability, memory usage

### 5. `test_summary.py`

**Purpose**: Quick validation of core functionality  
**Focus**: Essential test subset for CI/CD

**Key Tests**: Curated subset of critical tests for fast validation

## Test Patterns and Methodologies

### 1. Callback vs Await Pattern Testing

The test suite validates that our modal system works correctly with the callback pattern, which was discovered to be more reliable than the await pattern:

```python
# Callback pattern (reliable)
self.push_screen(modal, self.handle_result)

# Await pattern (unreliable in some environments)
result = await self.push_screen(modal)
```

### 2. Unicode and Internationalization

Comprehensive testing of Unicode support:

- Emoji handling: 🧙‍♂️🎮🎲⚔️
- Multiple scripts: 中文, العربية, русский
- Special characters: ñáéíóú
- Complex combinations

### 3. Performance Benchmarking

Performance tests include timing measurements:

- Modal creation time
- Render time
- Scroll performance
- Memory usage tracking
- Response time validation

### 4. Error Recovery

Tests validate graceful error handling:

- Corrupted data files
- Invalid configurations
- Exception during UI operations
- Network/IO errors

### 5. Stress Testing

High-load scenarios:

- 100+ choice modals
- 1000+ log entries
- Rapid operations (20+ per second)
- Memory leak detection

## Running Tests

### All Tests

```bash
cd grimoire-runner
python -m pytest tests/ -v
```

### Specific Test Files

```bash
python -m pytest tests/test_basic_modal.py -v
python -m pytest tests/test_textual_ui.py -v
python -m pytest tests/test_ui_edge_cases.py -v
python -m pytest tests/test_ui_performance.py -v
```

### Quick Validation

```bash
python tests/test_summary.py
```

### Performance Tests with Output

```bash
python -m pytest tests/test_ui_performance.py -v -s
```

## Test Infrastructure

### Dependencies

- `pytest`: Test framework
- `pytest-asyncio`: Async test support
- `pytest-textual-snapshot`: Textual UI testing
- `textual`: UI framework being tested

### Mock Objects

Tests use mock objects for:

- Choice objects with id/label
- System configurations
- File system operations
- Time and performance measurements

### Test Isolation

Each test:

- Creates temporary directories
- Uses independent app instances
- Cleans up resources
- Validates state reset

## Coverage Areas

### ✅ Covered

- Basic modal operations (create, select, confirm, cancel)
- Flow app lifecycle (create, execute, restart, quit)
- Unicode and internationalization
- Performance under load
- Error handling and recovery
- Memory management
- Concurrent operations
- Keyboard navigation
- Edge cases and boundary conditions

### 🔄 Areas for Future Enhancement

- Visual regression testing
- Network operation simulation
- Plugin system testing
- Database integration testing
- Advanced accessibility testing

## Best Practices

### Writing New Tests

1. Use descriptive test names that explain the scenario
2. Include both positive and negative test cases
3. Test boundary conditions and edge cases
4. Validate error handling paths
5. Include performance considerations for UI tests
6. Use appropriate async/await patterns
7. Clean up resources properly

### Debugging Tests

1. Use `-s` flag to see print statements
2. Add `await pilot.pause()` for debugging UI state
3. Check screen stack length for modal validation
4. Use query selectors to find UI elements
5. Validate both success and failure paths

### Performance Considerations

1. UI tests can be slower than unit tests
2. Use `pilot.pause()` judiciously
3. Avoid excessive waiting
4. Test with realistic data sizes
5. Monitor memory usage in long-running tests

## Conclusion

This comprehensive test suite provides confidence in the UI components' reliability, performance, and error handling. The tests cover normal usage patterns, edge cases, performance scenarios, and error recovery, ensuring a robust user experience across different conditions and use cases.

The callback pattern breakthrough solved critical modal interaction issues, and the test suite validates this approach works correctly across all scenarios. The tests serve as both validation and documentation of expected UI behavior.
