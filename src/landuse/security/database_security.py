"""Database security utilities for SQL injection prevention and access control."""

from typing import FrozenSet, List, Set

from pydantic import BaseModel, Field


class DatabaseSecurity:
    """
    Centralized database security validation following security best practices.

    Implements allowlist-based validation to prevent SQL injection attacks
    and unauthorized access to database objects.
    """

    # Allowlist of approved table names
    ALLOWED_TABLES: FrozenSet[str] = frozenset(
        [
            # Fact tables
            "fact_landuse_transitions",
            "fact_socioeconomic_projections",
            # Dimension tables
            "dim_scenario",
            "dim_geography",
            "dim_landuse",
            "dim_time",
            "dim_indicators",
            "dim_socioeconomic",
            # Views for analysis
            "v_income_trends",
            "v_population_trends",
            "v_landuse_socioeconomic",
            "v_full_projection_period",
            "v_scenarios_combined",
            # Allow common information schema tables for metadata queries
            "information_schema.tables",
            "information_schema.columns",
            "information_schema.schemata",
        ]
    )

    # Allowlist of approved column prefixes for dynamic queries
    ALLOWED_COLUMN_PREFIXES: FrozenSet[str] = frozenset(
        [
            "fact_",
            "dim_",
            "id",
            "name",
            "code",
            "year",
            "from_",
            "to_",
            "area_",
            "change_",
            "scenario_",
            "geography_",
            "landuse_",
            "table_",
            "column_",
            "data_",
            "is_",
            # Socioeconomic data fields
            "indicator_",
            "socioeconomic_",
            "projection_",
            "population_",
            "income_",
            "economic_",
            "value",
            "trend",
            "growth_",
            "urbanization_",
            "narrative_",
            "unit_",
            "measure",
        ]
    )

    # Disallowed SQL keywords and patterns
    # Note: Comment syntax (--,/*,*/) removed as comments are stripped before validation
    DANGEROUS_KEYWORDS: FrozenSet[str] = frozenset(
        [
            "DROP",
            "DELETE",
            "UPDATE",
            "INSERT",
            "ALTER",
            "CREATE",
            "TRUNCATE",
            "REPLACE",
            "MERGE",
            "UPSERT",
            "COPY",
            "GRANT",
            "REVOKE",
            "COMMIT",
            "ROLLBACK",
            "EXEC",
            "EXECUTE",
            "CALL",
            "EVAL",
            ";--",
            "xp_",
            "sp_",
        ]
    )

    @classmethod
    def validate_table_name(cls, table_name: str) -> str:
        """
        Validate table name against allowlist.

        Args:
            table_name: Table name to validate

        Returns:
            Validated table name

        Raises:
            ValueError: If table name is not in allowlist
        """
        if not table_name:
            raise ValueError("Table name cannot be empty")

        # Normalize case for comparison
        normalized_name = table_name.lower().strip()

        # Check against allowlist
        if normalized_name not in cls.ALLOWED_TABLES:
            raise ValueError(
                f"Table '{table_name}' is not allowed. Allowed tables: {', '.join(sorted(cls.ALLOWED_TABLES))}"
            )

        return table_name

    @classmethod
    def validate_column_name(cls, column_name: str) -> str:
        """
        Validate column name using prefix allowlist.

        Args:
            column_name: Column name to validate

        Returns:
            Validated column name

        Raises:
            ValueError: If column name doesn't match allowed patterns
        """
        if not column_name:
            raise ValueError("Column name cannot be empty")

        # Basic alphanumeric and underscore check
        if not column_name.replace("_", "").replace(".", "").isalnum():
            raise ValueError(f"Column name '{column_name}' contains invalid characters")

        # Check against allowed prefixes
        normalized_name = column_name.lower()
        allowed = any(normalized_name.startswith(prefix) for prefix in cls.ALLOWED_COLUMN_PREFIXES)

        if not allowed:
            raise ValueError(
                f"Column '{column_name}' doesn't match allowed patterns. "
                f"Allowed prefixes: {', '.join(sorted(cls.ALLOWED_COLUMN_PREFIXES))}"
            )

        return column_name

    @classmethod
    def remove_sql_comments(cls, query: str) -> str:
        """
        Remove SQL comments from query for security validation.

        Args:
            query: SQL query with potential comments

        Returns:
            Query with comments removed
        """
        import re

        # Remove -- style comments (to end of line)
        query = re.sub(r"--[^\n]*", "", query)

        # Remove /* */ style comments
        query = re.sub(r"/\*.*?\*/", "", query, flags=re.DOTALL)

        return query

    @classmethod
    def scan_query_for_dangerous_content(cls, query: str) -> List[str]:
        """
        Scan SQL query for dangerous keywords and patterns.

        Args:
            query: SQL query to scan

        Returns:
            List of dangerous patterns found
        """
        # Remove comments before checking for dangerous patterns
        query_without_comments = cls.remove_sql_comments(query)
        dangerous_patterns = []
        query_upper = query_without_comments.upper()

        # Check for dangerous keywords
        for keyword in cls.DANGEROUS_KEYWORDS:
            if keyword in query_upper:
                dangerous_patterns.append(keyword)

        return dangerous_patterns

    @classmethod
    def validate_query_safety(cls, query: str) -> None:
        """
        Validate that a query is safe for execution.

        Args:
            query: SQL query to validate

        Raises:
            ValueError: If query contains dangerous content
        """
        dangerous_patterns = cls.scan_query_for_dangerous_content(query)

        if dangerous_patterns:
            raise ValueError(
                f"Query contains dangerous keywords: {', '.join(dangerous_patterns)}. Only SELECT queries are allowed."
            )

    @classmethod
    def is_read_only_query(cls, query: str) -> bool:
        """
        Check if query is read-only (SELECT, WITH, etc.).

        Args:
            query: SQL query to check

        Returns:
            True if query is read-only
        """
        query_trimmed = query.strip().upper()
        read_only_starters = ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")

        return query_trimmed.startswith(read_only_starters)

    @classmethod
    def add_allowed_table(cls, table_name: str) -> None:
        """
        Add a table to the allowlist (for testing or dynamic scenarios).

        Args:
            table_name: Table name to add

        Note:
            This modifies the class-level allowlist and should be used carefully
        """
        # Convert frozenset to set, add item, convert back
        new_tables = set(cls.ALLOWED_TABLES)
        new_tables.add(table_name.lower())
        cls.ALLOWED_TABLES = frozenset(new_tables)


