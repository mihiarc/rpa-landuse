# Contributing Guide

Thank you for your interest in contributing to the LangChain Land Use Analysis project! This guide will help you get started.

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- uv (Python package manager)
- OpenAI API key

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/langchain-landuse.git
   cd langchain-landuse
   ```

2. **Create Virtual Environment**
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   uv pip install -r config/requirements.txt
   ```

4. **Set Up Environment**
   ```bash
   cp config/.env.example config/.env
   # Edit .env with your OpenAI API key
   ```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

### 2. Make Your Changes

Follow the coding standards and ensure your changes are well-tested.

### 3. Run Tests

```bash
# Run tests (when available)
uv run pytest

# Run linting
uv run flake8 scripts/

# Type checking
uv run mypy scripts/
```

### 4. Commit Your Changes

Use clear, descriptive commit messages:

```bash
git add .
git commit -m "feat: add natural language support for scenario comparisons"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes
- `refactor:` - Code refactoring
- `test:` - Test changes
- `chore:` - Build process or auxiliary tool changes

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Code Standards

### Python Style Guide

Follow PEP 8 with these specific guidelines:

```python
# Good: Descriptive variable names
land_use_transitions = process_data(county_data)

# Bad: Single letter variables
t = p(c)

# Good: Type hints
def calculate_area_change(
    from_area: float, 
    to_area: float
) -> Dict[str, float]:
    """Calculate the change in area between two time periods."""
    pass

# Good: Docstrings
def process_county_data(county: Dict[str, Any]) -> List[Transition]:
    """
    Process raw county data into transition records.
    
    Args:
        county: Dictionary containing county land use data
        
    Returns:
        List of Transition objects
        
    Raises:
        ValueError: If county data is invalid
    """
    pass
```

### Tool Development Guidelines

When creating new tools for the agent:

```python
def _create_new_tool(self) -> Tool:
    """Create a tool following the standard pattern."""
    return Tool(
        name="descriptive_tool_name",
        func=self._tool_implementation,
        description="Clear description of what the tool does for natural language understanding"
    )

def _tool_implementation(self, params: Union[str, Dict[str, Any]]) -> str:
    """
    Implement the tool functionality.
    
    Args:
        params: Tool parameters (handle both string and dict)
        
    Returns:
        String result for the agent to interpret
    """
    try:
        # Validate parameters
        if isinstance(params, str):
            params = self._parse_params(params)
        
        # Perform operation
        result = self._do_operation(params)
        
        # Format result
        return self._format_result(result)
        
    except Exception as e:
        return f"Error: {str(e)}"
```

### Natural Language Query Patterns

When adding query capabilities:

```python
# Support multiple phrasings
patterns = [
    "show me forest loss",
    "display forest reduction",
    "what areas lost forest",
    "forest to other land uses"
]

# Provide helpful examples
EXAMPLES = """
Natural language: "Which counties have the most urban growth?"
SQL generated: SELECT fips, SUM(area) as urban_growth 
               FROM transitions 
               WHERE to_land_use = 'Urban' 
               GROUP BY fips 
               ORDER BY urban_growth DESC
"""
```

## Adding Features

### 1. New Data Analysis Tools

To add a new analysis capability:

1. Create the tool method in `data_engineering_agent.py`
2. Add to `_create_tools()` method
3. Include parameter validation
4. Add rich output formatting
5. Document in `docs/api/tools.md`

Example:
```python
def _seasonal_analysis(self, params: Dict[str, Any]) -> str:
    """Analyze seasonal patterns in land use changes."""
    # Implementation
    pass
```

### 2. New Query Patterns

To support new types of natural language queries:

1. Identify the query pattern
2. Add examples to documentation
3. Test with the agent
4. Update query examples

### 3. New Data Formats

To support additional file formats:

1. Add read method
2. Add to format detection
3. Support in query tool
4. Add transformation support
5. Update documentation

## Testing

### Unit Tests

```python
# test_converters.py
def test_land_use_mapping():
    """Test that land use codes map correctly."""
    assert LAND_USE_MAP['cr'] == 'Crop'
    assert LAND_USE_MAP['ur'] == 'Urban'

