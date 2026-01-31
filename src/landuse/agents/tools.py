"""
Domain-specific tools for RPA Land Use Agent.

Each tool encapsulates a specific query pattern and calls the LandUseAPI.
The LLM never generates SQL - it just picks the right tool with the right parameters.
"""

import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from landuse.api import LandUseAPI

logger = logging.getLogger(__name__)

# ============== API Instance (Lazy Initialization) ==============

_api: LandUseAPI | None = None


def _get_api() -> LandUseAPI:
    """Get or create the API instance."""
    global _api
    if _api is None:
        _api = LandUseAPI()
    return _api


def close_api() -> None:
    """Close the API connection. Call on shutdown."""
    global _api
    if _api is not None:
        _api.close()
        _api = None


# ============== Input Schemas ==============


class LandUseAreaInput(BaseModel):
    """Input for land use area query."""

    states: list[str] = Field(description="Two-letter state codes (e.g., ['CA', 'TX', 'NC'])")
    land_use: str | None = Field(
        default=None,
        description="Land use type to filter by: crop, pasture, forest, urban, or rangeland",
    )
    year: int | None = Field(
        default=None,
        description="Year to query (e.g., 2030, 2050, 2070). Will match containing time period.",
    )
    scenario: str | None = Field(
        default=None,
        description="Scenario code: LM (low emissions), HM (high-moderate), HL (high-low), HH (high emissions)",
    )


class LandUseTransitionsInput(BaseModel):
    """Input for land use transitions query."""

    states: list[str] = Field(description="Two-letter state codes")
    from_use: str | None = Field(
        default=None, description="Source land use type (crop, pasture, forest, urban, rangeland)"
    )
    to_use: str | None = Field(default=None, description="Destination land use type")
    year_range: str | None = Field(default=None, description="Time period (e.g., '2020-2030', '2030-2040')")
    scenario: str | None = Field(default=None, description="Scenario code (LM, HM, HL, HH)")


class UrbanExpansionInput(BaseModel):
    """Input for urban expansion query."""

    states: list[str] = Field(description="Two-letter state codes")
    year_range: str | None = Field(default=None, description="Time period")
    scenario: str | None = Field(default=None, description="Scenario code (LM, HM, HL, HH)")
    source_land_use: str | None = Field(
        default=None,
        description="Filter by what's converting to urban (forest, crop, pasture, rangeland)",
    )


class ForestChangeInput(BaseModel):
    """Input for forest change query."""

    states: list[str] = Field(description="Two-letter state codes")
    year_range: str | None = Field(default=None, description="Time period")
    scenario: str | None = Field(default=None, description="Scenario code (LM, HM, HL, HH)")
    change_type: str = Field(
        default="net",
        description="Type of change: 'net' (gain minus loss), 'loss' only, or 'gain' only",
    )


class AgriculturalChangeInput(BaseModel):
    """Input for agricultural change query."""

    states: list[str] = Field(description="Two-letter state codes")
    ag_type: str | None = Field(default=None, description="Agricultural type: 'crop', 'pasture', or None for both")
    year_range: str | None = Field(default=None, description="Time period")
    scenario: str | None = Field(default=None, description="Scenario code (LM, HM, HL, HH)")


class ScenarioComparisonInput(BaseModel):
    """Input for scenario comparison."""

    states: list[str] = Field(description="Two-letter state codes")
    metric: str = Field(description="Metric to compare: 'urban_expansion', 'forest_loss', or 'ag_loss'")
    scenarios: list[str] | None = Field(
        default=None,
        description="Scenarios to compare (default: all 4). Options: LM, HM, HL, HH",
    )
    year: int | None = Field(default=None, description="Year filter")


class StateComparisonInput(BaseModel):
    """Input for state comparison."""

    states: list[str] = Field(description="Two-letter state codes to compare (2-10 states)")
    metric: str = Field(description="Metric to compare: 'urban_expansion', 'forest_loss', or 'land_area'")
    scenario: str | None = Field(default=None, description="Scenario code")
    year: int | None = Field(default=None, description="Year filter")


class TimeSeriesInput(BaseModel):
    """Input for time series query."""

    states: list[str] = Field(description="Two-letter state codes")
    metric: str = Field(
        description="Metric to track: 'urban_area', 'forest_area', 'crop_area', 'pasture_area', 'rangeland_area'"
    )
    scenario: str | None = Field(default=None, description="Scenario code")


class CountyQueryInput(BaseModel):
    """Input for county-level query."""

    state: str = Field(description="Two-letter state code")
    county: str = Field(description="County name (partial match supported)")
    metric: str = Field(default="area", description="Metric: 'area' for land use breakdown")
    year: int | None = Field(default=None, description="Year filter")
    scenario: str | None = Field(default=None, description="Scenario code")


class TopCountiesInput(BaseModel):
    """Input for top counties query."""

    metric: str = Field(description="Metric to rank by: 'urban_growth' or 'forest_loss'")
    limit: int = Field(default=10, description="Number of counties to return (1-50)")
    states: list[str] | None = Field(default=None, description="Optional state filter")
    scenario: str | None = Field(default=None, description="Scenario code")


class DataSummaryInput(BaseModel):
    """Input for data summary."""

    geography: str | None = Field(default=None, description="Optional geography filter")


# ============== Tools ==============


