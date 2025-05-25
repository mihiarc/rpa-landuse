#!/usr/bin/env python3
"""
Create semantic layers for RPA landuse data using PandasAI.

This script provides command-line functionality to create semantic layers 
for analyzing the RPA land use projection data.
"""

import os
import argparse
import sys
from rpa_landuse.pandasai.layers import extract_data_from_duckdb, create_semantic_layers


def main():
    """Main function to extract data and create semantic layers."""
    parser = argparse.ArgumentParser(description="Create semantic layers for RPA landuse data")
    parser.add_argument(
        "--db-path", 
        type=str, 
        default="data/database/rpa.db",
        help="Path to the DuckDB database file"
    )
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="semantic_layers/base_analysis",
        help="Directory to save Parquet files"
    )
    parser.add_argument(
        "--org-path", 
        type=str, 
        default="rpa-landuse",
        help="Organization path prefix for PandasAI datasets"
    )
    parser.add_argument(
        "--skip-extraction", 
        action="store_true",
        help="Skip data extraction and use existing Parquet files"
    )
    parser.add_argument(
        "--scenario-ids",
        type=int,
        nargs="+",
        default=[21, 22, 23, 24, 25],
        help="List of scenario IDs to include (default: 21-25, ensemble mean and RPA integrated scenarios)"
    )
    parser.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Process all scenarios instead of only the default ensemble and RPA scenarios"
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Extract data from DuckDB if not skipped
    if not args.skip_extraction:
        print("Extracting data from DuckDB...")
        
        # Determine scenario IDs to use
        scenario_ids = None if args.all_scenarios else args.scenario_ids
        if scenario_ids:
            print(f"Processing only scenarios {scenario_ids} (ensemble mean and RPA integrated scenarios)")
        
        output_files = extract_data_from_duckdb(
            db_path=args.db_path,
            output_dir=args.output_dir,
            scenario_ids=scenario_ids
        )
        print(f"Data extracted to {args.output_dir}/")
    else:
        print(f"Skipping data extraction, using existing files in {args.output_dir}/")
    
    # Create semantic layers
    print("Creating semantic layers...")
    try:
        datasets = create_semantic_layers(
            parquet_dir=args.output_dir,
            org_path=args.org_path
        )
        print("Semantic layers created successfully!")
        print(f"Created the following datasets:")
        for name in datasets.keys():
            print(f"- {name}")
    except Exception as e:
        print(f"Error creating semantic layers: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 