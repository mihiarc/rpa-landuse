# Data Reduction Implementation for RPA Land Use Viewer

This document outlines the steps to create smaller data views from large parquet files for GitHub and Streamlit Cloud deployment.

## Background

The original parquet data files in `semantic_layers/base_analysis/` are too large to push to GitHub, which makes deployment on Streamlit Cloud impossible. This implementation plan creates smaller, optimized versions of these datasets while preserving key insights.

## Implementation Steps

### 1. Create Data Processing Script

Create a new Python script `scripts/data_processor.py` with the following content:

```python
# scripts/data_processor.py
import pandas as pd
import os
import numpy as np

# Create output directory
output_dir = "data/processed"
os.makedirs(output_dir, exist_ok=True)

# Source data directory
source_dir = "semantic_layers/base_analysis"

# Process each file
files = [
    "gross_change_ensemble_all.parquet",
    "urbanization_trends.parquet",
    "to_urban_transitions.parquet",
    "from_forest_transitions.parquet",
    "county_transitions.parquet"
]

def reduce_gross_change(df):
    """Reduce the gross change ensemble dataset"""
    # Aggregate by region instead of county if applicable
    if 'region_name' in df.columns and 'county_name' in df.columns:
        df_small = df.groupby(['region_name', 'from_category', 'to_category']).agg({
            'total_area': 'sum',
            'scenario_name': 'first'  # Keep one scenario name as reference
        }).reset_index()
    else:
        # Otherwise take a sample of the most significant transitions
        df_small = df.sort_values('total_area', ascending=False).head(1000)
    
    return df_small

def reduce_urbanization_trends(df):
    """Reduce the urbanization trends dataset"""
    # Keep only key decades
    key_decades = ['2020-2030', '2040-2050', '2060-2070']
    df_small = df[df['decade_name'].isin(key_decades)]
    
    # If still too large, focus on high-growth regions
    if len(df_small) > 1000:
        # Sort by forest to urban conversion (assuming this is important)
        if 'forest_to_urban' in df_small.columns:
            df_small = df_small.sort_values('forest_to_urban', ascending=False).head(1000)
    
    return df_small

def reduce_transitions(df):
    """Reduce transition datasets (to_urban or from_forest)"""
    # Focus on largest transitions
    df_small = df.sort_values('total_area', ascending=False).head(1500)
    
    # Aggregate remaining into "Other" if needed
    if len(df) > 1500:
        remaining = df.iloc[1500:].copy()
        if 'from_category' in remaining.columns and 'to_category' in remaining.columns:
            agg_cols = ['scenario_name', 'decade_name']
            group_cols = agg_cols + ['from_category', 'to_category']
            
            aggregated = remaining.groupby(group_cols).agg({
                'total_area': 'sum'
            }).reset_index()
            
            # Add a note indicating this is aggregated data
            aggregated['note'] = 'Aggregated smaller transitions'
            
            df_small = pd.concat([df_small, aggregated])
    
    return df_small

def reduce_county_transitions(df):
    """Reduce the county-level transitions dataset"""
    # Keep only top counties by transition area
    if 'county_name' in df.columns and 'total_area' in df.columns:
        # Get top counties by total area
        top_counties = df.groupby('county_name')['total_area'].sum().nlargest(200).index
        df_small = df[df['county_name'].isin(top_counties)]
        
        # Aggregate remaining counties as "Other" by state
        if len(df) > len(df_small):
            remaining = df[~df['county_name'].isin(top_counties)].copy()
            
            if 'state_name' in remaining.columns:
                agg_cols = ['state_name', 'from_category', 'to_category', 'scenario_name', 'decade_name']
                aggregated = remaining.groupby(agg_cols).agg({
                    'total_area': 'sum'
                }).reset_index()
                aggregated['county_name'] = 'Other counties'
                
                df_small = pd.concat([df_small, aggregated])
    else:
        # If no county column, sample largest transitions
        df_small = df.sort_values('total_area', ascending=False).head(2000)
    
    return df_small

# Main processing function to apply appropriate reduction
def reduce_dataframe(df, filename):
    """Apply appropriate reduction technique based on file type"""
    print(f"Processing {filename} - Original size: {len(df)} rows")
    
    if "gross_change_ensemble" in filename:
        df_small = reduce_gross_change(df)
    elif "urbanization_trends" in filename:
        df_small = reduce_urbanization_trends(df)
    elif "county_transitions" in filename:
        df_small = reduce_county_transitions(df)
    elif "to_urban" in filename or "from_forest" in filename:
        df_small = reduce_transitions(df)
    else:
        # Default: take a sample of significant data points
        df_small = df.sample(min(1000, len(df)))
    
    print(f"Reduced {filename} to {len(df_small)} rows")
    return df_small

# Process each file
for file in files:
    try:
        # Load original data
        source_path = os.path.join(source_dir, file)
        print(f"Loading {source_path}")
        df = pd.read_parquet(source_path)
        
        # Apply reduction techniques
        df_small = reduce_dataframe(df, file)
        
        # Save to new location
        output_path = os.path.join(output_dir, file)
        df_small.to_parquet(output_path)
        
        # Report file size reduction
        original_size = os.path.getsize(source_path) / (1024 * 1024)  # MB
        new_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        print(f"File size reduced from {original_size:.2f}MB to {new_size:.2f}MB")
        
    except Exception as e:
        print(f"Error processing {file}: {e}")
```

