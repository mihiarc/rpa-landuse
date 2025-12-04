# Scenario Query Issue Analysis

**Date:** 2025-09-30
**Issue:** Agent can answer "compare forest change across scenarios" but NOT "compare forest change between HL and HH"

## Root Cause Analysis

### What Works
Query: "compare forest change across scenarios"
- Agent understands this as "show all scenarios"
- Generates: `SELECT scenario_name, SUM(acres) ... GROUP BY scenario_name`
- Returns all scenarios successfully

### What Doesn't Work
Query: "compare forest change between HL and HH"
- Agent sees "HL" and "HH" but doesn't recognize them as scenario codes
- Fails to generate proper WHERE clause
- Our translation layer never gets invoked because SQL generation fails

## The Real Problem

**It's not a database schema issue** - it's a **prompt engineering issue** combined with **translation logic issues**.

### Issue 1: Prompt Lacks Specific Examples

Current prompt says:
```
SCENARIO MAPPING:
- LM (Lower-Moderate) = RCP45_SSP1 = Sustainability pathway
...
```

But it doesn't have clear examples like:
```
EXAMPLE: User asks "Compare X between LM and HH"
SQL: SELECT ... WHERE scenario_name IN ('RCP45_SSP1', 'RCP85_SSP5')
```

### Issue 2: Translation Logic Fails on Generated SQL

Even if the agent generates:
```sql
WHERE scenario_name IN ('HL', 'HH')
```

Our current `translate_scenario_in_query()` only handles:
- `'LM'` (single quotes)
- `"LM"` (double quotes)

It MISSES:
- IN clauses: `IN ('HL', 'HH')`
- Array literals: `['HL', 'HH']`
- Complex patterns

## Solution Path

We need a **two-pronged approach**:

### 1. Enhanced Prompt Examples (Immediate Fix)

Add explicit query patterns to the prompt:

```python
QUERY PATTERN EXAMPLES:

User: "Compare forest change between LM and HH"
SQL: SELECT scenario_name, SUM(acres)
     FROM fact_landuse_transitions f
     JOIN dim_scenario s ON f.scenario_id = s.scenario_id
     WHERE s.scenario_name IN ('RCP45_SSP1', 'RCP85_SSP5')  -- LM and HH
     GROUP BY scenario_name

User: "Show me HL scenario forest loss"
SQL: SELECT SUM(acres)
     FROM fact_landuse_transitions f
     JOIN dim_scenario s ON f.scenario_id = s.scenario_id
     WHERE s.scenario_name = 'RCP85_SSP3'  -- HL
```

### 2. Improved Translation Logic (Critical Fix)

Enhance `translate_scenario_in_query()` to handle:

```python
def translate_scenario_in_query(self, query: str) -> str:
    """Translate with comprehensive pattern matching."""

    # Pattern 1: IN clauses - IN ('LM', 'HM')
    # Pattern 2: Single values - = 'LM'
    # Pattern 3: LIKE patterns - LIKE 'LM%'
    # Pattern 4: Array literals - ['LM', 'HM']
    # Pattern 5: Comments with codes (DON'T translate)
```

### 3. Optional: Database View (Future Enhancement)

Create a view with display names:

```sql
CREATE VIEW v_scenarios_with_display AS
SELECT
    scenario_id,
    scenario_name,
    CASE scenario_name
        WHEN 'RCP45_SSP1' THEN 'LM'
        WHEN 'RCP85_SSP2' THEN 'HM'
        WHEN 'RCP85_SSP3' THEN 'HL'
        WHEN 'RCP85_SSP5' THEN 'HH'
        ELSE 'OVERALL'
    END AS display_code,
    description
FROM dim_scenario;
```

Then agent could query:
```sql
WHERE display_code IN ('HL', 'HH')
```

## Why NOT Redesign Database Schema

**Reasons to avoid schema changes**:
1. **5.4M+ records** in fact table would need migration
2. **Breaking change** for existing code/queries
3. **Problem is solvable** at application layer
4. **Flexibility** - can change display names without schema migration
5. **Backward compatibility** - existing technical code still works

## Recommended Action Plan

### Phase 1: Fix Translation Logic (Critical)
Address PR #111 review findings:
- Fix SQL injection vulnerability in translation
- Add comprehensive pattern matching for IN clauses, etc.
- Add test coverage

### Phase 2: Enhance Prompt (High Priority)
Add explicit examples showing:
- How to query specific scenarios by RPA code
- How to compare between two specific scenarios
- WHERE clause patterns for RPA codes

### Phase 3: Add Database View (Optional Future)
If Phase 1 & 2 don't fully solve it, add:
- View with display_code column
- Documentation for agents to use the view
- Keep original table unchanged

## Test Queries to Verify Fix

```
1. "Compare forest change across scenarios" ✅ (currently works)
2. "Compare forest change between HL and HH" ❌ (currently fails)
3. "Show me LM scenario results" ❌ (likely fails)
4. "What's the difference between HM and HH?" ❌ (likely fails)
5. "Compare all scenarios" ✅ (currently works)
```

After fix, all 5 should work.