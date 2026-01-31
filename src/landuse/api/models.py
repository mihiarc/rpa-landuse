"""Pydantic 2 models for API inputs and outputs.

This module defines all data models for the Land Use API, including:
- Enums for valid query parameters
- Result models with to_llm_string() for Claude consumption
- Error handling models
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Scenario(str, Enum):
    """Climate scenario codes.

    Based on RCP (climate) and SSP (socioeconomic) pathway combinations.
    """
    LM = "LM"  # RCP45/SSP1 - Lower-Moderate (Taking the Green Road)
    HM = "HM"  # RCP85/SSP2 - High-Moderate (Middle of the Road)
    HL = "HL"  # RCP85/SSP3 - High-Low (A Rocky Road)
    HH = "HH"  # RCP85/SSP5 - High-High (Taking the Highway)


class LandUse(str, Enum):
    """Land use types in the RPA data."""
    CROP = "crop"
    PASTURE = "pasture"
    FOREST = "forest"
    URBAN = "urban"
    RANGELAND = "rangeland"


class Metric(str, Enum):
    """Query metrics for comparisons and rankings."""
    URBAN_EXPANSION = "urban_expansion"
    FOREST_LOSS = "forest_loss"
    FOREST_GAIN = "forest_gain"
    FOREST_NET = "forest_net"
    AG_LOSS = "ag_loss"
    LAND_AREA = "land_area"


class ChangeType(str, Enum):
    """Forest change types for queries."""
    NET = "net"
    LOSS = "loss"
    GAIN = "gain"


# ============== Result Models ==============


class APIResult(BaseModel):
    """Base result model with success/error handling and source attribution."""
    model_config = ConfigDict(frozen=True)

    success: bool = True
    error_message: str | None = None
    error_code: str | None = None
    source: str = "USDA Forest Service 2020 RPA Assessment"

    def to_llm_string(self) -> str:
        """Format result for LLM consumption. Override in subclasses."""
        raise NotImplementedError

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary, excluding None values."""
        return self.model_dump(exclude_none=True)


class ErrorResult(APIResult):
    """Error response with suggestion for recovery."""
    success: bool = False
    suggestion: str | None = None

    def to_llm_string(self) -> str:
        msg = f"**Error**: {self.error_message}"
        if self.suggestion:
            msg += f"\n**Suggestion**: {self.suggestion}"
        return msg


class LandUseAreaResult(APIResult):
    """Land use area query result with breakdowns by type and state."""
    total_acres: float
    total_formatted: str
    by_land_use: dict[str, str] = Field(default_factory=dict)
    by_state: dict[str, str] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)

    def to_llm_string(self) -> str:
        lines = ["**Land Use Area**", f"Total: {self.total_formatted} acres"]
        if self.by_land_use:
            lines.append("\n**By Type:**")
            for land_use, acres in self.by_land_use.items():
                lines.append(f"- {land_use}: {acres}")
        if len(self.by_state) > 1:
            lines.append("\n**By State:**")
            for state, acres in list(self.by_state.items())[:10]:
                lines.append(f"- {state}: {acres}")
        lines.append(f"\n*Source: {self.source}*")
        return "\n".join(lines)


class TransitionRecord(BaseModel):
    """Single land use transition record."""
    model_config = ConfigDict(frozen=True)

    from_use: str
    to_use: str
    acres: float
    formatted: str


class TransitionsResult(APIResult):
    """Land use transitions result with list of transitions."""
    total_acres: float
    total_formatted: str
    transitions: list[TransitionRecord] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)

    def to_llm_string(self) -> str:
        lines = ["**Land Use Transitions**", f"Total: {self.total_formatted} acres"]
        if self.transitions:
            lines.append("\n**Top Transitions:**")
            for t in self.transitions[:10]:
                lines.append(f"- {t.from_use} → {t.to_use}: {t.formatted}")
        lines.append(f"\n*Source: {self.source}*")
        return "\n".join(lines)


