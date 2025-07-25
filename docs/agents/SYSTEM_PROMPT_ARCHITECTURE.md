# Where and How the System Prompt is Stored

## Location

The system prompt is **not stored in a separate file**. Instead, it's dynamically generated within the `agent.py` file by the `_get_system_prompt()` method (lines 391-429).

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  agent.py                        │
│                                                  │
│  def _get_system_prompt(self, include_maps):    │
│      ┌─────────────────────────────────┐        │
│      │  Base Prompt (hardcoded)        │        │
│      │  - Role definition              │        │
│      │  - Instructions                 │        │
│      │  - Query patterns               │        │
│      └──────────────┬──────────────────┘        │
│                     │                            │
│      ┌──────────────▼──────────────────┐        │
│      │  Dynamic Content                │        │
│      │  - {self.schema_info}           │◄───────┼── From SCHEMA_INFO_TEMPLATE
│      │  - DEFAULT_ASSUMPTIONS          │◄───────┼── From constants.py
│      │  - State codes                  │        │
│      └──────────────┬──────────────────┘        │
│                     │                            │
│      ┌──────────────▼──────────────────┐        │
│      │  Conditional Content            │        │
│      │  - Map generation instructions  │        │
│      │  (if include_maps=True)        │        │
│      └─────────────────────────────────┘        │
└─────────────────────────────────────────────────┘
```

## System Prompt Structure

### 1. **Base Prompt** (Hardcoded in method)
```python
"""You are a specialized Landuse Data Analyst AI that converts natural language questions into DuckDB SQL queries.

DATABASE SCHEMA:
{self.schema_info}  # <-- Injected from constants.py

INSTRUCTIONS:
1. Convert natural language questions to appropriate SQL queries
2. Use the star schema joins to get meaningful results
3. Focus on relevant metrics (acres, transitions, geographic patterns)
4. Add meaningful ORDER BY clauses
5. Include appropriate LIMIT clauses
6. Explain the business meaning of results

DEFAULT ASSUMPTIONS (when user doesn't specify):
- Scenarios: Average across all scenarios (typical outcome)
- Time Periods: Full range 2012-2100
- Geographic Scope: All states/counties
- Transition Type: Focus on 'change' transitions

ALWAYS CLEARLY STATE YOUR ASSUMPTIONS in the response.

COMMON STATE CODES:
- Texas: '48', California: '06', New York: '36', Florida: '12'

QUERY PATTERNS:
- "Agricultural land loss" → Agriculture → non-Agriculture transitions
- "Forest loss" → Forest → non-Forest transitions
- "Urbanization" → Any → Urban transitions"""
```

### 2. **Dynamic Schema Section**
- `{self.schema_info}` is populated from `SCHEMA_INFO_TEMPLATE` in constants.py
- Contains the full database schema description
- Updated with actual table counts during initialization

### 3. **Optional Map Section** (Conditional)
```python
if include_maps:
    base_prompt += """

MAP GENERATION:
When results include geographic data (state_code), consider creating choropleth maps to visualize patterns.
Use the create_choropleth_map tool when appropriate."""
```

## How It's Used

```python
# In _agent_node method:
def _agent_node(self, state: LanduseAgentState) -> dict:
    # Get system prompt with current state
    system_prompt = self._get_system_prompt(state.get("include_maps", False))
    
    # Use it with the LLM
    response = self.llm.bind_tools(self.tools).invoke([
        {"role": "system", "content": system_prompt},
        *messages
    ])
```

## Why This Design?

### Advantages:
1. **Dynamic Generation**: Can adjust based on agent configuration
2. **Incorporates Live Data**: Uses actual schema info with table counts
3. **Conditional Features**: Adds map instructions only when needed
4. **Single Source**: No separate prompt file to maintain

### Disadvantages:
1. **Harder to Find**: Not immediately obvious where prompt lives
2. **Mixed with Code**: Business logic mixed with implementation
3. **Harder to Version**: Can't track prompt changes separately

## Relationship to Constants

The system prompt pulls from constants.py:
- **SCHEMA_INFO_TEMPLATE** → Becomes `{self.schema_info}`
- **DEFAULT_ASSUMPTIONS** → Referenced but hardcoded in prompt
- **STATE_NAMES** → Sample codes hardcoded in prompt

## Customization Options

To modify the system prompt:

1. **Edit the method directly** in `agent.py`
2. **Override in a subclass**:
   ```python
   class CustomAgent(LanduseAgent):
       def _get_system_prompt(self, include_maps: bool = False) -> str:
           return "Your custom prompt here"
   ```
3. **Make it configurable** (not currently implemented):
   ```python
   # Could add to constants.py:
   SYSTEM_PROMPT_TEMPLATE = "..."
   ```

## Summary

The system prompt is:
- **Stored**: In the `_get_system_prompt()` method in `agent.py`
- **Type**: Dynamically generated string
- **Location**: Lines 391-429 of `agent.py`
- **Composition**: Base template + dynamic schema + optional features
- **Not**: In a separate file or constants.py

This design keeps the prompt close to where it's used but makes it less discoverable and harder to maintain separately from the code.