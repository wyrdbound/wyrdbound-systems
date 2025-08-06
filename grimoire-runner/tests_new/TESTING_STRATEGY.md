# GRIMOIRE Engine Testing Strategy

## Overview

This document outlines our bottom-up, feature-isolated testing approach for the GRIMOIRE engine. The strategy focuses on building confidence through systematic testing of core functionality, starting with basic features and gradually expanding to more complex use cases.

## Testing Philosophy

### Core Principles

- **Bottom-Up Approach**: Start with fundamental components and build upward
- **Feature Isolation**: Test individual features in isolation before integration
- **Minimal Test Systems**: Use purpose-built minimal systems rather than complex real-world examples
- **Gradual Complexity**: Expand from simple use cases to complex scenarios
- **Comprehensive Coverage**: Ensure all GRIMOIRE specification features are tested

### Why This Approach Works

1. **Clear Dependencies**: Each phase builds on the previous, creating a clear dependency chain
2. **Fast Feedback**: Small, focused tests provide rapid feedback on changes
3. **Easy Debugging**: Isolated features make it easier to identify and fix issues
4. **Specification Validation**: Tests serve as executable specification documentation
5. **Regression Prevention**: Comprehensive test suite prevents breaking existing functionality

## Test Infrastructure

### Directory Structure

```
tests_new/
├── TESTING_STRATEGY.md          # This strategy document
├── conftest.py                  # Test fixtures and utilities
├── systems/                     # Minimal test systems
│   ├── minimal_basic/           # Basic system structure
│   ├── currency_test/           # Currency testing
│   ├── credits_test/            # Credits testing
│   ├── model_types/             # All attribute types
│   ├── model_inheritance/       # Model inheritance
│   └── model_validations/       # Validation rules
├── test_system_loading.py       # Phase 1.1 tests
└── test_model_definitions.py    # Phase 1.2 tests
```

### Key Utilities

- **SystemBuilder**: Programmatic test system creation
- **Test Fixtures**: Reusable test infrastructure
- **Minimal Systems**: Purpose-built systems for specific features

## Phase-by-Phase Progress

### ✅ Phase 1.1: System Definition Tests

**Status**: COMPLETED (14/14 tests passing)

**Objective**: Validate basic system loading and structure parsing

**Test Coverage**:

- Basic system loading functionality
- Required field validation (`id`, `kind`, `name`)
- Optional field handling (`description`, `version`)
- Currency definition parsing and validation
- Credits definition parsing and validation
- Edge cases and error handling
- Caching mechanisms

**Key Achievements**:

- Established solid foundation for system loading
- Validated SystemLoader core functionality
- Created minimal test systems infrastructure
- Implemented SystemBuilder utility for programmatic test creation

**Tests Added**: 14 tests across 3 test classes

- `TestBasicSystemLoading`: 7 tests
- `TestSystemDefinitionParsing`: 5 tests
- `TestSystemBuilderUtility`: 2 tests

**Notable Fixes**:

- Virtual environment configuration for consistent Python execution
- Currency weight optional field handling
- Enhanced error handling for malformed systems

---

### ✅ Phase 1.2: Model Definition Tests

**Status**: COMPLETED (26/26 tests passing, 2 skipped)

**Objective**: Comprehensive testing of model definition functionality

**Test Coverage**:

- All GRIMOIRE attribute types: `str`, `int`, `float`, `bool`, `roll`, `list`, `map`
- Attribute constraints: ranges, enums, defaults
- Model inheritance via `extends`
- Validation rules and derived attributes
- Optional attributes and edge cases
- Model references and collections
- Error handling for malformed models
- **Validation rule parsing and structure**
- **Basic validation execution (type checking, range validation)**
- **Derived attribute handling (not required in instances)**

**Key Achievements**:

- Enhanced `AttributeDefinition` class with missing `of` and `optional` fields
- Updated SystemLoader to parse all specification fields
- Validated complete model definition functionality
- Established patterns for complex attribute testing

**Tests Added**: 26 tests across 6 test classes

- `TestBasicModelLoading`: 2 tests
- `TestAttributeTypes`: 7 tests
- `TestModelInheritance`: 4 tests
- `TestValidationRules`: 3 tests
- `TestValidationExecution`: 5 tests (NEW)
- `TestModelLoadingEdgeCases`: 3 tests
- `TestModelBuilderUtility`: 2 tests

