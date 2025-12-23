"""Shared utilities for the Analytics Dashboard.

Helper functions for data processing, formatting, and color calculations.
"""

from typing import Optional

import pandas as pd
import streamlit as st

from .constants import TOP_STATES_DISPLAY


def calculate_symmetric_color_range(
    df: pd.DataFrame,
    column: str,
    max_cap: float = 100.0,
    quantile_low: float = 0.05,
    quantile_high: float = 0.95,
) -> tuple[float, float]:
    """Calculate a symmetric color range centered at zero.

    Uses quantiles to handle outliers and caps at max_cap.

    Args:
        df: DataFrame containing the data
        column: Column name to calculate range from
        max_cap: Maximum absolute value to allow
        quantile_low: Lower quantile for outlier handling
        quantile_high: Upper quantile for outlier handling

    Returns:
        Tuple of (min, max) for color range
    """
    if column not in df.columns or df.empty:
        return (-max_cap, max_cap)

    lower_bound = df[column].quantile(quantile_low)
    upper_bound = df[column].quantile(quantile_high)
    max_abs = max(abs(lower_bound), abs(upper_bound))
    max_abs = min(max_abs, max_cap)

    return (-max_abs, max_abs)


def format_acres(value: float) -> str:
    """Format acre values for display.

    Args:
        value: Acre value to format

    Returns:
        Formatted string with appropriate suffix (K, M)
    """
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.0f}K"
    else:
        return f"{value:.0f}"


def format_percent(value: float) -> str:
    """Format percentage values for display.

    Args:
        value: Percentage value

    Returns:
        Formatted percentage string
    """
    return f"{value:+.1f}%" if value != 0 else "0.0%"


def create_state_rankings_table(
    df: pd.DataFrame,
    value_column: str,
    state_column: str = "state_name",
    top_n: int = TOP_STATES_DISPLAY,
    ascending: bool = False,
    format_func: Optional[callable] = None,
) -> pd.DataFrame:
    """Create a formatted state rankings table.

    Args:
        df: DataFrame with state data
        value_column: Column to rank by
        state_column: Column containing state names
        top_n: Number of top states to show
        ascending: If True, show lowest values first
        format_func: Optional function to format values

    Returns:
        Formatted DataFrame for display
    """
    if df is None or df.empty:
        return pd.DataFrame()

    if ascending:
        ranked = df.nsmallest(top_n, value_column)
    else:
        ranked = df.nlargest(top_n, value_column)

    result = ranked[[state_column, value_column]].copy()
    result.columns = ["State", "Value"]

    if format_func:
        result["Value"] = result["Value"].apply(format_func)

    result.index = range(1, len(result) + 1)
    return result


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero.

    Args:
        numerator: The numerator
        denominator: The denominator
        default: Value to return if division by zero

    Returns:
        Result of division or default
    """
    if denominator == 0:
        return default
    return numerator / denominator


def calculate_net_change(loss: float, gain: float) -> float:
    """Calculate net change from loss and gain values.

    Args:
        loss: Loss value (should be positive)
        gain: Gain value (should be positive)

    Returns:
        Net change (gain - loss)
    """
    return gain - abs(loss)


def aggregate_by_category(
    df: pd.DataFrame,
    category_column: str,
    value_column: str,
    sort_descending: bool = True,
) -> pd.Series:
    """Aggregate values by category and optionally sort.

    Args:
        df: DataFrame with data
        category_column: Column to group by
        value_column: Column to sum
        sort_descending: Whether to sort descending

    Returns:
        Series with aggregated values
    """
    result = df.groupby(category_column)[value_column].sum()
    if sort_descending:
        result = result.sort_values(ascending=False)
    return result


def display_metric_row(
    col1,
    col2,
    col3,
    loss_value: float,
    gain_value: float,
    net_value: float,
    loss_label: str = "Total Loss",
    gain_label: str = "Total Gain",
    net_label: str = "Net Change",
):
    """Display a row of metrics in three columns.

    Args:
        col1, col2, col3: Streamlit columns
        loss_value: Loss value to display
        gain_value: Gain value to display
        net_value: Net change value
        loss_label: Label for loss metric
        gain_label: Label for gain metric
        net_label: Label for net change metric
    """
    with col1:
        st.metric(
            loss_label,
            format_acres(abs(loss_value)) + " acres",
            delta=None,
        )
    with col2:
        st.metric(
            gain_label,
            format_acres(gain_value) + " acres",
            delta=None,
        )
    with col3:
        delta_color = "normal" if net_value >= 0 else "inverse"
        st.metric(
            net_label,
            format_acres(abs(net_value)) + " acres",
            delta=format_percent(safe_divide(net_value, abs(loss_value)) * 100) if loss_value != 0 else "N/A",
            delta_color=delta_color,
        )
