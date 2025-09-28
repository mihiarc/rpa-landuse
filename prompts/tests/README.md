# Prompt Testing Framework

A comprehensive testing framework for validating AI prompt versions to ensure changes don't break existing functionality.

## Overview

The prompt testing framework provides automated testing of prompt versions against a suite of benchmark queries. It helps catch regressions, validate expected behaviors, and ensure prompt quality before deployment.

## Quick Start

### Run All Tests
```bash
# Test the active prompt version
uv run python prompts/test_prompt.py

# Test a specific version
uv run python prompts/test_prompt.py --version v1.0.1
```

### Run Specific Categories
```bash
# Test only basic queries
uv run python prompts/test_prompt.py --category basic_queries

# Test multiple categories
uv run python prompts/test_prompt.py --category edge_cases --category off_topic_queries
```

### Verbose Output
```bash
# Show detailed test results
uv run python prompts/test_prompt.py --verbose
```

### Save Results
```bash
# Save test results to JSON file
uv run python prompts/test_prompt.py --save-results
```

## Test Categories

### 1. Basic Queries (`basic_queries`)
Standard queries that should always work:
- Forest area calculations
- Urban expansion analysis
- Agricultural land loss

### 2. Scenario Comparisons (`scenario_comparisons`)
Tests for climate scenario functionality:
- RCP45 vs RCP85 comparisons
- SSP scenario differences

### 3. Geographic Queries (`geographic_queries`)
Location-based analysis tests:
- State-level queries
- County-level analysis

### 4. Temporal Queries (`temporal_queries`)
Time-based projection tests:
- Future year projections
- Long-term trend analysis

### 5. Edge Cases (`edge_cases`)
Boundary condition tests:
- Invalid state names
- Years beyond data range
- Ambiguous queries

### 6. Off-Topic Queries (`off_topic_queries`)
Queries that should be rejected:
- Stock market questions
- Weather forecasts
- General knowledge questions

### 7. Complex Queries (`complex_queries`)
Multi-factor analysis tests:
- Combined filters
- Aggregation queries

### 8. Regression Tests (`regression_tests`)
Critical bug fix validation:
- Column name fixes (v1.0.1)
- Table reference corrections

## Test Configuration

Tests are defined in `benchmark_queries.yaml` with the following structure:

```yaml
category_name:
  - name: "Test name"
    query: "The question to ask"
    expected_sql_contains:
      - "keyword1"
      - "keyword2"
    expected_response_contains:
      - "expected text"
    should_return_data: true
    critical: false  # Mark critical tests
```

### Test Attributes

- **name**: Descriptive test name
- **query**: The natural language question to test
- **expected_sql_contains**: Keywords that should appear in generated SQL
- **expected_sql_not_contains**: Keywords that should NOT appear in SQL
- **expected_response_contains**: Text that should appear in the response
- **should_return_data**: Whether the query should return data
- **should_reject**: Whether the query should be rejected (off-topic)
- **should_handle_gracefully**: Whether errors should be handled gracefully
- **critical**: Mark tests that must pass for deployment

## Adding New Tests

1. Edit `prompts/tests/benchmark_queries.yaml`
2. Add your test to the appropriate category:

```yaml
basic_queries:
  - name: "New test case"
    query: "Your test question here"
    expected_response_contains:
      - "expected"
      - "keywords"
    should_return_data: true
```

3. Run the test:
```bash
uv run python prompts/test_prompt.py --category basic_queries
```

## Understanding Results

### Pass/Fail Criteria

- ✅ **Passed**: All expectations met
- ⚠️ **Warning**: Non-critical failure
- ❌ **Failed**: Critical test failed

### Test Metrics

- **Total Tests**: Number of tests executed
- **Passed**: Tests that met all criteria
- **Failed**: Tests that didn't meet criteria
- **Critical Failures**: Failed tests marked as critical
- **Pass Rate**: Percentage of passed tests
- **Execution Time**: Total time for all tests

### Example Output

```
Test Results for v1.0.1
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Metric         ┃ Value  ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ Total Tests    │ 25     │
│ Passed         │ 22     │
│ Failed         │ 3      │
│ Pass Rate      │ 88.0%  │
│ Execution Time │ 45.2s  │
└────────────────┴────────┘

✅ Test suite PASSED
```

## Workflow Integration

### Before Deploying New Prompts

1. Create new prompt version
2. Run full test suite:
   ```bash
   uv run python prompts/test_prompt.py --version v1.0.2 --save-results
   ```
3. Review failed tests
4. Fix issues or update tests if behavior changed intentionally
5. Ensure all critical tests pass
6. Deploy when pass rate is acceptable (typically >80%)

### Continuous Testing

Run tests automatically when prompt files change:
```bash
# Watch for changes and run tests
watch -n 60 'uv run python prompts/test_prompt.py --category regression_tests'
```

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure `.env` file contains `OPENAI_API_KEY`
2. **Database Lock**: Close other connections to the database
3. **Import Errors**: Run from project root directory
4. **Timeout Issues**: Increase timeout or run fewer tests

### Debug Mode

For detailed debugging:
```bash
uv run python prompts/test_prompt.py --verbose --category edge_cases
```

## Architecture

### Components

1. **PromptTestRunner**: Main test execution engine
2. **TestResult**: Individual test result data
3. **TestSuiteResult**: Aggregate results for all tests
4. **benchmark_queries.yaml**: Test definitions
5. **test_prompt.py**: CLI entry point

### Test Flow

1. Load benchmark queries from YAML
2. Initialize agent with specified prompt version
3. Execute each query against the agent
4. Validate response against expectations
5. Aggregate results and generate report
6. Optionally save results to JSON

## Future Enhancements

- [ ] SQL extraction from agent state (needs instrumentation)
- [ ] Performance benchmarking
- [ ] Automated test generation from successful queries
- [ ] Integration with CI/CD pipeline
- [ ] Comparative analysis between versions
- [ ] Test coverage metrics

## Related Issues

- #93: Create prompt testing framework
- #99: Add off-topic rejection to prompts
- #91: File-based prompt versioning (completed)