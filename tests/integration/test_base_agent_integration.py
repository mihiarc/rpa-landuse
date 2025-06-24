#!/usr/bin/env python3
"""
Integration tests for the base agent
These tests verify that the base agent can be properly extended and used
"""

import pytest
import os
from pathlib import Path
from unittest.mock import patch

from landuse.agents.base_agent import BaseLanduseAgent
from landuse.agents.constants import DEFAULT_ASSUMPTIONS, RESPONSE_SECTIONS


class SimpleTestAgent(BaseLanduseAgent):
    """Simple implementation for integration testing"""
    
    def _get_agent_prompt(self) -> str:
        """Return a basic prompt for testing"""
        return """
You are a specialized Landuse Data Analyst AI that converts natural language questions into DuckDB SQL queries.

AVAILABLE TOOLS:
{tools}

Tool Names: [{tool_names}]

Use this format:

Question: the input question
Thought: analysis of what's needed
Action: the action to take
Action Input: the input to the action
Observation: the result
Thought: I now know the final answer
Final Answer: the final answer

DATABASE SCHEMA:
{schema_info}

DEFAULT ASSUMPTIONS:
- Scenarios: {default_scenarios}
- Time Period: {default_time}
- Geographic Scope: {default_geo}
- Transition Type: {default_transition}

Question: {input}
{agent_scratchpad}
""".format(
    default_scenarios=DEFAULT_ASSUMPTIONS["scenarios"],
    default_time=DEFAULT_ASSUMPTIONS["time_period"],
    default_geo=DEFAULT_ASSUMPTIONS["geographic_scope"],
    default_transition=DEFAULT_ASSUMPTIONS["transition_type"],
    tools="{tools}",
    tool_names="{tool_names}",
    schema_info="{schema_info}",
    input="{input}",
    agent_scratchpad="{agent_scratchpad}"
)


