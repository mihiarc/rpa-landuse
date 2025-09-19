#!/usr/bin/env python3
"""
Data Explorer for Landuse Database
Advanced tools for exploring database schema, running custom queries, and browsing data
"""

import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import duckdb
import pandas as pd
import streamlit as st

from landuse.connections import DuckDBConnection

# Configuration constants
MAX_DISPLAY_ROWS = 1000
DEFAULT_DISPLAY_ROWS = 100
DEFAULT_TTL = 300  # 5 minutes for most queries
SCHEMA_TTL = 3600  # 1 hour for schema information
MAX_EXPORT_ROWS = 10000
QUERY_TIMEOUT = 30  # seconds

# Allowed tables for security
ALLOWED_TABLES = {
    'dim_geography', 'dim_indicators', 'dim_landuse', 'dim_scenario',
    'dim_socioeconomic', 'dim_time', 'fact_landuse_transitions',
    'fact_socioeconomic_projections', 'v_full_projection_period',
    'v_income_trends', 'v_landuse_socioeconomic', 'v_population_trends',
    'v_scenarios_combined'
}


@st.cache_resource
def get_database_connection():
    """Get cached database connection using st.connection"""
    try:
        conn = st.connection(
            name="landuse_db_explorer",
            type=DuckDBConnection,
            database=os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'),
            read_only=True
        )
        return conn
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        st.stop()


@st.cache_data(ttl=SCHEMA_TTL)
def get_table_schema():
    """Get comprehensive table schema information"""
    conn = get_database_connection()

    try:
        tables_df = conn.list_tables(ttl=SCHEMA_TTL)
        schema_info = {}

        for _, row in tables_df.iterrows():
            table_name = row['table_name']

            if table_name not in ALLOWED_TABLES:
                continue

            columns = conn.get_table_info(table_name, ttl=SCHEMA_TTL)
            row_count = conn.get_row_count(table_name, ttl=DEFAULT_TTL)
            sample_query = f'SELECT * FROM "{table_name}" LIMIT 5'
            sample_data = conn.query(sample_query, ttl=SCHEMA_TTL)

            schema_info[table_name] = {
                'columns': columns,
                'row_count': row_count,
                'sample_data': sample_data
            }

        return schema_info
    except Exception as e:
        st.error(f"❌ Error getting schema: {e}")
        return {}


