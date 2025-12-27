"""
Domain-specific tools for RPA Land Use Agent.

Each tool encapsulates a specific query pattern and calls the LandUseService.
The LLM never generates SQL - it just picks the right tool with the right parameters.
"""

import logging

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from ..services.landuse_service import landuse_service

logger = logging.getLogger(__name__)


# ============== Input Schemas ==============


class LandUseAreaInput(BaseModel):
    """Input for land use area query."""

    states: list[str] = Field(
        description="Two-letter state codes (e.g., ['CA', 'TX', 'NC'])"
    )
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
    to_use: str | None = Field(
        default=None, description="Destination land use type"
    )
    year_range: str | None = Field(
        default=None, description="Time period (e.g., '2020-2030', '2030-2040')"
    )
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
    ag_type: str | None = Field(
        default=None, description="Agricultural type: 'crop', 'pasture', or None for both"
    )
    year_range: str | None = Field(default=None, description="Time period")
    scenario: str | None = Field(default=None, description="Scenario code (LM, HM, HL, HH)")


class ScenarioComparisonInput(BaseModel):
    """Input for scenario comparison."""

    states: list[str] = Field(description="Two-letter state codes")
    metric: str = Field(
        description="Metric to compare: 'urban_expansion', 'forest_loss', or 'ag_loss'"
    )
    scenarios: list[str] | None = Field(
        default=None,
        description="Scenarios to compare (default: all 4). Options: LM, HM, HL, HH",
    )
    year: int | None = Field(default=None, description="Year filter")


class StateComparisonInput(BaseModel):
    """Input for state comparison."""

    states: list[str] = Field(description="Two-letter state codes to compare (2-10 states)")
    metric: str = Field(
        description="Metric to compare: 'urban_expansion', 'forest_loss', or 'land_area'"
    )
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
    states: list[str] | None = Field(
        default=None, description="Optional state filter"
    )
    scenario: str | None = Field(default=None, description="Scenario code")


class DataSummaryInput(BaseModel):
    """Input for data summary."""

    geography: str | None = Field(default=None, description="Optional geography filter")


# ============== Tools ==============