class QueryValidationResult(BaseModel):
    """Result of query validation with detailed information."""

    is_valid: bool = Field(description="Whether the query passed validation")
    is_read_only: bool = Field(description="Whether the query is read-only")
    dangerous_patterns: List[str] = Field(default_factory=list, description="List of dangerous patterns found")
    table_names: List[str] = Field(default_factory=list, description="Table names found in query")
    validation_errors: List[str] = Field(default_factory=list, description="Validation error messages")


class QueryValidator:
    """
    High-level query validator that combines all security checks.
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize query validator.

        Args:
            strict_mode: If True, only explicitly allowed tables are permitted
        """
        self.strict_mode = strict_mode
        self.security = DatabaseSecurity()

    def validate_query(self, query: str) -> QueryValidationResult:
        """
        Perform comprehensive query validation.

        Args:
            query: SQL query to validate

        Returns:
            QueryValidationResult with validation details
        """
        result = QueryValidationResult()
        errors = []

        try:
            # Check if query is read-only
            result.is_read_only = self.security.is_read_only_query(query)

            # Scan for dangerous patterns
            result.dangerous_patterns = self.security.scan_query_for_dangerous_content(query)

            # Validate query safety
            if result.dangerous_patterns:
                errors.append(f"Dangerous keywords found: {', '.join(result.dangerous_patterns)}")

            # Extract and validate table names (basic implementation)
            # Note: A full implementation would use SQL parsing
            table_names = self._extract_table_names(query)
            result.table_names = table_names

            if self.strict_mode:
                for table_name in table_names:
                    try:
                        self.security.validate_table_name(table_name)
                    except ValueError as e:
                        errors.append(str(e))

            result.validation_errors = errors
            result.is_valid = len(errors) == 0

        except Exception as e:
            result.validation_errors = [f"Validation error: {str(e)}"]
            result.is_valid = False

        return result

    def _extract_table_names(self, query: str) -> List[str]:
        """
        Basic table name extraction from SQL query.

        Args:
            query: SQL query

        Returns:
            List of potential table names

        Note:
            This is a simplified implementation. A production system
            would use a proper SQL parser.
        """
        import re

        # Look for patterns like "FROM table_name" or "JOIN table_name"
        patterns = [
            r"\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            r"\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            r"\bINTO\s+([a-zA-Z_][a-zA-Z0-9_]*)",
            r"\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)",
        ]

        table_names = []
        query_upper = query.upper()

        for pattern in patterns:
            matches = re.findall(pattern, query_upper, re.IGNORECASE)
            table_names.extend(matches)

        # Remove duplicates while preserving order
        seen = set()
        unique_tables = []
        for table in table_names:
            if table.lower() not in seen:
                seen.add(table.lower())
                unique_tables.append(table.lower())

        return unique_tables