**Architecture Decisions**:

- **Kept AttributeDefinition class**: Provides type safety, validation, and IDE support over simple dictionaries
- **Hybrid approach**: YAML uses dictionaries, loader converts to structured objects
- **Comprehensive field support**: Added `of` and `optional` fields to match specification

**Critical Fixes**:

- Added missing `of` field for list/map element types
- Added missing `optional` field for nullable attributes
- Updated SystemLoader attribute parsing
- Fixed test access patterns for AttributeDefinition objects
- **Fixed derived attribute handling**: Derived attributes are no longer required in instance validation
- **Enhanced validation format**: Updated specification to use `expression` + `message` format for better documentation

---

### ✅ Phase 1.3: Compendium & Table Tests

**Status**: COMPLETED (22/22 tests passing, 1 skipped)  
**Objective**: Test compendium and table definition loading and validation

#### Test Structure:

- test_compendium_table_definitions.py ✅
  - Basic compendium loading and structure tests ✅
  - Basic table loading and structure tests ✅
  - Model validation for compendium entries ✅
  - Cross-references between models and compendiums ✅
  - Table entry type validation and cross-references ✅
  - Error handling for malformed definitions ✅

#### Focus Areas:

- **Compendium Loading**: ✅ Test compendium definition loading and validation
- **Table Loading**: ✅ Test table definition loading and validation
- **Model Integration**: ✅ Ensure compendium entries validate against their models
- **Cross-References**: ✅ Validate references between tables and compendiums
- **Error Handling**: ✅ Test malformed compendium and table definitions

#### Test Coverage:

1. **Basic Compendium Loading** (3 tests): System loading, structure validation, entry format
2. **Basic Table Loading** (4 tests): System loading, structure validation, range entries, complex objects
3. **Compendium Validation** (3 tests): Model validation, optional attributes, validation methods
4. **Table Validation** (2 tests): Validation methods, roll expression validation
5. **Integration Testing** (3 tests): Cross-system loading, entry_type references, cross-validation
6. **Error Handling** (4 tests): Entry_type validation gap, missing models, invalid expressions, empty entries
7. **Utility Functions** (2 tests): Programmatic creation helpers

#### Key Achievements:

- **Compendium System**: Full loading and validation of content collections
- **Table System**: Complete table loading with range and complex entry support
- **Model Integration**: Validated compendium entries against model constraints
- **Cross-References**: Tested table-compendium integration with entry_type validation
- **Robust Error Handling**: Comprehensive error case coverage
- **Test Infrastructure**: Created reusable minimal test systems for compendium/table testing

#### Architectural Decisions:

- **Minimal Test Systems**: Created three focused test systems (compendium_test, table_test, compendium_table_integration)
- **Separation of Concerns**: Isolated compendium testing from table testing for clarity
- **Integration Testing**: Dedicated system for testing cross-references between components
- **Programmatic Creation**: Utility tests for creating test data structures

#### Lessons Learned:

- CompendiumDefinition and TableDefinition classes handle complex validation scenarios well
- Cross-reference validation between tables and compendiums works as expected (entry IDs match)
- Roll expression validation provides helpful error messages for invalid dice expressions
- **DESIGN GAP FIXED**: `entry_type` field in tables now properly validates entry content
  - Previously, tables with `entry_type: "gear"` could contain string references without validation
  - TDD approach was used to implement proper entry_type validation
  - `TableDefinition.validate()` now detects basic type mismatches (strings/ints vs. model instances)
  - `TableDefinition.validate_with_system()` provides comprehensive model validation when system context is available
  - Fixed dice validation to use wyrdbound_dice library instead of restrictive regex patterns
  - **Result**: Enhanced type safety and better error messages for table definition issues

_Next: Flow Definition Tests_

---

### 🔄 Phase 1.4: Flow Definition Tests

**Status**: PLANNED

**Objective**: Test flow definition functionality and step validation

**Planned Coverage**:

- Flow definition structure and metadata
- Step definition types and validation
- Flow execution logic and branching
- Condition evaluation and routing
- Integration with models and compendiums

---

### 🔄 Phase 1.5: Source & Prompt Tests

**Status**: PLANNED