@pytest.mark.skipif(
    not os.path.exists("data/processed/landuse_analytics.duckdb"),
    reason="Database file not found"
)
class TestBaseAgentIntegration:
    """Integration tests for base agent"""
    
    @pytest.fixture
    def agent(self, monkeypatch):
        """Create a test agent instance"""
        # Override the test database path to use the real database
        monkeypatch.setenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")
        
        # Only create if database exists
        if not os.path.exists("data/processed/landuse_analytics.duckdb"):
            pytest.skip("Database not found")
        
        # Ensure API key is set
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No API key found")
        
        return SimpleTestAgent()
    
    def test_agent_initialization(self, agent):
        """Test that agent initializes correctly"""
        assert agent.db_path.exists()
        assert agent.schema_info is not None
        assert "fact_landuse_transitions" in agent.schema_info
        assert len(agent.tools) >= 3
    
    def test_schema_retrieval(self, agent):
        """Test schema information retrieval"""
        schema = agent._get_schema_help()
        
        # Check for key schema elements
        assert "Landuse Transitions Database Schema" in schema
        assert "dim_scenario" in schema
        assert "dim_time" in schema
        assert "dim_geography" in schema
        assert "dim_landuse" in schema
        assert "fact_landuse_transitions" in schema
    
    def test_query_examples(self, agent):
        """Test query example generation"""
        # Test specific example
        example = agent._suggest_query_examples("agricultural_loss")
        assert "Agricultural land loss" in example
        assert "SELECT" in example
        assert "AVG(f.acres)" in example
        
        # Test all examples
        all_examples = agent._suggest_query_examples()
        assert "Agricultural Loss" in all_examples
        assert "Urbanization" in all_examples
        assert "Climate Comparison" in all_examples
    
    def test_execute_simple_query(self, agent):
        """Test executing a simple query"""
        query = "SELECT COUNT(*) as total_records FROM fact_landuse_transitions LIMIT 1"
        result = agent._execute_landuse_query(query)
        
        assert "Error" not in result or "❌" not in result
        assert "total_records" in result.lower() or "Total Records" in result
    
    def test_execute_query_with_state_codes(self, agent):
        """Test query with state code conversion"""
        query = """
        SELECT 
            g.state_code,
            COUNT(*) as record_count
        FROM fact_landuse_transitions f
        JOIN dim_geography g ON f.geography_id = g.geography_id
        GROUP BY g.state_code
        LIMIT 5
        """
        result = agent._execute_landuse_query(query)
        
        # Should see state names, not codes
        assert any(state in result for state in ["California", "Texas", "Florida", "New York", "State"])
    
    def test_tool_functionality(self, agent):
        """Test that tools work correctly"""
        # Test schema tool
        schema_tool = next(t for t in agent.tools if t.name == "get_schema_info")
        schema_result = schema_tool.func("")
        assert "Landuse Transitions Database Schema" in schema_result
        
        # Test examples tool
        examples_tool = next(t for t in agent.tools if t.name == "suggest_query_examples")
        examples_result = examples_tool.func("agricultural_loss")
        assert "Agricultural land loss" in examples_result
    
    @pytest.mark.skipif(
        not (os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")),
        reason="Requires API key for full agent testing"
    )
    def test_natural_language_query(self, agent):
        """Test processing a natural language query"""
        # This test requires a real LLM API key
        result = agent.query("How many records are in the database?")
        
        # Should get a response (not an error)
        assert result is not None
        assert "Error processing query" not in result
        
        # Response should mention records or data
        assert any(word in result.lower() for word in ["record", "row", "data", "count", "total"])


class TestAgentCustomization:
    """Test agent customization features"""
    
    def test_custom_tools(self, monkeypatch):
        """Test adding custom tools"""
        # Override the test database path
        monkeypatch.setenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")
        
        class CustomToolAgent(SimpleTestAgent):
            def _get_additional_tools(self):
                from langchain_core.tools import Tool
                return [
                    Tool(
                        name="custom_analysis",
                        func=lambda x: "Custom analysis result",
                        description="Perform custom analysis"
                    )
                ]
        
        # Skip if no database
        if not os.path.exists("data/processed/landuse_analytics.duckdb"):
            pytest.skip("Database not found")
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No API key found")
        
        agent = CustomToolAgent()
        tool_names = [t.name for t in agent.tools]
        
        assert "custom_analysis" in tool_names
        assert len(agent.tools) >= 4  # Base 3 + custom 1
    
    def test_query_validation(self, monkeypatch):
        """Test query validation hook"""
        # Override the test database path
        monkeypatch.setenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")
        
        class ValidatingAgent(SimpleTestAgent):
            def _validate_query(self, sql_query: str):
                if "DROP" in sql_query.upper():
                    return "❌ DROP statements are not allowed"
                return None
        
        # Skip if no database
        if not os.path.exists("data/processed/landuse_analytics.duckdb"):
            pytest.skip("Database not found")
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No API key found")
        
        agent = ValidatingAgent()
        result = agent._execute_landuse_query("DROP TABLE test")
        
        assert "DROP statements are not allowed" in result
    
    def test_pre_post_hooks(self, monkeypatch):
        """Test pre and post query hooks"""
        # Override the test database path
        monkeypatch.setenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb")
        
        class HookedAgent(SimpleTestAgent):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.pre_called = False
                self.post_called = False
            
            def _pre_query_hook(self, query: str):
                self.pre_called = True
                if "blocked" in query:
                    return "Query blocked"
                return None
            
            def _post_query_hook(self, output: str):
                self.post_called = True
                return output + "\n[Processed]"
        
        # Skip if no database
        if not os.path.exists("data/processed/landuse_analytics.duckdb"):
            pytest.skip("Database not found")
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
            pytest.skip("No API key found")
        
        agent = HookedAgent()
        
        # Test blocking in pre-hook
        result = agent.query("This query should be blocked")
        assert result == "Query blocked"
        assert agent.pre_called
        
        # Test post-processing
        # Mock the agent to avoid real API calls
        agent.agent = lambda x: {"output": "Original result"}
        agent.agent.invoke = lambda x: {"output": "Original result"}
        
        result = agent.query("Normal query")
        assert "[Processed]" in result
        assert agent.post_called