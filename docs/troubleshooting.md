# Troubleshooting Guide

Common issues and solutions when using the LangChain Land Use Analysis system.

## Installation Issues

### Python Version Error

**Problem:** `ERROR: This project requires Python 3.8+`

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.8+ if needed
# macOS: brew install python@3.11
# Ubuntu: sudo apt install python3.11
# Windows: Download from python.org
```

### uv Installation Failed

**Problem:** `uv: command not found`

**Solution:**
```bash
# Install uv
pip install uv

# Or with pipx
pipx install uv

# Verify installation
uv --version
```

### Dependency Conflicts

**Problem:** `ERROR: pip's dependency resolver found conflicts`

**Solution:**
```bash
# Clean install in fresh environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -r config/requirements.txt
```

## API Key Issues

### Missing API Key

**Problem:** `Error: OPENAI_API_KEY not found`

**Solution:**
1. Create `.env` file in `config/` directory:
   ```bash
   cd config
   cp .env.example .env
   ```

2. Add your API key:
   ```bash
   OPENAI_API_KEY=sk-...your-key-here...
   ```

3. Verify it's loaded:
   ```python
   import os
   print(os.getenv("OPENAI_API_KEY"))
   ```

### Invalid API Key

**Problem:** `Error: Incorrect API key provided`

**Solution:**
- Verify key at https://platform.openai.com/api-keys
- Ensure no extra spaces or quotes
- Check API key permissions
- Verify billing is active

### Rate Limiting

**Problem:** `Error: Rate limit exceeded`

**Solution:**
```python
# Add retry logic
import time

def retry_query(agent, query, max_retries=3):
    for i in range(max_retries):
        try:
            return agent.run(query)
        except RateLimitError:
            time.sleep(2 ** i)  # Exponential backoff
    raise Exception("Max retries exceeded")
```

## Database Issues

### Database Not Found

**Problem:** `Error: Database file not found: landuse_transitions.db`

**Solution:**
1. Check if database exists:
   ```bash
   ls data/processed/
   ```

2. If missing, create it:
   ```bash
   uv run python scripts/converters/convert_landuse_with_agriculture.py
   ```

### Database Locked

**Problem:** `sqlite3.OperationalError: database is locked`

**Solution:**
```python
# Close any open connections
conn.close()

# Or use context manager
with sqlite3.connect('database.db') as conn:
    # Operations here
    pass  # Connection closes automatically
```

### Query Errors

**Problem:** `Error executing query: no such column`

**Solution:**
1. Check table schema:
   ```
   You> Describe the landuse_transitions table
   ```

2. Verify column names:
   ```sql
   -- Correct column names
   from_land_use (not from_landuse)
   area_1000_acres (not area)
   ```

## Agent/LangChain Issues

### Agent Import Error

**Problem:** `ImportError: cannot import name 'DataEngineeringAgent'`

**Solution:**
```bash
# Ensure you're in project root
cd /path/to/langchain-landuse

# Add to Python path
export PYTHONPATH="${PYTHONPATH}:${PWD}"

# Or in Python
import sys
sys.path.append('/path/to/langchain-landuse')
```

### Tool Execution Failed

**Problem:** `Error: Tool execution failed`

**Solution:**
1. Check tool parameters:
   ```python
   # Ensure correct format
   params = {
       "file_path": "data.csv",
       "query": "SELECT * FROM data"
   }
   ```

2. Verify file permissions:
   ```bash
   ls -la data/
   chmod 644 data/*.csv
   ```

### Memory/Context Issues

**Problem:** Agent doesn't remember previous queries

**Solution:**
```python
# Ensure using same agent instance
agent = DataEngineeringAgent()

# First query
result1 = agent.run("Show tables")

# Follow-up uses same agent
result2 = agent.run("Describe the first table")  # Uses context
```

## File Operation Issues

### File Not Found

**Problem:** `Error reading file: [Errno 2] No such file or directory`

**Solution:**
1. Check file path:
   ```python
   from pathlib import Path
   
   file_path = Path("data/sample.csv")
   if file_path.exists():
       agent.run(f"Read {file_path}")
   else:
       print(f"File not found: {file_path.absolute()}")
   ```

2. Use correct relative path:
   ```
   You> Read data/sample.csv  # Correct
   You> Read sample.csv       # May fail if not in data/
   ```

### Large File Handling

**Problem:** `MemoryError` when processing large files

