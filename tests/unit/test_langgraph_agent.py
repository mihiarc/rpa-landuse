#!/usr/bin/env python3
"""
Unit tests for LangGraph-based landuse agent
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Test imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

# TODO: Update to use the correct langgraph agent when refactoring is complete
pytest.skip("LangGraph agent refactoring in progress", allow_module_level=True)
# from landuse.agents.langgraph_agent import (
#     LangGraphLanduseAgent, LandGraphConfig, AgentState
# )


class TestLandGraphConfig:
    """Test configuration for LangGraph agent"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = LandGraphConfig(db_path="test.db")
        
        assert config.db_path == "test.db"
        assert config.model_name == "claude-3-5-sonnet-20241022"
        assert config.temperature == 0.1
        assert config.max_tokens == 4000
        assert config.max_iterations == 8
        assert config.enable_memory is True
        assert config.verbose is False
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = LandGraphConfig(
            db_path="custom.db",
            model_name="gpt-4o-mini",
            temperature=0.5,
            max_tokens=2000,
            max_iterations=5,
            enable_memory=False,
            verbose=True
        )
        
        assert config.db_path == "custom.db"
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.5
        assert config.max_tokens == 2000
        assert config.max_iterations == 5
        assert config.enable_memory is False
        assert config.verbose is True