@tool(args_schema=LandUseAreaInput)
def query_land_use_area(
    states: list[str],
    land_use: str | None = None,
    year: int | None = None,
    scenario: str | None = None,
) -> str:
    """
    Query current or projected land use area.

    Use for questions about:
    - Total cropland, forest, urban, pasture, or rangeland area
    - Land use distribution by state
    - Current vs future land area by type
    - How much of a specific land use is in certain states
    """
    result = _get_api().get_land_use_area(states, land_use, year, scenario)
    return result.to_llm_string()


@tool(args_schema=LandUseTransitionsInput)
def query_land_use_transitions(
    states: list[str],
    from_use: str | None = None,
    to_use: str | None = None,
    year_range: str | None = None,
    scenario: str | None = None,
) -> str:
    """
    Query land use transitions (what converts to what).

    Use for questions about:
    - Forest loss (Forest → Urban, Forest → Crop, etc.)
    - Agricultural land loss
    - Urbanization patterns (Any → Urban)
    - Net land use changes
    - What specific land types are converting to
    """
    result = _get_api().get_transitions(states, from_use, to_use, year_range, scenario)
    return result.to_llm_string()


@tool(args_schema=UrbanExpansionInput)
def query_urban_expansion(
    states: list[str],
    year_range: str | None = None,
    scenario: str | None = None,
    source_land_use: str | None = None,
) -> str:
    """
    Query urban/developed land expansion.

    Use for questions about:
    - How much new urban development is projected
    - What land is converting to urban/developed
    - Urban expansion by scenario
    - Development patterns over time
    - Which land uses are losing area to urbanization
    """
    result = _get_api().get_urban_expansion(states, year_range, scenario, source_land_use)
    return result.to_llm_string()


@tool(args_schema=ForestChangeInput)
def query_forest_change(
    states: list[str],
    year_range: str | None = None,
    scenario: str | None = None,
    change_type: str = "net",
) -> str:
    """
    Query forest area changes.

    Use for questions about:
    - Forest loss/gain projections
    - Net forest change
    - What forests are converting to
    - Forest area trends by scenario
    - How much forest a state will lose
    """
    result = _get_api().get_forest_change(states, year_range, scenario, change_type)
    return result.to_llm_string()


@tool(args_schema=AgriculturalChangeInput)
def query_agricultural_change(
    states: list[str],
    ag_type: str | None = None,
    year_range: str | None = None,
    scenario: str | None = None,
) -> str:
    """
    Query agricultural land changes.

    Use for questions about:
    - Cropland loss/changes
    - Pasture changes
    - Agricultural land to urban conversion
    - Farming land availability projections
    """
    result = _get_api().get_agricultural_change(states, ag_type, year_range, scenario)
    return result.to_llm_string()


@tool(args_schema=ScenarioComparisonInput)
def compare_scenarios(
    states: list[str],
    metric: str,
    scenarios: list[str] | None = None,
    year: int | None = None,
) -> str:
    """
    Compare land use changes across climate scenarios.

    Use for questions about:
    - How scenarios differ in their projections
    - Best/worst case projections
    - Scenario-specific impacts
    - LM vs HM vs HL vs HH comparisons
    """
    result = _get_api().compare_scenarios(states, metric, scenarios)
    return result.to_llm_string()


@tool(args_schema=StateComparisonInput)
def compare_states(
    states: list[str],
    metric: str,
    scenario: str | None = None,
    year: int | None = None,
) -> str:
    """
    Compare land use metrics across states.

    Use for questions about:
    - Which state has the most development
    - State-by-state rankings
    - Regional differences
    - Top/bottom states for a metric
    """
    result = _get_api().compare_states(states, metric, scenario, year)
    return result.to_llm_string()


@tool(args_schema=TimeSeriesInput)
def query_time_series(
    states: list[str],
    metric: str,
    scenario: str | None = None,
) -> str:
    """
    Query land use changes over time (2012-2070).

    Use for questions about:
    - Trends over time
    - When changes accelerate
    - Trajectory comparisons
    - Historical vs projected patterns
    """
    result = _get_api().get_time_series(states, metric, scenario)
    return result.to_llm_string()


@tool(args_schema=CountyQueryInput)
def query_by_county(
    state: str,
    county: str,
    metric: str = "area",
    year: int | None = None,
    scenario: str | None = None,
) -> str:
    """
    Query land use metrics for a specific county.

    Use for questions about:
    - County-level projections
    - Local land use patterns
    - Specific county analysis
    """
    result = _get_api().get_county_data(state, county, year, scenario)
    return result.to_llm_string()


@tool(args_schema=TopCountiesInput)
def query_top_counties(
    metric: str,
    limit: int = 10,
    states: list[str] | None = None,
    scenario: str | None = None,
) -> str:
    """
    Find top/bottom counties by a metric.

    Use for questions about:
    - Which counties have the most growth
    - Fastest urbanizing counties
    - Counties with most forest loss
    - Top development hotspots
    """
    result = _get_api().get_top_counties(metric, limit, states, scenario)
    return result.to_llm_string()


@tool(args_schema=DataSummaryInput)
def get_data_summary(geography: str | None = None) -> str:
    """
    Get summary statistics about available data.

    Use for questions about:
    - What data is available
    - Time range covered
    - Number of counties/states
    - Geographic coverage
    - Available scenarios
    """
    result = _get_api().get_data_summary()
    return result.to_llm_string()


# ============== Tool List ==============

TOOLS = [
    query_land_use_area,
    query_land_use_transitions,
    query_urban_expansion,
    query_forest_change,
    query_agricultural_change,
    compare_scenarios,
    compare_states,
    query_time_series,
    query_by_county,
    query_top_counties,
    get_data_summary,
]