**Solution:**
```python
# Set file size limit
os.environ['MAX_FILE_SIZE_MB'] = '200'

# Or use streaming
agent.run("Convert large_file.json to database format")
```

### Permission Denied

**Problem:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
```bash
# Check permissions
ls -la data/

# Fix permissions
chmod 755 data/
chmod 644 data/*

# For write operations
chmod 766 data/output/
```

## Query Issues

### Natural Language Not Understood

**Problem:** Agent doesn't understand the query

**Solution:**
1. Be more specific:
   ```
   ❌ "Show stuff"
   ✅ "Show me all tables in the landuse database"
   ```

2. Use keywords:
   ```
   ✅ "forest", "urban", "transition", "scenario"
   ```

3. Break complex queries:
   ```python
   # Instead of one complex query
   # Break into steps
   agent.run("First, show me all scenarios")
   agent.run("Now compare forest area between them")
   ```

### SQL Syntax Errors

**Problem:** `Error executing query: near "FORM": syntax error`

**Solution:**
```sql
-- Common SQL fixes
FROM not FORM
WHERE not WERE  
SELECT not SELCT

-- Use agent's natural language instead
You> Show me forest transitions
# Instead of writing SQL directly
```

### No Results Returned

**Problem:** Query returns empty results

**Solution:**
1. Check filters:
   ```
   You> Remove the WHERE clause and try again
   ```

2. Verify data exists:
   ```
   You> Count total rows in the table
   ```

3. Check case sensitivity:
   ```sql
   -- Land use values are capitalized
   WHERE from_land_use = 'Forest'  -- Correct
   WHERE from_land_use = 'forest'  -- Wrong
   ```

## Performance Issues

### Slow Queries

**Problem:** Queries take too long to execute

**Solution:**
1. Add LIMIT:
   ```
   You> Show me the first 100 forest transitions
   ```

2. Use indexed columns:
   ```
   You> Filter by scenario, year, and fips first
   ```

3. Use filtered views:
   ```
   You> Query landuse_changes_only instead of landuse_transitions
   ```

### Memory Usage

**Problem:** High memory usage during processing

**Solution:**
```python
# Monitor memory
import psutil

process = psutil.Process()
print(f"Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")

# Clear large objects
del large_dataframe
import gc
gc.collect()
```

## Environment Issues

### MkDocs Port Already in Use

**Problem:** `OSError: [Errno 48] Address already in use`

**Solution:**
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use different port
mkdocs serve -a localhost:8001
```

### Virtual Environment Not Activated

**Problem:** Packages not found despite installation

**Solution:**
```bash
# Check if in virtual environment
which python
# Should show .venv/bin/python

# Activate if needed
source .venv/bin/activate

# Verify activation
echo $VIRTUAL_ENV
```

## Common Error Messages

### Error Reference Table

| Error Message | Likely Cause | Quick Fix |
|--------------|--------------|-----------|
| `KeyError: 'OPENAI_API_KEY'` | Missing API key | Add to .env file |
| `FileNotFoundError` | Wrong file path | Check path exists |
| `sqlite3.OperationalError` | Database issue | Check DB exists |
| `JSONDecodeError` | Invalid JSON | Validate JSON format |
| `AttributeError` | Wrong method name | Check API docs |
| `ConnectionError` | Network issue | Check internet |
| `TimeoutError` | Slow operation | Increase timeout |

## Getting Help

### Debugging Steps

1. **Enable verbose output:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check agent state:**
   ```python
   print(f"Root dir: {agent.root_dir}")
   print(f"Tools: {[t.name for t in agent.tools]}")
   ```

3. **Test components individually:**
   ```python
   # Test file reading
   result = agent._read_csv("test.csv")
   
   # Test database connection
   import sqlite3
   conn = sqlite3.connect("test.db")
   ```

### Resources

- **GitHub Issues**: Report bugs and get help
- **Documentation**: Check docs for examples
- **Community**: Discord/Slack channels
- **Stack Overflow**: Tag with `langchain`

### Creating Bug Reports

Include:
1. Python version
2. Package versions (`pip freeze`)
3. Error message and traceback
4. Minimal code to reproduce
5. Expected vs actual behavior

Example:
```markdown
**Environment:**
- Python 3.11.0
- langchain==0.3.0
- OS: macOS 14.0

**Error:**
```
FileNotFoundError: data.csv
```

**Code to reproduce:**
```python
agent = DataEngineeringAgent()
agent.run("Read data.csv")
```

**Expected:** File should be read
**Actual:** Error thrown
```