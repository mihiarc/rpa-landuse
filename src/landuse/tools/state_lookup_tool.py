#!/usr/bin/env python3
"""
State lookup tool for the landuse agent.
Helps resolve state names, abbreviations, and FIPS codes intelligently.
"""

from typing import Any, Dict, Optional

from langchain.tools import tool

from landuse.utils.state_mappings import StateMapper


@tool
def lookup_state_info(state_reference: str) -> str:
    """
    Look up state information from a name, abbreviation, or FIPS code.
    Returns the appropriate SQL conditions for querying the database.

    Args:
        state_reference: State name (e.g., "California"), abbreviation (e.g., "CA"),
                        or FIPS code (e.g., "06")

    Returns:
        A string with SQL conditions or an error message
    """
    # Clean the input
    state_ref = state_reference.strip()

    # Check if it's a FIPS code (2 digits)
    if state_ref.isdigit() and len(state_ref) == 2:
        if StateMapper.is_valid_fips(state_ref):
            state_name = StateMapper.fips_to_name(state_ref)
            return f"state_code = '{state_ref}' -- {state_name}"
        else:
            return f"Error: '{state_ref}' is not a valid FIPS code"

    # Check if it's a state abbreviation (2 letters)
    if len(state_ref) == 2 and state_ref.isalpha():
        fips_code = StateMapper.abbrev_to_fips(state_ref)
        if fips_code:
            state_name = StateMapper.fips_to_name(fips_code)
            return f"state_code = '{fips_code}' -- {state_name} ({state_ref})"
        else:
            return f"Error: '{state_ref}' is not a valid state abbreviation"

    # Try as state name
    fips_code = StateMapper.name_to_fips(state_ref)
    if fips_code:
        abbrev = StateMapper.fips_to_abbrev(fips_code)
        return f"state_code = '{fips_code}' -- {state_ref} ({abbrev})"

    # If not found, return helpful error
    return (
        f"Error: Could not find state '{state_ref}'. "
        f"Try using the full state name (e.g., 'California'), "
        f"abbreviation (e.g., 'CA'), or FIPS code (e.g., '06')"
    )


@tool
def get_state_sql_condition(state_reference: str, use_state_name: bool = False) -> str:
    """
    Generate the appropriate SQL WHERE condition for a state query.

    Args:
        state_reference: State name, abbreviation, or FIPS code
        use_state_name: If True, use state_name field instead of state_code

    Returns:
        SQL WHERE condition string
    """
    # Clean the input
    state_ref = state_reference.strip()

    # For state names, we can use the state_name field directly
    if use_state_name and not (state_ref.isdigit() or (len(state_ref) == 2 and state_ref.isalpha())):
        return f"state_name = '{state_ref}'"

    # Otherwise, resolve to FIPS code
    fips_code = None

    # Check if it's already a FIPS code
    if state_ref.isdigit() and len(state_ref) == 2:
        if StateMapper.is_valid_fips(state_ref):
            fips_code = state_ref
    # Check if it's an abbreviation
    elif len(state_ref) == 2 and state_ref.isalpha():
        fips_code = StateMapper.abbrev_to_fips(state_ref)
    # Try as state name
    else:
        fips_code = StateMapper.name_to_fips(state_ref)

    if fips_code:
        return f"state_code = '{fips_code}'"
    else:
        # Fallback to state_name field
        return f"state_name = '{state_ref}'"


def create_state_lookup_tool():
    """Create the state lookup tool for the agent."""
    return lookup_state_info


def create_state_sql_tool():
    """Create the state SQL condition tool for the agent."""
    return get_state_sql_condition
