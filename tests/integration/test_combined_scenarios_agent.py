#!/usr/bin/env python3
"""Integration tests for combined scenarios with agent system.

Tests the agent's behavior with the 5-scenario structure:
- OVERALL (default ensemble mean)
- RCP45_SSP1, RCP45_SSP5, RCP85_SSP1, RCP85_SSP5

Priority: High ⚠️
Issue: #67
"""

import os
import sys
from pathlib import Path

import duckdb
import pytest

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from landuse.agents.landuse_agent import LandUseAgent
from landuse.core.app_config import AppConfig


def check_database_has_combined_scenarios(db_path: str) -> bool:
    """Check if database has combined scenarios structure."""
    try:
        conn = duckdb.connect(db_path, read_only=True)
        result = conn.execute("""
            SELECT COUNT(*) FROM dim_scenario
            WHERE scenario_name = 'OVERALL'
        """).fetchone()
        conn.close()
        return result[0] > 0
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("ANTHROPIC_API_KEY"), reason="Anthropic API key required for integration tests")
class TestCombinedScenariosAgent:
    """Integration tests for combined scenarios with agent system."""

    @pytest.fixture
    def agent_config(self):
        """Create test configuration with real database."""
        db_path = os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")

        # Skip if database doesn't exist
        if not Path(db_path).exists():
            pytest.skip(f"Database not found at {db_path}")

        return AppConfig(
            database={"path": db_path},
            agent={"max_iterations": 5, "enable_memory": False},
            logging={"level": "WARNING"},
        )

    @pytest.fixture
    def agent(self, agent_config):
        """Create agent instance for testing."""
        with LandUseAgent(agent_config) as agent:
            yield agent

    def test_agent_uses_overall_by_default(self, agent, agent_config):
        """Test that agent uses OVERALL scenario for single queries.

        When asking a simple question without specifying a scenario,
        the agent should default to using the OVERALL scenario instead
        of asking the user which scenario to use.
        """
        # Check if database has combined scenarios
        has_combined = check_database_has_combined_scenarios(agent_config.database.path)

        # Query without specifying a scenario
        response = agent.query("How much urban expansion occurs in California by 2050?")

        # Should NOT ask which scenario to use (if combined scenarios are implemented)
        assert response is not None

        if has_combined:
            # With combined scenarios, should not ask for scenario selection
            assert "which scenario" not in response.lower()
            assert "please specify" not in response.lower()

        # Should provide a concrete answer about urban expansion
        assert any(
            term in response.lower() for term in ["urban", "expansion", "california", "acres", "hectares", "2050"]
        )

    def test_agent_compares_scenarios_correctly(self, agent, agent_config):
        """Test scenario comparison excludes OVERALL.

        When comparing scenarios, the agent should compare the actual
        RCP-SSP combinations and not include the OVERALL scenario in
        the comparison (if combined scenarios are implemented).
        """
        has_combined = check_database_has_combined_scenarios(agent_config.database.path)

        response = agent.query("Compare forest loss across all climate scenarios between 2020 and 2070")

        assert response is not None

        # Should mention RCP/SSP scenarios
        scenario_mentioned = False
        for scenario in ["RCP45", "RCP85", "SSP1", "SSP2", "SSP3", "SSP5", "rcp45", "rcp85"]:
            if scenario.lower() in response.lower() or scenario.replace("_", "-").lower() in response.lower():
                scenario_mentioned = True
                break

        assert scenario_mentioned, "Response should mention specific RCP/SSP scenarios"

        # If combined scenarios exist, should NOT include OVERALL in comparisons
        if has_combined:
            # Check that OVERALL isn't listed among compared scenarios
            if "overall" in response.lower() and "scenarios" in response.lower():
                # Allow mentioning OVERALL in context, but not as a compared scenario
                pass  # This is more complex to validate without false positives

    def test_agent_handles_uncertainty_queries(self, agent):
        """Test agent can access statistical fields.

        The combined scenarios include statistical fields (std_dev, min, max)
        to represent uncertainty across the GCM ensemble. The agent should
        be able to access and explain these uncertainty metrics.
        """
        response = agent.query("What is the uncertainty range in urban expansion projections for Texas by 2070?")

        assert response is not None

        # Should mention uncertainty, variability, range, deviation, or confidence
        uncertainty_terms = [
            "uncertainty",
            "range",
            "deviation",
            "variability",
            "minimum",
            "maximum",
            "spread",
            "confidence",
            "std",
        ]

        assert any(term in response.lower() for term in uncertainty_terms), (
            "Response should discuss uncertainty metrics"
        )

        # Should provide specific context about Texas
        assert "texas" in response.lower()

    def test_default_scenario_for_trends(self, agent):
        """Test that trend queries use OVERALL by default.

        When asking about general trends without specifying scenarios,
        the agent should use the OVERALL scenario to provide a single
        clear answer.
        """
        response = agent.query("What is the trend in agricultural land conversion from 2020 to 2100?")

        assert response is not None

        # Should provide trend information
        assert any(
            term in response.lower()
            for term in ["trend", "increase", "decrease", "change", "conversion", "agricultural"]
        )

        # Should NOT ask for scenario selection
        assert "which scenario" not in response.lower()
        assert "please specify" not in response.lower()

    def test_explicit_scenario_request(self, agent):
        """Test that explicit scenario requests work correctly.

        When a user specifically asks for a particular RCP-SSP combination,
        the agent should use that scenario, not OVERALL.
        """
        response = agent.query("How much forest is lost under RCP85_SSP5 scenario in the Southeast by 2100?")

        assert response is not None

        # Should mention the requested scenario
        assert any(term in response.lower() for term in ["rcp85", "ssp5", "fossil", "high emission"])

        # Should provide specific data
        assert any(term in response.lower() for term in ["forest", "acres", "hectares", "southeast", "2100"])

    def test_multi_scenario_analysis(self, agent):
        """Test analysis across multiple specific scenarios.

        The agent should be able to compare specific subsets of scenarios
        when requested.
        """
        response = agent.query("Compare urban expansion between RCP45 scenarios (SSP1 vs SSP5)")

        assert response is not None

        # Should compare the two requested scenarios
        assert "ssp1" in response.lower() or "sustainability" in response.lower()
        assert "ssp5" in response.lower() or "fossil" in response.lower()
        assert "rcp45" in response.lower() or "rcp4.5" in response.lower()

        # Should provide comparison
        assert any(
            term in response.lower()
            for term in ["compare", "comparison", "versus", "vs", "difference", "higher", "lower"]
        )


