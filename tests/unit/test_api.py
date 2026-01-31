"""Unit tests for the Land Use API module.

These tests use the actual database to verify API functionality.
"""

import os
from pathlib import Path

import pytest

from landuse.api import (
    LandUseAPI,
    LandUseAreaResult,
    TransitionsResult,
    UrbanExpansionResult,
    ForestChangeResult,
    AgriculturalChangeResult,
    ScenarioComparisonResult,
    StateComparisonResult,
    TimeSeriesResult,
    CountyResult,
    TopCountiesResult,
    DataSummaryResult,
    ErrorResult,
    Scenario,
    LandUse,
)
from landuse.api.queries import QueryBuilder, SCENARIO_MAP, LANDUSE_MAP
from landuse.api.formatters import format_acres, format_percent


# Use actual database for integration tests
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_REAL_DB_PATH = _PROJECT_ROOT / "data" / "processed" / "landuse_analytics.duckdb"


class TestFormatters:
    """Tests for formatting utilities."""

    def test_format_acres_with_thousands(self):
        """Test acres formatting with thousands separators."""
        assert format_acres(1234567.89) == "1,234,568"

    def test_format_acres_small_number(self):
        """Test acres formatting with small numbers."""
        assert format_acres(500.0) == "500"

    def test_format_acres_zero(self):
        """Test acres formatting with zero."""
        assert format_acres(0.0) == "0"

    def test_format_percent(self):
        """Test percentage formatting."""
        assert format_percent(15.567) == "15.6%"
        assert format_percent(100.0) == "100.0%"


class TestQueryBuilder:
    """Tests for query builder."""

    def test_scenario_clause_valid(self):
        """Test scenario clause with valid code."""
        clause, params = QueryBuilder._scenario_clause("LM")
        assert "rcp_scenario" in clause
        assert "ssp_scenario" in clause
        assert params == ["RCP45", "SSP1"]

    def test_scenario_clause_invalid(self):
        """Test scenario clause with invalid code."""
        clause, params = QueryBuilder._scenario_clause("INVALID")
        assert clause == ""
        assert params == []

    def test_scenario_clause_none(self):
        """Test scenario clause with None."""
        clause, params = QueryBuilder._scenario_clause(None)
        assert clause == ""
        assert params == []

    def test_states_clause(self):
        """Test states clause building."""
        clause, params = QueryBuilder._states_clause(["CA", "TX"])
        assert "state_name IN" in clause
        assert len(params) == 2
        assert "California" in params
        assert "Texas" in params

    def test_states_clause_empty(self):
        """Test states clause with empty list."""
        clause, params = QueryBuilder._states_clause([])
        assert clause == ""
        assert params == []

    def test_landuse_clause(self):
        """Test land use clause building."""
        clause, params = QueryBuilder._landuse_clause("forest", "l")
        assert "l.landuse_name = ?" in clause
        assert params == ["Forest"]

    def test_year_clause(self):
        """Test year clause building."""
        clause, params = QueryBuilder._year_clause(2025)
        assert "start_year" in clause
        assert "end_year" in clause
        assert params == [2025, 2025]

    def test_land_use_area_query(self):
        """Test land use area query building."""
        result = QueryBuilder.land_use_area(
            states=["CA"],
            land_use="forest",
            scenario="LM"
        )
        assert "SELECT" in result.sql
        assert "total_acres" in result.sql
        assert len(result.params) > 0

    def test_transitions_query(self):
        """Test transitions query building."""
        result = QueryBuilder.transitions(
            states=["CA"],
            from_use="forest",
            to_use="urban"
        )
        assert "transition_type = 'change'" in result.sql
        assert "from_landuse" in result.sql
        assert "to_landuse" in result.sql


class TestEnums:
    """Tests for API enums."""

    def test_scenario_values(self):
        """Test scenario enum values."""
        assert Scenario.LM.value == "LM"
        assert Scenario.HM.value == "HM"
        assert Scenario.HL.value == "HL"
        assert Scenario.HH.value == "HH"

    def test_landuse_values(self):
        """Test land use enum values."""
        assert LandUse.CROP.value == "crop"
        assert LandUse.FOREST.value == "forest"
        assert LandUse.URBAN.value == "urban"


