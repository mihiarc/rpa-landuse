#!/usr/bin/env python3
"""
DuckDB Data Processor for RPA Land Use Viewer

This script creates smaller, optimized data views directly from the DuckDB database
for deployment on GitHub and Streamlit Cloud.

Instead of creating reduced views from existing parquet files, this script:
1. Connects directly to the DuckDB database
2. Runs optimized queries to create aggregated/sampled datasets
3. Saves the results as parquet files in data/processed/
"""

import os
import duckdb
import pandas as pd
from pathlib import Path

# Database and output paths
DB_PATH = "data/database/rpa.db"
OUTPUT_DIR = "data/processed"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_connection():
    """Get a DuckDB connection."""
    try:
        conn = duckdb.connect(DB_PATH)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise e

def create_gross_change_ensemble():
    """
    Create a reduced gross change ensemble dataset by aggregating at the region level
    instead of county level.
    """
    print("Creating gross change ensemble dataset...")
    
    query = """
    SELECT 
        c.region as region_name,
        lc.from_landuse as from_category,
        lc.to_landuse as to_category,
        s.scenario_name,
        SUM(lc.area_hundreds_acres) as total_area
    FROM 
        landuse_change lc
    JOIN 
        counties c ON lc.fips_code = c.fips_code
    JOIN
        scenarios s ON lc.scenario_id = s.scenario_id
    WHERE
        lc.from_landuse != lc.to_landuse  -- Only include actual transitions
    GROUP BY 
        c.region, lc.from_landuse, lc.to_landuse, s.scenario_name
    ORDER BY 
        total_area DESC
    """
    
    conn = get_connection()
    df = conn.execute(query).fetchdf()
    
    # Save to parquet
    output_path = os.path.join(OUTPUT_DIR, "gross_change_ensemble_all.parquet")
    df.to_parquet(output_path)
    
    print(f"Saved gross change ensemble dataset to {output_path}")
    print(f"Size: {len(df)} rows, {df.memory_usage().sum() / (1024 * 1024):.2f}MB")
    
    return df

def create_urbanization_trends():
    """
    Create a reduced urbanization trends dataset focused on key decades and main transitions.
    """
    print("Creating urbanization trends dataset...")
    
    query = """
    WITH forest_to_urban AS (
        SELECT 
            s.scenario_name,
            d.decade_name,
            SUM(lc.area_hundreds_acres) as forest_to_urban
        FROM 
            landuse_change lc
        JOIN 
            scenarios s ON lc.scenario_id = s.scenario_id
        JOIN 
            decades d ON lc.decade_id = d.decade_id
        WHERE 
            lc.from_landuse = 'fr' AND lc.to_landuse = 'ur'
        GROUP BY 
            s.scenario_name, d.decade_name
    ),
    cropland_to_urban AS (
        SELECT 
            s.scenario_name,
            d.decade_name,
            SUM(lc.area_hundreds_acres) as cropland_to_urban
        FROM 
            landuse_change lc
        JOIN 
            scenarios s ON lc.scenario_id = s.scenario_id
        JOIN 
            decades d ON lc.decade_id = d.decade_id
        WHERE 
            lc.from_landuse = 'cr' AND lc.to_landuse = 'ur'
        GROUP BY 
            s.scenario_name, d.decade_name
    ),
    pasture_to_urban AS (
        SELECT 
            s.scenario_name,
            d.decade_name,
            SUM(lc.area_hundreds_acres) as pasture_to_urban
        FROM 
            landuse_change lc
        JOIN 
            scenarios s ON lc.scenario_id = s.scenario_id
        JOIN 
            decades d ON lc.decade_id = d.decade_id
        WHERE 
            lc.from_landuse = 'ps' AND lc.to_landuse = 'ur'
        GROUP BY 
            s.scenario_name, d.decade_name
    )
    SELECT 
        f.scenario_name,
        f.decade_name,
        f.forest_to_urban,
        c.cropland_to_urban,
        p.pasture_to_urban
    FROM 
        forest_to_urban f
    JOIN 
        cropland_to_urban c ON f.scenario_name = c.scenario_name AND f.decade_name = c.decade_name
    JOIN 
        pasture_to_urban p ON f.scenario_name = p.scenario_name AND f.decade_name = p.decade_name
    ORDER BY 
        f.scenario_name, f.decade_name
    """
    
    conn = get_connection()
    df = conn.execute(query).fetchdf()
    
    # Save to parquet
    output_path = os.path.join(OUTPUT_DIR, "urbanization_trends.parquet")
    df.to_parquet(output_path)
    
    print(f"Saved urbanization trends dataset to {output_path}")
    print(f"Size: {len(df)} rows, {df.memory_usage().sum() / (1024 * 1024):.2f}MB")
    
    return df

def create_to_urban_transitions():
    """
    Create a reduced transitions to urban land dataset.
    Focus on largest transitions by area.
    """
    print("Creating to-urban transitions dataset...")
    
    query = """
    SELECT 
        s.scenario_name,
        d.decade_name,
        lc.from_landuse as from_category,
        'Urban' as to_category,
        SUM(lc.area_hundreds_acres) as total_area
    FROM 
        landuse_change lc
    JOIN 
        scenarios s ON lc.scenario_id = s.scenario_id
    JOIN 
        decades d ON lc.decade_id = d.decade_id
    WHERE 
        lc.to_landuse = 'ur'
    GROUP BY 
        s.scenario_name, d.decade_name, lc.from_landuse
    ORDER BY 
        total_area DESC
    LIMIT 1500
    """
    
    conn = get_connection()
    df = conn.execute(query).fetchdf()
    
    # Save to parquet
    output_path = os.path.join(OUTPUT_DIR, "to_urban_transitions.parquet")
    df.to_parquet(output_path)
    
    print(f"Saved to-urban transitions dataset to {output_path}")
    print(f"Size: {len(df)} rows, {df.memory_usage().sum() / (1024 * 1024):.2f}MB")
    
    return df

