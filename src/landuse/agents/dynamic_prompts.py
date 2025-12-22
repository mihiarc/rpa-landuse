"""Dynamic prompt builder with progressive disclosure for RPA context.

This module builds agent prompts dynamically based on the current state,
injecting only relevant RPA domain context that hasn't been explained yet.
"""

from typing import Literal

from landuse.agents.rpa_context import RPA_CONTEXT_LIBRARY, detect_relevant_concepts
from landuse.agents.state import AgentState


class DynamicRPAPromptBuilder:
    """Builds dynamic prompts with progressive disclosure of RPA domain knowledge.

    Instead of injecting all 288 lines of RPA context upfront, this builder:
    1. Detects which concepts are relevant to the current query
    2. Only explains concepts that haven't been explained in this session
    3. Calibrates response style based on user expertise level
    """

    # Base role description - always included
    BASE_ROLE = """You are an expert analyst for the USDA Forest Service 2020 RPA Assessment land use projections.
You help users understand and query county-level land use change data from 2020 to 2070 across 20 climate-socioeconomic scenarios.

Your capabilities:
- Execute SQL queries against the RPA land use database
- Explain land use patterns and trends
- Compare scenarios and geographic regions
- Provide context about RPA methodology when relevant"""

    # Expertise-calibrated response styles
    EXPERTISE_STYLES = {
        "novice": """
RESPONSE STYLE FOR NOVICE USER:
- Explain technical terms when first used
- Provide context for why patterns matter
- Use plain language, avoid jargon
- Suggest follow-up questions they might have
- Include brief explanations of RPA methodology when relevant""",
        "intermediate": """
RESPONSE STYLE FOR INTERMEDIATE USER:
- Assume familiarity with basic land use concepts
- Focus on insights and patterns
- Provide technical details when relevant
- Suggest advanced analysis options""",
        "expert": """
RESPONSE STYLE FOR EXPERT USER:
- Be concise and technical
- Focus on data and methodology details
- Skip basic explanations
- Provide nuanced interpretations
- Discuss model limitations when relevant""",
    }

    # Database schema summary (always included for SQL generation)
    SCHEMA_SUMMARY = """
DATABASE SCHEMA (DuckDB Star Schema):

FACT TABLE:
- fact_landuse_transitions: Core transition data
  * scenario_key, time_key, geography_key, from_landuse_key, to_landuse_key
  * acres_changed (the transition amount)

DIMENSION TABLES:
- dim_scenario: scenario_key, scenario_code (LM, HM, HL, HH), rcp, ssp, gcm, description
- dim_time: time_key, year (2020, 2030, 2040, 2050, 2060, 2070), decade_label
- dim_geography: geography_key, state_fips, county_fips, state_name, county_name, region
- dim_landuse: landuse_key, landuse_code (cr, ps, fr, ur, rg), landuse_name, category

SCENARIO CODES:
- LM: Low emissions, sustainability (RCP4.5 + SSP1)
- HM: Moderate emissions, business-as-usual (RCP8.5 + SSP2)
- HL: High emissions, fragmented growth (RCP8.5 + SSP3)
- HH: High emissions, rapid development (RCP8.5 + SSP5)

LAND USE CODES:
- cr: Cropland, ps: Pasture, fr: Forest, ur: Urban, rg: Rangeland"""

    # SQL generation guidance
    SQL_GUIDANCE = """
SQL QUERY PATTERNS:

1. Total transitions by scenario:
   SELECT s.scenario_code, SUM(f.acres_changed) as total_acres
   FROM fact_landuse_transitions f
   JOIN dim_scenario s ON f.scenario_key = s.scenario_key
   GROUP BY s.scenario_code

2. Geographic focus:
   SELECT g.state_name, SUM(f.acres_changed)
   FROM fact_landuse_transitions f
   JOIN dim_geography g ON f.geography_key = g.geography_key
   WHERE g.state_name = 'California'
   GROUP BY g.state_name

3. Land use transitions:
   SELECT from_lu.landuse_name as from_use, to_lu.landuse_name as to_use, SUM(f.acres_changed)
   FROM fact_landuse_transitions f
   JOIN dim_landuse from_lu ON f.from_landuse_key = from_lu.landuse_key
   JOIN dim_landuse to_lu ON f.to_landuse_key = to_lu.landuse_key
   GROUP BY from_lu.landuse_name, to_lu.landuse_name

IMPORTANT:
- Always include LIMIT clause to prevent large result sets
- Use scenario_code (LM, HM, HL, HH) not full scenario names
- Use landuse_code (cr, ps, fr, ur, rg) for filtering"""

    def __init__(self, base_schema_info: str = ""):
        """Initialize the prompt builder.

        Args:
            base_schema_info: Additional schema information to include.
        """
        self.additional_schema_info = base_schema_info

    def build_prompt(
        self,
        state: AgentState,
        include_schema: bool = True,
    ) -> tuple[str, list[str]]:
        """Build a dynamic prompt based on current state.

        Args:
            state: Current agent state with context tracking.
            include_schema: Whether to include database schema.

        Returns:
            Tuple of (prompt_text, newly_explained_concepts).
        """
        sections = [self.BASE_ROLE]

        # Get user expertise level
        expertise = state.get("user_expertise", "novice")
        if expertise in self.EXPERTISE_STYLES:
            sections.append(self.EXPERTISE_STYLES[expertise])

        # Get explained concepts to avoid repetition
        explained = set(state.get("explained_concepts", []))

        # Find latest user query for context detection
        user_query = self._extract_user_query(state)

        # Detect and inject relevant concepts (progressive disclosure)
        new_concepts = []
        if user_query:
            relevant = detect_relevant_concepts(user_query, list(explained))
            # Limit to 3 most relevant concepts
            concepts_to_add = relevant[:3]

            if concepts_to_add:
                concept_text = self._format_concepts(concepts_to_add)
                sections.append(concept_text)
                new_concepts = concepts_to_add

        # Add scenario-specific context if comparing scenarios
        detected_scenarios = state.get("detected_scenarios", [])
        if len(detected_scenarios) > 1:
            sections.append(self._get_scenario_comparison_context(detected_scenarios))

        # Add geographic context if focusing on specific regions
        detected_geography = state.get("detected_geography", [])
        if detected_geography:
            sections.append(self._get_geographic_context(detected_geography))

        # Always include schema for SQL generation
        if include_schema:
            sections.append(self.SCHEMA_SUMMARY)
            sections.append(self.SQL_GUIDANCE)
            if self.additional_schema_info:
                sections.append(f"ADDITIONAL SCHEMA INFO:\n{self.additional_schema_info}")

        return "\n\n".join(sections), new_concepts

    def _extract_user_query(self, state: AgentState) -> str:
        """Extract the latest user query from state messages."""
        from langchain_core.messages import HumanMessage

        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return str(msg.content)
        return ""

    def _format_concepts(self, concept_keys: list[str]) -> str:
        """Format RPA concepts for prompt injection."""
        lines = ["RELEVANT RPA CONTEXT (for your reference in answering):"]

        for key in concept_keys:
            if key in RPA_CONTEXT_LIBRARY:
                info = RPA_CONTEXT_LIBRARY[key]
                lines.append(f"\n{info['concept']}:")
                lines.append(info["explanation"])

        return "\n".join(lines)

    def _get_scenario_comparison_context(self, scenarios: list[str]) -> str:
        """Get context for comparing specific scenarios."""
        scenario_details = {
            "LM": "Low emissions pathway (RCP4.5+SSP1) - sustainability focus, less development pressure",
            "HM": "Moderate pathway (RCP8.5+SSP2) - business-as-usual continuation",
            "HL": "High emissions, slow growth (RCP8.5+SSP3) - fragmented development",
            "HH": "High emissions, rapid growth (RCP8.5+SSP5) - maximum development pressure",
        }

        lines = ["SCENARIO COMPARISON CONTEXT:"]
        for s in scenarios:
            if s in scenario_details:
                lines.append(f"- {s}: {scenario_details[s]}")

        lines.append(
            "\nWhen comparing scenarios, focus on how different development "
            "pressures and climate conditions affect land use transitions."
        )

        return "\n".join(lines)

    def _get_geographic_context(self, states: list[str]) -> str:
        """Get context for geographic focus."""
        regional_context = {
            "CA": "California - High urban pressure, significant forest-to-urban conversion",
            "TX": "Texas - Large agricultural base, rapid urban expansion in metro areas",
            "FL": "Florida - Coastal development pressure, wetland/forest conversion",
            "GA": "Georgia - Southeast urbanization hotspot, Atlanta metro expansion",
            "NC": "North Carolina - Fast-growing, forest-to-urban transitions",
        }

        lines = ["GEOGRAPHIC CONTEXT:"]
        for state in states[:3]:  # Limit to 3 states
            if state in regional_context:
                lines.append(f"- {regional_context[state]}")

        return "\n".join(lines)

    def build_minimal_prompt(
        self,
        expertise: Literal["novice", "intermediate", "expert"] = "novice",
    ) -> str:
        """Build a minimal prompt without state context.

        Useful for simple queries or when full state isn't available.

        Args:
            expertise: User expertise level.

        Returns:
            Minimal prompt string.
        """
        sections = [
            self.BASE_ROLE,
            self.EXPERTISE_STYLES.get(expertise, self.EXPERTISE_STYLES["novice"]),
            self.SCHEMA_SUMMARY,
            self.SQL_GUIDANCE,
        ]
        return "\n\n".join(sections)


def get_dynamic_system_prompt(
    state: AgentState,
    schema_info: str = "",
) -> tuple[str, list[str]]:
    """Convenience function to get a dynamic system prompt.

    Args:
        state: Current agent state.
        schema_info: Additional schema information.

    Returns:
        Tuple of (prompt_text, newly_explained_concepts).
    """
    builder = DynamicRPAPromptBuilder(schema_info)
    return builder.build_prompt(state)
