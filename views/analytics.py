#!/usr/bin/env python3
"""
Analytics Dashboard for Landuse Data
Pre-built visualizations and insights for land use transition analysis
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import third-party libraries after sys.path modification
import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from plotly.subplots import make_subplots  # noqa: E402

from landuse.config import LanduseConfig  # noqa: E402
from landuse.connections import DuckDBConnection  # noqa: E402

# Import state mappings and connection
from landuse.utilities.state_mappings import StateMapper  # noqa: E402

# RPA Assessment Official Color Palette
RPA_COLORS = {
    'dark_green': '#496f4a',
    'medium_green': '#85b18b',
    'medium_blue': '#a3cad4',
    'light_brown': '#cec597',
    'pink': '#edaa97',
    'dark_blue': '#61a4b5',
    'lighter_dark_green': '#89b18b',
    'lighter_medium_green': '#b8d0b9',
    'lighter_medium_blue': '#c8dfe5',
    'lighter_light_brown': '#e2dcc1'
}

# RPA color sequences for Plotly
RPA_COLOR_SEQUENCE = [
    RPA_COLORS['dark_green'],
    RPA_COLORS['medium_blue'],
    RPA_COLORS['medium_green'],
    RPA_COLORS['light_brown'],
    RPA_COLORS['pink'],
    RPA_COLORS['dark_blue']
]

# RPA gradient scales
RPA_GREEN_SCALE = [[0, RPA_COLORS['lighter_medium_green']], [0.5, RPA_COLORS['medium_green']], [1, RPA_COLORS['dark_green']]]
RPA_BLUE_SCALE = [[0, RPA_COLORS['lighter_medium_blue']], [0.5, RPA_COLORS['medium_blue']], [1, RPA_COLORS['dark_blue']]]
RPA_BROWN_SCALE = [[0, RPA_COLORS['lighter_light_brown']], [0.5, RPA_COLORS['light_brown']], [1, '#9f6b25']]


@st.cache_resource
def get_database_connection():
    """Get cached database connection using st.connection"""
    try:
        # Use unified config system
        config = LanduseConfig.for_agent_type('streamlit')

        conn = st.connection(
            name="landuse_db_analytics",
            type=DuckDBConnection,
            database=config.db_path,
            read_only=True
        )
        return conn, None
    except Exception as e:
        return None, f"Database connection error: {e}"

@st.cache_data
def load_summary_data():
    """Load summary statistics for the dashboard"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        # Basic dataset stats
        stats = {}

        # Use query method with appropriate TTL
        counties_df = conn.query("SELECT COUNT(DISTINCT fips_code) as count FROM dim_geography", ttl=3600)
        stats['total_counties'] = counties_df['count'].iloc[0]

        scenarios_df = conn.query("SELECT COUNT(*) as count FROM dim_scenario", ttl=3600)
        stats['total_scenarios'] = scenarios_df['count'].iloc[0]

        transitions_df = conn.query("SELECT COUNT(*) as count FROM fact_landuse_transitions WHERE transition_type = 'change'", ttl=300)
        stats['total_transitions'] = transitions_df['count'].iloc[0]

        time_df = conn.query("SELECT COUNT(*) as count FROM dim_time", ttl=3600)
        stats['time_periods'] = time_df['count'].iloc[0]

        return stats, None
    except Exception as e:
        return None, f"Error loading summary data: {e}"

@st.cache_data
def load_agricultural_loss_data():
    """Load agricultural land loss data by scenario"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT
            s.scenario_name,
            s.rcp_scenario,
            s.ssp_scenario,
            SUM(f.acres) as total_acres_lost
        FROM fact_landuse_transitions f
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE fl.landuse_category = 'Agriculture'
          AND tl.landuse_category != 'Agriculture'
          AND f.transition_type = 'change'
        GROUP BY s.scenario_name, s.rcp_scenario, s.ssp_scenario
        ORDER BY total_acres_lost DESC
        LIMIT 20
        """

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading agricultural data: {e}"

@st.cache_data
def load_urbanization_data():
    """Load urbanization data by state"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT
            g.state_code,
            fl.landuse_name as from_landuse,
            SUM(f.acres) as total_acres_urbanized
        FROM fact_landuse_transitions f
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE tl.landuse_name = 'Urban'
          AND f.transition_type = 'change'
        GROUP BY g.state_code, fl.landuse_name
        ORDER BY total_acres_urbanized DESC
        LIMIT 50
        """

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading urbanization data: {e}"

@st.cache_data
def load_forest_analysis_data():
    """Load comprehensive forest transition data"""
    conn, error = get_database_connection()
    if error:
        return None, None, None, error

    try:
        # Query 1: Forest loss by destination
        forest_loss_query = """
        SELECT
            tl.landuse_name as to_landuse,
            s.rcp_scenario,
            SUM(f.acres) as total_acres,
            AVG(f.acres) as avg_acres_per_county,
            COUNT(DISTINCT g.state_code) as states_affected
        FROM fact_landuse_transitions f
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        WHERE fl.landuse_name = 'Forest'
          AND tl.landuse_name != 'Forest'
          AND f.transition_type = 'change'
        GROUP BY tl.landuse_name, s.rcp_scenario
        ORDER BY total_acres DESC
        """

        # Query 2: Forest gain by source
        forest_gain_query = """
        SELECT
            fl.landuse_name as from_landuse,
            s.rcp_scenario,
            SUM(f.acres) as total_acres,
            AVG(f.acres) as avg_acres_per_county,
            COUNT(DISTINCT g.state_code) as states_affected
        FROM fact_landuse_transitions f
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        WHERE tl.landuse_name = 'Forest'
          AND fl.landuse_name != 'Forest'
          AND f.transition_type = 'change'
        GROUP BY fl.landuse_name, s.rcp_scenario
        ORDER BY total_acres DESC
        """

        # Query 3: State-level forest changes
        state_forest_query = """
        WITH forest_changes AS (
            SELECT
                g.state_code,
                CASE
                    WHEN fl.landuse_name = 'Forest' AND tl.landuse_name != 'Forest' THEN 'loss'
                    WHEN fl.landuse_name != 'Forest' AND tl.landuse_name = 'Forest' THEN 'gain'
                END as change_type,
                SUM(f.acres) as total_acres
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE f.transition_type = 'change'
              AND (fl.landuse_name = 'Forest' OR tl.landuse_name = 'Forest')
            GROUP BY g.state_code, change_type
        )
        SELECT
            state_code,
            SUM(CASE WHEN change_type = 'loss' THEN total_acres ELSE 0 END) as forest_loss,
            SUM(CASE WHEN change_type = 'gain' THEN total_acres ELSE 0 END) as forest_gain,
            SUM(CASE WHEN change_type = 'gain' THEN total_acres ELSE -total_acres END) as net_change
        FROM forest_changes
        GROUP BY state_code
        ORDER BY net_change DESC
        """

        df_loss = conn.query(forest_loss_query, ttl=300)
        df_gain = conn.query(forest_gain_query, ttl=300)
        df_states = conn.query(state_forest_query, ttl=300)

        # Add state names and abbreviations
        df_states['state_abbr'] = df_states['state_code'].map(StateMapper.FIPS_TO_ABBREV)
        df_states['state_name'] = df_states['state_code'].map(StateMapper.FIPS_TO_NAME)

        return df_loss, df_gain, df_states, None
    except Exception as e:
        return None, None, None, f"Error loading forest data: {e}"

