"""
Analysis repository for land use data analysis.

This repository provides methods for analyzing land use data,
including transitions, changes, and comparisons between scenarios.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
from .base_repository import BaseRepository

logger = logging.getLogger(__name__)

class AnalysisRepository(BaseRepository):
    """Repository for land use data analysis."""
    
    @classmethod
    def total_net_change_by_land_use_type(
        cls,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        scenario_id: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Calculate total net change (gain or loss) for each land use type.
        
        Args:
            start_year: Optional starting year
            end_year: Optional ending year
            scenario_id: Optional scenario ID
            
        Returns:
            DataFrame with land use types and their net changes
        """
        # Build filters
        filter_parts = []
        params = []
        
        if scenario_id:
            filter_parts.append("scenario_id = ?")
            params.append(scenario_id)
        
        if start_year and end_year:
            filter_parts.append("decade_id IN (SELECT decade_id FROM decades WHERE start_year >= ? AND end_year <= ?)")
            params.extend([start_year, end_year])
        
        # Create WHERE clause
        filter_sql = ""
        if filter_parts:
            filter_sql = "WHERE " + " AND ".join(filter_parts)
            
        # Build the query
        query = f"""
        WITH from_sums AS (
            SELECT 
                from_landuse AS land_use_type,
                -SUM(area_hundreds_acres * 100) AS net_change
            FROM landuse_change 
            {filter_sql}
            GROUP BY from_landuse
        ),
        to_sums AS (
            SELECT 
                to_landuse AS land_use_type,
                SUM(area_hundreds_acres * 100) AS net_change
            FROM landuse_change 
            {filter_sql}
            GROUP BY to_landuse
        ),
        combined AS (
            SELECT * FROM from_sums
            UNION ALL
            SELECT * FROM to_sums
        )
        SELECT 
            land_use_type,
            SUM(net_change) AS total_net_change
        FROM combined
        GROUP BY land_use_type
        ORDER BY total_net_change DESC
        """
        
        # Use same parameters for both parts of the query
        all_params = params + params if params else []
        
        return cls.query_to_df(query, all_params)
    
    @classmethod
    def annualized_change_rate(
        cls,
        scenario_id: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Calculate average annual rate of change for each land use type.
        
        Args:
            scenario_id: Optional scenario ID
            
        Returns:
            DataFrame with time periods, land use types, and annual change rates
        """
        # Build scenario filter
        scenario_filter = ""
        scenario_params = []
        
        if scenario_id:
            scenario_filter = "WHERE lut.scenario_id = ?"
            scenario_params.append(scenario_id)
        
        query = f"""
        WITH period_changes AS (
            SELECT 
                d.start_year,
                d.end_year,
                lut.from_landuse AS land_use_type,
                -SUM(lut.area_hundreds_acres * 100) AS acres_lost
            FROM landuse_change lut
            JOIN decades d ON lut.decade_id = d.decade_id
            {scenario_filter}
            GROUP BY d.start_year, d.end_year, lut.from_landuse
            
            UNION ALL
            
            SELECT 
                d.start_year,
                d.end_year,
                lut.to_landuse AS land_use_type,
                SUM(lut.area_hundreds_acres * 100) AS acres_gained
            FROM landuse_change lut
            JOIN decades d ON lut.decade_id = d.decade_id
            {scenario_filter}
            GROUP BY d.start_year, d.end_year, lut.to_landuse
        ),
        net_changes AS (
            SELECT
                start_year,
                end_year,
                land_use_type,
                SUM(acres_lost) AS net_change
            FROM period_changes
            GROUP BY start_year, end_year, land_use_type
        )
        SELECT
            start_year,
            end_year,
            land_use_type,
            net_change,
            (end_year - start_year) AS period_years,
            net_change / (end_year - start_year) AS annual_change_rate
        FROM net_changes
        ORDER BY start_year, annual_change_rate DESC
        """
        
        # Duplicate parameters for both parts of the UNION
        params = scenario_params + scenario_params if scenario_id else []
        
        return cls.query_to_df(query, params)
    
    @classmethod
    def peak_change_time_period(
        cls,
        scenario_id: Optional[int] = None,
        land_use_type: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Find time period with largest net change for each land use type.
        
        Args:
            scenario_id: Optional scenario ID
            land_use_type: Optional land use type
            
        Returns:
            DataFrame with peak change periods by land use type
        """
        # Build filters
        filter_parts = []
        params = []
        
        if scenario_id:
            filter_parts.append("lut.scenario_id = ?")
            params.append(scenario_id)
        
        if land_use_type:
            filter_parts.append("land_use_type = ?")
            params.append(land_use_type)
        
        # Create WHERE clause
        filter_sql = ""
        if filter_parts:
            filter_sql = "WHERE " + " AND ".join(filter_parts)
            
        query = f"""
        WITH period_changes AS (
            SELECT 
                d.start_year,
                d.end_year,
                lut.from_landuse AS land_use_type,
                -SUM(lut.area_hundreds_acres * 100) AS net_change
            FROM landuse_change lut
            JOIN decades d ON lut.decade_id = d.decade_id
            GROUP BY d.start_year, d.end_year, lut.from_landuse
            
            UNION ALL
            
            SELECT 
                d.start_year,
                d.end_year,
                lut.to_landuse AS land_use_type,
                SUM(lut.area_hundreds_acres * 100) AS net_change
            FROM landuse_change lut
            JOIN decades d ON lut.decade_id = d.decade_id
            GROUP BY d.start_year, d.end_year, lut.to_landuse
        ),
        net_changes AS (
            SELECT
                start_year,
                end_year,
                land_use_type,
                SUM(net_change) AS total_net_change
            FROM period_changes
            GROUP BY start_year, end_year, land_use_type
        ),
        ranked_changes AS (
            SELECT
                land_use_type,
                start_year,
                end_year,
                total_net_change,
                ABS(total_net_change) AS abs_change,
                ROW_NUMBER() OVER (PARTITION BY land_use_type ORDER BY ABS(total_net_change) DESC) AS rank
            FROM net_changes
            {filter_sql}
        )
        SELECT
            land_use_type,
            start_year,
            end_year,
            total_net_change
        FROM ranked_changes
        WHERE rank = 1
        ORDER BY abs_change DESC
        """
        
        return cls.query_to_df(query, params)
    
    @classmethod
    def major_transitions(
        cls,
        start_year: int,
        end_year: int,
        scenario_id: Optional[int] = None,
        limit: int = 10
    ) -> pd.DataFrame:
        """
        Identify the major land use transitions during a period.
        
        Args:
            start_year: Start year
            end_year: End year
            scenario_id: Optional scenario ID
            limit: Number of top transitions to return
            
        Returns:
            DataFrame with major transitions
        """
        # Find time periods that match the years
        time_periods_query = """
        SELECT decade_id 
        FROM decades 
        WHERE NOT (end_year <= ? OR start_year >= ?)
        ORDER BY start_year
        """
        
        time_periods_df = cls.query_to_df(time_periods_query, [start_year, end_year])
        
        if time_periods_df.empty:
            # Fall back to closest period
            closest_query = """
            SELECT decade_id
            FROM decades
            ORDER BY ABS(? - start_year) + ABS(? - end_year)
            LIMIT 1
            """
            closest_df = cls.query_to_df(closest_query, [start_year, end_year])
            
            if not closest_df.empty:
                decade_ids = closest_df['decade_id'].tolist()
            else:
                logger.warning("No matching time periods found")
                return pd.DataFrame()
        else:
            decade_ids = time_periods_df['decade_id'].tolist()
        
        # Build query with placeholders for decade_ids
        time_placeholders = ','.join(['?'] * len(decade_ids))
        
        query = f"""
        SELECT 
            from_landuse,
            to_landuse,
            SUM(area_hundreds_acres * 100) as acres_changed
        FROM 
            landuse_change
        WHERE 
            decade_id IN ({time_placeholders})
        """
        
        params = decade_ids.copy()
        
        if scenario_id:
            query += " AND scenario_id = ?"
            params.append(scenario_id)
            
        query += """
        GROUP BY 
            from_landuse, to_landuse
        ORDER BY 
            acres_changed DESC
        LIMIT ?
        """
        
        params.append(limit)
        
        return cls.query_to_df(query, params)
    
    @classmethod
    def compare_scenarios(
        cls,
        start_year: int,
        end_year: int,
        land_use_type: str,
        scenario_1: str,
        scenario_2: str
    ) -> pd.DataFrame:
        """
        Compare land use changes between two scenarios.
        
        Args:
            start_year: Start year for analysis
            end_year: End year for analysis
            land_use_type: Land use type to analyze
            scenario_1: First scenario name
            scenario_2: Second scenario name
            
        Returns:
            DataFrame with comparison results
        """
        # Get scenario IDs
        scenarios_query = """
        SELECT scenario_id, scenario_name
        FROM scenarios
        WHERE scenario_name IN (?, ?)
        """
        
        scenarios_df = cls.query_to_df(scenarios_query, [scenario_1, scenario_2])
        
        if len(scenarios_df) < 2:
            logger.warning("Could not find both scenarios")
            return pd.DataFrame()
        
        # Find matching time periods
        time_periods_query = """
        SELECT decade_id 
        FROM decades 
        WHERE NOT (end_year <= ? OR start_year >= ?)
        ORDER BY start_year
        """
        
        time_periods_df = cls.query_to_df(time_periods_query, [start_year, end_year])
        
        if time_periods_df.empty:
            logger.warning("No matching time periods found")
            return pd.DataFrame()
            
        decade_ids = time_periods_df['decade_id'].tolist()
        
        # Build query for each scenario
        time_placeholders = ','.join(['?'] * len(decade_ids))
        
        # Complex query to compare net changes for the specific land use type
        query = f"""
        WITH scenario1_changes AS (
            -- From changes (losses)
            SELECT 
                'from' as direction,
                from_landuse as land_use,
                to_landuse as conversion,
                -SUM(area_hundreds_acres * 100) as acres_changed
            FROM 
                landuse_change
            WHERE 
                scenario_id = ? AND
                decade_id IN ({time_placeholders}) AND
                from_landuse = ?
            GROUP BY 
                from_landuse, to_landuse
                
            UNION ALL
            
            -- To changes (gains)
            SELECT 
                'to' as direction,
                to_landuse as land_use,
                from_landuse as conversion,
                SUM(area_hundreds_acres * 100) as acres_changed
            FROM 
                landuse_change
            WHERE 
                scenario_id = ? AND
                decade_id IN ({time_placeholders}) AND
                to_landuse = ?
            GROUP BY 
                to_landuse, from_landuse
        ),
        scenario2_changes AS (
            -- From changes (losses)
            SELECT 
                'from' as direction,
                from_landuse as land_use,
                to_landuse as conversion,
                -SUM(area_hundreds_acres * 100) as acres_changed
            FROM 
                landuse_change
            WHERE 
                scenario_id = ? AND
                decade_id IN ({time_placeholders}) AND
                from_landuse = ?
            GROUP BY 
                from_landuse, to_landuse
                
            UNION ALL
            
            -- To changes (gains)
            SELECT 
                'to' as direction,
                to_landuse as land_use,
                from_landuse as conversion,
                SUM(area_hundreds_acres * 100) as acres_changed
            FROM 
                landuse_change
            WHERE 
                scenario_id = ? AND
                decade_id IN ({time_placeholders}) AND
                to_landuse = ?
            GROUP BY 
                to_landuse, from_landuse
        )
        SELECT
            s1.direction,
            s1.land_use,
            s1.conversion,
            s1.acres_changed as scenario1_change,
            s2.acres_changed as scenario2_change,
            (s1.acres_changed - s2.acres_changed) as difference,
            ((s1.acres_changed - s2.acres_changed) / ABS(NULLIF(s2.acres_changed, 0))) * 100 as percent_difference
        FROM
            scenario1_changes s1
        JOIN
            scenario2_changes s2 ON s1.direction = s2.direction AND s1.land_use = s2.land_use AND s1.conversion = s2.conversion
        ORDER BY
            ABS(s1.acres_changed - s2.acres_changed) DESC
        """
        
        # Prepare parameters
        scenario1_id = scenarios_df.loc[scenarios_df['scenario_name'] == scenario_1, 'scenario_id'].iloc[0]
        scenario2_id = scenarios_df.loc[scenarios_df['scenario_name'] == scenario_2, 'scenario_id'].iloc[0]
        
        params = [
            # Scenario 1 params - from
            scenario1_id,
            *decade_ids,
            land_use_type,
            # Scenario 1 params - to
            scenario1_id,
            *decade_ids,
            land_use_type,
            # Scenario 2 params - from
            scenario2_id,
            *decade_ids,
            land_use_type,
            # Scenario 2 params - to
            scenario2_id,
            *decade_ids,
            land_use_type
        ]
        
        return cls.query_to_df(query, params) 