"""
Land Use Service - Encapsulates all DuckDB queries for RPA land use data.

This service provides high-level query methods that tools can call,
keeping SQL generation away from the LLM.
"""

import logging
import os
from typing import Any

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

# Scenario code mappings
SCENARIO_MAPPING = {
    "LM": ("RCP45", "SSP1"),  # Lower-Moderate: Sustainability
    "HM": ("RCP85", "SSP2"),  # High-Moderate: Middle Road
    "HL": ("RCP85", "SSP3"),  # High-Low: Regional Rivalry
    "HH": ("RCP85", "SSP5"),  # High-High: Fossil Development
}

SCENARIO_NAMES = {
    "LM": "LM (Lower-Moderate: Sustainability)",
    "HM": "HM (High-Moderate: Middle Road)",
    "HL": "HL (High-Low: Regional Rivalry)",
    "HH": "HH (High-High: Fossil Development)",
}

# Land use type mappings
LANDUSE_TYPES = {
    "crop": "Crop",
    "pasture": "Pasture",
    "forest": "Forest",
    "urban": "Urban",
    "rangeland": "Rangeland",
}

# US State abbreviations to full names
STATE_NAMES = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
    "DC": "District of Columbia",
}

# Region mappings
REGIONS = {
    "Northeast": ["CT", "DE", "MA", "MD", "ME", "NH", "NJ", "NY", "PA", "RI", "VT"],
    "Southeast": ["AL", "AR", "FL", "GA", "KY", "LA", "MS", "NC", "SC", "TN", "VA", "WV"],
    "Midwest": ["IA", "IL", "IN", "KS", "MI", "MN", "MO", "ND", "NE", "OH", "SD", "WI"],
    "Southwest": ["AZ", "NM", "OK", "TX"],
    "West": ["CA", "CO", "ID", "MT", "NV", "OR", "UT", "WA", "WY"],
    "Pacific": ["AK", "HI"],
}


