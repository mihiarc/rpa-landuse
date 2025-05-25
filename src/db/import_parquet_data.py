#!/usr/bin/env python3
"""
Import the county land use projections data from Parquet into DuckDB.

This script:
1. Reads the filtered Parquet file with land use projections
2. Transforms the data into a normalized relational structure
3. Loads it into the DuckDB database
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from tqdm import tqdm
import pandas as pd

# Add the src directory to the Python path
src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(src_dir.parent))

from .database import DBManager
from .schema_manager import SchemaManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("parquet-data-import")

# Default Parquet data path
DEFAULT_PARQUET_PATH = "data/raw/rpa_landuse_data_filtered.parquet"

# Mapping from Parquet file land use names to database land use codes
LANDUSE_NAME_TO_CODE = {
    'Crop': 'cr',
    'Cropland': 'cr',
    'Pasture': 'ps',
    'Rangeland': 'rg',
    'Range': 'rg',
    'Forest': 'fr',
    'Urban': 'ur'
}

def setup_database():
    """Ensure database is initialized before importing data."""
    SchemaManager.initialize_database()
    SchemaManager.ensure_indexes()

def insert_scenarios(df):
    """Extract and insert scenario data from the DataFrame."""
    logger.info("Inserting scenarios data")
    scenarios = []
    
    # Get unique scenario names
    unique_scenarios = df['Scenario'].unique()
    
    scenario_id = 1
    for scenario_name in unique_scenarios:
        # Parse the scenario name into components (e.g., CNRM_CM5_rcp45_ssp1)
        parts = scenario_name.split('_')
        if len(parts) >= 4:
            gcm = '_'.join(parts[0:2])  # CNRM_CM5
            rcp = parts[2]              # rcp45
            ssp = parts[3]              # ssp1
        else:
            logger.warning(f"Unexpected scenario format: {scenario_name}")
            gcm, rcp, ssp = scenario_name, "", ""
            
        scenarios.append({
            'scenario_id': scenario_id,
            'scenario_name': scenario_name,
            'gcm': gcm,
            'rcp': rcp,
            'ssp': ssp,
            'description': f"{gcm} climate model with {rcp} emissions and {ssp} socioeconomic pathway"
        })
        scenario_id += 1
    
    # Convert to DataFrame and insert
    scenarios_df = pd.DataFrame(scenarios)
    
    with DBManager.connection() as conn:
        # Use DuckDB's fast DataFrame import
        conn.register('scenarios_temp', scenarios_df)
        conn.execute("""
            INSERT INTO scenarios 
            SELECT * FROM scenarios_temp
            WHERE NOT EXISTS (
                SELECT 1 FROM scenarios 
                WHERE scenario_name = scenarios_temp.scenario_name
            )
        """)
    
    logger.info(f"Inserted {len(scenarios)} scenarios")
    return {s['scenario_name']: s['scenario_id'] for s in scenarios}

def insert_decades(df):
    """Extract and insert decade data."""
    logger.info("Inserting decades data")
    decades = []
    
    decade_id = 1
    # Get all unique time steps from the DataFrame
    unique_year_ranges = df['YearRange'].unique()
    
    for decade_name in sorted(unique_year_ranges):
        # Parse years from format like "2012-2020"
        try:
            start_year, end_year = map(int, decade_name.split('-'))
            decades.append({
                'decade_id': decade_id,
                'decade_name': decade_name,
                'start_year': start_year,
                'end_year': end_year
            })
            decade_id += 1
        except ValueError:
            logger.warning(f"Could not parse decade: {decade_name}")
    
    # Convert to DataFrame and insert
    decades_df = pd.DataFrame(decades)
    
    with DBManager.connection() as conn:
        conn.register('decades_temp', decades_df)
        conn.execute("""
            INSERT INTO decades 
            SELECT * FROM decades_temp
            WHERE NOT EXISTS (
                SELECT 1 FROM decades 
                WHERE decade_name = decades_temp.decade_name
            )
        """)
    
    logger.info(f"Inserted {len(decades)} decades")
    return {d['decade_name']: d['decade_id'] for d in decades}

def insert_counties(df):
    """Extract and insert county FIPS codes."""
    logger.info("Inserting counties data")
    
    # Extract all unique FIPS codes
    unique_counties = df['FIPS'].unique()
    
    # Create county records with just FIPS codes initially
    county_records = [{'fips_code': fips} for fips in unique_counties]
    counties_df = pd.DataFrame(county_records)
    
    with DBManager.connection() as conn:
        conn.register('counties_temp', counties_df)
        conn.execute("""
            INSERT INTO counties (fips_code)
            SELECT fips_code FROM counties_temp
            WHERE NOT EXISTS (
                SELECT 1 FROM counties 
                WHERE fips_code = counties_temp.fips_code
            )
        """)
    
    logger.info(f"Inserted {len(unique_counties)} counties")
    return list(unique_counties)

def insert_landuse_types():
    """Insert land use categories."""
    logger.info("Inserting land use types")
    
    landuse_types = [
        {'landuse_type_code': 'cr', 'landuse_type_name': 'Cropland', 'description': 'Agricultural cropland'},
        {'landuse_type_code': 'ps', 'landuse_type_name': 'Pasture', 'description': 'Pasture land'},
        {'landuse_type_code': 'rg', 'landuse_type_name': 'Rangeland', 'description': 'Rangeland'},
        {'landuse_type_code': 'fr', 'landuse_type_name': 'Forest', 'description': 'Forest land'},
        {'landuse_type_code': 'ur', 'landuse_type_name': 'Urban', 'description': 'Urban developed land'},
    ]
    
    landuse_types_df = pd.DataFrame(landuse_types)
    
    with DBManager.connection() as conn:
        conn.register('landuse_types_temp', landuse_types_df)
        conn.execute("""
            INSERT INTO landuse_types 
            SELECT * FROM landuse_types_temp
            WHERE NOT EXISTS (
                SELECT 1 FROM landuse_types 
                WHERE landuse_type_code = landuse_types_temp.landuse_type_code
            )
        """)
    
    logger.info(f"Inserted {len(landuse_types)} land use types")

def process_transitions(df, scenario_map, decade_map):
    """Process and insert land use transition data from the DataFrame."""
    logger.info("Processing land use transitions")
    
    # We'll process batches of records for memory efficiency
    batch_size = 100000
    transition_id = 1
    total_transitions = 0
    unknown_landuse_types = set()
    
    # Prepare the needed columns for transitions
    transitions = []
    
    with DBManager.connection() as conn:
        # Process each row in the DataFrame
        for index, row in tqdm(df.iterrows(), total=len(df), desc="Processing transitions"):
            scenario_id = scenario_map[row['Scenario']]
            decade_id = decade_map[row['YearRange']]
            
            # Map the land use types from names to codes
            from_landuse = row['From']
            to_landuse = row['To']
            
            # Convert to database codes using the mapping
            from_code = LANDUSE_NAME_TO_CODE.get(from_landuse)
            to_code = LANDUSE_NAME_TO_CODE.get(to_landuse)
            
            # Skip records with unknown land use types
            if from_code is None:
                unknown_landuse_types.add(from_landuse)
                continue
            if to_code is None:
                unknown_landuse_types.add(to_landuse)
                continue
            
            transitions.append({
                'transition_id': transition_id,
                'scenario_id': scenario_id,
                'decade_id': decade_id,
                'fips_code': row['FIPS'],
                'from_landuse': from_code,
                'to_landuse': to_code,
                'area_hundreds_acres': row['Acres']
            })
            transition_id += 1
            
            # Insert batch if we've reached batch size
            if len(transitions) >= batch_size:
                transitions_df = pd.DataFrame(transitions)
                conn.register('transitions_temp', transitions_df)
                conn.execute("""
                    INSERT INTO landuse_change
                    SELECT * FROM transitions_temp
                """)
                total_transitions += len(transitions)
                transitions = []
                logger.info(f"Inserted batch - Total transitions: {total_transitions}")
        
        # Insert any remaining transitions
        if transitions:
            transitions_df = pd.DataFrame(transitions)
            conn.register('transitions_temp', transitions_df)
            conn.execute("""
                INSERT INTO landuse_change
                SELECT * FROM transitions_temp
            """)
            total_transitions += len(transitions)
            logger.info(f"Inserted batch - Total transitions: {total_transitions}")
    
    # Log any unknown land use types
    if unknown_landuse_types:
        logger.warning(f"Found {len(unknown_landuse_types)} unknown land use types: {unknown_landuse_types}")
    
    logger.info(f"Inserted {total_transitions} land use transitions in total")

def main():
    """Main function to import data."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Import land use data from Parquet into DuckDB")
    parser.add_argument('--input', type=str, default=DEFAULT_PARQUET_PATH,
                        help=f'Path to the input Parquet file (default: {DEFAULT_PARQUET_PATH})')
    args = parser.parse_args()
    
    parquet_path = args.input
    logger.info(f"Starting import of land use data from {parquet_path}")
    
    # Make sure the database is ready
    setup_database()
    
    # Load the Parquet data
    logger.info("Loading Parquet data")
    df = pd.read_parquet(parquet_path)
    logger.info(f"Loaded {len(df)} records from Parquet file")
    
    # Insert land use types
    insert_landuse_types()
    
    # Insert metadata
    scenario_map = insert_scenarios(df)
    decade_map = insert_decades(df)
    counties = insert_counties(df)
    
    # Process and insert the main transition data
    process_transitions(df, scenario_map, decade_map)
    
    # Optimize the database after import
    logger.info("Optimizing database")
    SchemaManager.optimize_database()
    
    logger.info("Data import complete!")

if __name__ == "__main__":
    main() 