#!/usr/bin/env python3
"""
Add ensemble scenarios to the RPA Land Use database.

This script creates ensemble scenarios by aggregating different sets of scenarios:
1. All scenarios ensemble: Mean of all 20 scenarios
2. RPA integrated scenarios (LM, HL, HM, HH): Mean of the 5 climate GCMs for each integrated scenario

Usage:
    python -m src.db.add_ensemble_scenario [--all] [--integrated] [--overall]

Options:
    --all         Create all ensemble scenarios (both overall and integrated)
    --integrated  Create the four integrated RPA scenario ensembles (LM, HL, HM, HH)
    --overall     Create the overall mean ensemble across all scenarios (default if no args provided)
"""

import os
import sys
import logging
import argparse
from pathlib import Path
import pandas as pd
from tqdm import tqdm

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
logger = logging.getLogger("ensemble-scenario-creator")

# Define RPA integrated scenarios and their mapping to RCP-SSP combinations
RPA_INTEGRATED_SCENARIOS = {
    'LM': {'rcp': 'rcp45', 'ssp': 'ssp1', 'description': 'Lower warming-moderate U.S. growth (RCP4.5-SSP1)'},
    'HL': {'rcp': 'rcp85', 'ssp': 'ssp3', 'description': 'High warming-low U.S. growth (RCP8.5-SSP3)'},
    'HM': {'rcp': 'rcp85', 'ssp': 'ssp2', 'description': 'High warming-moderate U.S. growth (RCP8.5-SSP2)'},
    'HH': {'rcp': 'rcp85', 'ssp': 'ssp5', 'description': 'High warming-high U.S. growth (RCP8.5-SSP5)'}
}

def check_if_ensemble_exists(scenario_name):
    """Check if an ensemble scenario already exists with the given name."""
    query = f"SELECT scenario_id FROM scenarios WHERE scenario_name = '{scenario_name}'"
    result = DBManager.query_df(query)
    
    if not result.empty:
        # Convert numpy.int32 to Python int to avoid DuckDB type errors
        scenario_id = int(result['scenario_id'].iloc[0])
        logger.info(f"Ensemble scenario '{scenario_name}' already exists with ID: {scenario_id}")
        return scenario_id
    
    return None

def delete_ensemble_scenario(scenario_id):
    """Delete an existing ensemble scenario."""
    # Convert numpy.int32 to Python int to avoid DuckDB type error
    scenario_id = int(scenario_id)
    
    logger.info(f"Deleting ensemble scenario with ID: {scenario_id}")
    with DBManager.connection() as conn:
        conn.execute("DELETE FROM landuse_change WHERE scenario_id = ?", [scenario_id])
        conn.execute("DELETE FROM scenarios WHERE scenario_id = ?", [scenario_id])

def get_all_scenarios():
    """Get all existing scenarios from the database."""
    query = "SELECT scenario_id, scenario_name, gcm, rcp, ssp FROM scenarios"
    return DBManager.query_df(query)

def get_next_scenario_id():
    """Get the next available scenario ID."""
    query = "SELECT MAX(scenario_id) + 1 AS next_id FROM scenarios"
    result = DBManager.query_df(query)
    return int(result['next_id'].iloc[0])  # Convert numpy.int32 to Python int

def create_ensemble_scenario(scenario_name, gcm, rcp, ssp, description):
    """Create a new scenario record for an ensemble scenario."""
    # Get the next available scenario ID
    ensemble_id = get_next_scenario_id()
    
    # Insert the new scenario
    insert_query = """
    INSERT INTO scenarios (scenario_id, scenario_name, gcm, rcp, ssp, description)
    VALUES (?, ?, ?, ?, ?, ?)
    """
    
    with DBManager.connection() as conn:
        conn.execute(insert_query, [ensemble_id, scenario_name, gcm, rcp, ssp, description])
    
    logger.info(f"Created new ensemble scenario '{scenario_name}' with ID: {ensemble_id}")
    return ensemble_id

def get_all_time_steps():
    """Get all time steps (decades) from the database."""
    query = "SELECT decade_id FROM decades ORDER BY decade_id"
    return DBManager.query_df(query)['decade_id'].tolist()

