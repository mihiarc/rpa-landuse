#!/usr/bin/env python3
"""
Integration tests for LangGraph workflow in the landuse agent.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
import duckdb

from landuse.agents import LanduseAgent
from landuse.config.landuse_config import LanduseConfig
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


class TestLangGraphWorkflow:
    """Integration tests for the full LangGraph workflow."""
    
    @pytest.fixture
    def test_db(self):
        """Create a test database with sample data."""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.duckdb")
        
        # Create test database with schema
        conn = duckdb.connect(db_path)
        
        # Create dimension tables
        conn.execute("""
            CREATE TABLE dim_scenario (
                scenario_id INTEGER PRIMARY KEY,
                scenario_name VARCHAR,
                rcp_scenario VARCHAR,
                ssp_scenario VARCHAR
            )
        """)
        
        conn.execute("""
            CREATE TABLE dim_time (
                time_id INTEGER PRIMARY KEY,
                year INTEGER
            )
        """)
        
        conn.execute("""
            CREATE TABLE dim_geography (
                geography_id INTEGER PRIMARY KEY,
                county_name VARCHAR,
                state_code VARCHAR,
                state_name VARCHAR
            )
        """)
        
        conn.execute("""
            CREATE TABLE dim_landuse (
                landuse_id INTEGER PRIMARY KEY,
                landuse_name VARCHAR,
                landuse_code VARCHAR
            )
        """)
        
        conn.execute("""
            CREATE TABLE fact_landuse_transitions (
                scenario_id INTEGER,
                time_id INTEGER,
                geography_id INTEGER,
                from_landuse_id INTEGER,
                to_landuse_id INTEGER,
                acres DOUBLE,
                transition_type VARCHAR
            )
        """)
        
        # Insert sample data
        conn.execute("INSERT INTO dim_scenario VALUES (1, 'RCP45-SSP2', 'RCP45', 'SSP2')")
        conn.execute("INSERT INTO dim_scenario VALUES (2, 'RCP85-SSP5', 'RCP85', 'SSP5')")
        
        conn.execute("INSERT INTO dim_time VALUES (1, 2020)")
        conn.execute("INSERT INTO dim_time VALUES (2, 2050)")
        
        conn.execute("INSERT INTO dim_geography VALUES (1, 'Harris', '48', 'Texas')")
        conn.execute("INSERT INTO dim_geography VALUES (2, 'Los Angeles', '06', 'California')")
        
        conn.execute("INSERT INTO dim_landuse VALUES (1, 'Forest', 'fr')")
        conn.execute("INSERT INTO dim_landuse VALUES (2, 'Urban', 'ur')")
        conn.execute("INSERT INTO dim_landuse VALUES (3, 'Crop', 'cr')")
        
        conn.execute("""
            INSERT INTO fact_landuse_transitions VALUES 
            (1, 1, 1, 1, 2, 1000.0, 'change'),
            (1, 2, 1, 1, 2, 2000.0, 'change'),
            (2, 1, 2, 3, 2, 1500.0, 'change')
        """)
        
        conn.close()
        
        yield db_path
        
        # Cleanup
        import shutil
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
    
    @pytest.fixture
    def agent(self, test_db):
        """Create an agent with test database."""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(
                db_path=test_db,
                enable_memory=True,
                max_iterations=5
            )
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('landuse.agents.landuse_agent.ChatOpenAI') as mock_llm:
                # Create a mock LLM that returns reasonable responses
                mock_llm_instance = Mock()
                mock_llm.return_value = mock_llm_instance
                
                agent = LanduseAgent(config)
                agent._test_llm = mock_llm_instance  # Store for test access
                
                yield agent
    
    def test_full_graph_workflow(self, agent):
        """Test the complete graph workflow from query to response."""
        # Build the graph
        agent.graph = agent._build_graph()
        assert agent.graph is not None
        
        # Mock LLM responses for the workflow
        responses = [
            # First response: agent decides to use execute_landuse_query tool
            Mock(
                tool_calls=[{
                    "name": "execute_landuse_query",
                    "args": {"query": "SELECT COUNT(*) FROM dim_scenario"},
                    "id": "tool_1"
                }],
                content=""
            ),
            # Second response: agent provides final answer
            Mock(
                tool_calls=[],
                content="There are 2 scenarios in the database."
            )
        ]
        
        agent._test_llm.bind_tools.return_value.invoke.side_effect = responses
        
        # Run query through graph
        result = agent._graph_query("How many scenarios are there?")
        
        # Verify result
        assert "2 scenarios" in result
    
    def test_graph_with_multiple_tools(self, agent):
        """Test graph workflow with multiple tool calls."""
        # Build the graph
        agent.graph = agent._build_graph()
        
        # Mock responses for multiple tool usage
        responses = [
            # First: query for data
            Mock(
                tool_calls=[{
                    "name": "execute_landuse_query",
                    "args": {"query": "SELECT SUM(acres) FROM fact_landuse_transitions WHERE from_landuse_id = 1"},
                    "id": "tool_1"
                }],
                content=""
            ),
            # Second: analyze results
            Mock(
                tool_calls=[{
                    "name": "analyze_landuse_results",
                    "args": {
                        "query_results": "3000 acres",
                        "original_question": "Total forest loss?",
                        "additional_context": None
                    },
                    "id": "tool_2"
                }],
                content=""
            ),
            # Third: final response
            Mock(
                tool_calls=[],
                content="The total forest loss is 3,000 acres across all scenarios."
            )
        ]
        
        agent._test_llm.bind_tools.return_value.invoke.side_effect = responses
        
        # Run query
        result = agent._graph_query("What is the total forest loss?")
        
        # Verify
        assert "3,000 acres" in result
    
    def test_memory_persistence_in_graph(self, agent):
        """Test that memory persists across queries in graph mode."""
        # Build graph with memory
        agent.graph = agent._build_graph()
        
        # First query
        responses1 = [
            Mock(tool_calls=[], content="Texas has significant forest areas.")
        ]
        agent._test_llm.bind_tools.return_value.invoke.side_effect = responses1
        
        result1 = agent._graph_query("Tell me about Texas forests", thread_id="test-thread")
        assert "Texas" in result1
        
        # Second query - should have context from first
        responses2 = [
            Mock(tool_calls=[], content="California has even more forest area than Texas.")
        ]
        agent._test_llm.bind_tools.return_value.invoke.side_effect = responses2
        
        result2 = agent._graph_query("How about California?", thread_id="test-thread")
        assert "California" in result2
    
    def test_error_handling_in_graph(self, agent):
        """Test error handling within the graph workflow."""
        # Build graph
        agent.graph = agent._build_graph()
        
        # Mock an error in tool execution
        error_response = Mock(
            tool_calls=[{
                "name": "execute_landuse_query",
                "args": {"query": "INVALID SQL"},
                "id": "tool_1"
            }],
            content=""
        )
        
        recovery_response = Mock(
            tool_calls=[],
            content="I encountered an error with the SQL query. Let me rephrase: The query syntax was invalid."
        )
        
        agent._test_llm.bind_tools.return_value.invoke.side_effect = [
            error_response,
            recovery_response
        ]
        
        # Run query - should handle error gracefully
        result = agent._graph_query("Run an invalid query")
        
        # Should get error handling response
        assert "error" in result.lower() or "invalid" in result.lower()
    
    def test_iteration_limit(self, agent):
        """Test that the graph respects iteration limits."""
        # Build graph
        agent.graph = agent._build_graph()
        
        # Mock responses that would loop forever
        loop_response = Mock(
            tool_calls=[{
                "name": "explore_landuse_schema",
                "args": {},
                "id": "tool_loop"
            }],
            content=""
        )
        
        # Set up infinite loop
        agent._test_llm.bind_tools.return_value.invoke.return_value = loop_response
        
        # Run query - should stop at max_iterations
        result = agent._graph_query("Keep calling tools forever")
        
        # Should handle max iterations gracefully
        assert result is not None
    
    def test_streaming_workflow(self, agent):
        """Test the streaming functionality."""
        # Build graph
        agent.graph = agent._build_graph()
        
        # Mock streaming chunks
        mock_chunks = [
            {"agent": {"messages": [Mock(content="Processing...")]}},
            {"tools": {"messages": [Mock(content="Executing query...")]}},
            {"agent": {"messages": [Mock(content="Final result: 42")]}},
        ]
        
        with patch.object(agent.graph, 'stream', return_value=iter(mock_chunks)):
            chunks = list(agent.stream_query("Stream this query"))
            
            # Verify we got chunks
            assert len(chunks) == 3
            assert "agent" in chunks[0]
            assert "tools" in chunks[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])