### 2. Create Directory Structure

Ensure the following directory structure exists:

```
rpa-landuse/
  ├── data/
  │   └── processed/           # This will store the smaller parquet files
  ├── scripts/
  │   └── data_processor.py    # The script you created above
  ├── semantic_layers/         # Original data location
  │   └── base_analysis/       # Contains the original large parquet files
  └── .gitignore               # Update this (see below)
```

### 3. Update the .gitignore File

Add the following to your `.gitignore` file:

```
# Ignore large original data files
semantic_layers/base_analysis/*.parquet

# Keep processed data files
!data/processed/*.parquet
```

### 4. Run the Data Processing Script

Run the script to create smaller datasets:

```bash
# Make sure you're in the project root
mkdir -p scripts data/processed
# Add the data_processor.py code to scripts/data_processor.py
python scripts/data_processor.py
```

### 5. Update the App Code

Modify `app.py` to use the new data location:

```python
@st.cache_data
def load_parquet_data():
    # Use processed data for deployed app
    data_dir = "data/processed"
    
    try:
        # Load the reduced dataset
        raw_data = {
            "Average Gross Change Across All Scenarios (2020-2070)": pd.read_parquet(os.path.join(data_dir, "gross_change_ensemble_all.parquet")),
            "Urbanization Trends By Decade": pd.read_parquet(os.path.join(data_dir, "urbanization_trends.parquet")),
            "Transitions to Urban Land": pd.read_parquet(os.path.join(data_dir, "to_urban_transitions.parquet")),
            "Transitions from Forest Land": pd.read_parquet(os.path.join(data_dir, "from_forest_transitions.parquet")),
            "County-Level Land Use Transitions": pd.read_parquet(os.path.join(data_dir, "county_transitions.parquet"))
        }
        
        # Note about reduced dataset (optional)
        st.sidebar.info("Note: This app uses a reduced dataset optimized for web deployment.")
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
```

### 6. Test Locally

Test the app locally with the reduced dataset:

```bash
streamlit run app.py
```

Ensure all visualizations and functionality still work with the reduced data.

### 7. Push to GitHub and Deploy

Commit and push all changes to GitHub:

```bash
git add data/processed/*.parquet
git add scripts/data_processor.py
git add app.py
git add .gitignore
git commit -m "Add reduced datasets for Streamlit Cloud deployment"
git push
```

### 8. Verify Deployment

After pushing to GitHub, deploy the app on Streamlit Cloud and verify that it loads correctly.

## Advanced Considerations

### Local vs. Cloud Switch (Optional)

You could add a feature to switch between the full and reduced datasets:

```python
@st.cache_data
def load_parquet_data():
    # Option to toggle between full and reduced datasets
    use_full_data = st.sidebar.checkbox("Use full dataset (local only)", value=False)
    
    if use_full_data:
        # Original data path (will only work locally)
        data_dir = "semantic_layers/base_analysis"
    else:
        # Reduced data path (works on Streamlit Cloud)
        data_dir = "data/processed"
    
    try:
        # Load data...
```

### Documentation

Add a note to your README.md explaining the data reduction approach, including:

1. What data is included in the reduced dataset
2. What aggregation or sampling methods were used
3. Limitations of the reduced dataset compared to the full version

## Troubleshooting

- If the reduced datasets are still too large (>100MB), consider further aggregation or sampling
- If specific visualizations don't work with reduced data, adjust the reduction strategy to preserve the necessary data points
- For deployment issues, check the Streamlit Cloud logs for specific error messages

## References

- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [GitHub Large File Storage](https://git-lfs.github.com/) (alternative if data is still too large)
- [Streamlit Deployment Guide](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app) 