class LandUseService:
    """Service for querying RPA land use data from DuckDB."""

    def __init__(self, db_path: str | None = None):
        """Initialize the service with database path."""
        self.db_path = db_path or os.getenv(
            "LANDUSE_DATABASE_PATH",
            os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb"),
        )
        self._connection: duckdb.DuckDBPyConnection | None = None

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection.

        Note: read_only=False allows sharing connection config with other services
        (e.g., AcademicUserService) that write to the same MotherDuck database.
        """
        if self._connection is None:
            self._connection = duckdb.connect(self.db_path, read_only=False)
        return self._connection

    def _scenario_filter(self, scenario: str | None) -> tuple[str, list]:
        """Build scenario filter clause."""
        if not scenario:
            return "", []

        scenario = scenario.upper()
        if scenario not in SCENARIO_MAPPING:
            return "", []

        rcp, ssp = SCENARIO_MAPPING[scenario]
        return "AND s.rcp_scenario = ? AND s.ssp_scenario = ?", [rcp, ssp]

    def _states_filter(self, states: list[str]) -> tuple[str, list]:
        """Build states filter clause using state abbreviations or names."""
        if not states:
            return "", []

        # Convert abbreviations to full state names
        state_names = []
        for s in states:
            s_upper = s.upper()
            if s_upper in STATE_NAMES:
                state_names.append(STATE_NAMES[s_upper])
            else:
                # Assume it's already a full state name
                state_names.append(s.title())

        placeholders = ", ".join(["?" for _ in state_names])
        return f"AND g.state_name IN ({placeholders})", state_names

    def _landuse_filter(self, land_use: str | None, prefix: str = "fl") -> tuple[str, list]:
        """Build land use filter clause."""
        if not land_use:
            return "", []

        # Normalize the land use name
        land_use_name = LANDUSE_TYPES.get(land_use.lower(), land_use.title())
        return f"AND {prefix}.landuse_name = ?", [land_use_name]

    def _year_filter(self, year: int | None) -> tuple[str, list]:
        """Build year filter clause (matches time periods containing the year)."""
        if not year:
            return "", []
        return "AND t.start_year <= ? AND t.end_year >= ?", [year, year]

    def _format_acres(self, acres: float) -> str:
        """Format acres with commas."""
        return f"{acres:,.0f}"

    def _format_percent(self, value: float) -> str:
        """Format percentage."""
        return f"{value:.1f}%"

    # ============== Core Query Methods ==============

    async def query_area(
        self,
        states: list[str],
        land_use: str | None = None,
        year: int | None = None,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        """
        Query land use area by state.

        Args:
            states: List of state abbreviations (e.g., ["CA", "TX"])
            land_use: Optional land use type filter (crop, pasture, forest, urban, rangeland)
            year: Optional year filter (will match containing time period)
            scenario: Optional scenario code (LM, HM, HL, HH)

        Returns:
            Dict with total acres, breakdown by land use, and metadata
        """
        conn = self._get_connection()

        # Build filters
        states_clause, states_params = self._states_filter(states)
        landuse_clause, landuse_params = self._landuse_filter(land_use, "l")
        year_clause, year_params = self._year_filter(year)
        scenario_clause, scenario_params = self._scenario_filter(scenario)

        # Query for current area (transition_type = 'same' means land staying in same use)
        query = f"""
        SELECT
            l.landuse_name,
            g.state_name,
            t.year_range,
            s.rcp_scenario,
            s.ssp_scenario,
            SUM(f.acres) as total_acres
        FROM fact_landuse_transitions f
        JOIN dim_landuse l ON f.from_landuse_id = l.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        WHERE f.from_landuse_id = f.to_landuse_id
        {states_clause}
        {landuse_clause}
        {year_clause}
        {scenario_clause}
        GROUP BY l.landuse_name, g.state_name, t.year_range, s.rcp_scenario, s.ssp_scenario
        ORDER BY total_acres DESC
        """

        params = states_params + landuse_params + year_params + scenario_params
        df = conn.execute(query, params).df()

        if df.empty:
            return {
                "error": "No data found for the specified filters",
                "states": states,
                "land_use": land_use,
                "year": year,
                "scenario": scenario,
            }

        # Aggregate results
        total_acres = float(df["total_acres"].sum())

        # Group by land use
        by_landuse = df.groupby("landuse_name")["total_acres"].sum().sort_values(ascending=False).to_dict()

        # Group by state
        by_state = df.groupby("state_name")["total_acres"].sum().sort_values(ascending=False).to_dict()

        return {
            "total_acres": total_acres,
            "total_acres_formatted": self._format_acres(total_acres),
            "by_landuse": {k: self._format_acres(v) for k, v in by_landuse.items()},
            "by_state": {k: self._format_acres(v) for k, v in by_state.items()},
            "states": states,
            "land_use": land_use,
            "year": year,
            "scenario": SCENARIO_NAMES.get(scenario.upper()) if scenario else None,
            "time_periods": df["year_range"].unique().tolist(),
            "source": "USDA Forest Service 2020 RPA Assessment",
        }

    async def query_transitions(
        self,
        states: list[str],
        from_use: str | None = None,
        to_use: str | None = None,
        year_range: str | None = None,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        """
        Query land use transitions (conversions between land use types).

        Args:
            states: List of state abbreviations
            from_use: Source land use type filter
            to_use: Destination land use type filter
            year_range: Time period filter (e.g., "2020-2030")
            scenario: Scenario code (LM, HM, HL, HH)

        Returns:
            Dict with transition data and totals
        """
        conn = self._get_connection()

        # Build filters
        states_clause, states_params = self._states_filter(states)
        from_clause, from_params = self._landuse_filter(from_use, "fl")
        to_clause, to_params = self._landuse_filter(to_use, "tl")
        scenario_clause, scenario_params = self._scenario_filter(scenario)

        # Year range filter
        year_clause = ""
        year_params = []
        if year_range:
            year_clause = "AND t.year_range = ?"
            year_params = [year_range]

        query = f"""
        SELECT
            fl.landuse_name as from_landuse,
            tl.landuse_name as to_landuse,
            g.state_name,
            t.year_range,
            s.rcp_scenario,
            s.ssp_scenario,
            SUM(f.acres) as transition_acres
        FROM fact_landuse_transitions f
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        WHERE f.transition_type = 'change'
        {states_clause}
        {from_clause}
        {to_clause}
        {year_clause}
        {scenario_clause}
        GROUP BY fl.landuse_name, tl.landuse_name, g.state_name, t.year_range, s.rcp_scenario, s.ssp_scenario
        ORDER BY transition_acres DESC
        """

        params = states_params + from_params + to_params + year_params + scenario_params
        df = conn.execute(query, params).df()

        if df.empty:
            return {
                "error": "No transitions found for the specified filters",
                "states": states,
                "from_use": from_use,
                "to_use": to_use,
                "year_range": year_range,
                "scenario": scenario,
            }

        total_transition_acres = float(df["transition_acres"].sum())

        # Group by transition type
        transitions = (
            df.groupby(["from_landuse", "to_landuse"])["transition_acres"].sum().sort_values(ascending=False).head(20)
        )

        transition_list = [
            {
                "from": idx[0],
                "to": idx[1],
                "acres": self._format_acres(val),
                "acres_raw": float(val),
            }
            for idx, val in transitions.items()
        ]

        return {
            "total_transition_acres": total_transition_acres,
            "total_formatted": self._format_acres(total_transition_acres),
            "transitions": transition_list,
            "states": states,
            "from_use": from_use,
            "to_use": to_use,
            "year_range": year_range,
            "scenario": SCENARIO_NAMES.get(scenario.upper()) if scenario else None,
            "source": "USDA Forest Service 2020 RPA Assessment",
        }

    async def query_urban_expansion(
        self,
        states: list[str],
        year_range: str | None = None,
        scenario: str | None = None,
        source_land_use: str | None = None,
    ) -> dict[str, Any]:
        """
        Query urban/developed land expansion.

        Args:
            states: List of state abbreviations
            year_range: Time period filter
            scenario: Scenario code
            source_land_use: Filter by source land use (what's converting to urban)

        Returns:
            Dict with urban expansion data
        """
        conn = self._get_connection()

        # Build filters
        states_clause, states_params = self._states_filter(states)
        scenario_clause, scenario_params = self._scenario_filter(scenario)
        source_clause, source_params = self._landuse_filter(source_land_use, "fl")

        year_clause = ""
        year_params = []
        if year_range:
            year_clause = "AND t.year_range = ?"
            year_params = [year_range]

        query = f"""
        SELECT
            fl.landuse_name as source_landuse,
            g.state_name,
            t.year_range,
            s.rcp_scenario,
            s.ssp_scenario,
            SUM(f.acres) as expansion_acres
        FROM fact_landuse_transitions f
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        WHERE tl.landuse_name = 'Urban'
        AND f.transition_type = 'change'
        {states_clause}
        {source_clause}
        {year_clause}
        {scenario_clause}
        GROUP BY fl.landuse_name, g.state_name, t.year_range, s.rcp_scenario, s.ssp_scenario
        ORDER BY expansion_acres DESC
        """

        params = states_params + source_params + year_params + scenario_params
        df = conn.execute(query, params).df()

        if df.empty:
            return {
                "error": "No urban expansion data found",
                "states": states,
                "year_range": year_range,
                "scenario": scenario,
            }

        total_expansion = float(df["expansion_acres"].sum())

        # By source land use
        by_source = df.groupby("source_landuse")["expansion_acres"].sum().sort_values(ascending=False).to_dict()

        # By state
        by_state = df.groupby("state_name")["expansion_acres"].sum().sort_values(ascending=False).to_dict()

        return {
            "total_expansion_acres": total_expansion,
            "total_formatted": self._format_acres(total_expansion),
            "by_source": {k: self._format_acres(v) for k, v in by_source.items()},
            "by_state": {k: self._format_acres(v) for k, v in by_state.items()},
            "states": states,
            "year_range": year_range,
            "scenario": SCENARIO_NAMES.get(scenario.upper()) if scenario else None,
            "note": "Urban development is assumed irreversible in RPA projections",
            "source": "USDA Forest Service 2020 RPA Assessment",
        }

    async def query_forest_change(
        self,
        states: list[str],
        year_range: str | None = None,
        scenario: str | None = None,
        change_type: str = "net",
    ) -> dict[str, Any]:
        """
        Query forest area changes.

        Args:
            states: List of state abbreviations
            year_range: Time period filter
            scenario: Scenario code
            change_type: "net", "loss", or "gain"

        Returns:
            Dict with forest change data
        """
        conn = self._get_connection()

        states_clause, states_params = self._states_filter(states)
        scenario_clause, scenario_params = self._scenario_filter(scenario)

        year_clause = ""
        year_params = []
        if year_range:
            year_clause = "AND t.year_range = ?"
            year_params = [year_range]

        # Query for forest losses (Forest -> Other)
        loss_query = f"""
        SELECT
            tl.landuse_name as to_use,
            g.state_name,
            t.year_range,
            SUM(f.acres) as acres
        FROM fact_landuse_transitions f
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        WHERE fl.landuse_name = 'Forest'
        AND f.transition_type = 'change'
        {states_clause}
        {year_clause}
        {scenario_clause}
        GROUP BY tl.landuse_name, g.state_name, t.year_range
        """

        # Query for forest gains (Other -> Forest)
        gain_query = f"""
        SELECT
            fl.landuse_name as from_use,
            g.state_name,
            t.year_range,
            SUM(f.acres) as acres
        FROM fact_landuse_transitions f
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        WHERE tl.landuse_name = 'Forest'
        AND f.transition_type = 'change'
        {states_clause}
        {year_clause}
        {scenario_clause}
        GROUP BY fl.landuse_name, g.state_name, t.year_range
        """

        params = states_params + year_params + scenario_params

        loss_df = conn.execute(loss_query, params).df()
        gain_df = conn.execute(gain_query, params).df()

        total_loss = float(loss_df["acres"].sum()) if not loss_df.empty else 0
        total_gain = float(gain_df["acres"].sum()) if not gain_df.empty else 0
        net_change = total_gain - total_loss

        result = {
            "states": states,
            "year_range": year_range,
            "scenario": SCENARIO_NAMES.get(scenario.upper()) if scenario else None,
            "source": "USDA Forest Service 2020 RPA Assessment",
        }

        if change_type == "loss" or change_type == "net":
            result["forest_loss_acres"] = total_loss
            result["forest_loss_formatted"] = self._format_acres(total_loss)
            if not loss_df.empty:
                by_dest = loss_df.groupby("to_use")["acres"].sum().sort_values(ascending=False)
                result["loss_by_destination"] = {k: self._format_acres(v) for k, v in by_dest.items()}

        if change_type == "gain" or change_type == "net":
            result["forest_gain_acres"] = total_gain
            result["forest_gain_formatted"] = self._format_acres(total_gain)
            if not gain_df.empty:
                by_source = gain_df.groupby("from_use")["acres"].sum().sort_values(ascending=False)
                result["gain_by_source"] = {k: self._format_acres(v) for k, v in by_source.items()}

        if change_type == "net":
            result["net_change_acres"] = net_change
            result["net_change_formatted"] = self._format_acres(abs(net_change))
            result["net_direction"] = "gain" if net_change > 0 else "loss"

        return result

    async def query_agricultural_change(
        self,
        states: list[str],
        ag_type: str | None = None,
        year_range: str | None = None,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        """
        Query agricultural land changes.

        Args:
            states: List of state abbreviations
            ag_type: "crop", "pasture", or None for both
            year_range: Time period filter
            scenario: Scenario code

        Returns:
            Dict with agricultural land change data
        """
        conn = self._get_connection()

        states_clause, states_params = self._states_filter(states)
        scenario_clause, scenario_params = self._scenario_filter(scenario)

        year_clause = ""
        year_params = []
        if year_range:
            year_clause = "AND t.year_range = ?"
            year_params = [year_range]

        # Determine which ag types to query
        ag_types = []
        if ag_type:
            ag_types = [LANDUSE_TYPES.get(ag_type.lower(), ag_type.title())]
        else:
            ag_types = ["Crop", "Pasture"]

        ag_placeholders = ", ".join(["?" for _ in ag_types])

        # Query for ag losses
        loss_query = f"""
        SELECT
            fl.landuse_name as ag_type,
            tl.landuse_name as to_use,
            g.state_name,
            t.year_range,
            SUM(f.acres) as acres
        FROM fact_landuse_transitions f
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        WHERE fl.landuse_name IN ({ag_placeholders})
        AND f.transition_type = 'change'
        {states_clause}
        {year_clause}
        {scenario_clause}
        GROUP BY fl.landuse_name, tl.landuse_name, g.state_name, t.year_range
        """

        params = ag_types + states_params + year_params + scenario_params
        loss_df = conn.execute(loss_query, params).df()

        if loss_df.empty:
            return {
                "error": "No agricultural change data found",
                "states": states,
                "ag_type": ag_type,
                "year_range": year_range,
                "scenario": scenario,
            }

        total_loss = float(loss_df["acres"].sum())

        # By ag type
        by_ag_type = loss_df.groupby("ag_type")["acres"].sum().sort_values(ascending=False).to_dict()

        # By destination
        by_destination = loss_df.groupby("to_use")["acres"].sum().sort_values(ascending=False).to_dict()

        # By state
        by_state = loss_df.groupby("state_name")["acres"].sum().sort_values(ascending=False).to_dict()

        return {
            "total_ag_loss_acres": total_loss,
            "total_formatted": self._format_acres(total_loss),
            "by_ag_type": {k: self._format_acres(v) for k, v in by_ag_type.items()},
            "by_destination": {k: self._format_acres(v) for k, v in by_destination.items()},
            "by_state": {k: self._format_acres(v) for k, v in by_state.items()},
            "states": states,
            "ag_type": ag_type,
            "year_range": year_range,
            "scenario": SCENARIO_NAMES.get(scenario.upper()) if scenario else None,
            "source": "USDA Forest Service 2020 RPA Assessment",
        }

    async def compare_scenarios(
        self,
        states: list[str],
        metric: str,
        scenarios: list[str] | None = None,
        year: int | None = None,
    ) -> dict[str, Any]:
        """
        Compare land use metrics across scenarios.

        Args:
            states: List of state abbreviations
            metric: Metric to compare (urban_expansion, forest_loss, ag_loss)
            scenarios: List of scenario codes to compare (default: all 4)
            year: Year filter

        Returns:
            Dict with comparison data
        """
        if not scenarios:
            scenarios = ["LM", "HM", "HL", "HH"]

        results = {}
        for scenario in scenarios:
            if metric == "urban_expansion":
                data = await self.query_urban_expansion(states, scenario=scenario)
                results[scenario] = {
                    "name": SCENARIO_NAMES.get(scenario.upper(), scenario),
                    "acres": data.get("total_expansion_acres", 0),
                    "formatted": data.get("total_formatted", "0"),
                }
            elif metric == "forest_loss":
                data = await self.query_forest_change(states, scenario=scenario, change_type="loss")
                results[scenario] = {
                    "name": SCENARIO_NAMES.get(scenario.upper(), scenario),
                    "acres": data.get("forest_loss_acres", 0),
                    "formatted": data.get("forest_loss_formatted", "0"),
                }
            elif metric == "ag_loss":
                data = await self.query_agricultural_change(states, scenario=scenario)
                results[scenario] = {
                    "name": SCENARIO_NAMES.get(scenario.upper(), scenario),
                    "acres": data.get("total_ag_loss_acres", 0),
                    "formatted": data.get("total_formatted", "0"),
                }

        # Sort by acres descending
        sorted_results = dict(sorted(results.items(), key=lambda x: x[1]["acres"], reverse=True))

        return {
            "metric": metric,
            "states": states,
            "year": year,
            "comparison": sorted_results,
            "highest": list(sorted_results.keys())[0] if sorted_results else None,
            "lowest": list(sorted_results.keys())[-1] if sorted_results else None,
            "source": "USDA Forest Service 2020 RPA Assessment",
        }

    async def compare_states(
        self,
        states: list[str],
        metric: str,
        scenario: str | None = None,
        year: int | None = None,
    ) -> dict[str, Any]:
        """
        Compare land use metrics across states.

        Args:
            states: List of state abbreviations to compare
            metric: Metric to compare
            scenario: Scenario code
            year: Year filter

        Returns:
            Dict with state comparison data
        """
        conn = self._get_connection()

        states_clause, states_params = self._states_filter(states)
        scenario_clause, scenario_params = self._scenario_filter(scenario)
        year_clause, year_params = self._year_filter(year)

        if metric == "urban_expansion":
            query = f"""
            SELECT
                g.state_name,
                g.state_name,
                SUM(f.acres) as total_acres
            FROM fact_landuse_transitions f
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            WHERE tl.landuse_name = 'Urban'
            AND f.transition_type = 'change'
            {states_clause}
            {year_clause}
            {scenario_clause}
            GROUP BY g.state_name, g.state_name
            ORDER BY total_acres DESC
            """
        elif metric == "forest_loss":
            query = f"""
            SELECT
                g.state_name,
                g.state_name,
                SUM(f.acres) as total_acres
            FROM fact_landuse_transitions f
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            WHERE fl.landuse_name = 'Forest'
            AND f.transition_type = 'change'
            {states_clause}
            {year_clause}
            {scenario_clause}
            GROUP BY g.state_name, g.state_name
            ORDER BY total_acres DESC
            """
        elif metric in ("land_area", "total_area"):
            query = f"""
            SELECT
                g.state_name,
                g.state_name,
                SUM(f.acres) as total_acres
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            WHERE f.transition_type = 'same'
            {states_clause}
            {year_clause}
            {scenario_clause}
            GROUP BY g.state_name, g.state_name
            ORDER BY total_acres DESC
            """
        else:
            return {"error": f"Unknown metric: {metric}"}

        params = states_params + year_params + scenario_params
        df = conn.execute(query, params).df()

        if df.empty:
            return {
                "error": "No data found for comparison",
                "states": states,
                "metric": metric,
            }

        comparison = [
            {
                "state": row["state_name"],
                "state_name": row["state_name"],
                "acres": float(row["total_acres"]),
                "formatted": self._format_acres(row["total_acres"]),
            }
            for _, row in df.iterrows()
        ]

        return {
            "metric": metric,
            "scenario": SCENARIO_NAMES.get(scenario.upper()) if scenario else None,
            "year": year,
            "comparison": comparison,
            "highest": comparison[0] if comparison else None,
            "lowest": comparison[-1] if comparison else None,
            "source": "USDA Forest Service 2020 RPA Assessment",
        }

    async def query_time_series(
        self,
        states: list[str],
        metric: str,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        """
        Query time series data for a metric.

        Args:
            states: List of state abbreviations
            metric: Metric to track (urban_area, forest_area, etc.)
            scenario: Scenario code

        Returns:
            Dict with time series data
        """
        conn = self._get_connection()

        states_clause, states_params = self._states_filter(states)
        scenario_clause, scenario_params = self._scenario_filter(scenario)

        if metric in ("urban_area", "urban"):
            landuse_filter = "AND l.landuse_name = 'Urban'"
        elif metric in ("forest_area", "forest"):
            landuse_filter = "AND l.landuse_name = 'Forest'"
        elif metric in ("crop_area", "crop"):
            landuse_filter = "AND l.landuse_name = 'Crop'"
        elif metric in ("pasture_area", "pasture"):
            landuse_filter = "AND l.landuse_name = 'Pasture'"
        elif metric in ("rangeland_area", "rangeland"):
            landuse_filter = "AND l.landuse_name = 'Rangeland'"
        else:
            landuse_filter = ""

        query = f"""
        SELECT
            t.year_range,
            t.start_year,
            t.end_year,
            SUM(f.acres) as total_acres
        FROM fact_landuse_transitions f
        JOIN dim_landuse l ON f.from_landuse_id = l.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        WHERE f.from_landuse_id = f.to_landuse_id
        {landuse_filter}
        {states_clause}
        {scenario_clause}
        GROUP BY t.year_range, t.start_year, t.end_year
        ORDER BY t.start_year
        """

        params = states_params + scenario_params
        df = conn.execute(query, params).df()

        if df.empty:
            return {
                "error": "No time series data found",
                "states": states,
                "metric": metric,
            }

        time_series = [
            {
                "period": row["year_range"],
                "start_year": int(row["start_year"]),
                "end_year": int(row["end_year"]),
                "acres": float(row["total_acres"]),
                "formatted": self._format_acres(row["total_acres"]),
            }
            for _, row in df.iterrows()
        ]

        # Calculate trend
        if len(time_series) >= 2:
            first = time_series[0]["acres"]
            last = time_series[-1]["acres"]
            change = last - first
            pct_change = (change / first * 100) if first > 0 else 0
            trend = {
                "direction": "increasing" if change > 0 else "decreasing",
                "change_acres": self._format_acres(abs(change)),
                "change_percent": self._format_percent(abs(pct_change)),
            }
        else:
            trend = None

        return {
            "metric": metric,
            "states": states,
            "scenario": SCENARIO_NAMES.get(scenario.upper()) if scenario else None,
            "time_series": time_series,
            "trend": trend,
            "source": "USDA Forest Service 2020 RPA Assessment",
        }

    async def query_by_county(
        self,
        state: str,
        county: str,
        metric: str,
        year: int | None = None,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        """
        Query land use metrics for a specific county.

        Args:
            state: State abbreviation
            county: County name
            metric: Metric to query
            year: Year filter
            scenario: Scenario code

        Returns:
            Dict with county data
        """
        conn = self._get_connection()

        scenario_clause, scenario_params = self._scenario_filter(scenario)
        year_clause, year_params = self._year_filter(year)

        # Find the county - convert state abbrev to full name
        state_full = STATE_NAMES.get(state.upper(), state.title())
        county_query = """
        SELECT geography_id, county_name, state_name, fips_code
        FROM dim_geography
        WHERE state_name = ?
        AND LOWER(county_name) LIKE ?
        LIMIT 1
        """
        county_df = conn.execute(county_query, [state_full, f"%{county.lower()}%"]).df()

        if county_df.empty:
            return {
                "error": f"County '{county}' not found in {state}",
                "state": state,
                "county": county,
            }

        geo_id = int(county_df["geography_id"].iloc[0])
        county_name = county_df["county_name"].iloc[0]
        fips = county_df["fips_code"].iloc[0]

        # Query the metric
        if metric in ("land_area", "area"):
            query = f"""
            SELECT
                l.landuse_name,
                t.year_range,
                SUM(f.acres) as total_acres
            FROM fact_landuse_transitions f
            JOIN dim_landuse l ON f.from_landuse_id = l.landuse_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            WHERE f.geography_id = ?
            AND f.from_landuse_id = f.to_landuse_id
            {year_clause}
            {scenario_clause}
            GROUP BY l.landuse_name, t.year_range
            ORDER BY total_acres DESC
            """
            params = [geo_id] + year_params + scenario_params
            df = conn.execute(query, params).df()

            by_landuse = df.groupby("landuse_name")["total_acres"].sum().sort_values(ascending=False).to_dict()

            return {
                "county": county_name,
                "state": state.upper(),
                "fips": fips,
                "metric": metric,
                "total_acres": float(df["total_acres"].sum()),
                "by_landuse": {k: self._format_acres(v) for k, v in by_landuse.items()},
                "scenario": SCENARIO_NAMES.get(scenario.upper()) if scenario else None,
                "source": "USDA Forest Service 2020 RPA Assessment",
            }

        return {"error": f"Unknown metric: {metric}"}

    async def query_top_counties(
        self,
        metric: str,
        limit: int = 10,
        states: list[str] | None = None,
        scenario: str | None = None,
    ) -> dict[str, Any]:
        """
        Find top counties by a metric.

        Args:
            metric: Metric to rank by (urban_growth, forest_loss, etc.)
            limit: Number of counties to return
            states: Optional state filter
            scenario: Scenario code

        Returns:
            Dict with top counties
        """
        conn = self._get_connection()

        states_clause, states_params = self._states_filter(states or [])
        scenario_clause, scenario_params = self._scenario_filter(scenario)

        if metric == "urban_growth":
            query = f"""
            SELECT
                g.county_name,
                g.state_name,
                g.fips_code,
                SUM(f.acres) as total_acres
            FROM fact_landuse_transitions f
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            WHERE tl.landuse_name = 'Urban'
            AND f.transition_type = 'change'
            {states_clause}
            {scenario_clause}
            GROUP BY g.county_name, g.state_name, g.fips_code
            ORDER BY total_acres DESC
            LIMIT ?
            """
        elif metric == "forest_loss":
            query = f"""
            SELECT
                g.county_name,
                g.state_name,
                g.fips_code,
                SUM(f.acres) as total_acres
            FROM fact_landuse_transitions f
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            WHERE fl.landuse_name = 'Forest'
            AND f.transition_type = 'change'
            {states_clause}
            {scenario_clause}
            GROUP BY g.county_name, g.state_name, g.fips_code
            ORDER BY total_acres DESC
            LIMIT ?
            """
        else:
            return {"error": f"Unknown metric: {metric}"}

        params = states_params + scenario_params + [limit]
        df = conn.execute(query, params).df()

        if df.empty:
            return {
                "error": "No data found",
                "metric": metric,
            }

        counties = [
            {
                "rank": i + 1,
                "county": row["county_name"],
                "state": row["state_name"],
                "fips": row["fips_code"],
                "acres": float(row["total_acres"]),
                "formatted": self._format_acres(row["total_acres"]),
            }
            for i, (_, row) in enumerate(df.iterrows())
        ]

        return {
            "metric": metric,
            "limit": limit,
            "states": states,
            "scenario": SCENARIO_NAMES.get(scenario.upper()) if scenario else None,
            "counties": counties,
            "source": "USDA Forest Service 2020 RPA Assessment",
        }

    async def get_data_summary(
        self,
        geography: str | None = None,
    ) -> dict[str, Any]:
        """
        Get summary statistics about available data.

        Args:
            geography: Optional state filter

        Returns:
            Dict with data summary
        """
        conn = self._get_connection()

        # Get counts
        fact_count = conn.execute("SELECT COUNT(*) FROM fact_landuse_transitions").fetchone()[0]
        county_count = conn.execute("SELECT COUNT(DISTINCT geography_id) FROM dim_geography").fetchone()[0]
        state_count = conn.execute("SELECT COUNT(DISTINCT state_name) FROM dim_geography").fetchone()[0]

        # Get time range
        time_df = conn.execute("""
            SELECT MIN(start_year) as min_year, MAX(end_year) as max_year
            FROM dim_time
        """).df()

        # Get scenarios
        scenarios = conn.execute("""
            SELECT DISTINCT rcp_scenario, ssp_scenario
            FROM dim_scenario
            ORDER BY rcp_scenario, ssp_scenario
        """).df()

        # Get land use types
        landuse_df = conn.execute("SELECT landuse_name FROM dim_landuse ORDER BY landuse_name").df()

        return {
            "total_records": int(fact_count),
            "counties": int(county_count),
            "states": int(state_count),
            "time_range": {
                "start": int(time_df["min_year"].iloc[0]),
                "end": int(time_df["max_year"].iloc[0]),
            },
            "scenarios": [{"rcp": row["rcp_scenario"], "ssp": row["ssp_scenario"]} for _, row in scenarios.iterrows()],
            "scenario_codes": list(SCENARIO_NAMES.keys()),
            "land_use_types": landuse_df["landuse_name"].tolist(),
            "source": "USDA Forest Service 2020 RPA Assessment",
            "coverage": "Private lands only (public lands assumed static)",
            "key_assumption": "Urban development is irreversible",
        }

    def close(self):
        """Close database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


# Singleton instance
landuse_service = LandUseService()
