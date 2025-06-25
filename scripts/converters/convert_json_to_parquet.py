"""
Simplified converter for RPA land use data.
Converts JSON format to Parquet format with basic validation.
"""

import json
import logging
from pathlib import Path

import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def convert_json_to_parquet(json_file, output_file):
    """
    Convert RPA land use data from JSON to Parquet format.

    Args:
        json_file (str): Path to input JSON file
        output_file (str): Path to output Parquet file

    Returns:
        dict: Statistics about the conversion
    """
    try:
        # Create output directory if it doesn't exist
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)

        # Load JSON data
        logger.info(f"Loading JSON file from {json_file}...")
        with open(json_file) as f:
            data = json.load(f)
        logger.info("Data structure loaded successfully")

        # Convert to DataFrame
        logger.info("Converting to DataFrame...")
        df = _convert_to_dataframe(data)

        # Save to Parquet
        logger.info(f"Saving to {output_file}...")
        df.to_parquet(output_file, index=False)

        # Generate statistics
        stats = {
            "record_count": len(df),
            "file_size_mb": Path(output_file).stat().st_size / (1024*1024),
            "unique_scenarios": df['Scenario'].nunique(),
            "unique_counties": df['FIPS'].nunique(),
            "unique_years": sorted(df['Year'].unique()),
            "total_acres": df['Acres'].sum()
        }

        logger.info(f"Conversion complete: {stats['record_count']} records saved")
        logger.info(f"File size: {stats['file_size_mb']:.2f} MB")

        return stats

    except Exception as e:
        logger.error(f"Error converting data: {str(e)}")
        raise

def _extract_end_year(year_range):
    """Extract the end year from a year range string (e.g., '2012-2020' -> 2020)."""
    return int(year_range.split('-')[1])

def _convert_matrix_to_df(matrix_data):
    """Convert the matrix data to a DataFrame in long format."""
    # Create mapping for column and row names
    land_use_map = {
        'cr': 'Crop',
        'ps': 'Pasture',
        'rg': 'Range',
        'fr': 'Forest',
        'ur': 'Urban',
        't1': 'Total',  # Total row sum
        't2': 'Total'   # Total column sum
    }

    rows = []
    for row in matrix_data:
        from_type = land_use_map[row['_row']]
        if from_type != 'Total':  # Skip the total row
            for col, value in row.items():
                if col != '_row' and col != 't1':  # Skip the row identifier and total
                    to_type = land_use_map[col]
                    if to_type != 'Total' and float(value) > 0:  # Skip total column and zero values
                        rows.append({
                            'From': from_type,
                            'To': to_type,
                            'Acres': float(value)
                        })

    return pd.DataFrame(rows)

def _convert_to_dataframe(data):
    """Convert nested JSON structure to a pandas DataFrame."""
    all_data = []

    # Iterate through the nested structure
    for scenario_name, scenario_data in data.items():
        logger.info(f"Processing scenario: {scenario_name}")

        for year_range, year_data in scenario_data.items():
            year = _extract_end_year(year_range)
            logger.info(f"  Year range: {year_range} (end year: {year})")

            county_count = 0
            for fips, county_data in year_data.items():
                # Convert the matrix data to a DataFrame
                df = _convert_matrix_to_df(county_data)

                # Add metadata columns
                df['Scenario'] = scenario_name
                df['Year'] = year
                df['YearRange'] = year_range
                df['FIPS'] = fips

                all_data.append(df)
                county_count += 1

            logger.info(f"  Processed {county_count} counties")

    # Combine all data into a single DataFrame
    logger.info("Concatenating all data...")
    final_df = pd.concat(all_data, ignore_index=True)

    return final_df

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Convert RPA land use data from JSON to Parquet format.')
    parser.add_argument('--input', default='data/raw/county_landuse_projections_RPA.json',
                      help='Input JSON file path')
    parser.add_argument('--output', default='data/processed/rpa_landuse_data.parquet',
                      help='Output Parquet file path')
    args = parser.parse_args()

    stats = convert_json_to_parquet(args.input, args.output)

    print("\nConversion Statistics:")
    print(f"Records: {stats['record_count']:,}")
    print(f"File size: {stats['file_size_mb']:.2f} MB")
    print(f"Scenarios: {stats['unique_scenarios']}")
    print(f"Counties: {stats['unique_counties']}")
    print(f"Years: {stats['unique_years']}")
    print(f"Total acres: {stats['total_acres']:,.2f}")
