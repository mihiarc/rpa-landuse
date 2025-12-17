#!/usr/bin/env python3
"""
Integration tests for LangGraph agent
"""

import os

# Test imports
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

# TODO: Update to use the correct langgraph agent when refactoring is complete
# from landuse.agents.langgraph_agent import LangGraphLanduseAgent, LandGraphConfig
pytest.skip("LangGraph agent refactoring in progress", allow_module_level=True)


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"),
    reason="No API key available for integration test",
)
class TestLangGraphIntegration:
    """Integration tests for LangGraph agent with real API calls"""

    @pytest.fixture
    def agent_config(self):
        """Create test configuration"""
        db_path = os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")

        # Skip if database doesn't exist
        if not Path(db_path).exists():
            pytest.skip(f"Database not found at {db_path}")

        return LandGraphConfig(
            db_path=db_path,
            max_iterations=3,
            enable_memory=False,  # Disable for testing
            verbose=True,
        )

    def test_simple_query(self, agent_config):
        """Test a simple landuse query"""
        agent = LangGraphLanduseAgent(agent_config)

        # Test a basic schema query
        response = agent.query("What tables are available in the database?")

        # Verify response
        assert response is not None
        assert len(response) > 0
        assert "❌" not in response  # No error

        # Should mention some expected tables
        assert any(
            table in response.lower()
            for table in ["fact_landuse_transitions", "dim_scenario", "dim_geography", "dim_landuse", "dim_time"]
        )

    def test_agricultural_query(self, agent_config):
        """Test an agricultural land loss query"""
        agent = LangGraphLanduseAgent(agent_config)

        response = agent.query("How much agricultural land is being lost on average?")

        # Verify response
        assert response is not None
        assert len(response) > 0
        assert "❌" not in response  # No error

        # Should contain relevant terms
        assert any(term in response.lower() for term in ["agricultural", "agriculture", "crop", "acres", "land"])

    def test_streaming_query(self, agent_config):
        """Test streaming functionality"""
        agent = LangGraphLanduseAgent(agent_config)

        # Collect stream chunks
        chunks = list(agent.stream_query("What are the main land use categories?"))

        # Verify we got some chunks
        assert len(chunks) > 0

        # Should not have error chunks
        error_chunks = [chunk for chunk in chunks if "error" in chunk]
        assert len(error_chunks) == 0

    def test_memory_functionality(self, agent_config):
        """Test conversation memory"""
        # Enable memory for this test
        agent_config.enable_memory = True
        agent = LangGraphLanduseAgent(agent_config)

        thread_id = "test-memory-thread"

        # First query
        response1 = agent.query("What states are in the database?", thread_id=thread_id)
        assert response1 is not None
        assert "❌" not in response1

        # Follow-up query that should use context
        response2 = agent.query("How many counties are in the first state you mentioned?", thread_id=thread_id)
        assert response2 is not None
        assert "❌" not in response2

    def test_error_handling(self, agent_config):
        """Test error handling with invalid queries"""
        agent = LangGraphLanduseAgent(agent_config)

        # Test with a query that should generate an invalid SQL
        response = agent.query("Show me the invalid_table_that_does_not_exist")

        # Should handle error gracefully
        assert response is not None
        assert len(response) > 0
        # May contain error message but should not crash

    def test_tool_usage(self, agent_config):
        """Test that tools are being used correctly"""
        agent = LangGraphLanduseAgent(agent_config)

        # Query that should use get_state_code tool
        response = agent.query("What is the state code for California?")

        assert response is not None
        assert "❌" not in response
        assert any(term in response for term in ["California", "06", "state_code"])

    @pytest.mark.skip(reason="Requires specific test data setup")
    def test_complex_analysis(self, agent_config):
        """Test complex multi-step analysis"""
        agent = LangGraphLanduseAgent(agent_config)

        response = agent.query(
            "Compare agricultural land loss between RCP45 and RCP85 scenarios "
            "in the top 3 states by total agricultural area"
        )

        assert response is not None
        assert "❌" not in response
        assert any(term in response.lower() for term in ["rcp45", "rcp85", "agricultural", "scenario"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