@tool(args_schema=LandUseAreaInput)
async def query_land_use_area(
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
    result = await landuse_service.query_area(states, land_use, year, scenario)

    if "error" in result:
        return f"Error: {result['error']}"

    # Format response
    lines = ["**Land Use Area**"]

    if land_use:
        lines.append(f"- **{land_use.title()}**: {result['total_acres_formatted']} acres")
    else:
        lines.append(f"- **Total Area**: {result['total_acres_formatted']} acres")

    if result.get("by_landuse"):
        lines.append("\n**By Land Use Type:**")
        for lu, acres in result["by_landuse"].items():
            lines.append(f"- {lu}: {acres} acres")

    if result.get("by_state") and len(result["by_state"]) > 1:
        lines.append("\n**By State:**")
        for state, acres in result["by_state"].items():
            lines.append(f"- {state}: {acres} acres")

    if result.get("scenario"):
        lines.append(f"\n*Scenario: {result['scenario']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=LandUseTransitionsInput)
async def query_land_use_transitions(
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
    result = await landuse_service.query_transitions(states, from_use, to_use, year_range, scenario)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = ["**Land Use Transitions**"]
    lines.append(f"- **Total Transition Area**: {result['total_formatted']} acres")

    if result.get("transitions"):
        lines.append("\n**Top Transitions:**")
        for t in result["transitions"][:10]:
            lines.append(f"- {t['from']} → {t['to']}: {t['acres']} acres")

    if result.get("scenario"):
        lines.append(f"\n*Scenario: {result['scenario']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=UrbanExpansionInput)
async def query_urban_expansion(
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
    result = await landuse_service.query_urban_expansion(states, year_range, scenario, source_land_use)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = ["**Urban Expansion**"]
    lines.append(f"- **Total New Urban Area**: {result['total_formatted']} acres")

    if result.get("by_source"):
        lines.append("\n**Source of New Urban Land:**")
        for source, acres in result["by_source"].items():
            lines.append(f"- From {source}: {acres} acres")

    if result.get("by_state") and len(result["by_state"]) > 1:
        lines.append("\n**By State:**")
        for state, acres in list(result["by_state"].items())[:5]:
            lines.append(f"- {state}: {acres} acres")

    if result.get("note"):
        lines.append(f"\n*Note: {result['note']}*")

    if result.get("scenario"):
        lines.append(f"\n*Scenario: {result['scenario']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=ForestChangeInput)
async def query_forest_change(
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
    result = await landuse_service.query_forest_change(states, year_range, scenario, change_type)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = ["**Forest Change**"]

    if "forest_loss_acres" in result:
        lines.append(f"- **Forest Loss**: {result['forest_loss_formatted']} acres")
        if result.get("loss_by_destination"):
            lines.append("  - Converting to:")
            for dest, acres in result["loss_by_destination"].items():
                lines.append(f"    - {dest}: {acres} acres")

    if "forest_gain_acres" in result:
        lines.append(f"- **Forest Gain**: {result['forest_gain_formatted']} acres")

    if "net_change_acres" in result:
        direction = result.get("net_direction", "change")
        lines.append(f"- **Net {direction.title()}**: {result['net_change_formatted']} acres")

    if result.get("scenario"):
        lines.append(f"\n*Scenario: {result['scenario']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=AgriculturalChangeInput)
async def query_agricultural_change(
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
    result = await landuse_service.query_agricultural_change(states, ag_type, year_range, scenario)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = ["**Agricultural Land Changes**"]
    lines.append(f"- **Total Agricultural Loss**: {result['total_formatted']} acres")

    if result.get("by_ag_type"):
        lines.append("\n**By Agricultural Type:**")
        for ag, acres in result["by_ag_type"].items():
            lines.append(f"- {ag}: {acres} acres")

    if result.get("by_destination"):
        lines.append("\n**Converting To:**")
        for dest, acres in result["by_destination"].items():
            lines.append(f"- {dest}: {acres} acres")

    if result.get("scenario"):
        lines.append(f"\n*Scenario: {result['scenario']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=ScenarioComparisonInput)
async def compare_scenarios(
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
    result = await landuse_service.compare_scenarios(states, metric, scenarios, year)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = [f"**Scenario Comparison: {metric.replace('_', ' ').title()}**"]

    if result.get("comparison"):
        lines.append("\n| Scenario | Acres |")
        lines.append("|----------|-------|")
        for code, data in result["comparison"].items():
            lines.append(f"| {data['name']} | {data['formatted']} |")

    if result.get("highest"):
        highest = result["comparison"].get(result["highest"], {})
        lines.append(f"\n**Highest**: {highest.get('name', result['highest'])}")

    if result.get("lowest"):
        lowest = result["comparison"].get(result["lowest"], {})
        lines.append(f"**Lowest**: {lowest.get('name', result['lowest'])}")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=StateComparisonInput)
async def compare_states(
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
    result = await landuse_service.compare_states(states, metric, scenario, year)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = [f"**State Comparison: {metric.replace('_', ' ').title()}**"]

    if result.get("comparison"):
        lines.append("\n| Rank | State | Acres |")
        lines.append("|------|-------|-------|")
        for i, data in enumerate(result["comparison"], 1):
            lines.append(f"| {i} | {data['state_name']} | {data['formatted']} |")

    if result.get("scenario"):
        lines.append(f"\n*Scenario: {result['scenario']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=TimeSeriesInput)
async def query_time_series(
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
    result = await landuse_service.query_time_series(states, metric, scenario)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = [f"**Time Series: {metric.replace('_', ' ').title()}**"]

    if result.get("time_series"):
        lines.append("\n| Period | Acres |")
        lines.append("|--------|-------|")
        for period in result["time_series"]:
            lines.append(f"| {period['period']} | {period['formatted']} |")

    if result.get("trend"):
        trend = result["trend"]
        lines.append(f"\n**Trend**: {trend['direction'].title()}")
        lines.append(f"- Change: {trend['change_acres']} acres ({trend['change_percent']})")

    if result.get("scenario"):
        lines.append(f"\n*Scenario: {result['scenario']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=CountyQueryInput)
async def query_by_county(
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
    result = await landuse_service.query_by_county(state, county, metric, year, scenario)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = [f"**{result['county']}, {result['state']}**"]
    lines.append(f"- FIPS: {result.get('fips', 'N/A')}")

    if result.get("by_landuse"):
        lines.append("\n**Land Use Breakdown:**")
        for lu, acres in result["by_landuse"].items():
            lines.append(f"- {lu}: {acres} acres")

    if result.get("scenario"):
        lines.append(f"\n*Scenario: {result['scenario']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=TopCountiesInput)
async def query_top_counties(
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
    result = await landuse_service.query_top_counties(metric, limit, states, scenario)

    if "error" in result:
        return f"Error: {result['error']}"

    lines = [f"**Top {limit} Counties by {metric.replace('_', ' ').title()}**"]

    if result.get("counties"):
        lines.append("\n| Rank | County | State | Acres |")
        lines.append("|------|--------|-------|-------|")
        for c in result["counties"]:
            lines.append(f"| {c['rank']} | {c['county']} | {c['state']} | {c['formatted']} |")

    if result.get("scenario"):
        lines.append(f"\n*Scenario: {result['scenario']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


@tool(args_schema=DataSummaryInput)
async def get_data_summary(geography: str | None = None) -> str:
    """
    Get summary statistics about available data.

    Use for questions about:
    - What data is available
    - Time range covered
    - Number of counties/states
    - Geographic coverage
    - Available scenarios
    """
    result = await landuse_service.get_data_summary(geography)

    lines = ["**RPA Land Use Data Summary**"]

    lines.append("\n**Coverage:**")
    lines.append(f"- Total Records: {result.get('total_records', 'N/A'):,}")
    lines.append(f"- Counties: {result.get('counties', 'N/A'):,}")
    lines.append(f"- States: {result.get('states', 'N/A')}")

    if result.get("time_range"):
        tr = result["time_range"]
        lines.append(f"- Time Range: {tr['start']}-{tr['end']}")

    lines.append("\n**Scenarios:**")
    for code, name in [
        ("LM", "Lower-Moderate (RCP45/SSP1): Sustainability pathway"),
        ("HM", "High-Moderate (RCP85/SSP2): Middle Road"),
        ("HL", "High-Low (RCP85/SSP3): Regional Rivalry"),
        ("HH", "High-High (RCP85/SSP5): Fossil Development"),
    ]:
        lines.append(f"- {code}: {name}")

    lines.append("\n**Land Use Types:**")
    for lu in result.get("land_use_types", []):
        lines.append(f"- {lu}")

    if result.get("coverage"):
        lines.append(f"\n*Coverage: {result['coverage']}*")

    if result.get("key_assumption"):
        lines.append(f"*Key Assumption: {result['key_assumption']}*")

    lines.append(f"\n*Source: {result.get('source', 'USDA Forest Service 2020 RPA Assessment')}*")

    return "\n".join(lines)


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