class TestLandUseAPI:
    """Integration tests for the LandUseAPI class.

    These tests use the actual database.
    """

    @pytest.fixture
    def api(self):
        """Create API instance for testing with real database."""
        if not _REAL_DB_PATH.exists():
            pytest.skip(f"Database not found at {_REAL_DB_PATH}")
        api = LandUseAPI(db_path=str(_REAL_DB_PATH))
        yield api
        api.close()

    def test_get_land_use_area_single_state(self, api):
        """Test land use area query for single state."""
        result = api.get_land_use_area(states=["CA"])

        assert result.success
        assert isinstance(result, LandUseAreaResult)
        assert result.total_acres > 0
        assert "," in result.total_formatted
        assert len(result.by_land_use) > 0

    def test_get_land_use_area_with_land_use_filter(self, api):
        """Test land use area query with land use filter."""
        result = api.get_land_use_area(states=["CA"], land_use="forest")

        assert result.success
        assert isinstance(result, LandUseAreaResult)
        assert result.total_acres > 0
        # Should only have Forest in by_land_use
        assert len(result.by_land_use) == 1
        assert "Forest" in result.by_land_use

    def test_get_land_use_area_with_scenario(self, api):
        """Test land use area query with scenario filter."""
        result = api.get_land_use_area(states=["CA"], scenario="LM")

        assert result.success
        assert isinstance(result, LandUseAreaResult)
        assert result.filters.get("scenario") == "LM"

    def test_get_land_use_area_invalid_state(self, api):
        """Test land use area query with invalid state."""
        result = api.get_land_use_area(states=["INVALID"])

        assert isinstance(result, ErrorResult)
        assert not result.success
        assert result.error_code == "NO_DATA"

    def test_get_transitions(self, api):
        """Test transitions query."""
        result = api.get_transitions(states=["CA"])

        assert result.success
        assert isinstance(result, TransitionsResult)
        assert result.total_acres > 0
        assert len(result.transitions) > 0
        assert result.transitions[0].from_use
        assert result.transitions[0].to_use

    def test_get_transitions_with_filters(self, api):
        """Test transitions query with filters."""
        result = api.get_transitions(
            states=["CA"],
            from_use="forest",
            to_use="urban"
        )

        assert result.success
        assert isinstance(result, TransitionsResult)
        for t in result.transitions:
            assert t.from_use == "Forest"
            assert t.to_use == "Urban"

    def test_get_urban_expansion(self, api):
        """Test urban expansion query."""
        result = api.get_urban_expansion(states=["CA"])

        assert result.success
        assert isinstance(result, UrbanExpansionResult)
        assert result.total_acres > 0
        assert len(result.by_source) > 0
        assert "Urban development is irreversible" in result.note

    def test_get_forest_change_net(self, api):
        """Test forest change query with net change."""
        result = api.get_forest_change(states=["CA"], change_type="net")

        assert result.success
        assert isinstance(result, ForestChangeResult)
        assert result.loss_acres is not None
        assert result.gain_acres is not None
        assert result.net_acres is not None
        assert result.net_direction in ("gain", "loss")

    def test_get_forest_change_loss_only(self, api):
        """Test forest change query with loss only."""
        result = api.get_forest_change(states=["CA"], change_type="loss")

        assert result.success
        assert isinstance(result, ForestChangeResult)
        assert result.loss_acres is not None
        assert result.gain_acres is None

    def test_get_agricultural_change(self, api):
        """Test agricultural change query."""
        result = api.get_agricultural_change(states=["CA"])

        assert result.success
        assert isinstance(result, AgriculturalChangeResult)
        assert result.total_loss_acres > 0
        assert len(result.by_ag_type) > 0

    def test_compare_scenarios(self, api):
        """Test scenario comparison."""
        result = api.compare_scenarios(
            states=["CA"],
            metric="urban_expansion"
        )

        assert result.success
        assert isinstance(result, ScenarioComparisonResult)
        assert len(result.comparison) == 4  # LM, HM, HL, HH
        assert result.highest is not None
        assert result.lowest is not None

    def test_compare_states(self, api):
        """Test state comparison."""
        result = api.compare_states(
            states=["CA", "TX", "FL"],
            metric="urban_expansion"
        )

        assert result.success
        assert isinstance(result, StateComparisonResult)
        assert len(result.rankings) == 3
        assert result.rankings[0].acres >= result.rankings[1].acres

    def test_get_time_series(self, api):
        """Test time series query."""
        result = api.get_time_series(states=["CA"], metric="urban_area")

        assert result.success
        assert isinstance(result, TimeSeriesResult)
        assert len(result.data_points) > 0
        assert result.trend_direction in ("increasing", "decreasing")

    def test_get_county_data(self, api):
        """Test county data query."""
        result = api.get_county_data(state="CA", county="Los Angeles")

        assert result.success
        assert isinstance(result, CountyResult)
        assert "Los Angeles" in result.county
        assert result.state == "California"
        assert result.fips
        assert result.total_acres > 0

    def test_get_county_data_not_found(self, api):
        """Test county data query with invalid county."""
        result = api.get_county_data(state="CA", county="Nonexistent County")

        assert isinstance(result, ErrorResult)
        assert not result.success
        assert result.error_code == "NOT_FOUND"

    def test_get_top_counties(self, api):
        """Test top counties query."""
        result = api.get_top_counties(metric="urban_growth", limit=5)

        assert result.success
        assert isinstance(result, TopCountiesResult)
        assert len(result.counties) == 5
        assert result.counties[0].rank == 1
        assert result.counties[0].acres >= result.counties[1].acres

    def test_get_data_summary(self, api):
        """Test data summary query."""
        result = api.get_data_summary()

        assert result.success
        assert isinstance(result, DataSummaryResult)
        assert result.total_records > 0
        assert result.counties > 0
        assert result.states > 0
        assert result.time_range[0] < result.time_range[1]
        assert len(result.scenarios) > 0
        assert len(result.land_use_types) == 5


