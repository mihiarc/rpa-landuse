#!/usr/bin/env python3
"""
Example showing how constants.py connects to the agent functionality
"""

from landuse.agents import LanduseAgent

# When you create an agent and ask a question...
agent = LanduseAgent()

# Example 1: State name mapping
# User asks about Texas, but database uses codes
query1 = "How much urban expansion is happening in Texas?"

# The agent internally:
# 1. Recognizes "Texas" needs to be converted
# 2. Uses STATE_NAMES from constants.py: {'48': 'Texas', ...}
# 3. Generates SQL with: WHERE state_code = '48'

# Example 2: Default assumptions
# User asks a vague question
query2 = "How much forest is being lost?"

# The agent internally:
# 1. Notices no scenario specified
# 2. Uses DEFAULT_ASSUMPTIONS from constants.py:
#    - "scenarios": "Averaged across all 20 climate scenarios"
#    - "time_period": "Full range 2012-2100"
# 3. Generates SQL with appropriate AVG() and no time filters

# Example 3: Schema knowledge
# User asks about land transitions
query3 = "Show me agricultural to urban transitions"

# The agent internally:
# 1. Uses SCHEMA_INFO_TEMPLATE to understand:
#    - fact_landuse_transitions is the main table
#    - dim_landuse has landuse_category = 'Agriculture'
#    - Needs to join multiple dimension tables
# 2. Generates proper star schema SQL query

# Example 4: Query limits
# User asks for a large dataset
query4 = "Show me all county-level transitions"

# The agent internally:
# 1. Uses DB_CONFIG['max_query_limit'] = 1000
# 2. Automatically adds: LIMIT 1000
# 3. Protects against runaway queries

# Example 5: Model configuration
# During agent initialization
agent = LanduseAgent(temperature=0.5)  # Override default

# The agent internally:
# 1. Checks MODEL_CONFIG['default_temperature'] = 0.1
# 2. Uses provided value if given, otherwise uses default
# 3. Also applies MODEL_CONFIG['max_iterations'] = 5 for safety

print("""
Constants.py provides:
1. STATE_NAMES - Geographic mappings
2. SCHEMA_INFO_TEMPLATE - Database knowledge  
3. DEFAULT_ASSUMPTIONS - Query defaults
4. QUERY_EXAMPLES - SQL patterns
5. DB_CONFIG - Database settings
6. MODEL_CONFIG - LLM settings

All in one centralized location for easy maintenance!
""")