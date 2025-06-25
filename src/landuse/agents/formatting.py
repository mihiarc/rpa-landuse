#!/usr/bin/env python3
"""
Output formatting utilities for landuse agents
Provides consistent formatting for query results and terminal display
"""

from io import StringIO
from typing import Optional, Union

import pandas as pd
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .constants import STATE_NAMES


def clean_sql_query(sql_query: str) -> str:
    """
    Clean up SQL query string by removing quotes and markdown formatting

    Args:
        sql_query: Raw SQL query string

    Returns:
        Cleaned SQL query
    """
    sql_query = sql_query.strip()

    # Keep removing quotes and markdown until we can't anymore
    previous = None
    while previous != sql_query:
        previous = sql_query

        # Remove markdown formatting
        if sql_query.startswith('```sql'):
            sql_query = sql_query[6:].strip()
        elif sql_query.startswith('```'):
            sql_query = sql_query[3:].strip()
        if sql_query.endswith('```'):
            sql_query = sql_query[:-3].strip()

        # Remove wrapping quotes
        if len(sql_query) >= 2:
            if ((sql_query.startswith('"') and sql_query.endswith('"')) or
                (sql_query.startswith("'") and sql_query.endswith("'"))):
                sql_query = sql_query[1:-1].strip()

    return sql_query


def format_query_results(
    df: pd.DataFrame,
    sql_query: str,
    max_display_rows: int = 50,
    include_summary: bool = True
) -> str:
    """
    Format query results in a professional, user-friendly way

    Args:
        df: Results dataframe
        sql_query: The SQL query that was executed
        max_display_rows: Maximum rows to display
        include_summary: Whether to include summary statistics

    Returns:
        Formatted results string
    """
    if df.empty:
        return f"✅ Query executed successfully but returned no results.\nSQL: {sql_query}"

    # Create a copy to avoid modifying the original
    df_display = df.copy()

    # Convert state codes to names if present
    if 'state_code' in df_display.columns:
        df_display['state'] = df_display['state_code'].apply(
            lambda x: STATE_NAMES.get(str(x).zfill(2), f"Unknown ({x})")
        )
        # Reorder columns to put state name first, drop state_code
        cols = df_display.columns.tolist()
        cols.remove('state_code')
        cols.remove('state')
        df_display = df_display[['state'] + cols]

    # Create a string buffer to capture Rich output
    string_io = StringIO()
    console = Console(file=string_io, force_terminal=True)

    # Create a Rich table
    table = Table(show_header=True, header_style="bold cyan", title=None)

    # Add columns
    for col in df_display.columns:
        col_display = col.replace('_', ' ').title()
        table.add_column(col_display, style="white", overflow="fold")

    # Add rows (limited for readability)
    display_rows = min(len(df_display), max_display_rows)
    for _idx, row in df_display.head(display_rows).iterrows():
        formatted_row = format_row_values(row, df_display.columns)
        table.add_row(*formatted_row)

    # Render the table
    console.print(table)
    result = "```\n" + string_io.getvalue() + "```\n"

    if len(df) > display_rows:
        result += f"\n*Showing first {display_rows} of {len(df):,} total records*\n"

    # Add summary statistics if requested
    if include_summary:
        summary = get_summary_statistics(df)
        if summary:
            result += f"\n{summary}\n"

    return result


def format_row_values(row: pd.Series, columns: list) -> list:
    """
    Format individual row values for display

    Args:
        row: Pandas series with row data
        columns: List of column names

    Returns:
        List of formatted values
    """
    formatted_row = []

    for col in columns:
        val = row[col]
        if isinstance(val, (int, float)):
            if pd.isna(val):
                formatted_row.append("N/A")
            elif col.lower().endswith('acres') or 'acre' in col.lower():
                # Round acres to whole numbers
                formatted_row.append(f"{int(round(val)):,}")
            elif isinstance(val, float):
                # For other floats, use 2 decimal places if needed
                if val == int(val):
                    formatted_row.append(f"{int(val):,}")
                else:
                    formatted_row.append(f"{val:,.2f}")
            else:
                formatted_row.append(f"{val:,}")
        else:
            formatted_row.append(str(val))

    return formatted_row


def get_summary_statistics(df: pd.DataFrame) -> Optional[str]:
    """
    Generate summary statistics for numeric columns

    Args:
        df: Results dataframe

    Returns:
        Formatted summary statistics or None
    """
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0 and len(df) > 1:
        summary = "📊 **Summary Statistics:**\n```\n"
        summary_df = df[numeric_cols].describe()
        summary += summary_df.to_string()
        summary += "\n```"
        return summary
    return None


def create_welcome_panel(db_path: str, model_name: str, api_key_masked: str) -> Panel:
    """
    Create welcome panel for chat interface

    Args:
        db_path: Path to database
        model_name: Model being used
        api_key_masked: Masked API key for display

    Returns:
        Rich Panel object
    """
    # Read ASCII logo if available
    logo_content = ""
    try:
        from pathlib import Path
        logo_path = Path(__file__).parent.parent.parent.parent / "assets" / "branding" / "ascii_logo_simple.txt"
        if logo_path.exists():
            logo_content = logo_path.read_text() + "\n\n"
    except Exception:
        pass  # nosec B110 - Optional logo, safe to skip

    content = (
        f"{logo_content}"
        "🌲 [bold green]RPA Land Use Analytics[/bold green]\n"
        "[yellow]AI-powered analysis of USDA Forest Service RPA Assessment data[/yellow]\n\n"
        f"[dim]Database: {db_path}[/dim]\n"
        f"[dim]Model: {model_name} | API Key: {api_key_masked}[/dim]"
    )
    return Panel.fit(content, border_style="green")


def create_examples_panel() -> Panel:
    """
    Create examples panel for chat interface

    Returns:
        Rich Panel with example queries
    """
    content = """[bold cyan]🚀 Example questions about the 2020 RPA Assessment:[/bold cyan]

• "How much agricultural land is projected to be lost by 2070?"
• "Which states have the most urban expansion under RCP8.5?"
• "Compare forest loss between RCP4.5 and RCP8.5 scenarios"
• "Show me crop to urban transitions in the South region"
• "What are the land use projections for California?"

[dim]Commands: 'exit' to quit | 'help' for examples | 'schema' for database info[/dim]"""

    return Panel(
        content,
        title="💡 Try these queries",
        border_style="blue"
    )


def format_error(error: Exception) -> Panel:
    """
    Format error message for display

    Args:
        error: Exception to format

    Returns:
        Rich Panel with error message
    """
    return Panel(
        f"❌ Error: {str(error)}",
        border_style="red"
    )


def format_response(response: str, title: str = "📊 Analysis Results") -> Panel:
    """
    Format agent response as markdown in a panel

    Args:
        response: Response text (markdown)
        title: Panel title

    Returns:
        Rich Panel with formatted response
    """
    response_md = Markdown(response)
    return Panel(
        response_md,
        title=title,
        border_style="green",
        padding=(1, 2)
    )
