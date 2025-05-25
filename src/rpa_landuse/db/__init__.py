"""
Database module for the RPA Land Use Viewer application.

This module provides database access and query capabilities.
"""

from rpa_landuse.db.database import DBManager
from rpa_landuse.db.base_repository import BaseRepository
from rpa_landuse.db.land_use_repository import LandUseRepository
from rpa_landuse.db.region_repository import RegionRepository
from rpa_landuse.db.analysis_repository import AnalysisRepository
from rpa_landuse.db.schema_manager import SchemaManager
from rpa_landuse.db.import_landuse_data import (
    setup_database, 
    insert_scenarios, 
    insert_time_steps, 
    insert_counties, 
    process_transitions
)
from rpa_landuse.db.add_ensemble_scenario import (
    check_if_ensemble_exists, 
    create_ensemble_scenario, 
    calculate_and_insert_ensemble_transitions
)

__version__ = "1.0.0"
__all__ = [
    'DBManager',
    'BaseRepository',
    'LandUseRepository',
    'RegionRepository',
    'AnalysisRepository',
    'SchemaManager',
    'setup_database',
    'insert_scenarios',
    'insert_time_steps',
    'insert_counties',
    'process_transitions',
    'check_if_ensemble_exists',
    'create_ensemble_scenario',
    'calculate_and_insert_ensemble_transitions'
] 