**Objective**: Test source and prompt definition functionality

**Planned Coverage**:

- Source definition loading and validation
- Prompt template parsing and rendering
- Dynamic content generation
- Integration with other system components

---

### 🔄 Phase 2.x: Integration Testing

**Status**: PLANNED

**Objective**: Test component interactions and full system integration

**Planned Coverage**:

- Cross-component validation
- Full system loading and execution
- Real-world scenario testing
- Performance and scalability validation

## Current Statistics

### Overall Progress

- **Total Tests**: 64 (61 passing, 3 skipped)
- **Overall Code Coverage**: 14.31% (focused on core components)
- **Phase 1.1**: 14/14 tests ✅ (System loading: 50% coverage)
- **Phase 1.2**: 26/26 tests ✅ (Model definitions: 24% coverage, 2 skipped for missing features)
- **Phase 1.3**: 22/22 tests ✅ (Tables: 39%, Compendiums: 38% coverage, 1 skipped for missing features)
- **Core Components**: Well-tested loading and validation logic
- **Architecture Validation**: Entry type validation implemented with TDD approach

### Skipped Tests (Missing Implementation)

- **Custom Validation Rules**: 2 tests skipped - expression evaluation not implemented
- **Model Validation Engine**: 1 test skipped - complete model validation not implemented
- **Derived Attribute Calculation**: Expression evaluation for derived values not implemented

These skipped tests clearly document what functionality is missing and will pass once expression evaluation is implemented.

### Test Distribution

| Component         | Tests | Status                  |
| ----------------- | ----- | ----------------------- |
| System Loading    | 14    | ✅ Complete             |
| Model Definitions | 26    | ✅ Complete (2 skipped) |
| Compendiums       | 11    | ✅ Complete (1 skipped) |
| Tables            | 11    | ✅ Complete             |
| Entry Type Fix    | 1     | ✅ Complete             |
| Flows             | 0     | 🔄 Planned              |
| Sources/Prompts   | 0     | 🔄 Planned              |
| Integration       | 0     | 🔄 Planned              |

## Quality Metrics

### Test Quality Indicators

- ✅ **Fast Execution**: All tests complete in <1 second
- ✅ **Isolated**: Each test can run independently
- ✅ **Deterministic**: Consistent results across runs
- ✅ **Comprehensive**: Cover both happy path and edge cases
- ✅ **Maintainable**: Clear structure and documentation

### Code Coverage Analysis

**Overall Coverage**: 14.31% (3,718 total statements, 3,057 uncovered)

#### Core Components Coverage (Well-Tested):

| Component              | Coverage | Status      | Lines Tested                             |
| ---------------------- | -------- | ----------- | ---------------------------------------- |
| `core/context.py`      | 100%     | ✅ Complete | All core context functionality           |
| `models/step.py`       | 100%     | ✅ Complete | Step definition models                   |
| `models/flow.py`       | 58%      | 🔄 Partial  | Flow definitions (143-175 missing)       |
| `models/system.py`     | 57%      | 🔄 Partial  | System loading (utility methods missing) |
| `models/source.py`     | 58%      | 🔄 Partial  | Source definitions (validation missing)  |
| `core/loader.py`       | 50%      | 🔄 Partial  | **Primary testing target**               |
| `models/table.py`      | 39%      | 🔄 Partial  | **Table validation tested**              |
| `models/compendium.py` | 38%      | 🔄 Partial  | **Compendium loading tested**            |
| `models/model.py`      | 24%      | 🔄 Limited  | **Model definitions tested**             |

#### Untested Components (0-15% coverage):

| Component                     | Coverage | Priority  | Reason                                 |
| ----------------------------- | -------- | --------- | -------------------------------------- |
| UI Components                 | 0%       | 🔴 Low    | Not needed for core engine testing     |
| `ui/browser.py`               | 0%       | 🔴 Low    | User interface, not core functionality |
| `ui/cli.py`                   | 0%       | 🔴 Low    | Command line interface                 |
| `ui/interactive.py`           | 0%       | 🔴 Low    | Interactive UI components              |
| `utils/logging.py`            | 0%       | 🟡 Medium | Utility, test in integration phase     |
| `utils/serialization.py`      | 0%       | 🟡 Medium | Data persistence utilities             |
| Executors                     | 5-20%    | 🟠 High   | **Next phase target (Flow testing)**   |
| `executors/flow_executor.py`  | 8%       | 🟠 High   | Core execution engine                  |
| `executors/table_executor.py` | 5%       | 🟠 High   | Table rolling functionality            |
| `integrations/`               | 15-22%   | 🟡 Medium | External service integration           |

