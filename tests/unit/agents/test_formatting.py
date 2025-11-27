#!/usr/bin/env python3
"""
Tests for the formatting module
"""

from io import StringIO

import pandas as pd
import pytest
from rich.panel import Panel

from landuse.agents.formatting import (
    clean_sql_query,
    create_examples_panel,
    create_welcome_panel,
    format_error,
    format_query_results,
    format_response,
    format_row_values,
    get_summary_statistics,
)


class TestCleanSQLQuery:
    """Test SQL query cleaning function"""

    def test_remove_quotes(self):
        """Test removing surrounding quotes"""
        assert clean_sql_query('"SELECT * FROM table"') == "SELECT * FROM table"
        assert clean_sql_query("'SELECT * FROM table'") == "SELECT * FROM table"
        assert clean_sql_query('""SELECT * FROM table""') == "SELECT * FROM table"

    def test_remove_markdown(self):
        """Test removing markdown formatting"""
        assert clean_sql_query('```sql\nSELECT * FROM table\n```') == "SELECT * FROM table"
        assert clean_sql_query('```SELECT * FROM table```') == "SELECT * FROM table"
        assert clean_sql_query('```sql SELECT * FROM table```') == "SELECT * FROM table"

    def test_combined_cleaning(self):
        """Test combined quote and markdown removal"""
        query = '"""```sql\nSELECT * FROM table\n```"""'
        assert clean_sql_query(query) == "SELECT * FROM table"

    def test_no_changes_needed(self):
        """Test query that doesn't need cleaning"""
        query = "SELECT * FROM table WHERE id = 1"
        assert clean_sql_query(query) == query


class TestFormatQueryResults:
    """Test query result formatting"""

    def test_empty_dataframe(self):
        """Test formatting empty results"""
        df = pd.DataFrame()
        result = format_query_results(df, "SELECT * FROM test")
        assert "✅ Query executed successfully but returned no results" in result
        assert "SELECT * FROM test" in result

    def test_simple_dataframe(self):
        """Test formatting simple results"""
        df = pd.DataFrame({
            'id': [1, 2, 3],
            'name': ['A', 'B', 'C'],
            'acres': [100.5, 200.7, 300.9]
        })
        result = format_query_results(df, "SELECT * FROM test", max_display_rows=5)

        # Check for table formatting
        assert "```" in result
        assert "Id" in result  # Column headers are title-cased
        assert "Name" in result
        assert "Acres" in result

        # Check acres are rounded
        assert "101" in result or "100" in result
        assert "201" in result or "200" in result
        assert "301" in result or "300" in result

    def test_state_code_conversion(self):
        """Test state code to name conversion"""
        df = pd.DataFrame({
            'state_code': ['06', '48', '36'],
            'value': [100, 200, 300]
        })
        result = format_query_results(df, "SELECT * FROM test")

        # Check state names appear
        assert "California" in result
        assert "Texas" in result
        assert "New York" in result
        assert "state_code" not in result  # Original column should be removed

    def test_large_dataframe_truncation(self):
        """Test truncation of large results"""
        df = pd.DataFrame({
            'id': range(100),
            'value': range(100)
        })
        result = format_query_results(df, "SELECT * FROM test", max_display_rows=10)

        assert "Showing first 10 of 100 total records" in result

    def test_summary_statistics(self):
        """Test inclusion of summary statistics"""
        df = pd.DataFrame({
            'acres': [100, 200, 300, 400, 500],
            'count': [10, 20, 30, 40, 50]
        })
        result = format_query_results(df, "SELECT * FROM test", include_summary=True)

        assert "Summary Statistics" in result
        assert "mean" in result.lower()
        assert "std" in result.lower()


class TestFormatRowValues:
    """Test individual row value formatting"""

    def test_format_numeric_values(self):
        """Test formatting of numeric values - all rounded to integers"""
        row = pd.Series({'id': 1000, 'acres': 12345.67, 'ratio': 0.123})
        formatted = format_row_values(row, ['id', 'acres', 'ratio'])

        assert formatted[0] == "1,000"
        assert formatted[1] == "12,346"  # Rounded acres
        # Note: formatting logic rounds all numeric values to integers
        assert formatted[2] == "0"  # 0.123 rounds to 0

    def test_format_na_values(self):
        """Test formatting of NA values"""
        import numpy as np
        row = pd.Series({'id': 1, 'value': np.nan, 'name': None})
        formatted = format_row_values(row, ['id', 'value', 'name'])

        assert formatted[0] == "1"
        assert formatted[1] == "N/A"
        assert formatted[2] == "N/A"  # pd.isna() treats None as NA

    def test_format_string_values(self):
        """Test formatting of string values"""
        row = pd.Series({'name': 'Test Name', 'code': 'ABC123'})
        formatted = format_row_values(row, ['name', 'code'])

        assert formatted[0] == "Test Name"
        assert formatted[1] == "ABC123"


class TestSummaryStatistics:
    """Test summary statistics generation"""

    def test_numeric_summary(self):
        """Test summary for numeric columns"""
        df = pd.DataFrame({
            'acres': [100, 200, 300],
            'count': [10, 20, 30],
            'name': ['A', 'B', 'C']
        })
        summary = get_summary_statistics(df)

        assert summary is not None
        assert "Summary Statistics" in summary
        assert "acres" in summary
        assert "count" in summary
        assert "name" not in summary  # Non-numeric column

    def test_no_numeric_columns(self):
        """Test summary for non-numeric dataframe"""
        df = pd.DataFrame({
            'name': ['A', 'B', 'C'],
            'code': ['X', 'Y', 'Z']
        })
        summary = get_summary_statistics(df)

        assert summary is None

    def test_single_row(self):
        """Test summary for single row (no statistics)"""
        df = pd.DataFrame({'value': [100]})
        summary = get_summary_statistics(df)

        assert summary is None


class TestUIComponents:
    """Test UI component creation"""

    def test_create_welcome_panel(self):
        """Test welcome panel creation"""
        panel = create_welcome_panel(
            "test.db",
            "gpt-4",
            "sk-...xyz"
        )

        assert isinstance(panel, Panel)
        assert panel.renderable is not None

    def test_create_examples_panel(self):
        """Test examples panel creation"""
        panel = create_examples_panel()

        assert isinstance(panel, Panel)
        assert "Example questions" in str(panel.renderable)

    def test_format_error(self):
        """Test error formatting"""
        error = ValueError("Test error message")
        panel = format_error(error)

        assert isinstance(panel, Panel)
        assert "Test error message" in str(panel.renderable)

    def test_format_response(self):
        """Test response formatting"""
        response = "# Test Response\n\nThis is a **test**"
        panel = format_response(response)

        assert isinstance(panel, Panel)
        assert panel.title == "📊 Analysis Results"

        # Test custom title
        panel2 = format_response(response, title="Custom Title")
        assert panel2.title == "Custom Title"
