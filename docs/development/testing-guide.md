# Testing Guide

This guide covers the testing infrastructure and best practices for the Langchain Landuse project.

## Overview

The project uses **pytest** as the testing framework with comprehensive unit and integration tests for all major components.

## Quick Start

```bash
# Install dependencies (including test dependencies)
uv sync

# Run all tests
uv run python run_tests.py

# Run specific test suites
uv run python run_tests.py unit        # Unit tests only
uv run python run_tests.py integration # Integration tests only
uv run python run_tests.py security    # Security tests only
uv run python run_tests.py coverage    # Generate coverage report
```

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures and configuration
├── unit/                # Unit tests (fast, isolated)
│   ├── test_security.py # Security utilities tests
│   └── test_converters.py # Data converter tests
├── integration/         # Integration tests
│   └── test_secure_agent.py # Agent integration tests
└── fixtures/           # Test data files
```

## Running Tests

### Using the Test Runner

The `run_tests.py` script provides convenient commands:

```bash
# Run all tests with coverage
uv run python run_tests.py all

# Run only failed tests from last run
uv run python run_tests.py failed

# Run tests in parallel (faster)
uv run python run_tests.py parallel

# List available test markers
uv run python run_tests.py markers
```

### Using pytest Directly

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=scripts --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_security.py

# Run specific test function
uv run pytest tests/unit/test_security.py::TestSQLQueryValidator::test_valid_queries

# Run tests matching pattern
uv run pytest -k "security"

# Run tests with specific marker
uv run pytest -m "unit"
uv run pytest -m "integration"
uv run pytest -m "security"

# Stop on first failure
uv run pytest -x

# Drop into debugger on failure
uv run pytest --pdb

# Verbose output
uv run pytest -v
```

## Test Markers

Tests are organized with markers for easy filtering:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Tests requiring database or external resources
- `@pytest.mark.security` - Security-specific tests
- `@pytest.mark.slow` - Tests taking >5 seconds
- `@pytest.mark.requires_api` - Tests needing real API keys
- `@pytest.mark.requires_db` - Tests needing the production database

Example usage:
```python
@pytest.mark.unit
def test_sql_validation():
    """This is a unit test"""
    pass

@pytest.mark.integration
@pytest.mark.requires_db
def test_database_query():
    """This test requires a database"""
    pass
```

## Writing Tests

### Unit Tests

Unit tests should be fast and isolated:

```python
# tests/unit/test_example.py
import pytest
from scripts.utilities.security import SQLQueryValidator

class TestSQLQueryValidator:
    def test_valid_query(self):
        validator = SQLQueryValidator()
        is_valid, error = validator.validate_query("SELECT * FROM table")
        assert is_valid
        assert error is None
    
    def test_invalid_query(self):
        validator = SQLQueryValidator()
        is_valid, error = validator.validate_query("DROP TABLE users")
        assert not is_valid
        assert "DROP" in error
```

### Integration Tests

Integration tests can use the test database:

```python
# tests/integration/test_agent.py
import pytest

@pytest.mark.integration
def test_agent_query(test_database):
    """Test agent with test database"""
    from scripts.agents.secure_landuse_query_agent import SecureLanduseQueryAgent
    
    agent = SecureLanduseQueryAgent()
    result = agent.query("How many scenarios exist?")
    assert "scenarios" in result.lower()
```

### Using Fixtures

Common fixtures are defined in `conftest.py`:

```python
def test_with_database(test_database):
    """test_database fixture provides a test DuckDB instance"""
    conn = duckdb.connect(str(test_database))
    result = conn.execute("SELECT COUNT(*) FROM dim_scenario").fetchone()
    assert result[0] > 0

def test_with_config(test_config_file):
    """test_config_file provides a test .env file"""
    config = SecureConfig.from_env(test_config_file)
    assert config.openai_api_key.startswith("sk-")

def test_malicious_queries(malicious_queries):
    """malicious_queries provides SQL injection test cases"""
    validator = SQLQueryValidator()
    for query in malicious_queries:
        is_valid, _ = validator.validate_query(query)
        assert not is_valid
```

## Test Coverage

### Viewing Coverage

```bash
# Generate coverage report
uv run pytest --cov=scripts --cov-report=html

# Open HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Requirements

- Minimum coverage: 70% (configured in pytest.ini)
- Target coverage: 85%+
- Critical modules (security, agents): 90%+

### Excluding Code from Coverage

```python
def debug_function():  # pragma: no cover
    """This function is excluded from coverage"""
    pass

if __name__ == "__main__":  # pragma: no cover
    main()
```

## Testing Best Practices

### 1. Test Naming

Use descriptive test names:
```python
# Good
def test_sql_injection_with_drop_table_is_blocked():
    pass

# Bad
def test_1():
    pass
```

### 2. Test Organization

Group related tests in classes:
```python
class TestSQLValidation:
    def test_valid_queries(self):
        pass
    
    def test_invalid_queries(self):
        pass
```

### 3. Use Fixtures

Don't repeat setup code:
```python
# Good
def test_agent(test_database, mock_llm):
    agent = SecureLanduseQueryAgent()
    # ... test code

# Bad
def test_agent():
    db = create_test_database()
    llm = create_mock_llm()
    agent = SecureLanduseQueryAgent()
    # ... test code
    cleanup_database(db)
```

### 4. Test Error Cases

Always test error conditions:
```python
def test_invalid_input():
    with pytest.raises(ValueError, match="Invalid FIPS code"):
        validate_fips_code("invalid")
```

### 5. Use Mocks Appropriately

Mock external dependencies:
```python
@patch('requests.post')
def test_api_call(mock_post):
    mock_post.return_value.json.return_value = {"result": "success"}
    result = make_api_call()
    assert result == "success"
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Nightly schedule

See `.github/workflows/tests.yml` for CI configuration.

## Troubleshooting

### Common Issues

1. **Import errors**
   ```bash
   # Ensure project is in Python path
   export PYTHONPATH=$PYTHONPATH:$(pwd)
   ```

2. **Missing dependencies**
   ```bash
   # Install all dependencies including test deps
   uv sync
   ```

3. **Database not found**
   ```bash
   # Tests use a test database, not production
   # This is created automatically by fixtures
   ```

4. **API key errors**
   ```bash
   # Tests use mock API keys by default
   # For integration tests with real APIs:
   export REAL_OPENAI_API_KEY=your-key
   ```

### Debugging Tests

```bash
# Drop into debugger on failure
uv run pytest --pdb

# Show print statements
uv run pytest -s

# Very verbose output
uv run pytest -vv

# Show local variables on failure
uv run pytest -l
```

## Adding New Tests

1. Create test file in appropriate directory:
   - `tests/unit/` for unit tests
   - `tests/integration/` for integration tests

2. Import necessary modules and fixtures

3. Write test functions with descriptive names

4. Use appropriate markers

5. Run tests to ensure they pass

6. Check coverage hasn't decreased

Example:
```python
# tests/unit/test_new_feature.py
import pytest
from scripts.new_module import NewFeature

@pytest.mark.unit
class TestNewFeature:
    def test_feature_initialization(self):
        feature = NewFeature()
        assert feature is not None
    
    def test_feature_process(self):
        feature = NewFeature()
        result = feature.process("input")
        assert result == "expected output"
    
    def test_feature_error_handling(self):
        feature = NewFeature()
        with pytest.raises(ValueError):
            feature.process(None)
```

Remember: Well-tested code is maintainable code!