@st.cache_data
def get_query_examples():
    """Get example queries organized by category"""
    return {
        "Basic Queries": {
            "Count records by table": """
SELECT 'dim_scenario' as table_name, COUNT(*) as row_count FROM dim_scenario
UNION ALL
SELECT 'dim_time', COUNT(*) FROM dim_time
UNION ALL
SELECT 'dim_geography', COUNT(*) FROM dim_geography
UNION ALL
SELECT 'dim_landuse', COUNT(*) FROM dim_landuse
UNION ALL
SELECT 'fact_landuse_transitions', COUNT(*) FROM fact_landuse_transitions;
""",
            "Browse scenarios": """
SELECT
    scenario_id,
    scenario_name,
    climate_model,
    rcp_scenario,
    ssp_scenario
FROM dim_scenario
ORDER BY scenario_name;
""",
            "Browse geography": """
SELECT
    geography_id,
    fips_code,
    county_name,
    state_code,
    state_name,
    region
FROM dim_geography
WHERE state_name IS NOT NULL
ORDER BY state_name, county_name
LIMIT 20;
"""
        },
        "Agricultural Analysis": {
            "Agricultural land loss": """
SELECT
    s.scenario_name,
    g.state_code,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE fl.landuse_category = 'Agriculture'
  AND tl.landuse_category != 'Agriculture'
  AND f.transition_type = 'change'
GROUP BY s.scenario_name, g.state_code, fl.landuse_name, tl.landuse_name
ORDER BY total_acres DESC
LIMIT 50;
""",
            "Crop vs Pasture transitions": """
SELECT
    t.year_range,
    g.state_code,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    AVG(f.acres) as avg_acres_per_scenario,
    COUNT(DISTINCT s.scenario_id) as scenario_count
FROM fact_landuse_transitions f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE ((fl.landuse_name = 'Crop' AND tl.landuse_name = 'Pasture')
   OR (fl.landuse_name = 'Pasture' AND tl.landuse_name = 'Crop'))
  AND f.transition_type = 'change'
GROUP BY t.year_range, g.state_code, fl.landuse_name, tl.landuse_name
ORDER BY avg_acres_per_scenario DESC
LIMIT 30;
"""
        },
        "Climate Analysis": {
            "RCP scenario comparison": """
SELECT
    s.rcp_scenario,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres,
    COUNT(DISTINCT s.scenario_id) as scenario_count
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
  AND fl.landuse_name != tl.landuse_name
GROUP BY s.rcp_scenario, fl.landuse_name, tl.landuse_name
ORDER BY total_acres DESC
LIMIT 40;
""",
            "SSP pathway impacts": """
SELECT
    s.ssp_scenario,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres,
    AVG(f.acres) as avg_acres_per_transition
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
  AND fl.landuse_name != tl.landuse_name
GROUP BY s.ssp_scenario, fl.landuse_name, tl.landuse_name
ORDER BY total_acres DESC
LIMIT 40;
"""
        },
        "Geographic Analysis": {
            "State-level summaries": """
SELECT
    g.state_code,
    g.state_name,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres,
    COUNT(DISTINCT g.fips_code) as counties_affected
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
  AND fl.landuse_name != tl.landuse_name
  AND g.state_name IS NOT NULL
GROUP BY g.state_code, g.state_name, fl.landuse_name, tl.landuse_name
ORDER BY total_acres DESC
LIMIT 50;
""",
            "County hotspots": """
SELECT
    g.fips_code,
    g.county_name,
    g.state_code,
    SUM(f.acres) as total_transition_acres,
    COUNT(DISTINCT CONCAT(fl.landuse_name, '->', tl.landuse_name)) as transition_types
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
  AND fl.landuse_name != tl.landuse_name
GROUP BY g.fips_code, g.county_name, g.state_code
ORDER BY total_transition_acres DESC
LIMIT 30;
"""
        },
        "Time Series": {
            "Trends over time": """
SELECT
    t.year_range,
    t.start_year,
    t.end_year,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres,
    AVG(f.acres) as avg_acres_per_scenario
FROM fact_landuse_transitions f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
  AND fl.landuse_name != tl.landuse_name
GROUP BY t.year_range, t.start_year, t.end_year, fl.landuse_name, tl.landuse_name
ORDER BY t.start_year, total_acres DESC;
""",
            "Acceleration analysis": """
WITH period_comparison AS (
  SELECT
    CASE
      WHEN t.start_year <= 2040 THEN 'Early (2012-2040)'
      ELSE 'Late (2041-2100)'
    END as period_group,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres
  FROM fact_landuse_transitions f
  JOIN dim_time t ON f.time_id = t.time_id
  JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
  JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
  WHERE f.transition_type = 'change'
    AND fl.landuse_name != tl.landuse_name
  GROUP BY period_group, fl.landuse_name, tl.landuse_name
)
SELECT
  from_landuse,
  to_landuse,
  SUM(CASE WHEN period_group = 'Early (2012-2040)' THEN total_acres ELSE 0 END) as early_period_acres,
  SUM(CASE WHEN period_group = 'Late (2041-2100)' THEN total_acres ELSE 0 END) as late_period_acres,
  (SUM(CASE WHEN period_group = 'Late (2041-2100)' THEN total_acres ELSE 0 END) -
   SUM(CASE WHEN period_group = 'Early (2012-2040)' THEN total_acres ELSE 0 END)) as acceleration
FROM period_comparison
GROUP BY from_landuse, to_landuse
ORDER BY ABS(acceleration) DESC
LIMIT 20;
"""
        }
    }


