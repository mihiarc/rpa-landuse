"""
Functions for extracting data from DuckDB and creating PandasAI semantic layers.
"""

import os
import duckdb
import pandas as pd
from pandasai import SmartDataframe
from pandasai.llm import BambooLLM
from dotenv import load_dotenv
from typing import List, Optional


def extract_data_from_duckdb(db_path="data/database/rpa.db", output_dir="semantic_layers/base_analysis", 
                            scenario_ids: Optional[List[int]] = None):
    """
    Extract data from DuckDB database and save as Parquet files.
    
    Args:
        db_path (str): Path to the DuckDB database file
        output_dir (str): Directory to save Parquet files
        scenario_ids (List[int], optional): List of scenario IDs to include (default: [21, 22, 23, 24, 25])
        
    Returns:
        dict: Dictionary with paths to the created Parquet files
    """
    # Use primary scenarios by default if none specified (ensemble mean and RPA integrated scenarios)
    if scenario_ids is None:
        scenario_ids = [21, 22, 23, 24, 25]
    
    # Create scenario filter for SQL queries
    scenario_filter = f"WHERE s.scenario_id IN ({','.join(map(str, scenario_ids))})"
    
    # Create directory for parquet files if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Connect to DuckDB
    print(f"Connecting to DuckDB database: {db_path}")
    conn = duckdb.connect(db_path)
    
    # Output file paths
    output_files = {
        "reference": f"{output_dir}/reference.parquet",
        "gross_change_ensemble_all": f"{output_dir}/gross_change_ensemble_all.parquet",
        "to_urban_transitions": f"{output_dir}/to_urban_transitions.parquet",
        "from_forest_transitions": f"{output_dir}/from_forest_transitions.parquet",
        "county_transitions": f"{output_dir}/county_transitions.parquet",
        "county_transitions_changes_only": f"{output_dir}/county_transitions_changes_only.parquet",
        "county_to_urban": f"{output_dir}/county_to_urban.parquet", 
        "county_from_forest": f"{output_dir}/county_from_forest.parquet",
        "urbanization_trends": f"{output_dir}/urbanization_trends.parquet"
    }
    
    # Extract reference information (scenarios + domains)
    print("Extracting reference information...")
    conn.sql(f"""
        SELECT 
            s.scenario_id,
            s.scenario_name,
            s.gcm, 
            s.rcp,
            s.ssp,
            'Scenario' as info_type
        FROM 
            scenarios s
        WHERE 
            s.scenario_id IN ({','.join(map(str, scenario_ids))})
        
        UNION ALL
        
        SELECT 
            NULL as scenario_id,
            landuse_type_name as scenario_name,
            landuse_type_code as gcm,
            NULL as rcp,
            NULL as ssp,
            'Land Use Type' as info_type
        FROM 
            landuse_types
        
        UNION ALL
        
        SELECT 
            decade_id as scenario_id,
            decade_name as scenario_name,
            start_year::TEXT as gcm,
            end_year::TEXT as rcp,
            NULL as ssp,
            'Time Period' as info_type
        FROM 
            decades
    """).write_parquet(output_files["reference"])
    
    # Create an aggregated transitions view with ONLY land use changes (excluding where from_category = to_category)
    print("Creating transitions summary for only changing land uses...")
    conn.sql(f"""
        SELECT 
            2020 as "Start Year",
            2070 as "End Year",
            l1.landuse_type_name as "From Land Use",
            l2.landuse_type_name as "To Land Use",
            SUM(lc.area_hundreds_acres) as "Total Area"
        FROM landuse_change lc
        JOIN scenarios s ON lc.scenario_id = s.scenario_id
        JOIN decades d ON lc.decade_id = d.decade_id
        JOIN landuse_types l1 ON lc.from_landuse = l1.landuse_type_code
        JOIN landuse_types l2 ON lc.to_landuse = l2.landuse_type_code
        {scenario_filter}
        AND l1.landuse_type_name != l2.landuse_type_name
        AND s.scenario_name = 'ensemble_overall'
        GROUP BY 
                l1.landuse_type_name, l2.landuse_type_name
    """).write_parquet(output_files["gross_change_ensemble_all"])
    
    # Create transitions TO Urban only
    print("Creating transitions TO Urban summary...")
    conn.sql(f"""
        SELECT 
            s.scenario_name,
            s.gcm, 
            s.rcp,
            s.ssp,
            d.decade_name,
            d.start_year,
            d.end_year,
            l1.landuse_type_name as from_category,
            'Urban' as to_category,
            SUM(lc.area_hundreds_acres) as total_area
        FROM landuse_change lc
        JOIN scenarios s ON lc.scenario_id = s.scenario_id
        JOIN decades d ON lc.decade_id = d.decade_id
        JOIN landuse_types l1 ON lc.from_landuse = l1.landuse_type_code
        JOIN landuse_types l2 ON lc.to_landuse = l2.landuse_type_code
        {scenario_filter}
        AND lc.to_landuse = 'ur' AND lc.from_landuse != 'ur'
        GROUP BY s.scenario_name, s.gcm, s.rcp, s.ssp, 
                d.decade_name, d.start_year, d.end_year, 
                l1.landuse_type_name
    """).write_parquet(output_files["to_urban_transitions"])
    
    # Create transitions FROM Forest only
    print("Creating transitions FROM Forest summary...")
    conn.sql(f"""
        SELECT 
            s.scenario_name,
            s.gcm, 
            s.rcp,
            s.ssp,
            d.decade_name,
            d.start_year,
            d.end_year,
            'Forest' as from_category,
            l2.landuse_type_name as to_category,
            SUM(lc.area_hundreds_acres) as total_area
        FROM landuse_change lc
        JOIN scenarios s ON lc.scenario_id = s.scenario_id
        JOIN decades d ON lc.decade_id = d.decade_id
        JOIN landuse_types l1 ON lc.from_landuse = l1.landuse_type_code
        JOIN landuse_types l2 ON lc.to_landuse = l2.landuse_type_code
        {scenario_filter}
        AND lc.from_landuse = 'fr' AND lc.to_landuse != 'fr'
        GROUP BY s.scenario_name, s.gcm, s.rcp, s.ssp, 
                d.decade_name, d.start_year, d.end_year, 
                l2.landuse_type_name
    """).write_parquet(output_files["from_forest_transitions"])
    
    # Create a county-level aggregation
    print("Creating county-level transitions...")
    conn.sql(f"""
        SELECT 
            co.fips_code,
            co.county_name,
            co.state_name,
            s.scenario_name,
            d.decade_name,
            l1.landuse_type_name as from_category,
            l2.landuse_type_name as to_category,
            SUM(lc.area_hundreds_acres) as total_area
        FROM landuse_change lc
        JOIN counties co ON lc.fips_code = co.fips_code
        JOIN scenarios s ON lc.scenario_id = s.scenario_id
        JOIN decades d ON lc.decade_id = d.decade_id
        JOIN landuse_types l1 ON lc.from_landuse = l1.landuse_type_code
        JOIN landuse_types l2 ON lc.to_landuse = l2.landuse_type_code
        {scenario_filter}
        GROUP BY co.fips_code, co.county_name, co.state_name,
                s.scenario_name, d.decade_name, 
                l1.landuse_type_name, l2.landuse_type_name
    """).write_parquet(output_files["county_transitions"])
    
    # Create a county-level aggregation with ONLY land use changes
    print("Creating county-level transitions for only changing land uses...")
    conn.sql(f"""
        SELECT 
            co.fips_code,
            co.county_name,
            co.state_name,
            s.scenario_name,
            d.decade_name,
            l1.landuse_type_name as from_category,
            l2.landuse_type_name as to_category,
            SUM(lc.area_hundreds_acres) as total_area
        FROM landuse_change lc
        JOIN counties co ON lc.fips_code = co.fips_code
        JOIN scenarios s ON lc.scenario_id = s.scenario_id
        JOIN decades d ON lc.decade_id = d.decade_id
        JOIN landuse_types l1 ON lc.from_landuse = l1.landuse_type_code
        JOIN landuse_types l2 ON lc.to_landuse = l2.landuse_type_code
        {scenario_filter}
        AND l1.landuse_type_name != l2.landuse_type_name
        GROUP BY co.fips_code, co.county_name, co.state_name,
                s.scenario_name, d.decade_name, 
                l1.landuse_type_name, l2.landuse_type_name
    """).write_parquet(output_files["county_transitions_changes_only"])
    
    # Create county-level transitions TO Urban
    print("Creating county-level transitions TO Urban...")
    conn.sql(f"""
        SELECT 
            co.fips_code,
            co.county_name,
            co.state_name,
            s.scenario_name,
            d.decade_name,
            l1.landuse_type_name as from_category,
            'Urban' as to_category,
            SUM(lc.area_hundreds_acres) as total_area
        FROM landuse_change lc
        JOIN counties co ON lc.fips_code = co.fips_code
        JOIN scenarios s ON lc.scenario_id = s.scenario_id
        JOIN decades d ON lc.decade_id = d.decade_id
        JOIN landuse_types l1 ON lc.from_landuse = l1.landuse_type_code
        JOIN landuse_types l2 ON lc.to_landuse = l2.landuse_type_code
        {scenario_filter}
        AND lc.to_landuse = 'ur' AND lc.from_landuse != 'ur'
        GROUP BY co.fips_code, co.county_name, co.state_name,
                s.scenario_name, d.decade_name, 
                l1.landuse_type_name
    """).write_parquet(output_files["county_to_urban"])
    
    # Create county-level transitions FROM Forest
    print("Creating county-level transitions FROM Forest...")
    conn.sql(f"""
        SELECT 
            co.fips_code,
            co.county_name,
            co.state_name,
            s.scenario_name,
            d.decade_name,
            'Forest' as from_category,
            l2.landuse_type_name as to_category,
            SUM(lc.area_hundreds_acres) as total_area
        FROM landuse_change lc
        JOIN counties co ON lc.fips_code = co.fips_code
        JOIN scenarios s ON lc.scenario_id = s.scenario_id
        JOIN decades d ON lc.decade_id = d.decade_id
        JOIN landuse_types l1 ON lc.from_landuse = l1.landuse_type_code
        JOIN landuse_types l2 ON lc.to_landuse = l2.landuse_type_code
        {scenario_filter}
        AND lc.from_landuse = 'fr' AND lc.to_landuse != 'fr'
        GROUP BY co.fips_code, co.county_name, co.state_name,
                s.scenario_name, d.decade_name, 
                l2.landuse_type_name
    """).write_parquet(output_files["county_from_forest"])
    
    # Create a time series view for analyzing trends
    print("Creating urbanization trends...")
    conn.sql(f"""
        SELECT 
            s.scenario_name,
            d.decade_name,
            d.start_year,
            SUM(CASE WHEN lc.from_landuse = 'fr' AND lc.to_landuse = 'ur' 
                THEN lc.area_hundreds_acres ELSE 0 END) as forest_to_urban,
            SUM(CASE WHEN lc.from_landuse = 'cr' AND lc.to_landuse = 'ur' 
                THEN lc.area_hundreds_acres ELSE 0 END) as cropland_to_urban,
            SUM(CASE WHEN lc.from_landuse = 'ps' AND lc.to_landuse = 'ur' 
                THEN lc.area_hundreds_acres ELSE 0 END) as pasture_to_urban
        FROM landuse_change lc
        JOIN scenarios s ON lc.scenario_id = s.scenario_id
        JOIN decades d ON lc.decade_id = d.decade_id
        {scenario_filter}
        GROUP BY s.scenario_name, d.decade_name, d.start_year
        ORDER BY s.scenario_name, d.start_year
    """).write_parquet(output_files["urbanization_trends"])
    
    # Close the database connection
    conn.close()
    print("DuckDB connection closed.")
    
    return output_files


