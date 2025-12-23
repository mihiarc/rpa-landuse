"""Main Analytics Dashboard UI orchestration.

This module contains the main() function and tab rendering logic.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

from landuse.utils.state_mappings import StateMapper

from .charts import (
    create_agricultural_flow_chart,
    create_agricultural_state_map,
    create_choropleth_map,
    create_forest_flow_chart,
    create_forest_state_map,
    create_sankey_diagram,
    create_scenario_spider_chart,
)
from .constants import (
    RPA_BROWN_SCALE,
    RPA_COLOR_SEQUENCE,
    RPA_COLORS,
    RPA_GREEN_SCALE,
)
from .data_loaders import (
    get_database_connection,
    load_agricultural_analysis_data,
    load_forest_analysis_data,
    load_sankey_data,
    load_scenario_comparison_data,
    load_state_transitions,
    load_urbanization_data,
)


def render_forest_overview(df_loss: pd.DataFrame, df_gain: pd.DataFrame) -> None:
    """Render the forest overview tab content."""
    st.markdown("#### Forest Transition Overview")

    if df_loss is None or df_gain is None:
        st.info("No forest transition data available")
        return

    # Wide layout with main visualization and side metrics
    main_col, metrics_col = st.columns([4, 2])

    with main_col:
        fig = create_forest_flow_chart(df_loss, df_gain)
        if fig:
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

    with metrics_col:
        total_loss = df_loss["total_acres"].sum()
        total_gain = df_gain["total_acres"].sum()
        net_change = total_gain - total_loss

        st.markdown("#### Forest Metrics")

        st.metric(
            "Total Forest Loss",
            f"{total_loss / 1e6:.1f}M acres",
            help="Total forest converted to other land uses",
        )

        st.metric(
            "Total Forest Gain",
            f"{total_gain / 1e6:.1f}M acres",
            help="Total land converted to forest",
        )

        st.metric(
            "Net Change",
            f"{net_change / 1e6:+.1f}M acres",
            delta=f"{(net_change / total_loss) * 100:+.1f}%",
            help="Net forest change across all scenarios",
        )

        if net_change < 0:
            st.error(f"Net forest loss of {abs(net_change / 1e6):.1f}M acres projected")
        else:
            st.success(f"Net forest gain of {net_change / 1e6:.1f}M acres projected")

    # Detailed breakdowns
    st.markdown("---")
    detail_col1, detail_col2, detail_col3 = st.columns([2, 2, 2])

    with detail_col1:
        st.markdown("##### Forest Loss Destinations")
        loss_summary = df_loss.groupby("to_landuse")["total_acres"].sum().sort_values(ascending=False)

        fig_loss = px.bar(
            x=loss_summary.values,
            y=loss_summary.index,
            orientation="h",
            title="Where Forests Convert To",
            labels={"x": "Acres", "y": "Land Use Type"},
            color=loss_summary.values,
            color_continuous_scale=RPA_BROWN_SCALE,
        )
        fig_loss.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_loss, use_container_width=True)

    with detail_col2:
        st.markdown("##### Forest Gain Sources")
        gain_summary = df_gain.groupby("from_landuse")["total_acres"].sum().sort_values(ascending=False)

        fig_gain = px.bar(
            x=gain_summary.values,
            y=gain_summary.index,
            orientation="h",
            title="Where Forest Gains Come From",
            labels={"x": "Acres", "y": "Land Use Type"},
            color=gain_summary.values,
            color_continuous_scale=RPA_GREEN_SCALE,
        )
        fig_gain.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_gain, use_container_width=True)

    with detail_col3:
        st.markdown("##### Transition Summary")
        loss_pct = loss_summary / loss_summary.sum() * 100
        gain_pct = gain_summary / gain_summary.sum() * 100

        summary_data = []
        for landuse in set(loss_summary.index) | set(gain_summary.index):
            summary_data.append({
                "Land Use": landuse,
                "Loss %": f"{loss_pct.get(landuse, 0):.1f}%" if landuse in loss_pct else "-",
                "Gain %": f"{gain_pct.get(landuse, 0):.1f}%" if landuse in gain_pct else "-",
            })

        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)


def render_forest_geographic(df_states: pd.DataFrame) -> None:
    """Render the forest geographic distribution tab."""
    st.markdown("#### Geographic Distribution of Forest Changes")

    if df_states is None or df_states.empty:
        st.info("No geographic data available")
        return

    with st.expander("Understanding the Map Metric", expanded=False):
        st.info("""
        **How to interpret the percentage change:**

        This map shows the **change in forest transition activity between 2020-2030 and 2060-2070**:
        - **Negative % (purple)**: Decreasing forest transition activity over time
        - **Near 0% (teal)**: Stable forest transition activity
        - **Positive % (yellow)**: Increasing forest transition activity over time

        **Formula:** ((2070 Activity - 2025 Activity) / 2025 Activity) x 100
        """)

    fig = create_forest_state_map(df_states)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False})

    # State rankings
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Top States - Forest Gain (%)")
        top_gain_states = df_states.nlargest(10, "percent_change")[
            ["state_name", "percent_change", "net_change", "forest_gain"]
        ]
        top_gain_states["Percent Change"] = top_gain_states["percent_change"].apply(lambda x: f"{x:+.1f}%")
        top_gain_states["Net Change"] = top_gain_states["net_change"].apply(lambda x: f"{x / 1e6:+.2f}M")
        top_gain_states["Total Gain"] = top_gain_states["forest_gain"].apply(lambda x: f"{x / 1e6:.2f}M")
        display_df = top_gain_states[["state_name", "Percent Change", "Net Change", "Total Gain"]].copy()
        st.dataframe(display_df.rename(columns={"state_name": "State"}), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("##### Top States - Forest Loss (%)")
        top_loss_states = df_states.nsmallest(10, "percent_change")[
            ["state_name", "percent_change", "net_change", "forest_loss"]
        ]
        top_loss_states["Percent Change"] = top_loss_states["percent_change"].apply(lambda x: f"{x:+.1f}%")
        top_loss_states["Net Change"] = top_loss_states["net_change"].apply(lambda x: f"{x / 1e6:+.2f}M")
        top_loss_states["Total Loss"] = top_loss_states["forest_loss"].apply(lambda x: f"{x / 1e6:.2f}M")
        display_df = top_loss_states[["state_name", "Percent Change", "Net Change", "Total Loss"]].copy()
        st.dataframe(display_df.rename(columns={"state_name": "State"}), use_container_width=True, hide_index=True)

    # Summary insights
    st.markdown("##### Geographic Insights")
    gaining_states = len(df_states[df_states["net_change"] > 0])
    losing_states = len(df_states[df_states["net_change"] < 0])

    st.info(f"""
    **Key Findings:**
    - {gaining_states} states show net forest gain
    - {losing_states} states show net forest loss
    - Regional patterns suggest climate and development pressures vary significantly by location
    """)


def render_agricultural_overview(df_loss: pd.DataFrame, df_gain: pd.DataFrame) -> None:
    """Render the agricultural overview tab content."""
    st.markdown("#### Agricultural Transition Overview")

    if df_loss is None or df_gain is None:
        st.info("No data available for agricultural transitions")
        return

    main_col, metrics_col = st.columns([4, 2])

    with main_col:
        fig = create_agricultural_flow_chart(df_loss, df_gain)
        if fig:
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

    with metrics_col:
        total_loss = df_loss["total_acres"].sum()
        total_gain = df_gain["total_acres"].sum()
        net_change = total_gain - total_loss

        st.markdown("#### Agricultural Metrics")

        st.metric(
            "Total Agricultural Loss",
            f"{total_loss / 1e6:.1f}M acres",
            help="Total agricultural land converted to other uses",
        )

        st.metric(
            "Total Agricultural Gain",
            f"{total_gain / 1e6:.1f}M acres",
            help="Total land converted to agriculture",
        )

        st.metric(
            "Net Change",
            f"{net_change / 1e6:+.1f}M acres",
            delta=f"{(net_change / total_loss) * 100:+.1f}%" if total_loss > 0 else "N/A",
            help="Net agricultural change across all scenarios",
        )

        if net_change < 0:
            st.error(f"Net agricultural loss of {abs(net_change / 1e6):.1f}M acres projected")
        else:
            st.success(f"Net agricultural gain of {net_change / 1e6:.1f}M acres projected")

    # Detailed breakdowns
    st.markdown("---")
    detail_col1, detail_col2, detail_col3 = st.columns([2, 2, 2])

    with detail_col1:
        st.markdown("##### Agricultural Loss Destinations")
        loss_summary = df_loss.groupby("to_landuse")["total_acres"].sum().sort_values(ascending=False)

        fig_loss = px.bar(
            x=loss_summary.values[:5],
            y=loss_summary.index[:5],
            orientation="h",
            title="Where Agricultural Land Goes",
            labels={"x": "Acres", "y": "Land Use Type"},
            color_discrete_sequence=[RPA_COLORS["pink"]],
        )
        fig_loss.update_layout(height=250, showlegend=False, xaxis_tickformat=".2s", margin=dict(t=30, b=0))
        st.plotly_chart(fig_loss, use_container_width=True)

    with detail_col2:
        st.markdown("##### Agricultural Gain Sources")
        gain_summary = df_gain.groupby("from_landuse")["total_acres"].sum().sort_values(ascending=False)

        fig_gain = px.bar(
            x=gain_summary.values[:5],
            y=gain_summary.index[:5],
            orientation="h",
            title="What Becomes Agricultural Land",
            labels={"x": "Acres", "y": "Land Use Type"},
            color_discrete_sequence=[RPA_COLORS["medium_green"]],
        )
        fig_gain.update_layout(height=250, showlegend=False, xaxis_tickformat=".2s", margin=dict(t=30, b=0))
        st.plotly_chart(fig_gain, use_container_width=True)

    with detail_col3:
        st.markdown("##### Scenario Comparison")
        rcp_loss = df_loss.groupby("rcp_scenario")["total_acres"].sum()
        rcp_gain = df_gain.groupby("rcp_scenario")["total_acres"].sum()

        comparison_df = pd.DataFrame({
            "Scenario": ["RCP4.5", "RCP8.5"],
            "Loss (M acres)": [rcp_loss.get("rcp45", 0) / 1e6, rcp_loss.get("rcp85", 0) / 1e6],
            "Gain (M acres)": [rcp_gain.get("rcp45", 0) / 1e6, rcp_gain.get("rcp85", 0) / 1e6],
        })
        comparison_df["Net (M acres)"] = comparison_df["Gain (M acres)"] - comparison_df["Loss (M acres)"]

        st.dataframe(comparison_df.round(1), use_container_width=True, hide_index=True)


def render_agricultural_geographic(df_states: pd.DataFrame) -> None:
    """Render the agricultural geographic distribution tab."""
    st.markdown("#### Geographic Distribution of Agricultural Changes")

    if df_states is None or df_states.empty:
        st.info("No geographic data available")
        return

    with st.expander("Understanding the Map Metric", expanded=False):
        st.info("""
        **How to interpret the percentage change:**

        This map shows the **change in agricultural transition activity between 2020-2030 and 2060-2070**:
        - **Negative % (purple)**: Decreasing agricultural transition activity over time
        - **Near 0% (teal)**: Stable agricultural transition activity
        - **Positive % (yellow)**: Increasing agricultural transition activity over time

        **Formula:** ((2070 Activity - 2025 Activity) / 2025 Activity) x 100
        """)

    fig = create_agricultural_state_map(df_states)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False})

    # State rankings
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Top States - Agricultural Gain (%)")
        top_gain_states = df_states.nlargest(10, "percent_change")[
            ["state_name", "percent_change", "net_change", "ag_gain"]
        ]
        top_gain_states["Percent Change"] = top_gain_states["percent_change"].apply(lambda x: f"{x:+.1f}%")
        top_gain_states["Net Change"] = top_gain_states["net_change"].apply(lambda x: f"{x / 1e6:+.2f}M")
        top_gain_states["Total Gain"] = top_gain_states["ag_gain"].apply(lambda x: f"{x / 1e6:.2f}M")
        display_df = top_gain_states[["state_name", "Percent Change", "Net Change", "Total Gain"]].copy()
        st.dataframe(display_df.rename(columns={"state_name": "State"}), use_container_width=True, hide_index=True)

    with col2:
        st.markdown("##### Top States - Agricultural Loss (%)")
        top_loss_states = df_states.nsmallest(10, "percent_change")[
            ["state_name", "percent_change", "net_change", "ag_loss"]
        ]
        top_loss_states["Percent Change"] = top_loss_states["percent_change"].apply(lambda x: f"{x:+.1f}%")
        top_loss_states["Net Change"] = top_loss_states["net_change"].apply(lambda x: f"{x / 1e6:+.2f}M")
        top_loss_states["Total Loss"] = top_loss_states["ag_loss"].apply(lambda x: f"{x / 1e6:.2f}M")
        display_df = top_loss_states[["state_name", "Percent Change", "Net Change", "Total Loss"]].copy()
        st.dataframe(display_df.rename(columns={"state_name": "State"}), use_container_width=True, hide_index=True)

    # Summary insights
    st.markdown("##### Geographic Insights")
    gaining_states = len(df_states[df_states["net_change"] > 0])
    losing_states = len(df_states[df_states["net_change"] < 0])

    st.info(f"""
    **Key Findings:**
    - {gaining_states} states show net agricultural gain
    - {losing_states} states show net agricultural loss
    - Regional patterns suggest varying development and conservation pressures
    """)


def render_urbanization_tab() -> None:
    """Render the urbanization patterns tab."""
    st.markdown("### Urbanization Patterns")
    st.markdown("**Comprehensive analysis of urban expansion across states and land use sources**")

    urban_data, urban_error = load_urbanization_data()
    if urban_error:
        st.error(f"{urban_error}")
        return

    if urban_data is None or urban_data.empty:
        st.info("No urbanization data available")
        return

    viz_col1, viz_col2 = st.columns(2)

    with viz_col1:
        st.markdown("#### Urbanization Sources")
        source_breakdown = (
            urban_data.groupby("from_landuse")["total_acres_urbanized"].sum().sort_values(ascending=False)
        )

        fig_pie = px.pie(
            values=source_breakdown.values,
            names=source_breakdown.index,
            title="Land Converted to Urban",
            color_discrete_sequence=RPA_COLOR_SEQUENCE,
            hole=0.4,
        )
        fig_pie.update_traces(textinfo="percent+label")
        fig_pie.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    with viz_col2:
        st.markdown("#### Geographic Distribution")
        state_totals = urban_data.groupby("state_code")["total_acres_urbanized"].sum().reset_index()
        state_totals["state_abbr"] = state_totals["state_code"].map(StateMapper.FIPS_TO_ABBREV)

        fig_map = px.choropleth(
            state_totals.head(20),
            locations="state_abbr",
            locationmode="USA-states",
            color="total_acres_urbanized",
            color_continuous_scale=RPA_BROWN_SCALE,
            title="Urban Expansion Hotspots",
        )
        fig_map.update_layout(geo={"scope": "usa"}, height=350, margin={"r": 0, "t": 30, "l": 0, "b": 0})
        st.plotly_chart(fig_map, use_container_width=True, config={"scrollZoom": False})

    # Detailed insights
    st.markdown("---")
    detail_col1, detail_col2, detail_col3 = st.columns([2, 2, 2])

    with detail_col1:
        st.markdown("#### Key Insights")
        top_state_data = (
            urban_data.groupby("state_code")["total_acres_urbanized"].sum().sort_values(ascending=False)
        )
        top_state = top_state_data.index[0]
        top_state_acres = top_state_data.iloc[0]

        st.success(f"""
        **Urban Development Patterns:**
        - **Top State:** {StateMapper.FIPS_TO_NAME.get(top_state, top_state)} ({top_state_acres / 1e6:.1f}M acres)
        - **Primary Source:** {source_breakdown.index[0]} -> Urban
        - **Total Urbanized:** {source_breakdown.sum() / 1e6:.1f}M acres nationwide
        """)

    with detail_col2:
        st.markdown("#### Source Breakdown")
        source_df = pd.DataFrame({
            "Land Type": source_breakdown.index,
            "Acres": source_breakdown.apply(lambda x: f"{x / 1e6:.2f}M"),
            "Percent": source_breakdown.apply(lambda x: f"{x / source_breakdown.sum() * 100:.1f}%"),
        })
        st.dataframe(source_df, use_container_width=True, hide_index=True)

    with detail_col3:
        st.markdown("#### Top 10 States")
        top_states_df = top_state_data.head(10).reset_index()
        top_states_df["state_name"] = top_states_df["state_code"].map(StateMapper.FIPS_TO_NAME)
        top_states_df["acres"] = top_states_df["total_acres_urbanized"].apply(lambda x: f"{x / 1e6:.2f}M")
        display_df = top_states_df[["state_name", "acres"]].copy()
        display_df.columns = ["State", "Urban Expansion"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def show_enhanced_visualizations() -> None:
    """Show enhanced visualization section with maps and Sankey diagrams."""
    st.markdown("### Enhanced Visualizations")
    st.markdown("**Interactive maps, flow diagrams, and advanced analytics**")

    viz_tab1, viz_tab2 = st.tabs(["Geographic Analysis", "Transition Flows"])

    with viz_tab1:
        st.markdown("#### State-Level Land Use Changes")
        st.markdown(
            "**Interactive map showing the percentage change in land use transition activity between 2020-2030 and 2060-2070 periods**"
        )
        st.info(
            "**What this shows:** The percentage increase or decrease in the total amount of land changing from one use to another. Green = more transition activity, Red = less transition activity."
        )

        state_data, state_error = load_state_transitions()
        if state_error:
            st.error(f"{state_error}")
        elif state_data is not None and not state_data.empty:
            fig = create_choropleth_map(state_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": False})

            st.markdown("##### Top 10 States by Percentage Change (2025-2070)")

            df_sorted = state_data.copy()
            df_sorted["abs_change"] = df_sorted["percent_change"].abs()
            top_states = df_sorted.nlargest(10, "abs_change")[
                ["state_name", "percent_change", "baseline", "future", "dominant_transition"]
            ]

            top_states["Change (%)"] = top_states["percent_change"].apply(lambda x: f"{x:+.1f}%")
            top_states["2025 Baseline"] = top_states["baseline"].apply(lambda x: f"{x:,.0f}")
            top_states["2070 Projection"] = top_states["future"].apply(lambda x: f"{x:,.0f}")

            display_df = top_states[
                ["state_name", "Change (%)", "2025 Baseline", "2070 Projection", "dominant_transition"]
            ]
            display_df.columns = ["State", "Change (%)", "2025 (acres)", "2070 (acres)", "Dominant Transition"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    with viz_tab2:
        st.markdown("#### Land Use Transition Flows")
        st.markdown("**Sankey diagram showing flows between land use types**")

        with st.expander("How to read this diagram", expanded=False):
            st.markdown("""
            - **Width of flows** represents the total acres transitioning
            - **Node size** shows the total volume of land involved
            - **Colors** distinguish different land use types
            - **Hover** over flows or nodes for detailed information
            - Use filters below to explore specific transitions
            """)

        st.markdown("##### Filter Options")
        col1, col2, col3 = st.columns(3)

        with col1:
            from_filter = st.selectbox(
                "From Land Use",
                ["All", "Crop", "Pasture", "Forest", "Urban", "Rangeland"],
                key="sankey_from",
                help="Filter by source land use type",
            )

        with col2:
            to_filter = st.selectbox(
                "To Land Use",
                ["All", "Crop", "Pasture", "Forest", "Urban", "Rangeland"],
                key="sankey_to",
                help="Filter by destination land use type",
            )

        with col3:
            state_options = ["All"] + sorted(StateMapper.get_all_names())
            state_filter = st.selectbox(
                "State",
                state_options,
                key="sankey_state",
                help="Filter by state to see regional land use transitions",
            )

        with st.spinner("Loading transition flows..."):
            sankey_data, sankey_error = load_sankey_data(from_filter, to_filter, state_filter)

        if sankey_error:
            if "No transitions found" in sankey_error:
                st.warning(f"{sankey_error}")
            else:
                st.error(f"{sankey_error}")
        elif sankey_data is not None and not sankey_data.empty:
            fig = create_sankey_diagram(sankey_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            _render_sankey_statistics(sankey_data, state_filter)
        else:
            st.info("No transition data available for the selected filters. Try selecting 'All' for broader results.")


def _render_sankey_statistics(sankey_data: pd.DataFrame, state_filter: str) -> None:
    """Render statistics for the Sankey diagram."""
    st.markdown("---")
    st.markdown("##### Transition Statistics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_flow = sankey_data["value"].sum()
        st.metric("Total Acres", f"{total_flow / 1e6:.1f}M", help="Total acres transitioning between land uses")

    with col2:
        num_transitions = len(sankey_data)
        st.metric("Transitions Shown", num_transitions, help="Number of transition pathways displayed")

    with col3:
        avg_flow = sankey_data["value"].mean()
        st.metric("Average Flow", f"{avg_flow / 1e6:.1f}M", help="Average acres per transition")

    with col4:
        if "county_count" in sankey_data.columns:
            total_counties = sankey_data["county_count"].sum()
            st.metric("Counties Affected", total_counties, help="Number of counties with transitions")
        else:
            max_scenarios = sankey_data["scenario_count"].max()
            st.metric("Max Scenarios", max_scenarios, help="Maximum scenarios for any transition")

    st.markdown("##### Detailed Transition Data")

    display_df = sankey_data.copy()
    display_df["Transition"] = display_df["source"] + " -> " + display_df["target"]
    display_df["Acres (M)"] = (display_df["value"] / 1e6).round(2)
    display_df["Scenarios"] = display_df["scenario_count"]

    display_df = display_df[["Transition", "Acres (M)", "Scenarios"]]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Transition": st.column_config.TextColumn("Land Use Transition", width="medium"),
            "Acres (M)": st.column_config.NumberColumn("Acres (Millions)", format="%.2f", width="small"),
            "Scenarios": st.column_config.NumberColumn("Scenario Count", width="small"),
        },
    )

    if num_transitions > 0:
        top_transition = display_df.iloc[0]
        if state_filter and state_filter != "All":
            st.info(
                f"**Key Insight for {state_filter}:** The largest transition is {top_transition['Transition']} with {top_transition['Acres (M)']}M acres"
            )
        else:
            st.info(
                f"**Key Insight:** The largest transition is {top_transition['Transition']} with {top_transition['Acres (M)']}M acres"
            )


def main() -> None:
    """Main analytics dashboard entry point."""
    st.title("RPA Assessment Analytics Dashboard")
    st.markdown("**Visualizations and insights from the USDA Forest Service 2020 RPA Assessment**")

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Forest Analysis", "Agricultural Analysis", "Urbanization Trends", "Enhanced Visualizations"]
    )

    with tab1:
        st.markdown("### Forest Analysis")
        st.markdown("**Comprehensive analysis of forest gains, losses, and transitions**")

        df_loss, df_gain, df_states, forest_error = load_forest_analysis_data()
        if forest_error:
            st.error(f"{forest_error}")
        else:
            forest_tab1, forest_tab2 = st.tabs(["Overview", "Geographic Distribution"])

            with forest_tab1:
                render_forest_overview(df_loss, df_gain)

            with forest_tab2:
                render_forest_geographic(df_states)

    with tab2:
        st.markdown("### Agricultural Analysis")
        st.markdown("**Comprehensive analysis of agricultural gains, losses, and transitions**")

        df_loss, df_gain, df_states, ag_error = load_agricultural_analysis_data()

        if ag_error:
            st.error(f"{ag_error}")
        else:
            ag_tab1, ag_tab2 = st.tabs(["Overview", "Geographic Distribution"])

            with ag_tab1:
                render_agricultural_overview(df_loss, df_gain)

            with ag_tab2:
                render_agricultural_geographic(df_states)

    with tab3:
        render_urbanization_tab()

    with tab4:
        show_enhanced_visualizations()

    # Footer
    st.markdown("---")
    st.markdown("""
    **Want to explore further?**
    - Use the **Chat** interface for custom natural language queries
    - Visit the **Data Explorer** for advanced SQL analysis
    - Check **Settings** for configuration options
    """)


if __name__ == "__main__":
    main()
