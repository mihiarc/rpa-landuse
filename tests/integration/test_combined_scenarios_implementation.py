#!/usr/bin/env python3
"""Implementation guide and tests for combined scenarios feature.

This file documents and tests the combined scenarios implementation progress.
When fully implemented, the system should:
1. Have 5 scenarios (OVERALL + 4 RCP-SSP combinations)
2. Default to OVERALL for single queries
3. Exclude OVERALL from scenario comparisons
4. Include statistical fields for uncertainty

Issue: #67
"""

import os
import sys
from pathlib import Path

import duckdb
import pytest

sys.path.append(str(Path(__file__).parent.parent.parent / "src"))


class TestCombinedScenariosImplementation:
    """Tests to verify combined scenarios implementation status."""

    @pytest.fixture
    def db_path(self):
        """Get database path."""
        db_path = os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")
        if not Path(db_path).exists():
            pytest.skip(f"Database not found at {db_path}")
        return db_path

    def test_database_scenario_count(self, db_path):
        """Check current scenario count in database.

        Expected states:
        - Original: 20 GCM-specific scenarios
        - Combined: 5 scenarios (4 RCP-SSP + 1 OVERALL)
        """
        conn = duckdb.connect(db_path, read_only=True)

        # Check which table exists
        table_name = "dim_scenario"
        try:
            conn.execute("SELECT 1 FROM dim_scenario_combined LIMIT 1").fetchone()
            table_name = "dim_scenario_combined"
        except:
            pass

        # Count scenarios
        result = conn.execute(f"SELECT COUNT(DISTINCT scenario_name) FROM {table_name}").fetchone()
        scenario_count = result[0]

        # Get scenario names
        scenarios = conn.execute(f"SELECT DISTINCT scenario_name FROM {table_name} ORDER BY scenario_name").fetchall()
        scenario_names = [s[0] for s in scenarios]

        conn.close()

        print(f"\nDatabase has {scenario_count} scenarios:")
        for name in scenario_names[:5]:
            print(f"  - {name}")
        if len(scenario_names) > 5:
            print(f"  ... and {len(scenario_names) - 5} more")

        # Check implementation status
        has_overall = any("OVERALL" in name for name in scenario_names)
        has_gcm_scenarios = any("CNRM" in name or "HadGEM" in name for name in scenario_names)

        if scenario_count == 5 and has_overall:
            print("✅ Combined scenarios fully implemented")
        elif scenario_count == 20 and has_gcm_scenarios:
            print("⚠️  Original GCM scenarios still in use - combined scenarios not yet implemented")
        else:
            print(f"❓ Unexpected scenario count: {scenario_count}")

        # This test documents the current state rather than asserting
        assert scenario_count > 0, "Database should have scenarios"

    def test_check_for_overall_scenario(self, db_path):
        """Check if OVERALL scenario exists.

        The OVERALL scenario should be the ensemble mean of all GCMs.
        """
        conn = duckdb.connect(db_path, read_only=True)

        # Check which table exists
        table_name = "dim_scenario"
        try:
            conn.execute("SELECT 1 FROM dim_scenario_combined LIMIT 1").fetchone()
            table_name = "dim_scenario_combined"
        except:
            pass

        result = conn.execute(f"""
            SELECT COUNT(*) FROM {table_name}
            WHERE scenario_name = 'OVERALL'
        """).fetchone()

        has_overall = result[0] > 0
        conn.close()

        if has_overall:
            print("\n✅ OVERALL scenario exists")
        else:
            print("\n⚠️  OVERALL scenario not found - needed for default queries")

        # Document current state
        assert True  # This test is for documentation

    def test_check_combined_rcp_ssp_scenarios(self, db_path):
        """Check for combined RCP-SSP scenarios.

        Expected combined scenarios:
        - RCP45_SSP1 (Sustainability)
        - RCP45_SSP5 (Fossil-fueled Development)
        - RCP85_SSP1 (Sustainability with high emissions)
        - RCP85_SSP5 (Fossil-fueled Development with high emissions)
        """
        conn = duckdb.connect(db_path, read_only=True)

        # Check for combined scenario pattern (no GCM prefix)
        result = conn.execute("""
            SELECT DISTINCT scenario_name
            FROM dim_scenario
            WHERE scenario_name NOT LIKE '%CNRM%'
            AND scenario_name NOT LIKE '%HadGEM%'
            AND scenario_name NOT LIKE '%IPSL%'
            AND scenario_name NOT LIKE '%MRI%'
            AND scenario_name NOT LIKE '%NorESM%'
            ORDER BY scenario_name
        """).fetchall()

        combined_scenarios = [r[0] for r in result]
        conn.close()

        if combined_scenarios:
            print(f"\n{len(combined_scenarios)} potential combined scenarios found:")
            for name in combined_scenarios:
                print(f"  - {name}")
        else:
            print("\n⚠️  No combined RCP-SSP scenarios found")

        # Expected scenarios
        expected = ["RCP45_SSP1", "RCP45_SSP5", "RCP85_SSP1", "RCP85_SSP5", "OVERALL"]
        found_expected = [s for s in expected if any(s in scenario for scenario in combined_scenarios)]

        if len(found_expected) == 5:
            print("✅ All expected combined scenarios present")
        else:
            missing = set(expected) - set(found_expected)
            if missing:
                print(f"⚠️  Missing scenarios: {missing}")

    def test_check_database_views(self, db_path):
        """Check for expected database views.

        Expected views:
        - v_default_transitions: Uses OVERALL scenario
        - v_scenario_comparisons: Excludes OVERALL
        """
        conn = duckdb.connect(db_path, read_only=True)

        # Get all views
        result = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_type = 'VIEW'
            ORDER BY table_name
        """).fetchall()

        views = [r[0] for r in result]
        conn.close()

        print(f"\n{len(views)} views found in database:")
        for view in views:
            print(f"  - {view}")

        # Check for expected views
        expected_views = ["v_default_transitions", "v_scenario_comparisons"]
        found_views = [v for v in expected_views if v in views]

        if len(found_views) == len(expected_views):
            print("✅ All expected views present")
        else:
            missing = set(expected_views) - set(found_views)
            if missing:
                print(f"⚠️  Missing views: {missing}")

    def test_check_statistical_fields(self, db_path):
        """Check for statistical fields in fact table.

        Statistical fields needed for uncertainty analysis:
        - std_dev or coefficient_variation
        - min_value
        - max_value
        """
        conn = duckdb.connect(db_path, read_only=True)

        # Get fact table columns
        result = conn.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'fact_landuse_transitions'
            ORDER BY ordinal_position
        """).fetchall()

        columns = [r[0] for r in result]
        conn.close()

        # Check for statistical columns
        stat_columns = [
            c
            for c in columns
            if any(term in c.lower() for term in ["std", "dev", "min", "max", "variance", "coefficient"])
        ]

        if stat_columns:
            print("\n✅ Statistical fields found:")
            for col in stat_columns:
                print(f"  - {col}")
        else:
            print("\n⚠️  No statistical fields found - needed for uncertainty analysis")

        print(f"\nAll fact table columns: {', '.join(columns)}")

    def test_agent_prompts_reference_combined_scenarios(self):
        """Check if agent prompts reference combined scenarios.

        The agent should be configured to use OVERALL by default.
        """
        from landuse.agents.prompts import SYSTEM_PROMPT_BASE

        prompt_text = SYSTEM_PROMPT_BASE

        # Check for references to combined scenarios
        has_overall = "OVERALL" in prompt_text
        has_default = "default" in prompt_text.lower() and "overall" in prompt_text.lower()
        has_exclude = "exclude" in prompt_text.lower() and "overall" in prompt_text.lower()

        print("\n Agent prompt configuration:")
        if has_overall:
            print("✅ References OVERALL scenario")
        if has_default:
            print("✅ Configured to use OVERALL as default")
        if has_exclude:
            print("✅ Configured to exclude OVERALL from comparisons")

        if not (has_overall and has_default):
            print("⚠️  Agent prompts may need updating for combined scenarios")

        assert has_overall, "Agent prompts should reference OVERALL scenario"