@st.cache_data
def load_climate_comparison_data():
    """Load data for climate scenario comparison"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT
            s.rcp_scenario,
            fl.landuse_name as from_landuse,
            tl.landuse_name as to_landuse,
            SUM(f.acres) as total_acres
        FROM fact_landuse_transitions f
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE f.transition_type = 'change'
        GROUP BY s.rcp_scenario, fl.landuse_name, tl.landuse_name
        ORDER BY total_acres DESC
        LIMIT 100
        """

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading climate comparison data: {e}"

@st.cache_data
def load_time_series_data():
    """Load time series data for trend analysis"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT
            t.start_year,
            t.end_year,
            t.year_range,
            fl.landuse_name as from_landuse,
            tl.landuse_name as to_landuse,
            SUM(f.acres) as total_acres
        FROM fact_landuse_transitions f
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE f.transition_type = 'change'
          AND fl.landuse_name != tl.landuse_name
        GROUP BY t.start_year, t.end_year, t.year_range, fl.landuse_name, tl.landuse_name
        ORDER BY t.start_year, total_acres DESC
        """

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading time series data: {e}"

def create_agricultural_loss_chart(df):
    """Create agricultural land loss visualization"""
    if df is None or df.empty:
        return None

    # Create bar chart
    fig = px.bar(
        df.head(10),
        x='total_acres_lost',
        y='scenario_name',
        color='rcp_scenario',
        title='Top 10 Scenarios by Agricultural Land Loss',
        labels={
            'total_acres_lost': 'Total Acres Lost',
            'scenario_name': 'Scenario',
            'rcp_scenario': 'RCP Pathway'
        },
        color_discrete_map={'rcp45': '#2E86AB', 'rcp85': '#F24236'}
    )

    fig.update_layout(
        height=500,
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Acres Lost (millions)",
        xaxis_tickformat='.1s',  # Format x-axis to show millions
        font={"size": 12}
    )

    return fig

def create_urbanization_chart(df):
    """Create urbanization analysis visualization"""
    if df is None or df.empty:
        return None

    # Aggregate by state
    state_totals = df.groupby('state_code')['total_acres_urbanized'].sum().reset_index()
    state_totals = state_totals.sort_values('total_acres_urbanized', ascending=True).tail(15)

    fig = px.bar(
        state_totals,
        x='total_acres_urbanized',
        y='state_code',
        title='Top 15 States by Urban Expansion (Total Acres)',
        labels={
            'total_acres_urbanized': 'Total Acres Urbanized',
            'state_code': 'State'
        },
        color='total_acres_urbanized',
        color_continuous_scale=RPA_BROWN_SCALE
    )

    fig.update_layout(
        height=500,
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Acres Urbanized (millions)",
        xaxis_tickformat='.1s',  # Format x-axis to show millions
        font={"size": 12}
    )

    return fig

