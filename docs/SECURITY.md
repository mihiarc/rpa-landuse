# Security Guide

This document outlines the security features and best practices implemented in the Langchain Landuse Analysis System.

## Overview

The system implements multiple layers of security to protect against common vulnerabilities and ensure safe operation when processing natural language queries and database operations.

## Security Features

### 1. SQL Injection Prevention

All user-generated queries are validated before execution:

- **Query Validation**: Only SELECT statements are allowed
- **Keyword Blocking**: Dangerous SQL keywords (DROP, DELETE, etc.) are blocked
- **Comment Stripping**: SQL comments are removed to prevent comment-based attacks
- **Single Statement Enforcement**: Multiple SQL statements are not allowed

Example of blocked queries:
```sql
-- These will be rejected:
DROP TABLE dim_scenario;
SELECT * FROM users; DELETE FROM users;
SELECT * FROM users WHERE id = 1 OR '1'='1'--
```

### 2. Input Validation

All user inputs are validated and sanitized:

- **File Path Validation**: Prevents directory traversal attacks
- **Identifier Sanitization**: Database identifiers are validated against safe patterns
- **Parameter Validation**: Query parameters are type-checked and range-validated

### 3. API Key Security

API keys are handled securely throughout the system:

- **Secure Storage**: Keys stored in `.env` files (gitignored)
- **Format Validation**: Keys are validated against expected patterns
- **Masking**: Keys are masked in logs and UI output
- **No Hardcoding**: Code is scanned to prevent hardcoded secrets

### 4. Rate Limiting

Protection against API abuse:

- **Default Limit**: 60 queries per minute per user
- **Configurable**: Limits can be adjusted based on needs
- **Graceful Handling**: Clear error messages with retry information

### 5. Database Security

Database access is restricted and monitored:

- **Read-Only Access**: Agents connect with read-only permissions
- **Query Limits**: Automatic LIMIT clauses prevent data exfiltration
- **Connection Security**: Connections are properly closed after use

### 6. Logging and Auditing

Comprehensive security logging:

- **Query Logging**: All queries are logged with status
- **Access Logging**: Resource access attempts are tracked
- **Security Events**: Failed validations and rate limits are logged
- **No Sensitive Data**: Logs exclude full API keys and query results

## Configuration

### Environment Variables

Create a `config/.env` file with:

```bash
# Required (at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Security Settings
DEFAULT_QUERY_LIMIT=1000    # Max rows returned
LOG_LEVEL=INFO              # Logging verbosity
ENABLE_LOGGING=true         # Enable security logging
```

### File Permissions

On Unix-like systems, ensure proper file permissions:

```bash
chmod 600 config/.env       # Only owner can read/write
chmod 755 scripts/*.py      # Scripts are executable
```

## Usage

### Running the Secure Agent

```bash
# Run the secure setup wizard first
uv run python setup_secure_agents.py

# Then run the secure agent
uv run python scripts/agents/secure_landuse_query_agent.py
```

### Security Features in Action

When you run the secure agent, you'll see:

1. **API Key Validation**: Keys are validated on startup
2. **Query Validation**: Each query is checked before execution
3. **Rate Limiting**: Prevents excessive API usage
4. **Audit Logging**: All actions are logged

## Best Practices for Users

1. **Protect Your API Keys**
   - Never share your `.env` file
   - Don't commit API keys to version control
   - Rotate keys regularly

2. **Use Appropriate Queries**
   - Stick to analytical queries
   - Avoid trying to modify data
   - Report any security issues

3. **Monitor Usage**
   - Check logs regularly
   - Watch for unusual patterns
   - Stay within rate limits

## Security Architecture

```
┌─────────────────┐
│   User Input    │
└────────┬────────┘
         │
    ┌────▼────┐
    │Validation│  ← Rate Limiting
    └────┬────┘     Input Sanitization
         │          SQL Validation
    ┌────▼────┐
    │  Agent  │  ← Secure Config
    └────┬────┘     API Key Validation
         │
    ┌────▼────┐
    │ Database │  ← Read-Only Access
    └─────────┘     Query Limits
```

## Logging

Security logs are stored in `logs/security.log` and include:

- Query attempts (successful and blocked)
- Rate limit violations
- Invalid input attempts
- Configuration errors

Example log entry:
```
2024-01-15 10:23:45 - security - INFO - Query attempt - User: user123, Status: success, Error: None
2024-01-15 10:24:12 - security - WARNING - Blocked query from user123: DROP TABLE...
```

## Troubleshooting

### Common Security Issues

1. **"Invalid API key format"**
   - Ensure your API key matches the expected pattern
   - OpenAI: `sk-` followed by 48 characters
   - Anthropic: `sk-ant-` followed by 95 characters

2. **"Rate limit exceeded"**
   - Wait for the specified retry time
   - Consider upgrading limits if needed frequently

3. **"Query validation failed"**
   - Ensure you're only using SELECT statements
   - Remove any data modification keywords
   - Check for SQL injection patterns

### Getting Help

If you encounter security issues:

1. Check the security logs
2. Review this documentation
3. Report issues (without including sensitive data)

## Updates and Maintenance

Keep your security features up to date:

```bash
# Update dependencies
uv sync

# Re-run security setup
uv run python setup_secure_agents.py

# Test security features
uv run python scripts/utilities/security.py
```

## Compliance

This system implements security best practices aligned with:

- OWASP Top 10 recommendations
- SQL injection prevention guidelines
- API security best practices
- Data protection principles

Remember: Security is a shared responsibility. Always follow best practices and report any concerns.