def execute_query(query: str, ttl: int = 60):
    """
    Execute a SQL query using the cached database connection.

    Args:
        query: SQL query to execute
        ttl: Time-to-live for cache in seconds

    Returns:
        DataFrame with query results

    Raises:
        Various DuckDB exceptions with user-friendly error messages
    """
    conn = get_database_connection()

    # Add safety limit if not present (skip if query has UNION)
    query_trimmed = query.strip().rstrip(';')
    query_upper = query_trimmed.upper()

    # Only add LIMIT if:
    # 1. It's a SELECT query
    # 2. Doesn't already have LIMIT
    # 3. Doesn't have UNION (which may have its own limits)
    if (query_upper.startswith('SELECT') and
        'LIMIT' not in query_upper and
        'UNION' not in query_upper):
        query = f"{query_trimmed} LIMIT {MAX_DISPLAY_ROWS}"
    else:
        query = query_trimmed

    try:
        return conn.query(query, ttl=ttl)
    except duckdb.BinderException as e:
        error_str = str(e).lower()
        if "column" in error_str and "not found" in error_str:
            st.error(f"❌ Column not found: {e}")
            st.info("💡 Check column names in the Schema Browser tab")
        elif "table" in error_str:
            st.error(f"❌ Table not found: {e}")
            st.info(f"💡 Available tables: {', '.join(sorted(ALLOWED_TABLES))}")
        else:
            st.error(f"❌ Binding error: {e}")
        st.stop()
    except duckdb.SyntaxException as e:
        st.error(f"❌ SQL Syntax Error: {e}")
        st.info("💡 Check for missing commas, unclosed quotes, or invalid keywords")
        st.stop()
    except duckdb.ConnectionException as e:
        st.error(f"❌ Database Connection Error: {e}")
        st.info("💡 Try refreshing the page")
        st.stop()
    except Exception as e:
        st.error(f"❌ Unexpected Error: {e}")
        st.stop()