def create_forest_flow_chart(df_loss, df_gain):
    """Create a combined flow chart showing forest gains and losses"""
    if df_loss is None or df_gain is None:
        return None

    # Prepare data for waterfall chart
    fig = go.Figure()

    # Group by land use type for cleaner visualization
    loss_by_type = df_loss.groupby('to_landuse')['total_acres'].sum().sort_values(ascending=False)
    gain_by_type = df_gain.groupby('from_landuse')['total_acres'].sum().sort_values(ascending=False)

    # Create waterfall chart
    x_labels = []
    y_values = []
    colors = []

    # Add losses (negative values)
    for landuse, acres in loss_by_type.items():
        x_labels.append(f"To {landuse}")
        y_values.append(-acres)
        colors.append(f'{RPA_COLORS["pink"]}99')  # RPA pink for losses

    # Add gains (positive values)
    for landuse, acres in gain_by_type.items():
        x_labels.append(f"From {landuse}")
        y_values.append(acres)
        colors.append(f'{RPA_COLORS["medium_green"]}99')  # RPA green for gains

    # Create bar chart
    fig.add_trace(go.Bar(
        x=x_labels,
        y=y_values,
        marker_color=colors,
        text=[f"{abs(v/1e6):.1f}M" for v in y_values],
        textposition='outside',
        hovertemplate='%{x}<br>%{y:,.0f} acres<extra></extra>'
    ))

    # Calculate net change
    total_loss = sum(v for v in y_values if v < 0)
    total_gain = sum(v for v in y_values if v > 0)
    net_change = total_gain + total_loss

    # Update layout
    fig.update_layout(
        title={
            'text': f"Forest Transitions: Net Change = {net_change/1e6:+.1f}M acres",
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title="Transition Type",
        yaxis_title="Acres",
        yaxis_tickformat='.2s',
        height=500,
        showlegend=False,
        yaxis_zeroline=True,
        yaxis_zerolinewidth=2,
        yaxis_zerolinecolor='black'
    )

    return fig

def create_forest_state_map(df_states):
    """Create choropleth map showing net forest change by state"""
    if df_states is None or df_states.empty:
        return None

    # Create choropleth with diverging color scale
    fig = px.choropleth(
        df_states,
        locations='state_abbr',
        locationmode='USA-states',
        color='net_change',
        color_continuous_scale=RPA_GREEN_SCALE,  # RPA green scale
        color_continuous_midpoint=0,
        hover_name='state_name',
        hover_data={
            'state_abbr': False,
            'forest_loss': ':,.0f',
            'forest_gain': ':,.0f',
            'net_change': ':,.0f',
            'state_name': False
        },
        labels={
            'net_change': 'Net Forest Change (acres)',
            'forest_loss': 'Forest Loss',
            'forest_gain': 'Forest Gain'
        },
        title='Net Forest Change by State (All Scenarios Combined)'
    )

    # Update layout
    fig.update_layout(
        geo={
            "scope": 'usa',
            "projection_type": 'albers usa',
            "showlakes": True,
            "lakecolor": 'rgba(255, 255, 255, 0.3)'
        },
        height=600,
        margin={"r":0,"t":40,"l":0,"b":0},
        coloraxis_colorbar={
            "title": "Net Change<br>(acres)",
            "thicknessmode": "pixels",
            "thickness": 15,
            "lenmode": "pixels",
            "len": 300,
            "yanchor": "middle",
            "y": 0.5
        }
    )

    return fig

def create_forest_scenario_comparison(df_loss, df_gain):
    """Create comparison of forest changes across climate scenarios"""
    if df_loss is None or df_gain is None:
        return None

    # Aggregate by scenario
    loss_by_scenario = df_loss.groupby('rcp_scenario')['total_acres'].sum()
    gain_by_scenario = df_gain.groupby('rcp_scenario')['total_acres'].sum()

    # Create grouped bar chart
    fig = go.Figure()

    scenarios = ['rcp45', 'rcp85']

    fig.add_trace(go.Bar(
        name='Forest Loss',
        x=scenarios,
        y=[-loss_by_scenario.get(s, 0) for s in scenarios],
        marker_color='rgba(255, 99, 71, 0.7)',
        text=[f"{abs(loss_by_scenario.get(s, 0)/1e6):.1f}M" for s in scenarios],
        textposition='outside'
    ))

    fig.add_trace(go.Bar(
        name='Forest Gain',
        x=scenarios,
        y=[gain_by_scenario.get(s, 0) for s in scenarios],
        marker_color='rgba(34, 139, 34, 0.7)',
        text=[f"{gain_by_scenario.get(s, 0)/1e6:.1f}M" for s in scenarios],
        textposition='outside'
    ))

    # Calculate net change line
    net_changes = [gain_by_scenario.get(s, 0) - loss_by_scenario.get(s, 0) for s in scenarios]

    fig.add_trace(go.Scatter(
        name='Net Change',
        x=scenarios,
        y=net_changes,
        mode='lines+markers+text',
        line={"color": 'black', "width": 3},
        marker={"size": 10},
        text=[f"{v/1e6:+.1f}M" for v in net_changes],
        textposition='top center',
        yaxis='y2'
    ))

    # Update layout with dual y-axes
    fig.update_layout(
        title='Forest Changes by Climate Scenario',
        xaxis_title='Climate Scenario',
        yaxis_title='Forest Loss/Gain (acres)',
        yaxis2={
            "title": 'Net Change (acres)',
            "overlaying": 'y',
            "side": 'right',
            "showgrid": False
        },
        yaxis_tickformat='.2s',
        yaxis2_tickformat='.2s',
        height=500,
        hovermode='x unified',
        barmode='relative',
        legend={"x": 0.02, "y": 0.98, "xanchor": 'left', "yanchor": 'top'}
    )

    return fig

def create_climate_comparison_chart(df):
    """Create climate scenario comparison visualization"""
    if df is None or df.empty:
        return None

    # Focus on major transitions
    major_transitions = df[df['total_acres'] > df['total_acres'].quantile(0.8)]

    fig = px.sunburst(
        major_transitions,
        path=['rcp_scenario', 'from_landuse', 'to_landuse'],
        values='total_acres',
        title='Land Use Transitions by Climate Scenario',
        color='total_acres',
        color_continuous_scale=RPA_BLUE_SCALE
    )

    fig.update_layout(height=600, font={"size": 12})

    return fig

def create_time_series_chart(df):
    """Create time series trend visualization"""
    if df is None or df.empty:
        return None

    # Focus on major land use changes
    major_changes = df.groupby(['start_year', 'from_landuse', 'to_landuse'])['total_acres'].sum().reset_index()
    major_changes = major_changes[major_changes['total_acres'] > major_changes['total_acres'].quantile(0.7)]

    # Create transition labels
    major_changes['transition'] = major_changes['from_landuse'] + ' → ' + major_changes['to_landuse']

    fig = px.line(
        major_changes,
        x='start_year',
        y='total_acres',
        color='transition',
        title='Major Land Use Transitions Over Time',
        labels={
            'start_year': 'Year',
            'total_acres': 'Total Acres Transitioned',
            'transition': 'Land Use Transition'
        }
    )

    fig.update_layout(
        height=500,
        xaxis_title="Year",
        yaxis_title="Acres (millions)",
        yaxis_tickformat='.1s',  # Format y-axis to show millions
        font={"size": 12},
        legend={"orientation": "v", "yanchor": "top", "y": 1, "xanchor": "left", "x": 1.02}
    )

    return fig

@st.cache_data
def load_state_transitions():
    """Load state-level transition data for choropleth map"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        WITH state_transitions AS (
            SELECT
                g.state_code,
                fl.landuse_name as from_landuse,
                tl.landuse_name as to_landuse,
                SUM(f.acres) as total_acres,
                AVG(f.acres) as avg_acres_per_scenario
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE f.transition_type = 'change'
            GROUP BY g.state_code, fl.landuse_name, tl.landuse_name
        ),
        state_totals AS (
            SELECT
                state_code,
                SUM(total_acres) as total_change_acres,
                COUNT(DISTINCT CONCAT(from_landuse, ' to ', to_landuse)) as transition_types
            FROM state_transitions
            GROUP BY state_code
        )
        SELECT
            st.state_code,
            st.total_change_acres,
            st.transition_types,
            (SELECT CONCAT(from_landuse, ' → ', to_landuse)
             FROM state_transitions s
             WHERE s.state_code = st.state_code
             ORDER BY total_acres DESC
             LIMIT 1) as dominant_transition
        FROM state_totals st
        """

        df = conn.query(query, ttl=300)

        # Add state abbreviations and names
        df['state_abbr'] = df['state_code'].map(StateMapper.FIPS_TO_ABBREV)
        df['state_name'] = df['state_code'].map(StateMapper.FIPS_TO_NAME)

        return df, None
    except Exception as e:
        return None, f"Error loading state transitions: {e}"

@st.cache_data
def load_sankey_data(from_landuse=None, to_landuse=None, scenario_filter=None):
    """Load data for Sankey diagram of land use flows"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        # Build dynamic WHERE clause
        where_conditions = ["f.transition_type = 'change'"]

        if from_landuse and from_landuse != "All":
            where_conditions.append(f"fl.landuse_name = '{from_landuse}'")
        if to_landuse and to_landuse != "All":
            where_conditions.append(f"tl.landuse_name = '{to_landuse}'")
        if scenario_filter and scenario_filter != "All":
            where_conditions.append(f"s.rcp_scenario = '{scenario_filter}'")

        where_clause = " AND ".join(where_conditions)

        query = f"""
        SELECT
            fl.landuse_name as source,
            tl.landuse_name as target,
            SUM(f.acres) as value,
            COUNT(DISTINCT s.scenario_id) as scenario_count
        FROM fact_landuse_transitions f
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE {where_clause}
        GROUP BY fl.landuse_name, tl.landuse_name
        HAVING SUM(f.acres) > 1000000
        ORDER BY value DESC
        LIMIT 20
        """

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading Sankey data: {e}"

def create_choropleth_map(df):
    """Create interactive choropleth map of state-level transitions using modern Plotly API"""
    if df is None or df.empty:
        return None

    # Use Plotly Express for cleaner API (2025 best practice)
    fig = px.choropleth(
        df,
        locations='state_abbr',
        locationmode='USA-states',
        color='total_change_acres',
        color_continuous_scale=RPA_BROWN_SCALE,
        hover_name='state_name',
        hover_data={
            'state_abbr': False,  # Hide from hover
            'total_change_acres': ':,.0f',
            'dominant_transition': True,
            'transition_types': True,
            'state_name': False  # Already shown as hover_name
        },
        labels={
            'total_change_acres': 'Total Acres Changed',
            'dominant_transition': 'Dominant Transition',
            'transition_types': 'Transition Types'
        },
        title='Total Land Use Changes by State'
    )

    # Update layout for better visualization
    fig.update_layout(
        geo={
            "scope": 'usa',
            "projection_type": 'albers usa',
            "showlakes": True,
            "lakecolor": 'rgba(255, 255, 255, 0.3)',
            "bgcolor": 'rgba(0,0,0,0)'
        },
        height=600,
        margin={"r":0,"t":40,"l":0,"b":0},
        coloraxis_colorbar={
            "title": "Total Acres<br>Changed",
            "thicknessmode": "pixels",
            "thickness": 15,
            "lenmode": "pixels",
            "len": 300,
            "yanchor": "middle",
            "y": 0.5
        }
    )

    return fig

def create_sankey_diagram(df):
    """Create Sankey diagram for land use flows with modern Plotly features"""
    if df is None or df.empty:
        return None

    # Create node labels
    all_nodes = list(set(df['source'].tolist() + df['target'].tolist()))
    node_dict = {node: i for i, node in enumerate(all_nodes)}

    # Define modern color palette for land use types
    node_colors = {
        'Crop': '#d4a574',      # Wheat color
        'Pasture': '#90ee90',   # Light green
        'Forest': '#228b22',    # Forest green
        'Urban': '#696969',     # Dim gray
        'Rangeland': '#daa520'  # Goldenrod
    }

    # Prepare hover data
    hover_labels = []
    for _, row in df.iterrows():
        acres_millions = row['value'] / 1_000_000
        hover_labels.append(
            f"{row['source']} → {row['target']}<br>" +
            f"Total: {acres_millions:.2f}M acres<br>" +
            f"Across {row['scenario_count']} scenarios"
        )

    # Create Sankey diagram with enhanced features
    fig = go.Figure(data=[go.Sankey(
        arrangement='snap',  # Better node positioning
        node={
            "pad": 20,
            "thickness": 25,
            "line": {"color": "white", "width": 2},
            "label": all_nodes,
            "color": [node_colors.get(node, '#999999') for node in all_nodes],
            "customdata": all_nodes,
            "hovertemplate": '%{customdata}<br>%{value:,.0f} acres<extra></extra>'
        },
        link={
            "source": [node_dict[src] for src in df['source']],
            "target": [node_dict[tgt] for tgt in df['target']],
            "value": df['value'],
            "customdata": hover_labels,
            "hovertemplate": '%{customdata}<extra></extra>',
            # Color links based on source
            "color": [node_colors.get(df.iloc[i]['source'], 'rgba(200,200,200,0.4)')
                   for i in range(len(df))],
            # Make colors more transparent
            "line": {"width": 0}
        },
        textfont={"size": 14, "color": "black"}
    )])

    fig.update_layout(
        title={
            'text': "Land Use Transition Flows",
            'x': 0.5,
            'xanchor': 'center'
        },
        font={"size": 12, "family": "Arial, sans-serif"},
        height=550,
        margin={"l": 0, "r": 0, "t": 40, "b": 20},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

@st.cache_data
def load_animated_timeline_data():
    """Load data for animated timeline visualization"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT
            t.start_year,
            t.year_range,
            s.rcp_scenario,
            fl.landuse_name as from_landuse,
            tl.landuse_name as to_landuse,
            SUM(f.acres) as total_acres,
            COUNT(DISTINCT g.state_code) as states_affected
        FROM fact_landuse_transitions f
        JOIN dim_time t ON f.time_id = t.time_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
        JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        WHERE f.transition_type = 'change'
          AND fl.landuse_name != tl.landuse_name
        GROUP BY t.start_year, t.year_range, s.rcp_scenario,
                 fl.landuse_name, tl.landuse_name
        HAVING SUM(f.acres) > 500000  -- Focus on major transitions
        ORDER BY t.start_year, total_acres DESC
        """

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading timeline data: {e}"

@st.cache_data
def load_scenario_comparison_data():
    """Load scenario list for comparison"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        query = """
        SELECT DISTINCT
            s.scenario_name,
            s.climate_model,
            s.rcp_scenario,
            s.ssp_scenario
        FROM dim_scenario s
        ORDER BY s.scenario_name
        """

        df = conn.query(query, ttl=300)
        return df, None
    except Exception as e:
        return None, f"Error loading scenarios: {e}"

def create_animated_timeline(df):
    """Create animated timeline of transitions"""
    if df is None or df.empty:
        return None

    # Create transition labels
    df['transition'] = df['from_landuse'] + ' → ' + df['to_landuse']

    # Aggregate by year and scenario type
    timeline_data = df.groupby(['start_year', 'rcp_scenario', 'transition'])['total_acres'].sum().reset_index()

    # Create animated bar chart
    fig = px.bar(
        timeline_data,
        x='transition',
        y='total_acres',
        color='rcp_scenario',
        animation_frame='start_year',
        animation_group='transition',
        title='Land Use Transitions Over Time - Press Play to Animate',
        labels={
            'total_acres': 'Total Acres',
            'transition': 'Land Use Transition',
            'rcp_scenario': 'Climate Scenario',
            'start_year': 'Year'
        },
        color_discrete_map={'rcp45': '#2E86AB', 'rcp85': '#F24236'},
        range_y=[0, timeline_data['total_acres'].max() * 1.1],
        height=600
    )

    # Update layout for better readability
    fig.update_layout(
        xaxis_tickangle=-45,
        showlegend=True,
        xaxis_title="Land Use Transition",
        yaxis_title="Total Acres",
        yaxis_tickformat='.2s',
        updatemenus=[{
            'type': 'buttons',
            'showactive': False,
            'x': 0.1,
            'y': 1.15,
            'xanchor': 'left',
            'yanchor': 'top'
        }]
    )

    # Slow down animation for better viewing
    fig.layout.updatemenus[0].buttons[0].args[1]["frame"]["duration"] = 1500
    fig.layout.updatemenus[0].buttons[0].args[1]["transition"]["duration"] = 750

    return fig

def create_scenario_spider_chart(selected_scenarios):
    """Create spider/radar chart comparing scenarios"""
    conn, error = get_database_connection()
    if error:
        return None, error

    if not selected_scenarios:
        return None, "No scenarios selected"

    try:
        # Build query for selected scenarios
        scenario_list = "', '".join(selected_scenarios)
        query = f"""
        WITH scenario_summary AS (
            SELECT
                s.scenario_name,
                tl.landuse_name as to_landuse,
                SUM(f.acres) as total_acres_gained
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE f.transition_type = 'change'
              AND s.scenario_name IN ('{scenario_list}')
            GROUP BY s.scenario_name, tl.landuse_name
        )
        SELECT * FROM scenario_summary
        ORDER BY scenario_name, to_landuse
        """

        df = conn.query(query, ttl=300)

        if df.empty:
            return None, "No data for selected scenarios"

        # Pivot data for radar chart
        pivot_df = df.pivot(index='scenario_name', columns='to_landuse', values='total_acres_gained').fillna(0)

        # Create radar chart
        fig = go.Figure()

        colors = px.colors.qualitative.Set2

        for i, scenario in enumerate(pivot_df.index):
            values = pivot_df.loc[scenario].values.tolist()
            # Normalize values to make comparison easier
            max_val = max(values) if max(values) > 0 else 1
            normalized_values = [v/max_val * 100 for v in values]

            fig.add_trace(go.Scatterpolar(
                r=normalized_values,
                theta=pivot_df.columns.tolist(),
                fill='toself',
                name=scenario.split('_')[0],  # Show just model name
                line_color=colors[i % len(colors)],
                opacity=0.6
            ))

        fig.update_layout(
            polar={
                "radialaxis": {
                    "visible": True,
                    "range": [0, 100],
                    "ticksuffix": '%'
                }
            },
            showlegend=True,
            title="Scenario Comparison: Relative Land Gains by Type",
            height=500
        )

        return fig, None

    except Exception as e:
        return None, f"Error creating comparison: {e}"

def show_enhanced_visualizations():
    """Show enhanced visualization section"""
    st.markdown("### 🎨 Enhanced Visualizations")
    st.markdown("**Interactive maps, flow diagrams, and advanced analytics**")

    # Create sub-tabs for enhanced visualizations
    viz_tab1, viz_tab2, viz_tab3, viz_tab4 = st.tabs([
        "🗺️ Geographic Analysis",
        "🔀 Transition Flows",
        "⏱️ Animated Timeline",
        "🕸️ Scenario Comparison"
    ])

    with viz_tab1:
        st.markdown("#### State-Level Land Use Changes")
        st.markdown("**Interactive map showing total land use changes by state**")

        state_data, state_error = load_state_transitions()
        if state_error:
            st.error(f"❌ {state_error}")
        elif state_data is not None and not state_data.empty:
            # Create choropleth map
            fig = create_choropleth_map(state_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})

            # Show state details
            st.markdown("##### 🏆 Top 10 States by Total Change")
            top_states = state_data.nlargest(10, 'total_change_acres')[['state_name', 'total_change_acres', 'dominant_transition']]
            top_states['total_change_acres'] = top_states['total_change_acres'].apply(lambda x: f"{x:,.0f}")
            st.dataframe(top_states, use_container_width=True, hide_index=True)

    with viz_tab2:
        st.markdown("#### Land Use Transition Flows")
        st.markdown("**Sankey diagram showing flows between land use types**")

        # Add filters
        col1, col2, col3 = st.columns(3)

        with col1:
            from_filter = st.selectbox(
                "From Land Use",
                ["All", "Crop", "Pasture", "Forest", "Urban", "Rangeland"],
                key="sankey_from"
            )

        with col2:
            to_filter = st.selectbox(
                "To Land Use",
                ["All", "Crop", "Pasture", "Forest", "Urban", "Rangeland"],
                key="sankey_to"
            )

        with col3:
            scenario_filter = st.selectbox(
                "Climate Scenario",
                ["All", "rcp45", "rcp85"],
                key="sankey_scenario"
            )

        # Load and display Sankey diagram
        sankey_data, sankey_error = load_sankey_data(from_filter, to_filter, scenario_filter)
        if sankey_error:
            st.error(f"❌ {sankey_error}")
        elif sankey_data is not None and not sankey_data.empty:
            fig = create_sankey_diagram(sankey_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # Show flow statistics
            st.markdown("##### 📊 Flow Statistics")
            total_flow = sankey_data['value'].sum()
            st.metric("Total Acres in Flow", f"{total_flow:,.0f}")

            # Show top flows
            st.markdown("##### Top Transition Flows")
            top_flows = sankey_data.head(5)[['source', 'target', 'value', 'scenario_count']]
            top_flows['value'] = top_flows['value'].apply(lambda x: f"{x:,.0f}")
            st.dataframe(top_flows, use_container_width=True, hide_index=True)
        else:
            st.info("No data available for selected filters")

    with viz_tab3:
        st.markdown("#### Animated Timeline")
        st.markdown("**Watch land use transitions evolve over time**")

        timeline_data, timeline_error = load_animated_timeline_data()
        if timeline_error:
            st.error(f"❌ {timeline_error}")
        elif timeline_data is not None and not timeline_data.empty:
            # Create animated chart
            fig = create_animated_timeline(timeline_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # Show timeline insights
            st.markdown("##### 🔍 Timeline Insights")

            col1, col2, col3 = st.columns(3)
            with col1:
                # Period with most change
                period_totals = timeline_data.groupby('year_range')['total_acres'].sum()
                peak_period = period_totals.idxmax() if not period_totals.empty else "N/A"
                st.metric("Peak Activity Period", peak_period)

            with col2:
                # Most affected states
                max_states = timeline_data['states_affected'].max() if not timeline_data.empty else 0
                st.metric("Max States Affected", max_states)

            with col3:
                # Total transitions shown
                unique_transitions = timeline_data['transition'].nunique() if 'transition' in timeline_data.columns else 0
                st.metric("Unique Transitions", unique_transitions)

            # Instructions
            st.info("💡 **Tip:** Click the play button to watch transitions evolve over time. Use the slider to manually explore specific years.")
        else:
            st.info("No timeline data available")

    with viz_tab4:
        st.markdown("#### Multi-Scenario Comparison")
        st.markdown("**Compare land use patterns across different climate scenarios**")

        # Load available scenarios
        scenarios_df, scenarios_error = load_scenario_comparison_data()
        if scenarios_error:
            st.error(f"❌ {scenarios_error}")
        elif scenarios_df is not None and not scenarios_df.empty:
            # Create columns for filters
            col1, col2 = st.columns([3, 1])

            with col1:
                # Multi-select for scenarios
                selected_scenarios = st.multiselect(
                    "Select scenarios to compare (2-6 recommended)",
                    scenarios_df['scenario_name'].tolist(),
                    default=scenarios_df['scenario_name'].tolist()[:3],
                    max_selections=6,
                    key="scenario_spider",
                    help="Select 2-6 scenarios for optimal visualization"
                )

            with col2:
                # Show selected count
                st.metric("Selected", f"{len(selected_scenarios)}/6")

            if selected_scenarios and len(selected_scenarios) >= 2:
                # Create spider chart
                fig, chart_error = create_scenario_spider_chart(selected_scenarios)
                if chart_error:
                    st.error(f"❌ {chart_error}")
                elif fig:
                    st.plotly_chart(fig, use_container_width=True)

                    # Show scenario details
                    st.markdown("##### 📊 Selected Scenario Details")
                    selected_details = scenarios_df[scenarios_df['scenario_name'].isin(selected_scenarios)]

                    # Create a summary table
                    summary_df = selected_details[['climate_model', 'rcp_scenario', 'ssp_scenario']].copy()
                    summary_df['Model'] = summary_df['climate_model']
                    summary_df['RCP'] = summary_df['rcp_scenario'].str.upper()
                    summary_df['SSP'] = summary_df['ssp_scenario'].str.upper()
                    summary_df = summary_df[['Model', 'RCP', 'SSP']]

                    st.dataframe(summary_df, use_container_width=True, hide_index=True)

                    st.info("📊 **Note:** Values are normalized to 100% for each scenario to enable comparison of relative land use patterns.")
            else:
                st.warning("Please select at least 2 scenarios to create a comparison chart.")
        else:
            st.info("No scenario data available")

def show_summary_metrics():
    """Display summary metrics cards in wide layout"""
    stats, error = load_summary_data()

    if error:
        st.error(f"❌ {error}")
        return

    if stats:
        # Create a container for metrics with custom styling
        st.markdown("""
        <style>
        .metric-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 12px;
            color: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            text-align: center;
            height: 100%;
        }
        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .metric-label {
            font-size: 1rem;
            opacity: 0.9;
        }
        </style>
        """, unsafe_allow_html=True)

        # Use 6 columns for better wide layout distribution
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 2])

        with col1:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['total_counties']:,}</div>
                <div class="metric-label">🏛️ US Counties</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['total_scenarios']}</div>
                <div class="metric-label">🌡️ Climate Scenarios</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['total_transitions']/1000000:.1f}M</div>
                <div class="metric-label">🔄 Land Transitions</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-value">{stats['time_periods']}</div>
                <div class="metric-label">📅 Time Periods</div>
            </div>
            """, unsafe_allow_html=True)

        with col5:
            st.markdown("""
            <div class="metric-container">
                <div class="metric-value">2012-2100</div>
                <div class="metric-label">📆 Year Range</div>
            </div>
            """, unsafe_allow_html=True)

        with col6:
            st.markdown("""
            <div class="metric-container">
                <div class="metric-value">5</div>
                <div class="metric-label">🌍 Land Use Types</div>
            </div>
            """, unsafe_allow_html=True)

