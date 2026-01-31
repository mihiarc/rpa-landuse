"""Query builder for parameterized SQL against star schema.

This module generates safe, parameterized SQL queries for the RPA land use
star schema. All queries use parameter binding to prevent SQL injection.
"""

from dataclasses import dataclass

from landuse.utils.state_mappings import StateMapper


# Scenario code to RCP/SSP mapping
SCENARIO_MAP: dict[str, tuple[str, str]] = {
    "LM": ("RCP45", "SSP1"),  # Lower-Moderate: Sustainability
    "HM": ("RCP85", "SSP2"),  # High-Moderate: Middle Road
    "HL": ("RCP85", "SSP3"),  # High-Low: Regional Rivalry
    "HH": ("RCP85", "SSP5"),  # High-High: Fossil Development
}

# Scenario display names
SCENARIO_NAMES: dict[str, str] = {
    "LM": "LM (Lower-Moderate)",
    "HM": "HM (High-Moderate)",
    "HL": "HL (High-Low)",
    "HH": "HH (High-High)",
}

# Land use type mappings (lowercase input -> database name)
LANDUSE_MAP: dict[str, str] = {
    "crop": "Crop",
    "pasture": "Pasture",
    "forest": "Forest",
    "urban": "Urban",
    "rangeland": "Rangeland",
}


@dataclass
class QueryResult:
    """Result from query builder containing SQL and parameters."""
    sql: str
    params: list
    description: str


