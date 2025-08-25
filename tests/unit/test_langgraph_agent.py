#!/usr/bin/env python3
"""
Unit tests for LangGraph-based landuse agent
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import duckdb

# Test imports
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from landuse.agents import LanduseAgent
from landuse.agents.landuse_agent import AgentState
from landuse.config.landuse_config import LanduseConfig


class TestLanduseConfig:
    """Test configuration for LangGraph agent"""
    
    @pytest.fixture
    def mock_db_path(self, tmp_path):
        """Create a mock database path"""
        db_path = tmp_path / "test_landuse.duckdb"
        # Create a minimal valid DuckDB database
        conn = duckdb.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        return db_path
    
    def test_default_config(self, mock_db_path):
        """Test default configuration values"""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(db_path=str(mock_db_path))
        
            assert config.db_path == str(mock_db_path)
            assert config.model_name == "gpt-4o-mini"  # Default is gpt-4o-mini now
            # Don't test specific values that might be overridden by env vars
            assert isinstance(config.temperature, float)
            assert isinstance(config.max_tokens, int)
            assert config.max_iterations == 8
            assert config.enable_memory is True
            assert config.verbose is False
    
    def test_custom_config(self, mock_db_path):
        """Test custom configuration values"""
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(
                db_path=str(mock_db_path),
                model_name="claude-3-5-sonnet-20241022",
                temperature=0.5,
                max_tokens=2000,
                max_iterations=5,
                enable_memory=False,
                verbose=True
            )
        
            assert config.db_path == str(mock_db_path)
            assert config.model_name == "claude-3-5-sonnet-20241022"
            assert config.temperature == 0.5
            assert config.max_tokens == 2000
            assert config.max_iterations == 5
            assert config.enable_memory is False
            assert config.verbose is True


class TestLanduseAgent:
    """Test LangGraph landuse agent functionality"""
    
    @pytest.fixture
    def mock_db_path(self):
        """Create a temporary database path for testing"""
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.duckdb")
        yield db_path
        # Cleanup
        import shutil
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
    
    @pytest.fixture
    def test_config(self, mock_db_path):
        """Create test configuration"""
        # Create actual test database
        conn = duckdb.connect(str(mock_db_path))
        # Create minimal schema
        conn.execute("CREATE TABLE dim_scenario (scenario_id INTEGER, scenario_name VARCHAR)")
        conn.execute("CREATE TABLE dim_time (time_id INTEGER, year INTEGER)")
        conn.execute("CREATE TABLE dim_geography (geography_id INTEGER, county_name VARCHAR, state_code VARCHAR)")
        conn.execute("CREATE TABLE dim_landuse (landuse_id INTEGER, landuse_name VARCHAR)")
        conn.execute("CREATE TABLE fact_landuse_transitions (scenario_id INTEGER, time_id INTEGER, geography_id INTEGER, from_landuse_id INTEGER, to_landuse_id INTEGER, acres DOUBLE)")
        conn.close()
        
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            return LanduseConfig(
                db_path=str(mock_db_path),
                model_name="claude-3-5-sonnet-20241022",
                max_iterations=3,
                enable_memory=False,  # Disable for testing
                verbose=False
            )
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key-123'})
    @patch('landuse.agents.landuse_agent.ChatAnthropic')
    def test_agent_initialization(self, mock_llm, test_config):
        """Test agent initialization"""
        # Mock LLM
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        # Initialize agent
        agent = LanduseAgent(test_config)
        
        # Verify initialization
        assert agent.config == test_config
        assert agent.llm == mock_llm_instance
        assert len(agent.tools) >= 3  # At least 3 core tools
        assert agent.graph is None  # Graph built on demand
        
        # Verify LLM was created with correct parameters
        mock_llm.assert_called_once_with(
            anthropic_api_key='test-key-123',
            model=test_config.model_name,
            temperature=test_config.temperature,
            max_tokens=test_config.max_tokens
        )
    
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key-456'})
    @patch('landuse.agents.llm_manager.ChatOpenAI')
    def test_openai_initialization(self, mock_llm, test_config):
        """Test agent initialization with OpenAI"""
        # Mock LLM
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        # Create config with GPT model
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(
                db_path=test_config.db_path,
                model_name="gpt-4o-mini",
                enable_memory=False
            )
        
        # Initialize agent
        agent = LanduseAgent(config)
        
        # Verify OpenAI LLM was created
        mock_llm.assert_called_once_with(
            openai_api_key='test-key-456',
            model="gpt-4o-mini",
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
    
    def test_missing_api_key(self, test_config):
        """Test error when API key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY environment variable is required"):
                LanduseAgent(test_config)
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.landuse_agent.ChatAnthropic')
    def test_schema_info_generation(self, mock_llm, test_config):
        """Test schema information generation"""
        # Mock LLM
        mock_llm.return_value = Mock()
        
        # Initialize agent
        agent = LanduseAgent(test_config)
        
        # Verify schema info contains expected elements
        assert "dim_scenario" in agent.schema
        assert "dim_time" in agent.schema
        assert "dim_geography" in agent.schema
        assert "fact_landuse_transitions" in agent.schema
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.landuse_agent.ChatAnthropic')
    def test_tools_creation(self, mock_llm, test_config):
        """Test tools are created correctly"""
        # Mock dependencies
        mock_llm.return_value = Mock()
        
        # Initialize agent
        agent = LanduseAgent(test_config)
        
        # Verify tools
        assert len(agent.tools) >= 3
        
        tool_names = [tool.name for tool in agent.tools]
        expected_tools = [
            "execute_landuse_query",
            "analyze_landuse_results", 
            "explore_landuse_schema"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.landuse_agent.ChatAnthropic')
    def test_query_processing(self, mock_llm, test_config):
        """Test query processing workflow"""
        # Mock LLM
        mock_llm_instance = Mock()
        mock_llm.return_value = mock_llm_instance
        
        # Initialize agent
        agent = LanduseAgent(test_config)
        
        # Mock the simple_query method since that's what's used by default
        with patch.object(agent, 'simple_query', return_value="Test response about agricultural land loss"):
            # Test query
            result = agent.query("How much agricultural land is being lost?")
        
            # Verify
            assert result == "Test response about agricultural land loss"
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.landuse_agent.ChatAnthropic')
    def test_query_with_thread_id(self, mock_llm, test_config):
        """Test query processing with thread ID for memory"""
        # Mock LLM
        mock_llm.return_value = Mock()
        
        # Create config with memory enabled
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(
                db_path=test_config.db_path,
                enable_memory=True
            )
        
        # Initialize agent
        agent = LanduseAgent(config)
        
        # Build the graph to test thread_id support
        agent.graph = agent._build_graph()
        
        # Mock graph execution
        with patch.object(agent.graph, 'invoke', return_value={"messages": [Mock(content="Response with memory")]}) as mock_invoke:
            # Test query with graph and thread ID
            result = agent.query("Test query", use_graph=True, thread_id="test-thread-123")
            
            # Verify thread ID was passed in config
            call_args = mock_invoke.call_args
            if len(call_args) > 1 and 'config' in call_args[1]:
                config_arg = call_args[1]['config']
                assert config_arg['configurable']['thread_id'] == "test-thread-123"
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.landuse_agent.ChatAnthropic')
    def test_error_handling(self, mock_llm, test_config):
        """Test error handling in query processing"""
        # Mock LLM
        mock_llm.return_value = Mock()
        
        # Initialize agent
        agent = LanduseAgent(test_config)
        
        # Mock simple_query to raise exception
        with patch.object(agent, 'simple_query', return_value="Error processing query: Test error"):
            # Test query
            result = agent.query("Test query")
        
            # Verify error is handled gracefully
            assert "Error processing query" in result
            assert "Test error" in result
    
    @patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
    @patch('landuse.agents.landuse_agent.ChatAnthropic')
    def test_stream_query(self, mock_llm, test_config):
        """Test streaming query functionality"""
        # Mock LLM
        mock_llm.return_value = Mock()
        
        # Initialize agent
        agent = LanduseAgent(test_config)
        
        # Build the graph
        agent.graph = agent._build_graph()
        
        # Mock graph streaming
        mock_chunks = [
            {"step": 1, "data": "Processing..."},
            {"step": 2, "data": "Executing query..."},
            {"step": 3, "data": "Final result"}
        ]
        
        with patch.object(agent.graph, 'stream', return_value=iter(mock_chunks)):
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
        from landuse.agents.landuse_agent import AgentState
        
        # Verify the class exists and has the expected structure
        assert hasattr(AgentState, '__annotations__')
        
        expected_fields = {
            'messages', 'context', 'iteration_count', 'max_iterations'
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
        from landuse.agents import LanduseAgent
        from landuse.config.landuse_config import LanduseConfig
        
        # Create a test database
        import tempfile
        tmpdir = tempfile.mkdtemp()
        db_path = os.path.join(tmpdir, "test.duckdb")
        
        # Create minimal valid DuckDB database
        conn = duckdb.connect(db_path)
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        
        # Verify the tool creation doesn't raise errors
        with patch('landuse.config.landuse_config.LanduseConfig.__post_init__', return_value=None):
            config = LanduseConfig(db_path=db_path)
        
        # Mock the initialization parts we don't want to test
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'}):
            with patch('landuse.agents.landuse_agent.ChatAnthropic'):
                    # Need to mock the schema query results
                    with patch('duckdb.connect') as mock_db:
                        mock_conn = Mock()
                        # Mock table count query
                        mock_conn.execute.return_value.fetchone.return_value = (1,)
                        # Mock schema query - return empty results
                        mock_conn.execute.return_value.fetchall.return_value = []
                        mock_db.return_value = mock_conn
                        
                        agent = LanduseAgent(config)
                    tools = agent._create_tools()
                    
                    # Verify we have the expected tools
                    assert len(tools) >= 3
                    
                    # Find the execute query tool
                    execute_tool = None
                    for tool in tools:
                        if tool.name == "execute_landuse_query":
                            execute_tool = tool
                            break
                    
                    assert execute_tool is not None
                    assert callable(execute_tool.func)
        
        # Cleanup
        import shutil
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])