"""
Unit tests for the Secure Landuse Agent
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from pathlib import Path
import pandas as pd
from datetime import datetime

from landuse.agents.secure_landuse_agent import (
    SecureLanduseAgent, SecureLanduseQueryParams
)
from landuse.utilities.security import (
    SQLQueryValidator, InputValidator, RateLimiter,
    SecureConfig, SecurityLogger
)
from tests.fixtures.agent_fixtures import *


class TestSecureLanduseQueryParams:
    """Test secure query parameters model"""
    
    def test_valid_params(self):
        """Test creation of valid secure parameters"""
        params = SecureLanduseQueryParams(
            query="Show me forest loss",
            limit=100,
            include_summary=True,
            user_id="test_user"
        )
        assert params.query == "Show me forest loss"
        assert params.limit == 100
        assert params.include_summary is True
        assert params.user_id == "test_user"
    
    def test_query_length_validation(self):
        """Test query length validation"""
        # Should accept normal length queries
        params = SecureLanduseQueryParams(query="Normal query")
        assert params.query == "Normal query"
        
        # Should reject very long queries
        with pytest.raises(ValueError, match="Query too long"):
            SecureLanduseQueryParams(query="x" * 1001)
    
    def test_limit_validation(self):
        """Test limit parameter validation"""
        # Valid limits
        params = SecureLanduseQueryParams(query="test", limit=500)
        assert params.limit == 500
        
        # Too high
        with pytest.raises(ValueError):
            SecureLanduseQueryParams(query="test", limit=1001)
        
        # Too low
        with pytest.raises(ValueError):
            SecureLanduseQueryParams(query="test", limit=0)


class TestSecureLanduseAgent:
    """Test the secure landuse agent"""
    
    @pytest.fixture
    def mock_secure_config(self):
        """Mock secure configuration"""
        config = Mock()
        config.database_path = "test.duckdb"
        config.openai_api_key = "test-key"
        config.anthropic_api_key = "test-ant-key"
        config.landuse_model = "gpt-4o-mini"
        config.temperature = 0.1
        config.max_tokens = 2000
        config.max_query_limit = 100
        return config
    
    @pytest.fixture
    def mock_security_components(self):
        """Mock security components"""
        return {
            "sql_validator": Mock(spec=SQLQueryValidator),
            "input_validator": Mock(spec=InputValidator),
            "rate_limiter": Mock(spec=RateLimiter),
            "security_logger": Mock(spec=SecurityLogger)
        }
    
    @pytest.fixture
    @patch('scripts.agents.secure_landuse_agent.SecureConfig.from_env')
    @patch('scripts.agents.secure_landuse_agent.Path.exists')
    @patch('scripts.agents.secure_landuse_agent.ChatOpenAI')
    def agent(self, mock_openai, mock_exists, mock_config, 
              mock_secure_config, mock_security_components):
        """Create secure agent instance with mocked dependencies"""
        mock_exists.return_value = True
        mock_config.return_value = mock_secure_config
        
        # Mock security components
        with patch('scripts.agents.secure_landuse_agent.SQLQueryValidator') as mock_sql_val:
            with patch('scripts.agents.secure_landuse_agent.InputValidator') as mock_input_val:
                with patch('scripts.agents.secure_landuse_agent.RateLimiter') as mock_rate_lim:
                    with patch('scripts.agents.secure_landuse_agent.SecurityLogger') as mock_sec_log:
                        mock_sql_val.return_value = mock_security_components["sql_validator"]
                        mock_input_val.return_value = mock_security_components["input_validator"]
                        mock_rate_lim.return_value = mock_security_components["rate_limiter"]
                        mock_sec_log.return_value = mock_security_components["security_logger"]
                        
                        agent = SecureLanduseAgent()
                        
                        # Inject mocked components
                        agent.sql_validator = mock_security_components["sql_validator"]
                        agent.input_validator = mock_security_components["input_validator"]
                        agent.rate_limiter = mock_security_components["rate_limiter"]
                        agent.security_logger = mock_security_components["security_logger"]
                        
                        return agent
    
    def test_agent_initialization_missing_db(self):
        """Test agent handles missing database"""
        with patch('scripts.agents.secure_landuse_agent.SecureConfig.from_env') as mock_config:
            with patch('scripts.agents.secure_landuse_agent.Path.exists', return_value=False):
                config = Mock()
                config.database_path = "nonexistent.db"
                mock_config.return_value = config
                
                with pytest.raises(FileNotFoundError, match="Database not found"):
                    SecureLanduseAgent()
    
    def test_agent_initialization_missing_api_key(self):
        """Test agent requires API keys"""
        with patch('scripts.agents.secure_landuse_agent.SecureConfig.from_env') as mock_config:
            with patch('scripts.agents.secure_landuse_agent.Path.exists', return_value=True):
                # Test Claude model without key
                config = Mock()
                config.database_path = "test.db"
                config.landuse_model = "claude-3-haiku-20240307"
                config.anthropic_api_key = None
                config.openai_api_key = "test"
                mock_config.return_value = config
                
                with pytest.raises(ValueError, match="Anthropic API key required"):
                    SecureLanduseAgent()
                
                # Test GPT model without key
                config.landuse_model = "gpt-4o-mini"
                config.openai_api_key = None
                
                with pytest.raises(ValueError, match="OpenAI API key required"):
                    SecureLanduseAgent()
    
    def test_execute_secure_landuse_query_validation(self, agent, mock_security_components):
        """Test query validation in secure execution"""
        # Test blocked dangerous query
        mock_security_components["sql_validator"].validate_query.return_value = (
            False, "Dangerous keyword 'DROP' not allowed"
        )
        
        result = agent._execute_secure_landuse_query("DROP TABLE users")
        
        assert "Security Error" in result
        assert "Dangerous keyword 'DROP' not allowed" in result
        
        # Verify logging
        mock_security_components["security_logger"].log_query.assert_called_with(
            user_id="system",
            query="DROP TABLE users",
            status="blocked",
            error="Dangerous keyword 'DROP' not allowed"
        )
    
    @patch('scripts.agents.secure_landuse_agent.duckdb.connect')
    def test_execute_secure_landuse_query_success(self, mock_connect, agent, mock_security_components):
        """Test successful secure query execution"""
        # Mock validation success
        mock_security_components["sql_validator"].validate_query.return_value = (True, None)
        
        # Mock database connection
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        
        # Mock query result
        mock_df = pd.DataFrame({
            "scenario": ["RCP45", "RCP85"],
            "acres": [1000, 1500]
        })
        mock_conn.execute.return_value.df.return_value = mock_df
        
        result = agent._execute_secure_landuse_query("SELECT * FROM scenarios")
        
        assert "Query Results" in result
        assert "2 rows" in result
        assert "RCP45" in result
        
        # Verify read-only connection
        mock_connect.assert_called_with(str(agent.db_path), read_only=True)
        
        # Verify success logging
        mock_security_components["security_logger"].log_query.assert_called_with(
            user_id="system",
            query="SELECT * FROM scenarios",
            status="success",
            error=None
        )
    
    def test_execute_secure_landuse_query_limit_enforcement(self, agent, mock_security_components):
        """Test automatic LIMIT enforcement"""
        mock_security_components["sql_validator"].validate_query.return_value = (True, None)
        
        with patch('scripts.agents.secure_landuse_agent.duckdb.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            mock_conn.execute.return_value.df.return_value = pd.DataFrame()
            
            # Query without LIMIT
            agent._execute_secure_landuse_query("SELECT * FROM table")
            
            # Verify LIMIT was added
            executed_query = mock_conn.execute.call_args[0][0]
            assert "LIMIT 100" in executed_query
    
    def test_execute_secure_landuse_query_error_handling(self, agent, mock_security_components):
        """Test error handling in secure query execution"""
        mock_security_components["sql_validator"].validate_query.return_value = (True, None)
        
        with patch('scripts.agents.secure_landuse_agent.duckdb.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            result = agent._execute_secure_landuse_query("SELECT * FROM table")
            
            assert "Error executing query" in result
            assert "Connection failed" in result
            
            # Verify error logging
            mock_security_components["security_logger"].log_query.assert_called_with(
                user_id="system",
                query="SELECT * FROM table",
                status="error",
                error="Connection failed"
            )
    
    def test_query_with_rate_limiting(self, agent, mock_security_components):
        """Test rate limiting in query method"""
        # Test rate limit exceeded
        mock_security_components["rate_limiter"].check_rate_limit.return_value = (
            False, "Rate limit exceeded: Max 60 requests per 60 seconds"
        )
        
        result = agent.query("Test query", user_id="test_user")
        
        assert "Rate limit exceeded" in result
        
        # Verify rate limit logging
        mock_security_components["security_logger"].log_rate_limit.assert_called_with(
            "test_user", 60
        )
    
    def test_query_success(self, agent, mock_security_components):
        """Test successful query processing"""
        # Mock rate limit OK
        mock_security_components["rate_limiter"].check_rate_limit.return_value = (True, None)
        
        # Mock agent response
        agent.agent = Mock()
        agent.agent.invoke.return_value = {
            "output": "Analysis complete: 1000 acres of forest lost"
        }
        
        result = agent.query("How much forest is lost?", user_id="test_user")
        
        assert "Analysis complete" in result
        assert "1000 acres" in result
    
    def test_suggest_query_examples(self, agent):
        """Test secure query example suggestions"""
        # Test specific category
        result = agent._suggest_query_examples("agricultural_loss")
        assert "Agricultural land loss" in result
        assert "secure query example" in result
        assert "LIMIT" in result
        
        # Test general examples
        result = agent._suggest_query_examples()
        assert "Secure Query Examples" in result
        assert "agricultural" in result.lower()
        assert "urbanization" in result.lower()
    
    @patch('scripts.agents.secure_landuse_agent.Console')
    def test_chat_security_features(self, mock_console_class, agent):
        """Test chat mode shows security features"""
        mock_console = Mock()
        mock_console.input.side_effect = ["exit"]
        mock_console_class.return_value = mock_console
        agent.console = mock_console
        
        agent.chat()
        
        # Verify security panel was shown
        security_shown = False
        for call in mock_console.print.call_args_list:
            if len(call[0]) > 0:
                content = str(call[0][0])
                if "Security Features Active" in content:
                    security_shown = True
                    assert "SQL injection prevention" in content
                    assert "Rate limiting" in content
                    assert "Audit logging" in content
                    break
        
        assert security_shown, "Security features panel not shown"
    
    def test_create_agent_prompt_security_focus(self, agent):
        """Test agent prompt includes security requirements"""
        prompt_template = agent.agent.agent.prompt.template
        
        assert "SECURITY REQUIREMENTS" in prompt_template
        assert "Only generate SELECT queries" in prompt_template
        assert "no data modification allowed" in prompt_template
        assert "Never include user input directly" in prompt_template
        assert "secure SQL queries" in prompt_template


class TestSecureLanduseAgentIntegration:
    """Integration tests for secure landuse agent"""
    
    @pytest.mark.integration
    def test_security_workflow(self, test_database, tmp_path, monkeypatch):
        """Test complete security workflow"""
        monkeypatch.setenv("LANDUSE_DB_PATH", str(test_database))
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        
        with patch('scripts.agents.secure_landuse_agent.ChatOpenAI'):
            with patch('scripts.utilities.security.Path') as mock_path:
                mock_path.return_value.parent.mkdir.return_value = None
                
                agent = SecureLanduseAgent()
                
                # Test various security scenarios
                
                # 1. Test SQL injection attempt
                agent.sql_validator.validate_query = Mock(
                    return_value=(False, "SQL injection detected")
                )
                result = agent._execute_secure_landuse_query(
                    "SELECT * FROM users WHERE id = '1' OR '1'='1'"
                )
                assert "Security Error" in result
                
                # 2. Test valid query
                agent.sql_validator.validate_query = Mock(
                    return_value=(True, None)
                )
                result = agent._execute_secure_landuse_query(
                    "SELECT COUNT(*) FROM dim_scenario"
                )
                assert "Query Results" in result or "Error" in result
                
                # 3. Test rate limiting
                agent.rate_limiter.check_rate_limit = Mock(
                    side_effect=[(True, None)] * 5 + [(False, "Rate limit exceeded")]
                )
                
                # First 5 queries should work
                for i in range(5):
                    result = agent.query(f"Query {i}", user_id="test_user")
                    assert "Error" not in result or "Rate limit" not in result
                
                # 6th query should be rate limited
                result = agent.query("Query 6", user_id="test_user")
                assert "Rate limit exceeded" in result
    
    @pytest.mark.integration
    def test_malicious_query_patterns(self, agent):
        """Test detection of various malicious query patterns"""
        malicious_queries = [
            "'; DROP TABLE users; --",
            "SELECT * FROM users UNION SELECT password FROM admin",
            "UPDATE users SET admin = true",
            "DELETE FROM fact_landuse_transitions",
            "INSERT INTO users VALUES ('hacker', 'admin')",
            "EXEC xp_cmdshell 'dir'",
            "SELECT * FROM users; SHUTDOWN;",
            "CREATE TABLE malware (payload TEXT)"
        ]
        
        for query in malicious_queries:
            # Mock validator to use real validation logic
            validator = SQLQueryValidator()
            is_valid, error = validator.validate_query(query)
            
            if not is_valid:
                agent.sql_validator.validate_query = Mock(
                    return_value=(is_valid, error)
                )
                result = agent._execute_secure_landuse_query(query)
                assert "Security Error" in result
    
    @pytest.mark.integration 
    @pytest.mark.slow
    def test_concurrent_user_rate_limiting(self, agent):
        """Test rate limiting for concurrent users"""
        import threading
        import time
        
        results = {}
        
        def query_as_user(user_id, num_queries):
            user_results = []
            for i in range(num_queries):
                # Mock rate limiter to allow 3 queries per user
                if i < 3:
                    agent.rate_limiter.check_rate_limit = Mock(
                        return_value=(True, None)
                    )
                else:
                    agent.rate_limiter.check_rate_limit = Mock(
                        return_value=(False, "Rate limit exceeded")
                    )
                
                result = agent.query(f"Query {i}", user_id=user_id)
                user_results.append("Rate limit" in result)
                time.sleep(0.1)
            
            results[user_id] = user_results
        
        # Create threads for multiple users
        threads = []
        for user_id in ["user1", "user2", "user3"]:
            t = threading.Thread(
                target=query_as_user,
                args=(user_id, 5)
            )
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify each user hit rate limit after 3 queries
        for user_id, user_results in results.items():
            # First 3 should not be rate limited
            assert not any(user_results[:3])
            # 4th and 5th should be rate limited
            assert all(user_results[3:])
    
    @pytest.mark.integration
    def test_audit_log_generation(self, tmp_path, agent):
        """Test security audit log generation"""
        log_file = tmp_path / "security.log"
        
        # Create a real security logger
        logger = SecurityLogger(str(log_file))
        agent.security_logger = logger
        
        # Perform various operations
        queries = [
            ("SELECT * FROM dim_scenario", "success", True),
            ("DROP TABLE users", "blocked", False),
            ("SELECT * FROM nonexistent", "error", True)
        ]
        
        for query, expected_status, is_valid in queries:
            agent.sql_validator.validate_query = Mock(
                return_value=(is_valid, None if is_valid else "Blocked")
            )
            
            if expected_status == "error":
                with patch('scripts.agents.secure_landuse_agent.duckdb.connect') as mock_conn:
                    mock_conn.side_effect = Exception("Table not found")
                    agent._execute_secure_landuse_query(query)
            else:
                agent._execute_secure_landuse_query(query)
        
        # Verify log file exists and contains entries
        assert log_file.exists()
        
        log_content = log_file.read_text()
        assert "SELECT * FROM dim_scenario" in log_content
        assert "DROP TABLE users" in log_content
        assert "blocked" in log_content