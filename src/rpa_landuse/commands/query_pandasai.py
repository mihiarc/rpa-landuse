#!/usr/bin/env python3
"""
PandasAI Query Tool for RPA Land Use Data.

This script provides a command-line interface for querying the RPA land use
data with natural language using PandasAI.
"""

import sys
import argparse
import json
import pandas as pd
from rpa_landuse.pandasai.query import (
    query_transitions,
    query_to_urban,
    query_from_forest,
    query_county_transitions,
    query_county_to_urban,
    query_county_from_forest,
    query_urbanization_trends,
    multi_dataset_query
)


def display_result(result, output_format='pretty'):
    """
    Display query result in the specified format.
    
    Args:
        result: Result from PandasAI query
        output_format: Format to display (pretty, json, csv)
    """
    if isinstance(result, pd.DataFrame):
        if output_format == 'json':
            print(result.to_json(orient='records', indent=2))
        elif output_format == 'csv':
            print(result.to_csv(index=False))
        else:  # pretty
            print(result.to_string(index=False))
    elif isinstance(result, dict):
        # For multi-dataset queries
        if output_format == 'json':
            # Convert DataFrame values to JSON
            json_result = {}
            for key, value in result.items():
                if isinstance(value, pd.DataFrame):
                    json_result[key] = json.loads(value.to_json(orient='records'))
                else:
                    json_result[key] = value
            print(json.dumps(json_result, indent=2))
        else:
            for dataset, res in result.items():
                print(f"\n=== Results from {dataset} ===")
                if isinstance(res, pd.DataFrame):
                    if output_format == 'csv':
                        print(res.to_csv(index=False))
                    else:  # pretty
                        print(res.to_string(index=False))
                else:
                    print(res)
    else:
        # For string or other results
        print(result)


def main():
    """Main function to run the PandasAI query tool."""
    parser = argparse.ArgumentParser(description="RPA Land Use PandasAI Query Tool")
    
    parser.add_argument(
        "--dataset",
        choices=[
            "transitions",
            "to_urban",
            "from_forest",
            "county",
            "county_to_urban",
            "county_from_forest",
            "urbanization",
            "all"
        ],
        default="transitions",
        help="Dataset to query (default: transitions)"
    )
    
    parser.add_argument(
        "--data-dir",
        default="semantic_layers/base_analysis",
        help="Directory containing Parquet files (default: semantic_layers/base_analysis)"
    )
    
    parser.add_argument(
        "--format",
        choices=["pretty", "json", "csv"],
        default="pretty",
        help="Output format (default: pretty)"
    )
    
    parser.add_argument(
        "query",
        help="Natural language query to execute"
    )
    
    args = parser.parse_args()
    
    try:
        # Determine which dataset to query
        if args.dataset == "all":
            result = multi_dataset_query(
                query=args.query,
                parquet_dir=args.data_dir
            )
        elif args.dataset == "transitions":
            result = query_transitions(
                query=args.query,
                parquet_dir=args.data_dir
            )
        elif args.dataset == "to_urban":
            result = query_to_urban(
                query=args.query,
                parquet_dir=args.data_dir
            )
        elif args.dataset == "from_forest":
            result = query_from_forest(
                query=args.query,
                parquet_dir=args.data_dir
            )
        elif args.dataset == "county":
            result = query_county_transitions(
                query=args.query,
                parquet_dir=args.data_dir
            )
        elif args.dataset == "county_to_urban":
            result = query_county_to_urban(
                query=args.query,
                parquet_dir=args.data_dir
            )
        elif args.dataset == "county_from_forest":
            result = query_county_from_forest(
                query=args.query,
                parquet_dir=args.data_dir
            )
        elif args.dataset == "urbanization":
            result = query_urbanization_trends(
                query=args.query,
                parquet_dir=args.data_dir
            )
            
        # Display the result
        display_result(result, args.format)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main()) 