#!/usr/bin/env python3
"""
Update Streamlit app to use database views for spatial aggregations.
"""

import re
from pathlib import Path

def update_streamlit_app():
    """Update the streamlit app to use database views."""
    
    app_path = Path(__file__).parent.parent / "streamlit_app.py"
    
    print(f"Updating {app_path}...")
    
    # Read the current app
    with open(app_path, 'r') as f:
        content = f.read()
    
    # Create the new data loading function
    new_load_function = '''
# Load data using database views 
@st.cache_data
def load_data_from_views():
    """Load data from database views for different spatial levels."""
    import duckdb
    
    # Database path
    db_path = "data/database/rpa.db"
    
    try:
        conn = duckdb.connect(db_path)
        
        # Load each spatial level into a dictionary
        datasets = {}
        
        # Load the main dataset (county level)
        datasets["County-Level Land Use Transitions"] = conn.execute(
            'SELECT * FROM "County-Level Land Use Transitions"'
        ).df()
        
        # Load other spatial levels 
        datasets["State-Level Land Use Transitions"] = conn.execute(
            'SELECT * FROM "State-Level Land Use Transitions"'  
        ).df()
        
        datasets["Region-Level Land Use Transitions"] = conn.execute(
            'SELECT * FROM "Region-Level Land Use Transitions"'
        ).df()
        
        datasets["Subregion-Level Land Use Transitions"] = conn.execute(
            'SELECT * FROM "Subregion-Level Land Use Transitions"'
        ).df()
        
        datasets["National-Level Land Use Transitions"] = conn.execute(
            'SELECT * FROM "National-Level Land Use Transitions"'
        ).df()
        
        # Create derived datasets for the existing app structure
        county_df = datasets["County-Level Land Use Transitions"]
        
        # Average Gross Change Across All Scenarios (2020-2070)
        gross_change = county_df.groupby([
            'scenario_name', 'state_name', 'from_category', 'to_category'
        ])['total_area'].sum().reset_index()
        datasets["Average Gross Change Across All Scenarios (2020-2070)"] = gross_change
        
        # Urbanization Trends By Decade
        urbanization = county_df[county_df['to_category'] == 'Urban'].groupby([
            'scenario_name', 'decade_name'
        ]).agg({
            'total_area': 'sum'
        }).reset_index()
        urbanization['forest_to_urban'] = county_df[
            (county_df['from_category'] == 'Forest') & 
            (county_df['to_category'] == 'Urban')
        ].groupby(['scenario_name', 'decade_name'])['total_area'].sum().values
        urbanization['cropland_to_urban'] = county_df[
            (county_df['from_category'] == 'Cropland') & 
            (county_df['to_category'] == 'Urban')
        ].groupby(['scenario_name', 'decade_name'])['total_area'].sum().values
        urbanization['pasture_to_urban'] = county_df[
            (county_df['from_category'] == 'Pasture') & 
            (county_df['to_category'] == 'Urban')
        ].groupby(['scenario_name', 'decade_name'])['total_area'].sum().values
        datasets["Urbanization Trends By Decade"] = urbanization
        
        # Transitions to Urban Land
        datasets["Transitions to Urban Land"] = county_df[county_df['to_category'] == 'Urban']
        
        # Transitions from Forest Land
        datasets["Transitions from Forest Land"] = county_df[county_df['from_category'] == 'Forest']
        
        conn.close()
        st.sidebar.success("Using database views for optimal performance")
        
    except Exception as e:
        st.error(f"Error loading data from database: {e}")
        st.info("Falling back to parquet files...")
        # Fallback to original method
        return load_parquet_data()
    
    return datasets
'''
    
    # Replace the load_parquet_data function with the new one
    # Find the function definition
    pattern = r'@st\.cache_data\s*\ndef load_parquet_data\(\):.*?return data'
    
    # Replace with new function
    content = re.sub(pattern, new_load_function.strip(), content, flags=re.DOTALL)
    
    # Update the data loading call
    content = content.replace('data = load_parquet_data()', 'data = load_data_from_views()')
    
    # Write the updated content
    with open(app_path, 'w') as f:
        f.write(content)
    
    print("✅ Streamlit app updated to use database views!")
    print("\nChanges made:")
    print("1. Replaced load_parquet_data() with load_data_from_views()")
    print("2. App now loads data directly from database views")
    print("3. Spatial aggregations are handled by the database")
    print("4. Added fallback to parquet files if database fails")

if __name__ == "__main__":
    update_streamlit_app() 