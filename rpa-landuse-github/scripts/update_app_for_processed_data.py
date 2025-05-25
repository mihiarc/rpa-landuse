#!/usr/bin/env python3
"""
Update app.py to use either original or processed data based on availability.

This script shows how to modify the load_parquet_data function in app.py
to use either the original semantic_layers data or the processed data views,
depending on what's available.
"""

import os

def get_updated_data_loader_function():
    """
    Returns the updated load_parquet_data function code that can be
    used to replace the existing function in app.py.
    """
    updated_function = """
@st.cache_data
def load_parquet_data():
    # Try processed data first (smaller, optimized for deployment)
    processed_dir = "data/processed"
    original_dir = "semantic_layers/base_analysis"
    
    # Check if processed data exists
    if os.path.exists(processed_dir) and any(f.endswith('.parquet') for f in os.listdir(processed_dir)):
        data_dir = processed_dir
        st.sidebar.success("Using optimized datasets for better performance")
    else:
        # Fall back to original data
        data_dir = original_dir
    
    try:
        # Define dataset files
        files = {
            "Average Gross Change Across All Scenarios (2020-2070)": "gross_change_ensemble_all.parquet",
            "Urbanization Trends By Decade": "urbanization_trends.parquet",
            "Transitions to Urban Land": "to_urban_transitions.parquet",
            "Transitions from Forest Land": "from_forest_transitions.parquet",
            "County-Level Land Use Transitions": "county_transitions.parquet"
        }
        
        # Load datasets
        raw_data = {}
        for key, filename in files.items():
            file_path = os.path.join(data_dir, filename)
            if os.path.exists(file_path):
                raw_data[key] = pd.read_parquet(file_path)
            else:
                st.warning(f"File not found: {file_path}")
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        raise e
    
    # Convert hundred acres to acres for all datasets
    data = {}
    for key, df in raw_data.items():
        df_copy = df.copy()
        
        # Convert total_area column if it exists
        if "total_area" in df_copy.columns:
            df_copy["total_area"] = df_copy["total_area"] * 100
            
        # Convert specific columns for urbanization trends dataset
        if key == "Urbanization Trends By Decade":
            area_columns = ["forest_to_urban", "cropland_to_urban", "pasture_to_urban"]
            for col in area_columns:
                if col in df_copy.columns:
                    df_copy[col] = df_copy[col] * 100
        
        data[key] = df_copy
    
    return data
"""
    return updated_function

def print_update_instructions():
    """Print instructions for updating app.py"""
    print("""
=== HOW TO UPDATE APP.PY ===

1. Find the existing 'load_parquet_data()' function in app.py
2. Replace it with the function below
3. This updated function will:
   - First check if processed data exists in data/processed/
   - Use processed data if available, otherwise fall back to original data
   - Show appropriate messages to the user

=== UPDATED FUNCTION CODE ===
""")
    print(get_updated_data_loader_function())

def main():
    """Print the updated code and instructions"""
    print_update_instructions()
    
if __name__ == "__main__":
    main() 