def get_api_key():
    """Get the API key from environment variables."""
    load_dotenv(dotenv_path=".env")
    
    # Try PandasAI specific key first, then fallback to OpenAI key
    api_key = os.getenv("PANDABI_API_KEY")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        
    if not api_key:
        raise ValueError(
            "No API key found in .env file. "
            "Please create a .env file with your PANDABI_API_KEY."
        )
    
    return api_key


def get_llm():
    """Get the LLM with the API key."""
    api_key = get_api_key()
    
    # Use BambooLLM with the provided API key
    # Note: PandasAI 3.0.0b17 uses BambooLLM instead of OpenAI directly
    return BambooLLM(api_key=api_key)


def create_semantic_layers(parquet_dir="semantic_layers/base_analysis", org_path="rpa-landuse"):
    """
    Create semantic layers using PandasAI for the extracted data.
    
    Args:
        parquet_dir (str): Directory containing the Parquet files
        org_path (str): Organization path prefix for PandasAI datasets
        
    Returns:
        dict: Dictionary with the created semantic layer objects
    """
    # Get the appropriate LLM
    llm = get_llm()
    
    # Paths for the parquet files
    reference_parquet = f"{parquet_dir}/reference.parquet"
    transitions_changes_parquet = f"{parquet_dir}/gross_change_ensemble_all.parquet"
    to_urban_parquet = f"{parquet_dir}/to_urban_transitions.parquet"
    from_forest_parquet = f"{parquet_dir}/from_forest_transitions.parquet"
    
    county_parquet = f"{parquet_dir}/county_transitions.parquet"
    county_changes_parquet = f"{parquet_dir}/county_transitions_changes_only.parquet"
    county_to_urban_parquet = f"{parquet_dir}/county_to_urban.parquet"
    county_from_forest_parquet = f"{parquet_dir}/county_from_forest.parquet"
    
    urbanization_parquet = f"{parquet_dir}/urbanization_trends.parquet"
    
    # Load the datasets
    print(f"Loading data from {reference_parquet}")
    reference_df = pd.read_parquet(reference_parquet)
    
    print(f"Loading data from {transitions_changes_parquet}")
    transitions_changes_df = pd.read_parquet(transitions_changes_parquet)
    
    print(f"Loading data from {to_urban_parquet}")
    to_urban_df = pd.read_parquet(to_urban_parquet)
    
    print(f"Loading data from {from_forest_parquet}")
    from_forest_df = pd.read_parquet(from_forest_parquet)
    
    print(f"Loading data from {county_parquet}")
    county_df = pd.read_parquet(county_parquet)
    
    print(f"Loading data from {county_changes_parquet}")
    county_changes_df = pd.read_parquet(county_changes_parquet)
    
    print(f"Loading data from {county_to_urban_parquet}")
    county_to_urban_df = pd.read_parquet(county_to_urban_parquet)
    
    print(f"Loading data from {county_from_forest_parquet}")
    county_from_forest_df = pd.read_parquet(county_from_forest_parquet)
    
    print(f"Loading data from {urbanization_parquet}")
    urbanization_df = pd.read_parquet(urbanization_parquet)
    
    # Create SmartDataframes with the data
    print("Creating semantic layer for reference information...")
    reference_smart_df = SmartDataframe(
        reference_df,
        config={"llm": llm, "name": "Reference Information"}
    )
    
    print("Creating semantic layer for transitions with changes only...")
    transitions_changes_smart_df = SmartDataframe(
        transitions_changes_df,
        config={"llm": llm, "name": "Land Use Transitions - Ensemble Changes"}
    )
    
    print("Creating semantic layer for transitions TO Urban...")
    to_urban_smart_df = SmartDataframe(
        to_urban_df,
        config={"llm": llm, "name": "Transitions TO Urban"}
    )
    
    print("Creating semantic layer for transitions FROM Forest...")
    from_forest_smart_df = SmartDataframe(
        from_forest_df,
        config={"llm": llm, "name": "Transitions FROM Forest"}
    )
    
    # Create county-level transitions semantic layer
    print("Creating semantic layer for county transitions...")
    county_smart_df = SmartDataframe(
        county_df,
        config={"llm": llm, "name": "County Land Use Transitions"}
    )
    
    print("Creating semantic layer for county transitions with changes only...")
    county_changes_smart_df = SmartDataframe(
        county_changes_df,
        config={"llm": llm, "name": "County Land Use Transitions - Changes Only"}
    )
    
    print("Creating semantic layer for county transitions TO Urban...")
    county_to_urban_smart_df = SmartDataframe(
        county_to_urban_df,
        config={"llm": llm, "name": "County Transitions TO Urban"}
    )
    
    print("Creating semantic layer for county transitions FROM Forest...")
    county_from_forest_smart_df = SmartDataframe(
        county_from_forest_df,
        config={"llm": llm, "name": "County Transitions FROM Forest"}
    )
    
    # Create urbanization trends semantic layer
    print("Creating semantic layer for urbanization trends...")
    urbanization_smart_df = SmartDataframe(
        urbanization_df,
        config={"llm": llm, "name": "Urbanization Trends"}
    )
    
    # Return the created SmartDataframes
    return {
        "reference": reference_smart_df,
        "transitions_changes": transitions_changes_smart_df,
        "to_urban": to_urban_smart_df,
        "from_forest": from_forest_smart_df,
        "county": county_smart_df,
        "county_changes": county_changes_smart_df,
        "county_to_urban": county_to_urban_smart_df,
        "county_from_forest": county_from_forest_smart_df,
        "urbanization": urbanization_smart_df
    } 