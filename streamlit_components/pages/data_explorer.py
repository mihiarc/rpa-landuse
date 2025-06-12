"""
Data Explorer page for the RPA Land Use Viewer application.

Provides interactive data exploration and filtering capabilities.
"""
import streamlit as st
import pandas as pd
from typing import Dict
from ..config.constants import SCENARIO_NAMES


def render_data_explorer_page(data: Dict[str, pd.DataFrame]):
    """
    Render the data explorer page with filtering and export options.
    
    Args:
        data: Dictionary of loaded datasets
    """
    st.markdown("### Explore Land Use Transition Data")
    st.markdown("Filter and analyze land use changes across different scenarios and time periods.")
    
    # Dataset selection
    dataset_name = st.selectbox(
        "Select Dataset",
        list(data.keys()),
        help="Choose which dataset to explore"
    )
    
    if dataset_name not in data:
        st.error(f"Dataset '{dataset_name}' not found")
        return
        
    df = data[dataset_name]
    
    # Display dataset info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Records", f"{len(df):,}")
    with col2:
        st.metric("Columns", len(df.columns))
    with col3:
        if 'total_area' in df.columns:
            st.metric("Total Area", f"{df['total_area'].sum():,.0f} acres")
    
    # Filtering options
    st.markdown("#### Filter Options")
    
    filter_cols = st.columns(3)
    
    # Scenario filter
    with filter_cols[0]:
        if 'scenario_name' in df.columns:
            scenarios = ['All'] + sorted(df['scenario_name'].unique().tolist())
            selected_scenario = st.selectbox("Scenario", scenarios)
            if selected_scenario != 'All':
                df = df[df['scenario_name'] == selected_scenario]
    
    # State filter
    with filter_cols[1]:
        if 'state_name' in df.columns:
            states = ['All'] + sorted(df['state_name'].unique().tolist())
            selected_state = st.selectbox("State", states)
            if selected_state != 'All':
                df = df[df['state_name'] == selected_state]
    
    # Time period filter
    with filter_cols[2]:
        if 'decade_name' in df.columns:
            decades = ['All'] + sorted(df['decade_name'].unique().tolist())
            selected_decade = st.selectbox("Decade", decades)
            if selected_decade != 'All':
                df = df[df['decade_name'] == selected_decade]
    
    # Additional filters for land use transitions
    if 'from_category' in df.columns and 'to_category' in df.columns:
        st.markdown("#### Land Use Transition Filters")
        trans_cols = st.columns(2)
        
        with trans_cols[0]:
            from_cats = ['All'] + sorted(df['from_category'].unique().tolist())
            selected_from = st.selectbox("From Land Use", from_cats)
            if selected_from != 'All':
                df = df[df['from_category'] == selected_from]
        
        with trans_cols[1]:
            to_cats = ['All'] + sorted(df['to_category'].unique().tolist())
            selected_to = st.selectbox("To Land Use", to_cats)
            if selected_to != 'All':
                df = df[df['to_category'] == selected_to]
    
    # Display filtered data
    st.markdown(f"#### Filtered Data ({len(df):,} records)")
    
    # Aggregation options
    if st.checkbox("Show aggregated view"):
        agg_cols = st.multiselect(
            "Group by columns",
            [col for col in df.columns if col not in ['total_area', 'area']],
            default=['scenario_name'] if 'scenario_name' in df.columns else []
        )
        
        if agg_cols and any(col in df.columns for col in ['total_area', 'area']):
            value_col = 'total_area' if 'total_area' in df.columns else 'area'
            agg_df = df.groupby(agg_cols)[value_col].sum().reset_index()
            agg_df = agg_df.sort_values(value_col, ascending=False)
            st.dataframe(agg_df, use_container_width=True)
        else:
            st.dataframe(df, use_container_width=True)
    else:
        # Show raw data with column selection
        show_cols = st.multiselect(
            "Select columns to display",
            df.columns.tolist(),
            default=df.columns.tolist()[:10]  # Show first 10 columns by default
        )
        if show_cols:
            st.dataframe(df[show_cols], use_container_width=True)
        else:
            st.warning("Please select at least one column to display")
    
    # Export options
    st.markdown("#### Export Data")
    export_cols = st.columns(3)
    
    with export_cols[0]:
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download as CSV",
            data=csv,
            file_name=f"{dataset_name.lower().replace(' ', '_')}_filtered.csv",
            mime="text/csv"
        )
    
    with export_cols[1]:
        # Summary statistics
        if st.button("Show Summary Statistics"):
            st.markdown("##### Summary Statistics")
            st.dataframe(df.describe(), use_container_width=True)
    
    with export_cols[2]:
        # Data quality check
        if st.button("Data Quality Check"):
            st.markdown("##### Data Quality Report")
            null_counts = df.isnull().sum()
            quality_df = pd.DataFrame({
                'Column': null_counts.index,
                'Null Count': null_counts.values,
                'Null %': (null_counts.values / len(df) * 100).round(2)
            })
            quality_df = quality_df[quality_df['Null Count'] > 0]
            if len(quality_df) > 0:
                st.dataframe(quality_df, use_container_width=True)
            else:
                st.success("No missing values found in the dataset!")