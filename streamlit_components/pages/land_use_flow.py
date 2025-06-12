"""
Land Use Flow Diagrams page for the RPA Land Use Viewer application.

Displays Sankey diagrams showing transitions between land use categories.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Optional, List
from ..config.constants import COLOR_SCHEMES


def create_sankey_diagram(transitions_data: pd.DataFrame, title: str, 
                         scenario_name: str) -> go.Figure:
    """
    Create a Sankey diagram showing land use transitions.
    
    Args:
        transitions_data: DataFrame with from_category, to_category, and total_area columns
        title: Title for the diagram
        scenario_name: Scenario name for filtering
    
    Returns:
        go.Figure: Plotly Sankey diagram
    """
    # Filter data for the specific scenario
    filtered_data = transitions_data[transitions_data["scenario_name"] == scenario_name]
    
    # Aggregate data across all time periods
    sankey_data = filtered_data.groupby(["from_category", "to_category"])["total_area"].sum().reset_index()
    
    # Filter out transitions where land use stays the same
    sankey_data = sankey_data[sankey_data["from_category"] != sankey_data["to_category"]]
    
    # Get unique land use categories
    all_categories = list(set(sankey_data["from_category"].unique()) | set(sankey_data["to_category"].unique()))
    
    # Create node indices
    node_indices = {category: i for i, category in enumerate(all_categories)}
    
    # Prepare data for Sankey
    source = [node_indices[cat] for cat in sankey_data["from_category"]]
    target = [node_indices[cat] for cat in sankey_data["to_category"]]
    value = sankey_data["total_area"].tolist()
    
    # Define colors for different land use types
    color_map = {
        'Forest': '#228B22',      # Forest Green
        'Cropland': '#FFD700',    # Gold
        'Pasture': '#90EE90',     # Light Green
        'Urban': '#FF6347',       # Tomato Red
        'Other': '#D3D3D3',       # Light Gray
        'Range': '#DEB887',       # Burlywood
        'Water': '#4169E1',       # Royal Blue
        'Federal': '#8B4513'      # Saddle Brown
    }
    
    # Assign colors to nodes
    node_colors = [color_map.get(cat, '#D3D3D3') for cat in all_categories]
    
    # Create Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=25,  # Increased padding between nodes for better spacing
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_categories,
            color=node_colors
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color='rgba(255, 0, 255, 0.4)'  # Semi-transparent links
        )
    )])
    
    # Calculate dynamic height based on number of categories
    num_categories = len(all_categories)
    dynamic_height = max(800, 100 * num_categories)  # At least 100px per category
    
    fig.update_layout(
        title_text=title,
        font_size=12,
        height=dynamic_height,  # Dynamic height based on categories
        margin=dict(l=30, r=30, t=80, b=120)  # Increased margins all around
    )
    
    return fig


def render_land_use_flow_page(data: Dict[str, pd.DataFrame]):
    """
    Render the land use flow diagrams page.
    
    Args:
        data: Dictionary of loaded datasets
    """
    st.header("🌊 Land Use Transition Flow Diagrams")
    
    st.markdown("""
    Sankey diagrams show the flow of land from one use type to another. The width of each flow 
    represents the total acres converted between land use categories over the selected time period.
    """)
    
    # Check if county transitions data is available
    if "County-Level Land Use Transitions" not in data:
        st.error("County-level land use transitions data not available")
        return
    
    # Get county transitions data
    county_df = data["County-Level Land Use Transitions"]
    
    # Filter for only the 5 key RPA scenarios
    key_scenarios = [
        'ensemble_LM',    # Lower warming-moderate growth (RCP4.5-SSP1)
        'ensemble_HL',    # High warming-low growth (RCP8.5-SSP3)
        'ensemble_HM',    # High warming-moderate growth (RCP8.5-SSP2)
        'ensemble_HH',    # High warming-high growth (RCP8.5-SSP5)
        'ensemble_overall' # Overall mean projection
    ]
    
    # Check which scenarios are actually available in the data
    available_scenarios = county_df["scenario_name"].unique()
    scenarios_to_use = [s for s in key_scenarios if s in available_scenarios]
    
    if not scenarios_to_use:
        # If none of the key scenarios are found, use what's available
        scenarios_to_use = list(available_scenarios)
    
    county_df = county_df[county_df["scenario_name"].isin(scenarios_to_use)]
    
    # Controls for Sankey diagram
    st.subheader("Diagram Controls")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        # Scenario selection
        scenario_descriptions = {
            'ensemble_LM': 'Sustainable Development (RCP4.5-SSP1)',
            'ensemble_HL': 'Climate Challenge (RCP8.5-SSP3)', 
            'ensemble_HM': 'Moderate Growth (RCP8.5-SSP2)',
            'ensemble_HH': 'High Development (RCP8.5-SSP5)',
            'ensemble_overall': 'Ensemble Projection (All Scenarios)'
        }
        
        sankey_scenarios = county_df["scenario_name"].unique().tolist()
        scenario_options = [scenario_descriptions.get(scenario, scenario) for scenario in sankey_scenarios]
        
        # Find index for default selection
        default_idx = 0
        if 'ensemble_overall' in sankey_scenarios:
            default_idx = sankey_scenarios.index('ensemble_overall')
        
        selected_scenario_display = st.selectbox(
            "Climate & Economic Scenario", 
            options=scenario_options,
            index=default_idx,
            key="sankey_scenario"
        )
        
        # Map back to original scenario name
        scenario_reverse_map = {v: k for k, v in scenario_descriptions.items()}
        selected_sankey_scenario = scenario_reverse_map.get(selected_scenario_display, selected_scenario_display)
    
    with col2:
        # Time period selection
        sankey_decades = county_df["decade_name"].unique().tolist()
        sankey_decades.sort()
        selected_time_period = st.selectbox(
            "Time Period", 
            options=["All Periods"] + sankey_decades,
            key="sankey_time"
        )
    
    with col3:
        # Geographic scope
        geographic_scope = st.selectbox(
            "Geographic Scope",
            options=["National", "By State"],
            key="sankey_scope"
        )
    
    # Advanced filters
    with st.expander("🔍 Advanced Filters"):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # From land use filter
            all_from_categories = county_df["from_category"].unique().tolist()
            all_from_categories.sort()
            selected_from_categories = st.multiselect(
                "From Land Use Types (leave empty for all)",
                options=all_from_categories,
                key="sankey_from"
            )
        
        with col2:
            # To land use filter
            all_to_categories = county_df["to_category"].unique().tolist()
            all_to_categories.sort()
            selected_to_categories = st.multiselect(
                "To Land Use Types (leave empty for all)",
                options=all_to_categories,
                key="sankey_to"
            )
        
        # Minimum flow threshold
        min_threshold = st.slider(
            "Minimum Flow Threshold (acres)",
            min_value=0,
            max_value=100000,
            value=1000,
            step=1000,
            help="Hide flows smaller than this threshold to reduce clutter",
            key="sankey_threshold"
        )
    
    # Filter data based on selections
    filtered_sankey_data = county_df[county_df["scenario_name"] == selected_sankey_scenario]
    
    # Apply time period filter
    if selected_time_period != "All Periods":
        filtered_sankey_data = filtered_sankey_data[filtered_sankey_data["decade_name"] == selected_time_period]
    
    # Apply land use filters
    if selected_from_categories:
        filtered_sankey_data = filtered_sankey_data[filtered_sankey_data["from_category"].isin(selected_from_categories)]
    
    if selected_to_categories:
        filtered_sankey_data = filtered_sankey_data[filtered_sankey_data["to_category"].isin(selected_to_categories)]
    
    # Create Sankey diagram(s)
    if geographic_scope == "National":
        # Single national diagram
        st.subheader("🌊 National Land Use Transitions")
        
        # Aggregate data
        sankey_data = filtered_sankey_data.groupby(["from_category", "to_category"])["total_area"].sum().reset_index()
        
        # Apply threshold filter
        sankey_data = sankey_data[sankey_data["total_area"] >= min_threshold]
        
        # Filter out transitions where land use stays the same
        sankey_data = sankey_data[sankey_data["from_category"] != sankey_data["to_category"]]
        
        if len(sankey_data) > 0:
            # Create title
            time_text = f" ({selected_time_period})" if selected_time_period != "All Periods" else " (2020-2070)"
            sankey_title = f"National Land Use Transitions - {selected_scenario_display}{time_text}"
            
            # Create Sankey diagram
            sankey_fig = create_sankey_diagram(
                filtered_sankey_data, 
                sankey_title,
                selected_sankey_scenario
            )
            
            st.plotly_chart(sankey_fig, use_container_width=True, key="national_sankey")
            
            # Show summary statistics
            with st.expander("📊 Flow Summary Statistics"):
                summary_stats = sankey_data.copy()
                summary_stats["total_area"] = summary_stats["total_area"].apply(lambda x: f"{x:,.0f}")
                summary_stats.columns = ["From Land Use", "To Land Use", "Total Acres Converted"]
                summary_stats = summary_stats.sort_values("Total Acres Converted", ascending=False)
                st.dataframe(summary_stats, use_container_width=True)
                
                # Download option
                csv_data = sankey_data.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Flow Data (CSV)",
                    data=csv_data,
                    file_name=f"land_use_flows_{selected_sankey_scenario}_{selected_time_period}.csv",
                    mime="text/csv"
                )
        else:
            st.warning("No data available for the selected filters. Try adjusting your criteria.")
    
    else:
        # Multiple state diagrams
        st.subheader("🌊 Land Use Transitions by State")
        
        # Get available states
        available_states = filtered_sankey_data["state_name"].unique().tolist()
        available_states.sort()
        
        # State selection
        selected_states = st.multiselect(
            "Select States to Display (max 4 for readability)",
            options=available_states,
            default=available_states[:2] if len(available_states) >= 2 else available_states,
            max_selections=4,
            key="sankey_states"
        )
        
        if selected_states:
            # Create diagrams for each selected state
            for state in selected_states:
                state_data = filtered_sankey_data[filtered_sankey_data["state_name"] == state]
                
                # Aggregate data for this state
                state_sankey_data = state_data.groupby(["from_category", "to_category"])["total_area"].sum().reset_index()
                
                # Apply threshold filter
                state_sankey_data = state_sankey_data[state_sankey_data["total_area"] >= min_threshold]
                
                # Filter out transitions where land use stays the same
                state_sankey_data = state_sankey_data[state_sankey_data["from_category"] != state_sankey_data["to_category"]]
                
                if len(state_sankey_data) > 0:
                    # Create title
                    time_text = f" ({selected_time_period})" if selected_time_period != "All Periods" else " (2020-2070)"
                    state_title = f"{state} Land Use Transitions - {selected_scenario_display}{time_text}"
                    
                    # Create Sankey diagram
                    state_fig = create_sankey_diagram(
                        state_data, 
                        state_title,
                        selected_sankey_scenario
                    )
                    
                    st.plotly_chart(state_fig, use_container_width=True, key=f"sankey_{state}")
                    
                    # Show summary for this state
                    with st.expander(f"📊 {state} Flow Summary"):
                        state_summary = state_sankey_data.copy()
                        state_summary["total_area"] = state_summary["total_area"].apply(lambda x: f"{x:,.0f}")
                        state_summary.columns = ["From Land Use", "To Land Use", "Total Acres Converted"]
                        state_summary = state_summary.sort_values("Total Acres Converted", ascending=False)
                        st.dataframe(state_summary, use_container_width=True)
                else:
                    st.info(f"No significant transitions found for {state} with current filters.")
        else:
            st.info("Please select at least one state to display diagrams.")