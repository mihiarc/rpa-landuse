# Migration Guide: Switching to Secure Landuse Agent

This guide helps you migrate from the original `landuse_natural_language_agent.py` to the new secure version.

## Quick Start

```bash
# 1. Run the secure setup wizard
uv run python setup_secure_agents.py

# 2. Use the secure agent
uv run python scripts/agents/secure_landuse_agent.py
```

## What's New

### 🔒 Security Features
- **SQL Injection Prevention**: All queries are validated
- **Rate Limiting**: 60 queries/minute default
- **Secure Configuration**: Validated environment variables
- **Audit Logging**: Track all queries and access

### 🚀 Enhanced Features
- **Better Error Messages**: Clear security violation explanations
- **API Key Validation**: Ensures correct key format
- **Multi-Model Support**: Easy switching between GPT and Claude
- **Session Security**: Secure session management

## Key Differences

| Feature | Original | Secure Version |
|---------|----------|----------------|
| SQL Validation | Basic | Comprehensive |
| Rate Limiting | None | 60/minute |
| API Key Check | Runtime | Startup validation |
| Logging | Basic | Security audit trail |
| Error Handling | Generic | Specific security errors |

## Migration Steps

### 1. Update Your Environment

The secure version validates your `.env` file on startup:

```bash
# Original (minimal validation)
OPENAI_API_KEY=sk-...

# Secure (full validation)
OPENAI_API_KEY=sk-...              # Validated format
TEMPERATURE=0.1                     # Range validated
MAX_TOKENS=4000                     # Range validated
DEFAULT_QUERY_LIMIT=1000           # Security limit
LOG_LEVEL=INFO                     # For audit trail
```

### 2. Update Your Scripts

If you have scripts using the agent:

```python
# Original
from landuse_natural_language_agent import LanduseNaturalLanguageAgent
agent = LanduseNaturalLanguageAgent()

# Secure
from secure_landuse_agent import SecureLanduseAgent
agent = SecureLanduseAgent()
```

### 3. Handle New Security Errors

The secure version may reject queries that worked before:

```python
# Original: might allow dangerous queries
response = agent.query("SELECT * FROM users; DROP TABLE users;")

# Secure: will reject with clear error
response = agent.query("SELECT * FROM users; DROP TABLE users;")
# Returns: "❌ Security Error: Multiple statements not allowed"
```

## Backward Compatibility

The secure agent maintains the same interface:
- Same `query()` method
- Same `chat()` interactive mode
- Same natural language processing

## New Security Considerations

1. **Rate Limits**: Plan for rate limiting in automated scripts
2. **Query Validation**: Some complex queries may need adjustment
3. **Logging**: Security logs are created in `logs/` directory
4. **Permissions**: Ensure proper file permissions on `.env`

## Testing Your Migration

Run these tests to ensure everything works:

```bash
# 1. Test basic query
echo "How much agricultural land is being lost?" | uv run python scripts/agents/secure_landuse_agent.py

# 2. Test security (should be blocked)
echo "DROP TABLE dim_scenario" | uv run python scripts/agents/secure_landuse_agent.py

# 3. Run test suite
uv run python scripts/agents/test_landuse_agent.py
```

## Rollback Plan

If you need to temporarily revert:

```bash
# Use original agent
uv run python scripts/agents/landuse_natural_language_agent.py

# Both can coexist during migration
```

## Benefits of Migrating

✅ **Protection** from SQL injection attacks
✅ **Rate limiting** prevents API abuse  
✅ **Audit trail** for compliance
✅ **Validated configuration** prevents errors
✅ **Better error messages** for debugging

## Need Help?

- Check `logs/security.log` for detailed error information
- Review `docs/SECURITY.md` for security details
- The original agent remains available during transition

Remember: The secure version is designed to be a drop-in replacement with added protection!