def show_schema_browser():
    """Display interactive schema browser with enhanced features"""

    # Educational info box about star schema
    with st.expander("📚 Understanding the Star Schema", expanded=False):
        st.markdown("""
        ### What is a Star Schema?

        This database uses a **star schema** design - a simple and efficient structure for analytical queries:

        **🌟 Center (Fact Table)**
        - `fact_landuse_transitions` - Contains the actual land use change data (measurements)
        - Each row represents a specific land use transition with measurable values (acres)

        **⭐ Points (Dimension Tables)**
        Surrounding tables that provide context:
        - `dim_scenario` - Climate and socioeconomic scenarios (RCP/SSP combinations)
        - `dim_geography` - Location information (counties, states, regions)
        - `dim_time` - Time periods (year ranges from 2012-2100)
        - `dim_landuse` - Land use categories (Crop, Forest, Urban, etc.)

        **How to Use It:**
        1. Start with the fact table for measurements
        2. JOIN dimension tables to add context
        3. Filter and aggregate to answer specific questions

        **Example Pattern:**
        ```sql
        SELECT
            g.state_name,
            s.scenario_name,
            SUM(f.acres) as total_acres
        FROM fact_landuse_transitions f
        JOIN dim_geography g ON f.geography_id = g.geography_id
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        GROUP BY g.state_name, s.scenario_name
        ```
        """)

    schema_info = get_table_schema()

    if not schema_info:
        st.warning("No schema information available")
        return

    # Database overview metrics
    col1, col2, col3, col4 = st.columns(4)

    total_tables = len(schema_info)
    total_rows = sum(info['row_count'] for info in schema_info.values())
    fact_tables = sum(1 for name in schema_info.keys() if 'fact' in name)
    dim_tables = sum(1 for name in schema_info.keys() if 'dim' in name)

    with col1:
        st.metric("📊 Total Tables", total_tables)
    with col2:
        st.metric("📈 Total Rows", f"{total_rows:,}")
    with col3:
        st.metric("📦 Fact Tables", fact_tables)
    with col4:
        st.metric("🎯 Dimension Tables", dim_tables)

    st.markdown("---")

    # Search/filter for tables
    search_term = st.text_input("🔍 Search tables:", placeholder="Type to filter tables...")

    # Filter tables based on search
    filtered_tables = {name: info for name, info in schema_info.items()
                      if search_term.lower() in name.lower()} if search_term else schema_info

    if not filtered_tables:
        st.info(f"No tables found matching '{search_term}'")
        return

    st.markdown(f"### 📁 Tables ({len(filtered_tables)} found)")

    # Table selector
    selected_table = st.selectbox(
        "Select a table to explore:",
        list(filtered_tables.keys()),
        help="Choose a table to view its structure and sample data"
    )

    if selected_table and selected_table in filtered_tables:
        table_data = filtered_tables[selected_table]

        # Table summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", f"{table_data['row_count']:,}")
        with col2:
            st.metric("Columns", len(table_data['columns']))
        with col3:
            st.metric("Table Type", "Fact" if "fact_" in selected_table else "Dimension")

        # Quick actions
        st.markdown("#### Quick Actions")
        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            if st.button("🔍 Browse Data", use_container_width=True):
                st.session_state.query_text = f"SELECT * FROM {selected_table} LIMIT 100;"
                st.session_state.active_tab = 0  # Switch to SQL Editor tab
        with action_col2:
            if st.button("📊 Table Stats", use_container_width=True):
                st.session_state.query_text = f"SELECT COUNT(*) as total_rows FROM {selected_table};"
                st.session_state.active_tab = 0
        with action_col3:
            if st.button("🎲 Random Sample", use_container_width=True):
                st.session_state.query_text = f"SELECT * FROM {selected_table} USING SAMPLE 10;"
                st.session_state.active_tab = 0

        # Column information
        st.markdown("#### 📋 Column Details")
        st.dataframe(
            table_data['columns'],
            use_container_width=True,
            hide_index=True
        )

        # Sample data
        st.markdown("#### 🔍 Sample Data (First 5 Rows)")
        if not table_data['sample_data'].empty:
            st.dataframe(
                table_data['sample_data'],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No sample data available")


@st.fragment
def show_query_editor():
    """SQL query editor interface - runs in isolation for better performance"""
    st.markdown("### 📝 SQL Query Editor")

    # Initialize query text in session state
    if 'query_text' not in st.session_state:
        st.session_state.query_text = "SELECT * FROM dim_landuse LIMIT 10;"

    # Query templates with descriptions
    template_descriptions = {
        "": "",
        "Basic SELECT": "View agricultural land use types (simple filtering example)",
        "JOIN tables": "Total acres by scenario and time period (demonstrates table joins)",
        "Aggregation": "Count land use types by category (grouping and counting)",
        "Time series": "Total land transitions over years (temporal analysis)"
    }

    col1, col2 = st.columns([3, 1])
    with col2:
        template = st.selectbox(
            "Quick templates:",
            list(template_descriptions.keys()),
            help="Load a query template to get started"
        )

        # Show description of selected template
        if template and template_descriptions[template]:
            st.caption(f"📝 {template_descriptions[template]}")

        if template == "Basic SELECT":
            st.session_state.query_text = """SELECT *
FROM dim_landuse
WHERE landuse_category = 'Agriculture'
LIMIT 10;"""
        elif template == "JOIN tables":
            st.session_state.query_text = """SELECT
    s.scenario_name,
    t.year_range,
    SUM(f.acres) as total_acres
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_time t ON f.time_id = t.time_id
GROUP BY s.scenario_name, t.year_range
LIMIT 10;"""
        elif template == "Aggregation":
            st.session_state.query_text = """SELECT
    landuse_name,
    COUNT(*) as count,
    landuse_category
FROM dim_landuse
GROUP BY landuse_name, landuse_category
ORDER BY count DESC;"""
        elif template == "Time series":
            st.session_state.query_text = """SELECT
    t.start_year,
    SUM(f.acres) as total_acres
FROM fact_landuse_transitions f
JOIN dim_time t ON f.time_id = t.time_id
WHERE t.start_year BETWEEN 2012 AND 2070
GROUP BY t.start_year
ORDER BY t.start_year;"""

    # Query input
    query = st.text_area(
        "SQL Query:",
        value=st.session_state.query_text,
        height=200,
        help=f"Write SQL queries to explore the data. Results automatically limited to {MAX_DISPLAY_ROWS} rows.",
        placeholder="SELECT * FROM table_name WHERE condition..."
    )

    # Update session state
    st.session_state.query_text = query

    # Query controls
    col1, col2 = st.columns([1, 1])

    with col1:
        run_query = st.button(
            "▶️ Run Query",
            type="primary",
            use_container_width=True,
            disabled=not query.strip()
        )

    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.query_text = ""
            st.rerun()

    # Execute query
    if run_query and query.strip():
        with st.spinner("Executing query..."):
            start_time = time.time()
            df = execute_query(query, ttl=30)  # Short TTL for custom queries
            execution_time = time.time() - start_time

        # Show execution info
        col1, col2, col3 = st.columns([2, 2, 3])
        with col1:
            st.success("✅ Query executed")
        with col2:
            st.info(f"⏱️ {execution_time:.2f}s")
        with col3:
            st.info(f"📊 {len(df):,} rows returned")

        display_query_results(df, query)


def display_query_results(df: pd.DataFrame, query: str):
    """
    Display query results with export options.

    Args:
        df: DataFrame with query results
        query: Original SQL query
    """
    if df.empty:
        st.info("ℹ️ Query returned no results")
        return

    st.markdown("### 📄 Query Results")

    # Display options
    col1, col2 = st.columns([1, 2])

    with col1:
        format_numbers = st.checkbox("Format numbers", value=True)

    with col2:
        # Adjust min_value based on actual data
        min_rows = min(10, len(df)) if len(df) > 0 else 1
        max_rows = st.number_input(
            "Display rows:",
            min_value=min_rows,
            max_value=min(MAX_DISPLAY_ROWS, len(df)),
            value=min(DEFAULT_DISPLAY_ROWS, len(df)),
            step=min(10, len(df))
        )

    # Format display dataframe
    display_df = df.head(max_rows).copy()

    if format_numbers:
        numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
        for col in numeric_cols:
            if col in display_df.columns:
                if display_df[col].dtype == 'int64':
                    display_df[col] = display_df[col].apply(lambda x: f"{x:,}")
                else:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}")

    # Display data (always hide index)
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=min(600, max(100, len(display_df) * 35 + 50))
    )

    if len(df) > max_rows:
        st.caption(f"📄 Showing first {max_rows} of {len(df):,} rows")

    # Export options
    st.markdown("#### 📥 Export Options")
    export_col1, export_col2, export_col3 = st.columns(3)

    with export_col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="CSV",
            data=csv,
            file_name="query_results.csv",
            mime="text/csv",
            use_container_width=True
        )

    with export_col2:
        json_str = df.to_json(orient='records', indent=2)
        st.download_button(
            label="JSON",
            data=json_str,
            file_name="query_results.json",
            mime="application/json",
            use_container_width=True
        )

    with export_col3:
        parquet_buffer = BytesIO()
        df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
        st.download_button(
            label="Parquet",
            data=parquet_buffer.getvalue(),
            file_name="query_results.parquet",
            mime="application/octet-stream",
            use_container_width=True
        )

    # Statistics for numeric columns
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
    if numeric_cols:
        with st.expander("📊 View Statistics"):
            stats_df = df[numeric_cols].describe()
            st.dataframe(stats_df, use_container_width=True)