class UrbanExpansionResult(APIResult):
    """Urban expansion result showing sources of new urban land."""
    total_acres: float
    total_formatted: str
    by_source: dict[str, str] = Field(default_factory=dict)
    by_state: dict[str, str] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)
    note: str = "Urban development is irreversible in RPA projections"

    def to_llm_string(self) -> str:
        lines = ["**Urban Expansion**", f"Total: {self.total_formatted} acres"]
        if self.by_source:
            lines.append("\n**By Source:**")
            for src, acres in self.by_source.items():
                lines.append(f"- From {src}: {acres}")
        if len(self.by_state) > 1:
            lines.append("\n**By State:**")
            for state, acres in list(self.by_state.items())[:10]:
                lines.append(f"- {state}: {acres}")
        lines.append(f"\n*Note: {self.note}*")
        lines.append(f"*Source: {self.source}*")
        return "\n".join(lines)


class ForestChangeResult(APIResult):
    """Forest change result with loss, gain, and net change."""
    loss_acres: float | None = None
    loss_formatted: str | None = None
    gain_acres: float | None = None
    gain_formatted: str | None = None
    net_acres: float | None = None
    net_formatted: str | None = None
    net_direction: str | None = None
    loss_by_destination: dict[str, str] = Field(default_factory=dict)
    gain_by_source: dict[str, str] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)

    def to_llm_string(self) -> str:
        lines = ["**Forest Change**"]
        if self.loss_formatted:
            lines.append(f"- Loss: {self.loss_formatted} acres")
            if self.loss_by_destination:
                for dest, acres in list(self.loss_by_destination.items())[:5]:
                    lines.append(f"  - To {dest}: {acres}")
        if self.gain_formatted:
            lines.append(f"- Gain: {self.gain_formatted} acres")
            if self.gain_by_source:
                for src, acres in list(self.gain_by_source.items())[:5]:
                    lines.append(f"  - From {src}: {acres}")
        if self.net_formatted:
            lines.append(f"- Net {self.net_direction}: {self.net_formatted} acres")
        lines.append(f"\n*Source: {self.source}*")
        return "\n".join(lines)


class AgriculturalChangeResult(APIResult):
    """Agricultural land change result."""
    total_loss_acres: float
    total_loss_formatted: str
    by_ag_type: dict[str, str] = Field(default_factory=dict)
    by_destination: dict[str, str] = Field(default_factory=dict)
    by_state: dict[str, str] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)

    def to_llm_string(self) -> str:
        lines = ["**Agricultural Land Change**", f"Total Loss: {self.total_loss_formatted} acres"]
        if self.by_ag_type:
            lines.append("\n**By Type:**")
            for ag_type, acres in self.by_ag_type.items():
                lines.append(f"- {ag_type}: {acres}")
        if self.by_destination:
            lines.append("\n**Converted To:**")
            for dest, acres in self.by_destination.items():
                lines.append(f"- {dest}: {acres}")
        lines.append(f"\n*Source: {self.source}*")
        return "\n".join(lines)


class ScenarioComparisonResult(APIResult):
    """Scenario comparison result across multiple climate scenarios."""
    metric: str
    comparison: dict[str, dict[str, Any]] = Field(default_factory=dict)
    highest: str | None = None
    lowest: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)

    def to_llm_string(self) -> str:
        lines = [f"**Scenario Comparison: {self.metric}**"]
        for code, data in self.comparison.items():
            lines.append(f"- {data['name']}: {data['formatted']}")
        if self.highest and self.highest in self.comparison:
            lines.append(f"\n**Highest**: {self.comparison[self.highest]['name']}")
        if self.lowest and self.lowest in self.comparison:
            lines.append(f"**Lowest**: {self.comparison[self.lowest]['name']}")
        lines.append(f"\n*Source: {self.source}*")
        return "\n".join(lines)


