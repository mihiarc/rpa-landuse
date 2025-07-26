#!/usr/bin/env python3
"""
Data Explorer for Landuse Database
Advanced tools for exploring database schema, running custom queries, and browsing data
"""

import json
import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import third-party libraries after sys.path modification
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402
import time  # noqa: E402
from io import BytesIO  # noqa: E402

# Import connection
from landuse.connections import DuckDBConnection  # noqa: E402
from landuse.utilities.state_mappings import StateMapper  # noqa: E402


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
        return conn, None
    except Exception as e:
        return None, f"Database connection error: {e}"

@st.cache_data
def get_table_schema():
    """Get comprehensive table schema information"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        # Get all tables
        tables_df = conn.list_tables(ttl=3600)

        schema_info = {}

        for _, row in tables_df.iterrows():
            table_name = row['table_name']

            # Get column information
            columns = conn.get_table_info(table_name, ttl=3600)

            # Get row count
            row_count = conn.get_row_count(table_name, ttl=300)

            # Get sample data
            sample_query = f"SELECT * FROM {table_name} LIMIT 5"
            sample_data = conn.query(sample_query, ttl=3600)

            schema_info[table_name] = {
                'columns': columns,
                'row_count': row_count,
                'sample_data': sample_data
            }

        return schema_info, None
    except Exception as e:
        return None, f"Error getting schema: {e}"

@st.cache_data
def get_query_examples():
    """Get example queries organized by category"""
    return {
        "Basic Queries": {
            "Count records by table": """
-- Get row counts for all main tables
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
-- View all climate scenarios
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
-- View geography with state information
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
-- Agricultural land being converted to other uses
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
-- Transitions between crop and pasture land
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
-- Compare land use changes between RCP scenarios
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
-- Compare socioeconomic pathways (SSP)
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
-- Land use changes by state
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
-- Counties with most land use change
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
-- How transitions change over time periods
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
-- Compare early vs late periods
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

