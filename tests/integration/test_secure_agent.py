"""
Integration tests for the secure landuse query agent
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import os

from landuse.agents.secure_landuse_agent import SecureLanduseAgent, SecureLanduseQueryParams
from landuse.utilities.security import SQLQueryValidator, RateLimiter


class TestSecureLanduseAgent:
    """Integration tests for secure agent"""
    
    @pytest.mark.integration
    def test_agent_initialization(self, test_database, monkeypatch):
        """Test agent initializes correctly with test database"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        agent = SecureLanduseAgent()
        
        assert agent.db_path == test_database
        assert agent.sql_validator is not None
        assert agent.rate_limiter is not None
        assert agent.security_logger is not None
    
    @pytest.mark.integration
    def test_schema_retrieval(self, test_database, monkeypatch):
        """Test agent can retrieve database schema"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        agent = SecureLanduseAgent()
        schema = agent._get_schema_info()
        
        assert "fact_landuse_transitions" in schema
        assert "dim_scenario" in schema
        assert "dim_time" in schema
        assert "dim_geography" in schema
        assert "dim_landuse" in schema
    
    @pytest.mark.integration
    def test_valid_query_execution(self, test_database, monkeypatch):
        """Test execution of valid queries"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        agent = SecureLanduseAgent()
        
        # Simple SELECT query
        result = agent._execute_secure_landuse_query("SELECT COUNT(*) FROM dim_scenario")
        assert "Query Results" in result
        assert "2" in result  # We inserted 2 scenarios in test data
        
        # JOIN query
        result = agent._execute_secure_landuse_query("""
            SELECT s.scenario_name, COUNT(*) as transition_count
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            GROUP BY s.scenario_name
        """)
        assert "Query Results" in result
        assert "CNRM_CM5" in result
    
    @pytest.mark.integration
    def test_sql_injection_prevention(self, test_database, monkeypatch):
        """Test that SQL injection attempts are blocked"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        agent = SecureLanduseAgent()
        
        # Various injection attempts
        malicious_queries = [
            "DROP TABLE dim_scenario",
            "DELETE FROM fact_landuse_transitions",
            "SELECT * FROM dim_scenario; DROP TABLE dim_scenario",
            "UPDATE dim_scenario SET scenario_name = 'hacked'",
            "SELECT * FROM dim_scenario UNION SELECT null,null,null,null INTO OUTFILE '/tmp/data.txt'"
        ]
        
        for query in malicious_queries:
            result = agent._execute_secure_landuse_query(query)
            assert "Security Error" in result or "Error" in result
            assert "Query Results" not in result
    
    @pytest.mark.integration
    def test_rate_limiting(self, test_database, monkeypatch):
        """Test rate limiting functionality"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        # Create agent with strict rate limit
        agent = SecureLanduseAgent()
        agent.rate_limiter = RateLimiter(max_calls=2, time_window=60)
        
        # First two queries should succeed
        for i in range(2):
            response = agent.query("SELECT * FROM dim_scenario", user_id="test_user")
            assert "Error" not in response or "Rate limit" not in response
        
        # Third query should be rate limited
        response = agent.query("SELECT * FROM dim_scenario", user_id="test_user")
        assert "Rate limit" in response or "retry after" in response.lower()
    
    @pytest.mark.integration
    def test_query_limit_enforcement(self, test_database, monkeypatch):
        """Test that query limits are enforced"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        monkeypatch.setenv("DEFAULT_QUERY_LIMIT", "1")
        
        agent = SecureLanduseAgent()
        
        # Query without LIMIT should have one added
        result = agent._execute_secure_landuse_query("SELECT * FROM dim_scenario")
        assert "LIMIT" in result  # The query shown should have LIMIT added
    
    @pytest.mark.integration
    @patch('scripts.agents.secure_landuse_agent.ChatAnthropic')
    @patch('scripts.agents.secure_landuse_agent.ChatOpenAI')
    def test_natural_language_processing(self, mock_openai, mock_anthropic, test_database, monkeypatch):
        """Test natural language query processing"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        # Mock the LLM to return a valid SQL query
        mock_llm = Mock()
        mock_llm.invoke.return_value = Mock(content="SELECT COUNT(*) FROM fact_landuse_transitions WHERE transition_type = 'change'")
        mock_openai.return_value = mock_llm
        
        agent = SecureLanduseAgent()
        
        # Process natural language query
        response = agent.query("How many land use changes occurred?")
        
        # Should process without errors
        assert isinstance(response, str)
        assert "Error" not in response or len(response) > 100  # Either no error or detailed response
    
    @pytest.mark.integration
    def test_parameter_validation(self, test_database, monkeypatch):
        """Test query parameter validation"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        agent = SecureLanduseAgent()
        
        # Test with invalid parameters
        with pytest.raises(ValueError):
            params = SecureLanduseQueryParams(
                query="a" * 1001,  # Too long
                limit=1000
            )
        
        # Valid parameters
        params = SecureLanduseQueryParams(
            query="How much forest is being lost?",
            limit=50,
            include_summary=True
        )
        assert params.query == "How much forest is being lost?"
        assert params.limit == 50
    
    @pytest.mark.integration
    def test_security_logging(self, test_database, monkeypatch, tmp_path):
        """Test that security events are logged"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        # Create a temporary log file
        log_file = tmp_path / "test_security.log"
        
        with patch('scripts.utilities.security.SecurityLogger') as mock_logger_class:
            mock_logger = Mock()
            mock_logger_class.return_value = mock_logger
            
            agent = SecureLanduseAgent()
            
            # Execute a query
            agent._execute_secure_landuse_query("SELECT * FROM dim_scenario")
            
            # Verify logging was called
            mock_logger.log_query.assert_called()
            
            # Try malicious query
            agent._execute_secure_landuse_query("DROP TABLE dim_scenario")
            
            # Verify blocked query was logged
            calls = mock_logger.log_query.call_args_list
            assert any("blocked" in str(call) for call in calls)
    
    @pytest.mark.integration
    def test_read_only_database_access(self, test_database, monkeypatch):
        """Test that database is accessed in read-only mode"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        agent = SecureLanduseAgent()
        
        # Even if a write query somehow passes validation, it should fail at execution
        with patch.object(agent.sql_validator, 'validate_query', return_value=(True, None)):
            result = agent._execute_secure_landuse_query("INSERT INTO dim_scenario VALUES (999, 'test', 'test', 'test', 'test')")
            assert "Error" in result  # Should fail due to read-only connection
    
    @pytest.mark.integration
    def test_error_handling(self, test_database, monkeypatch):
        """Test graceful error handling"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        agent = SecureLanduseAgent()
        
        # Invalid SQL syntax
        result = agent._execute_secure_landuse_query("SELECT * FORM dim_scenario")  # Typo: FORM instead of FROM
        assert "Error" in result
        assert "FORM" in result  # Error should include the problematic query
        
        # Non-existent table
        result = agent._execute_secure_landuse_query("SELECT * FROM non_existent_table")
        assert "Error" in result
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_concurrent_requests(self, test_database, monkeypatch):
        """Test handling of concurrent requests"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        import threading
        import time
        
        agent = SecureLanduseAgent()
        results = []
        
        def make_query(user_id):
            result = agent._execute_secure_landuse_query(f"SELECT '{user_id}', COUNT(*) FROM dim_scenario")
            results.append(result)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=make_query, args=(f"user{i}",))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join(timeout=5)
        
        # All queries should complete successfully
        assert len(results) == 5
        assert all("Query Results" in r for r in results)


class TestSecureAgentWithMocks:
    """Test secure agent with mocked dependencies"""
    
    @patch('scripts.agents.secure_landuse_agent.duckdb.connect')
    def test_database_connection_error(self, mock_connect, monkeypatch):
        """Test handling of database connection errors"""
        monkeypatch.setenv("LANDUSE_DB_PATH", "data/test.db")
        
        # Mock connection failure
        mock_connect.side_effect = Exception("Connection failed")
        
        # Create mock file
        with patch('pathlib.Path.exists', return_value=True):
            agent = SecureLanduseAgent()
            
            result = agent._execute_secure_landuse_query("SELECT * FROM dim_scenario")
            assert "Error" in result
            assert "Connection failed" in result
    
    def test_api_key_validation(self, monkeypatch):
        """Test API key validation during initialization"""
        # Invalid OpenAI key format
        monkeypatch.setenv("OPENAI_API_KEY", "invalid-key")
        monkeypatch.setenv("LANDUSE_DB_PATH", "data/test.db")
        
        with patch('pathlib.Path.exists', return_value=True):
            with pytest.raises(Exception):  # Could be ValueError or ValidationError
                agent = SecureLanduseAgent()
    
    @patch('scripts.agents.secure_landuse_agent.ChatOpenAI')
    def test_llm_error_handling(self, mock_openai, test_database, monkeypatch):
        """Test handling of LLM errors"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        
        # Mock LLM failure
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM API error")
        mock_openai.return_value = mock_llm
        
        agent = SecureLanduseAgent()
        
        response = agent.query("Test query")
        assert "Error" in response