class TestLangGraphLanduseAgent:
    """Test LangGraph landuse agent functionality"""
    
    @pytest.fixture
    def mock_db_path(self):
        """Create a temporary database path for testing"""
        with tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False) as f:
            yield f.name
        # Cleanup
        if os.path.exists(f.name):
            os.unlink(f.name)
    
    @pytest.fixture
    def test_config(self, mock_db_path):
        """Create test configuration"""
        return LandGraphConfig(
            db_path=mock_db_path,
            model_name="claude-3-5-sonnet-20241022",
            max_iterations=3,
            enable_memory=False,  # Disable for testing
            verbose=False
        )
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key-123'})
    @patch('landuse.agents.langgraph_agent.ChatAnthropic')
    @patch('duckdb.connect')
    def test_agent_initialization(self, mock_connect, mock_llm, test_config):
        """Test agent initialization"""
        # Mock database connection
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = [1000]
        mock_connect.return_value = mock_conn
        
        # Mock LLM
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        # Initialize agent
        agent = LangGraphLanduseAgent(test_config)
        
        # Verify initialization
        assert agent.config == test_config
        assert agent.db_path == Path(test_config.db_path)
        assert agent.llm == mock_llm_instance
        assert len(agent.tools) == 4  # 4 tools defined
        assert agent.graph is not None
        
        # Verify LLM was created with correct parameters
        mock_llm.assert_called_once_with(
            api_key='test-key-123',
            model=test_config.model_name,
            temperature=test_config.temperature,
            max_tokens=test_config.max_tokens
        )
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key-456'})
    @patch('landuse.agents.langgraph_agent.ChatOpenAI')
    @patch('duckdb.connect')
    def test_openai_initialization(self, mock_connect, mock_llm, mock_db_path):
        """Test agent initialization with OpenAI"""
        # Mock database connection
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = [1000]
        mock_connect.return_value = mock_conn
        
        # Mock LLM
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        # Create config with GPT model
        config = LandGraphConfig(
            db_path=mock_db_path,
            model_name="gpt-4o-mini",
            enable_memory=False
        )
        
        # Initialize agent
        agent = LangGraphLanduseAgent(config)
        
        # Verify OpenAI LLM was created
        mock_llm.assert_called_once_with(
            api_key='test-key-456',
            model="gpt-4o-mini",
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
    
    def test_missing_api_key(self, test_config):
        """Test error when API key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key required"):
                LangGraphLanduseAgent(test_config)
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.langgraph_agent.ChatAnthropic')
    @patch('duckdb.connect')
    def test_schema_info_generation(self, mock_connect, mock_llm, test_config):
        """Test schema information generation"""
        # Mock database connection and queries
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Mock table count queries
        count_results = [
            [20],    # dim_scenario
            [6],     # dim_time  
            [3075],  # dim_geography
            [5],     # dim_landuse
            [5400000] # fact_landuse_transitions
        ]
        mock_conn.execute.return_value.fetchone.side_effect = count_results
        
        # Mock LLM
        mock_llm.return_value = Mock()
        
        # Initialize agent
        agent = LangGraphLanduseAgent(test_config)
        
        # Verify schema info contains expected elements
        assert "dim_scenario: 20 records" in agent.schema_info
        assert "dim_time: 6 records" in agent.schema_info
        assert "dim_geography: 3,075 records" in agent.schema_info
        assert "fact_landuse_transitions: 5,400,000 records" in agent.schema_info
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.langgraph_agent.ChatAnthropic')
    @patch('duckdb.connect')
    def test_tools_creation(self, mock_connect, mock_llm, test_config):
        """Test tools are created correctly"""
        # Mock dependencies
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = [1000]
        mock_connect.return_value = mock_conn
        mock_llm.return_value = Mock()
        
        # Initialize agent
        agent = LangGraphLanduseAgent(test_config)
        
        # Verify tools
        assert len(agent.tools) == 4
        
        tool_names = [tool.name for tool in agent.tools]
        expected_tools = [
            "execute_landuse_query",
            "get_schema_info", 
            "get_state_code",
            "suggest_query_examples"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.langgraph_agent.ChatAnthropic')
    @patch('duckdb.connect')
    def test_query_processing(self, mock_connect, mock_llm, test_config):
        """Test query processing workflow"""
        # Mock database
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = [1000]
        mock_connect.return_value = mock_conn
        
        # Mock LLM
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        # Mock graph execution
        mock_response = {
            "messages": [Mock(content="Test response about agricultural land loss")]
        }
        
        # Initialize agent
        agent = LangGraphLanduseAgent(test_config)
        
        # Mock the graph invoke method
        agent.graph.invoke = Mock(return_value=mock_response)
        
        # Test query
        result = agent.query("How much agricultural land is being lost?")
        
        # Verify
        assert result == "Test response about agricultural land loss"
        agent.graph.invoke.assert_called_once()
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.langgraph_agent.ChatAnthropic')
    @patch('duckdb.connect')
    def test_query_with_thread_id(self, mock_connect, mock_llm, mock_db_path):
        """Test query processing with thread ID for memory"""
        # Mock database
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = [1000]
        mock_connect.return_value = mock_conn
        
        # Mock LLM
        mock_llm.return_value = Mock()
        
        # Create config with memory enabled
        config = LandGraphConfig(
            db_path=mock_db_path,
            enable_memory=True
        )
        
        # Initialize agent
        agent = LangGraphLanduseAgent(config)
        
        # Mock graph execution
        mock_response = {
            "messages": [Mock(content="Response with memory")]
        }
        agent.graph.invoke = Mock(return_value=mock_response)
        
        # Test query with thread ID
        result = agent.query("Test query", thread_id="test-thread-123")
        
        # Verify thread ID was passed in config
        call_args = agent.graph.invoke.call_args
        config_arg = call_args[1]['config']
        assert config_arg['configurable']['thread_id'] == "test-thread-123"
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.langgraph_agent.ChatAnthropic')
    @patch('duckdb.connect')
    def test_error_handling(self, mock_connect, mock_llm, test_config):
        """Test error handling in query processing"""
        # Mock database
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = [1000]
        mock_connect.return_value = mock_conn
        
        # Mock LLM
        mock_llm.return_value = Mock()
        
        # Initialize agent
        agent = LangGraphLanduseAgent(test_config)
        
        # Mock graph to raise exception
        agent.graph.invoke = Mock(side_effect=Exception("Test error"))
        
        # Test query
        result = agent.query("Test query")
        
        # Verify error is handled
        assert "❌ Error processing query" in result
        assert "Test error" in result
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.langgraph_agent.ChatAnthropic')
    @patch('duckdb.connect')
    def test_stream_query(self, mock_connect, mock_llm, test_config):
        """Test streaming query functionality"""
        # Mock database
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = [1000]
        mock_connect.return_value = mock_conn
        
        # Mock LLM
        mock_llm.return_value = Mock()
        
        # Initialize agent
        agent = LangGraphLanduseAgent(test_config)
        
        # Mock graph streaming
        mock_chunks = [
            {"step": 1, "data": "Processing..."},
            {"step": 2, "data": "Executing query..."},
            {"step": 3, "data": "Final result"}
        ]
        agent.graph.stream = Mock(return_value=iter(mock_chunks))
        
        # Test streaming
        results = list(agent.stream_query("Test query"))
        
        # Verify chunks were yielded
        assert len(results) == 3
        assert results[0]["step"] == 1
        assert results[1]["step"] == 2
        assert results[2]["step"] == 3


class TestAgentState:
    """Test AgentState TypedDict"""
    
    def test_agent_state_structure(self):
        """Test AgentState has correct structure"""
        # This test verifies the TypedDict is properly defined
        # We can't instantiate TypedDict directly but can verify the structure
        from landuse.agents.langgraph_agent import AgentState
        
        # Verify the class exists and has the expected structure
        assert hasattr(AgentState, '__annotations__')
        
        expected_fields = {
            'messages', 'current_query', 'sql_queries', 
            'query_results', 'analysis_context', 
            'iteration_count', 'max_iterations'
        }
        
        actual_fields = set(AgentState.__annotations__.keys())
        assert expected_fields == actual_fields


class TestToolFunctions:
    """Test individual tool functions"""
    
    @patch('duckdb.connect')
    def test_execute_landuse_query_tool(self, mock_connect):
        """Test the execute_landuse_query tool function"""
        # This would require more complex mocking of the tool function
        # For now, we verify it's importable and callable
        from landuse.agents.langgraph_agent import LangGraphLanduseAgent
        
        # Verify the tool creation doesn't raise errors
        config = LandGraphConfig(db_path="test.db")
        
        # Mock the initialization parts we don't want to test
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('landuse.agents.langgraph_agent.ChatAnthropic'):
                # Mock database connection
                mock_conn = Mock()
                mock_conn.execute.return_value.fetchone.return_value = [1000]
                mock_connect.return_value = mock_conn
                
                agent = LangGraphLanduseAgent(config)
                tools = agent._create_tools()
                
                # Verify we have the expected tools
                assert len(tools) == 4
                
                # Find the execute query tool
                execute_tool = None
                for tool in tools:
                    if tool.name == "execute_landuse_query":
                        execute_tool = tool
                        break
                
                assert execute_tool is not None
                assert callable(execute_tool.func)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])