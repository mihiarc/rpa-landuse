"""
PandasAI integration for the RPA Land Use Viewer.

This module provides functionality for creating and querying semantic layers
using PandasAI to enable natural language queries on land use data.
"""

from rpa_landuse.pandasai.layers import (
    create_semantic_layers,
    extract_data_from_duckdb
)

from rpa_landuse.pandasai.query import (
    query_transitions,
    query_county_transitions,
    query_urbanization_trends
)

__all__ = [
    'create_semantic_layers',
    'extract_data_from_duckdb',
    'query_transitions',
    'query_county_transitions',
    'query_urbanization_trends'
] 