#### Coverage Strategy:

**Current Focus** (Phases 1.1-1.3): Core loading and definition validation

- ✅ System loading: 50% coverage on critical paths
- ✅ Model definitions: 24% coverage on validation logic
- ✅ Table/Compendium: 38-39% coverage on structure validation

**Next Phase** (1.4): Flow definitions and execution

- 🎯 Target: `models/flow.py` (58% → 85%+)
- 🎯 Target: `executors/flow_executor.py` (8% → 60%+)
- 🎯 Target: `executors/base.py` (54% → 80%+)

**Future Phases**: Execution engine and integrations

- Integration testing will cover executor components
- UI components remain low priority for core engine validation

### Code Quality Improvements

- ✅ **Enhanced AttributeDefinition**: Added missing specification fields
- ✅ **Improved SystemLoader**: Better field parsing and validation
- ✅ **Architecture Validation**: Confirmed hybrid dictionary/object approach
- ✅ **Error Handling**: Robust handling of malformed input
- ✅ **Entry Type Validation**: TDD implementation with comprehensive validation

## Lessons Learned

### Successful Patterns

1. **Minimal Test Systems**: Purpose-built systems are more effective than complex examples
2. **Bottom-Up Approach**: Building foundation first prevents cascading failures
3. **Feature Isolation**: Testing individual features before integration reduces complexity
4. **Architecture Questions**: Testing revealed and resolved fundamental design decisions

### Key Insights

1. **Specification Gaps**: Testing revealed missing fields in AttributeDefinition
2. **Hybrid Approach Value**: Dictionary YAML + structured objects provides best of both worlds
3. **Test-Driven Architecture**: Tests help validate and refine architectural decisions
4. **Progressive Complexity**: Starting simple and building up reduces debugging complexity

## Next Steps

### Short Term (Phase 1.4: Flow Definition Tests)

1. **Flow Structure Testing**: Flow definition loading and validation (target: `models/flow.py` 58% → 85%+)
2. **Step Definition Testing**: Comprehensive step type validation
3. **Flow Validation Logic**: Condition evaluation and routing validation
4. **Integration Preparation**: Foundation for execution engine testing

### Short Term (Phase 1.5: Source & Prompt Tests)

1. Source definition testing and validation
2. Prompt template parsing and rendering
3. Complete core component coverage
4. **Coverage Target**: Achieve 25%+ overall coverage with core components at 60%+

### Medium Term (Phase 2.x: Integration & Execution)

1. **Expression Engine Implementation**: Currently missing custom validation rule execution
   - TODO: Implement expression evaluation for derived attributes
   - TODO: Implement custom validation rule execution
   - Priority: High (blocks full model validation)
2. **Execution Engine Testing**: Target executor components (currently 5-20% coverage)
3. Integration testing between components
4. Real-world scenario validation
5. **Coverage Target**: 40%+ overall with execution paths well-covered
6. Performance and scalability testing
7. Full GRIMOIRE specification compliance validation

### Current Technical Debt

- **🔴 HIGH PRIORITY**: Custom validation rule execution not implemented
  - ValidationRule parsing works ✅
  - Expression evaluation missing ❌
  - Tests document current limitation with clear TODOs
- **🟡 MEDIUM PRIORITY**: Derived attribute calculation not implemented
  - Derived attributes correctly marked as non-required ✅
  - Expression evaluation for derived values missing ❌## Conclusion

Our testing strategy is proving highly effective at building confidence in the GRIMOIRE engine while simultaneously improving code quality and architectural clarity. The bottom-up, feature-isolated approach allows for rapid development cycles while maintaining comprehensive coverage of the specification.

The systematic progression through phases ensures each component is thoroughly validated before building upon it, creating a solid foundation for the complete GRIMOIRE system.

---

_Last Updated: August 6, 2025_
_Current Status: Phase 1.3 Complete with Enhanced Validation Testing (61/64 tests passing, 3 skipped for missing expression evaluation)_