def show_query_examples():
    """Display example queries organized by category"""
    st.markdown("### 📋 Example Queries")
    st.markdown("Click any example to load it into the SQL editor")

    examples = get_query_examples()

    # Create tabs for each category
    tabs = st.tabs(list(examples.keys()))

    for category, tab in zip(examples.keys(), tabs):
        with tab:
            for name, query in examples[category].items():
                with st.expander(f"🔍 {name}"):
                    st.code(query, language="sql")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("▶️ Run Now", key=f"run_{category}_{name}", type="primary", use_container_width=True):
                            with st.spinner("Executing query..."):
                                df = execute_query(query, ttl=60)
                            display_query_results(df, query)
                    with col2:
                        if st.button("📝 Load in Editor", key=f"load_{category}_{name}", use_container_width=True, help="Copy this query to the SQL Editor tab where you can modify it"):
                            st.session_state.query_text = query
                            st.session_state.active_tab = 0  # Switch to SQL Editor
                            st.rerun()


def show_data_dictionary():
    """Display data dictionary and documentation"""
    st.markdown("### 📚 Data Dictionary")

    # Land use categories
    st.markdown("#### 🌱 Land Use Categories")
    landuse_data = pd.DataFrame({
        "Code": ["cr", "ps", "rg", "fr", "ur"],
        "Name": ["Crop", "Pasture", "Rangeland", "Forest", "Urban"],
        "Category": ["Agriculture", "Agriculture", "Natural", "Natural", "Developed"],
        "Description": [
            "Agricultural cropland for farming",
            "Livestock grazing and pasture land",
            "Natural grasslands and rangeland",
            "Forested areas and woodlands",
            "Developed urban and suburban areas"
        ]
    })
    st.dataframe(landuse_data, use_container_width=True, hide_index=True)

    # Climate scenarios
    st.markdown("#### 🌡️ Climate Scenarios")
    scenario_data = pd.DataFrame({
        "Component": ["RCP", "RCP", "SSP", "SSP", "SSP", "SSP"],
        "Value": ["4.5", "8.5", "1", "2", "3", "5"],
        "Description": [
            "Lower emissions pathway (moderate climate change)",
            "Higher emissions pathway (severe climate change)",
            "Sustainability pathway (strong international cooperation)",
            "Middle of the road (moderate challenges)",
            "Regional rivalry (significant challenges)",
            "Fossil-fueled development (high economic growth)"
        ]
    })
    st.dataframe(scenario_data, use_container_width=True, hide_index=True)

    # Time periods
    st.markdown("#### 📅 Time Periods")
    st.info("""
    The dataset covers projections from 2012 to 2100 in 10-year intervals:
    - **2012-2020**: Calibration period (historical baseline)
    - **2020-2030**: Near-term projections
    - **2030-2040**: Mid-term projections
    - **2040-2070**: Long-term projections
    - **2070-2100**: Extended future projections
    """)

    # Schema relationships
    st.markdown("#### 🏗️ Schema Relationships")
    st.markdown("""
    **Star Schema Structure:**
    - `fact_landuse_transitions` - Central fact table with transition data
    - `dim_scenario` - Climate and socioeconomic scenarios
    - `dim_time` - Time period dimensions
    - `dim_geography` - Geographic locations (counties, states)
    - `dim_landuse` - Land use type definitions

    **Join Pattern Example:**
    ```sql
    FROM fact_landuse_transitions f
    JOIN dim_scenario s ON f.scenario_id = s.scenario_id
    JOIN dim_time t ON f.time_id = t.time_id
    JOIN dim_geography g ON f.geography_id = g.geography_id
    JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
    JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
    ```
    """)


def main():
    """Main data explorer interface"""
    st.title("🔍 RPA Assessment Data Explorer")
    st.markdown("**Interactive database exploration with SQL editor and schema browser**")

    # Initialize session state
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = 0

    # Create main tabs
    tabs = st.tabs([
        "📝 SQL Editor",
        "🗺️ Schema Browser",
        "📋 Example Queries",
        "📚 Data Dictionary"
    ])

    with tabs[0]:
        show_query_editor()

    with tabs[1]:
        show_schema_browser()

    with tabs[2]:
        show_query_examples()

    with tabs[3]:
        show_data_dictionary()

    # Footer
    st.markdown("---")
    st.markdown("""
    **💡 Pro Tips:**
    - Use the **Schema Browser** to explore table structures
    - Copy **Example Queries** as templates for your analysis
    - Query results are automatically limited to 1,000 rows
    """)


if __name__ == "__main__":
    main()