#!/usr/bin/env python3
"""
Security utilities for the Landuse Analysis System
Provides input validation, sanitization, and security helpers
"""

import hashlib
import logging
import re
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

class SQLQueryValidator:
    """Validates and sanitizes SQL queries for security"""

    # Dangerous SQL keywords that should be blocked in user input
    DANGEROUS_KEYWORDS = {
        'DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'REPLACE',
        'INSERT', 'UPDATE', 'GRANT', 'REVOKE', 'EXECUTE', 'EXEC',
        'SCRIPT', 'SHUTDOWN', 'KILL'
    }

    # Allowed SQL keywords for read-only queries
    ALLOWED_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT', 'RIGHT', 'INNER',
        'OUTER', 'ON', 'AS', 'WITH', 'GROUP', 'BY', 'ORDER', 'HAVING',
        'LIMIT', 'OFFSET', 'UNION', 'DISTINCT', 'COUNT', 'SUM', 'AVG',
        'MIN', 'MAX', 'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AND',
        'OR', 'NOT', 'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'IS', 'NULL'
    }

    # Pattern to detect SQL comments
    SQL_COMMENT_PATTERNS = [
        re.compile(r'--.*$', re.MULTILINE),  # -- style comments
        re.compile(r'/\*.*?\*/', re.DOTALL),  # /* */ style comments
        re.compile(r'#.*$', re.MULTILINE)     # # style comments (MySQL)
    ]

    @classmethod
    def validate_query(cls, query: str) -> tuple[bool, Optional[str]]:
        """
        Validate a SQL query for safety
        Returns (is_valid, error_message)
        """
        if not query or not isinstance(query, str):
            return False, "Query must be a non-empty string"

        # Remove comments first
        cleaned_query = cls._remove_comments(query)

        # Convert to uppercase for keyword checking
        query_upper = cleaned_query.upper()

        # Check for multiple statements (semicolon not at end)
        if ';' in cleaned_query.rstrip(';'):
            return False, "Multiple statements not allowed"

        # Check for dangerous keywords
        for keyword in cls.DANGEROUS_KEYWORDS:
            if re.search(r'\b' + keyword + r'\b', query_upper):
                return False, f"Dangerous keyword '{keyword}' not allowed"

        # Basic structure validation - allow WITH (CTE) or SELECT
        if not (query_upper.strip().startswith('SELECT') or query_upper.strip().startswith('WITH')):
            return False, "Only SELECT queries are allowed"

        # Check for suspicious patterns
        suspicious_patterns = [
            (r'0x[0-9a-fA-F]+', "Hexadecimal literals not allowed"),
            (r'char\s*\(', "CHAR function not allowed"),
            (r'concat\s*\(', "CONCAT function not allowed for security"),
            (r'into\s+outfile', "INTO OUTFILE not allowed"),
            (r'into\s+dumpfile', "INTO DUMPFILE not allowed"),
        ]

        for pattern, message in suspicious_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                return False, message

        return True, None

    @classmethod
    def _remove_comments(cls, query: str) -> str:
        """Remove SQL comments from query"""
        result = query
        for pattern in cls.SQL_COMMENT_PATTERNS:
            result = pattern.sub('', result)
        return result

    @classmethod
    def sanitize_identifier(cls, identifier: str) -> str:
        """
        Sanitize a database identifier (table name, column name)
        Only allows alphanumeric characters and underscores
        """
        if not identifier:
            raise ValueError("Identifier cannot be empty")

        # Only allow alphanumeric and underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', identifier)

        # Must start with letter or underscore
        if not re.match(r'^[a-zA-Z_]', sanitized):
            raise ValueError(f"Invalid identifier: {identifier}")

        # Length check
        if len(sanitized) > 64:  # Standard SQL identifier length limit
            raise ValueError(f"Identifier too long: {identifier}")

        return sanitized