class StateRanking(BaseModel):
    """Single state in a comparison ranking."""
    model_config = ConfigDict(frozen=True)

    state: str
    state_abbrev: str
    acres: float
    formatted: str


class StateComparisonResult(APIResult):
    """State comparison result with rankings."""
    metric: str
    rankings: list[StateRanking] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)

    def to_llm_string(self) -> str:
        lines = [f"**State Comparison: {self.metric}**"]
        for i, item in enumerate(self.rankings, 1):
            lines.append(f"{i}. {item.state}: {item.formatted}")
        lines.append(f"\n*Source: {self.source}*")
        return "\n".join(lines)


class TimeSeriesPoint(BaseModel):
    """Time series data point."""
    model_config = ConfigDict(frozen=True)

    period: str
    start_year: int
    end_year: int
    acres: float
    formatted: str


class TimeSeriesResult(APIResult):
    """Time series result with trend analysis."""
    metric: str
    data_points: list[TimeSeriesPoint] = Field(default_factory=list)
    trend_direction: str | None = None
    trend_change_acres: str | None = None
    trend_change_percent: str | None = None
    filters: dict[str, Any] = Field(default_factory=dict)

    def to_llm_string(self) -> str:
        lines = [f"**Time Series: {self.metric}**"]
        for pt in self.data_points:
            lines.append(f"- {pt.period}: {pt.formatted}")
        if self.trend_direction:
            trend_info = f"{self.trend_direction}"
            if self.trend_change_percent:
                trend_info += f" ({self.trend_change_percent})"
            lines.append(f"\n**Trend**: {trend_info}")
        lines.append(f"\n*Source: {self.source}*")
        return "\n".join(lines)


class CountyResult(APIResult):
    """County detail result with land use breakdown."""
    county: str
    state: str
    state_abbrev: str
    fips: str
    total_acres: float
    total_formatted: str
    by_land_use: dict[str, str] = Field(default_factory=dict)
    filters: dict[str, Any] = Field(default_factory=dict)

    def to_llm_string(self) -> str:
        lines = [f"**{self.county}, {self.state}**", f"FIPS: {self.fips}"]
        lines.append(f"Total: {self.total_formatted} acres")
        if self.by_land_use:
            lines.append("\n**Land Use:**")
            for land_use, acres in self.by_land_use.items():
                lines.append(f"- {land_use}: {acres}")
        lines.append(f"\n*Source: {self.source}*")
        return "\n".join(lines)


class RankedCounty(BaseModel):
    """Ranked county record for top counties queries."""
    model_config = ConfigDict(frozen=True)

    rank: int
    county: str
    state: str
    fips: str
    acres: float
    formatted: str


class TopCountiesResult(APIResult):
    """Top counties ranking result."""
    metric: str
    counties: list[RankedCounty] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)

    def to_llm_string(self) -> str:
        lines = [f"**Top Counties: {self.metric}**"]
        for c in self.counties:
            lines.append(f"{c.rank}. {c.county}, {c.state}: {c.formatted}")
        lines.append(f"\n*Source: {self.source}*")
        return "\n".join(lines)


class DataSummaryResult(APIResult):
    """Data summary result with coverage statistics."""
    total_records: int
    counties: int
    states: int
    time_range: tuple[int, int]
    scenarios: list[str]
    land_use_types: list[str]
    coverage: str = "Private lands only"
    key_assumption: str = "Urban development is irreversible"

    def to_llm_string(self) -> str:
        lines = [
            "**RPA Land Use Data Summary**",
            f"- Records: {self.total_records:,}",
            f"- Counties: {self.counties:,}",
            f"- States: {self.states}",
            f"- Time range: {self.time_range[0]}-{self.time_range[1]}",
            f"- Scenarios: {', '.join(self.scenarios)}",
            f"- Land uses: {', '.join(self.land_use_types)}",
            f"\n*Coverage: {self.coverage}*",
            f"*Key assumption: {self.key_assumption}*",
        ]
        return "\n".join(lines)
