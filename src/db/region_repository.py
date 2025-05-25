"""
Region repository for accessing geographic data.

This repository provides methods to access and manipulate region data, 
including counties, states, and RPA regions.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from .base_repository import BaseRepository
from .database import DBManager

logger = logging.getLogger(__name__)

class RegionRepository(BaseRepository):
    """Repository for accessing region data."""
    
    # Constants for materialized view management
    MATERIALIZED_VIEWS = {
        'region_transitions': """
        SELECT 
            s.scenario_id, 
            s.scenario_name,
            t.decade_id,
            d.decade_name,
            c.region,
            t.from_landuse,
            t.to_landuse,
            SUM(t.area_hundreds_acres) AS total_area
        FROM 
            landuse_change t
        JOIN 
            counties c ON t.fips_code = c.fips_code
        JOIN 
            scenarios s ON t.scenario_id = s.scenario_id
        JOIN 
            decades d ON t.decade_id = d.decade_id
        GROUP BY 
            s.scenario_id, s.scenario_name, t.decade_id, d.decade_name,
            c.region, t.from_landuse, t.to_landuse
        """,
        
        'subregion_transitions': """
        SELECT 
            s.scenario_id, 
            s.scenario_name,
            t.decade_id,
            d.decade_name,
            c.region,
            c.subregion,
            t.from_landuse,
            t.to_landuse,
            SUM(t.area_hundreds_acres) AS total_area
        FROM 
            landuse_change t
        JOIN 
            counties c ON t.fips_code = c.fips_code
        JOIN 
            scenarios s ON t.scenario_id = s.scenario_id
        JOIN 
            decades d ON t.decade_id = d.decade_id
        GROUP BY 
            s.scenario_id, s.scenario_name, t.decade_id, d.decade_name,
            c.region, c.subregion, t.from_landuse, t.to_landuse
        """,
        
        'state_transitions': """
        SELECT 
            s.scenario_id, 
            s.scenario_name,
            t.decade_id,
            d.decade_name,
            c.state_name,
            c.region,
            c.subregion,
            t.from_landuse,
            t.to_landuse,
            SUM(t.area_hundreds_acres) AS total_area
        FROM 
            landuse_change t
        JOIN 
            counties c ON t.fips_code = c.fips_code
        JOIN 
            scenarios s ON t.scenario_id = s.scenario_id
        JOIN 
            decades d ON t.decade_id = d.decade_id
        GROUP BY 
            s.scenario_id, s.scenario_name, t.decade_id, d.decade_name,
            c.state_name, c.region, c.subregion, t.from_landuse, t.to_landuse
        """
    }
    
    @classmethod
    def get_counties(cls) -> pd.DataFrame:
        """
        Get all counties.
        
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
    def get_states(cls) -> pd.DataFrame:
        """
        Get all states.
        
        Returns:
            DataFrame with state information
        """
        query = """
        SELECT 
            state_fips,
            state_name,
            state_abbr
        FROM 
            states
        ORDER BY 
            state_name
        """
        return cls.query_to_df(query)
    
    @classmethod
    def get_rpa_regions(cls) -> pd.DataFrame:
        """
        Get all RPA regions.
        
        Returns:
            DataFrame with RPA region information
        """
        query = """
        SELECT 
            region_id,
            region_name
        FROM 
            rpa_regions
        ORDER BY 
            region_name
        """
        return cls.query_to_df(query)
    
    @classmethod
    def get_rpa_subregions(cls) -> pd.DataFrame:
        """
        Get all RPA subregions.
        
        Returns:
            DataFrame with RPA subregion information
        """
        query = """
        SELECT 
            subregion_id,
            region_id,
            subregion_name
        FROM 
            rpa_subregions
        ORDER BY 
            subregion_name
        """
        return cls.query_to_df(query)
    
    @classmethod
    def get_counties_by_state(cls, state_fips: str) -> pd.DataFrame:
        """
        Get counties for a specific state.
        
        Args:
            state_fips: State FIPS code
            
        Returns:
            DataFrame with county information
        """
        query = """
        SELECT 
            c.fips_code,
            c.county_name,
            s.state_fips,
            s.state_name,
            s.state_abbr
        FROM 
            counties c
        JOIN 
            county_state_mapping csm ON c.fips_code = csm.county_fips
        JOIN
            states s ON csm.state_fips = s.state_fips
        WHERE 
            s.state_fips = ?
        ORDER BY 
            c.county_name
        """
        return cls.query_to_df(query, [state_fips])
    
    @classmethod
    def get_counties_by_region(cls, region_id: int) -> pd.DataFrame:
        """
        Get counties for a specific RPA region.
        
        Args:
            region_id: RPA region ID
            
        Returns:
            DataFrame with county information
        """
        query = """
        SELECT 
            c.fips_code,
            c.county_name,
            r.region_id,
            r.region_name
        FROM 
            counties c
        JOIN 
            county_region_mapping crm ON c.fips_code = crm.county_fips
        JOIN
            rpa_regions r ON crm.region_id = r.region_id
        WHERE 
            r.region_id = ?
        ORDER BY 
            c.county_name
        """
        return cls.query_to_df(query, [region_id])
    
    @classmethod
    def get_counties_by_subregion(cls, subregion_id: int) -> pd.DataFrame:
        """
        Get counties for a specific RPA subregion.
        
        Args:
            subregion_id: RPA subregion ID
            
        Returns:
            DataFrame with county information
        """
        query = """
        SELECT 
            c.fips_code,
            c.county_name,
            sr.subregion_id,
            sr.subregion_name,
            r.region_id,
            r.region_name
        FROM 
            counties c
        JOIN 
            county_subregion_mapping csrm ON c.fips_code = csrm.county_fips
        JOIN
            rpa_subregions sr ON csrm.subregion_id = sr.subregion_id
        JOIN
            rpa_regions r ON sr.region_id = r.region_id
        WHERE 
            sr.subregion_id = ?
        ORDER BY 
            c.county_name
        """
        return cls.query_to_df(query, [subregion_id])
    
    @classmethod
    def get_region_mapping(cls) -> pd.DataFrame:
        """
        Get a complete mapping of counties to states, regions, and subregions.
        
        Returns:
            DataFrame with complete region mapping
        """
        query = """
        SELECT 
            c.fips_code,
            c.county_name,
            s.state_fips,
            s.state_name,
            s.state_abbr,
            r.region_id,
            r.region_name,
            sr.subregion_id,
            sr.subregion_name
        FROM 
            counties c
        LEFT JOIN 
            county_state_mapping csm ON c.fips_code = csm.county_fips
        LEFT JOIN
            states s ON csm.state_fips = s.state_fips
        LEFT JOIN
            county_region_mapping crm ON c.fips_code = crm.county_fips
        LEFT JOIN
            rpa_regions r ON crm.region_id = r.region_id
        LEFT JOIN
            county_subregion_mapping csrm ON c.fips_code = csrm.county_fips
        LEFT JOIN
            rpa_subregions sr ON csrm.subregion_id = sr.subregion_id
        ORDER BY 
            s.state_name,
            c.county_name
        """
        return cls.query_to_df(query)
    
    # --- Regional Analysis Methods ---
    
    @classmethod
    def create_materialized_views(cls, threads: int = 8, memory_limit: str = '4GB') -> None:
        """
        Create materialized views for regional analysis.
        
        This method creates or refreshes the materialized views for regional transitions.
        
        Args:
            threads: Number of threads to use for parallel execution
            memory_limit: Memory limit for DuckDB query execution
        """
        logger.info("Creating materialized views for regional analysis")
        
        with DBManager.connection() as conn:
            # Set up optimizations
            conn.execute(f"SET threads={threads}")
            conn.execute(f"SET memory_limit='{memory_limit}'")
            
            # Create indexes to optimize joins if not exist
            logger.info("Creating supporting indexes")
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_counties_region 
            ON counties(region);
            """)
            
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_counties_subregion 
            ON counties(subregion);
            """)
            
            conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_counties_state_name 
            ON counties(state_name);
            """)
            
            # Create or replace the materialized views
            for view_name, view_query in cls.MATERIALIZED_VIEWS.items():
                table_name = f"mat_{view_name}"
                logger.info(f"Creating materialized view: {table_name}")
                
                # Create or replace materialized view as table
                conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                conn.execute(f"CREATE TABLE {table_name} AS {view_query}")
                
                # Create indexes on the materialized view for common filters
                conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_scenario 
                ON {table_name}(scenario_id);
                """)
                
                conn.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
                ON {table_name}(decade_id);
                """)
                
                if 'region' in view_query:
                    conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_region 
                    ON {table_name}(region);
                    """)
                
                if 'subregion' in view_query:
                    conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_subregion 
                    ON {table_name}(subregion);
                    """)
                
                if 'state_name' in view_query:
                    conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_state 
                    ON {table_name}(state_name);
                    """)
                
                # Analyze the table for query optimization
                conn.execute(f"ANALYZE {table_name}")
                
            logger.info("Created all materialized views for regional analysis")
    
    @classmethod
    def export_regional_data_to_parquet(cls, output_dir: str = 'data/exports', 
                                        partition_by_scenario: bool = True,
                                        scenario_ids: Optional[List[int]] = None) -> Dict[str, str]:
        """
        Export regionalized data to Parquet files for external analysis.
        
        This method exports the materialized views to Parquet format, optionally 
        partitioning the data by scenario for more efficient access.
        
        Args:
            output_dir: Directory where Parquet files will be saved
            partition_by_scenario: If True, create separate files for each scenario
            scenario_ids: Optional list of scenario IDs to export (if None, all scenarios are exported)
            
        Returns:
            Dictionary mapping view names to their Parquet file paths
        """
        logger.info(f"Exporting regional data to Parquet in {output_dir}")
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Track all generated files
        exported_files = {}
        
        with DBManager.connection() as conn:
            # Set optimized settings for export
            conn.execute("SET threads=8")
            
            for view_name in cls.MATERIALIZED_VIEWS.keys():
                mat_table = f"mat_{view_name}"
                
                if partition_by_scenario:
                    # Get scenarios to export
                    scenario_filter = ""
                    if scenario_ids:
                        scenario_ids_str = ", ".join(str(s_id) for s_id in scenario_ids)
                        scenario_filter = f"WHERE scenario_id IN ({scenario_ids_str})"
                        
                    # Get all scenarios that match filter
                    scenarios = conn.execute(f"""
                    SELECT DISTINCT scenario_id, scenario_name 
                    FROM {mat_table}
                    {scenario_filter}
                    ORDER BY scenario_id
                    """).fetchall()
                    
                    # Create a directory for this view
                    view_dir = os.path.join(output_dir, view_name)
                    os.makedirs(view_dir, exist_ok=True)
                    
                    # Export each scenario to a separate file
                    for scenario_id, scenario_name in scenarios:
                        # Clean scenario name for filename
                        clean_name = "".join(c if c.isalnum() else "_" for c in scenario_name)
                        filename = f"{view_name}_scenario_{scenario_id}_{clean_name}.parquet"
                        filepath = os.path.join(view_dir, filename)
                        
                        logger.info(f"Exporting {mat_table} for scenario {scenario_id} to {filepath}")
                        
                        # Use DuckDB's COPY statement for efficient export
                        conn.execute(f"""
                        COPY (
                            SELECT * FROM {mat_table} 
                            WHERE scenario_id = {scenario_id}
                        ) TO '{filepath}' (FORMAT PARQUET, COMPRESSION 'ZSTD')
                        """)
                        
                        if scenario_id not in exported_files:
                            exported_files[scenario_id] = []
                        exported_files[scenario_id].append(filepath)
                else:
                    # Export entire view or filtered by scenario_ids to a single file
                    scenario_filter = ""
                    if scenario_ids:
                        scenario_ids_str = ", ".join(str(s_id) for s_id in scenario_ids)
                        scenario_filter = f"WHERE scenario_id IN ({scenario_ids_str})"
                        
                    filepath = os.path.join(output_dir, f"{view_name}.parquet")
                    logger.info(f"Exporting {mat_table} to {filepath}")
                    
                    conn.execute(f"""
                    COPY (
                        SELECT * FROM {mat_table}
                        {scenario_filter}
                    ) 
                    TO '{filepath}' (FORMAT PARQUET, COMPRESSION 'ZSTD')
                    """)
                    
                    exported_files[view_name] = filepath
        
        logger.info(f"Exported {len(exported_files)} regional data files to Parquet format")
        return exported_files
    
    @classmethod
    def get_region_transitions(cls, scenario_id: Optional[int] = None, 
                              decade_id: Optional[int] = None,
                              region: Optional[str] = None,
                              use_materialized: bool = True) -> pd.DataFrame:
        """
        Get aggregated land use transitions by region.
        
        Args:
            scenario_id: Optional filter by scenario
            decade_id: Optional filter by time step
            region: Optional filter by region
            use_materialized: Whether to use materialized views (much faster)
            
        Returns:
            DataFrame with region-level transitions
        """
        table_name = "mat_region_transitions" if use_materialized else "(" + cls.MATERIALIZED_VIEWS['region_transitions'] + ")"
        
        query = f"""
        SELECT * FROM {table_name}
        WHERE 1=1
        """
        
        params = []
        if scenario_id:
            query += " AND scenario_id = ?"
            params.append(scenario_id)
        
        if decade_id:
            query += " AND decade_id = ?"
            params.append(decade_id)
            
        if region:
            query += " AND region = ?"
            params.append(region)
            
        query += " ORDER BY region, from_landuse, to_landuse"
        
        return cls.query_to_df(query, params)
    
    @classmethod
    def get_subregion_transitions(cls, scenario_id: Optional[int] = None, 
                                 decade_id: Optional[int] = None,
                                 region: Optional[str] = None, 
                                 subregion: Optional[str] = None,
                                 use_materialized: bool = True) -> pd.DataFrame:
        """
        Get aggregated land use transitions by subregion.
        
        Args:
            scenario_id: Optional filter by scenario
            decade_id: Optional filter by time step
            region: Optional filter by region
            subregion: Optional filter by subregion
            use_materialized: Whether to use materialized views (much faster)
            
        Returns:
            DataFrame with subregion-level transitions
        """
        table_name = "mat_subregion_transitions" if use_materialized else "(" + cls.MATERIALIZED_VIEWS['subregion_transitions'] + ")"
        
        query = f"""
        SELECT * FROM {table_name}
        WHERE 1=1
        """
        
        params = []
        if scenario_id:
            query += " AND scenario_id = ?"
            params.append(scenario_id)
        
        if decade_id:
            query += " AND decade_id = ?"
            params.append(decade_id)
            
        if region:
            query += " AND region = ?"
            params.append(region)
            
        if subregion:
            query += " AND subregion = ?"
            params.append(subregion)
            
        query += " ORDER BY region, subregion, from_landuse, to_landuse"
        
        return cls.query_to_df(query, params)
    
    @classmethod
    def get_state_transitions(cls, scenario_id: Optional[int] = None, 
                             decade_id: Optional[int] = None,
                             state_name: Optional[str] = None,
                             region: Optional[str] = None, 
                             subregion: Optional[str] = None,
                             use_materialized: bool = True) -> pd.DataFrame:
        """
        Get aggregated land use transitions by state.
        
        Args:
            scenario_id: Optional filter by scenario
            decade_id: Optional filter by time step
            state_name: Optional filter by state
            region: Optional filter by region
            subregion: Optional filter by subregion
            use_materialized: Whether to use materialized views (much faster)
            
        Returns:
            DataFrame with state-level transitions
        """
        table_name = "mat_state_transitions" if use_materialized else "(" + cls.MATERIALIZED_VIEWS['state_transitions'] + ")"
        
        query = f"""
        SELECT * FROM {table_name}
        WHERE 1=1
        """
        
        params = []
        if scenario_id:
            query += " AND scenario_id = ?"
            params.append(scenario_id)
        
        if decade_id:
            query += " AND decade_id = ?"
            params.append(decade_id)
            
        if state_name:
            query += " AND state_name = ?"
            params.append(state_name)
            
        if region:
            query += " AND region = ?"
            params.append(region)
            
        if subregion:
            query += " AND subregion = ?"
            params.append(subregion)
            
        query += " ORDER BY state_name, from_landuse, to_landuse"
        
        return cls.query_to_df(query, params)
    
    @classmethod
    def get_region_totals(cls, scenario_id: Optional[int] = None, 
                         decade_id: Optional[int] = None) -> pd.DataFrame:
        """
        Get total area by region, summarizing across all land use types.
        
        Args:
            scenario_id: Optional filter by scenario
            decade_id: Optional filter by time step
            
        Returns:
            DataFrame with region-level totals
        """
        query = """
        SELECT 
            scenario_id,
            scenario_name,
            decade_id,
            decade_name,
            region,
            SUM(total_area) as total_area
        FROM 
            mat_region_transitions
        WHERE 1=1
        """
        
        params = []
        if scenario_id:
            query += " AND scenario_id = ?"
            params.append(scenario_id)
        
        if decade_id:
            query += " AND decade_id = ?"
            params.append(decade_id)
            
        query += """
        GROUP BY 
            scenario_id, scenario_name, decade_id, decade_name, region
        ORDER BY 
            region
        """
        
        return cls.query_to_df(query, params)
    
    @classmethod
    def refresh_materialized_views(cls, 
                                  scenario_id: Optional[int] = None,
                                  threads: int = 8, 
                                  memory_limit: str = '4GB') -> None:
        """
        Refresh the materialized views, optionally for a specific scenario.
        
        This allows for incremental updates when new scenarios or data are added.
        
        Args:
            scenario_id: If provided, only refresh data for this scenario
            threads: Number of threads to use for parallel execution
            memory_limit: Memory limit for DuckDB query execution
        """
        logger.info("Refreshing materialized views for regional analysis")
        
        with DBManager.connection() as conn:
            # Set up optimizations
            conn.execute(f"SET threads={threads}")
            conn.execute(f"SET memory_limit='{memory_limit}'")
            
            # For each materialized view
            for view_name, view_query in cls.MATERIALIZED_VIEWS.items():
                table_name = f"mat_{view_name}"
                
                # Check if the table exists
                table_exists = conn.execute(f"""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='{table_name}'
                """).fetchone()
                
                if not table_exists:
                    # Table doesn't exist yet, create it
                    logger.info(f"Table {table_name} doesn't exist, creating it")
                    conn.execute(f"CREATE TABLE {table_name} AS {view_query}")
                    
                    # Create indexes
                    logger.info(f"Creating indexes for {table_name}")
                    conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_scenario 
                    ON {table_name}(scenario_id)
                    """)
                    
                    conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
                    ON {table_name}(decade_id)
                    """)
                    
                    if 'region' in view_query:
                        conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table_name}_region 
                        ON {table_name}(region)
                        """)
                    
                    if 'subregion' in view_query:
                        conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table_name}_subregion 
                        ON {table_name}(subregion)
                        """)
                    
                    if 'state_name' in view_query:
                        conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table_name}_state 
                        ON {table_name}(state_name)
                        """)
                elif scenario_id:
                    # Table exists and we need to refresh a specific scenario
                    logger.info(f"Refreshing {table_name} for scenario {scenario_id}")
                    
                    # First, delete existing data for this scenario
                    conn.execute(f"""
                    DELETE FROM {table_name} 
                    WHERE scenario_id = {scenario_id}
                    """)
                    
                    # Then insert new data
                    scenario_filter = view_query + f" WHERE s.scenario_id = {scenario_id}"
                    conn.execute(f"""
                    INSERT INTO {table_name} 
                    {scenario_filter}
                    """)
                else:
                    # Full refresh of existing table
                    logger.info(f"Performing full refresh of {table_name}")
                    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                    conn.execute(f"CREATE TABLE {table_name} AS {view_query}")
                    
                    # Recreate indexes
                    conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_scenario 
                    ON {table_name}(scenario_id)
                    """)
                    
                    conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_time 
                    ON {table_name}(decade_id)
                    """)
                    
                    if 'region' in view_query:
                        conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table_name}_region 
                        ON {table_name}(region)
                        """)
                    
                    if 'subregion' in view_query:
                        conn.execute(f"""
                        CREATE INDEX IF NOT EXISTS idx_{table_name}_subregion 
                        ON {table_name}(subregion)
                        """)
                
                # Analyze the table for query optimization
                conn.execute(f"ANALYZE {table_name}")
            
            logger.info("Refreshed all materialized views for regional analysis") 