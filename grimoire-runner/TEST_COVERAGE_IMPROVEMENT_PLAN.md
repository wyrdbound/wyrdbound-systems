# Grimoire Runner Test Coverage Improvement Plan

## Executive Summary

Current test coverage: **25.33%** (1,264 lines covered out of 4,990 total)

- **135 tests passing** across 11 test files
- **Well-tested areas**: Core engine, system loader, templates, Textual UI components
- **Major gaps**: CLI interface, integrations, utilities, and several executor modules

## Coverage Analysis by Component

### ✅ Well-Covered Areas (>60% coverage)

1. **Templates System (64% coverage)**

   - Good coverage of Jinja2 template rendering
   - Variable extraction and validation working well
   - Integration with system loader tested

2. **Core System Loader (75% coverage)**

   - YAML parsing and validation well-tested
   - System caching mechanisms covered
   - Error handling for corrupted files tested

3. **Flow Models (67% coverage)**

   - Step definition parsing covered
   - Flow execution logic mostly tested
   - Variable resolution working

4. **Simple Textual UI (74% coverage)**
   - Modal dialogs well-tested
   - User interaction patterns covered
   - Basic UI components functional

### ⚠️ Moderately-Covered Areas (25-60% coverage)

1. **Core Engine (50% coverage)**

   - Basic execution flow tested
   - Missing: Advanced debugging features, breakpoints, concurrent execution edge cases
   - **Priority**: High - this is the heart of the system

2. **Dice Integration (45% coverage)**

   - Basic dice rolling covered
   - Missing: Complex dice expressions, modifier applications, error scenarios
   - **Priority**: Medium - important for RPG functionality

3. **Context Data Models (41% coverage)**

   - Basic data storage tested
   - Missing: Complex variable resolution, nested context handling
   - **Priority**: Medium - affects all execution paths

4. **LLM Integration (27% coverage)**
   - Basic structure tested
   - Missing: Actual LLM API calls, error handling, response processing
   - **Priority**: Medium - important for modern RPG tools

### ❌ Critical Coverage Gaps (0-25% coverage)

1. **CLI Interface (0% coverage) - 276 lines**

   - **Impact**: High - this is the primary user interface
   - **Missing**: Argument parsing, command execution, error reporting
   - **Priority**: CRITICAL

2. **RNG Integration (0% coverage) - 56 lines**

   - **Impact**: Medium - name generation functionality
   - **Missing**: All integration logic, fallback mechanisms
   - **Priority**: High

3. **UI Components (0% coverage) - 1,239 total lines**

   - `browser.py` (152 lines) - System browsing interface
   - `interactive.py` (222 lines) - Interactive mode
   - `textual_app.py` (206 lines) - Main application
   - `textual_browser.py` (170 lines) - UI browser
   - `textual_executor.py` (323 lines) - Step execution UI
   - **Impact**: High - these are primary user-facing components
   - **Priority**: High

4. **Utilities (0% coverage) - 145 lines**

   - `logging.py` (32 lines) - Logging infrastructure
   - `serialization.py` (113 lines) - Data serialization
   - **Impact**: Medium - supporting infrastructure
   - **Priority**: Medium

5. **Choice Executor (11% coverage) - 133 lines**
   - **Impact**: High - critical for interactive RPG flows
   - **Missing**: User choice handling, validation, result processing
   - **Priority**: High

## Improvement Strategy

### Phase 1: Critical Infrastructure (Target: 40% coverage)

**Week 1-2: CLI Interface Testing**

```python
# Priority test cases needed:
- test_cli_argument_parsing()
- test_cli_command_execution()
- test_cli_error_handling()
- test_cli_help_and_version()
- test_cli_flow_execution()
- test_cli_system_loading()
```

**Week 2-3: Choice Executor Testing**

```python
# Critical functionality tests:
- test_choice_presentation()
- test_choice_validation()
- test_choice_result_processing()
- test_choice_cancellation()
- test_choice_multi_select()
```

### Phase 2: UI Component Testing (Target: 50% coverage)

**Week 3-5: Core UI Components**

```python
# Focus areas:
- textual_executor.py - Step execution interface
- textual_app.py - Main application logic
- interactive.py - Interactive mode
- browser.py - System browser
```

