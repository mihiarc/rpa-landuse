"""Public API for RPA Land Use data access.

This module provides a clean, synchronous Python API for chatbot agents
to query RPA land use projection data from DuckDB.

Example:
    >>> from landuse.api import LandUseAPI
    >>> with LandUseAPI() as api:
    ...     result = api.get_land_use_area(states=["CA", "TX"], land_use="forest")
    ...     if result.success:
    ...         print(result.to_llm_string())

For Claude tool definitions:
    >>> from landuse.api import LandUseAPI, Scenario, LandUse, Metric
    >>> tools = [{
    ...     "name": "get_land_use_area",
    ...     "description": "Query land use area for US states",
    ...     "input_schema": {
    ...         "type": "object",
    ...         "properties": {
    ...             "states": {"type": "array", "items": {"type": "string"}},
    ...             "land_use": {"type": "string", "enum": [e.value for e in LandUse]},
    ...             "scenario": {"type": "string", "enum": [e.value for e in Scenario]}
    ...         },
    ...         "required": ["states"]
    ...     }
    ... }]
"""

from landuse.api.client import LandUseAPI
from landuse.api.models import (
    # Enums for query parameters
    ChangeType,
    LandUse,
    Metric,
    Scenario,
    # Result models
    AgriculturalChangeResult,
    APIResult,
    CountyResult,
    DataSummaryResult,
    ErrorResult,
    ForestChangeResult,
    LandUseAreaResult,
    RankedCounty,
    ScenarioComparisonResult,
    StateComparisonResult,
    StateRanking,
    TimeSeriesPoint,
    TimeSeriesResult,
    TopCountiesResult,
    TransitionRecord,
    TransitionsResult,
    UrbanExpansionResult,
)

__all__ = [
    # Main API class
    "LandUseAPI",
    # Enums
    "Scenario",
    "LandUse",
    "Metric",
    "ChangeType",
    # Base result
    "APIResult",
    "ErrorResult",
    # Query results
    "LandUseAreaResult",
    "TransitionsResult",
    "TransitionRecord",
    "UrbanExpansionResult",
    "ForestChangeResult",
    "AgriculturalChangeResult",
    "ScenarioComparisonResult",
    "StateComparisonResult",
    "StateRanking",
    "TimeSeriesResult",
    "TimeSeriesPoint",
    "CountyResult",
    "TopCountiesResult",
    "RankedCounty",
    "DataSummaryResult",
]
