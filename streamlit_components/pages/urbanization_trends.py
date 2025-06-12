"""
Urbanization Trends page for the RPA Land Use Viewer application.

Analyzes and visualizes urban development patterns and trends.
"""
import streamlit as st
import pandas as pd
import duckdb
import os
from typing import Dict
from ..components.visualizations import (
    create_bar_chart, create_time_series_plot, 
    display_metrics_row, create_pie_chart
)
from ..config.constants import SCENARIO_NAMES, DB_PATH


def render_urbanization_trends_page(data: Dict[str, pd.DataFrame]):
    """
    Render the urbanization trends analysis page.
    
    Args:
        data: Dictionary of loaded datasets
    """
    st.markdown("### Urbanization Trends Analysis")
    st.markdown("Explore patterns of urban development and identify areas experiencing rapid urbanization.")
    
    # Load urbanization trends data
    if "Urbanization Trends By Decade" not in data:
        st.error("Urbanization trends data not available")
        return
    
    urban_df = data["Urbanization Trends By Decade"]
    
    # Scenario selection
    scenario = st.selectbox(
        "Select Scenario", 
        SCENARIO_NAMES,
        help="Choose a scenario to analyze urbanization patterns"
    )
    
    # Filter data by scenario
    if scenario != "All Scenarios":
        urban_df_filtered = urban_df[urban_df['scenario_name'] == scenario]
    else:
        urban_df_filtered = urban_df
    
    # Display key metrics
    st.markdown("#### Key Urbanization Metrics")
    
    # Calculate metrics
    total_to_urban = urban_df_filtered[['forest_to_urban', 'cropland_to_urban', 'pasture_to_urban']].sum().sum()
    forest_to_urban = urban_df_filtered['forest_to_urban'].sum()
    cropland_to_urban = urban_df_filtered['cropland_to_urban'].sum()
    pasture_to_urban = urban_df_filtered['pasture_to_urban'].sum()
    
    metrics = {
        "Total Land to Urban": (f"{total_to_urban:,.0f} acres", None),
        "Forest to Urban": (f"{forest_to_urban:,.0f} acres", f"{forest_to_urban/total_to_urban*100:.1f}%"),
        "Cropland to Urban": (f"{cropland_to_urban:,.0f} acres", f"{cropland_to_urban/total_to_urban*100:.1f}%"),
        "Pasture to Urban": (f"{pasture_to_urban:,.0f} acres", f"{pasture_to_urban/total_to_urban*100:.1f}%")
    }
    
    display_metrics_row(metrics)
    
    # Analysis options  
    tab1, tab2, tab3, tab4 = st.tabs([
        "Temporal Trends", 
        "Scenario Comparison", 
        "Land Source Analysis",
        "County Hotspots"
    ])
    
    with tab1:
        st.markdown("##### Urbanization Over Time")
        
        # Aggregate by decade for national trends
        decade_trends = urban_df_filtered.groupby('decade_name')[
            ['forest_to_urban', 'cropland_to_urban', 'pasture_to_urban']
        ].sum().reset_index()
        
        if not decade_trends.empty:
            fig = create_time_series_plot(
                decade_trends,
                'decade_name',
                ['forest_to_urban', 'cropland_to_urban', 'pasture_to_urban'],
                title="National Urban Development by Source Land Type",
                xlabel="Decade",
                ylabel="Area Converted to Urban (acres)"
            )
            st.pyplot(fig)
            
            # Show data table
            st.markdown("##### Detailed Temporal Data")
            st.dataframe(decade_trends, use_container_width=True)
        else:
            st.warning("No temporal data available for the selected scenario")
    
    with tab2:
        st.markdown("##### Scenario Comparison")
        
        if scenario == "All Scenarios":
            # Compare all scenarios
            scenario_comparison = urban_df.groupby('scenario_name')[
                ['forest_to_urban', 'cropland_to_urban', 'pasture_to_urban']
            ].sum().reset_index()
            
            scenario_comparison['total_to_urban'] = scenario_comparison[['forest_to_urban', 'cropland_to_urban', 'pasture_to_urban']].sum(axis=1)
            scenario_comparison = scenario_comparison.sort_values('total_to_urban', ascending=False)
            
            if not scenario_comparison.empty:
                fig = create_bar_chart(
                    scenario_comparison,
                    'scenario_name',
                    'total_to_urban',
                    title="Total Urban Development by Scenario (2020-2070)",
                    xlabel="Scenario",
                    ylabel="Total Area Converted to Urban (acres)",
                    color="#DC143C"
                )
                st.pyplot(fig)
                
                # Show detailed breakdown
                st.markdown("##### Scenario Breakdown by Land Source")
                st.dataframe(scenario_comparison, use_container_width=True)
            else:
                st.warning("No scenario data available")
        else:
            st.info(f"Showing data for scenario: {scenario}. Select 'All Scenarios' to compare different scenarios.")
    
    with tab3:
        st.markdown("##### Sources of New Urban Land")
        
        # Create pie chart of land sources
        source_data = pd.DataFrame({
            'Source': ['Forest', 'Cropland', 'Pasture'],
            'Area': [forest_to_urban, cropland_to_urban, pasture_to_urban]
        })
        
        if source_data['Area'].sum() > 0:
            fig = create_pie_chart(
                source_data,
                'Source',
                'Area',
                title="Distribution of Land Sources for Urban Development"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Additional analysis
            st.markdown("##### Conversion Rate Analysis")
            
            # Calculate conversion rates over time
            if scenario != "All Scenarios":
                total_conversion = urban_df_filtered[['forest_to_urban', 'cropland_to_urban', 'pasture_to_urban']].sum(axis=1)
                urban_df_filtered_copy = urban_df_filtered.copy()
                urban_df_filtered_copy['total_conversion'] = total_conversion
                
                avg_per_decade = urban_df_filtered_copy.groupby('decade_name')['total_conversion'].mean()
                
                if not avg_per_decade.empty:
                    st.markdown("Average conversion per decade:")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        for decade, value in avg_per_decade.items():
                            st.metric(decade, f"{value:,.0f} acres")
                    
                    with col2:
                        # Calculate rate of change
                        rate_change = avg_per_decade.pct_change().fillna(0) * 100
                        st.markdown("Rate of change between decades:")
                        for decade, rate in rate_change.items():
                            if rate != 0:
                                st.write(f"{decade}: {rate:+.1f}%")
        else:
            st.warning("No urbanization data available for analysis")
    
    with tab4:
        st.markdown("##### County-Level Urban Hotspots")
        
        # Use county-level data if available
        if "County-Level Land Use Transitions" in data:
            county_df = data["County-Level Land Use Transitions"]
            
            # Filter for urban transitions
            to_urban = county_df[county_df['to_category'] == 'Urban'] if 'to_category' in county_df.columns else pd.DataFrame()
            
            if not to_urban.empty:
                if scenario != "All Scenarios" and 'scenario_name' in to_urban.columns:
                    to_urban = to_urban[to_urban['scenario_name'] == scenario]
                
                # Group by state and county if these columns exist
                if 'state_name' in to_urban.columns and 'county_name' in to_urban.columns:
                    county_summary = to_urban.groupby(['state_name', 'county_name'])['total_area'].sum().reset_index()
                    county_summary = county_summary.sort_values('total_area', ascending=False)
                    
                    # Show top counties
                    top_n = st.slider("Number of top counties to display", 10, 50, 20)
                    top_counties = county_summary.head(top_n)
                    
                    st.markdown(f"Top {top_n} counties by urban development:")
                    
                    # Format for display
                    display_df = top_counties.copy()
                    display_df.columns = ['State', 'County', 'Total Urban Growth (acres)']
                    display_df['Total Urban Growth (acres)'] = display_df['Total Urban Growth (acres)'].apply(lambda x: f"{x:,.0f}")
                    
                    st.dataframe(display_df, use_container_width=True)
                    
                    # Export option
                    csv = top_counties.to_csv(index=False)
                    st.download_button(
                        label="Download County Hotspots Data",
                        data=csv,
                        file_name=f"urban_hotspots_{scenario.lower().replace(' ', '_')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("County-level breakdown not available in current dataset structure")
            else:
                st.info("No urban transition data found in county dataset")
        else:
            # Try database connection as fallback
            try:
                @st.cache_data
                def load_county_urban_hotspots():
                    """Load county-level urbanization hotspots from database."""
                    if not os.path.exists(DB_PATH):
                        return pd.DataFrame()
                    
                    conn = duckdb.connect(DB_PATH, read_only=True)
                    query = """
                    SELECT 
                        state_name,
                        county_name,
                        scenario_name,
                        SUM(CASE WHEN to_category = 'Urban' THEN total_area ELSE 0 END) as total_to_urban
                    FROM county_level_transitions
                    WHERE to_category = 'Urban'
                    GROUP BY state_name, county_name, scenario_name
                    ORDER BY total_to_urban DESC
                    """
                    df = conn.execute(query).fetchdf()
                    conn.close()
                    return df
                
                hotspots_df = load_county_urban_hotspots()
                
                if not hotspots_df.empty:
                    if scenario != "All Scenarios":
                        hotspots_df = hotspots_df[hotspots_df['scenario_name'] == scenario]
                    
                    top_n = st.slider("Number of top counties to display", 10, 50, 20)
                    top_counties = hotspots_df.nlargest(top_n, 'total_to_urban')
                    
                    st.markdown(f"Top {top_n} counties by urban development:")
                    st.dataframe(top_counties, use_container_width=True)
                else:
                    st.info("No county-level data available. County analysis requires database access.")
                    
            except Exception as e:
                st.info("County-level analysis not available. This feature requires database connectivity.")