class InputValidator:
    """General input validation utilities"""

    @staticmethod
    def validate_file_path(path: str, allowed_extensions: Optional[list[str]] = None) -> Path:
        """
        Validate and sanitize file paths
        Prevents directory traversal attacks
        """
        # Check for directory traversal attempts first
        if '..' in path:
            raise ValueError("Directory traversal not allowed")

        # Convert to Path object
        file_path = Path(path).resolve()

        # Check if path is within allowed directories
        allowed_dirs = [
            Path.cwd() / "data",
            Path.cwd() / "scripts",
            Path.cwd() / "config"
        ]

        if not any(str(file_path).startswith(str(allowed_dir)) for allowed_dir in allowed_dirs):
            raise ValueError(f"Access to path {file_path} not allowed")

        # Check extension if specified
        if allowed_extensions and file_path.suffix not in allowed_extensions:
            raise ValueError(f"File extension {file_path.suffix} not allowed")

        return file_path

    @staticmethod
    def validate_scenario_name(scenario: str) -> str:
        """Validate scenario name format"""
        # Expected format: MODEL_rcpXX_sspY
        pattern = r'^[A-Z0-9_]+_rcp\d{2}_ssp\d$'
        if not re.match(pattern, scenario):
            raise ValueError(f"Invalid scenario name format: {scenario}")
        return scenario

    @staticmethod
    def validate_fips_code(fips: str) -> str:
        """Validate FIPS code format"""
        # FIPS codes should be 5 digits
        if not re.match(r'^\d{5}$', fips):
            raise ValueError(f"Invalid FIPS code: {fips}")
        return fips

    @staticmethod
    def validate_year_range(year_range: str) -> tuple[int, int]:
        """Validate year range format and values"""
        match = re.match(r'^(\d{4})-(\d{4})$', year_range)
        if not match:
            raise ValueError(f"Invalid year range format: {year_range}")

        start_year = int(match.group(1))
        end_year = int(match.group(2))

        if start_year >= end_year:
            raise ValueError(f"Start year must be before end year: {year_range}")

        if start_year < 1900 or end_year > 2200:
            raise ValueError(f"Year range out of bounds: {year_range}")

        return start_year, end_year


class RateLimiter:
    """Simple rate limiter for API calls"""

    def __init__(self, max_calls: int = 60, time_window: int = 60):
        """
        Initialize rate limiter
        Args:
            max_calls: Maximum number of calls allowed
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(self, identifier: str) -> tuple[bool, Optional[str]]:
        """
        Check if rate limit is exceeded
        Returns (is_allowed, error_message)
        """
        now = time.time()

        # Clean old entries
        self.calls[identifier] = [
            call_time for call_time in self.calls[identifier]
            if now - call_time < self.time_window
        ]

        # Check limit
        if len(self.calls[identifier]) >= self.max_calls:
            retry_after = self.time_window - (now - self.calls[identifier][0])
            return False, f"Rate limit exceeded. Retry after {retry_after:.0f} seconds"

        # Record this call
        self.calls[identifier].append(now)
        return True, None

    def rate_limit_decorator(self, get_identifier):
        """Decorator for rate limiting functions"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                identifier = get_identifier(*args, **kwargs)
                allowed, error = self.check_rate_limit(identifier)
                if not allowed:
                    raise Exception(f"Rate limit exceeded: {error}")
                return func(*args, **kwargs)
            return wrapper
        return decorator


