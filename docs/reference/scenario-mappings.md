# Scenario Naming Consistency Implementation

**Version:** 1.0.0
**Date:** 2025-09-30
**Type:** Feature Enhancement

## Problem Statement

Users experience a disconnect between how RPA scenarios are presented in the UI documentation versus how they appear in database queries and agent responses:

- **UI Documentation**: Uses RPA codes (LM, HM, HL, HH) with descriptive names
- **Database**: Stores scenarios as technical codes (RCP45_SSP1, RCP85_SSP2, RCP85_SSP3, RCP85_SSP5)
- **Agent Responses**: Shows technical codes, not the user-friendly names users just learned

This creates cognitive friction and confusion for users trying to work with scenarios.

## Solution Overview

Implemented a **mapping layer** that:
1. Accepts both naming conventions in user queries
2. Translates to database format for execution
3. Formats results with user-friendly names

**Key Advantage**: No database schema changes required - translation happens at the application layer.

## Architecture

### Components Created

#### 1. Scenario Mapping Configuration (`src/landuse/config/scenario_mappings.py`)

**Purpose**: Centralized bidirectional mapping between database and display names.

**Key Classes**:
- `ScenarioDisplay`: NamedTuple storing full scenario information
- `ScenarioMapping`: Main mapping class with translation methods

**Core Mappings**:
```python
DB_TO_RPA = {
    'OVERALL': 'OVERALL',
    'RCP45_SSP1': 'LM',    # Lower-Moderate
    'RCP85_SSP2': 'HM',    # High-Moderate
    'RCP85_SSP3': 'HL',    # High-Low
    'RCP85_SSP5': 'HH',    # High-High
}
```

**Key Methods**:
- `get_display_name(db_name, format)`: Convert DB name to display format
- `get_db_name(user_input)`: Parse user input to DB name
- `get_scenario_info(scenario)`: Get full scenario details
- `get_sort_key(scenario_name)`: Get display order for sorting

#### 2. Response Formatter (`src/landuse/agents/response_formatter.py`)

**Purpose**: Format agent responses with user-friendly scenario names.

**Key Methods**:
- `format_scenario_in_text(text, format)`: Replace DB names in text
- `format_dataframe_scenarios(df, column, format)`: Format DataFrame scenario column
- `create_scenario_reference_table()`: Generate markdown reference
- `get_scenario_summary(scenario)`: Get concise scenario summary

#### 3. Query Executor Updates (`src/landuse/agents/query_executor.py`)

**Changes**:
- Added `translate_scenario_in_query()` method
- Updated `execute_query()` to translate before execution
- Updated result formatting to show user-friendly names

**Translation Logic**:
```python
def translate_scenario_in_query(self, query: str) -> str:
    """Translate user-friendly names to database names in SQL."""
    for rpa_code, db_name in ScenarioMapping.RPA_TO_DB.items():
        if rpa_code == 'OVERALL':
            continue
        query = query.replace(f"'{rpa_code}'", f"'{db_name}'")
    return query
```

#### 4. Agent Prompt Updates (`src/landuse/agents/prompts.py`)

**Version**: Prompt 1.2.0 (documented in `prompts/CHANGELOG.md`)

**Key Additions**:
- New "CRITICAL - SCENARIO NAMING" section
- Scenario mapping reference table
- Updated naming rules and guidelines
- Fixed incorrect scenario list (removed non-existent RCP45_SSP5 and RCP85_SSP1)

**Naming Rules**:
1. ACCEPT user queries with EITHER naming convention
2. WRITE SQL queries using database names
3. PRESENT results using user-friendly format
4. Query executor handles automatic translation

## Scenario Mapping Reference

| RPA Code | Full Name | Database Name | Description |
|----------|-----------|---------------|-------------|
| OVERALL | Ensemble Mean | OVERALL | Mean across all scenarios (default) |
| LM | Lower-Moderate | RCP45_SSP1 | Sustainability (low emissions, 2.5°C) |
| HM | High-Moderate | RCP85_SSP2 | Middle of the Road (high emissions, 4.5°C) |
| HL | High-Low | RCP85_SSP3 | Regional Rivalry (high emissions, 4.5°C) |
| HH | High-High | RCP85_SSP5 | Fossil-fueled Development (high emissions, 4.5°C) |

## Display Format Options

The `format` parameter supports multiple presentation styles:

- `'code'`: Just RPA code (e.g., "LM")
- `'name'`: Just scenario name (e.g., "Lower-Moderate")
- `'full'`: Code with name (e.g., "LM (Lower-Moderate)") **[Default]**
- `'full_technical'`: Code, name, and DB name (e.g., "LM (Lower-Moderate, RCP45_SSP1)")
- `'detailed'`: Full information including climate and growth metrics

## User Flows

### Before Implementation

1. User sees "LM (Lower-Moderate)" in documentation
2. User asks "Compare forest loss in LM vs HH"
3. Agent doesn't understand "LM" and "HH"
4. User must learn technical codes and ask again
5. Results show "RCP45_SSP1" instead of "LM"
6. User confused about mapping back to learned codes

### After Implementation

1. User sees "LM (Lower-Moderate)" in documentation
2. User asks "Compare forest loss in LM vs HH"
3. Agent automatically translates: LM → RCP45_SSP1, HH → RCP85_SSP5
4. Query executes successfully
5. Results formatted to show "LM (Lower-Moderate)" and "HH (High-High)"
6. User sees consistent naming throughout experience

## Integration Points

### Query Execution Flow

