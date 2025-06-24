#!/usr/bin/env python3
"""
Data Explorer for Landuse Database
Advanced tools for exploring database schema, running custom queries, and browsing data
"""

import streamlit as st
import pandas as pd
import duckdb
import sys
from pathlib import Path
import os
import json

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def get_database_connection():
    """Get database connection - not cached as DuckDB connections cannot be pickled"""
    try:
        db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
        if not Path(db_path).exists():
            return None, f"Database not found at {db_path}"
        
        conn = duckdb.connect(str(db_path), read_only=True)
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
        tables_query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY table_name"
        tables = conn.execute(tables_query).fetchall()
        
        schema_info = {}
        
        for table_name, in tables:
            # Get column information
            columns_query = f"DESCRIBE {table_name}"
            columns = conn.execute(columns_query).df()
            
            # Get row count
            count_query = f"SELECT COUNT(*) as row_count FROM {table_name}"
            row_count = conn.execute(count_query).fetchone()[0]
            
            # Get sample data
            sample_query = f"SELECT * FROM {table_name} LIMIT 5"
            sample_data = conn.execute(sample_query).df()
            
            schema_info[table_name] = {
                'columns': columns,
                'row_count': row_count,
                'sample_data': sample_data
            }
        
        conn.close()
        return schema_info, None
    except Exception as e:
        conn.close()
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
        
        result = conn.execute(query)
        df = result.df()
        conn.close()
        return df, None
    except Exception as e:
        conn.close()
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

def show_query_interface():
    """Display custom SQL query interface"""
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
    """Main data explorer interface"""
    st.title("🔍 Data Explorer")
    st.markdown("**Advanced tools for exploring the landuse database**")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "📊 Schema Browser", 
        "🔧 SQL Interface", 
        "📚 Data Dictionary"
    ])
    
    with tab1:
        show_schema_browser()
    
    with tab2:
        show_query_interface()
    
    with tab3:
        show_data_dictionary()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    **🎯 Pro Tips:**
    - Start with the **Schema Browser** to understand table structures
    - Use **example queries** as templates for your own analysis
    - Check the **Data Dictionary** for field definitions and categories
    - Results are automatically limited to 1000 rows for performance
    """)

if __name__ == "__main__":
    main()