def main():
    """Main analytics dashboard"""
    st.title("📊 RPA Assessment Analytics Dashboard")
    st.markdown("**Visualizations and insights from the USDA Forest Service 2020 RPA Assessment**")

    # Show summary metrics
    show_summary_metrics()

    st.markdown("---")

    # Create tabs for different analysis areas
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏙️ Urbanization Trends",
        "🌾 Agricultural Analysis",
        "🌲 Forest Analysis",
        "🌡️ Climate Scenarios",
        "📈 Time Series",
        "🎨 Enhanced Visualizations"
    ])

    with tab1:
        st.markdown("### 🏙️ Urbanization Patterns")
        st.markdown("**Comprehensive analysis of urban expansion across states and land use sources**")

        urban_data, urban_error = load_urbanization_data()
        if urban_error:
            st.error(f"❌ {urban_error}")
        elif urban_data is not None and not urban_data.empty:
            # Create two-column layout for urbanization analysis
            viz_col1, viz_col2 = st.columns(2)

            with viz_col1:
                # Sources of urbanization
                st.markdown("#### 🏘️ Urbanization Sources")
                source_breakdown = urban_data.groupby('from_landuse')['total_acres_urbanized'].sum().sort_values(ascending=False)

                fig_pie = px.pie(
                    values=source_breakdown.values,
                    names=source_breakdown.index,
                    title="Land Converted to Urban",
                    color_discrete_sequence=RPA_COLOR_SEQUENCE,
                    hole=0.4  # Donut chart
                )
                fig_pie.update_traces(textinfo='percent+label')
                fig_pie.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)

            with viz_col2:
                # Top converting states map preview
                st.markdown("#### 📍 Geographic Distribution")
                state_totals = urban_data.groupby('state_code')['total_acres_urbanized'].sum().reset_index()
                state_totals['state_abbr'] = state_totals['state_code'].map(StateMapper.FIPS_TO_ABBREV)

                # Mini choropleth
                fig_map = px.choropleth(
                    state_totals.head(20),
                    locations='state_abbr',
                    locationmode='USA-states',
                    color='total_acres_urbanized',
                    color_continuous_scale=RPA_BROWN_SCALE,
                    title="Urban Expansion Hotspots"
                )
                fig_map.update_layout(
                    geo={'scope': 'usa'},
                    height=350,
                    margin={"r":0,"t":30,"l":0,"b":0}
                )
                st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': False})

            # Detailed insights in full width
            st.markdown("---")

            # Create expandable sections for detailed analysis
            with st.container():
                detail_col1, detail_col2, detail_col3 = st.columns([2, 2, 2])

                with detail_col1:
                    st.markdown("#### 🔍 Key Insights")
                    if not urban_data.empty:
                        top_state_data = urban_data.groupby('state_code')['total_acres_urbanized'].sum().sort_values(ascending=False)
                        top_state = top_state_data.index[0]
                        top_state_acres = top_state_data.iloc[0]

                        st.success(f"""
                        **Urban Development Patterns:**
                        - **Top State:** {StateMapper.FIPS_TO_NAME.get(top_state, top_state)} ({top_state_acres/1e6:.1f}M acres)
                        - **Primary Source:** {source_breakdown.index[0]} → Urban
                        - **Total Urbanized:** {source_breakdown.sum()/1e6:.1f}M acres nationwide
                        """)

                with detail_col2:
                    st.markdown("#### 📊 Source Breakdown")
                    source_df = pd.DataFrame({
                        'Land Type': source_breakdown.index,
                        'Acres': source_breakdown.apply(lambda x: f"{x/1e6:.2f}M"),
                        'Percent': source_breakdown.apply(lambda x: f"{x/source_breakdown.sum()*100:.1f}%")
                    })
                    st.dataframe(source_df, use_container_width=True, hide_index=True)

                with detail_col3:
                    st.markdown("#### 🏆 Top 10 States")
                    top_states_df = top_state_data.head(10).reset_index()
                    top_states_df['state_name'] = top_states_df['state_code'].map(StateMapper.FIPS_TO_NAME)
                    top_states_df['acres'] = top_states_df['total_acres_urbanized'].apply(lambda x: f"{x/1e6:.2f}M")
                    display_df = top_states_df[['state_name', 'acres']].copy()
                    display_df.columns = ['State', 'Urban Expansion']
                    st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("📊 No urbanization data available")

    with tab2:
        st.markdown("### 🌾 Agricultural Land Loss Analysis")
        st.markdown("**Comprehensive analysis of agricultural land conversion across climate scenarios**")

        ag_data, ag_error = load_agricultural_loss_data()
        if ag_error:
            st.error(f"❌ {ag_error}")
        elif ag_data is not None and not ag_data.empty:
            # Create side-by-side layout for charts
            chart_col1, chart_col2 = st.columns([3, 2])

            with chart_col1:
                # Main agricultural loss chart
                fig = create_agricultural_loss_chart(ag_data)
                if fig:
                    fig.update_layout(height=600)  # Taller for wide layout
                    st.plotly_chart(fig, use_container_width=True)

            with chart_col2:
                # Additional visualization - pie chart of RCP scenarios
                rcp_counts = ag_data['rcp_scenario'].value_counts()
                fig_pie = px.pie(
                    values=rcp_counts.values,
                    names=[s.upper() for s in rcp_counts.index],
                    title="Distribution by Climate Pathway",
                    color_discrete_map={'RCP45': '#2E86AB', 'RCP85': '#F24236'}
                )
                fig_pie.update_layout(height=300)
                st.plotly_chart(fig_pie, use_container_width=True)

                # Summary statistics
                st.markdown("#### 📊 Summary Statistics")
                total_loss = ag_data['total_acres_lost'].sum()
                avg_loss = ag_data['total_acres_lost'].mean()

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Loss", f"{total_loss/1e6:.1f}M acres")
                with col2:
                    st.metric("Avg per Scenario", f"{avg_loss/1e6:.1f}M acres")

            # Insights and data table in full width
            st.markdown("---")

            insight_col1, insight_col2, insight_col3 = st.columns([2, 2, 1])

            with insight_col1:
                st.markdown("#### 🔍 Key Insights")
                if not ag_data.empty:
                    top_scenario = ag_data.iloc[0]
                    rcp85_count = len(ag_data[ag_data['rcp_scenario'] == 'rcp85'])
                    total_scenarios = len(ag_data)

                    st.info(f"""
                    **Major Findings:**
                    - **Highest Loss:** {top_scenario['scenario_name']} ({top_scenario['total_acres_lost']/1e6:.1f}M acres)
                    - **RCP8.5 Dominance:** {rcp85_count}/{total_scenarios} scenarios ({rcp85_count/total_scenarios*100:.0f}%)
                    - **Climate Impact:** Higher emissions → more agricultural loss
                    """)

            with insight_col2:
                st.markdown("#### 📋 Top 5 Scenarios")
                display_df = ag_data.head(5)[['scenario_name', 'rcp_scenario', 'ssp_scenario', 'total_acres_lost']].copy()
                display_df['total_acres_lost'] = display_df['total_acres_lost'].apply(lambda x: f"{x/1e6:.2f}M")
                display_df.columns = ['Scenario', 'RCP', 'SSP', 'Acres Lost']
                st.dataframe(display_df, use_container_width=True, hide_index=True)

            with insight_col3:
                st.markdown("#### 🎯 Quick Actions")
                if st.button("📥 Export Data", key="export_ag"):
                    st.download_button(
                        label="Download CSV",
                        data=ag_data.to_csv(index=False),
                        file_name="agricultural_loss_data.csv",
                        mime="text/csv"
                    )
        else:
            st.info("📊 No agricultural data available")

    with tab3:
        st.markdown("### 🌲 Forest Analysis")
        st.markdown("**Comprehensive analysis of forest gains, losses, and transitions**")

        # Load forest data
        df_loss, df_gain, df_states, forest_error = load_forest_analysis_data()

        if forest_error:
            st.error(f"❌ {forest_error}")
        else:
            # Create sub-tabs for forest analysis
            forest_tab1, forest_tab2, forest_tab3 = st.tabs([
                "📊 Overview",
                "🗺️ Geographic Distribution",
                "🌡️ Climate Impact"
            ])

            with forest_tab1:
                st.markdown("#### 🌲 Forest Transition Overview")

                if df_loss is not None and df_gain is not None:
                    # Wide layout with main visualization and side metrics
                    main_col, metrics_col = st.columns([4, 2])

                    with main_col:
                        # Show flow chart
                        fig = create_forest_flow_chart(df_loss, df_gain)
                        if fig:
                            fig.update_layout(height=500)
                            st.plotly_chart(fig, use_container_width=True)

                    with metrics_col:
                        # Key metrics in vertical layout
                        total_loss = df_loss['total_acres'].sum()
                        total_gain = df_gain['total_acres'].sum()
                        net_change = total_gain - total_loss

                        st.markdown("#### 📊 Forest Metrics")

                        st.metric(
                            "🔻 Total Forest Loss",
                            f"{total_loss/1e6:.1f}M acres",
                            help="Total forest converted to other land uses"
                        )

                        st.metric(
                            "🔺 Total Forest Gain",
                            f"{total_gain/1e6:.1f}M acres",
                            help="Total land converted to forest"
                        )

                        st.metric(
                            "📊 Net Change",
                            f"{net_change/1e6:+.1f}M acres",
                            delta=f"{(net_change/total_loss)*100:+.1f}%",
                            help="Net forest change across all scenarios"
                        )

                        # Quick insight box
                        if net_change < 0:
                            st.error(f"⚠️ Net forest loss of {abs(net_change/1e6):.1f}M acres projected")
                        else:
                            st.success(f"✅ Net forest gain of {net_change/1e6:.1f}M acres projected")

                    # Detailed breakdowns in full width
                    st.markdown("---")

                    # Use three columns for detailed analysis
                    detail_col1, detail_col2, detail_col3 = st.columns([2, 2, 2])

                    with detail_col1:
                        st.markdown("##### 🔻 Forest Loss Destinations")
                        loss_summary = df_loss.groupby('to_landuse')['total_acres'].sum().sort_values(ascending=False)

                        # Create a horizontal bar chart
                        fig_loss = px.bar(
                            x=loss_summary.values,
                            y=loss_summary.index,
                            orientation='h',
                            title="Where Forests Convert To",
                            labels={'x': 'Acres', 'y': 'Land Use Type'},
                            color=loss_summary.values,
                            color_continuous_scale=RPA_BROWN_SCALE
                        )
                        fig_loss.update_layout(height=300, showlegend=False)
                        st.plotly_chart(fig_loss, use_container_width=True)

                    with detail_col2:
                        st.markdown("##### 🔺 Forest Gain Sources")
                        gain_summary = df_gain.groupby('from_landuse')['total_acres'].sum().sort_values(ascending=False)

                        # Create a horizontal bar chart
                        fig_gain = px.bar(
                            x=gain_summary.values,
                            y=gain_summary.index,
                            orientation='h',
                            title="Where Forest Gains Come From",
                            labels={'x': 'Acres', 'y': 'Land Use Type'},
                            color=gain_summary.values,
                            color_continuous_scale=RPA_GREEN_SCALE
                        )
                        fig_gain.update_layout(height=300, showlegend=False)
                        st.plotly_chart(fig_gain, use_container_width=True)

                    with detail_col3:
                        st.markdown("##### 📊 Transition Summary")

                        # Combined summary table
                        loss_pct = loss_summary / loss_summary.sum() * 100
                        gain_pct = gain_summary / gain_summary.sum() * 100

                        summary_data = []
                        for landuse in set(loss_summary.index) | set(gain_summary.index):
                            summary_data.append({
                                'Land Use': landuse,
                                'Loss %': f"{loss_pct.get(landuse, 0):.1f}%" if landuse in loss_pct else "-",
                                'Gain %': f"{gain_pct.get(landuse, 0):.1f}%" if landuse in gain_pct else "-"
                            })

                        summary_df = pd.DataFrame(summary_data)
                        st.dataframe(summary_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No forest transition data available")

            with forest_tab2:
                st.markdown("#### Geographic Distribution of Forest Changes")

                if df_states is not None and not df_states.empty:
                    # Show map
                    fig = create_forest_state_map(df_states)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})

                    # State rankings
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("##### 🌲 Top States - Net Forest Gain")
                        top_gain_states = df_states.nlargest(10, 'net_change')[['state_name', 'net_change', 'forest_gain']]
                        top_gain_states['net_change'] = top_gain_states['net_change'].apply(lambda x: f"{x/1e6:+.2f}M")
                        top_gain_states['forest_gain'] = top_gain_states['forest_gain'].apply(lambda x: f"{x/1e6:.2f}M")
                        st.dataframe(
                            top_gain_states.rename(columns={
                                'state_name': 'State',
                                'net_change': 'Net Change',
                                'forest_gain': 'Total Gain'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )

                    with col2:
                        st.markdown("##### 🔥 Top States - Net Forest Loss")
                        top_loss_states = df_states.nsmallest(10, 'net_change')[['state_name', 'net_change', 'forest_loss']]
                        top_loss_states['net_change'] = top_loss_states['net_change'].apply(lambda x: f"{x/1e6:+.2f}M")
                        top_loss_states['forest_loss'] = top_loss_states['forest_loss'].apply(lambda x: f"{x/1e6:.2f}M")
                        st.dataframe(
                            top_loss_states.rename(columns={
                                'state_name': 'State',
                                'net_change': 'Net Change',
                                'forest_loss': 'Total Loss'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )

                    # Summary insights
                    st.markdown("##### 🔍 Geographic Insights")
                    gaining_states = len(df_states[df_states['net_change'] > 0])
                    losing_states = len(df_states[df_states['net_change'] < 0])

                    st.info(f"""
                    **Key Findings:**
                    - {gaining_states} states show net forest gain
                    - {losing_states} states show net forest loss
                    - Regional patterns suggest climate and development pressures vary significantly by location
                    """)
                else:
                    st.info("No geographic data available")

            with forest_tab3:
                st.markdown("#### Climate Scenario Impact on Forests")

                if df_loss is not None and df_gain is not None:
                    # Show scenario comparison
                    fig = create_forest_scenario_comparison(df_loss, df_gain)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

                    # Scenario details
                    st.markdown("##### 📊 Scenario Breakdown")

                    # Create summary by scenario
                    scenario_summary = []
                    for scenario in ['rcp45', 'rcp85']:
                        loss_acres = df_loss[df_loss['rcp_scenario'] == scenario]['total_acres'].sum()
                        gain_acres = df_gain[df_gain['rcp_scenario'] == scenario]['total_acres'].sum()
                        net = gain_acres - loss_acres

                        scenario_summary.append({
                            'Scenario': scenario.upper(),
                            'Forest Loss': f"{loss_acres/1e6:.2f}M acres",
                            'Forest Gain': f"{gain_acres/1e6:.2f}M acres",
                            'Net Change': f"{net/1e6:+.2f}M acres",
                            'Net %': f"{(net/loss_acres)*100:+.1f}%"
                        })

                    summary_df = pd.DataFrame(scenario_summary)
                    st.dataframe(summary_df, use_container_width=True, hide_index=True)

                    # Climate insights
                    st.markdown("##### 🌡️ Climate Impact Analysis")

                    rcp45_net = summary_df[summary_df['Scenario'] == 'RCP45']['Net Change'].iloc[0]
                    rcp85_net = summary_df[summary_df['Scenario'] == 'RCP85']['Net Change'].iloc[0]

                    st.info(f"""
                    **Climate Scenario Insights:**
                    - RCP4.5 (moderate emissions): {rcp45_net} net forest change
                    - RCP8.5 (high emissions): {rcp85_net} net forest change
                    - Higher emission scenarios typically show different forest transition patterns
                    - Climate impacts interact with socioeconomic factors (SSP scenarios) to drive land use change
                    """)
                else:
                    st.info("No climate scenario data available")

    with tab4:
        st.markdown("### Climate Scenario Comparison")
        st.markdown("**Differences in land use patterns between RPA climate pathways**")

        # Add RPA scenario context
        with st.expander("📚 Understanding RPA Scenarios", expanded=False):
            st.markdown("""
            The 2020 RPA Assessment uses **four integrated scenarios** combining climate and socioeconomic pathways:

            #### Climate Pathways (RCPs)
            - **RCP 4.5**: Lower emissions (~2.5°C warming by 2100) - assumes climate policies
            - **RCP 8.5**: High emissions (~4.5°C warming by 2100) - limited climate action

            #### Socioeconomic Pathways (SSPs)
            - **SSP1 - Sustainability**: Green growth, international cooperation
            - **SSP2 - Middle of the Road**: Historical trends continue
            - **SSP3 - Regional Rivalry**: Nationalism, resource competition
            - **SSP5 - Fossil-fueled Development**: Rapid growth, high consumption

            #### The Four RPA Scenarios
            | Code | Name | Climate | Society | U.S. Growth |
            |------|------|---------|---------|-------------|
            | **LM** | Lower-Moderate | RCP4.5-SSP1 | Sustainable | GDP: 3.0x, Pop: 1.5x |
            | **HL** | High-Low | RCP8.5-SSP3 | Regional rivalry | GDP: 1.9x, Pop: 1.0x |
            | **HM** | High-Moderate | RCP8.5-SSP2 | Middle road | GDP: 2.8x, Pop: 1.4x |
            | **HH** | High-High | RCP8.5-SSP5 | Fossil-fueled | GDP: 4.7x, Pop: 1.9x |
            """)

        climate_data, climate_error = load_climate_comparison_data()
        if climate_error:
            st.error(f"❌ {climate_error}")
        elif climate_data is not None and not climate_data.empty:

            # Show sunburst chart
            fig = create_climate_comparison_chart(climate_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # Show RCP comparison
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### RCP4.5 vs RCP8.5 Summary")
                rcp_comparison = climate_data.groupby('rcp_scenario')['total_acres'].sum()

                fig_bar = px.bar(
                    x=rcp_comparison.index,
                    y=rcp_comparison.values,
                    title="Total Land Use Changes by RCP Scenario",
                    labels={'x': 'RCP Scenario', 'y': 'Total Acres'},
                    color=rcp_comparison.index,
                    color_discrete_map={'rcp45': '#2E86AB', 'rcp85': '#F24236'}
                )
                fig_bar.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

            with col2:
                st.markdown("#### 🔍 RPA Climate Insights")
                if len(rcp_comparison) >= 2:
                    rcp85_total = rcp_comparison.get('rcp85', 0)
                    rcp45_total = rcp_comparison.get('rcp45', 0)
                    difference = ((rcp85_total - rcp45_total) / rcp45_total * 100) if rcp45_total > 0 else 0

                    st.markdown(f"""
                    - **RCP8.5 Impact:** {difference:+.1f}% more land use change vs RCP4.5
                    - **Scenario LM (RCP4.5):** Only sustainable development scenario
                    - **Scenarios HL/HM/HH (RCP8.5):** All high-warming futures
                    - **Policy Relevance:** Sustainable path (LM) shows least disruption
                    """)
        else:
            st.info("📊 No climate comparison data available")

    with tab5:
        st.markdown("### Time Series Analysis")
        st.markdown("**How land use transitions change over time periods**")

        time_data, time_error = load_time_series_data()
        if time_error:
            st.error(f"❌ {time_error}")
        elif time_data is not None and not time_data.empty:

            # Show time series chart
            fig = create_time_series_chart(time_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

            # Show period analysis
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown("#### 📅 Changes by Time Period")
                period_totals = time_data.groupby('year_range')['total_acres'].sum().sort_values(ascending=False)

                fig_period = px.bar(
                    x=period_totals.index,
                    y=period_totals.values,
                    title="Total Land Use Changes by Time Period",
                    labels={'x': 'Time Period', 'y': 'Total Acres'},
                    color=period_totals.values,
                    color_continuous_scale=RPA_BLUE_SCALE
                )
                fig_period.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig_period, use_container_width=True)

            with col2:
                st.markdown("#### 🔍 Temporal Insights")
                if not time_data.empty:
                    peak_period = period_totals.index[0]
                    st.markdown(f"""
                    - **Peak Activity:** {peak_period} shows highest land use change
                    - **Trends:** Acceleration or deceleration of transitions over time
                    - **Future Outlook:** Projections through 2100
                    """)

                st.markdown("#### 📊 Period Summary")
                st.dataframe(period_totals.head(6), use_container_width=True)
        else:
            st.info("📊 No time series data available")

    with tab6:
        show_enhanced_visualizations()

    # Footer
    st.markdown("---")
    st.markdown("""
    **💡 Want to explore further?**
    - Use the **Chat** interface for custom natural language queries
    - Visit the **Data Explorer** for advanced SQL analysis
    - Check **Settings** for configuration options
    """)

if __name__ == "__main__":
    main()
