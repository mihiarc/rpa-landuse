# Combined Scenarios Integration Tests

## Overview
This directory contains integration tests for issue #67 - adding integration tests for combined scenarios with the agent system.

## Test Files Created

### 1. `test_combined_scenarios_agent.py`
Main integration test file for testing agent behavior with combined scenarios:

- **TestCombinedScenariosAgent**: Tests agent behavior with the 5-scenario structure
  - `test_agent_uses_overall_by_default`: Verifies agent uses OVERALL scenario for single queries
  - `test_agent_compares_scenarios_correctly`: Ensures scenario comparisons exclude OVERALL
  - `test_agent_handles_uncertainty_queries`: Tests access to statistical fields
  - `test_default_scenario_for_trends`: Confirms trend queries use OVERALL by default
  - `test_explicit_scenario_request`: Tests specific scenario requests work correctly
  - `test_multi_scenario_analysis`: Verifies comparison of specific scenario subsets

- **TestDatabaseViews**: Tests database views for combined scenarios
  - `test_v_default_transitions_uses_overall`: Verifies v_default_transitions uses OVERALL
  - `test_v_scenario_comparisons_excludes_overall`: Ensures comparisons exclude OVERALL
  - `test_statistical_fields_accessible`: Tests availability of uncertainty metrics

- **TestEndToEndWorkflow**: Complete workflow tests
  - `test_conversation_flow_with_combined_scenarios`: Tests realistic user conversation flow
  - `test_performance_with_combined_scenarios`: Verifies query performance (<2 seconds)

### 2. `test_combined_scenarios_implementation.py`
Implementation status and readiness tests:

- **TestCombinedScenariosImplementation**: Verifies current implementation status
  - `test_database_scenario_count`: Documents current vs expected scenario count
  - `test_check_for_overall_scenario`: Checks for OVERALL scenario existence
  - `test_check_combined_rcp_ssp_scenarios`: Verifies combined RCP-SSP scenarios
  - `test_check_database_views`: Checks for required views
  - `test_check_statistical_fields`: Verifies statistical fields for uncertainty
  - `test_agent_prompts_reference_combined_scenarios`: Confirms prompts use OVERALL

- **TestImplementationReadiness**: System readiness checks
  - `test_converter_supports_combined_scenarios`: Confirms converter has COMBINED_SCENARIOS
  - `test_agent_can_handle_queries`: Basic agent functionality test

## Current Implementation Status

### ✅ Completed
- Agent prompts configured to use OVERALL scenario as default
- Converter (`LanduseCombinedScenarioConverter`) supports 5 combined scenarios:
  - OVERALL (ensemble mean)
  - RCP45_SSP1, RCP85_SSP2, RCP85_SSP3, RCP85_SSP5
- Test framework created with comprehensive coverage

### ⚠️ Pending Implementation
- Database currently has test data, needs combined scenarios data loaded
- Views `v_default_transitions` and `v_scenario_comparisons` need to be created
- Statistical fields (std_dev, min_value, max_value) need to be added to fact table

## Running the Tests

```bash
# Run all combined scenarios tests
uv run python -m pytest tests/integration/test_combined_scenarios*.py -v

# Run specific test class
uv run python -m pytest tests/integration/test_combined_scenarios_agent.py::TestDatabaseViews -v

# Run with verbose output
uv run python -m pytest tests/integration/test_combined_scenarios_implementation.py -v -s

# Skip tests requiring API key
uv run python -m pytest tests/integration/test_combined_scenarios_agent.py::TestDatabaseViews -v
```

## Requirements for Full Testing

1. **Database with Combined Scenarios**: Run the converter to create combined scenarios:
   ```bash
   uv run python scripts/converters/convert_to_duckdb.py
   ```

2. **OpenAI API Key**: Set environment variable for agent tests:
   ```bash
   export OPENAI_API_KEY=your_api_key_here
   ```

3. **Database Views**: Create required views after loading combined scenarios data

## Test Coverage

The tests cover all requirements from issue #67:
- ✅ Default OVERALL scenario usage for single queries
- ✅ Scenario comparison queries exclude OVERALL
- ✅ Statistical fields (std_dev, min, max) accessibility
- ✅ Prompt system handles new scenarios correctly
- ✅ Database view testing (when created)
- ✅ End-to-end workflow tests
- ✅ Performance requirements (<2 seconds response time)

## Next Steps

1. Load combined scenarios data into database
2. Create database views (`v_default_transitions`, `v_scenario_comparisons`)
3. Add statistical fields to fact table
4. Run full test suite with real data and API key
5. Verify all tests pass with combined scenarios implementation