"""
Update county names and state information in the database based on FIPS codes.

This script fetches county information from the US Census API and updates
the counties table in the DuckDB database.
"""

import sys
import os
import requests
import pandas as pd
import duckdb
import logging
from pathlib import Path
from tqdm import tqdm

# Add the src directory to the Python path
src_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(src_dir.parent))

# Using a relative import when run as a module
try:
    from utils.state_fips_mapping import STATE_FIPS, get_region_from_state
except ImportError:
    # For when script is run directly
    from src.utils.state_fips_mapping import STATE_FIPS, get_region_from_state

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default database path
DB_PATH = Path(src_dir).parent / "data" / "database" / "rpa.db"

def fetch_county_data():
    """
    Fetch county data from the US Census API.
    
    Returns:
        DataFrame with county data
    """
    logger.info("Fetching county data from Census API")
    try:
        # Using the Census API to get county names (2020 Census - Geography)
        url = "https://api.census.gov/data/2020/dec/pl?get=NAME&for=county:*"
        response = requests.get(url)
        response.raise_for_status()
        
        # Convert JSON response to DataFrame
        data = response.json()
        columns = data[0]
        rows = data[1:]
        
        df = pd.DataFrame(rows, columns=columns)
        
        # Create FIPS code by combining state and county codes
        df['fips_code'] = df['state'] + df['county']
        
        # Extract county name from NAME field (format: "County Name, State Name")
        df['county_name'] = df['NAME'].apply(lambda x: x.split(',')[0])
        
        # Extract state name from NAME field when available (format: "County Name, State Name")
        def extract_state_name(name_field):
            parts = name_field.split(',')
            if len(parts) > 1:
                return parts[1].strip()
            return None
            
        df['state_name_from_api'] = df['NAME'].apply(extract_state_name)
        
        # Add state_name based on state FIPS code
        df['state_name'] = df.apply(
            lambda row: STATE_FIPS.get(row['state']) or row['state_name_from_api'], 
            axis=1
        )
        
        # Add region based on state name
        df['region'] = df['state_name'].apply(lambda x: get_region_from_state(x))
        
        # Select only needed columns
        result = df[['fips_code', 'county_name', 'state_name', 'state', 'region']]
        result = result.rename(columns={'state': 'state_fips'})
        
        logger.info(f"Retrieved {len(result)} counties")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching county data: {e}")
        return pd.DataFrame()


def update_county_names_in_db(db_path=DB_PATH):
    """
    Update county names in the database.
    
    Args:
        db_path: Path to the DuckDB database
    """
    # Fetch county data
    county_data = fetch_county_data()
    if county_data.empty:
        logger.error("Failed to fetch county data. Exiting.")
        return
    
    try:
        # Connect to database
        conn = duckdb.connect(str(db_path))
        
        # Check if counties table exists
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='counties'"
        ).fetchone()
        
        if not table_exists:
            logger.error("Counties table does not exist in database")
            conn.close()
            return
        
        # Count counties that need updating
        count_missing = conn.execute("""
        SELECT COUNT(*) 
        FROM counties 
        WHERE county_name IS NULL OR state_name IS NULL
        """).fetchone()[0]
        
        logger.info(f"Found {count_missing} counties that need updating")
        
        # Create a temporary table with the county data
        logger.info("Creating temporary table with Census data")
        conn.register("census_counties", county_data)
        conn.execute("DROP TABLE IF EXISTS temp_census_counties")
        conn.execute("""
        CREATE TABLE temp_census_counties AS 
        SELECT * FROM census_counties
        """)
        
        # Get the list of FIPS codes
        fips_codes = conn.execute("SELECT DISTINCT fips_code FROM counties").fetchdf()
        
        # Apply state names based on FIPS code
        logger.info("Updating state names based on FIPS codes")
        for _, row in tqdm(fips_codes.iterrows(), total=len(fips_codes), desc="Updating state names"):
            fips = row['fips_code']
            if fips and len(fips) >= 2:
                state_fips = fips[:2]
                state_name = STATE_FIPS.get(state_fips)
                if state_name:
                    region = get_region_from_state(state_name)
                    conn.execute("""
                    UPDATE counties
                    SET 
                        state_name = ?,
                        state_fips = ?,
                        region = ?
                    WHERE fips_code = ?
                    """, [state_name, state_fips, region, fips])
        
        # Now update county names with data from Census
        logger.info("Updating county names from Census API data")
        for _, row in tqdm(county_data.iterrows(), total=len(county_data), desc="Updating counties"):
            conn.execute("""
            UPDATE counties 
            SET county_name = ?
            WHERE fips_code = ? AND (county_name IS NULL OR county_name LIKE 'County%')
            """, [row['county_name'], row['fips_code']])
        
        # Check for any remaining counties without names
        still_missing = conn.execute("""
        SELECT COUNT(*) 
        FROM counties 
        WHERE county_name IS NULL OR state_name IS NULL
        """).fetchone()[0]
        
        logger.info(f"Updated county names. {still_missing} counties still missing information.")
        
        # Show some example updated counties
        logger.info("Sample of updated counties:")
        sample = conn.execute("""
        SELECT fips_code, county_name, state_name, region 
        FROM counties 
        WHERE county_name IS NOT NULL AND state_name IS NOT NULL
        LIMIT 5
        """).fetchdf()
        for _, row in sample.iterrows():
            logger.info(f"{row['fips_code']}: {row['county_name']}, {row['state_name']} ({row['region']})")
        
        conn.close()
        logger.info("County update completed successfully")
        
    except Exception as e:
        logger.error(f"Error updating county names: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
def main():
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Update county names in the database")
    parser.add_argument(
        "--db", 
        default=str(DB_PATH), 
        help="Path to DuckDB database file"
    )
    args = parser.parse_args()
    
    update_county_names_in_db(args.db)

if __name__ == "__main__":
    main() 