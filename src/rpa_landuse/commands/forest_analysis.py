#!/usr/bin/env python3
"""
Forest Loss Analysis Tool

This module provides command-line tools for analyzing forest loss rates
from the RPA land use data.
"""

import pandas as pd
import argparse
import sys
from pathlib import Path


def load_forest_data(data_path="semantic_layers/base_analysis"):
    """Load forest loss data from parquet files."""
    try:
        county_transitions = pd.read_parquet(
            Path(data_path) / "county_transitions.parquet"
        )
        
        # Filter for only the 5 key RPA scenarios
        key_scenarios = [
            'ensemble_LM',    # Lower warming-moderate growth (RCP4.5-SSP1)
            'ensemble_HL',    # High warming-low growth (RCP8.5-SSP3)
            'ensemble_HM',    # High warming-moderate growth (RCP8.5-SSP2)
            'ensemble_HH',    # High warming-high growth (RCP8.5-SSP5)
            'ensemble_overall' # Overall mean projection
        ]
        county_transitions = county_transitions[
            county_transitions["scenario_name"].isin(key_scenarios)
        ]
        
        # Filter for forest transitions only (from forest to other land uses)
        forest_data = county_transitions[county_transitions["from_category"] == "Forest"]
        return forest_data
    except FileNotFoundError as e:
        print(f"Error: Could not find data files in {data_path}")
        print("Make sure you're running from the project root directory")
        sys.exit(1)


def analyze_forest_loss(data, scenario=None, decade=None, level="county", top_n=10, to_category=None):
    """
    Analyze forest loss rates.
    
    Args:
        data: DataFrame with forest transition data
        scenario: Scenario name to filter by (optional)
        decade: Decade to filter by (optional)  
        level: Analysis level ('county', 'state')
        top_n: Number of top results to return
        to_category: Filter by destination land use (optional)
    
    Returns:
        DataFrame with analysis results
    """
    # Filter data
    filtered_data = data.copy()
    
    if scenario:
        filtered_data = filtered_data[filtered_data["scenario_name"] == scenario]
    
    if decade:
        filtered_data = filtered_data[filtered_data["decade_name"] == decade]
    
    if to_category:
        filtered_data = filtered_data[filtered_data["to_category"] == to_category]
    
    # Group by analysis level
    if level == "county":
        group_cols = ["county_name", "state_name", "fips_code"]
    elif level == "state":
        group_cols = ["state_name"]
    else:  # region - fallback to state since region_name doesn't exist
        group_cols = ["state_name"]
    
    # Calculate metrics
    analysis = filtered_data.groupby(group_cols).agg({
        "total_area": ["sum", "mean"],
        "decade_name": "nunique"
    }).round(2)
    
    # Flatten column names
    analysis.columns = ["total_acres", "avg_acres_per_decade", "num_decades"]
    analysis = analysis.reset_index()
    
    # Calculate forest loss rate
    analysis["forest_loss_rate"] = (analysis["total_acres"] / analysis["num_decades"]).round(2)
    
    # Sort and return top N
    analysis = analysis.sort_values("total_acres", ascending=False)
    return analysis.head(top_n)


def main():
    """Command-line interface for forest loss analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze forest loss rates from RPA data"
    )
    
    parser.add_argument(
        "--scenario", 
        help="Filter by scenario name (e.g., 'ensemble_HH')"
    )
    
    parser.add_argument(
        "--decade", 
        help="Filter by decade (e.g., '2020-2030')"
    )
    
    parser.add_argument(
        "--level", 
        choices=["county", "state"],
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
        "--to-category",
        choices=["Urban", "Cropland", "Pasture", "Rangeland"],
        help="Filter by destination land use (what forest is converted to)"
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
    
    parser.add_argument(
        "--list-destinations",
        action="store_true", 
        help="List available destination land uses"
    )
    
    args = parser.parse_args()
    
    # Load data
    print("Loading forest loss data...")
    data = load_forest_data()
    
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
    
    if args.list_destinations:
        destinations = data["to_category"].unique()
        print("\nAvailable destination land uses:")
        for dest in sorted(destinations):
            print(f"  {dest}")
        return
    
    # Perform analysis
    print(f"\nAnalyzing forest loss at {args.level} level...")
    if args.scenario:
        print(f"Scenario: {args.scenario}")
    if args.decade:
        print(f"Decade: {args.decade}")
    if args.to_category:
        print(f"Forest converted to: {args.to_category}")
    
    results = analyze_forest_loss(
        data, 
        scenario=args.scenario,
        decade=args.decade,
        level=args.level,
        top_n=args.top,
        to_category=args.to_category
    )
    
    if len(results) == 0:
        print("No data found matching the specified criteria.")
        return
    
    # Display results
    conversion_text = f" (converted to {args.to_category})" if args.to_category else ""
    print(f"\n🌲 Top {len(results)} {args.level}s by forest loss{conversion_text}:")
    print("=" * 80)
    
    for i, row in results.iterrows():
        if args.level == "county":
            location = f"{row['county_name']}, {row['state_name']}"
        else:
            location = row[results.columns[0]]  # First column is the location
        
        print(f"{i+1:2d}. {location}")
        print(f"    Total forest acres lost: {row['total_acres']:,.0f}")
        print(f"    Forest loss rate: {row['forest_loss_rate']:,.1f} acres/decade")
        print(f"    Average per decade: {row['avg_acres_per_decade']:,.1f} acres")
        print(f"    Time periods covered: {row['num_decades']} decades")
        print()
    
    # Save to file if requested
    if args.output:
        # Add metadata to results
        results_with_metadata = results.copy()
        results_with_metadata["scenario"] = args.scenario or "All scenarios"
        results_with_metadata["time_period"] = args.decade or "All periods"
        results_with_metadata["destination"] = args.to_category or "All destinations"
        results_with_metadata["analysis_level"] = args.level
        results_with_metadata["generated_date"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
        
        results_with_metadata.to_csv(args.output, index=False)
        print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main() 