# Query Limits Analysis

## Current Configuration

### 1. Iteration Limits
- **Location**: `src/landuse/agents/constants.py`
- **Current Value**: 3 iterations
- **Applied in**: `src/landuse/agents/base_agent.py` (AgentExecutor)
- **Purpose**: Limits how many times the agent can call tools before giving up

### 2. Time Limits
- **Current Status**: NOT IMPLEMENTED
- **LangChain Support**: AgentExecutor supports `max_execution_time` parameter
- **Recommendation**: Add configurable timeout to prevent long-running queries

### 3. Query Row Limits
- **Location**: `src/landuse/agents/constants.py`
- **Current Value**: 1000 rows max
- **Applied in**: `src/landuse/agents/base_agent.py` (adds LIMIT clause)
- **Purpose**: Prevents overwhelming memory with large result sets

### 4. Rate Limiting
- **Location**: `src/landuse/utilities/security.py`
- **Current Value**: 60 calls per minute
- **Purpose**: Prevents API abuse

## Issues to Address

1. **Too Few Iterations**: 3 iterations might be insufficient for complex queries that require multiple tool calls
2. **No Time Limit**: Queries could run indefinitely without timeout protection
3. **Hard-coded Values**: Limits should be configurable via environment variables

## Proposed Changes

### 1. Increase Default Iterations
- Change from 3 to 5-10 iterations for complex queries
- Make it configurable via environment variable

### 2. Add Execution Time Limit
- Add `max_execution_time` parameter to AgentExecutor
- Default to 120 seconds (2 minutes)
- Make it configurable

### 3. Make All Limits Configurable
- Add environment variables:
  - `LANDUSE_MAX_ITERATIONS` (default: 5)
  - `LANDUSE_MAX_EXECUTION_TIME` (default: 120)
  - `LANDUSE_MAX_QUERY_ROWS` (default: 1000)
  - `LANDUSE_RATE_LIMIT_CALLS` (default: 60)
  - `LANDUSE_RATE_LIMIT_WINDOW` (default: 60)

### 4. Add Logging
- Log when limits are hit
- Provide helpful error messages

## Implementation Plan

1. Update `constants.py` to read from environment variables
2. Add `max_execution_time` to AgentExecutor initialization
3. Update documentation and .env.example
4. Add tests for limit handling
5. Add logging for debugging