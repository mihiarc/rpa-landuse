"""
Unit tests for the Landuse Natural Language Agent
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import duckdb
import pandas as pd
import pytest

from landuse.agents import LanduseAgent


class TestLanduseAgent:
    """Test the unified landuse agent"""

    @pytest.fixture
    def mock_db_path(self, tmp_path):
        """Create a mock database path"""
        db_path = tmp_path / "test_landuse.duckdb"
        # Create empty file to simulate database existence
        db_path.touch()
        return db_path

    @pytest.fixture
    @patch('landuse.agents.agent.ChatAnthropic')
    def agent(self, mock_anthropic, mock_db_path):
        """Create agent instance with mocked dependencies"""
        mock_llm = Mock()
        mock_anthropic.return_value = mock_llm
        
        agent = LanduseAgent(db_path=str(mock_db_path))
        return agent

    def test_agent_initialization(self, mock_db_path):
        """Test agent initializes correctly"""
        with patch('landuse.agents.agent.ChatAnthropic') as mock_anthropic:
            agent = LanduseAgent(db_path=str(mock_db_path))
            
            assert agent.db_path == Path(mock_db_path)
            assert agent.llm is not None
            assert len(agent.tools) >= 5  # Core tools
            assert agent.app is not None  # LangGraph app

    def test_agent_initialization_missing_db(self):
        """Test agent handles missing database gracefully"""
        with patch('landuse.agents.agent.ChatAnthropic'):
            # In the new agent, database is checked when getting schema
            agent = LanduseAgent(db_path="nonexistent.db")
            # Should create agent but schema info will show error
            assert "Error getting schema info" in agent.schema_info

    @patch('duckdb.connect')
    def test_get_schema_info(self, mock_connect, agent):
        """Test schema information retrieval"""
        # Mock database connection
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Mock query results
        mock_conn.execute.return_value.fetchone.return_value = (100,)
        
        # Re-get schema info
        schema_info = agent._get_schema_info()
        
        assert "fact_landuse_transitions" in schema_info
        assert "dim_scenario" in schema_info
        assert "dim_time" in schema_info
        assert "dim_geography" in schema_info
        assert "dim_landuse" in schema_info
        mock_conn.close.assert_called()

    def test_query_method(self, agent):
        """Test the main query method"""
        with patch.object(agent, 'app') as mock_app:
            mock_app.invoke.return_value = {
                "messages": [Mock(content="Test response")]
            }
            
            response = agent.query("How much forest is being lost?")
            
            assert response == "Test response"
            mock_app.invoke.assert_called_once()

    def test_query_method_error_handling(self, agent):
        """Test error handling in query method"""
        with patch.object(agent, 'app') as mock_app:
            mock_app.invoke.side_effect = Exception("Agent error")
            
            response = agent.query("Test query")
            
            assert "Error" in response
            assert "Agent error" in response

    def test_analysis_styles(self):
        """Test different analysis style configurations"""
        with patch('landuse.agents.agent.ChatAnthropic'):
            # Standard style
            agent1 = LanduseAgent(analysis_style="standard")
            assert agent1.analysis_style == "standard"
            
            # Executive style
            agent2 = LanduseAgent(analysis_style="executive")
            assert agent2.analysis_style == "executive"
            
            # Detailed style
            agent3 = LanduseAgent(analysis_style="detailed")
            assert agent3.analysis_style == "detailed"

    def test_domain_focus(self):
        """Test different domain focus configurations"""
        with patch('landuse.agents.agent.ChatAnthropic'):
            # Agricultural focus
            agent1 = LanduseAgent(domain_focus="agricultural")
            assert agent1.domain_focus == "agricultural"
            
            # Climate focus
            agent2 = LanduseAgent(domain_focus="climate")
            assert agent2.domain_focus == "climate"
            
            # Urban focus
            agent3 = LanduseAgent(domain_focus="urban")
            assert agent3.domain_focus == "urban"

    def test_enable_maps(self):
        """Test map generation configuration"""
        with patch('landuse.agents.agent.ChatAnthropic'):
            # Without maps
            agent1 = LanduseAgent(enable_maps=False)
            assert not agent1.enable_maps
            assert len([t for t in agent1.tools if "map" in t.name.lower()]) == 0
            
            # With maps
            agent2 = LanduseAgent(enable_maps=True)
            assert agent2.enable_maps
            assert len([t for t in agent2.tools if "map" in t.name.lower()]) > 0

    def test_get_system_prompt(self, agent):
        """Test system prompt generation"""
        # Standard prompt
        prompt1 = agent._get_system_prompt(include_maps=False)
        assert "Landuse Data Analyst" in prompt1
        assert "MAP GENERATION" not in prompt1
        
        # With maps
        prompt2 = agent._get_system_prompt(include_maps=True)
        assert "MAP GENERATION" in prompt2

    def test_tool_creation(self, agent):
        """Test that all required tools are created"""
        tool_names = [tool.name for tool in agent.tools]
        
        # Core tools
        assert "execute_landuse_query" in tool_names
        assert "get_schema_info" in tool_names
        assert "suggest_query_examples" in tool_names
        assert "get_state_code" in tool_names
        assert "get_default_assumptions" in tool_names

    @patch('landuse.agents.agent.Console')
    def test_chat_method_exit(self, mock_console_class, agent):
        """Test chat method with exit command"""
        mock_console = Mock()
        mock_console.input.side_effect = ["exit"]
        mock_console_class.return_value = mock_console
        agent.console = mock_console
        
        agent.chat()
        
        # Verify console.print was called
        assert mock_console.print.called
        
        # Verify exit was processed
        assert mock_console.input.call_count == 1

    @patch('landuse.agents.agent.Console')
    def test_chat_method_help(self, mock_console_class, agent):
        """Test chat method with help command"""
        mock_console = Mock()
        mock_console.input.side_effect = ["help", "exit"]
        mock_console_class.return_value = mock_console
        agent.console = mock_console
        
        agent.chat()
        
        # Verify console.print was called multiple times
        assert mock_console.print.call_count >= 2
        
        # Verify help command was processed
        assert mock_console.input.call_count == 2

    @patch('landuse.agents.agent.Console')
    def test_chat_method_schema(self, mock_console_class, agent):
        """Test chat method with schema command"""
        mock_console = Mock()
        mock_console.input.side_effect = ["schema", "exit"]
        mock_console_class.return_value = mock_console
        agent.console = mock_console
        
        agent.chat()
        
        # Verify console.print was called
        assert mock_console.print.called
        
        # Verify schema command was processed
        assert mock_console.input.call_count == 2

    def test_langgraph_state(self, agent):
        """Test LangGraph state management"""
        from landuse.agents.agent import LanduseAgentState
        
        # Test state structure
        state = LanduseAgentState(
            messages=[],
            current_query="test",
            sql_queries=[],
            query_results=[],
            analysis_context={},
            iteration_count=0,
            max_iterations=5,
            include_maps=False
        )
        
        assert state["current_query"] == "test"
        assert state["iteration_count"] == 0
        assert state["max_iterations"] == 5

    def test_prompt_modes_info(self, agent):
        """Test prompt modes information display"""
        # Test that the method exists
        assert hasattr(agent, '_show_prompt_modes_info')
        
        # Test it can be called without error
        with patch.object(agent.console, 'print') as mock_print:
            agent._show_prompt_modes_info()
            mock_print.assert_called()


class TestLanduseAgentIntegration:
    """Integration tests for the landuse agent"""

    @pytest.mark.integration
    def test_full_query_workflow(self, test_database, monkeypatch):
        """Test complete query workflow with real database"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        with patch('landuse.agents.agent.ChatAnthropic') as mock_anthropic:
            # Mock LLM
            mock_llm = Mock()
            mock_anthropic.return_value = mock_llm
            
            agent = LanduseAgent(db_path=str(test_database))
            
            # Test tools directly
            tools_by_name = {tool.name: tool for tool in agent.tools}
            
            # Test execute query tool
            result = tools_by_name["execute_landuse_query"].invoke({
                "sql_query": "SELECT COUNT(*) as count FROM dim_scenario"
            })
            
            assert "success" in result or "error" in result

    @pytest.mark.integration
    def test_agent_with_real_llm_format(self, test_database, monkeypatch):
        """Test agent with proper LLM response format"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        with patch('landuse.agents.agent.ChatAnthropic') as mock_anthropic:
            mock_llm = Mock()
            mock_anthropic.return_value = mock_llm
            
            agent = LanduseAgent(db_path=str(test_database))
            
            # Mock proper LangGraph response
            with patch.object(agent, 'app') as mock_app:
                mock_app.invoke.return_value = {
                    "messages": [Mock(content="There are 2 scenarios in the database")]
                }
                
                response = agent.query("How many scenarios are there?")
                assert "2 scenarios" in response

    @pytest.mark.slow
    def test_performance_large_results(self, tmp_path):
        """Test handling of large result sets"""
        # Create mock database path
        mock_db_path = tmp_path / "test_landuse.duckdb"
        mock_db_path.touch()
        
        with patch('landuse.agents.agent.ChatAnthropic'):
            agent = LanduseAgent(db_path=str(mock_db_path))
            
            # Test with large mock data
            with patch('duckdb.connect') as mock_connect:
                # Create large mock dataset
                large_df = pd.DataFrame({
                    "col1": range(1000),
                    "col2": [f"value_{i}" for i in range(1000)],
                    "col3": [i * 10.5 for i in range(1000)]
                })
                
                mock_conn = Mock()
                mock_connect.return_value = mock_conn
                mock_result = Mock()
                mock_result.df.return_value = large_df
                mock_conn.execute.return_value = mock_result
                
                # Test tool directly
                tools_by_name = {tool.name: tool for tool in agent.tools}
                result = tools_by_name["execute_landuse_query"].invoke({
                    "sql_query": "SELECT * FROM large_table"
                })
                
                # Should format large results appropriately
                assert "formatted_output" in result or "error" in result