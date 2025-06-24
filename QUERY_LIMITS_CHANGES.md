# Query Limits Configuration Changes

## Summary

This branch implements configurable query execution limits to prevent runaway queries and improve the agent's robustness.

## Changes Made

### 1. **Constants Configuration** (`src/landuse/agents/constants.py`)
- Made limits configurable via environment variables
- Increased default max_iterations from 3 to 5
- Added new `max_execution_time` parameter (default: 120 seconds)
- Added `RATE_LIMIT_CONFIG` for rate limiting configuration

### 2. **Base Agent Updates** (`src/landuse/agents/base_agent.py`)
- Added `max_execution_time` to AgentExecutor initialization
- Enhanced error handling for iteration and time limits
- Added logging for query processing and limit violations
- Improved error messages with actionable suggestions

### 3. **Environment Variables Added**
- `LANDUSE_MAX_ITERATIONS` - Max tool calls before stopping (default: 5)
- `LANDUSE_MAX_EXECUTION_TIME` - Max seconds for query execution (default: 120)
- `LANDUSE_MAX_QUERY_ROWS` - Max rows returned by queries (default: 1000)
- `LANDUSE_DEFAULT_DISPLAY_LIMIT` - Default rows to display (default: 50)
- `LANDUSE_RATE_LIMIT_CALLS` - Max calls per time window (default: 60)
- `LANDUSE_RATE_LIMIT_WINDOW` - Time window in seconds (default: 60)

### 4. **Documentation Updates**
- Updated `.env.example` with new configuration options
- Updated `CLAUDE.md` with environment variable documentation
- Created `QUERY_LIMITS_ANALYSIS.md` with detailed analysis

### 5. **UI Improvements**
- Updated `quickstart.py` to display configured limits
- Shows current configuration in a nice table format
- Helps users understand current settings

### 6. **Test Updates**
- Updated `test_constants.py` to reflect new defaults
- Added test for `RATE_LIMIT_CONFIG`
- All tests passing

## Benefits

1. **Prevents Runaway Queries**: Queries that take too long or require too many steps are automatically stopped
2. **Better User Experience**: Clear error messages tell users how to fix issues
3. **Configurable**: All limits can be adjusted via environment variables
4. **Debugging**: Logging helps diagnose why queries fail
5. **Flexible**: Different environments can have different limits

## Example Usage

```bash
# Set custom limits
export LANDUSE_MAX_ITERATIONS=10
export LANDUSE_MAX_EXECUTION_TIME=300

# Run agent
uv run landuse-agent
```

## Error Messages

When limits are exceeded, users see helpful messages like:
- "🔄 Query required too many steps (>5). Try a simpler query or increase LANDUSE_MAX_ITERATIONS."
- "⏱️ Query took too long (>120s). Try a simpler query or increase LANDUSE_MAX_EXECUTION_TIME."

## Testing

Created `test_query_limits.py` to demonstrate limit behavior (not committed, just for testing).