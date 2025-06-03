"""
Data service for loading and processing RPA land use data.
"""

import os
import json
import logging
from typing import Dict, Optional, List, Any
import pandas as pd
import streamlit as st
import duckdb

from ..config import (
    PROCESSED_DATA_DIR, 
    DATASET_FILES, 
    DATABASE_PATH,
    HUNDRED_ACRES_TO_ACRES,
    URBANIZATION_AREA_COLUMNS,
    SCENARIO_DESCRIPTIONS,
    KEY_SCENARIOS
)

logger = logging.getLogger(__name__)


class DataService:
    """Service class for data loading and processing operations."""
    
    @staticmethod
    @st.cache_data
    def load_parquet_data() -> Dict[str, pd.DataFrame]:
        """
        Load and process parquet datasets for the application.
        
        Returns:
            Dictionary of processed DataFrames
        """
        try:
            # Load datasets
            raw_data = {}
            for key, filename in DATASET_FILES.items():
                file_path = PROCESSED_DATA_DIR / filename
                if file_path.exists():
                    raw_data[key] = pd.read_parquet(file_path)
                else:
                    st.warning(f"File not found: {file_path}")
        except Exception as e:
            st.error(f"Error loading data: {e}")
            raise e
        
        # Convert hundred acres to acres for all datasets
        data = {}
        for key, df in raw_data.items():
            df_copy = df.copy()
            
            # Convert total_area column if it exists
            if "total_area" in df_copy.columns:
                df_copy["total_area"] = df_copy["total_area"] * HUNDRED_ACRES_TO_ACRES
                
            # Convert specific columns for urbanization trends dataset
            if key == "Urbanization Trends By Decade":
                for col in URBANIZATION_AREA_COLUMNS:
                    if col in df_copy.columns:
                        df_copy[col] = df_copy[col] * HUNDRED_ACRES_TO_ACRES
            
            data[key] = df_copy
        
        return data
    
    @staticmethod
    @st.cache_data
    def load_rpa_docs() -> List[Dict[str, Any]]:
        """
        Load RPA documentation if available.
        
        Returns:
            List of documentation chunks
        """
        try:
            docs_path = "docs/rpa_text/gtr_wo102_Chap4_chunks.json"
            with open(docs_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"RPA documentation not found at {docs_path}")
            return []
    
    @staticmethod
    def filter_key_scenarios(df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame to only include key RPA scenarios.
        
        Args:
            df: DataFrame with scenario_name column
            
        Returns:
            Filtered DataFrame
        """
        return df[df["scenario_name"].isin(KEY_SCENARIOS)]
    
    @staticmethod
    @st.cache_data
    def load_spatial_data(
        spatial_level: str, 
        scenario_filter: Optional[str] = None, 
        geographic_filter: Optional[str] = None, 
        filter_value: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load data from database views based on spatial level and filters.
        
        Args:
            spatial_level: County, State, Region, Subregion, or National
            scenario_filter: Optional scenario name filter
            geographic_filter: Optional geographic filter type (state, region, subregion)
            filter_value: Optional filter value
            
        Returns:
            Filtered DataFrame
        """
        try:
            conn = duckdb.connect(str(DATABASE_PATH))
            
            # Map spatial levels to view names
            view_mapping = {
                "County": '"County-Level Land Use Transitions"',
                "State": '"State-Level Land Use Transitions"',
                "Region": '"Region-Level Land Use Transitions"',
                "Subregion": '"Subregion-Level Land Use Transitions"', 
                "National": '"National-Level Land Use Transitions"'
            }
            
            view_name = view_mapping.get(spatial_level)
            if not view_name:
                raise ValueError(f"Unknown spatial level: {spatial_level}")
            
            # Build the query with optional filtering
            query = f'SELECT * FROM {view_name}'
            
            # Add filters
            conditions = []
            
            # Add scenario filter if specified
            if scenario_filter and scenario_filter != "Overall Mean":
                # Map display name back to database scenario name
                scenario_reverse_mapping = {v: k for k, v in SCENARIO_DESCRIPTIONS.items()}
                scenario_reverse_mapping['Ensemble Projection (Average of All Scenarios)'] = 'ensemble_overall'
                scenario_key = scenario_reverse_mapping.get(scenario_filter, scenario_filter)
                conditions.append(f"scenario_name = '{scenario_key}'")
            
            # Add geographic filter if specified
            if geographic_filter and filter_value and filter_value != "All":
                if geographic_filter == "state":
                    conditions.append(f"state_name = '{filter_value}'")
                elif geographic_filter == "region":
                    conditions.append(f"region = '{filter_value}'")
                elif geographic_filter == "subregion":
                    conditions.append(f"subregion = '{filter_value}'")
            
            # Add WHERE clause if we have conditions
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            df = conn.execute(query).df()
            conn.close()
            return df
            
        except Exception as e:
            st.error(f"Error loading {spatial_level} data: {e}")
            return pd.DataFrame()
    
    @staticmethod
    @st.cache_data
    def get_geographic_options() -> Dict[str, List[str]]:
        """
        Get available states, regions, and subregions for filtering.
        
        Returns:
            Dictionary with geographic options
        """
        try:
            conn = duckdb.connect(str(DATABASE_PATH))
            
            # Get unique values for filtering
            states = conn.execute(
                'SELECT DISTINCT state_name FROM "County-Level Land Use Transitions" ORDER BY state_name'
            ).fetchall()
            regions = conn.execute(
                'SELECT DISTINCT region FROM "County-Level Land Use Transitions" WHERE region IS NOT NULL ORDER BY region'
            ).fetchall()
            subregions = conn.execute(
                'SELECT DISTINCT subregion FROM "County-Level Land Use Transitions" WHERE subregion IS NOT NULL ORDER BY subregion'
            ).fetchall()
            
            conn.close()
            
            return {
                'states': [row[0] for row in states],
                'regions': [row[0] for row in regions],
                'subregions': [row[0] for row in subregions]
            }
        except Exception as e:
            st.error(f"Error loading geographic options: {e}")
            return {'states': [], 'regions': [], 'subregions': []}
    
    @staticmethod
    def aggregate_to_state_level(
        county_df: pd.DataFrame, 
        transition_type: str, 
        scenario: str, 
        decade: str
    ) -> pd.DataFrame:
        """
        Aggregate county-level data to state level for mapping.
        
        Args:
            county_df: The county-level transitions dataframe
            transition_type: 'to_urban', 'from_forest', or 'all'
            scenario: The scenario name to filter by
            decade: The decade name to filter by
        
        Returns:
            DataFrame aggregated at state level
        """
        # Filter by scenario and decade
        filtered_df = county_df[
            (county_df["scenario_name"] == scenario) & 
            (county_df["decade_name"] == decade)
        ].copy()
        
        # Apply transition type filter
        if transition_type == 'to_urban':
            filtered_df = filtered_df[filtered_df["to_category"] == "Urban"]
        elif transition_type == 'from_forest':
            filtered_df = filtered_df[filtered_df["from_category"] == "Forest"]
        
        # Aggregate to state level
        state_df = filtered_df.groupby("state_name")["total_area"].sum().reset_index()
        
        # Rename columns for clarity
        state_df.columns = ["name", "total_area"]
        
        return state_df 