class TestResultModels:
    """Tests for result model methods."""

    @pytest.fixture
    def api(self):
        """Create API instance for testing with real database."""
        if not _REAL_DB_PATH.exists():
            pytest.skip(f"Database not found at {_REAL_DB_PATH}")
        api = LandUseAPI(db_path=str(_REAL_DB_PATH))
        yield api
        api.close()

    def test_to_llm_string_land_use_area(self, api):
        """Test LLM string formatting for land use area."""
        result = api.get_land_use_area(states=["CA"])
        llm_str = result.to_llm_string()

        assert "**Land Use Area**" in llm_str
        assert "Total:" in llm_str
        assert "acres" in llm_str
        assert "Source:" in llm_str

    def test_to_llm_string_urban_expansion(self, api):
        """Test LLM string formatting for urban expansion."""
        result = api.get_urban_expansion(states=["CA"])
        llm_str = result.to_llm_string()

        assert "**Urban Expansion**" in llm_str
        assert "Note:" in llm_str
        assert "irreversible" in llm_str

    def test_to_llm_string_forest_change(self, api):
        """Test LLM string formatting for forest change."""
        result = api.get_forest_change(states=["CA"])
        llm_str = result.to_llm_string()

        assert "**Forest Change**" in llm_str
        assert "Loss:" in llm_str
        assert "Gain:" in llm_str
        assert "Net" in llm_str

    def test_to_dict(self, api):
        """Test dict serialization."""
        result = api.get_land_use_area(states=["CA"])
        data = result.to_dict()

        assert "total_acres" in data
        assert "total_formatted" in data
        assert "by_land_use" in data
        assert "success" in data


class TestContextManager:
    """Tests for context manager functionality."""

    def test_context_manager(self):
        """Test using API as context manager."""
        if not _REAL_DB_PATH.exists():
            pytest.skip(f"Database not found at {_REAL_DB_PATH}")
        with LandUseAPI(db_path=str(_REAL_DB_PATH)) as api:
            result = api.get_data_summary()
            assert result.success

    def test_connection_closed_after_context(self):
        """Test that connection is closed after context exit."""
        if not _REAL_DB_PATH.exists():
            pytest.skip(f"Database not found at {_REAL_DB_PATH}")
        api = LandUseAPI(db_path=str(_REAL_DB_PATH))
        with api:
            _ = api.get_data_summary()
        assert api._conn is None


class TestVerboseMode:
    """Tests for verbose mode."""

    def test_verbose_mode_creates_console(self):
        """Test that verbose mode creates a console."""
        api = LandUseAPI(verbose=True)
        assert api._console is not None
        api.close()

    def test_non_verbose_mode_no_console(self):
        """Test that non-verbose mode has no console."""
        api = LandUseAPI(verbose=False)
        assert api._console is None
        api.close()