class QueryBuilder:
    """Build parameterized SQL queries for the star schema.

    All methods return QueryResult with SQL and parameters for safe execution.
    No string interpolation is used for user-provided values.
    """

    @staticmethod
    def _scenario_clause(scenario: str | None) -> tuple[str, list]:
        """Build scenario filter clause with parameters."""
        if not scenario:
            return "", []
        scenario = scenario.upper()
        if scenario not in SCENARIO_MAP:
            return "", []
        rcp, ssp = SCENARIO_MAP[scenario]
        return "AND s.rcp_scenario = ? AND s.ssp_scenario = ?", [rcp, ssp]

    @staticmethod
    def _states_clause(states: list[str]) -> tuple[str, list]:
        """Build states filter clause using state names."""
        if not states:
            return "", []

        # Convert abbreviations to full state names for database query
        state_names = []
        for s in states:
            s_upper = s.upper().strip()
            name = StateMapper.abbrev_to_name(s_upper)
            if name:
                state_names.append(name)
            else:
                # Assume it's already a full state name
                state_names.append(s.title())

        if not state_names:
            return "", []

        placeholders = ", ".join(["?" for _ in state_names])
        return f"AND g.state_name IN ({placeholders})", state_names

    @staticmethod
    def _landuse_clause(land_use: str | None, alias: str = "l") -> tuple[str, list]:
        """Build land use filter clause with parameters."""
        if not land_use:
            return "", []
        name = LANDUSE_MAP.get(land_use.lower(), land_use.title())
        return f"AND {alias}.landuse_name = ?", [name]

    @staticmethod
    def _year_clause(year: int | None) -> tuple[str, list]:
        """Build year filter clause (matches containing time period)."""
        if not year:
            return "", []
        return "AND t.start_year <= ? AND t.end_year >= ?", [year, year]

    @staticmethod
    def _year_range_clause(year_range: str | None) -> tuple[str, list]:
        """Build exact year range filter clause."""
        if not year_range:
            return "", []
        return "AND t.year_range = ?", [year_range]

    @classmethod
    def land_use_area(
        cls,
        states: list[str],
        land_use: str | None = None,
        year: int | None = None,
        scenario: str | None = None,
    ) -> QueryResult:
        """Build query for land use area by state.

        Args:
            states: List of state abbreviations (e.g., ["CA", "TX"])
            land_use: Optional land use type filter
            year: Optional year filter (matches containing period)
            scenario: Optional scenario code (LM, HM, HL, HH)

        Returns:
            QueryResult with SQL and parameters
        """
        states_clause, states_params = cls._states_clause(states)
        landuse_clause, landuse_params = cls._landuse_clause(land_use, "l")
        year_clause, year_params = cls._year_clause(year)
        scenario_clause, scenario_params = cls._scenario_clause(scenario)

        sql = f"""
        SELECT
            l.landuse_name,
            g.state_name,
            t.year_range,
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
        GROUP BY l.landuse_name, g.state_name, t.year_range
        ORDER BY total_acres DESC
        """

        params = states_params + landuse_params + year_params + scenario_params
        return QueryResult(sql=sql.strip(), params=params, description="Land use area query")

    @classmethod
    def transitions(
        cls,
        states: list[str],
        from_use: str | None = None,
        to_use: str | None = None,
        year_range: str | None = None,
        scenario: str | None = None,
    ) -> QueryResult:
        """Build query for land use transitions.

        Args:
            states: List of state abbreviations
            from_use: Source land use type filter
            to_use: Destination land use type filter
            year_range: Time period filter (e.g., "2020-2030")
            scenario: Scenario code

        Returns:
            QueryResult with SQL and parameters
        """
        states_clause, states_params = cls._states_clause(states)
        from_clause, from_params = cls._landuse_clause(from_use, "fl")
        to_clause, to_params = cls._landuse_clause(to_use, "tl")
        year_clause, year_params = cls._year_range_clause(year_range)
        scenario_clause, scenario_params = cls._scenario_clause(scenario)

        sql = f"""
        SELECT
            fl.landuse_name as from_landuse,
            tl.landuse_name as to_landuse,
            g.state_name,
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
        GROUP BY fl.landuse_name, tl.landuse_name, g.state_name
        ORDER BY transition_acres DESC
        """

        params = states_params + from_params + to_params + year_params + scenario_params
        return QueryResult(sql=sql.strip(), params=params, description="Transitions query")

    @classmethod
    def urban_expansion(
        cls,
        states: list[str],
        year_range: str | None = None,
        scenario: str | None = None,
        source_land_use: str | None = None,
    ) -> QueryResult:
        """Build query for urban expansion data.

        Args:
            states: List of state abbreviations
            year_range: Time period filter
            scenario: Scenario code
            source_land_use: Filter by source land use type

        Returns:
            QueryResult with SQL and parameters
        """
        states_clause, states_params = cls._states_clause(states)
        scenario_clause, scenario_params = cls._scenario_clause(scenario)
        source_clause, source_params = cls._landuse_clause(source_land_use, "fl")
        year_clause, year_params = cls._year_range_clause(year_range)

        sql = f"""
        SELECT
            fl.landuse_name as source_landuse,
            g.state_name,
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
        GROUP BY fl.landuse_name, g.state_name
        ORDER BY expansion_acres DESC
        """

        params = states_params + source_params + year_params + scenario_params
        return QueryResult(sql=sql.strip(), params=params, description="Urban expansion query")

    @classmethod
    def forest_loss(
        cls,
        states: list[str],
        year_range: str | None = None,
        scenario: str | None = None,
    ) -> QueryResult:
        """Build query for forest loss (Forest -> Other).

        Args:
            states: List of state abbreviations
            year_range: Time period filter
            scenario: Scenario code

        Returns:
            QueryResult with SQL and parameters
        """
        states_clause, states_params = cls._states_clause(states)
        year_clause, year_params = cls._year_range_clause(year_range)
        scenario_clause, scenario_params = cls._scenario_clause(scenario)

        sql = f"""
        SELECT
            tl.landuse_name as to_use,
            g.state_name,
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
        GROUP BY tl.landuse_name, g.state_name
        ORDER BY acres DESC
        """

        params = states_params + year_params + scenario_params
        return QueryResult(sql=sql.strip(), params=params, description="Forest loss query")

    @classmethod
    def forest_gain(
        cls,
        states: list[str],
        year_range: str | None = None,
        scenario: str | None = None,
    ) -> QueryResult:
        """Build query for forest gain (Other -> Forest).

        Args:
            states: List of state abbreviations
            year_range: Time period filter
            scenario: Scenario code

        Returns:
            QueryResult with SQL and parameters
        """
        states_clause, states_params = cls._states_clause(states)
        year_clause, year_params = cls._year_range_clause(year_range)
        scenario_clause, scenario_params = cls._scenario_clause(scenario)

        sql = f"""
        SELECT
            fl.landuse_name as from_use,
            g.state_name,
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
        GROUP BY fl.landuse_name, g.state_name
        ORDER BY acres DESC
        """

        params = states_params + year_params + scenario_params
        return QueryResult(sql=sql.strip(), params=params, description="Forest gain query")

    @classmethod
    def agricultural_change(
        cls,
        states: list[str],
        ag_type: str | None = None,
        year_range: str | None = None,
        scenario: str | None = None,
    ) -> QueryResult:
        """Build query for agricultural land change.

        Args:
            states: List of state abbreviations
            ag_type: "crop", "pasture", or None for both
            year_range: Time period filter
            scenario: Scenario code

        Returns:
            QueryResult with SQL and parameters
        """
        states_clause, states_params = cls._states_clause(states)
        scenario_clause, scenario_params = cls._scenario_clause(scenario)
        year_clause, year_params = cls._year_range_clause(year_range)

        # Determine which ag types to query
        if ag_type:
            ag_types = [LANDUSE_MAP.get(ag_type.lower(), ag_type.title())]
        else:
            ag_types = ["Crop", "Pasture"]

        ag_placeholders = ", ".join(["?" for _ in ag_types])

        sql = f"""
        SELECT
            fl.landuse_name as ag_type,
            tl.landuse_name as to_use,
            g.state_name,
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
        GROUP BY fl.landuse_name, tl.landuse_name, g.state_name
        ORDER BY acres DESC
        """

        params = ag_types + states_params + year_params + scenario_params
        return QueryResult(sql=sql.strip(), params=params, description="Agricultural change query")

    @classmethod
    def state_comparison(
        cls,
        states: list[str],
        metric: str,
        scenario: str | None = None,
        year: int | None = None,
    ) -> QueryResult:
        """Build query for state comparison.

        Args:
            states: List of state abbreviations to compare
            metric: Metric to compare (urban_expansion, forest_loss, land_area)
            scenario: Scenario code
            year: Year filter

        Returns:
            QueryResult with SQL and parameters
        """
        states_clause, states_params = cls._states_clause(states)
        scenario_clause, scenario_params = cls._scenario_clause(scenario)
        year_clause, year_params = cls._year_clause(year)

        if metric == "urban_expansion":
            sql = f"""
            SELECT
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
            GROUP BY g.state_name
            ORDER BY total_acres DESC
            """
        elif metric == "forest_loss":
            sql = f"""
            SELECT
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
            GROUP BY g.state_name
            ORDER BY total_acres DESC
            """
        else:  # land_area
            sql = f"""
            SELECT
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
            GROUP BY g.state_name
            ORDER BY total_acres DESC
            """

        params = states_params + year_params + scenario_params
        return QueryResult(sql=sql.strip(), params=params, description=f"State comparison ({metric})")

    @classmethod
    def time_series(
        cls,
        states: list[str],
        metric: str,
        scenario: str | None = None,
    ) -> QueryResult:
        """Build query for time series data.

        Args:
            states: List of state abbreviations
            metric: Metric to track (urban_area, forest_area, etc.)
            scenario: Scenario code

        Returns:
            QueryResult with SQL and parameters
        """
        states_clause, states_params = cls._states_clause(states)
        scenario_clause, scenario_params = cls._scenario_clause(scenario)

        # Determine land use filter based on metric
        metric_lower = metric.lower().replace("_area", "").replace("_", "")
        if metric_lower in ("urban", "forest", "crop", "pasture", "rangeland"):
            landuse_name = LANDUSE_MAP.get(metric_lower, metric_lower.title())
            landuse_filter = f"AND l.landuse_name = '{landuse_name}'"
        else:
            landuse_filter = ""

        sql = f"""
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
        return QueryResult(sql=sql.strip(), params=params, description=f"Time series ({metric})")

    @classmethod
    def county_lookup(cls, state: str, county: str) -> QueryResult:
        """Build query to find a county by name.

        Args:
            state: State abbreviation
            county: County name (partial match supported)

        Returns:
            QueryResult with SQL and parameters
        """
        state_name = StateMapper.abbrev_to_name(state.upper()) or state.title()

        sql = """
        SELECT geography_id, county_name, state_name, fips_code
        FROM dim_geography
        WHERE state_name = ?
        AND LOWER(county_name) LIKE ?
        LIMIT 1
        """

        params = [state_name, f"%{county.lower()}%"]
        return QueryResult(sql=sql.strip(), params=params, description="County lookup")

    @classmethod
    def county_area(
        cls,
        geography_id: int,
        year: int | None = None,
        scenario: str | None = None,
    ) -> QueryResult:
        """Build query for county land use area.

        Args:
            geography_id: Geography ID from county lookup
            year: Year filter
            scenario: Scenario code

        Returns:
            QueryResult with SQL and parameters
        """
        year_clause, year_params = cls._year_clause(year)
        scenario_clause, scenario_params = cls._scenario_clause(scenario)

        sql = f"""
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

        params = [geography_id] + year_params + scenario_params
        return QueryResult(sql=sql.strip(), params=params, description="County area query")

    @classmethod
    def top_counties(
        cls,
        metric: str,
        limit: int = 10,
        states: list[str] | None = None,
        scenario: str | None = None,
    ) -> QueryResult:
        """Build query for top counties by metric.

        Args:
            metric: Metric to rank by (urban_growth, forest_loss)
            limit: Number of counties to return
            states: Optional state filter
            scenario: Scenario code

        Returns:
            QueryResult with SQL and parameters
        """
        states_clause, states_params = cls._states_clause(states or [])
        scenario_clause, scenario_params = cls._scenario_clause(scenario)

        if metric == "urban_growth":
            sql = f"""
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
        else:  # forest_loss
            sql = f"""
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

        params = states_params + scenario_params + [limit]
        return QueryResult(sql=sql.strip(), params=params, description=f"Top counties ({metric})")

    @classmethod
    def data_summary(cls) -> QueryResult:
        """Build queries for data summary statistics.

        Returns:
            QueryResult with SQL and parameters (multiple queries separated by semicolons)
        """
        sql = """
        SELECT
            (SELECT COUNT(*) FROM fact_landuse_transitions) as fact_count,
            (SELECT COUNT(DISTINCT geography_id) FROM dim_geography) as county_count,
            (SELECT COUNT(DISTINCT state_name) FROM dim_geography) as state_count,
            (SELECT MIN(start_year) FROM dim_time) as min_year,
            (SELECT MAX(end_year) FROM dim_time) as max_year
        """
        return QueryResult(sql=sql.strip(), params=[], description="Data summary")