def execute_custom_query(query):
    """Execute a custom SQL query"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        # Add LIMIT if not present for safety
        query_upper = query.upper().strip()
        if query_upper.startswith('SELECT') and 'LIMIT' not in query_upper:
            query = f"{query.rstrip(';')} LIMIT 1000"

        # Use short TTL for custom queries to see fresh results
        df = conn.query(query, ttl=60)
        return df, None
    except Exception as e:
        return None, f"Query error: {e}"

def show_schema_browser():
    """Display interactive schema browser"""
    st.markdown("### 📊 Database Schema Browser")

    schema_info, error = get_table_schema()
    if error:
        st.error(f"❌ {error}")
        return

    if not schema_info:
        st.warning("No schema information available")
        return

    # Table selector
    table_names = list(schema_info.keys())
    selected_table = st.selectbox(
        "Select a table to explore:",
        table_names,
        help="Choose a table to view its structure and sample data"
    )

    if selected_table and selected_table in schema_info:
        table_data = schema_info[selected_table]

        # Table summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Rows", f"{table_data['row_count']:,}")
        with col2:
            st.metric("Columns", len(table_data['columns']))
        with col3:
            st.metric("Table Type", "Fact" if "fact_" in selected_table else "Dimension")

        # Column information
        st.markdown("#### 📋 Column Details")
        st.dataframe(
            table_data['columns'],
            use_container_width=True,
            hide_index=True
        )

        # Sample data
        st.markdown("#### 🔍 Sample Data")
        if not table_data['sample_data'].empty:
            st.dataframe(
                table_data['sample_data'],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No sample data available")

@st.fragment
def show_query_interface():
    """Display custom SQL query interface - runs in isolation"""
    st.markdown("### 🔧 Custom SQL Query Interface")

    # Query examples
    examples = get_query_examples()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("#### ✏️ SQL Editor")

        # Example query selector
        example_category = st.selectbox(
            "Load example query:",
            ["Custom"] + list(examples.keys()),
            help="Select an example to start with, or choose Custom for your own query"
        )

        if example_category != "Custom":
            example_queries = examples[example_category]
            example_name = st.selectbox(
                "Choose specific example:",
                list(example_queries.keys())
            )
            default_query = example_queries[example_name]
        else:
            default_query = "-- Enter your SQL query here\nSELECT * FROM dim_landuse LIMIT 10;"

        # SQL editor
        query = st.text_area(
            "SQL Query:",
            value=default_query,
            height=300,
            help="Enter your SQL query. LIMIT clauses will be added automatically for safety."
        )

        # Query controls
        col_exec, col_clear = st.columns([1, 1])
        with col_exec:
            execute_button = st.button("🚀 Execute Query", type="primary", use_container_width=True)
        with col_clear:
            if st.button("🗑️ Clear", use_container_width=True):
                st.rerun()

    with col2:
        st.markdown("#### 💡 Query Tips")
        st.info("""
        **Best Practices:**
        - Always include appropriate WHERE clauses
        - Use JOINs to connect related tables
        - Add LIMIT for large result sets
        - Use meaningful column aliases

        **Performance Tips:**
        - Filter early with WHERE clauses
        - Use scenario_id, time_id for filtering
        - Aggregate before joining when possible
        """)

        st.markdown("#### 🏗️ Schema Relationships")
        st.markdown("""
        **Star Schema:**
        - `fact_landuse_transitions` (center)
        - `dim_scenario` (scenarios)
        - `dim_time` (time periods)
        - `dim_geography` (locations)
        - `dim_landuse` (land use types)

        **Join Pattern:**
        ```sql
        FROM fact_landuse_transitions f
        JOIN dim_scenario s ON f.scenario_id = s.scenario_id
        JOIN dim_time t ON f.time_id = t.time_id
        -- etc.
        ```
        """)

    # Execute query
    if execute_button and query.strip():
        with st.spinner("🔍 Executing query..."):
            result_df, error = execute_custom_query(query)

        if error:
            st.error(f"❌ {error}")
        elif result_df is not None:
            st.markdown("#### 📊 Query Results")

            # Results summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows Returned", len(result_df))
            with col2:
                st.metric("Columns", len(result_df.columns))
            with col3:
                if len(result_df) >= 1000:
                    st.warning("⚠️ Results limited to 1000 rows")
                else:
                    st.success("✅ Complete results")

            # Display results
            st.dataframe(result_df, use_container_width=True, hide_index=True)

            # Download option
            if not result_df.empty:
                csv = result_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name="landuse_query_results.csv",
                    mime="text/csv"
                )

def show_interactive_schema_browser():
    """Show interactive schema browser with enhanced features"""
    schema_info, error = get_table_schema()

    if error:
        st.error(f"❌ {error}")
        return

    if schema_info:
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
        
        # Add search/filter for tables
        search_term = st.text_input("🔍 Search tables:", placeholder="Type to filter tables...")
        
        # Filter tables based on search
        filtered_tables = {name: info for name, info in schema_info.items() 
                          if search_term.lower() in name.lower()} if search_term else schema_info
        
        if not filtered_tables:
            st.info(f"No tables found matching '{search_term}'")
            return
        
        st.markdown(f"### 📁 Tables ({len(filtered_tables)} found)")
        
        # Create two columns for table layout
        col_left, col_right = st.columns(2)
        
        # Split tables into two columns
        table_items = list(filtered_tables.items())
        
        for idx, (table_name, info) in enumerate(table_items):
            # Determine which column to use
            target_col = col_left if idx % 2 == 0 else col_right
            
            with target_col:
                # Determine table type icon and color
                if 'fact' in table_name:
                    icon = "📦"  # Fact table
                    card_color = "#e3f2fd"  # Light blue
                    border_color = "#2196f3"
                elif 'dim' in table_name:
                    icon = "🎯"  # Dimension table
                    card_color = "#f3e5f5"  # Light purple
                    border_color = "#9c27b0"
                else:
                    icon = "🗺️"  # Other
                    card_color = "#e8f5e9"  # Light green
                    border_color = "#4caf50"
                
                # Create a container for the table card
                with st.container():
                    # Use columns to create a card-like layout
                    if st.button(
                    f"{icon} **{table_name}**",
                    key=f"table_{table_name}",
                    use_container_width=True,
                    help=f"📊 {info['row_count']:,} rows · {len(info['columns'])} columns"
                    ):
                        st.session_state.selected_table = table_name
                        st.session_state.query_text = f"-- Query for {table_name}\nSELECT * FROM {table_name} LIMIT 10;"
                        st.rerun()
                    
                    # Add visual separation with colored background
                    if 'fact' in table_name:
                        st.markdown(
                            f'<div style="background: #e3f2fd; padding: 0.5rem; margin: -0.5rem 0 1rem 0; border-radius: 0 0 8px 8px;">'
                            f'<small>📦 Fact Table · {info["row_count"]:,} rows · {len(info["columns"])} columns</small></div>',
                            unsafe_allow_html=True
                        )
                    elif 'dim' in table_name:
                        st.markdown(
                            f'<div style="background: #f3e5f5; padding: 0.5rem; margin: -0.5rem 0 1rem 0; border-radius: 0 0 8px 8px;">'
                            f'<small>🎯 Dimension Table · {info["row_count"]:,} rows · {len(info["columns"])} columns</small></div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div style="background: #e8f5e9; padding: 0.5rem; margin: -0.5rem 0 1rem 0; border-radius: 0 0 8px 8px;">'
                            f'<small>🗺️ Table · {info["row_count"]:,} rows · {len(info["columns"])} columns</small></div>',
                            unsafe_allow_html=True
                        )
                
                # Show details if selected
                if 'selected_table' in st.session_state and st.session_state.selected_table == table_name:
                    with st.expander("📋 Table Details", expanded=True):
                        # Show table type
                        table_type = "Fact Table" if 'fact' in table_name else "Dimension Table" if 'dim' in table_name else "Table"
                        st.info(f"**Type:** {table_type}")
                        
                        # Column information in a more compact format
                        st.markdown("**Columns:**")
                        cols_per_row = 2
                        cols = list(info['columns'].iterrows())
                        for i in range(0, len(cols), cols_per_row):
                            col_row = st.columns(cols_per_row)
                            for j, (_, col) in enumerate(cols[i:i+cols_per_row]):
                                if j < len(col_row):
                                    with col_row[j]:
                                        st.caption(f"• `{col['column_name']}` ({col['column_type']})")
                        
                        # Quick actions
                        st.markdown("**Quick Actions:**")
                        action_col1, action_col2, action_col3 = st.columns(3)
                        with action_col1:
                            if st.button("🔍 Browse", key=f"browse_{table_name}", use_container_width=True):
                                st.session_state.query_text = f"SELECT * FROM {table_name} LIMIT 100;"
                                st.rerun()
                        with action_col2:
                            if st.button("📊 Stats", key=f"count_{table_name}", use_container_width=True):
                                st.session_state.query_text = f"SELECT COUNT(*) as total_rows FROM {table_name};"
                                st.rerun()
                        with action_col3:
                            if st.button("🔎 Sample", key=f"sample_{table_name}", use_container_width=True):
                                st.session_state.query_text = f"SELECT * FROM {table_name} USING SAMPLE 10;"
                                st.rerun()

def show_enhanced_query_interface():
    """Show enhanced SQL query interface with live results"""
    st.markdown("### 📝 SQL Query Editor")
    
    # Add helpful note about schema browser
    st.info("💡 **Tip:** Switch to the **Schema Browser** tab to explore tables and generate queries automatically")

    # Initialize query text in session state if not exists
    if 'query_text' not in st.session_state:
        st.session_state.query_text = "-- Welcome to the SQL editor!\n-- Use the Schema Browser tab to explore tables\n-- Or write your own query below\n\nSELECT * FROM dim_landuse LIMIT 10;"

    # Query input with syntax highlighting hint
    query = st.text_area(
        "SQL Query:",
        value=st.session_state.query_text,
        height=200,
        help="Write SQL queries to explore the data. Supports all DuckDB SQL features.",
        placeholder="SELECT * FROM table_name WHERE condition..."
    )

    # Update session state
    st.session_state.query_text = query

    # Query controls in columns
    col1, col2, col3, col4 = st.columns([2, 2, 2, 3])

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
            st.session_state.query_results = None
            st.rerun()
    
    with col3:
        if st.button("📄 Format SQL", use_container_width=True):
            # Simple SQL formatting
            formatted = query.upper().replace('SELECT', 'SELECT\n    ')
            formatted = formatted.replace('FROM', '\nFROM')
            formatted = formatted.replace('WHERE', '\nWHERE')
            formatted = formatted.replace('GROUP BY', '\nGROUP BY')
            formatted = formatted.replace('ORDER BY', '\nORDER BY')
            st.session_state.query_text = formatted
            st.rerun()

    with col4:
        # Quick templates
        template = st.selectbox(
            "Quick templates:",
            ["", "Basic SELECT", "JOIN tables", "Aggregation", "Time series"],
            help="Load a query template"
        )
        
        if template == "Basic SELECT":
            st.session_state.query_text = "SELECT *\nFROM table_name\nWHERE condition\nLIMIT 10;"
            st.rerun()
        elif template == "JOIN tables":
            st.session_state.query_text = "SELECT\n    t1.column1,\n    t2.column2\nFROM table1 t1\nJOIN table2 t2 ON t1.id = t2.id\nLIMIT 10;"
            st.rerun()
        elif template == "Aggregation":
            st.session_state.query_text = "SELECT\n    group_column,\n    COUNT(*) as count,\n    SUM(value) as total\nFROM table_name\nGROUP BY group_column\nORDER BY count DESC;"
            st.rerun()
        elif template == "Time series":
            st.session_state.query_text = "SELECT\n    time_column,\n    SUM(value) as total\nFROM table_name\nWHERE time_column BETWEEN '2012-01-01' AND '2070-12-31'\nGROUP BY time_column\nORDER BY time_column;"
            st.rerun()

    # Run query and show results
    if run_query and query:
        run_custom_query_enhanced(query)
    elif 'query_results' in st.session_state and st.session_state.query_results is not None:
        # Show cached results
        display_query_results(st.session_state.query_results, st.session_state.get('last_query', ''))

def run_custom_query_enhanced(query: str):
    """Run a custom SQL query with enhanced error handling and display"""
    conn, error = get_database_connection()
    if error:
        st.error(f"❌ {error}")
        return

    try:
        with st.spinner("Executing query..."):
            start_time = time.time()
            df = conn.query(query, ttl=0)  # Don't cache custom queries
            execution_time = time.time() - start_time
            
            # Store results in session state
            st.session_state.query_results = df
            st.session_state.last_query = query

        # Show execution info
        col1, col2, col3 = st.columns([2, 2, 3])
        with col1:
            st.success("✅ Query executed")
        with col2:
            st.info(f"⏱️ {execution_time:.2f}s")
        with col3:
            st.info(f"📊 {len(df):,} rows returned")
        
        # Display results
        display_query_results(df, query)

    except Exception as e:
        st.error(f"❌ Query Error: {str(e)}")
        
        # Enhanced error hints
        error_str = str(e).lower()
        if "column" in error_str and "not found" in error_str:
            st.info("💡 **Tip:** Check column names in the Schema Browser")
            # Try to extract column name and suggest alternatives
            import re
            match = re.search(r"column ['\"]?([^'\"\\s]+)['\"]?", str(e), re.IGNORECASE)
            if match:
                bad_column = match.group(1)
                st.warning(f"Column '{bad_column}' not found. Check the schema for correct column names.")
        elif "table" in error_str and "not exist" in error_str:
            st.info("💡 **Tip:** Available tables: fact_landuse_transitions, dim_scenario, dim_geography, dim_landuse, dim_time")
        elif "syntax" in error_str:
            st.info("💡 **Tip:** DuckDB uses standard SQL syntax. Common issues: missing commas, unclosed quotes, invalid keywords.")
        elif "type" in error_str:
            st.info("💡 **Tip:** Check data types. Use CAST() to convert between types if needed.")

def display_query_results(df, query):
    """Display query results with enhanced formatting"""
    if df is not None and not df.empty:
        # Show results header
        st.markdown("### 📄 Query Results")
        
        # Display options
        display_col1, display_col2, display_col3 = st.columns([2, 2, 3])
        
        with display_col1:
            show_index = st.checkbox("Show index", value=False)
        
        with display_col2:
            # Determine numeric columns
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
            format_numbers = st.checkbox("Format numbers", value=True)
        
        with display_col3:
            # Row limit for display
            max_rows = st.number_input(
                "Display rows:",
                min_value=min(1, len(df)),  # At least 1 row if data exists
                max_value=min(1000, len(df)),
                value=min(100, len(df)),
                step=10 if len(df) >= 10 else 1  # Adjust step based on data size
            )
        
        # Format dataframe if requested
        display_df = df.head(max_rows).copy()
        if format_numbers and numeric_cols:
            for col in numeric_cols:
                if display_df[col].dtype == 'int64':
                    display_df[col] = display_df[col].apply(lambda x: f"{x:,}")
                else:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:,.2f}")
        
        # Show data
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=not show_index,
            height=min(400, len(display_df) * 35 + 35)
        )
        
        # If results are truncated, show note
        if len(df) > max_rows:
            st.caption(f"📄 Showing first {max_rows} of {len(df):,} rows")
        
        # Export options
        st.markdown("#### 📥 Export Options")
        export_col1, export_col2, export_col3, export_col4 = st.columns(4)
        
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
            # Parquet export
            parquet_buffer = BytesIO()
            df.to_parquet(parquet_buffer, engine='pyarrow', index=False)
            st.download_button(
                label="Parquet",
                data=parquet_buffer.getvalue(),
                file_name="query_results.parquet",
                mime="application/octet-stream",
                use_container_width=True
            )
        
        with export_col4:
            # Copy query button
            if st.button("📋 Copy Query", use_container_width=True):
                st.code(query, language='sql')
                st.success("Query displayed above for copying")
        
        # Statistics for numeric columns
        if numeric_cols and len(numeric_cols) > 0:
            with st.expander("📊 View Statistics"):
                stats_df = df[numeric_cols].describe()
                st.dataframe(stats_df, use_container_width=True)
    else:
        st.info("ℹ️ Query returned no results")

def show_query_examples_panel():
    """Show query examples in a panel format"""
    st.markdown("### 📋 Example Queries")
    st.markdown("Click any example to load it into the SQL editor")
    
    examples = get_query_examples()
    
    # Create tabs for each category
    tabs = st.tabs(list(examples.keys()))
    
    for i, (category, tab) in enumerate(zip(examples.keys(), tabs)):
        with tab:
            for name, query in examples[category].items():
                # Create an expander for each query
                with st.expander(f"🔍 {name}"):
                    st.code(query, language="sql")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button(f"Load Query", key=f"load_{category}_{name}", use_container_width=True):
                            st.session_state.query_text = query
                            st.rerun()
                    with col2:
                        if st.button(f"Run Now", key=f"run_{category}_{name}", type="primary", use_container_width=True):
                            st.session_state.query_text = query
                            run_custom_query_enhanced(query)

def show_data_dictionary():
    """Display data dictionary and documentation"""
    st.markdown("### 📚 Data Dictionary")

    # Land use categories
    st.markdown("#### 🌱 Land Use Categories")
    landuse_data = {
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
    }
    st.dataframe(pd.DataFrame(landuse_data), use_container_width=True, hide_index=True)

    # Climate scenarios
    st.markdown("#### 🌡️ Climate Scenarios")
    scenario_data = {
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
    }
    st.dataframe(pd.DataFrame(scenario_data), use_container_width=True, hide_index=True)

    # Time periods
    st.markdown("#### 📅 Time Periods")
    st.info("""
    The dataset covers projections from 2012 to 2100 in 10-year intervals:
    - **2012-2020**: Calibration period (historical baseline)
    - **2020-2030**: Near-term projections
    - **2030-2040**: Mid-term projections
    - **2040-2050**: Long-term projections
    - **2050-2060**: Extended projections
    - **2060-2070**: Future projections
    """)

def main():
    """Main data explorer interface with three-panel layout"""
    
    st.title("🔍 Data Explorer")
    st.markdown("**Interactive database exploration with live schema browser and SQL editor**")
    
    # Initialize session state
    if 'selected_table' not in st.session_state:
        st.session_state.selected_table = None
    if 'query_results' not in st.session_state:
        st.session_state.query_results = None
    if 'last_query' not in st.session_state:
        st.session_state.last_query = ""
    
    # Create main tabs for better organization
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 SQL Editor",
        "🗺️ Schema Browser",
        "📋 Example Queries",
        "📚 Data Dictionary"
    ])
    
    with tab1:
        show_enhanced_query_interface()
    
    with tab2:
        st.markdown("### 🗺️ Database Schema Browser")
        st.markdown("Explore the database structure, view table relationships, and preview data.")
        show_interactive_schema_browser()
        
    with tab3:
        show_query_examples_panel()
        
    with tab4:
        show_data_dictionary()

    # Footer
    st.markdown("---")
    st.markdown("""
    **🎯 Pro Tips:**
    - Use the **Schema Browser** tab to explore table structures and relationships
    - Copy **Example Queries** as templates for your own analysis
    - Check the **Data Dictionary** tab for field definitions and categories
    - Query results are automatically limited to 1000 rows for performance
    - Use Ctrl+Enter (or Cmd+Enter on Mac) to run queries quickly
    """)

if __name__ == "__main__":
    main()
