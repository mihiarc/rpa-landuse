#!/usr/bin/env python3
"""
Regional Analysis Data Generation Script.

This script creates materialized views for regional aggregations of land use transitions
and exports them to Parquet format for external analysis.
"""

import argparse
import logging
import sys
from pathlib import Path
from rpa_landuse.db.region_repository import RegionRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    """Main function to run the regional analysis data generation."""
    parser = argparse.ArgumentParser(
        description="Generate regional analysis data from land use transitions"
    )
    parser.add_argument(
        "--threads", 
        type=int, 
        default=8,
        help="Number of threads to use for parallel processing"
    )
    parser.add_argument(
        "--memory", 
        default="4GB",
        help="Memory limit for DuckDB operations (e.g., 4GB, 8GB)"
    )
    parser.add_argument(
        "--export-dir", 
        default="semantic_layers/regional_analysis",
        help="Directory where to export Parquet files"
    )
    parser.add_argument(
        "--scenario-id", 
        type=int,
        help="Specific scenario ID to process (if not provided, only the ensemble and RPA scenarios are processed)"
    )
    parser.add_argument(
        "--scenario-ids",
        type=int,
        nargs="+",
        default=[21, 22, 23, 24, 25],
        help="List of scenario IDs to process (default: 21-25, ensemble mean and RPA integrated scenarios)"
    )
    parser.add_argument(
        "--all-scenarios",
        action="store_true",
        help="Process all scenarios instead of only the default ensemble and RPA scenarios"
    )
    parser.add_argument(
        "--no-partition", 
        action="store_true",
        help="Do not partition exports by scenario (creates larger single files)"
    )
    parser.add_argument(
        "--only-export", 
        action="store_true",
        help="Skip materialized view creation and only export existing views"
    )
    parser.add_argument(
        "--only-views", 
        action="store_true",
        help="Only create materialized views without exporting"
    )
    
    args = parser.parse_args()
    
    logger.info("Starting regional analysis data generation")
    
    try:
        # Step 1: Create/refresh materialized views
        if not args.only_export:
            logger.info(f"Creating materialized views with {args.threads} threads and {args.memory} memory limit")
            
            if args.scenario_id:
                # Only refresh a specific scenario
                logger.info(f"Refreshing materialized views for scenario {args.scenario_id}")
                RegionRepository.refresh_materialized_views(
                    scenario_id=args.scenario_id,
                    threads=args.threads,
                    memory_limit=args.memory
                )
            else:
                # Create/refresh all materialized views
                logger.info("Creating all materialized views")
                RegionRepository.create_materialized_views(
                    threads=args.threads,
                    memory_limit=args.memory
                )
        
        # Step 2: Export to Parquet
        if not args.only_views:
            logger.info(f"Exporting materialized views to Parquet in {args.export_dir}")
            
            # Determine which scenarios to export
            scenario_ids = None
            if args.scenario_id:
                scenario_ids = [args.scenario_id]
            elif not args.all_scenarios:
                scenario_ids = args.scenario_ids
                logger.info(f"Processing only scenarios {scenario_ids} (ensemble mean and RPA integrated scenarios)")
            
            exported_files = RegionRepository.export_regional_data_to_parquet(
                output_dir=args.export_dir,
                partition_by_scenario=not args.no_partition,
                scenario_ids=scenario_ids
            )
            
            # Report on exported files
            if isinstance(exported_files, dict):
                total_files = 0
                if args.no_partition:
                    total_files = len(exported_files)
                    logger.info(f"Exported {total_files} consolidated Parquet files")
                else:
                    for scenario_id, files in exported_files.items():
                        if isinstance(files, list):
                            total_files += len(files)
                        else:
                            total_files += 1
                    logger.info(f"Exported {total_files} scenario-partitioned Parquet files")
        
        logger.info("Regional analysis data generation completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error in regional analysis data generation: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main()) 