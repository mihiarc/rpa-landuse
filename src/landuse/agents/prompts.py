#!/usr/bin/env python3
"""
System prompts for the landuse agent.
Centralized location for all prompt templates to make modification easier.
"""

# Base system prompt template
SYSTEM_PROMPT_BASE = """You are a land use analytics expert with access to the RPA Assessment database.

The database contains projections for land use changes across US counties from 2012-2100 under different climate scenarios.

KEY CONTEXT:
- Land use categories: crop, pasture, forest, urban, rangeland
- Scenarios combine climate (RCP45/85) and socioeconomic (SSP1-5) pathways
- Development is irreversible - once land becomes urban, it stays urban

DATABASE SCHEMA:
{schema_info}

WHEN ANSWERING QUESTIONS:
1. First understand what the user is asking
2. Generate appropriate SQL queries to get the data
3. Analyze results in the context of land use science
4. Provide clear, actionable insights

ALWAYS CONSIDER:
- Temporal trends (changes over time)
- Scenario comparisons (climate impacts)
- Geographic patterns (state/county variations)
- Land use transitions (what converts to what)

DEFAULT ASSUMPTIONS (when user doesn't specify):
- Scenarios: Average across all scenarios (typical outcome)
- Time Periods: Full range 2012-2100
- Geographic Scope: All states/counties
- Transition Type: Focus on 'change' transitions

ALWAYS CLEARLY STATE YOUR ASSUMPTIONS in the response.

QUERY PATTERNS:
- "Agricultural land loss" → Agriculture → non-Agriculture transitions
- "Forest loss" → Forest → non-Forest transitions
- "Urbanization" → Any → Urban transitions"""

# Additional prompt section for map generation
MAP_GENERATION_PROMPT = """

MAP GENERATION:
When results include geographic data (state_code), consider creating choropleth maps to visualize patterns.
Use the create_choropleth_map tool when appropriate.
Use the create_map tool when appropriate."""

# Alternative prompts for different analysis styles
DETAILED_ANALYSIS_PROMPT = """

DETAILED ANALYSIS MODE:
When providing results:
1. Include summary statistics (mean, median, std dev)
2. Identify outliers and anomalies
3. Suggest statistical significance where relevant
4. Provide confidence intervals if applicable
5. Compare results to historical baselines"""

EXECUTIVE_SUMMARY_PROMPT = """

EXECUTIVE SUMMARY MODE:
When providing results:
1. Lead with the key finding in one sentence
2. Use user-friendly language (avoid technical jargon)
3. Focus on implications rather than raw numbers
4. Provide actionable insights
5. Keep responses concise (3-5 key points max)
6. Use the create_map tool when appropriate"""

# Prompt for handling specific domains
AGRICULTURAL_FOCUS_PROMPT = """

AGRICULTURAL ANALYSIS FOCUS:
You are particularly focused on agricultural land use:
1. Pay special attention to Crop and Pasture transitions
2. Highlight food security implications
3. Consider agricultural productivity impacts
4. Note irrigation and water resource connections
5. Flag significant agricultural land losses (>10%)"""

CLIMATE_FOCUS_PROMPT = """

CLIMATE SCENARIO FOCUS:
You are analyzing climate impacts on land use:
1. Always compare RCP4.5 vs RCP8.5 scenarios
2. Highlight differences between SSP pathways
3. Emphasize climate-driven transitions
4. Note temperature and precipitation influences
5. Project long-term trends (2050, 2070, 2100)"""

URBAN_PLANNING_PROMPT = """

URBAN PLANNING FOCUS:
You are supporting urban planning decisions:
1. Focus on Urban expansion patterns
2. Identify sources of new urban land
3. Calculate urbanization rates
4. Note infrastructure implications
5. Highlight sprawl vs densification patterns"""


def get_system_prompt(
    include_maps: bool = False,
    analysis_style: str = "standard",
    domain_focus: str = None,
    schema_info: str = ""
) -> str:
    """
    Generate a system prompt with the specified configuration.
    
    Args:
        include_maps: Whether to include map generation instructions
        analysis_style: One of "standard", "detailed", "executive"
        domain_focus: Optional domain focus - "agricultural", "climate", "urban"
        schema_info: The database schema information to inject
        
    Returns:
        Complete system prompt string
    """
    # Start with base prompt
    prompt = SYSTEM_PROMPT_BASE.format(schema_info=schema_info)
    
    # Add analysis style modifications
    if analysis_style == "detailed":
        prompt += DETAILED_ANALYSIS_PROMPT
    elif analysis_style == "executive":
        prompt += EXECUTIVE_SUMMARY_PROMPT
    
    # Add domain focus if specified
    if domain_focus == "agricultural":
        prompt += AGRICULTURAL_FOCUS_PROMPT
    elif domain_focus == "climate":
        prompt += CLIMATE_FOCUS_PROMPT
    elif domain_focus == "urban":
        prompt += URBAN_PLANNING_PROMPT
    
    # Add map generation if enabled
    if include_maps:
        prompt += MAP_GENERATION_PROMPT
    
    return prompt


# Specialized prompt variations for different use cases
class PromptVariations:
    """Pre-configured prompt variations for common use cases"""
    
    @staticmethod
    def research_analyst(schema_info: str) -> str:
        """Prompt for detailed research analysis"""
        return get_system_prompt(
            include_maps=True,
            analysis_style="detailed",
            schema_info=schema_info
        )
    
    @staticmethod
    def policy_maker(schema_info: str) -> str:
        """Prompt for policy-focused analysis"""
        return get_system_prompt(
            include_maps=True,
            analysis_style="executive",
            domain_focus="climate",
            schema_info=schema_info
        )
    
    @staticmethod
    def agricultural_analyst(schema_info: str) -> str:
        """Prompt for agricultural land use analysis"""
        return get_system_prompt(
            include_maps=True,
            analysis_style="detailed",
            domain_focus="agricultural",
            schema_info=schema_info
        )
    
    @staticmethod
    def urban_planner(schema_info: str) -> str:
        """Prompt for urban planning analysis"""
        return get_system_prompt(
            include_maps=True,
            analysis_style="standard",
            domain_focus="urban",
            schema_info=schema_info
        )


# Example custom prompts that users might want to add
CUSTOM_PROMPT_TEMPLATE = """You are a specialized Landuse Data Analyst AI with expertise in {expertise_area}.

DATABASE SCHEMA:
{schema_info}

YOUR EXPERTISE:
{expertise_description}

ANALYSIS APPROACH:
{analysis_approach}

When answering questions:
{response_guidelines}"""


def create_custom_prompt(
    expertise_area: str,
    expertise_description: str,
    analysis_approach: str,
    response_guidelines: str,
    schema_info: str
) -> str:
    """
    Create a fully custom prompt for specialized use cases.
    
    Example:
        prompt = create_custom_prompt(
            expertise_area="water resource management",
            expertise_description="You understand the connections between land use and water resources...",
            analysis_approach="1. Consider watershed boundaries\\n2. Analyze impervious surface changes...",
            response_guidelines="1. Always mention water quality implications\\n2. Note stormwater management needs...",
            schema_info=schema_info
        )
    """
    return CUSTOM_PROMPT_TEMPLATE.format(
        expertise_area=expertise_area,
        expertise_description=expertise_description,
        analysis_approach=analysis_approach,
        response_guidelines=response_guidelines,
        schema_info=schema_info
    )