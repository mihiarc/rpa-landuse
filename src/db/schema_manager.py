"""
Database schema management utility for the RPA Land Use Viewer.

This module handles schema creation, updates, and indexes to optimize
database performance.
"""

import logging
import os
from pathlib import Path
from .database import DBManager

logger = logging.getLogger(__name__)

class SchemaManager:
    """
    Manages the database schema, indexes, and optimizations.
    
    This class provides methods to:
    - Initialize the database schema
    - Add or update indexes
    - Run optimization tasks
    - Execute schema migration scripts
    """
    
    # Key indexes for optimizing common queries
    INDEXES = [
        # Basic indexes (already defined in init.sql)
        ("idx_landuse_change", "landuse_change (scenario_id, decade_id, fips_code)"),
        ("idx_from_landuse", "landuse_change (from_landuse)"),
        ("idx_to_landuse", "landuse_change (to_landuse)"),
        
        # Additional optimized indexes for common queries
        ("idx_transitions_scenario_decade", "landuse_change (scenario_id, decade_id)"),
        ("idx_transitions_scenario_fips", "landuse_change (scenario_id, fips_code)"),
        ("idx_transitions_from_to", "landuse_change (from_landuse, to_landuse)"),
        ("idx_transitions_complete", "landuse_change (scenario_id, decade_id, fips_code, from_landuse, to_landuse)"),
        
        # Indexes for lookups
        ("idx_scenarios_name", "scenarios (scenario_name)"),
        ("idx_scenarios_climate", "scenarios (gcm, rcp, ssp)"),
        ("idx_decades_years", "decades (start_year, end_year)"),
    ]
    
    @classmethod
    def initialize_database(cls) -> None:
        """
        Initialize the database with the base schema.
        
        This runs the init.sql script to create the basic tables if they don't exist.
        """
        init_sql_path = Path("data/database/init.sql")
        if not init_sql_path.exists():
            logger.error(f"Init SQL file not found at {init_sql_path}")
            raise FileNotFoundError(f"Init SQL file not found at {init_sql_path}")
        
        with open(init_sql_path, "r") as f:
            init_sql = f.read()
        
        logger.info("Initializing database schema")
        with DBManager.connection() as conn:
            conn.execute(init_sql)
        logger.info("Database schema initialized")
    
    @classmethod
    def ensure_indexes(cls) -> None:
        """
        Ensure all required indexes exist in the database.
        
        This method creates all indexes with IF NOT EXISTS to ensure they're present.
        We simply create all indexes each time since creating an existing index is a no-op.
        """
        logger.info("Ensuring database indexes are created")
        
        with DBManager.connection() as conn:
            for index_name, index_def in cls.INDEXES:
                # Just create the index with IF NOT EXISTS
                logger.info(f"Creating index {index_name}")
                create_query = f"CREATE INDEX IF NOT EXISTS {index_name} ON {index_def}"
                conn.execute(create_query)
        
        logger.info("All database indexes are in place")
    
    @classmethod
    def optimize_database(cls) -> None:
        """
        Run optimization tasks on the database.
        
        This includes:
        - Analyzing tables for query planning
        - Vacuuming to reclaim space
        - Optimizing layout
        """
        logger.info("Optimizing database")
        
        with DBManager.connection() as conn:
            # Analyze tables for better query planning
            logger.info("Analyzing tables")
            conn.execute("ANALYZE")
            
            # Vacuum to reclaim space and optimize layout
            logger.info("Vacuuming database")
            conn.execute("VACUUM")
            
            # Optimization is handled by ANALYZE and VACUUM
            logger.info("Optimization complete")
        
        logger.info("Database optimization complete")
    
    @classmethod
    def run_migration_scripts(cls, script_paths: list) -> None:
        """
        Run migration scripts to update the database schema.
        
        Args:
            script_paths: List of paths to SQL script files to execute
        """
        logger.info(f"Running {len(script_paths)} migration scripts")
        
        for script_path in script_paths:
            path = Path(script_path)
            if not path.exists():
                logger.warning(f"Migration script not found: {script_path}")
                continue
                
            logger.info(f"Running migration script: {path.name}")
            
            with open(path, "r") as f:
                script = f.read()
                
            with DBManager.connection() as conn:
                try:
                    conn.execute(script)
                    logger.info(f"Migration script completed: {path.name}")
                except Exception as e:
                    logger.error(f"Error in migration script {path.name}: {e}")
                    raise
        
        logger.info("All migration scripts completed") 