```
User Query
    ↓
Agent receives query with "LM"
    ↓
Query Executor translates "LM" → "RCP45_SSP1"
    ↓
SQL executes with database names
    ↓
Results returned with "RCP45_SSP1"
    ↓
Response Formatter converts to "LM (Lower-Moderate)"
    ↓
User sees user-friendly names
```

### DataFrame Processing

```python
# Example: Formatting query results
df = query_executor.execute_query(sql)['dataframe']
# df['scenario_name'] = ['RCP45_SSP1', 'RCP85_SSP5']

df = ResponseFormatter.format_dataframe_scenarios(df)
# df['scenario_name'] = ['LM (Lower-Moderate)', 'HH (High-High)']
```

## Backward Compatibility

✅ **Fully backward compatible**:
- Existing queries using technical names (RCP45_SSP1) continue to work
- New queries can use RPA codes (LM, HM, HL, HH)
- Mixed naming in same query supported
- No database schema changes required
- No migration scripts needed

## Testing Recommendations

### Unit Tests
```python
def test_scenario_mapping():
    assert ScenarioMapping.get_db_name('LM') == 'RCP45_SSP1'
    assert ScenarioMapping.get_display_name('RCP45_SSP1') == 'LM (Lower-Moderate)'

def test_query_translation():
    query = "SELECT * FROM dim_scenario WHERE scenario_name = 'LM'"
    translated = executor.translate_scenario_in_query(query)
    assert "'RCP45_SSP1'" in translated

def test_dataframe_formatting():
    df = pd.DataFrame({'scenario_name': ['RCP45_SSP1', 'RCP85_SSP5']})
    formatted = ResponseFormatter.format_dataframe_scenarios(df)
    assert 'LM (Lower-Moderate)' in formatted['scenario_name'].values
```

### Integration Tests
- Query with RPA codes (LM, HM, HL, HH)
- Query with technical codes (RCP45_SSP1, etc.)
- Mixed naming in same query
- Result formatting verification
- Sorting by display order

### End-to-End Tests
- Complete user workflow from question to formatted response
- Scenario comparison queries
- Geographic queries with scenarios
- Temporal analysis across scenarios

## Performance Impact

**Negligible**:
- Translation happens in-memory with simple string replacement
- Mapping lookups are O(1) dictionary operations
- No database queries added
- No significant computational overhead

## Documentation Updates

### Files Modified

1. **`src/landuse/config/scenario_mappings.py`** (NEW)
   - Comprehensive docstrings
   - Usage examples in docstrings
   - Module-level documentation

2. **`src/landuse/agents/response_formatter.py`** (NEW)
   - Complete method documentation
   - Example code in docstrings

3. **`src/landuse/agents/query_executor.py`** (MODIFIED)
   - Added translation method with documentation
   - Updated execute_query docstring

4. **`src/landuse/agents/prompts.py`** (MODIFIED)
   - Version 1.2.0
   - Comprehensive scenario naming guidance
   - Updated examples and patterns

5. **`prompts/CHANGELOG.md`** (MODIFIED)
   - Detailed version 1.2.0 entry
   - Technical impact documented
   - Integration points listed

6. **`SCENARIO_NAMING_IMPLEMENTATION.md`** (NEW)
   - This comprehensive documentation

## Migration Path

**Phase 1** (Implemented):
- ✅ Mapping layer created
- ✅ Response formatting implemented
- ✅ Query translation added
- ✅ Prompt updated to version 1.2.0
- ✅ Documentation completed

**Phase 2** (Future - Optional):
- Add `display_name` column to `dim_scenario` table
- Create database views with friendly names
- Implement user preference for naming style

**Phase 3** (Future - Optional):
- A/B test different presentation formats
- Collect user feedback on naming preference
- Consider localization for international users

## Troubleshooting

### Issue: Query still shows technical codes
**Solution**: Ensure query_executor.py changes are applied and Response Formatter is imported

### Issue: User-friendly names not recognized
**Solution**: Check ScenarioMapping.get_db_name() for supported input formats

### Issue: Results not sorted correctly
**Solution**: Use `sort=True` parameter in `format_dataframe_scenarios()`

### Issue: Mixed case sensitivity problems
**Solution**: ScenarioMapping handles case-insensitive matching automatically

## Version Control

### Schema Version
- **Current**: 2.2.0
- **This Change**: No schema version bump (no database changes)

### Prompt Version
- **Previous**: 1.1.0
- **Current**: 1.2.0
- **Changelog**: `prompts/CHANGELOG.md`

### Application Version
- Update in next release notes
- Tag as minor version bump (new feature, backward compatible)

## Future Enhancements

1. **User Preferences**: Allow users to choose display format (code, name, full)
2. **Localization**: Support for non-English scenario names
3. **Theme Names**: Consider adding theme names ("Taking the Green Road")
4. **Visualization**: Color coding for different scenarios in charts
5. **Smart Suggestions**: Autocomplete for scenario names in UI
6. **Help Command**: `/scenarios` command to show mapping table
7. **Admin Config**: Allow administrators to customize display formats

## Summary

This implementation successfully resolves the scenario naming disconnect while:
- ✅ Maintaining zero database schema changes
- ✅ Preserving full backward compatibility
- ✅ Adding negligible performance overhead
- ✅ Improving user experience significantly
- ✅ Following clean architecture principles
- ✅ Providing comprehensive documentation
- ✅ Supporting future extensibility

The mapping layer approach provides maximum flexibility while minimizing technical debt and migration complexity.