"""
Unit tests for security utilities
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from landuse.utils.security import (
    InputValidator,
    RateLimiter,
    SecureConfig,
    SecurityLogger,
    SQLQueryValidator,
    generate_session_token,
    hash_api_key,
    mask_api_key,
)


class TestSQLQueryValidator:
    """Test SQL query validation"""

    def test_valid_queries(self):
        """Test that valid queries pass validation"""
        validator = SQLQueryValidator()

        valid_queries = [
            "SELECT * FROM dim_scenario",
            "SELECT COUNT(*) FROM fact_landuse_transitions",
            "SELECT s.scenario_name, SUM(f.acres) FROM fact_landuse_transitions f JOIN dim_scenario s ON f.scenario_id = s.scenario_id GROUP BY s.scenario_name",
            "SELECT * FROM dim_time WHERE start_year >= 2020 ORDER BY start_year LIMIT 10",
            "WITH cte AS (SELECT * FROM dim_scenario) SELECT * FROM cte",
        ]

        for query in valid_queries:
            is_valid, error = validator.validate_query(query)
            assert is_valid, f"Query should be valid: {query}, Error: {error}"

    def test_invalid_queries_dangerous_keywords(self):
        """Test that queries with dangerous keywords are blocked"""
        validator = SQLQueryValidator()

        dangerous_queries = [
            ("DROP TABLE dim_scenario", "DROP"),
            ("DELETE FROM fact_landuse_transitions", "DELETE"),
            ("TRUNCATE TABLE dim_scenario", "TRUNCATE"),
            ("ALTER TABLE dim_scenario ADD COLUMN hack VARCHAR", "ALTER"),
            ("UPDATE dim_scenario SET scenario_name = 'hacked'", "UPDATE"),
            ("INSERT INTO dim_scenario VALUES (999, 'hack')", "INSERT"),
            ("GRANT ALL ON dim_scenario TO PUBLIC", "GRANT"),
            ("EXECUTE sp_configure", "EXECUTE"),
        ]

        for query, keyword in dangerous_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, f"Query with {keyword} should be invalid"
            assert keyword in error, f"Error should mention {keyword}"

    def test_invalid_queries_multiple_statements(self):
        """Test that multiple statements are blocked"""
        validator = SQLQueryValidator()

        multi_queries = [
            "SELECT * FROM dim_scenario; DROP TABLE dim_scenario",
            "SELECT * FROM dim_scenario; DELETE FROM dim_scenario WHERE 1=1",
            "SELECT 1; SELECT 2; SELECT 3",
        ]

        for query in multi_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, "Multiple statements should be invalid"
            assert "Multiple statements" in error

    def test_invalid_queries_not_select(self):
        """Test that non-SELECT queries are blocked"""
        validator = SQLQueryValidator()

        non_select_queries = ["SHOW TABLES", "DESCRIBE dim_scenario", "EXPLAIN SELECT * FROM dim_scenario"]

        for query in non_select_queries:
            is_valid, error = validator.validate_query(query)
            assert not is_valid, "Non-SELECT queries should be invalid"
            assert "Only SELECT queries" in error

    def test_sql_injection_patterns(self):
        """Test detection of SQL injection patterns"""
        validator = SQLQueryValidator()

        injection_queries = [
            "SELECT * FROM users WHERE id = 1 OR '1'='1'",  # This is actually allowed in our validator
            "SELECT * FROM users WHERE name = '' OR 1=1--",
            "SELECT 0x414141",  # Hex literal
            "SELECT CHAR(65,66,67)",  # CHAR function
            "SELECT * FROM users INTO OUTFILE '/tmp/hack.txt'",
        ]

        # Note: Some basic OR conditions are allowed, but suspicious functions are not
        is_valid, _ = validator.validate_query(injection_queries[0])
        assert is_valid  # Basic OR is allowed

        is_valid, error = validator.validate_query(injection_queries[2])
        assert not is_valid and "Hexadecimal" in error

        is_valid, error = validator.validate_query(injection_queries[3])
        assert not is_valid and "CHAR function" in error

        is_valid, error = validator.validate_query(injection_queries[4])
        assert not is_valid and "INTO OUTFILE" in error

    def test_comment_removal(self):
        """Test that SQL comments are properly removed"""
        validator = SQLQueryValidator()

        queries_with_comments = [
            "SELECT * FROM dim_scenario -- This is a comment",
            "SELECT * FROM dim_scenario /* multi\nline\ncomment */",
            "SELECT * FROM dim_scenario # MySQL style comment",
        ]

        for query in queries_with_comments:
            is_valid, _ = validator.validate_query(query)
            assert is_valid, "Queries with comments should be valid after cleaning"

    def test_sanitize_identifier(self):
        """Test identifier sanitization"""
        validator = SQLQueryValidator()

        # Valid identifiers
        valid_ids = ["table_name", "column123", "_private", "CamelCase"]
        for identifier in valid_ids:
            result = validator.sanitize_identifier(identifier)
            assert result == identifier

        # Invalid identifiers
        with pytest.raises(ValueError):
            validator.sanitize_identifier("")

        with pytest.raises(ValueError):
            validator.sanitize_identifier("123start")  # Can't start with number

        with pytest.raises(ValueError):
            validator.sanitize_identifier("a" * 65)  # Too long

        # Sanitization
        assert validator.sanitize_identifier("table-name") == "tablename"
        assert validator.sanitize_identifier("table name") == "tablename"
        assert validator.sanitize_identifier("table@name!") == "tablename"


class TestInputValidator:
    """Test input validation utilities"""

    def test_validate_file_path(self):
        """Test file path validation"""
        validator = InputValidator()

        # Valid paths (relative to project)
        valid_path = validator.validate_file_path("data/test.csv")
        assert isinstance(valid_path, Path)

        # Directory traversal attempts
        with pytest.raises(ValueError, match="Directory traversal"):
            validator.validate_file_path("../../../etc/passwd")

        # Outside allowed directories
        with pytest.raises(ValueError, match="Access to path"):
            validator.validate_file_path("/etc/passwd")

        # Extension validation
        with pytest.raises(ValueError, match="extension"):
            validator.validate_file_path("data/test.exe", allowed_extensions=[".csv", ".json"])

    def test_validate_scenario_name(self):
        """Test scenario name validation"""
        validator = InputValidator()

        # Valid scenarios
        valid_scenarios = ["CNRM_CM5_rcp45_ssp1", "GFDL_ESM4_rcp85_ssp5", "IPSL_CM6A_LR_rcp45_ssp2"]

        for scenario in valid_scenarios:
            result = validator.validate_scenario_name(scenario)
            assert result == scenario

        # Invalid scenarios
        invalid_scenarios = [
            "invalid_format",
            "CNRM_CM5_rcp45",  # Missing ssp
            "CNRM_CM5_ssp1",  # Missing rcp
            "cnrm_cm5_rcp45_ssp1",  # Lowercase
            "CNRM_CM5_rcp450_ssp1",  # Wrong rcp format
        ]

        for scenario in invalid_scenarios:
            with pytest.raises(ValueError, match="Invalid scenario"):
                validator.validate_scenario_name(scenario)

    def test_validate_fips_code(self):
        """Test FIPS code validation"""
        validator = InputValidator()

        # Valid FIPS codes
        valid_codes = ["01001", "06037", "48201", "00000", "99999"]
        for code in valid_codes:
            result = validator.validate_fips_code(code)
            assert result == code

        # Invalid FIPS codes
        invalid_codes = ["1001", "123456", "ABCDE", "01-001", ""]
        for code in invalid_codes:
            with pytest.raises(ValueError, match="Invalid FIPS"):
                validator.validate_fips_code(code)

    def test_validate_year_range(self):
        """Test year range validation"""
        validator = InputValidator()

        # Valid ranges
        valid_ranges = [("2012-2020", (2012, 2020)), ("2020-2030", (2020, 2030)), ("1900-2100", (1900, 2100))]

        for year_range, expected in valid_ranges:
            result = validator.validate_year_range(year_range)
            assert result == expected

        # Invalid ranges
        invalid_ranges = [
            "2020-2012",  # Start after end
            "2020-2020",  # Same year
            "1899-2020",  # Too early
            "2020-2201",  # Too late
            "2020-30",  # Wrong format
            "2020",  # Single year
            "invalid",  # Not a year
        ]

        for year_range in invalid_ranges:
            with pytest.raises(ValueError):
                validator.validate_year_range(year_range)


class TestRateLimiter:
    """Test rate limiting functionality"""

    def test_basic_rate_limiting(self):
        """Test basic rate limiting behavior"""
        limiter = RateLimiter(max_calls=3, time_window=1)

        # First 3 calls should succeed
        for i in range(3):
            allowed, error = limiter.check_rate_limit("user1")
            assert allowed, f"Call {i + 1} should be allowed"
            assert error is None

        # 4th call should fail
        allowed, error = limiter.check_rate_limit("user1")
        assert not allowed
        assert "Rate limit exceeded" in error

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        allowed, error = limiter.check_rate_limit("user1")
        assert allowed

    def test_multiple_users(self):
        """Test rate limiting tracks users separately"""
        limiter = RateLimiter(max_calls=2, time_window=60)

        # User 1 makes 2 calls
        for _ in range(2):
            allowed, _ = limiter.check_rate_limit("user1")
            assert allowed

        # User 1 is blocked
        allowed, _ = limiter.check_rate_limit("user1")
        assert not allowed

        # User 2 can still make calls
        allowed, _ = limiter.check_rate_limit("user2")
        assert allowed

    def test_rate_limit_decorator(self):
        """Test rate limiting decorator"""
        limiter = RateLimiter(max_calls=2, time_window=60)

        call_count = 0

        @limiter.rate_limit_decorator(lambda *args, **kwargs: kwargs.get("user_id", "anonymous"))
        def test_function(user_id="anonymous"):
            nonlocal call_count
            call_count += 1
            return "success"

        # First 2 calls succeed
        assert test_function(user_id="test") == "success"
        assert test_function(user_id="test") == "success"
        assert call_count == 2

        # 3rd call raises exception
        with pytest.raises(Exception, match="Rate limit exceeded"):
            test_function(user_id="test")

        assert call_count == 2  # Function not called


class TestSecureConfig:
    """Test secure configuration management"""

    def test_valid_config(self):
        """Test creation of valid configuration"""
        config = SecureConfig(
            anthropic_api_key="sk-ant-" + "a" * 48,
            landuse_model="claude-sonnet-4-5-20250929",
            temperature=0.5,
            max_tokens=2000,
            database_path="data/processed/landuse_analytics.duckdb",
        )

        assert config.anthropic_api_key.startswith("sk-ant-")
        assert config.temperature == 0.5
        assert config.max_tokens == 2000

    def test_config_validation(self):
        """Test configuration validation"""
        # Invalid temperature
        with pytest.raises(ValueError):
            SecureConfig(temperature=1.5)

        # Invalid model
        with pytest.raises(ValueError):
            SecureConfig(landuse_model="invalid-model")

        # Invalid log level
        with pytest.raises(ValueError):
            SecureConfig(log_level="INVALID")

    @patch("pathlib.Path.exists")
    def test_database_path_validation(self, mock_exists):
        """Test database path validation"""
        mock_exists.return_value = False

        with pytest.raises(ValueError, match="Database not found"):
            SecureConfig(database_path="nonexistent.db")

    @patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "sk-ant-test" + "a" * 44,
        "LANDUSE_MODEL": "claude-sonnet-4-5-20250929",
        "TEMPERATURE": "0.7",
        "MAX_TOKENS": "3000"
    })
    @patch("pathlib.Path.exists")
    def test_from_env(self, mock_exists):
        """Test loading configuration from environment"""
        mock_exists.return_value = True

        config = SecureConfig.from_env()

        assert config.anthropic_api_key == os.environ["ANTHROPIC_API_KEY"]
        assert config.landuse_model == "claude-sonnet-4-5-20250929"
        assert config.temperature == 0.7
        assert config.max_tokens == 3000


class TestSecurityLogger:
    """Test security logging functionality"""

    def test_log_query(self):
        """Test query logging"""
        with patch("logging.Logger.info") as mock_info, patch("logging.Logger.warning") as mock_warning:
            logger = SecurityLogger()

            # Successful query
            logger.log_query("user1", "SELECT * FROM table", "success")
            mock_info.assert_called_once()

            # Blocked query
            logger.log_query("user1", "DROP TABLE users", "blocked", "SQL injection detected")
            mock_warning.assert_called_once()

    def test_log_access(self):
        """Test access logging"""
        with patch("logging.Logger.info") as mock_info:
            logger = SecurityLogger()
            logger.log_access("user1", "/api/data", "GET", "allowed")
            mock_info.assert_called_once()

    def test_log_rate_limit(self):
        """Test rate limit logging"""
        with patch("logging.Logger.warning") as mock_warning:
            logger = SecurityLogger()
            logger.log_rate_limit("user1", 60)
            mock_warning.assert_called_once()


class TestUtilityFunctions:
    """Test utility functions"""

    def test_hash_api_key(self):
        """Test API key hashing"""
        key1 = "sk-test123"
        key2 = "sk-test456"

        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)

        # Same key produces same hash
        assert hash1 == hash_api_key(key1)

        # Different keys produce different hashes
        assert hash1 != hash2

        # Hash is always 64 characters (SHA256)
        assert len(hash1) == 64

    def test_generate_session_token(self):
        """Test session token generation"""
        token1 = generate_session_token()
        token2 = generate_session_token()

        # Tokens are unique
        assert token1 != token2

        # Tokens have sufficient length
        assert len(token1) >= 32

        # Tokens are URL-safe
        assert all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in token1)

    def test_mask_api_key(self):
        """Test API key masking"""
        # Normal key
        key = "sk-1234567890abcdef"
        masked = mask_api_key(key)
        assert masked == "sk-1...cdef"

        # Short key
        short_key = "sk-123"
        assert mask_api_key(short_key) == "****"

        # Empty key
        assert mask_api_key("") == "****"
