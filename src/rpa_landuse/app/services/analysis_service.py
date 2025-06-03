"""
Analysis service for advanced data analysis operations.

This service provides advanced data analysis operations for the RPA Land Use Viewer application.

It includes methods for loading and processing enhanced urbanization and forest loss data.

The data is loaded from the RPA Land Use change database using DuckDB.

The data is processed to provide enhanced metrics and visualizations.
"""

import logging
from typing import Optional, Dict, List, Any
import pandas as pd
import numpy as np
import streamlit as st
import duckdb

from ..config import DATABASE_PATH, SCENARIO_DESCRIPTIONS

logger = logging.getLogger(__name__)


class AnalysisService:
    """Service class for advanced data analysis operations."""
    
    @staticmethod
    @st.cache_data
    def load_enhanced_urbanization_data(
        spatial_level: str, 
        scenario_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load enhanced urbanization data with baseline rates and proper calculations.
        
        Args:
            spatial_level: County, State, Subregion, Region, or National
            scenario_filter: Optional scenario name filter
            
        Returns:
            Enhanced DataFrame with baseline metrics
        """
        # Create reverse mapping for database queries
        scenario_reverse_mapping = {v: k for k, v in SCENARIO_DESCRIPTIONS.items()}
        scenario_reverse_mapping['Ensemble Projection (Average of All Scenarios)'] = 'ensemble_overall'
        
        try:
            conn = duckdb.connect(str(DATABASE_PATH))
            
            if spatial_level == "County":
                # Enhanced county query with baseline urban area and proper rate calculations
                query = '''
                WITH baseline_urban AS (
                    SELECT 
                        fips_code,
                        county_name,
                        state_name,
                        scenario_name,
                        baseline_acres_2020 as baseline_urban_acres_2020
                    FROM baseline_county_land_stock
                    WHERE land_use_code = 'ur'
                ),
                new_urban_with_source AS (
                    SELECT 
                        fips_code,
                        county_name,
                        state_name,
                        scenario_name,
                        from_category,
                        SUM(total_area) as new_urban_acres,
                        region,
                        subregion
                    FROM "County-Level Land Use Transitions"
                    WHERE to_category = 'Urban' AND from_category != 'Urban'
                    GROUP BY fips_code, county_name, state_name, scenario_name, from_category, region, subregion
                ),
                total_new_urban AS (
                    SELECT 
                        fips_code,
                        county_name,
                        state_name,
                        scenario_name,
                        region,
                        subregion,
                        SUM(new_urban_acres) as total_new_urban_acres
                    FROM new_urban_with_source
                    GROUP BY fips_code, county_name, state_name, scenario_name, region, subregion
                )
                SELECT 
                    b.fips_code,
                    t.county_name,
                    t.state_name,
                    t.region,
                    t.subregion,
                    b.scenario_name,
                    COALESCE(b.baseline_urban_acres_2020, 0) as baseline_urban_acres_2020,
                    COALESCE(t.total_new_urban_acres, 0) as total_new_urban_acres,
                    (COALESCE(b.baseline_urban_acres_2020, 0) + COALESCE(t.total_new_urban_acres, 0)) as projected_urban_acres_2070,
                    -- Proper urbanization rate as percentage relative to 2020 baseline
                    CASE 
                        WHEN COALESCE(b.baseline_urban_acres_2020, 0) > 0 THEN 
                            (COALESCE(t.total_new_urban_acres, 0) / b.baseline_urban_acres_2020 * 100)
                        ELSE NULL
                    END as urbanization_rate_percent,
                    -- Absolute urban expansion rate (acres per decade)
                    COALESCE(t.total_new_urban_acres, 0) / 5.0 as urban_expansion_rate_acres_per_decade,
                    -- Annualized growth rate
                    CASE 
                        WHEN COALESCE(b.baseline_urban_acres_2020, 0) > 0 THEN 
                            (POWER((COALESCE(b.baseline_urban_acres_2020, 0) + COALESCE(t.total_new_urban_acres, 0)) / b.baseline_urban_acres_2020, 1.0/50.0) - 1) * 100
                        ELSE NULL
                    END as annualized_urban_growth_rate_percent,
                    -- Source breakdown pivot (need to handle separately)
                    s.from_category,
                    COALESCE(s.new_urban_acres, 0) as source_acres
                FROM baseline_urban b
                FULL OUTER JOIN total_new_urban t ON b.fips_code = t.fips_code 
                    AND b.county_name = t.county_name 
                    AND b.state_name = t.state_name 
                    AND b.scenario_name = t.scenario_name
                LEFT JOIN new_urban_with_source s ON b.fips_code = s.fips_code 
                    AND b.county_name = s.county_name 
                    AND b.state_name = s.state_name 
                    AND b.scenario_name = s.scenario_name
                WHERE 1=1
                '''
                
            elif spatial_level == "State":
                # Enhanced state query using baseline_state_land_stock
                query = '''
                WITH baseline_urban AS (
                    SELECT 
                        state_name,
                        region,
                        subregion,
                        scenario_name,
                        baseline_acres_2020 as baseline_urban_acres_2020
                    FROM baseline_state_land_stock
                    WHERE land_use_code = 'ur'
                ),
                new_urban_development AS (
                    SELECT 
                        state_name,
                        region,
                        subregion,
                        scenario_name,
                        SUM(total_area) as total_new_urban_acres
                    FROM "State-Level Land Use Transitions"
                    WHERE to_category = 'Urban' AND from_category != 'Urban'
                    GROUP BY state_name, region, subregion, scenario_name
                )
                SELECT 
                    b.state_name,
                    b.region,
                    b.subregion,
                    b.scenario_name,
                    COALESCE(b.baseline_urban_acres_2020, 0) as baseline_urban_acres_2020,
                    COALESCE(t.total_new_urban_acres, 0) as total_new_urban_acres,
                    (COALESCE(b.baseline_urban_acres_2020, 0) + COALESCE(t.total_new_urban_acres, 0)) as projected_urban_acres_2070,
                    -- Proper urbanization rate as percentage relative to 2020 baseline
                    CASE 
                        WHEN COALESCE(b.baseline_urban_acres_2020, 0) > 0 THEN 
                            (COALESCE(t.total_new_urban_acres, 0) / b.baseline_urban_acres_2020 * 100)
                        ELSE NULL
                    END as urbanization_rate_percent,
                    -- Absolute urban expansion rate (acres per decade)
                    COALESCE(t.total_new_urban_acres, 0) / 5.0 as urban_expansion_rate_acres_per_decade,
                    -- Annualized growth rate
                    CASE 
                        WHEN COALESCE(b.baseline_urban_acres_2020, 0) > 0 THEN 
                            (POWER((COALESCE(b.baseline_urban_acres_2020, 0) + COALESCE(t.total_new_urban_acres, 0)) / b.baseline_urban_acres_2020, 1.0/50.0) - 1) * 100
                        ELSE NULL
                    END as annualized_urban_growth_rate_percent
                FROM baseline_urban b
                LEFT JOIN new_urban_development t ON b.state_name = t.state_name 
                    AND b.scenario_name = t.scenario_name
                WHERE 1=1
                '''
            else:
                raise ValueError(f"Unsupported spatial level: {spatial_level}")
            
            # Add scenario filter if specified
            if scenario_filter and scenario_filter != "All Scenarios":
                scenario_key = scenario_reverse_mapping.get(scenario_filter, scenario_filter)
                query += f" AND b.scenario_name = '{scenario_key}'"
            
            query += " ORDER BY COALESCE(t.total_new_urban_acres, 0) DESC"
            
            # Execute query and load data
            result_df = conn.execute(query).df()
            conn.close()
            
            if result_df.empty:
                st.warning(f"No data available for {spatial_level} level with the selected scenario.")
                return pd.DataFrame()
            
            return result_df
                
        except Exception as e:
            st.error(f"Error loading enhanced urbanization data: {str(e)}")
            logger.error(f"Error loading enhanced urbanization data: {str(e)}", exc_info=True)
            return pd.DataFrame()
    
    @staticmethod
    @st.cache_data
    def load_enhanced_forest_data(
        spatial_level: str, 
        scenario_filter: Optional[str] = None, 
        destination_filter: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load enhanced forest loss data with baseline rates and destination breakdown.
        
        Args:
            spatial_level: County, State, Subregion, Region, or National
            scenario_filter: Optional scenario name filter
            destination_filter: Optional destination land use filter
            
        Returns:
            Enhanced DataFrame with baseline metrics
        """
        # Similar implementation to urbanization but for forest loss
        # Implementation would follow same pattern as urbanization but for forest->other transitions
        logger.info(f"Loading enhanced forest data for {spatial_level} level")
        
        try:
            # Placeholder implementation - would need similar complex query structure
            # This would be implemented similar to the urbanization query above
            # but filtering for from_category = 'Forest' instead of to_category = 'Urban'
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading enhanced forest data: {e}")
            return pd.DataFrame() 