def calculate_and_insert_ensemble_transitions(ensemble_id, scenario_ids, batch_size=50000):
    """Calculate and insert the ensemble transitions for a given set of scenario IDs."""
    if not scenario_ids:
        logger.warning("No scenarios found to average. Skipping.")
        return 0
    
    logger.info(f"Calculating and inserting ensemble transitions for {len(scenario_ids)} scenarios")
    
    # Get all time steps (decades)
    time_steps = get_all_time_steps()
    
    # Get the current max transition ID to start incrementing from
    max_id_query = "SELECT MAX(transition_id) + 1 AS next_id FROM landuse_change"
    max_id_result = DBManager.query_df(max_id_query)
    next_transition_id = int(max_id_result['next_id'].iloc[0]) if not max_id_result['next_id'].isnull().iloc[0] else 1
    
    total_inserted = 0
    
    # Process each time step (decade) separately to manage memory
    for decade_id in tqdm(time_steps, desc="Processing decades"):
        logger.info(f"Processing decade ID: {decade_id}")
        
        # Query to calculate the mean transitions for this decade
        ensemble_query = f"""
        SELECT 
            decade_id,
            fips_code,
            from_landuse,
            to_landuse,
            AVG(area_hundreds_acres) AS area_hundreds_acres
        FROM 
            landuse_change
        WHERE 
            scenario_id IN ({','.join([str(id) for id in scenario_ids])})
            AND decade_id = {decade_id}
        GROUP BY 
            decade_id, fips_code, from_landuse, to_landuse
        """
        
        # Get the ensemble data for this decade
        ensemble_df = DBManager.query_df(ensemble_query)
        
        if ensemble_df.empty:
            logger.warning(f"No data found for decade {decade_id}")
            continue
        
        # Add the ensemble scenario ID and transition IDs
        ensemble_df['scenario_id'] = ensemble_id
        ensemble_df['transition_id'] = range(next_transition_id, next_transition_id + len(ensemble_df))
        next_transition_id += len(ensemble_df)
        
        # Process in batches to avoid memory issues
        for start_idx in range(0, len(ensemble_df), batch_size):
            end_idx = min(start_idx + batch_size, len(ensemble_df))
            batch_df = ensemble_df.iloc[start_idx:end_idx]
            
            # Insert the batch
            with DBManager.connection() as conn:
                conn.register('ensemble_batch', batch_df)
                conn.execute("""
                    INSERT INTO landuse_change
                    SELECT 
                        transition_id, scenario_id, decade_id, 
                        fips_code, from_landuse, to_landuse, area_hundreds_acres
                    FROM 
                        ensemble_batch
                """)
            
            total_inserted += len(batch_df)
            logger.info(f"Inserted batch of {len(batch_df)} rows. Total: {total_inserted}")
    
    logger.info(f"Successfully inserted {total_inserted} ensemble transitions")
    return total_inserted

def create_overall_ensemble(force=False):
    """Create an ensemble scenario that averages all scenarios."""
    scenario_name = "ensemble_overall"
    description = "Mean of all scenarios (overall ensemble)"
    
    logger.info("Creating overall ensemble scenario (mean of all scenarios)")
    
    # Check if this ensemble already exists
    existing_id = check_if_ensemble_exists(scenario_name)
    if existing_id is not None:
        if not force:
            response = input(f"Overall ensemble scenario already exists with ID {existing_id}. Delete and recreate? (y/n): ")
            if response.lower() != 'y':
                logger.info("Skipping overall ensemble creation")
                return
        
        # Delete existing ensemble scenario data
        delete_ensemble_scenario(existing_id)
    
    # Get all scenarios (excluding any existing ensembles)
    scenarios_df = get_all_scenarios()
    scenarios_df = scenarios_df[~scenarios_df['scenario_name'].str.contains('ensemble')]
    
    scenario_ids = scenarios_df['scenario_id'].tolist()
    logger.info(f"Found {len(scenario_ids)} scenarios to average for overall ensemble")
    
    # Create the new ensemble scenario
    ensemble_id = create_ensemble_scenario(
        scenario_name=scenario_name,
        gcm="ensemble",
        rcp="ensemble", 
        ssp="ensemble",
        description=description
    )
    
    # Calculate and insert the ensemble transitions
    calculate_and_insert_ensemble_transitions(ensemble_id, scenario_ids)
    
    return ensemble_id

