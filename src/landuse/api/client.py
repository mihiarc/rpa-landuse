"""LandUseAPI - Direct DuckDB access for chatbot agents.

This module provides a clean, synchronous Python API for querying RPA land use
data. Designed for Claude tool calling with structured Pydantic outputs and
LLM-optimized string formatting.

Example:
    >>> from landuse.api import LandUseAPI
    >>> with LandUseAPI() as api:
    ...     result = api.get_land_use_area(states=["CA", "TX"], land_use="forest")
    ...     print(result.to_llm_string())
"""

import os

import duckdb
from rich.console import Console

from landuse.api.formatters import format_acres, format_percent, format_state_abbrev
from landuse.api.models import (
    AgriculturalChangeResult,
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
from landuse.api.queries import QueryBuilder, SCENARIO_NAMES


class LandUseAPI:
    """Python API for chatbot agent access to RPA land use data.

    All methods return Pydantic models with to_llm_string() for Claude.
    Never raises exceptions - returns ErrorResult on failure.

    Attributes:
        db_path: Path to the DuckDB database file

    Example:
        >>> api = LandUseAPI()
        >>> result = api.get_land_use_area(states=["CA"])
        >>> if result.success:
        ...     print(result.total_formatted)
    """

    def __init__(
        self,
        db_path: str | None = None,
        verbose: bool = False,
    ):
        """Initialize the API.

        Args:
            db_path: Path to DuckDB database. Defaults to LANDUSE_DB_PATH or
                     LANDUSE_DATABASE_PATH environment variable.
            verbose: Enable Rich console output for debugging.
        """
        self.db_path = db_path or os.getenv(
            "LANDUSE_DATABASE_PATH",
            os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb"),
        )
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._console = Console() if verbose else None

    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = duckdb.connect(self.db_path, read_only=True)
        return self._conn

    def _log(self, message: str, style: str = "green") -> None:
        """Log to console if verbose mode is enabled."""
        if self._console:
            self._console.print(f"[{style}]{message}[/{style}]")

    def _error(
        self,
        message: str,
        code: str,
        suggestion: str | None = None,
    ) -> ErrorResult:
        """Create error result with optional suggestion."""
        self._log(f"Error: {message}", "red")
        return ErrorResult(
            error_message=message,
            error_code=code,
            suggestion=suggestion,
        )

    def get_land_use_area(
        self,
        states: list[str],
        land_use: str | None = None,
        year: int | None = None,
        scenario: str | None = None,
    ) -> LandUseAreaResult | ErrorResult:
        """Query land use area by state.

        Args:
            states: Two-letter state codes (e.g., ["CA", "TX"])
            land_use: Filter by type: crop, pasture, forest, urban, rangeland
            year: Filter by year (matches containing time period)
            scenario: Scenario code: LM, HM, HL, HH

        Returns:
            LandUseAreaResult with area data or ErrorResult on failure
        """
        try:
            query = QueryBuilder.land_use_area(states, land_use, year, scenario)
            self._log(f"Executing: {query.description}")

            conn = self._get_conn()
            df = conn.execute(query.sql, query.params).df()

            if df.empty:
                return self._error(
                    "No data found for the specified filters",
                    "NO_DATA",
                    "Try broadening your query filters or check state codes",
                )

            total = float(df["total_acres"].sum())
            by_land_use = df.groupby("landuse_name")["total_acres"].sum().to_dict()
            by_state = df.groupby("state_name")["total_acres"].sum().to_dict()

            return LandUseAreaResult(
                total_acres=total,
                total_formatted=format_acres(total),
                by_land_use={k: format_acres(v) for k, v in by_land_use.items()},
                by_state={k: format_acres(v) for k, v in by_state.items()},
                filters={
                    "states": states,
                    "land_use": land_use,
                    "year": year,
                    "scenario": scenario,
                },
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def get_transitions(
        self,
        states: list[str],
        from_use: str | None = None,
        to_use: str | None = None,
        year_range: str | None = None,
        scenario: str | None = None,
    ) -> TransitionsResult | ErrorResult:
        """Query land use transitions.

        Args:
            states: Two-letter state codes
            from_use: Source land use type filter
            to_use: Destination land use type filter
            year_range: Time period filter (e.g., "2020-2030")
            scenario: Scenario code

        Returns:
            TransitionsResult with transition data or ErrorResult on failure
        """
        try:
            query = QueryBuilder.transitions(states, from_use, to_use, year_range, scenario)
            self._log(f"Executing: {query.description}")

            conn = self._get_conn()
            df = conn.execute(query.sql, query.params).df()

            if df.empty:
                return self._error(
                    "No transitions found for the specified filters",
                    "NO_DATA",
                    "Try broadening your query filters",
                )

            total = float(df["transition_acres"].sum())
            transitions = []
            grouped = df.groupby(["from_landuse", "to_landuse"])["transition_acres"].sum()
            for (from_lu, to_lu), acres in grouped.sort_values(ascending=False).head(20).items():
                transitions.append(
                    TransitionRecord(
                        from_use=from_lu,
                        to_use=to_lu,
                        acres=float(acres),
                        formatted=format_acres(acres),
                    )
                )

            return TransitionsResult(
                total_acres=total,
                total_formatted=format_acres(total),
                transitions=transitions,
                filters={
                    "states": states,
                    "from_use": from_use,
                    "to_use": to_use,
                    "year_range": year_range,
                    "scenario": scenario,
                },
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def get_urban_expansion(
        self,
        states: list[str],
        year_range: str | None = None,
        scenario: str | None = None,
        source_land_use: str | None = None,
    ) -> UrbanExpansionResult | ErrorResult:
        """Query urban expansion data.

        Args:
            states: Two-letter state codes
            year_range: Time period filter
            scenario: Scenario code
            source_land_use: Filter by source land use type

        Returns:
            UrbanExpansionResult with expansion data or ErrorResult on failure
        """
        try:
            query = QueryBuilder.urban_expansion(states, year_range, scenario, source_land_use)
            self._log(f"Executing: {query.description}")

            conn = self._get_conn()
            df = conn.execute(query.sql, query.params).df()

            if df.empty:
                return self._error(
                    "No urban expansion data found",
                    "NO_DATA",
                    "Try different filters or check state codes",
                )

            total = float(df["expansion_acres"].sum())
            by_source = df.groupby("source_landuse")["expansion_acres"].sum().to_dict()
            by_state = df.groupby("state_name")["expansion_acres"].sum().to_dict()

            return UrbanExpansionResult(
                total_acres=total,
                total_formatted=format_acres(total),
                by_source={k: format_acres(v) for k, v in by_source.items()},
                by_state={k: format_acres(v) for k, v in by_state.items()},
                filters={
                    "states": states,
                    "year_range": year_range,
                    "scenario": scenario,
                    "source_land_use": source_land_use,
                },
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def get_forest_change(
        self,
        states: list[str],
        year_range: str | None = None,
        scenario: str | None = None,
        change_type: str = "net",
    ) -> ForestChangeResult | ErrorResult:
        """Query forest area changes.

        Args:
            states: Two-letter state codes
            year_range: Time period filter
            scenario: Scenario code
            change_type: "net", "loss", or "gain"

        Returns:
            ForestChangeResult with forest change data or ErrorResult on failure
        """
        try:
            conn = self._get_conn()

            # Query forest loss
            loss_query = QueryBuilder.forest_loss(states, year_range, scenario)
            loss_df = conn.execute(loss_query.sql, loss_query.params).df()

            # Query forest gain
            gain_query = QueryBuilder.forest_gain(states, year_range, scenario)
            gain_df = conn.execute(gain_query.sql, gain_query.params).df()

            total_loss = float(loss_df["acres"].sum()) if not loss_df.empty else 0.0
            total_gain = float(gain_df["acres"].sum()) if not gain_df.empty else 0.0
            net_change = total_gain - total_loss

            # Build result based on change_type
            result_data: dict = {
                "filters": {
                    "states": states,
                    "year_range": year_range,
                    "scenario": scenario,
                    "change_type": change_type,
                },
            }

            if change_type in ("loss", "net"):
                result_data["loss_acres"] = total_loss
                result_data["loss_formatted"] = format_acres(total_loss)
                if not loss_df.empty:
                    loss_by_dest = loss_df.groupby("to_use")["acres"].sum().to_dict()
                    result_data["loss_by_destination"] = {
                        k: format_acres(v) for k, v in loss_by_dest.items()
                    }

            if change_type in ("gain", "net"):
                result_data["gain_acres"] = total_gain
                result_data["gain_formatted"] = format_acres(total_gain)
                if not gain_df.empty:
                    gain_by_src = gain_df.groupby("from_use")["acres"].sum().to_dict()
                    result_data["gain_by_source"] = {
                        k: format_acres(v) for k, v in gain_by_src.items()
                    }

            if change_type == "net":
                result_data["net_acres"] = abs(net_change)
                result_data["net_formatted"] = format_acres(abs(net_change))
                result_data["net_direction"] = "gain" if net_change > 0 else "loss"

            return ForestChangeResult(**result_data)

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def get_agricultural_change(
        self,
        states: list[str],
        ag_type: str | None = None,
        year_range: str | None = None,
        scenario: str | None = None,
    ) -> AgriculturalChangeResult | ErrorResult:
        """Query agricultural land changes.

        Args:
            states: Two-letter state codes
            ag_type: "crop", "pasture", or None for both
            year_range: Time period filter
            scenario: Scenario code

        Returns:
            AgriculturalChangeResult with change data or ErrorResult on failure
        """
        try:
            query = QueryBuilder.agricultural_change(states, ag_type, year_range, scenario)
            self._log(f"Executing: {query.description}")

            conn = self._get_conn()
            df = conn.execute(query.sql, query.params).df()

            if df.empty:
                return self._error(
                    "No agricultural change data found",
                    "NO_DATA",
                    "Try broadening your query filters",
                )

            total_loss = float(df["acres"].sum())
            by_ag_type = df.groupby("ag_type")["acres"].sum().to_dict()
            by_destination = df.groupby("to_use")["acres"].sum().to_dict()
            by_state = df.groupby("state_name")["acres"].sum().to_dict()

            return AgriculturalChangeResult(
                total_loss_acres=total_loss,
                total_loss_formatted=format_acres(total_loss),
                by_ag_type={k: format_acres(v) for k, v in by_ag_type.items()},
                by_destination={k: format_acres(v) for k, v in by_destination.items()},
                by_state={k: format_acres(v) for k, v in by_state.items()},
                filters={
                    "states": states,
                    "ag_type": ag_type,
                    "year_range": year_range,
                    "scenario": scenario,
                },
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def compare_scenarios(
        self,
        states: list[str],
        metric: str,
        scenarios: list[str] | None = None,
    ) -> ScenarioComparisonResult | ErrorResult:
        """Compare land use metrics across scenarios.

        Args:
            states: Two-letter state codes
            metric: Metric to compare (urban_expansion, forest_loss, ag_loss)
            scenarios: List of scenario codes to compare (default: all 4)

        Returns:
            ScenarioComparisonResult with comparison data or ErrorResult on failure
        """
        try:
            if not scenarios:
                scenarios = ["LM", "HM", "HL", "HH"]

            results: dict[str, dict] = {}

            for scenario in scenarios:
                scenario_upper = scenario.upper()
                if metric == "urban_expansion":
                    data = self.get_urban_expansion(states, scenario=scenario_upper)
                    if data.success:
                        results[scenario_upper] = {
                            "name": SCENARIO_NAMES.get(scenario_upper, scenario_upper),
                            "acres": data.total_acres,
                            "formatted": data.total_formatted,
                        }
                elif metric == "forest_loss":
                    data = self.get_forest_change(states, scenario=scenario_upper, change_type="loss")
                    if data.success and data.loss_acres is not None:
                        results[scenario_upper] = {
                            "name": SCENARIO_NAMES.get(scenario_upper, scenario_upper),
                            "acres": data.loss_acres,
                            "formatted": data.loss_formatted,
                        }
                elif metric == "ag_loss":
                    data = self.get_agricultural_change(states, scenario=scenario_upper)
                    if data.success:
                        results[scenario_upper] = {
                            "name": SCENARIO_NAMES.get(scenario_upper, scenario_upper),
                            "acres": data.total_loss_acres,
                            "formatted": data.total_loss_formatted,
                        }

            if not results:
                return self._error(
                    "No comparison data found",
                    "NO_DATA",
                    "Check that the metric is valid and states have data",
                )

            # Sort by acres descending
            sorted_results = dict(
                sorted(results.items(), key=lambda x: x[1]["acres"], reverse=True)
            )
            keys = list(sorted_results.keys())

            return ScenarioComparisonResult(
                metric=metric,
                comparison=sorted_results,
                highest=keys[0] if keys else None,
                lowest=keys[-1] if keys else None,
                filters={"states": states, "scenarios": scenarios},
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def compare_states(
        self,
        states: list[str],
        metric: str,
        scenario: str | None = None,
        year: int | None = None,
    ) -> StateComparisonResult | ErrorResult:
        """Compare land use metrics across states.

        Args:
            states: List of two-letter state codes to compare
            metric: Metric to compare (urban_expansion, forest_loss, land_area)
            scenario: Scenario code
            year: Year filter

        Returns:
            StateComparisonResult with rankings or ErrorResult on failure
        """
        try:
            query = QueryBuilder.state_comparison(states, metric, scenario, year)
            self._log(f"Executing: {query.description}")

            conn = self._get_conn()
            df = conn.execute(query.sql, query.params).df()

            if df.empty:
                return self._error(
                    "No comparison data found",
                    "NO_DATA",
                    "Check state codes and metric name",
                )

            rankings = []
            for _, row in df.iterrows():
                state_name = row["state_name"]
                rankings.append(
                    StateRanking(
                        state=state_name,
                        state_abbrev=format_state_abbrev(state_name),
                        acres=float(row["total_acres"]),
                        formatted=format_acres(row["total_acres"]),
                    )
                )

            return StateComparisonResult(
                metric=metric,
                rankings=rankings,
                filters={
                    "states": states,
                    "scenario": scenario,
                    "year": year,
                },
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def get_time_series(
        self,
        states: list[str],
        metric: str,
        scenario: str | None = None,
    ) -> TimeSeriesResult | ErrorResult:
        """Query time series data for a metric.

        Args:
            states: Two-letter state codes
            metric: Metric to track (urban_area, forest_area, etc.)
            scenario: Scenario code

        Returns:
            TimeSeriesResult with time series data or ErrorResult on failure
        """
        try:
            query = QueryBuilder.time_series(states, metric, scenario)
            self._log(f"Executing: {query.description}")

            conn = self._get_conn()
            df = conn.execute(query.sql, query.params).df()

            if df.empty:
                return self._error(
                    "No time series data found",
                    "NO_DATA",
                    "Check state codes and metric name",
                )

            data_points = []
            for _, row in df.iterrows():
                data_points.append(
                    TimeSeriesPoint(
                        period=row["year_range"],
                        start_year=int(row["start_year"]),
                        end_year=int(row["end_year"]),
                        acres=float(row["total_acres"]),
                        formatted=format_acres(row["total_acres"]),
                    )
                )

            # Calculate trend
            trend_direction = None
            trend_change_acres = None
            trend_change_percent = None

            if len(data_points) >= 2:
                first = data_points[0].acres
                last = data_points[-1].acres
                change = last - first
                pct_change = (change / first * 100) if first > 0 else 0
                trend_direction = "increasing" if change > 0 else "decreasing"
                trend_change_acres = format_acres(abs(change))
                trend_change_percent = format_percent(abs(pct_change))

            return TimeSeriesResult(
                metric=metric,
                data_points=data_points,
                trend_direction=trend_direction,
                trend_change_acres=trend_change_acres,
                trend_change_percent=trend_change_percent,
                filters={
                    "states": states,
                    "scenario": scenario,
                },
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def get_county_data(
        self,
        state: str,
        county: str,
        year: int | None = None,
        scenario: str | None = None,
    ) -> CountyResult | ErrorResult:
        """Query land use data for a specific county.

        Args:
            state: State abbreviation
            county: County name (partial match supported)
            year: Year filter
            scenario: Scenario code

        Returns:
            CountyResult with county data or ErrorResult on failure
        """
        try:
            conn = self._get_conn()

            # Look up the county
            lookup_query = QueryBuilder.county_lookup(state, county)
            county_df = conn.execute(lookup_query.sql, lookup_query.params).df()

            if county_df.empty:
                return self._error(
                    f"County '{county}' not found in {state}",
                    "NOT_FOUND",
                    "Check the county name spelling",
                )

            geo_id = int(county_df["geography_id"].iloc[0])
            county_name = county_df["county_name"].iloc[0]
            state_name = county_df["state_name"].iloc[0]
            fips = county_df["fips_code"].iloc[0]

            # Query county area
            area_query = QueryBuilder.county_area(geo_id, year, scenario)
            df = conn.execute(area_query.sql, area_query.params).df()

            if df.empty:
                return self._error(
                    "No data found for this county",
                    "NO_DATA",
                )

            total = float(df["total_acres"].sum())
            by_land_use = df.groupby("landuse_name")["total_acres"].sum().to_dict()

            return CountyResult(
                county=county_name,
                state=state_name,
                state_abbrev=state.upper(),
                fips=fips,
                total_acres=total,
                total_formatted=format_acres(total),
                by_land_use={k: format_acres(v) for k, v in by_land_use.items()},
                filters={
                    "year": year,
                    "scenario": scenario,
                },
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def get_top_counties(
        self,
        metric: str,
        limit: int = 10,
        states: list[str] | None = None,
        scenario: str | None = None,
    ) -> TopCountiesResult | ErrorResult:
        """Find top counties by a metric.

        Args:
            metric: Metric to rank by (urban_growth, forest_loss)
            limit: Number of counties to return
            states: Optional state filter
            scenario: Scenario code

        Returns:
            TopCountiesResult with rankings or ErrorResult on failure
        """
        try:
            query = QueryBuilder.top_counties(metric, limit, states, scenario)
            self._log(f"Executing: {query.description}")

            conn = self._get_conn()
            df = conn.execute(query.sql, query.params).df()

            if df.empty:
                return self._error(
                    "No data found",
                    "NO_DATA",
                    "Try a different metric or remove state filters",
                )

            counties = []
            for i, (_, row) in enumerate(df.iterrows()):
                counties.append(
                    RankedCounty(
                        rank=i + 1,
                        county=row["county_name"],
                        state=row["state_name"],
                        fips=row["fips_code"],
                        acres=float(row["total_acres"]),
                        formatted=format_acres(row["total_acres"]),
                    )
                )

            return TopCountiesResult(
                metric=metric,
                counties=counties,
                filters={
                    "limit": limit,
                    "states": states,
                    "scenario": scenario,
                },
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def get_data_summary(self) -> DataSummaryResult | ErrorResult:
        """Get summary statistics about available data.

        Returns:
            DataSummaryResult with coverage information or ErrorResult on failure
        """
        try:
            conn = self._get_conn()

            # Get counts and ranges
            summary_query = QueryBuilder.data_summary()
            summary_df = conn.execute(summary_query.sql, summary_query.params).df()

            fact_count = int(summary_df["fact_count"].iloc[0])
            county_count = int(summary_df["county_count"].iloc[0])
            state_count = int(summary_df["state_count"].iloc[0])
            min_year = int(summary_df["min_year"].iloc[0])
            max_year = int(summary_df["max_year"].iloc[0])

            # Get scenarios
            scenarios_df = conn.execute(
                "SELECT DISTINCT rcp_scenario || '/' || ssp_scenario as scenario FROM dim_scenario ORDER BY scenario"
            ).df()
            scenarios = scenarios_df["scenario"].tolist()

            # Get land use types
            landuse_df = conn.execute(
                "SELECT landuse_name FROM dim_landuse ORDER BY landuse_name"
            ).df()
            land_use_types = landuse_df["landuse_name"].tolist()

            return DataSummaryResult(
                total_records=fact_count,
                counties=county_count,
                states=state_count,
                time_range=(min_year, max_year),
                scenarios=scenarios,
                land_use_types=land_use_types,
            )

        except Exception as e:
            return self._error(str(e), "DATABASE_ERROR")

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "LandUseAPI":
        """Context manager entry."""
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit - close connection."""
        self.close()
