"""Result formatting utilities for API output.

This module provides formatting functions for presenting numeric data
in a human-readable format suitable for LLM consumption.
"""


def format_acres(acres: float) -> str:
    """Format acres with thousands separators.

    Args:
        acres: Number of acres to format

    Returns:
        Formatted string with commas as thousands separators

    Examples:
        >>> format_acres(1234567.89)
        '1,234,568'
        >>> format_acres(500.0)
        '500'
    """
    return f"{int(round(acres)):,}"


def format_percent(value: float) -> str:
    """Format percentage value.

    Args:
        value: Percentage value to format

    Returns:
        Formatted string with percent sign

    Examples:
        >>> format_percent(15.5)
        '15.5%'
        >>> format_percent(100.0)
        '100.0%'
    """
    return f"{value:.1f}%"


def format_change(change: float, units: str = "acres") -> str:
    """Format a change value with direction indicator.

    Args:
        change: Change value (positive or negative)
        units: Unit label to append

    Returns:
        Formatted string with + or - prefix

    Examples:
        >>> format_change(5000, "acres")
        '+5,000 acres'
        >>> format_change(-3000, "acres")
        '-3,000 acres'
    """
    sign = "+" if change >= 0 else ""
    return f"{sign}{int(round(change)):,} {units}"


def format_state_abbrev(state_name: str) -> str:
    """Get state abbreviation from full name.

    Args:
        state_name: Full state name

    Returns:
        Two-letter state abbreviation or original name if not found
    """
    from landuse.utils.state_mappings import StateMapper
    abbrev = StateMapper.name_to_abbrev(state_name)
    return abbrev if abbrev else state_name[:2].upper()