def create_integrated_ensembles(force=False):
    """Create ensemble scenarios for each RPA integrated scenario."""
    logger.info("Creating integrated RPA ensemble scenarios")
    
    # Get all scenarios (excluding any existing ensembles)
    scenarios_df = get_all_scenarios()
    scenarios_df = scenarios_df[~scenarios_df['scenario_name'].str.contains('ensemble')]
    
    created_ids = []
    
    # Create an ensemble for each RPA integrated scenario
    for rpa_code, info in RPA_INTEGRATED_SCENARIOS.items():
        scenario_name = f"ensemble_{rpa_code}"
        description = f"Mean of {rpa_code} scenarios ({info['description']})"
        
        logger.info(f"Processing {rpa_code} integrated scenario")
        
        # Check if this ensemble already exists
        existing_id = check_if_ensemble_exists(scenario_name)
        if existing_id is not None:
            if not force:
                response = input(f"{rpa_code} ensemble scenario already exists with ID {existing_id}. Delete and recreate? (y/n): ")
                if response.lower() != 'y':
                    logger.info(f"Skipping {rpa_code} ensemble creation")
                    continue
            
            # Delete existing ensemble scenario data
            delete_ensemble_scenario(existing_id)
        
        # Filter scenarios matching this RPA integrated scenario (by RCP and SSP)
        matching_scenarios = scenarios_df[
            (scenarios_df['rcp'] == info['rcp']) & 
            (scenarios_df['ssp'] == info['ssp'])
        ]
        
        scenario_ids = matching_scenarios['scenario_id'].tolist()
        logger.info(f"Found {len(scenario_ids)} scenarios for {rpa_code} ensemble")
        
        if not scenario_ids:
            logger.warning(f"No scenarios found for {rpa_code} (rcp={info['rcp']}, ssp={info['ssp']})")
            continue
        
        # Create the new ensemble scenario
        ensemble_id = create_ensemble_scenario(
            scenario_name=scenario_name,
            gcm="ensemble",
            rcp=info['rcp'],
            ssp=info['ssp'],
            description=description
        )
        
        # Calculate and insert the ensemble transitions
        calculate_and_insert_ensemble_transitions(ensemble_id, scenario_ids)
        created_ids.append(ensemble_id)
    
    return created_ids

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Create ensemble scenarios in the RPA database")
    parser.add_argument("--all", action="store_true", help="Create all ensemble scenarios")
    parser.add_argument("--integrated", action="store_true", help="Create integrated RPA scenario ensembles")
    parser.add_argument("--overall", action="store_true", help="Create overall ensemble (all scenarios)")
    parser.add_argument("--force", action="store_true", help="Force recreation without confirmation")
    args = parser.parse_args()
    
    # Default to overall if no specific option is provided
    if not (args.all or args.integrated or args.overall):
        args.overall = True
    
    return args

def main():
    """Main function to create ensemble scenarios."""
    logger.info("Starting creation of ensemble scenarios")
    
    args = parse_args()
    
    created_ids = []
    
    if args.all or args.overall:
        overall_id = create_overall_ensemble(force=args.force)
        if overall_id:
            created_ids.append(overall_id)
    
    if args.all or args.integrated:
        integrated_ids = create_integrated_ensembles(force=args.force)
        created_ids.extend(integrated_ids)
    
    # Optimize the database after import
    if created_ids:
        logger.info("Optimizing database")
        SchemaManager.optimize_database()
        
        logger.info(f"Successfully created {len(created_ids)} ensemble scenarios")
        logger.info("To view an ensemble scenario, use: python query_db.py transitions --scenario <id> --decade 1")
    else:
        logger.info("No ensemble scenarios were created")

if __name__ == "__main__":
    main() 