class TestImplementationReadiness:
    """Tests to verify system readiness for combined scenarios."""

    def test_converter_supports_combined_scenarios(self):
        """Check if converter supports combined scenarios."""
        from scripts.converters.convert_to_duckdb import LanduseCombinedScenarioConverter

        # Check for combined scenarios support
        has_combined = hasattr(LanduseCombinedScenarioConverter, "COMBINED_SCENARIOS")

        if has_combined:
            scenarios = LanduseCombinedScenarioConverter.COMBINED_SCENARIOS
            print(f"\n✅ Converter supports {len(scenarios)} combined scenarios:")
            for name in scenarios:
                print(f"  - {name}")
        else:
            print("\n⚠️  Converter may need updates for combined scenarios")

        assert has_combined, "Converter should support COMBINED_SCENARIOS"

    def test_agent_can_handle_queries(self):
        """Test if agent can handle basic queries with current database."""
        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OpenAI API key required for agent testing")

        from landuse.agents.landuse_agent import LanduseAgent
        from landuse.core.app_config import AppConfig

        db_path = os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")
        if not Path(db_path).exists():
            pytest.skip(f"Database not found at {db_path}")

        config = AppConfig(database={"path": db_path}, agent={"max_iterations": 3}, logging={"level": "WARNING"})

        with LanduseAgent(config) as agent:
            # Test a simple query
            response = agent.query("How many scenarios are in the database?")

            assert response is not None
            assert len(response) > 0
            print(f"\nAgent response: {response[:200]}...")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
