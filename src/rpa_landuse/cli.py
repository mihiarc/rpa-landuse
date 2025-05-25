#!/usr/bin/env python3
"""
Command-line interface for the RPA Land Use Viewer package.
"""

import argparse
import sys
from pathlib import Path

def run_app(args):
    """Run the Streamlit app."""
    import streamlit.web.bootstrap as bootstrap
    
    # Find app.py in the package
    package_dir = Path(__file__).parent.parent.parent
    app_path = package_dir / "app.py"
    
    if not app_path.exists():
        print(f"Error: Could not find app.py at {app_path}")
        sys.exit(1)
    
    # Use the updated Streamlit API
    bootstrap.run(str(app_path), "", [], {})

def create_semantic_layers(args):
    """Create semantic layers for data analysis."""
    from rpa_landuse.pandasai.layers import extract_data_from_duckdb, create_semantic_layers
    import os
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    if not args.skip_extraction:
        extract_data_from_duckdb(
            db_path=args.db_path,
            output_dir=args.output_dir,
            scenario_ids=args.scenario_ids if not args.all_scenarios else None
        )
    
    create_semantic_layers(
        parquet_dir=args.output_dir,
        org_path=args.org_path
    )

def create_regional_layers(args):
    """Create regional layers for data analysis."""
    from rpa_landuse.commands.create_regional_layers import main as regional_main
    sys.exit(regional_main())

def query_database(args):
    """Query the database using the command-line query tool."""
    from rpa_landuse.commands.query_duckdb import main as query_main
    sys.exit(query_main())

def query_natural_language(args):
    """Query the data using natural language with PandasAI."""
    from rpa_landuse.commands.query_pandasai import main as query_pandasai_main
    sys.exit(query_pandasai_main())

def analyze_urban_development(args):
    """Analyze urban development rates."""
    from rpa_landuse.commands.urban_analysis import main as urban_main
    sys.exit(urban_main())

def analyze_forest_loss(args):
    """Analyze forest loss rates."""
    from rpa_landuse.commands.forest_analysis import main as forest_main
    sys.exit(forest_main())

def analyze_ag_loss(args):
    """Analyze agricultural land loss rates."""
    from rpa_landuse.commands.ag_analysis import main as ag_main
    sys.exit(ag_main())

def initialize_db(args):
    """Initialize the database schema and optionally import data."""
    from rpa_landuse.db.schema_manager import SchemaManager
    
    SchemaManager.initialize_database()
    SchemaManager.ensure_indexes()
    
    if args.import_data and args.data_path:
        from rpa_landuse.db.import_landuse_data import process_transitions
        process_transitions(args.data_path)

def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="RPA Land Use - Tools for analyzing RPA land use projections"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # App command
    app_parser = subparsers.add_parser("app", help="Run the Streamlit app")
    
    # Semantic layers command
    semantic_parser = subparsers.add_parser(
        "semantic-layers", help="Create semantic layers for data analysis"
    )
    semantic_parser.add_argument(
        "--db-path", 
        type=str, 
        default="data/database/rpa.db",
        help="Path to the DuckDB database file"
    )
    semantic_parser.add_argument(
        "--output-dir", 
        type=str, 
        default="semantic_layers/base_analysis",
        help="Directory to save Parquet files"
    )
    semantic_parser.add_argument(
        "--org-path", 
        type=str, 
        default="rpa-landuse",
        help="Organization path prefix for PandasAI datasets"
    )
    semantic_parser.add_argument(
        "--skip-extraction", 
        action="store_true",
        help="Skip data extraction and use existing Parquet files"
    )
    semantic_parser.add_argument(
        "--scenario-ids",
        type=int,
        nargs="+",
        default=[21, 22, 23, 24, 25],
        help="List of scenario IDs to include (default: 21-25, ensemble mean and RPA integrated scenarios)"
    )
    semantic_parser.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Process all scenarios instead of only the default ensemble and RPA scenarios"
    )
    
    # Regional layers command
    regional_parser = subparsers.add_parser(
        "regional-layers", help="Create regional aggregation layers for data analysis"
    )
    
    # Query database command
    query_parser = subparsers.add_parser(
        "query", help="Query the database using the command-line tool"
    )
    
    # PandasAI natural language query command
    nl_query_parser = subparsers.add_parser(
        "pandasai-query", help="Query data using natural language with PandasAI"
    )
    
    # Urban development analysis command
    urban_parser = subparsers.add_parser(
        "urban-analysis", help="Analyze urban development rates and identify hotspots"
    )
    
    # Forest loss analysis command
    forest_parser = subparsers.add_parser(
        "forest-analysis", help="Analyze forest loss rates and identify hotspots"
    )
    
    # Agricultural land loss analysis command
    ag_parser = subparsers.add_parser(
        "ag-analysis", help="Analyze agricultural land loss rates and identify hotspots (cropland and pasture)"
    )
    
    # DB init command
    db_parser = subparsers.add_parser("init-db", help="Initialize the database")
    db_parser.add_argument(
        "--import-data",
        action="store_true",
        help="Import data after initialization"
    )
    db_parser.add_argument(
        "--data-path",
        type=str,
        default="data/raw/county_landuse_projections_RPA.json",
        help="Path to the data file to import"
    )
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    if args.command == "app":
        run_app([])
    elif args.command == "semantic-layers":
        create_semantic_layers(args)
    elif args.command == "regional-layers":
        create_regional_layers(args)
    elif args.command == "query":
        query_database(args)
    elif args.command == "pandasai-query":
        query_natural_language(args)
    elif args.command == "urban-analysis":
        analyze_urban_development(args)
    elif args.command == "forest-analysis":
        analyze_forest_loss(args)
    elif args.command == "ag-analysis":
        analyze_ag_loss(args)
    elif args.command == "init-db":
        initialize_db(args)

if __name__ == "__main__":
    main() 