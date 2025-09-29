# Prompt Version Changelog

All notable changes to the system prompts will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- Features and improvements in development

## [1.1.0] - 2025-09-29

### New Features
- Added domain scope limitation instructions to maintain agent focus
- Implemented off-topic query rejection mechanism
- Agent now politely declines questions unrelated to land use/RPA data

### Changes
- Added IMPORTANT SCOPE LIMITATION section at the beginning of the prompt
- Defined explicit lists of allowed and prohibited topic areas
- Added standard rejection message for off-topic queries
- Included examples of appropriate vs off-topic questions

### Technical Impact
- Resolves Issue #99: Agent no longer responds to unrelated queries (stocks, weather, math, etc.)
- All off-topic query tests now pass (100% success rate)
- Maintains full compatibility with existing land use query functionality
- Improves user experience by setting clear boundaries on agent capabilities

### Testing
- Verified with prompt testing framework: `uv run python prompts/test_prompt.py --category off_topic_queries`
- All 3 off-topic query tests pass successfully
- No regression in existing land use query functionality

## [1.0.1] - 2025-09-28

### Bug Fixes
- Fixed SQL column name errors in prompt examples
  - Corrected `to_landuse` to `to_landuse_id` with proper JOIN to dim_landuse
  - Corrected `from_landuse` to `from_landuse_id` with proper JOIN to dim_landuse
- Fixed references to non-existent tables
  - Removed references to `fact_landuse_combined` (doesn't exist)
  - Removed references to `dim_scenario_combined` (doesn't exist)
  - Updated examples to use actual table names: `fact_landuse_transitions` and `dim_scenario`
- Updated SQL query examples to use proper JOINs for landuse name lookups

### Technical Impact
- Resolves production error: "Table 'f' does not have a column named 'to_landuse'"
- Ensures all SQL examples in prompt generate valid, executable queries
- Maintains backward compatibility with existing agent functionality

## [1.0.0] - 2025-09-28

### Initial Release
- Original production prompt for the landuse agent
- Comprehensive instructions for analyzing 2020 RPA Assessment database
- Support for 5 combined climate-socioeconomic scenarios
- Cross-dataset integration capabilities
- Query pattern examples and best practices
- Geographic query support with state lookups
- Socioeconomic data interpretation guidelines
- Number formatting standards

### Key Features
- **Scenarios**: OVERALL (default), RCP45_SSP1, RCP45_SSP5, RCP85_SSP1, RCP85_SSP5
- **Land Use Categories**: crop, pasture, forest, urban, rangeland
- **Time Range**: 2012-2100 projections
- **Geographic Coverage**: All US counties

### Technical Details
- Uses combined tables (dim_scenario_combined, fact_landuse_combined)
- Default scenario is OVERALL (ensemble mean)
- 2025 as baseline year for projections
- Automatic related dataset querying

## Version Guidelines

### Version Numbering
- **Major (X.0.0)**: Breaking changes to prompt structure or fundamental behavior
- **Minor (0.X.0)**: New features, capabilities, or significant improvements
- **Patch (0.0.X)**: Bug fixes, clarifications, minor adjustments

### Creating New Versions
1. Copy the latest version file in `prompts/versions/`
2. Rename with new version number (e.g., v1.1.0.py)
3. Make your changes to the prompt
4. Update metadata in the file (VERSION, RELEASE_DATE, AUTHOR, DESCRIPTION)
5. Document changes in this changelog
6. Test thoroughly before activating

### Activating Versions
To activate a new version:
```bash
echo "v1.1.0" > prompts/active_version.txt
```

Or programmatically:
```python
from prompts.prompt_manager import PromptManager
manager = PromptManager()
manager.set_active_version("v1.1.0")
```

### Rollback Procedure
If issues are detected with a new version:
```python
from prompts.prompt_manager import PromptManager
manager = PromptManager()
previous = manager.rollback()
print(f"Rolled back to {previous}")
```

## Best Practices

1. **Test Before Production**: Always test new prompts with benchmark queries
2. **Document Changes**: Clearly describe what changed and why
3. **Preserve Compatibility**: Avoid breaking existing functionality
4. **Monitor Performance**: Track metrics after deploying new versions
5. **Gradual Rollout**: Consider A/B testing for major changes