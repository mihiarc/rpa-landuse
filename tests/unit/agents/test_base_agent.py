#!/usr/bin/env python3
"""
Tests for the base agent class
"""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest
from langchain_core.tools import Tool

from landuse.agents.base_agent import BaseLanduseAgent


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test-key-123")
    monkeypatch.setenv("LANDUSE_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("TEMPERATURE", "0.1")
    monkeypatch.setenv("MAX_TOKENS", "4000")


class TestableAgent(BaseLanduseAgent):
    """Concrete implementation for testing"""

    def _get_agent_prompt(self) -> str:
        """Simple test prompt"""
        return """
You are a test agent.

Tools: {tools}
Tool Names: {tool_names}

Question: {input}
Schema: {schema_info}
Agent Scratchpad: {agent_scratchpad}
"""


class TestBaseLanduseAgent:
    """Test the base agent class"""

    @pytest.fixture
    def mock_db_path(self, tmp_path):
        """Create a mock database file"""
        db_file = tmp_path / "test.duckdb"
        db_file.touch()
        return str(db_file)

    @pytest.fixture(autouse=True)
    def mock_duckdb_connect(self, monkeypatch):
        """Mock duckdb.connect to avoid real database operations"""
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = [1000]
        mock_conn.execute.return_value.fetchall.return_value = []

        def mock_connect(*args, **kwargs):
            return mock_conn

        monkeypatch.setattr("duckdb.connect", mock_connect)
        return mock_conn

    def test_initialization_with_openai(self, mock_db_path, mock_env):
        """Test agent initialization with OpenAI model"""
        agent = TestableAgent(db_path=mock_db_path)

        assert agent.db_path == Path(mock_db_path)
        assert agent.model_name == "gpt-4o-mini"
        assert agent.temperature == 0.1
        assert agent.max_tokens == 4000
        assert agent.verbose is False

    def test_initialization_with_anthropic(self, mock_db_path, mock_env, monkeypatch):
        """Test agent initialization with Anthropic model"""
        monkeypatch.setenv("LANDUSE_MODEL", "claude-3-haiku-20240307")

        agent = TestableAgent(db_path=mock_db_path)

        assert agent.model_name == "claude-3-haiku-20240307"

    def test_initialization_missing_db(self, mock_env):
        """Test initialization with missing database"""
        with pytest.raises(FileNotFoundError, match="Database file not found"):
            TestableAgent(db_path="nonexistent.db")

    def test_initialization_missing_api_key(self, mock_db_path, monkeypatch):
        """Test initialization without API key"""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(ValueError, match="API key required"):
            TestableAgent(db_path=mock_db_path)

    def test_mask_api_key(self, mock_db_path, mock_env):
        """Test API key masking"""
        agent = TestableAgent(db_path=mock_db_path)

        # Test normal key
        masked = agent._mask_api_key("sk-1234567890abcdef")
        assert masked == "sk-1...cdef"

        # Test short key
        masked = agent._mask_api_key("short")
        assert masked == "****"

    @patch('duckdb.connect')
    def test_get_schema_info(self, mock_connect, mock_db_path, mock_env):
        """Test schema information retrieval"""
        # Mock database connection
        mock_conn = Mock()
        mock_conn.execute.return_value.fetchone.return_value = [1000]
        mock_conn.execute.return_value.fetchall.return_value = [
            ["CNRM_CM5_rcp45_ssp1"],
            ["CNRM_CM5_rcp85_ssp5"]
        ]
        mock_connect.return_value = mock_conn

        agent = TestableAgent(db_path=mock_db_path)

        # Check schema info
        assert "Landuse Transitions Database Schema" in agent.schema_info
        assert "fact_landuse_transitions" in agent.schema_info
        assert "1,000 records" in agent.schema_info
        assert "CNRM_CM5_rcp45_ssp1" in agent.schema_info

    def test_create_tools(self, mock_db_path, mock_env):
        """Test tool creation"""
        agent = TestableAgent(db_path=mock_db_path)

        assert len(agent.tools) >= 3
        tool_names = [tool.name for tool in agent.tools]
        assert "execute_landuse_query" in tool_names
        assert "get_schema_info" in tool_names
        assert "suggest_query_examples" in tool_names

    @patch('duckdb.connect')
    def test_execute_landuse_query_success(self, mock_connect, mock_db_path, mock_env):
        """Test successful query execution"""
        # Mock database results
        mock_df = pd.DataFrame({
            'state_code': ['06', '48'],
            'acres': [1000.5, 2000.7]
        })
        mock_conn = Mock()
        mock_result = Mock()
        mock_result.df.return_value = mock_df
        mock_conn.execute.return_value = mock_result
        mock_connect.return_value = mock_conn

        agent = TestableAgent(db_path=mock_db_path)
        result = agent._execute_landuse_query("SELECT * FROM test")

        # Check result formatting
        assert "California" in result
        assert "Texas" in result
        assert "1,001" in result or "1,000" in result  # Rounded acres

    @patch('duckdb.connect')
    def test_execute_landuse_query_with_limit(self, mock_connect, mock_db_path, mock_env):
        """Test query execution adds LIMIT when missing"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        agent = TestableAgent(db_path=mock_db_path)

        # Execute query without LIMIT
        agent._execute_landuse_query("SELECT * FROM test")

        # Check LIMIT was added
        executed_query = mock_conn.execute.call_args[0][0]
        assert "LIMIT" in executed_query
        assert "1000" in executed_query

    def test_suggest_query_examples(self, mock_db_path, mock_env):
        """Test query example suggestions"""
        agent = TestableAgent(db_path=mock_db_path)

        # Test specific category
        result = agent._suggest_query_examples("agricultural_loss")
        assert "Agricultural land loss" in result
        assert "SELECT" in result

        # Test general examples
        result = agent._suggest_query_examples()
        assert "Common Query Examples" in result
        assert "Agricultural Loss" in result  # Title-cased in output
        assert "Urbanization" in result

    def test_query_method(self, mock_db_path, mock_env):
        """Test the main query method"""
        agent = TestableAgent(db_path=mock_db_path)

        # Mock the agent executor
        mock_response = {"output": "Test response"}
        agent.agent = Mock()
        agent.agent.invoke.return_value = mock_response

        result = agent.query("Test query")

        assert result == "Test response"
        agent.agent.invoke.assert_called_once()

    def test_query_error_handling(self, mock_db_path, mock_env):
        """Test query error handling"""
        agent = TestableAgent(db_path=mock_db_path)

        # Mock agent to raise error
        agent.agent = Mock()
        agent.agent.invoke.side_effect = Exception("Test error")

        result = agent.query("Test query")

        assert "❌ Error processing query" in result
        assert "Test error" in result

    def test_pre_post_query_hooks(self, mock_db_path, mock_env):
        """Test pre and post query hooks"""
        class HookedAgent(TestableAgent):
            def _pre_query_hook(self, query: str):
                if "forbidden" in query:
                    return "❌ Forbidden query"
                return None

            def _post_query_hook(self, output: str):
                return output + "\n\n✅ Processed by hook"

        agent = HookedAgent(db_path=mock_db_path)
        agent.agent = Mock()
        agent.agent.invoke.return_value = {"output": "Original response"}

        # Test pre-query hook blocking
        result = agent.query("forbidden query")
        assert result == "❌ Forbidden query"

        # Test post-query hook modification
        result = agent.query("normal query")
        assert "Original response" in result
        assert "✅ Processed by hook" in result


class TestAgentSubclassHooks:
    """Test that subclasses can properly override hooks"""

    def test_additional_tools_hook(self, tmp_path, mock_env):
        """Test adding additional tools via hook"""
        db_file = tmp_path / "test.duckdb"
        db_file.touch()

        class ExtendedAgent(TestableAgent):
            def _get_additional_tools(self):
                return [
                    Tool(
                        name="custom_tool",
                        func=lambda x: "Custom result",
                        description="Custom tool"
                    )
                ]

        agent = ExtendedAgent(db_path=str(db_file))
        tool_names = [tool.name for tool in agent.tools]

        assert "custom_tool" in tool_names
        assert len(agent.tools) >= 4

    def test_validate_query_hook(self, tmp_path, mock_env):
        """Test query validation hook"""
        db_file = tmp_path / "test.duckdb"
        db_file.touch()

        class ValidatingAgent(TestableAgent):
            def _validate_query(self, sql_query: str):
                if "DROP" in sql_query.upper():
                    return "❌ DROP statements not allowed"
                return None

        agent = ValidatingAgent(db_path=str(db_file))

        result = agent._execute_landuse_query("DROP TABLE test")
        assert "DROP statements not allowed" in result
