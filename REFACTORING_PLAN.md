# Agent Refactoring Plan

## Overview
The landuse agents have grown large (600+ lines each) with significant code duplication. This refactoring will extract common functionality into a base class and shared utilities.

## Current Issues
1. **landuse_natural_language_agent.py**: 558 lines
2. **secure_landuse_agent.py**: 620+ lines
3. **Estimated 40-50% code duplication** between agents
4. Difficult to maintain and modify
5. Hard to add new features consistently

## Refactoring Goals
1. Create a base agent class with shared functionality
2. Extract common constants and configurations
3. Reduce each agent to only its unique features
4. Improve testability and maintainability
5. Make it easier to create new agent variants

## Proposed Structure

```
src/landuse/agents/
├── __init__.py
├── base_agent.py          # New: Base class for all agents
├── constants.py           # New: Shared constants and schemas
├── formatting.py          # New: Output formatting utilities
├── landuse_natural_language_agent.py  # Simplified
├── secure_landuse_agent.py            # Simplified
└── general_data_agent.py              # Keep as is for now
```

## Implementation Steps

### Phase 1: Extract Constants
1. Create `constants.py` with:
   - SCHEMA_INFO template
   - STATE_NAMES mapping
   - DEFAULT_ASSUMPTIONS
   - QUERY_EXAMPLES

### Phase 2: Create Base Agent
1. Create `BaseLanduseAgent` class with:
   - Common initialization
   - Base `_get_schema_info()` method
   - Base `_execute_query()` method
   - Shared `chat()` interface
   - Common tool creation logic

### Phase 3: Extract Utilities
1. Create `formatting.py` with:
   - `clean_sql_query()` function
   - `format_query_results()` function
   - Table formatting helpers
   - Rich console utilities

### Phase 4: Refactor Natural Language Agent
1. Extend `BaseLanduseAgent`
2. Override only specific methods
3. Remove duplicated code
4. Target: ~200 lines

### Phase 5: Refactor Secure Agent
1. Extend `BaseLanduseAgent`
2. Add security-specific features
3. Override methods for security validation
4. Target: ~250 lines

### Phase 6: Update Tests
1. Create base agent tests
2. Update existing tests for new structure
3. Add tests for shared utilities

## Expected Benefits
1. **Code Reduction**: From ~1200 lines to ~600-700 lines total
2. **Maintainability**: Changes to shared functionality in one place
3. **Consistency**: All agents behave similarly for common features
4. **Extensibility**: Easy to create new specialized agents
5. **Testability**: Shared components can be tested independently

## Migration Strategy
1. All changes on `refactor/deduplicate-agents` branch
2. Ensure all tests pass after each phase
3. Keep backward compatibility for public APIs
4. Document any breaking changes

## Success Metrics
- [ ] 40%+ reduction in total lines of code
- [ ] All existing tests passing
- [ ] Each agent file under 300 lines
- [ ] No functional regressions
- [ ] Improved code coverage