"""
Unit tests for the Landuse Natural Language Agent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import pandas as pd
import duckdb
from landuse.agents.landuse_natural_language_agent import (
    LanduseNaturalLanguageAgent, LanduseQueryParams
)
from tests.fixtures.agent_fixtures import *


class TestLanduseQueryParams:
    """Test the query parameters model"""
    
    def test_valid_params(self):
        """Test creation of valid parameters"""
        params = LanduseQueryParams(
            query="How much forest is being lost?",
            limit=100,
            include_summary=True
        )
        assert params.query == "How much forest is being lost?"
        assert params.limit == 100
        assert params.include_summary is True
    
    def test_default_params(self):
        """Test default parameter values"""
        params = LanduseQueryParams(query="Test query")
        assert params.limit == 50
        assert params.include_summary is True
    
    def test_query_required(self):
        """Test that query is required"""
        with pytest.raises(ValueError):
            LanduseQueryParams()


class TestLanduseNaturalLanguageAgent:
    """Test the main landuse natural language agent"""
    
    @pytest.fixture
    def mock_db_path(self, tmp_path):
        """Create a mock database path"""
        db_path = tmp_path / "test_landuse.duckdb"
        # Create empty file to simulate database existence
        db_path.touch()
        return db_path
    
    @pytest.fixture
    @patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic')
    def agent(self, mock_anthropic, mock_db_path, mock_anthropic_llm):
        """Create agent instance with mocked dependencies"""
        mock_anthropic.return_value = mock_anthropic_llm
        
        with patch('scripts.agents.landuse_natural_language_agent.Path.exists', return_value=True):
            agent = LanduseNaturalLanguageAgent(str(mock_db_path))
        
        return agent
    
    def test_agent_initialization(self, mock_db_path):
        """Test agent initializes correctly"""
        with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic') as mock_anthropic:
            with patch('scripts.agents.landuse_natural_language_agent.Path.exists', return_value=True):
                agent = LanduseNaturalLanguageAgent(str(mock_db_path))
                
                assert agent.db_path == mock_db_path
                assert agent.llm is not None
                assert len(agent.tools) == 5
                assert agent.agent is not None
    
    def test_agent_initialization_missing_db(self):
        """Test agent handles missing database gracefully"""
        with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic'):
            with patch('scripts.agents.landuse_natural_language_agent.Path.exists', return_value=False):
                agent = LanduseNaturalLanguageAgent("nonexistent.db")
                assert "Database file not found" in agent.schema_info
    
    @patch('scripts.agents.landuse_natural_language_agent.duckdb.connect')
    def test_get_schema_info(self, mock_connect, agent):
        """Test schema information retrieval"""
        # Mock database connection
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Mock query results
        mock_conn.execute.return_value.fetchone.return_value = (100,)
        mock_conn.execute.return_value.fetchall.return_value = [
            ("CNRM_CM5_rcp45_ssp1",),
            ("CNRM_CM5_rcp85_ssp5",)
        ]
        
        schema_info = agent._get_schema_info()
        
        assert "fact_landuse_transitions" in schema_info
        assert "dim_scenario" in schema_info
        assert "dim_time" in schema_info
        assert "dim_geography" in schema_info
        assert "dim_landuse" in schema_info
        mock_conn.close.assert_called_once()
    
    @patch('scripts.agents.landuse_natural_language_agent.duckdb.connect')
    def test_execute_landuse_query_valid(self, mock_connect, agent):
        """Test executing a valid SQL query"""
        # Mock database connection
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Mock query result
        mock_result = Mock()
        mock_df = pd.DataFrame({
            "scenario_name": ["CNRM_CM5_rcp45_ssp1", "CNRM_CM5_rcp85_ssp5"],
            "total_acres": [1000000, 1500000]
        })
        mock_result.df.return_value = mock_df
        mock_conn.execute.return_value = mock_result
        
        result = agent._execute_landuse_query("SELECT * FROM dim_scenario")
        
        assert "Query Results" in result
        assert "2 rows" in result
        assert "CNRM_CM5" in result
        assert mock_conn.close.called
    
    def test_execute_landuse_query_with_markdown(self, agent):
        """Test query execution strips markdown formatting"""
        with patch('scripts.agents.landuse_natural_language_agent.duckdb.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.df.return_value = pd.DataFrame({"col": [1]})
            
            # Test various markdown formats
            queries = [
                "```sql\nSELECT * FROM table\n```",
                "```SELECT * FROM table```",
                "SELECT * FROM table```"
            ]
            
            for query in queries:
                result = agent._execute_landuse_query(query)
                # Verify SQL was cleaned
                actual_query = mock_conn.execute.call_args[0][0]
                assert not actual_query.startswith('```')
                assert not actual_query.endswith('```')
    
    def test_execute_landuse_query_empty_result(self, agent):
        """Test handling of empty query results"""
        with patch('scripts.agents.landuse_natural_language_agent.duckdb.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.df.return_value = pd.DataFrame()
            
            result = agent._execute_landuse_query("SELECT * FROM empty_table")
            
            assert "no results" in result
            assert "SELECT * FROM empty_table" in result
    
    def test_execute_landuse_query_error(self, agent):
        """Test error handling in query execution"""
        with patch('scripts.agents.landuse_natural_language_agent.duckdb.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            result = agent._execute_landuse_query("SELECT * FROM table")
            
            assert "Error" in result
            assert "Connection failed" in result
    
    def test_suggest_query_examples(self, agent):
        """Test query example suggestions"""
        # Test specific category
        result = agent._suggest_query_examples("agricultural_loss")
        assert "Agricultural land loss" in result
        assert "```sql" in result
        
        # Test general category
        result = agent._suggest_query_examples()
        assert "Agricultural Loss" in result or "agricultural" in result.lower()
        assert "Urbanization" in result or "urban" in result.lower()
        assert "Climate Comparison" in result or "climate" in result.lower()
    
    def test_explain_query_results(self, agent):
        """Test query result explanation"""
        result = agent._explain_query_results("test results")
        assert "Interpreting Landuse Transition Results" in result
        assert "Key Metrics" in result
        assert "Business Insights" in result
    
    def test_get_default_assumptions(self, agent):
        """Test default assumptions documentation"""
        result = agent._get_default_assumptions()
        assert "Default Analysis Assumptions" in result
        assert "Climate Scenarios" in result
        assert "Time Periods" in result
        assert "Geographic Scope" in result
    
    def test_query_method(self, agent, mock_agent_executor):
        """Test the main query method"""
        agent.agent = mock_agent_executor
        
        response = agent.query("How much forest is being lost?")
        
        assert response == "Test response from agent"
        mock_agent_executor.invoke.assert_called_once()
        call_args = mock_agent_executor.invoke.call_args[0][0]
        assert call_args["input"] == "How much forest is being lost?"
        assert "schema_info" in call_args
    
    def test_query_method_error_handling(self, agent):
        """Test error handling in query method"""
        agent.agent = Mock()
        agent.agent.invoke.side_effect = Exception("Agent error")
        
        response = agent.query("Test query")
        
        assert "Error" in response
        assert "Agent error" in response
    
    @patch('scripts.agents.landuse_natural_language_agent.Console')
    def test_chat_method_exit(self, mock_console_class, agent):
        """Test chat method with exit command"""
        mock_console = Mock()
        mock_console.input.side_effect = ["exit"]
        mock_console_class.return_value = mock_console
        agent.console = mock_console
        
        agent.chat()
        
        # Verify console.print was called
        assert mock_console.print.called
        
        # Verify exit was processed (input was called once)
        assert mock_console.input.call_count == 1
    
    @patch('scripts.agents.landuse_natural_language_agent.Console')
    def test_chat_method_help(self, mock_console_class, agent):
        """Test chat method with help command"""
        mock_console = Mock()
        mock_console.input.side_effect = ["help", "exit"]
        mock_console_class.return_value = mock_console
        agent.console = mock_console
        
        agent.chat()
        
        # Verify console.print was called multiple times
        assert mock_console.print.call_count >= 2
        
        # Verify help command was processed (input called twice)
        assert mock_console.input.call_count == 2
    
    @patch('scripts.agents.landuse_natural_language_agent.Console')
    def test_chat_method_schema(self, mock_console_class, agent):
        """Test chat method with schema command"""
        mock_console = Mock()
        mock_console.input.side_effect = ["schema", "exit"]
        mock_console_class.return_value = mock_console
        agent.console = mock_console
        
        agent.chat()
        
        # Verify console.print was called
        assert mock_console.print.called
        
        # Verify schema command was processed (input called twice)
        assert mock_console.input.call_count == 2
    
    def test_tool_functions(self, agent):
        """Test that all tool functions are callable"""
        # Test each tool can be called
        tools_by_name = {tool.name: tool for tool in agent.tools}
        
        # Test execute_landuse_query tool
        assert "execute_landuse_query" in tools_by_name
        
        # Test get_schema_info tool
        assert "get_schema_info" in tools_by_name
        result = tools_by_name["get_schema_info"].func("")
        assert "Landuse Transitions Database Schema" in result
        
        # Test suggest_query_examples tool
        assert "suggest_query_examples" in tools_by_name
        result = tools_by_name["suggest_query_examples"].func("general")
        assert "Example" in result
        
        # Test explain_query_results tool
        assert "explain_query_results" in tools_by_name
        result = tools_by_name["explain_query_results"].func("test")
        assert "Interpreting" in result
        
        # Test get_default_assumptions tool
        assert "get_default_assumptions" in tools_by_name
        result = tools_by_name["get_default_assumptions"].func("")
        assert "Default" in result
    
    def test_create_agent_prompt(self, agent):
        """Test agent prompt creation"""
        # Access the prompt through the agent executor
        prompt_template = agent.agent.agent.prompt.template
        
        assert "Landuse Data Analyst AI" in prompt_template
        assert "DuckDB SQL" in prompt_template
        assert "DEFAULT ASSUMPTIONS" in prompt_template
        assert "{input}" in prompt_template
        assert "{schema_info}" in prompt_template
        assert "{agent_scratchpad}" in prompt_template


class TestLanduseAgentIntegration:
    """Integration tests for the landuse agent"""
    
    @pytest.mark.integration
    def test_full_query_workflow(self, test_database, monkeypatch):
        """Test complete query workflow with real database"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic') as mock_anthropic:
            # Mock LLM to return a valid query
            mock_llm = Mock()
            mock_llm.invoke.return_value = Mock(
                content="SELECT COUNT(*) as scenario_count FROM dim_scenario"
            )
            mock_anthropic.return_value = mock_llm
            
            agent = LanduseNaturalLanguageAgent(str(test_database))
            
            # Execute a query through the tools
            result = agent._execute_landuse_query(
                "SELECT COUNT(*) as count FROM dim_scenario"
            )
            
            assert "Query Results" in result
            assert "count" in result.lower()
    
    @pytest.mark.integration
    def test_agent_with_sample_queries(self, test_database, sample_nl_queries, monkeypatch):
        """Test agent with various natural language queries"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        with patch('scripts.agents.landuse_natural_language_agent.ChatAnthropic') as mock_anthropic:
            mock_llm = Mock()
            mock_anthropic.return_value = mock_llm
            
            agent = LanduseNaturalLanguageAgent(str(test_database))
            
            for query_type, nl_query in sample_nl_queries.items():
                # Mock agent response
                agent.agent = Mock()
                agent.agent.invoke.return_value = {
                    "output": f"Processed query about {query_type}"
                }
                
                response = agent.query(nl_query)
                assert query_type in response.lower()
    
    @pytest.mark.slow
    def test_performance_large_results(self, agent):
        """Test handling of large result sets"""
        with patch('scripts.agents.landuse_natural_language_agent.duckdb.connect') as mock_connect:
            # Create large mock dataset
            large_df = pd.DataFrame({
                "col1": range(1000),
                "col2": [f"value_{i}" for i in range(1000)],
                "col3": [i * 10.5 for i in range(1000)]
            })
            
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.df.return_value = large_df
            
            result = agent._execute_landuse_query("SELECT * FROM large_table")
            
            # Should only show first 20 rows
            assert "first 20 rows" in result
            assert "980 more rows" in result
            assert "Summary Statistics" in result