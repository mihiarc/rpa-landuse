#!/usr/bin/env python3
"""
Analytics Dashboard for Landuse Data
Pre-built visualizations and insights for land use transition analysis
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import duckdb
import sys
from pathlib import Path
import os

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

@st.cache_data
def get_database_connection():
    """Get database connection with caching"""
    try:
        db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
        if not Path(db_path).exists():
            return None, f"Database not found at {db_path}"
        
        conn = duckdb.connect(str(db_path), read_only=True)
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
        stats['total_counties'] = conn.execute("SELECT COUNT(DISTINCT fips_code) FROM dim_geography").fetchone()[0]
        stats['total_scenarios'] = conn.execute("SELECT COUNT(*) FROM dim_scenario").fetchone()[0]
        stats['total_transitions'] = conn.execute("SELECT COUNT(*) FROM fact_landuse_transitions WHERE transition_type = 'change'").fetchone()[0]
        stats['time_periods'] = conn.execute("SELECT COUNT(*) FROM dim_time").fetchone()[0]
        
        conn.close()
        return stats, None
    except Exception as e:
        conn.close()
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
        
        df = conn.execute(query).df()
        conn.close()
        return df, None
    except Exception as e:
        conn.close()
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
        
        df = conn.execute(query).df()
        conn.close()
        return df, None
    except Exception as e:
        conn.close()
        return None, f"Error loading urbanization data: {e}"

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
        
        df = conn.execute(query).df()
        conn.close()
        return df, None
    except Exception as e:
        conn.close()
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
        
        df = conn.execute(query).df()
        conn.close()
        return df, None
    except Exception as e:
        conn.close()
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
        font=dict(size=12)
    )
    
    # Format x-axis to show millions
    fig.update_xaxis(tickformat='.1s')
    
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
        color_continuous_scale='Reds'
    )
    
    fig.update_layout(
        height=500,
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title="Acres Urbanized (millions)",
        font=dict(size=12)
    )
    
    fig.update_xaxis(tickformat='.1s')
    
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
        color_continuous_scale='RdYlBu_r'
    )
    
    fig.update_layout(height=600, font=dict(size=12))
    
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
        font=dict(size=12),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02)
    )
    
    fig.update_yaxis(tickformat='.1s')
    
    return fig

def show_summary_metrics():
    """Display summary metrics cards"""
    stats, error = load_summary_data()
    
    if error:
        st.error(f"❌ {error}")
        return
    
    if stats:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "🏛️ US Counties", 
                f"{stats['total_counties']:,}",
                help="Total number of counties in the dataset"
            )
        
        with col2:
            st.metric(
                "🌡️ Climate Scenarios", 
                stats['total_scenarios'],
                help="Number of climate and socioeconomic scenarios"
            )
        
        with col3:
            st.metric(
                "🔄 Land Transitions", 
                f"{stats['total_transitions']:,}",
                help="Total number of land use change records"
            )
        
        with col4:
            st.metric(
                "📅 Time Periods", 
                stats['time_periods'],
                help="Number of time periods (2012-2100)"
            )

def main():
    """Main analytics dashboard"""
    st.title("📊 Analytics Dashboard")
    st.markdown("**Pre-built visualizations and insights for land use transition analysis**")
    
    # Show summary metrics
    show_summary_metrics()
    
    st.markdown("---")
    
    # Create tabs for different analysis areas
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌾 Agricultural Analysis", 
        "🏙️ Urbanization Trends", 
        "🌡️ Climate Scenarios", 
        "📈 Time Series"
    ])
    
    with tab1:
        st.markdown("### Agricultural Land Loss Analysis")
        st.markdown("**Scenarios showing the greatest loss of agricultural land to other uses**")
        
        ag_data, ag_error = load_agricultural_loss_data()
        if ag_error:
            st.error(f"❌ {ag_error}")
        elif ag_data is not None and not ag_data.empty:
            
            # Show chart
            fig = create_agricultural_loss_chart(ag_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            # Show insights
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("#### 🔍 Key Insights")
                if not ag_data.empty:
                    top_scenario = ag_data.iloc[0]
                    rcp85_count = len(ag_data[ag_data['rcp_scenario'] == 'rcp85'])
                    total_scenarios = len(ag_data)
                    
                    st.markdown(f"""
                    - **Highest Loss:** {top_scenario['scenario_name']} with {top_scenario['total_acres_lost']:,.0f} acres
                    - **RCP8.5 Dominance:** {rcp85_count}/{total_scenarios} of top scenarios use RCP8.5 (higher emissions)
                    - **Climate Impact:** Higher emission scenarios generally show more agricultural land loss
                    """)
            
            with col2:
                st.markdown("#### 📋 Data Table")
                st.dataframe(
                    ag_data.head(10)[['scenario_name', 'rcp_scenario', 'total_acres_lost']],
                    use_container_width=True
                )
        else:
            st.info("📊 No agricultural data available")
    
    with tab2:
        st.markdown("### Urbanization Patterns")
        st.markdown("**States experiencing the most land conversion to urban use**")
        
        urban_data, urban_error = load_urbanization_data()
        if urban_error:
            st.error(f"❌ {urban_error}")
        elif urban_data is not None and not urban_data.empty:
            
            # Show chart
            fig = create_urbanization_chart(urban_data)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
            
            # Show breakdown by source land use
            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("#### 🏘️ Urbanization Sources")
                source_breakdown = urban_data.groupby('from_landuse')['total_acres_urbanized'].sum().sort_values(ascending=False)
                
                fig_pie = px.pie(
                    values=source_breakdown.values,
                    names=source_breakdown.index,
                    title="Sources of Urban Development",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig_pie.update_layout(height=400)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                st.markdown("#### 🔍 Key Insights")
                if not urban_data.empty:
                    top_state = urban_data.groupby('state_code')['total_acres_urbanized'].sum().sort_values(ascending=False).iloc[0]
                    
                    st.markdown(f"""
                    - **Most Active State:** Leading in urban expansion
                    - **Primary Source:** {source_breakdown.index[0]} land most commonly converted
                    - **Development Pressure:** Concentrated in specific regions
                    """)
                
                st.markdown("#### 📊 Top States")
                state_totals = urban_data.groupby('state_code')['total_acres_urbanized'].sum().sort_values(ascending=False).head(10)
                st.dataframe(state_totals, use_container_width=True)
        else:
            st.info("📊 No urbanization data available")
    
    with tab3:
        st.markdown("### Climate Scenario Comparison")
        st.markdown("**Differences in land use patterns between climate pathways**")
        
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
                st.markdown("#### 🔍 Climate Insights")
                if len(rcp_comparison) >= 2:
                    rcp85_total = rcp_comparison.get('rcp85', 0)
                    rcp45_total = rcp_comparison.get('rcp45', 0)
                    difference = ((rcp85_total - rcp45_total) / rcp45_total * 100) if rcp45_total > 0 else 0
                    
                    st.markdown(f"""
                    - **RCP8.5 Impact:** {difference:+.1f}% more land use change vs RCP4.5
                    - **Higher Emissions:** Lead to more dramatic land use transitions
                    - **Policy Relevance:** Shows importance of climate mitigation
                    """)
        else:
            st.info("📊 No climate comparison data available")
    
    with tab4:
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
                    color_continuous_scale='Blues'
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