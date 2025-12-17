#!/usr/bin/env python3
"""
Override database configuration to use combined scenarios.
This module helps the agent use the new combined scenario tables.
"""

# Table mappings for combined scenarios
COMBINED_TABLE_MAPPINGS = {
    # Map original table names to combined versions
    'dim_scenario': 'dim_scenario_combined',
    'fact_landuse_transitions': 'fact_landuse_combined',
}

# Views to prioritize
PREFERRED_VIEWS = [
    'v_default_transitions',  # Uses OVERALL scenario
    'v_scenario_comparisons',  # Excludes OVERALL for comparisons
]

def get_combined_schema_override():
    """Return schema configuration for combined scenarios."""
    return {
        'primary_tables': {
            'scenarios': 'dim_scenario_combined',
            'transitions': 'fact_landuse_combined',
            'geography': 'dim_geography',
            'time': 'dim_time',
            'landuse': 'dim_landuse'
        },
        'views': PREFERRED_VIEWS,
        'exclude_tables': [
            'dim_scenario',  # Original scenario table
            'fact_landuse_transitions',  # Original transitions
            'dim_scenario_original',  # Backup tables
            'fact_landuse_transitions_original'
        ]
    }

def transform_query_to_combined(query: str) -> str:
    """Transform a query to use combined tables instead of original ones."""
    modified_query = query

    # Replace table names
    for original, combined in COMBINED_TABLE_MAPPINGS.items():
        # Only replace if it's a table reference, not part of another word
        modified_query = modified_query.replace(f' {original} ', f' {combined} ')
        modified_query = modified_query.replace(f' {original}\n', f' {combined}\n')
        modified_query = modified_query.replace(f'FROM {original}', f'FROM {combined}')
        modified_query = modified_query.replace(f'JOIN {original}', f'JOIN {combined}')
        modified_query = modified_query.replace(f' {original},', f' {combined},')
        modified_query = modified_query.replace(f'({original})', f'({combined})')

    return modified_query

def get_scenario_guidance():
    """Return guidance for using combined scenarios."""
    return """
    IMPORTANT: Use the COMBINED scenario tables:
    - Use 'dim_scenario_combined' (5 scenarios) NOT 'dim_scenario' (20 scenarios)
    - Use 'fact_landuse_combined' NOT 'fact_landuse_transitions'
    - Use 'v_default_transitions' for queries needing default OVERALL scenario
    - Use 'v_scenario_comparisons' when comparing scenarios (excludes OVERALL)

    Available scenarios in dim_scenario_combined:
    1. OVERALL - Default ensemble mean (use for single queries)
    2. RCP45_SSP1 - Sustainability pathway
    3. RCP45_SSP5 - Fossil-fueled Development (low emissions)
    4. RCP85_SSP1 - Sustainability (high emissions)
    5. RCP85_SSP5 - Fossil-fueled Development (high emissions)
    """
