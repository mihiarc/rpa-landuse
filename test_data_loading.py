import pandas as pd
import os

# Simulate the data loading function
data_dir = 'data/processed'
files = {
    'Average Gross Change Across All Scenarios (2020-2070)': 'gross_change_ensemble_all.parquet',
    'Urbanization Trends By Decade': 'urbanization_trends.parquet',
    'Transitions to Urban Land': 'to_urban_transitions.parquet',
    'Transitions from Forest Land': 'from_forest_transitions.parquet',
    'County-Level Land Use Transitions': 'county_transitions.parquet'
}

raw_data = {}
for key, filename in files.items():
    file_path = os.path.join(data_dir, filename)
    if os.path.exists(file_path):
        raw_data[key] = pd.read_parquet(file_path)
        print(f'Loaded: {key} - Shape: {raw_data[key].shape}')
    else:
        print(f'File not found: {file_path}')

# Convert hundred acres to acres for all datasets
data = {}
for key, df in raw_data.items():
    df_copy = df.copy()
    
    # Convert total_area column if it exists
    if 'total_area' in df_copy.columns:
        df_copy['total_area'] = df_copy['total_area'] * 100
        
    # Convert specific columns for urbanization trends dataset
    if key == 'Urbanization Trends By Decade':
        area_columns = ['forest_to_urban', 'cropland_to_urban', 'pasture_to_urban']
        for col in area_columns:
            if col in df_copy.columns:
                df_copy[col] = df_copy[col] * 100
    
    data[key] = df_copy

print('Final data keys:', list(data.keys()))
if 'Urbanization Trends By Decade' in data:
    print('Urbanization data shape:', data['Urbanization Trends By Decade'].shape)
    print('Urbanization scenarios:', data['Urbanization Trends By Decade']['scenario_name'].unique())
else:
    print('ERROR: Urbanization Trends By Decade not found in data!') 