class SecureConfig(BaseModel):
    """Secure configuration management with validation"""

    openai_api_key: Optional[str] = Field(None, min_length=20)
    landuse_model: str = Field("gpt-4o-mini", pattern="^(gpt-4|gpt-3.5)")
    temperature: float = Field(0.1, ge=0.0, le=1.0)
    max_tokens: int = Field(4000, ge=1, le=8000)
    database_path: str = Field("data/processed/landuse_analytics.duckdb")
    max_query_limit: int = Field(1000, ge=1, le=10000)
    enable_logging: bool = Field(True)
    log_level: str = Field("INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    @field_validator('openai_api_key')
    def validate_api_key(cls, v, info):
        """Validate API key format"""
        if v and not v.startswith('sk-'):
            logger.warning(f"Unusual {info.field_name} format detected")
        return v

    @field_validator('database_path')
    def validate_db_path(cls, v):
        """Validate database path exists"""
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Database not found at {v}")
        return v

    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "SecureConfig":
        """Load configuration from environment with validation"""
        import os

        from dotenv import load_dotenv

        if env_path:
            load_dotenv(env_path)

        config_dict = {
            'openai_api_key': os.getenv('OPENAI_API_KEY'),
            'landuse_model': os.getenv('LANDUSE_MODEL', 'gpt-4o-mini'),
            'temperature': float(os.getenv('TEMPERATURE', '0.1')),
            'max_tokens': int(os.getenv('MAX_TOKENS', '4000')),
            'database_path': os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'),
            'max_query_limit': int(os.getenv('DEFAULT_QUERY_LIMIT', '1000')),
            'enable_logging': os.getenv('ENABLE_LOGGING', 'true').lower() == 'true',
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }

        # Filter out None values to avoid type issues
        filtered_config = {k: v for k, v in config_dict.items() if v is not None}

        return cls(**filtered_config)


class SecurityLogger:
    """Centralized security logging"""

    def __init__(self, log_file: Optional[str] = None):
        self.logger = logging.getLogger('security')
        if log_file:
            handler = logging.FileHandler(log_file)
            handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(handler)

    def log_query(self, user_id: str, query: str, status: str, error: Optional[str] = None):
        """Log query attempts"""
        self.logger.info(f"Query attempt - User: {user_id}, Status: {status}, Error: {error}")
        if status == "blocked":
            self.logger.warning(f"Blocked query from {user_id}: {query[:100]}...")

    def log_access(self, user_id: str, resource: str, action: str, status: str):
        """Log resource access attempts"""
        self.logger.info(f"Access attempt - User: {user_id}, Resource: {resource}, Action: {action}, Status: {status}")

    def log_rate_limit(self, identifier: str, limit: int):
        """Log rate limit violations"""
        self.logger.warning(f"Rate limit exceeded - Identifier: {identifier}, Limit: {limit}")


def hash_api_key(api_key: str) -> str:
    """Hash API key for secure storage/comparison"""
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_session_token() -> str:
    """Generate secure session token"""
    return secrets.token_urlsafe(32)


def mask_api_key(api_key: str) -> str:
    """Mask API key for display (show first 4 and last 4 characters)"""
    if len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}...{api_key[-4:]}"


# =============================================================================
# SQL Value Sanitization Functions
# =============================================================================

