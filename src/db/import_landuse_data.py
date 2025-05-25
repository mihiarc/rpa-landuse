#!/usr/bin/env python3
"""
Import the county land use projections data from JSON into DuckDB.

This script:
1. Reads the large JSON file with land use projections
2. Transforms the data into a normalized relational structure
3. Loads it into the DuckDB database
"""

import os
import sys
import json
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
logger = logging.getLogger("data-import")

# Default JSON data path
DEFAULT_JSON_PATH = "data/raw/county_landuse_projections_RPA.json"

def setup_database():
    """Ensure database is initialized before importing data."""
    SchemaManager.initialize_database()
    SchemaManager.ensure_indexes()

def insert_scenarios(json_data):
    """Extract and insert scenario data from the JSON."""
    logger.info("Inserting scenarios data")
    scenarios = []
    
    scenario_id = 1
    for scenario_name in json_data.keys():
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

def insert_time_steps(json_data):
    """Extract and insert time step data."""
    logger.info("Inserting time steps data")
    time_steps = []
    
    time_step_id = 1
    # Get all unique time steps from the JSON
    all_time_steps = set()
    for scenario_data in json_data.values():
        all_time_steps.update(scenario_data.keys())
    
    for time_step_name in sorted(all_time_steps):
        # Parse years from format like "2012-2020"
        try:
            start_year, end_year = map(int, time_step_name.split('-'))
            time_steps.append({
                'time_step_id': time_step_id,
                'time_step_name': time_step_name,
                'start_year': start_year,
                'end_year': end_year
            })
            time_step_id += 1
        except ValueError:
            logger.warning(f"Could not parse time step: {time_step_name}")
    
    # Convert to DataFrame and insert
    time_steps_df = pd.DataFrame(time_steps)
    
    with DBManager.connection() as conn:
        conn.register('time_steps_temp', time_steps_df)
        conn.execute("""
            INSERT INTO time_steps 
            SELECT * FROM time_steps_temp
            WHERE NOT EXISTS (
                SELECT 1 FROM time_steps 
                WHERE time_step_name = time_steps_temp.time_step_name
            )
        """)
    
    logger.info(f"Inserted {len(time_steps)} time steps")
    return {ts['time_step_name']: ts['time_step_id'] for ts in time_steps}

def insert_counties(json_data):
    """Extract and insert county FIPS codes."""
    logger.info("Inserting counties data")
    counties = set()
    
    # Extract all unique FIPS codes
    for scenario_data in json_data.values():
        for time_step_data in scenario_data.values():
            counties.update(time_step_data.keys())
    
    # Create county records with just FIPS codes initially
    county_records = [{'fips_code': fips} for fips in counties]
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
    
    logger.info(f"Inserted {len(counties)} counties")
    return list(counties)

def process_transitions(json_data, scenario_map, time_step_map, counties):
    """Process and insert land use transition data."""
    logger.info("Processing land use transitions")
    
    # We'll process batches of records for memory efficiency
    batch_size = 100000
    transition_id = 1
    total_transitions = 0
    
    with DBManager.connection() as conn:
        # For each scenario
        for scenario_name, scenario_data in tqdm(json_data.items(), desc="Scenarios"):
            scenario_id = scenario_map[scenario_name]
            
            # For each time step
            for time_step_name, time_step_data in tqdm(scenario_data.items(), 
                                                      desc=f"Time steps in {scenario_name}", 
                                                      leave=False):
                time_step_id = time_step_map[time_step_name]
                transitions = []
                
                # For each county
                for fips_code, county_data in time_step_data.items():
                    # Process each row in the transition matrix
                    for row_data in county_data:
                        from_land_use = row_data.get('_row')
                        if not from_land_use:
                            continue
                            
                        # Extract transitions to each land use type
                        for to_land_use in ['cr', 'ps', 'rg', 'fr', 'ur']:
                            area = row_data.get(to_land_use, 0)
                            if area > 0:
                                transitions.append({
                                    'transition_id': transition_id,
                                    'scenario_id': scenario_id,
                                    'time_step_id': time_step_id,
                                    'fips_code': fips_code,
                                    'from_land_use': from_land_use,
                                    'to_land_use': to_land_use,
                                    'area_hundreds_acres': area
                                })
                                transition_id += 1
                    
                    # Insert batch if we've reached batch size
                    if len(transitions) >= batch_size:
                        transitions_df = pd.DataFrame(transitions)
                        conn.register('transitions_temp', transitions_df)
                        conn.execute("""
                            INSERT INTO land_use_transitions 
                            SELECT * FROM transitions_temp
                        """)
                        total_transitions += len(transitions)
                        transitions = []
                        logger.info(f"Inserted batch - Total transitions: {total_transitions}")
                
                # Insert any remaining transitions for this time step
                if transitions:
                    transitions_df = pd.DataFrame(transitions)
                    conn.register('transitions_temp', transitions_df)
                    conn.execute("""
                        INSERT INTO land_use_transitions 
                        SELECT * FROM transitions_temp
                    """)
                    total_transitions += len(transitions)
                    logger.info(f"Inserted batch - Total transitions: {total_transitions}")
    
    logger.info(f"Inserted {total_transitions} land use transitions in total")

def main():
    """Main function to import data."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Import land use data from JSON into DuckDB")
    parser.add_argument('--input', type=str, default=DEFAULT_JSON_PATH,
                        help=f'Path to the input JSON file (default: {DEFAULT_JSON_PATH})')
    args = parser.parse_args()
    
    json_path = args.input
    logger.info(f"Starting import of land use data from {json_path}")
    
    # Make sure the database is ready
    setup_database()
    
    # Load the JSON data
    logger.info("Loading JSON data (this may take a while for large files)")
    with open(json_path, 'r') as f:
        json_data = json.load(f)
    
    # Insert metadata
    scenario_map = insert_scenarios(json_data)
    time_step_map = insert_time_steps(json_data)
    counties = insert_counties(json_data)
    
    # Process and insert the main transition data
    process_transitions(json_data, scenario_map, time_step_map, counties)
    
    # Optimize the database after import
    logger.info("Optimizing database")
    SchemaManager.optimize_database()
    
    logger.info("Data import complete!")

if __name__ == "__main__":
    main() 