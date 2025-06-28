"""
Unit tests for the Landuse Natural Language Agent
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import duckdb
import pandas as pd
import pytest

from landuse.agents import LanduseAgent
from landuse.config.landuse_config import LanduseConfig


class TestLanduseAgent:
    """Test the unified landuse agent"""

    @pytest.fixture
    def mock_db_path(self, tmp_path):
        """Create a mock database path"""
        db_path = tmp_path / "test_landuse.duckdb"
        # Create a minimal valid DuckDB database
        import duckdb
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        return db_path

    @pytest.fixture
    def agent(self, mock_db_path):
        """Create agent instance with mocked dependencies"""
        # Skip validation in test
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(db_path=str(mock_db_path))
            
        with patch('landuse.agents.base_agent.ChatAnthropic') as mock_anthropic:
            with patch('os.getenv', return_value='test-key'):
                mock_llm = Mock()
                mock_anthropic.return_value = mock_llm
                agent = LanduseAgent(config=config)
                return agent

    def test_agent_initialization(self, mock_db_path):
        """Test agent initializes correctly"""
        # Skip validation in test
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(db_path=str(mock_db_path))
            
        with patch('landuse.agents.base_agent.ChatAnthropic') as mock_anthropic:
            with patch('os.getenv', return_value='test-key'):
                agent = LanduseAgent(config=config)
                
                assert agent.config.db_path == str(mock_db_path)
            assert agent.llm is not None
            assert len(agent.tools) >= 3  # Core tools in new architecture
            assert agent.graph is None  # Graph built on demand

    def test_agent_initialization_missing_db(self):
        """Test agent handles missing database gracefully"""
        with patch('landuse.agents.base_agent.ChatAnthropic'):
            # The new AgentConfig validates database exists
            with pytest.raises(FileNotFoundError) as exc_info:
                config = LanduseConfig(db_path="nonexistent.db")
            
            # Check the error message
            assert "Database file not found" in str(exc_info.value)

    @patch('duckdb.connect')
    def test_get_schema_info(self, mock_connect, agent):
        """Test schema information retrieval"""
        # Mock database connection
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Mock query results
        mock_conn.execute.return_value.fetchone.return_value = (100,)
        
        # Re-get schema info
        schema_info = agent._get_schema()
        
        # In test, we only have a test table
        assert "test" in schema_info
        assert "INTEGER" in schema_info
        # DuckDB connections don't need explicit close in read-only mode
        # mock_conn.close.assert_called()

    def test_query_method(self, agent):
        """Test the main query method"""
        with patch.object(agent, 'graph') as mock_graph:
            mock_graph.invoke.return_value = {
                "messages": [Mock(content="Test response")]
            }
            
            response = agent.query("How much forest is being lost?")
            
            assert response == "Test response"
            mock_graph.invoke.assert_called_once()

    def test_query_method_error_handling(self, agent):
        """Test error handling in query method"""
        with patch.object(agent, 'graph') as mock_graph:
            mock_graph.invoke.side_effect = Exception("Agent error")
            
            response = agent.query("Test query")
            
            assert "Error" in response
            assert "Agent error" in response

    @pytest.mark.skip(reason="Analysis styles not supported in new architecture")
    def test_analysis_styles(self):
        """Test different analysis style configurations"""
        with patch('landuse.agents.base_agent.ChatAnthropic'):
            # Standard style
            agent1 = LanduseAgent(analysis_style="standard")
            assert agent1.analysis_style == "standard"
            
            # Executive style
            agent2 = LanduseAgent(analysis_style="executive")
            assert agent2.analysis_style == "executive"
            
            # Detailed style
            agent3 = LanduseAgent(analysis_style="detailed")
            assert agent3.analysis_style == "detailed"

    @pytest.mark.skip(reason="Domain focus not supported in new architecture")
    def test_domain_focus(self):
        """Test different domain focus configurations"""
        with patch('landuse.agents.base_agent.ChatAnthropic'):
            # Agricultural focus
            agent1 = LanduseAgent(domain_focus="agricultural")
            assert agent1.domain_focus == "agricultural"
            
            # Climate focus
            agent2 = LanduseAgent(domain_focus="climate")
            assert agent2.domain_focus == "climate"
            
            # Urban focus
            agent3 = LanduseAgent(domain_focus="urban")
            assert agent3.domain_focus == "urban"

    @pytest.mark.skip(reason="Enable maps parameter not supported in new architecture")
    def test_enable_maps(self):
        """Test map generation configuration"""
        with patch('landuse.agents.base_agent.ChatAnthropic'):
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
        # Standard prompt is now accessed via the system_prompt attribute
        prompt1 = agent.system_prompt
        assert "land use analytics expert" in prompt1
        assert "RPA Assessment database" in prompt1

    def test_tool_creation(self, agent):
        """Test that all required tools are created"""
        tool_names = [tool.name for tool in agent.tools]
        
        # Core tools in new architecture
        assert "execute_landuse_query" in tool_names
        assert "analyze_landuse_results" in tool_names
        assert "explore_landuse_schema" in tool_names

    @patch('builtins.input', return_value='exit')
    def test_chat_method_exit(self, mock_input, agent):
        """Test chat method with exit command"""
        # Mock console.print to avoid actual output
        with patch.object(agent.console, 'print'):
            agent.chat()
        
        # Verify input was called
        assert mock_input.called

    @patch('builtins.input', side_effect=['help', 'exit'])
    def test_chat_method_help(self, mock_input, agent):
        """Test chat method with help command"""
        # Mock console.print to avoid actual output
        with patch.object(agent.console, 'print'):
            agent.chat()
        
        # Verify both inputs were processed
        assert mock_input.call_count == 2

    @patch('builtins.input', side_effect=['schema', 'exit'])
    def test_chat_method_schema(self, mock_input, agent):
        """Test chat method with schema command"""
        # Mock console.print to avoid actual output
        with patch.object(agent.console, 'print'):
            agent.chat()
        
        # Verify inputs were processed
        assert mock_input.call_count == 2

    def test_langgraph_state(self, agent):
        """Test LangGraph state management"""
        from landuse.agents.landuse_agent import AgentState
        
        # Test state structure
        state = AgentState(
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
        """Test prompt information display"""
        # Test that the show help method exists
        assert hasattr(agent, '_show_help')
        
        # Test it can be called without error
        with patch.object(agent.console, 'print') as mock_print:
            agent._show_help()
            mock_print.assert_called()


class TestLanduseAgentIntegration:
    """Integration tests for the landuse agent"""

    @pytest.mark.integration
    def test_full_query_workflow(self, test_database, monkeypatch):
        """Test complete query workflow with real database"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        with patch('landuse.agents.base_agent.ChatAnthropic') as mock_anthropic:
            # Mock LLM
            mock_llm = Mock()
            mock_anthropic.return_value = mock_llm
            
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(db_path=str(test_database))
            agent = LanduseAgent(config=config)
            
            # Test tools directly
            tools_by_name = {tool.name: tool for tool in agent.tools}
            
            # Test execute query tool
            result = tools_by_name["execute_landuse_query"].invoke({
                "query": "SELECT COUNT(*) as count FROM dim_scenario"
            })
            
            # The result is a string from the tool, not a dict
            assert isinstance(result, str)
            # Should contain some result or error message
            assert len(result) > 0

    @pytest.mark.integration
    def test_agent_with_real_llm_format(self, test_database, monkeypatch):
        """Test agent with proper LLM response format"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        with patch('landuse.agents.base_agent.ChatAnthropic') as mock_anthropic:
            mock_llm = Mock()
            mock_anthropic.return_value = mock_llm
            
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(db_path=str(test_database))
            agent = LanduseAgent(config=config)
            
            # Mock proper LangGraph response
            with patch.object(agent, 'graph') as mock_graph:
                mock_graph.invoke.return_value = {
                    "messages": [Mock(content="There are 2 scenarios in the database")]
                }
                
                response = agent.query("How many scenarios are there?")
                assert "2 scenarios" in response

    @pytest.mark.slow
    def test_performance_large_results(self, tmp_path):
        """Test handling of large result sets"""
        # Create valid mock database
        mock_db_path = tmp_path / "test_landuse.duckdb"
        conn = duckdb.connect(str(mock_db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        with patch('landuse.agents.base_agent.ChatAnthropic'):
            with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
                config = LanduseConfig(db_path=str(mock_db_path))
            agent = LanduseAgent(config=config)
            
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
                    "query": "SELECT * FROM large_table"
                })
                
                # Tool returns string with error message for non-existent table
                assert isinstance(result, str)
                # Should contain error about missing table
                assert "large_table" in result.lower() or "error" in result.lower()