**Testing Strategy for UI:**

- Mock Textual components for isolated testing
- Test UI state management without full rendering
- Focus on business logic rather than visual aspects
- Use Textual's testing utilities for integration tests

### Phase 3: Integration & Utilities (Target: 60% coverage)

**Week 5-6: Integration Modules**

```python
# RNG Integration tests:
- test_name_generation()
- test_fallback_mechanisms()
- test_integration_availability()

# Enhanced LLM Integration tests:
- test_llm_api_calls()
- test_llm_error_handling()
- test_llm_response_processing()
```

**Week 6-7: Utility Modules**

```python
# Logging tests:
- test_log_configuration()
- test_log_formatting()
- test_log_levels()

# Serialization tests:
- test_data_serialization()
- test_deserialization()
- test_serialization_errors()
```

### Phase 4: Advanced Features (Target: 70% coverage)

**Week 7-8: Engine Advanced Features**

```python
# Missing engine functionality:
- test_debugging_features()
- test_breakpoint_handling()
- test_concurrent_execution()
- test_performance_monitoring()
```

## Implementation Guidelines

### Testing Best Practices

1. **Mock External Dependencies**

   ```python
   # Example for LLM testing
   @patch('openai.ChatCompletion.create')
   def test_llm_integration(mock_openai):
       mock_openai.return_value = mock_response
       # Test integration logic
   ```

2. **Use Fixtures for Common Setup**

   ```python
   @pytest.fixture
   def sample_system():
       return SystemLoader().load_system("test_system")

   @pytest.fixture
   def execution_context():
       return ExecutionContext(system=sample_system())
   ```

3. **Test Error Paths**

   ```python
   def test_cli_invalid_arguments():
       with pytest.raises(SystemExit):
           main(["--invalid-flag"])
   ```

4. **UI Testing Strategy**
   ```python
   # For Textual UI components
   async def test_modal_interaction():
       app = SimpleFlowApp()
       async with app.run_test() as pilot:
           # Test UI interactions
           await pilot.click("#confirm-button")
           assert app.result == expected_result
   ```

### Test File Organization

Create new test files:

- `test_cli_interface.py` - CLI functionality
- `test_choice_executor_advanced.py` - Complete choice handling
- `test_ui_components.py` - Core UI components
- `test_integrations_complete.py` - All integration modules
- `test_utilities.py` - Logging and serialization

### Priority Test Cases

**Immediate (Next 2 weeks):**

1. CLI argument parsing and validation
2. Choice executor user interaction flows
3. RNG integration with fallback testing
4. Basic UI component state management

**Short-term (Next month):**

1. Complete UI component coverage
2. Advanced engine features (debugging, breakpoints)
3. LLM integration error handling
4. Serialization edge cases

**Medium-term (Next 2 months):**

1. Performance and load testing
2. Integration testing between components
3. Error recovery and resilience testing
4. Documentation and example coverage

## Expected Outcomes

**After Phase 1 (40% coverage):**

- CLI interface fully tested and reliable
- Choice execution robust and user-friendly
- Core user workflows validated

**After Phase 2 (50% coverage):**

- UI components tested and stable
- User experience predictable across interfaces
- Integration between UI and engine verified

**After Phase 3 (60% coverage):**

- All integrations working reliably
- Utility functions robust and well-tested
- Error handling comprehensive

**After Phase 4 (70% coverage):**

- Advanced features fully tested
- Performance characteristics understood
- Production-ready reliability

## Success Metrics

- **Coverage Target**: 70% overall coverage
- **Critical Path Coverage**: 90% for CLI, core engine, and choice executor
- **UI Coverage**: 60% focusing on business logic
- **Integration Coverage**: 80% for all external integrations
- **Test Performance**: All tests complete in under 2 minutes
- **Test Reliability**: Zero flaky tests, 100% pass rate

## Risk Mitigation

1. **UI Testing Complexity**: Use Textual's testing framework and focus on business logic
2. **Integration Testing**: Mock external services and test integration logic separately
3. **Performance Impact**: Run coverage tests separately from performance tests
4. **Maintenance Burden**: Write focused, maintainable tests with good documentation

This plan provides a structured approach to significantly improve test coverage while maintaining development velocity and focusing on the most critical user-facing functionality first.
