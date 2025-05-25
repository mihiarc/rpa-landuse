#!/usr/bin/env python3
"""
Script to update the counties table with state, region, and subregion information.

This script uses the state_fips_mapping.py file and regions.yml to populate 
the state_name, region, and subregion fields in the counties table.
"""

import logging
import sys
import yaml
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# Import from database module
from src.db.database import DBManager

# Handle imports for both direct execution and module import
try:
    # When imported as a module
    from .state_fips_mapping import STATE_FIPS, STATE_TO_REGION, parse_fips
except ImportError:
    # When run directly
    from src.utils.state_fips_mapping import STATE_FIPS, STATE_TO_REGION, parse_fips

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("counties-updater")

def load_rpa_regions():
    """
    Load RPA regions and subregions from the YAML config file.
    
    Returns:
        Dict mapping states to tuples of (region, subregion)
    """
    logger.info("Loading RPA regions from YAML config")
    config_path = Path(__file__).resolve().parent.parent.parent / "cfg" / "regions.yml"
    
    if not config_path.exists():
        logger.error(f"Regions config file not found at {config_path}")
        return {}
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Create a mapping of state to (region, subregion)
    state_to_region_subregion = {}
    
    # Process the hierarchical structure
    regions_data = config.get('RPA_Assessment_Regions', {})
    for major_region, subregions in regions_data.items():
        # Clean up region name (remove _Region suffix and replace underscores with spaces)
        clean_region = major_region.replace('_Region', '').replace('_', ' ')
        
        for subregion, states in subregions.items():
            # Clean up subregion name (replace underscores with spaces)
            clean_subregion = subregion.replace('_', ' ')
            
            for state in states:
                state_to_region_subregion[state] = (clean_region, clean_subregion)
    
    logger.info(f"Loaded mapping for {len(state_to_region_subregion)} states")
    return state_to_region_subregion

def update_counties_with_state_info():
    """
    Update counties table with state names from FIPS codes.
    """
    logger.info("Updating counties with state information")
    
    # Load RPA regions from YAML
    rpa_regions = load_rpa_regions()
    
    # Ensure the counties table has a subregion column
    with DBManager.connection() as conn:
        # Check if subregion column exists, if not add it
        check_query = """
        SELECT * FROM counties LIMIT 1
        """
        column_info = conn.execute(check_query).description
        column_names = [col[0].lower() for col in column_info]
        
        if 'subregion' not in column_names:
            logger.info("Adding subregion column to counties table")
            conn.execute("ALTER TABLE counties ADD COLUMN subregion TEXT")
    
    # Now get all counties that need updating
    query = """
    SELECT 
        fips_code,
        state_name
    FROM 
        counties
    """
    
    with DBManager.connection() as conn:
        counties = conn.execute(query).fetchall()
        
        # Process each county
        updated_count = 0
        for county in counties:
            fips_code = county[0]
            existing_state = county[1]
            
            state_fips, _ = parse_fips(fips_code)
            
            if state_fips and state_fips in STATE_FIPS:
                state_name = STATE_FIPS[state_fips]
                
                # Try to get region and subregion from YAML config
                region, subregion = None, None
                if state_name in rpa_regions:
                    region, subregion = rpa_regions[state_name]
                else:
                    # Fall back to the basic region from STATE_TO_REGION
                    region = STATE_TO_REGION.get(state_name)
                
                # Update the county record
                update_query = """
                UPDATE counties
                SET 
                    state_name = ?,
                    state_fips = ?,
                    region = ?,
                    subregion = ?
                WHERE 
                    fips_code = ?
                """
                
                conn.execute(update_query, [state_name, state_fips, region, subregion, fips_code])
                updated_count += 1
        
        logger.info(f"Updated {updated_count} counties with state, region, and subregion information")
        
        # Get some stats about the update
        stats_query = """
        SELECT 
            region, 
            subregion, 
            COUNT(*) as count
        FROM 
            counties
        WHERE 
            region IS NOT NULL
        GROUP BY 
            region, 
            subregion
        ORDER BY 
            region, 
            subregion
        """
        
        stats = conn.execute(stats_query).fetchall()
        logger.info("County distribution by region and subregion:")
        for region, subregion, count in stats:
            subregion_str = subregion if subregion else "Unspecified"
            logger.info(f"  {region} - {subregion_str}: {count} counties")

def main():
    """Main function."""
    logger.info("Starting counties table update")
    
    try:
        update_counties_with_state_info()
        logger.info("Counties table update completed successfully")
    except Exception as e:
        logger.error(f"Error updating counties table: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main() 