def test_year_extraction():
    """Test year extraction from range."""
    assert extract_end_year('2020-2030') == 2030
```

### Integration Tests

```python
# test_agent_queries.py
def test_basic_query():
    """Test basic natural language query."""
    agent = DataEngineeringAgent()
    result = agent.run("List all tables")
    assert "landuse_transitions" in result
```

### Test Data

Keep test data minimal and in `tests/data/`:
```
tests/
└── data/
    ├── sample_transitions.json
    ├── test_database.db
    └── fixtures.py
```

## Documentation

### Adding Documentation

1. **API Documentation**: Update relevant files in `docs/api/`
2. **Query Examples**: Add to `docs/queries/examples.md`
3. **Use Cases**: Document in `docs/examples/use-cases.md`
4. **Docstrings**: Always include in code

### Documentation Style

```markdown
# Clear Heading

Brief description of the topic.

## Subsection

### Code Example

\```python
# Always include examples
agent.run("Your natural language query here")
\```

### Expected Output

\```
Show what users should expect to see
\```
```

## Performance Considerations

### Optimize for Large Datasets

```python
# Good: Streaming for large files
def process_large_file(file_path):
    with open(file_path, 'r') as f:
        for chunk in iter(lambda: f.read(4096), ''):
            process_chunk(chunk)

# Good: Batch database operations
def insert_batch(data, batch_size=10000):
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        cursor.executemany(sql, batch)
```

### Memory Management

```python
# Good: Clear large objects
def process_data():
    large_df = read_large_file()
    result = analyze(large_df)
    del large_df  # Explicitly free memory
    return result
```

## Pull Request Process

1. **Update Documentation**: Ensure docs reflect your changes
2. **Add Tests**: Include tests for new functionality
3. **Check Standards**: Run linting and formatting
4. **Update CHANGELOG**: Note significant changes
5. **Request Review**: Tag appropriate reviewers

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Documentation
- [ ] Code includes docstrings
- [ ] Documentation updated
- [ ] Examples added
```

## Common Development Tasks

### Adding a New Scenario

```python
# 1. Update scenario list
SCENARIOS = ['Baseline', 'High Crop Demand', 'High Forest', 'High Urban', 'New Scenario']

# 2. Update documentation
# docs/data/sources.md - Add scenario description

# 3. Test with agent
agent.run("Show me data for the New Scenario")
```

### Improving Query Performance

```python
# 1. Add appropriate index
CREATE INDEX idx_scenario_year ON landuse_transitions(scenario, year);

# 2. Update query patterns
def optimize_query(original_query):
    # Add query optimization logic
    pass
```

### Enhancing Natural Language Understanding

```python
# 1. Add synonyms
SYNONYMS = {
    'urban': ['city', 'developed', 'built'],
    'forest': ['trees', 'woodland', 'timber'],
    'agricultural': ['farming', 'ag', 'crops and pasture']
}

# 2. Improve query parsing
def parse_natural_language(query):
    # Enhanced parsing logic
    pass
```

## Getting Help

### Resources

- Project Issues: [GitHub Issues](https://github.com/yourusername/langchain-landuse/issues)
- LangChain Docs: [langchain.com](https://langchain.com)
- OpenAI API: [platform.openai.com](https://platform.openai.com)

### Communication Channels

- GitHub Issues: Bug reports and feature requests
- Discussions: General questions and ideas
- Pull Requests: Code contributions

## Code of Conduct

### Be Respectful
- Use welcoming and inclusive language
- Respect differing viewpoints and experiences
- Accept constructive criticism gracefully

### Contribute Positively
- Focus on what is best for the community
- Show empathy towards other community members
- Help others learn and grow

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS.md file
- Release notes
- Project documentation

Thank you for contributing to make land use analysis more accessible through natural language!