class SQLSanitizer:
    """SQL value sanitization utilities for safe query construction.

    These functions help prevent SQL injection when building dynamic queries.
    Always prefer parameterized queries when possible, but use these functions
    when parameterized queries are not feasible (e.g., dynamic IN clauses).
    """

    # Allowlists for common domain values
    ALLOWED_LANDUSE_TYPES = frozenset(["Crop", "Pasture", "Forest", "Urban", "Rangeland"])
    ALLOWED_RCP_SCENARIOS = frozenset(["rcp45", "rcp85", "RCP4.5", "RCP8.5"])
    ALLOWED_SSP_SCENARIOS = frozenset(["ssp1", "ssp2", "ssp3", "ssp5", "SSP1", "SSP2", "SSP3", "SSP5"])
    ALLOWED_TRANSITION_TYPES = frozenset(["change", "same"])

    # Valid time periods in the dataset
    ALLOWED_TIME_PERIODS = frozenset([
        "2012-2020", "2020-2030", "2030-2040",
        "2040-2050", "2050-2060", "2060-2070"
    ])

    @classmethod
    def escape_string(cls, value: str) -> str:
        """
        Escape a string value for safe SQL inclusion.

        Escapes single quotes by doubling them, which is the SQL standard.
        Also removes null bytes and other dangerous characters.

        Args:
            value: The string value to escape

        Returns:
            Escaped string safe for SQL inclusion (without surrounding quotes)

        Example:
            >>> SQLSanitizer.escape_string("O'Brien")
            "O''Brien"
        """
        if not isinstance(value, str):
            raise TypeError(f"Expected string, got {type(value).__name__}")

        # Remove null bytes (can cause truncation)
        value = value.replace('\x00', '')

        # Escape single quotes by doubling them
        value = value.replace("'", "''")

        # Remove backslashes (can escape quotes in some databases)
        value = value.replace("\\", "")

        return value

    @classmethod
    def safe_string(cls, value: str) -> str:
        """
        Return a safely quoted string for SQL inclusion.

        Args:
            value: The string value to quote

        Returns:
            Quoted and escaped string ready for SQL

        Example:
            >>> SQLSanitizer.safe_string("O'Brien")
            "'O''Brien'"
        """
        return f"'{cls.escape_string(value)}'"

    @classmethod
    def safe_in_clause(cls, values: list[str], allowlist: frozenset[str] | None = None) -> str:
        """
        Build a safe IN clause from a list of values.

        Args:
            values: List of string values
            allowlist: Optional set of allowed values for validation

        Returns:
            SQL IN clause string like "('value1', 'value2')"

        Raises:
            ValueError: If any value is not in the allowlist (when provided)
            ValueError: If values list is empty

        Example:
            >>> SQLSanitizer.safe_in_clause(["Forest", "Urban"], SQLSanitizer.ALLOWED_LANDUSE_TYPES)
            "('Forest', 'Urban')"
        """
        if not values:
            raise ValueError("Values list cannot be empty")

        # Validate against allowlist if provided
        if allowlist is not None:
            invalid_values = set(values) - allowlist
            if invalid_values:
                raise ValueError(f"Invalid values: {invalid_values}. Allowed: {allowlist}")

        # Escape each value and build the clause
        escaped = [cls.safe_string(v) for v in values]
        return f"({', '.join(escaped)})"

    @classmethod
    def validate_landuse(cls, value: str) -> str:
        """Validate a land use type against the allowlist."""
        if value not in cls.ALLOWED_LANDUSE_TYPES:
            raise ValueError(f"Invalid land use type: {value}. Allowed: {cls.ALLOWED_LANDUSE_TYPES}")
        return value

    @classmethod
    def validate_state_code(cls, value: str) -> str:
        """
        Validate a state FIPS code (2 digits).

        Accepts both 2-digit state codes and 5-digit county FIPS codes.
        """
        # State codes should be 2 digits, county FIPS codes are 5 digits
        if re.match(r'^\d{2}$', value):
            return value
        if re.match(r'^\d{5}$', value):
            return value
        raise ValueError(f"Invalid state/FIPS code: {value}")

    @classmethod
    def validate_scenario_name(cls, value: str) -> str:
        """
        Validate a scenario name format.

        Expected format: MODEL_rcpXX_sspY (e.g., CNRM-CM5_rcp45_ssp1)
        """
        # Allow alphanumeric, underscores, and hyphens
        if not re.match(r'^[A-Za-z0-9_-]+$', value):
            raise ValueError(f"Invalid scenario name: {value}")
        return value

    @classmethod
    def validate_time_period(cls, value: str) -> str:
        """Validate a time period against the allowlist."""
        if value not in cls.ALLOWED_TIME_PERIODS:
            raise ValueError(f"Invalid time period: {value}. Allowed: {cls.ALLOWED_TIME_PERIODS}")
        return value

    @classmethod
    def safe_scenario_list(cls, scenarios: list[str]) -> str:
        """
        Build a safe IN clause for scenario names.

        Validates each scenario name format before including.
        """
        validated = [cls.validate_scenario_name(s) for s in scenarios]
        return cls.safe_in_clause(validated)

    @classmethod
    def safe_state_list(cls, state_codes: list[str]) -> str:
        """
        Build a safe IN clause for state codes.

        Validates each state code format before including.
        """
        validated = [cls.validate_state_code(s) for s in state_codes]
        return cls.safe_in_clause(validated)

    @classmethod
    def safe_landuse_list(cls, landuse_types: list[str]) -> str:
        """
        Build a safe IN clause for land use types.

        Validates against the allowlist.
        """
        return cls.safe_in_clause(landuse_types, cls.ALLOWED_LANDUSE_TYPES)

    @classmethod
    def safe_time_period_list(cls, periods: list[str]) -> str:
        """
        Build a safe IN clause for time periods.

        Validates against the allowlist.
        """
        return cls.safe_in_clause(periods, cls.ALLOWED_TIME_PERIODS)


# Example usage for testing
if __name__ == "__main__":
    # Test SQL validation
    test_queries = [
        "SELECT * FROM dim_scenario WHERE scenario_id = 1",
        "DROP TABLE dim_scenario",
        "SELECT * FROM dim_scenario; DELETE FROM dim_scenario",
        "SELECT * FROM dim_scenario WHERE name = 'test' OR '1'='1'"
    ]

    validator = SQLQueryValidator()
    for query in test_queries:
        is_valid, error = validator.validate_query(query)
        console.print(f"Query: {query[:50]}...")
        console.print(f"Valid: {is_valid}, Error: {error}\n")

    # Test rate limiter
    limiter = RateLimiter(max_calls=3, time_window=10)
    for i in range(5):
        allowed, error = limiter.check_rate_limit("test_user")
        console.print(f"Call {i+1}: Allowed: {allowed}, Error: {error}")
        time.sleep(1)
