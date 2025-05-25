#!/usr/bin/env python3
"""
Urban Development Analysis Tool

This module provides command-line tools for analyzing urban development rates
from the RPA land use data.
"""

import pandas as pd
import argparse
import sys
from pathlib import Path


def load_urban_data(data_path="semantic_layers/base_analysis"):
    """Load urban development data from parquet files."""
    try:
        county_transitions = pd.read_parquet(
            Path(data_path) / "county_transitions.parquet"
        )
        # Filter for urban transitions only
        urban_data = county_transitions[county_transitions["to_category"] == "Urban"]
        return urban_data
    except FileNotFoundError as e:
        print(f"Error: Could not find data files in {data_path}")
        print("Make sure you're running from the project root directory")
        sys.exit(1)


def analyze_urban_development(data, scenario=None, decade=None, level="county", top_n=10):
    """
    Analyze urban development rates.
    
    Args:
        data: DataFrame with urban transition data
        scenario: Scenario name to filter by (optional)
        decade: Decade to filter by (optional)  
        level: Analysis level ('county', 'state', 'region')
        top_n: Number of top results to return
    
    Returns:
        DataFrame with analysis results
    """
    # Filter data
    filtered_data = data.copy()
    
    if scenario:
        filtered_data = filtered_data[filtered_data["scenario_name"] == scenario]
    
    if decade:
        filtered_data = filtered_data[filtered_data["decade_name"] == decade]
    
    # Group by analysis level
    if level == "county":
        group_cols = ["county_name", "state_name", "fips_code"]
    elif level == "state":
        group_cols = ["state_name"]
    else:  # region
        group_cols = ["region_name"] if "region_name" in filtered_data.columns else ["state_name"]
    
    # Calculate metrics
    analysis = filtered_data.groupby(group_cols).agg({
        "total_area": ["sum", "mean", "count"],
        "decade_name": "nunique"
    }).round(2)
    
    # Flatten column names
    analysis.columns = ["total_acres", "avg_acres_per_transition", "num_transitions", "num_decades"]
    analysis = analysis.reset_index()
    
    # Calculate urbanization rate
    analysis["urbanization_rate"] = (analysis["total_acres"] / analysis["num_decades"]).round(2)
    
    # Sort and return top N
    analysis = analysis.sort_values("total_acres", ascending=False)
    return analysis.head(top_n)


def main():
    """Command-line interface for urban development analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze urban development rates from RPA data"
    )
    
    parser.add_argument(
        "--scenario", 
        help="Filter by scenario name (e.g., 'HH_CNRM_CM5')"
    )
    
    parser.add_argument(
        "--decade", 
        help="Filter by decade (e.g., '2020-2030')"
    )
    
    parser.add_argument(
        "--level", 
        choices=["county", "state", "region"],
        default="county",
        help="Analysis level (default: county)"
    )
    
    parser.add_argument(
        "--top", 
        type=int, 
        default=10,
        help="Number of top results to show (default: 10)"
    )
    
    parser.add_argument(
        "--output", 
        help="Save results to CSV file"
    )
    
    parser.add_argument(
        "--list-scenarios", 
        action="store_true",
        help="List available scenarios"
    )
    
    parser.add_argument(
        "--list-decades", 
        action="store_true",
        help="List available decades"
    )
    
    args = parser.parse_args()
    
    # Load data
    print("Loading urban development data...")
    data = load_urban_data()
    
    # List options if requested
    if args.list_scenarios:
        scenarios = data["scenario_name"].unique()
        print("\nAvailable scenarios:")
        for scenario in sorted(scenarios):
            print(f"  {scenario}")
        return
    
    if args.list_decades:
        decades = data["decade_name"].unique()
        print("\nAvailable decades:")
        for decade in sorted(decades):
            print(f"  {decade}")
        return
    
    # Perform analysis
    print(f"\nAnalyzing urban development at {args.level} level...")
    if args.scenario:
        print(f"Scenario: {args.scenario}")
    if args.decade:
        print(f"Decade: {args.decade}")
    
    results = analyze_urban_development(
        data, 
        scenario=args.scenario,
        decade=args.decade,
        level=args.level,
        top_n=args.top
    )
    
    if len(results) == 0:
        print("No data found matching the specified criteria.")
        return
    
    # Display results
    print(f"\n🏆 Top {len(results)} {args.level}s by urban development:")
    print("=" * 80)
    
    for i, row in results.iterrows():
        if args.level == "county":
            location = f"{row['county_name']}, {row['state_name']}"
        else:
            location = row[results.columns[0]]  # First column is the location
        
        print(f"{i+1:2d}. {location}")
        print(f"    Total acres urbanized: {row['total_acres']:,.0f}")
        print(f"    Urbanization rate: {row['urbanization_rate']:,.1f} acres/decade")
        print(f"    Number of transitions: {row['num_transitions']}")
        print()
    
    # Save to file if requested
    if args.output:
        results.to_csv(args.output, index=False)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main() 