def create_from_forest_transitions():
    """
    Create a reduced transitions from forest land dataset.
    Focus on largest transitions by area.
    """
    print("Creating from-forest transitions dataset...")
    
    query = """
    SELECT 
        s.scenario_name,
        d.decade_name,
        'Forest' as from_category,
        lc.to_landuse as to_category,
        SUM(lc.area_hundreds_acres) as total_area
    FROM 
        landuse_change lc
    JOIN 
        scenarios s ON lc.scenario_id = s.scenario_id
    JOIN 
        decades d ON lc.decade_id = d.decade_id
    WHERE 
        lc.from_landuse = 'fr'
    GROUP BY 
        s.scenario_name, d.decade_name, lc.to_landuse
    ORDER BY 
        total_area DESC
    LIMIT 1500
    """
    
    conn = get_connection()
    df = conn.execute(query).fetchdf()
    
    # Save to parquet
    output_path = os.path.join(OUTPUT_DIR, "from_forest_transitions.parquet")
    df.to_parquet(output_path)
    
    print(f"Saved from-forest transitions dataset to {output_path}")
    print(f"Size: {len(df)} rows, {df.memory_usage().sum() / (1024 * 1024):.2f}MB")
    
    return df

def create_county_transitions():
    """
    Create a reduced county-level transitions dataset.
    Focus on top counties by total transition area and aggregate the rest.
    """
    print("Creating county transitions dataset...")
    
    # First, identify top 200 counties by total transition area
    top_counties_query = """
    SELECT 
        lc.fips_code,
        SUM(lc.area_hundreds_acres) as total_transition_area
    FROM 
        landuse_change lc
    GROUP BY 
        lc.fips_code
    ORDER BY 
        total_transition_area DESC
    LIMIT 200
    """
    
    conn = get_connection()
    top_counties = conn.execute(top_counties_query).fetchdf()
    top_fips_list = top_counties['fips_code'].tolist()
    top_fips_str = ', '.join(f"'{fips}'" for fips in top_fips_list)
    
    # Query for the top counties' transitions
    main_query = f"""
    SELECT 
        c.county_name,
        c.state_name,
        lt_from.landuse_type_name as from_category,
        lt_to.landuse_type_name as to_category,
        s.scenario_name,
        d.decade_name,
        SUM(lc.area_hundreds_acres) as total_area
    FROM 
        landuse_change lc
    JOIN 
        counties c ON lc.fips_code = c.fips_code
    JOIN 
        scenarios s ON lc.scenario_id = s.scenario_id
    JOIN 
        decades d ON lc.decade_id = d.decade_id
    JOIN
        landuse_types lt_from ON lc.from_landuse = lt_from.landuse_type_code
    JOIN
        landuse_types lt_to ON lc.to_landuse = lt_to.landuse_type_code
    WHERE 
        lc.fips_code IN ({top_fips_str})
    GROUP BY 
        c.county_name, c.state_name, lt_from.landuse_type_name, lt_to.landuse_type_name, 
        s.scenario_name, d.decade_name
    ORDER BY 
        total_area DESC
    """
    
    # Query for aggregated "Other counties" by state
    other_counties_query = f"""
    SELECT 
        'Other counties' as county_name,
        c.state_name,
        lt_from.landuse_type_name as from_category,
        lt_to.landuse_type_name as to_category,
        s.scenario_name,
        d.decade_name,
        SUM(lc.area_hundreds_acres) as total_area
    FROM 
        landuse_change lc
    JOIN 
        counties c ON lc.fips_code = c.fips_code
    JOIN 
        scenarios s ON lc.scenario_id = s.scenario_id
    JOIN 
        decades d ON lc.decade_id = d.decade_id
    JOIN
        landuse_types lt_from ON lc.from_landuse = lt_from.landuse_type_code
    JOIN
        landuse_types lt_to ON lc.to_landuse = lt_to.landuse_type_code
    WHERE 
        lc.fips_code NOT IN ({top_fips_str})
    GROUP BY 
        c.state_name, lt_from.landuse_type_name, lt_to.landuse_type_name, 
        s.scenario_name, d.decade_name
    ORDER BY 
        total_area DESC
    """
    
    # Execute both queries and combine results
    top_counties_data = conn.execute(main_query).fetchdf()
    other_counties_data = conn.execute(other_counties_query).fetchdf()
    df = pd.concat([top_counties_data, other_counties_data])
    
    # Save to parquet
    output_path = os.path.join(OUTPUT_DIR, "county_transitions.parquet")
    df.to_parquet(output_path)
    
    print(f"Saved county transitions dataset to {output_path}")
    print(f"Size: {len(df)} rows, {df.memory_usage().sum() / (1024 * 1024):.2f}MB")
    
    return df

def main():
    """Generate all reduced datasets directly from DuckDB."""
    print(f"Creating reduced data views from DuckDB database: {DB_PATH}")
    print(f"Output directory: {OUTPUT_DIR}\n")
    
    # Create each dataset
    create_gross_change_ensemble()
    create_urbanization_trends()
    create_to_urban_transitions()
    create_from_forest_transitions()
    create_county_transitions()
    
    print("\nAll datasets created successfully!")
    print(f"To use these datasets, update your app.py to load data from {OUTPUT_DIR}")

if __name__ == "__main__":
    main() 