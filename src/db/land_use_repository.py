"""
Land use data repository for accessing and manipulating land use data.

This repository provides methods to access land use data, scenarios,
time steps, and transitions.
"""

import logging
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)

class LandUseRepository(BaseRepository):
    """Repository for accessing land use data."""
    
    @classmethod
    def get_scenarios(cls) -> pd.DataFrame:
        """
        Get all available scenarios.
        
        Returns:
            DataFrame with scenario information
        """
        query = """
        SELECT 
            scenario_id,
            scenario_name,
            gcm,
            rcp,
            ssp
        FROM 
            scenarios
        ORDER BY 
            scenario_name
        """
        return cls.query_to_df(query)
    
    @classmethod
    def get_time_steps(cls) -> pd.DataFrame:
        """
        Get all available time steps.
        
        Returns:
            DataFrame with time step information
        """
        query = """
        SELECT 
            decade_id as time_step_id,
            start_year,
            end_year
        FROM 
            decades
        ORDER BY 
            start_year
        """
        return cls.query_to_df(query)
    
    @classmethod
    def get_counties(cls) -> pd.DataFrame:
        """
        Get all available counties.
        
        Returns:
            DataFrame with county information
        """
        query = """
        SELECT 
            fips_code,
            county_name
        FROM 
            counties
        ORDER BY 
            county_name
        """
        return cls.query_to_df(query)
    
    @classmethod
    def get_land_use_types(cls) -> List[str]:
        """
        Get all land use types from the transitions.
        
        Returns:
            List of unique land use types
        """
        query = """
        SELECT DISTINCT from_landuse as land_use_type FROM landuse_change
        UNION
        SELECT DISTINCT to_landuse as land_use_type FROM landuse_change
        ORDER BY land_use_type
        """
        df = cls.query_to_df(query)
        if df.empty:
            return []
        return df['land_use_type'].tolist()
    
    @classmethod
    def get_scenario_by_name(cls, scenario_name: str) -> Optional[Dict[str, Any]]:
        """
        Get scenario details by name.
        
        Args:
            scenario_name: Name of the scenario
            
        Returns:
            Dictionary with scenario details or None if not found
        """
        query = """
        SELECT 
            scenario_id,
            scenario_name,
            gcm,
            rcp,
            ssp
        FROM 
            scenarios
        WHERE 
            scenario_name = ?
        """
        return cls.get_single_row(query, [scenario_name])
    
    @classmethod
    def get_time_period(cls, start_year: int, end_year: int) -> Optional[int]:
        """
        Get time step ID for a given period.
        
        Args:
            start_year: Start year of the period
            end_year: End year of the period
            
        Returns:
            Time step ID or None if not found
        """
        query = """
        SELECT 
            decade_id as time_step_id
        FROM 
            decades
        WHERE 
            start_year = ? AND end_year = ?
        """
        return cls.get_single_value(query, [start_year, end_year])
    
    @classmethod
    def find_matching_time_periods(cls, start_year: int, end_year: int) -> List[int]:
        """
        Find time periods that match or overlap with the given range.
        
        Args:
            start_year: Start year of the period
            end_year: End year of the period
            
        Returns:
            List of matching time step IDs
        """
        query = """
        SELECT 
            decade_id as time_step_id 
        FROM 
            decades 
        WHERE 
            NOT (end_year <= ? OR start_year >= ?)
        ORDER BY 
            start_year
        """
        df = cls.query_to_df(query, [start_year, end_year])
        if df.empty:
            # Fall back to closest period
            query_closest = """
            SELECT 
                decade_id as time_step_id
            FROM 
                decades
            ORDER BY 
                ABS(? - start_year) + ABS(? - end_year)
            LIMIT 1
            """
            closest = cls.get_single_value(query_closest, [start_year, end_year])
            return [closest] if closest is not None else []
        
        return df['time_step_id'].tolist()
    
    @classmethod
    def get_transitions(
        cls,
        scenario_id: int,
        time_step_ids: List[int],
        fips_code: Optional[str] = None,
        land_use_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Get land use transitions filtered by parameters.
        
        Args:
            scenario_id: Scenario ID
            time_step_ids: List of time step IDs
            fips_code: Optional county FIPS code
            land_use_type: Optional land use type
            
        Returns:
            DataFrame with transition information
        """
        # Build the query with placeholders for time_step_ids
        time_placeholders = ','.join(['?'] * len(time_step_ids))
        
        query = f"""
        SELECT 
            t.from_landuse as from_land_use,
            t.to_landuse as to_land_use,
            SUM(t.area_hundreds_acres * 100) as acres_changed
        FROM 
            landuse_change t
        WHERE 
            t.scenario_id = ? 
            AND t.decade_id IN ({time_placeholders})
        """
        
        params = [scenario_id] + time_step_ids
        
        if fips_code:
            query += " AND t.fips_code = ?"
            params.append(fips_code)
            
        if land_use_type:
            query += " AND t.from_landuse = ?"
            params.append(land_use_type)
            
        query += """
        GROUP BY 
            t.from_landuse, t.to_landuse
        ORDER BY 
            acres_changed DESC
        """
        
        return cls.query_to_df(query, params) 