"""
Land Use Flow Diagrams tab implementation.

This tab provides a visualization of land use transition flows using Sankey diagrams.
The Sankey diagrams show the flow of land from one use type to another, with the 
width of each flow representing the total acres converted between land use categories.
"""

import streamlit as st
import pandas as pd
from .base_tab import BaseTab
from ..utils.visualizations import ChartUtils
from ..config import SCENARIO_DESCRIPTIONS, KEY_SCENARIOS


class LandUseFlowsTab(BaseTab):
    """Land Use Flow Diagrams tab showing Sankey diagrams."""
    
    def render(self) -> None:
        """Render the land use flows tab content."""
        st.header("🌊 Land Use Transition Flow Diagrams")
        
        st.markdown("""
        Sankey diagrams show the flow of land from one use type to another. The width of each flow 
        represents the total acres converted between land use categories over the selected time period.
        
        💡 **Tip**: If the chart appears cut off, use the "Chart Height" slider in Advanced Filters to adjust the display size.
        """)
        
        # Get county transitions data 
        if 'County-Level Land Use Transitions' not in self.data:
            st.error("County-Level Land Use Transitions data not available")
            return
            
        county_df = self.data["County-Level Land Use Transitions"]
        
        # Filter for only the 5 key RPA scenarios
        county_df = county_df[county_df["scenario_name"].isin(KEY_SCENARIOS)]
        
        # Controls for Sankey diagram
        st.subheader("Diagram Controls")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            # Scenario selection
            sankey_scenarios = county_df["scenario_name"].unique().tolist()
            scenario_options = [SCENARIO_DESCRIPTIONS.get(scenario, scenario) for scenario in sankey_scenarios]
            selected_scenario_display = st.selectbox(
                "Climate & Economic Scenario", 
                options=scenario_options,
                index=4,  # Default to Ensemble Projection
                key="sankey_scenario"
            )
            # Map back to original scenario name
            scenario_reverse_map = {v: k for k, v in SCENARIO_DESCRIPTIONS.items()}
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
            
            # Chart height adjustment
            chart_height = st.slider(
                "Chart Height (pixels)",
                min_value=600,
                max_value=1200,
                value=800,
                step=50,
                help="Adjust chart height if content is getting cut off",
                key="sankey_height"
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
            st.subheader(f"🌊 National Land Use Transitions")
            
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
                try:
                    sankey_fig = ChartUtils.create_sankey_diagram(
                        filtered_sankey_data, 
                        sankey_title,
                        selected_sankey_scenario,
                        height=chart_height
                    )
                    
                    st.plotly_chart(sankey_fig, use_container_width=True, key="national_sankey")
                    
                    # Show summary statistics
                    with st.expander("📊 Flow Summary Statistics"):
                        summary_stats = sankey_data.copy()
                        summary_stats["total_area"] = summary_stats["total_area"].map(lambda x: f"{x:,.0f}")
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
                        
                except Exception as e:
                    st.error(f"Error creating Sankey diagram: {e}")
                    self.logger.error(f"Sankey diagram creation failed: {e}")
            else:
                st.warning("No data available for the selected filters. Try adjusting your criteria.")
        
        else:
            # Multiple state diagrams
            st.subheader(f"🌊 Land Use Transitions by State")
            
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
                        try:
                            state_fig = ChartUtils.create_sankey_diagram(
                                state_data, 
                                state_title,
                                selected_sankey_scenario,
                                height=chart_height
                            )
                            
                            st.plotly_chart(state_fig, use_container_width=True, key=f"sankey_{state}")
                            
                            # Show summary for this state
                            with st.expander(f"📊 {state} Flow Summary"):
                                state_summary = state_sankey_data.copy()
                                state_summary["total_area"] = state_summary["total_area"].map(lambda x: f"{x:,.0f}")
                                state_summary.columns = ["From Land Use", "To Land Use", "Total Acres Converted"]
                                state_summary = state_summary.sort_values("Total Acres Converted", ascending=False)
                                st.dataframe(state_summary, use_container_width=True)
                                
                        except Exception as e:
                            st.error(f"Error creating Sankey diagram for {state}: {e}")
                            self.logger.error(f"Sankey diagram creation failed for {state}: {e}")
                    else:
                        st.info(f"No significant transitions found for {state} with current filters.")
            else:
                st.info("Please select at least one state to display diagrams.") 