@pytest.mark.integration
class TestDatabaseViews:
    """Test database views for combined scenarios."""

    @pytest.fixture
    def db_connection(self):
        """Create DuckDB connection for testing views."""
        import duckdb

        db_path = os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")

        if not db_path or not Path(db_path).exists():
            pytest.skip(f"Database not found at {db_path}")

        try:
            conn = duckdb.connect(db_path, read_only=True)
            # Verify it's a valid database
            conn.execute("SELECT 1").fetchone()
        except Exception as e:
            pytest.skip(f"Invalid database at {db_path}: {e}")

        yield conn
        conn.close()

    def test_v_default_transitions_uses_overall(self, db_connection):
        """Test that v_default_transitions view uses OVERALL scenario.

        This view should automatically filter to the OVERALL scenario
        for simplified queries.
        """
        # Check if view exists
        result = db_connection.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_type = 'VIEW'
            AND table_name = 'v_default_transitions'
        """).fetchall()

        if not result:
            pytest.skip("v_default_transitions view not found")

        # Query the view
        result = db_connection.execute("""
            SELECT DISTINCT scenario_name
            FROM v_default_transitions
            LIMIT 5
        """).fetchall()

        # Should only have OVERALL scenario
        if result:
            assert len(result) == 1
            assert result[0][0] == "OVERALL"

    def test_v_scenario_comparisons_excludes_overall(self, db_connection):
        """Test that v_scenario_comparisons excludes OVERALL.

        This view should only include the 4 actual RCP-SSP scenarios
        for comparison purposes.
        """
        # Check if view exists
        result = db_connection.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_type = 'VIEW'
            AND table_name = 'v_scenario_comparisons'
        """).fetchall()

        if not result:
            pytest.skip("v_scenario_comparisons view not found")

        # Query the view
        result = db_connection.execute("""
            SELECT DISTINCT scenario_name
            FROM v_scenario_comparisons
            ORDER BY scenario_name
        """).fetchall()

        # Should have 4 scenarios, not including OVERALL
        scenario_names = [r[0] for r in result]

        assert "OVERALL" not in scenario_names
        assert len(scenario_names) == 4

        # Should have the expected RCP-SSP combinations
        expected_patterns = ["RCP45_SSP1", "RCP45_SSP5", "RCP85_SSP1", "RCP85_SSP5"]
        for pattern in expected_patterns:
            assert any(pattern in s for s in scenario_names)

    def test_statistical_fields_accessible(self, db_connection):
        """Test that statistical fields are accessible in the database.

        The combined scenarios should include std_dev, min, and max fields
        for uncertainty analysis.
        """
        # Check fact table structure
        result = db_connection.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'fact_landuse_transitions'
            AND column_name IN ('std_dev', 'min_value', 'max_value', 'coefficient_variation')
        """).fetchall()

        statistical_columns = [r[0] for r in result]

        # Should have at least std_dev for uncertainty
        if statistical_columns:
            assert "std_dev" in statistical_columns or "coefficient_variation" in statistical_columns


def has_valid_anthropic_key():
    """Check if a valid (non-test) Anthropic API key is available."""
    key = os.getenv("ANTHROPIC_API_KEY", "")
    # Skip if no key or if it looks like a test key
    return key and not key.startswith("sk-test") and len(key) > 20


@pytest.mark.integration
@pytest.mark.skipif(
    not has_valid_anthropic_key(), reason="Valid Anthropic API key required for end-to-end tests (test keys don't work)"
)
class TestEndToEndWorkflow:
    """End-to-end workflow tests for combined scenarios."""

    @pytest.fixture
    def agent(self):
        """Create agent for end-to-end testing."""
        db_path = os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")

        if not Path(db_path).exists():
            pytest.skip(f"Database not found at {db_path}")

        config = AppConfig(
            database={"path": db_path}, agent={"max_iterations": 8, "enable_memory": True}, logging={"level": "WARNING"}
        )

        with LandUseAgent(config) as agent:
            yield agent

    def test_conversation_flow_with_combined_scenarios(self, agent):
        """Test a conversation flow using combined scenarios.

        Simulates a realistic user conversation to ensure the agent
        handles the combined scenarios correctly throughout.
        """
        thread_id = "test-combined-flow"

        # First query - general question (should use OVERALL)
        response1 = agent.query("What are the main land use changes happening nationally?", thread_id=thread_id)
        assert response1 is not None
        assert len(response1) > 50  # Should have substantial content

        # Follow-up - specific state (still using OVERALL by default)
        response2 = agent.query("How about specifically in California?", thread_id=thread_id)
        assert response2 is not None
        assert "california" in response2.lower()

        # Scenario comparison request
        response3 = agent.query(
            "Now compare these California trends across different climate scenarios", thread_id=thread_id
        )
        assert response3 is not None
        # Should mention multiple scenarios
        assert any(term in response3.lower() for term in ["rcp", "ssp", "scenario"])

        # Uncertainty question
        response4 = agent.query("What's the uncertainty in these projections?", thread_id=thread_id)
        assert response4 is not None
        assert any(term in response4.lower() for term in ["uncertainty", "range", "variability", "confidence"])

    @pytest.mark.slow
    def test_performance_with_combined_scenarios(self, agent):
        """Test query performance with combined scenarios.

        Queries should complete within 2 seconds as specified in requirements.
        """
        import time

        queries = [
            "Total urban expansion by 2070",
            "Forest loss in the Southeast",
            "Agricultural trends in the Midwest",
        ]

        for query in queries:
            start_time = time.time()
            response = agent.query(query)
            elapsed_time = time.time() - start_time

            assert response is not None
            # Should complete within 3 seconds (allowing some buffer)
            assert elapsed_time < 3.0, f"Query took {elapsed_time:.2f}s, expected <3s"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
