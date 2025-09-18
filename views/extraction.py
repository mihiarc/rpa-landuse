#!/usr/bin/env python3
"""
Data Extraction Interface for Landuse Database
Comprehensive tools for extracting, filtering, and exporting land use data
"""

import io
import json
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import third-party libraries after sys.path modification
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

# Import state mappings and connection
from landuse.agents.constants import STATE_NAMES  # noqa: E402
from landuse.config import LanduseConfig  # noqa: E402
from landuse.connections import DuckDBConnection  # noqa: E402


@st.cache_resource
def get_database_connection():
    """Get cached database connection using st.connection"""
    try:
        # Use unified config system
        config = LanduseConfig.for_agent_type('streamlit')

        conn = st.connection(
            name="landuse_db",
            type=DuckDBConnection,
            database=config.db_path,
            read_only=True
        )
        return conn, None
    except Exception as e:
        return None, f"Database connection error: {e}"

@st.cache_data
def get_filter_options():
    """Get available filter options from the database"""
    conn, error = get_database_connection()
    if error:
        return None, error

    try:
        filters = {}

        # Get scenarios
        scenarios_query = """
        SELECT DISTINCT scenario_name, rcp_scenario, ssp_scenario, climate_model
        FROM dim_scenario
        ORDER BY scenario_name
        """
        filters['scenarios'] = conn.query(scenarios_query)

        # Get time periods
        time_query = """
        SELECT DISTINCT year_range, start_year, end_year
        FROM dim_time
        ORDER BY start_year
        """
        filters['time_periods'] = conn.query(time_query)

        # Get states
        states_query = """
        SELECT DISTINCT state_code, state_name
        FROM dim_geography
        WHERE state_name IS NOT NULL
        ORDER BY state_name
        """
        filters['states'] = conn.query(states_query)

        # Get land use types
        landuse_query = """
        SELECT DISTINCT landuse_name, landuse_category
        FROM dim_landuse
        ORDER BY landuse_name
        """
        filters['landuse_types'] = conn.query(landuse_query)

        return filters, None
    except Exception as e:
        return None, f"Error loading filters: {e}"

def build_extraction_query(extract_type, filters):
    """Build SQL query based on extraction type and filters"""

    # Base queries for different extraction types
    base_queries = {
        "transitions": """
            SELECT
                f.transition_id,
                s.scenario_name,
                s.rcp_scenario,
                s.ssp_scenario,
                s.climate_model,
                t.year_range,
                t.start_year,
                t.end_year,
                g.fips_code,
                g.county_name,
                g.state_code,
                g.state_name,
                fl.landuse_name as from_landuse,
                fl.landuse_category as from_category,
                tl.landuse_name as to_landuse,
                tl.landuse_category as to_category,
                f.acres,
                f.transition_type
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        """,

        "summary_by_state": """
            SELECT
                g.state_code,
                g.state_name,
                s.scenario_name,
                t.year_range,
                fl.landuse_name as from_landuse,
                tl.landuse_name as to_landuse,
                SUM(f.acres) as total_acres,
                COUNT(DISTINCT g.fips_code) as counties_affected,
                AVG(f.acres) as avg_acres_per_county
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE f.transition_type = 'change'
        """,

        "summary_by_scenario": """
            SELECT
                s.scenario_name,
                s.rcp_scenario,
                s.ssp_scenario,
                s.climate_model,
                fl.landuse_name as from_landuse,
                tl.landuse_name as to_landuse,
                SUM(f.acres) as total_acres,
                COUNT(DISTINCT g.fips_code) as counties_affected,
                COUNT(DISTINCT g.state_code) as states_affected
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE f.transition_type = 'change'
        """,

        "time_series": """
            SELECT
                t.start_year,
                t.end_year,
                t.year_range,
                s.scenario_name,
                fl.landuse_name as from_landuse,
                tl.landuse_name as to_landuse,
                SUM(f.acres) as total_acres
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE f.transition_type = 'change'
        """
    }

    # Get base query
    query = base_queries.get(extract_type, base_queries["transitions"])

    # Build WHERE clause based on filters
    where_conditions = []
    if extract_type == "transitions":
        where_conditions = []
    elif extract_type in ["summary_by_state", "summary_by_scenario", "time_series"]:
        where_conditions = ["f.transition_type = 'change'"]

    # Add scenario filters
    if filters.get('scenarios'):
        scenario_list = "', '".join(filters['scenarios'])
        where_conditions.append(f"s.scenario_name IN ('{scenario_list}')")

    # Add time period filters
    if filters.get('time_periods'):
        time_list = "', '".join(filters['time_periods'])
        where_conditions.append(f"t.year_range IN ('{time_list}')")

    # Add state filters
    if filters.get('states'):
        state_list = "', '".join(filters['states'])
        where_conditions.append(f"g.state_code IN ('{state_list}')")

    # Add land use filters
    if filters.get('from_landuse'):
        from_list = "', '".join(filters['from_landuse'])
        where_conditions.append(f"fl.landuse_name IN ('{from_list}')")

    if filters.get('to_landuse'):
        to_list = "', '".join(filters['to_landuse'])
        where_conditions.append(f"tl.landuse_name IN ('{to_list}')")

    # Add transition type filter
    if filters.get('transition_type'):
        where_conditions.append(f"f.transition_type = '{filters['transition_type']}'")

    # Combine WHERE conditions
    if where_conditions:
        if "WHERE" in query:
            query += " AND " + " AND ".join(where_conditions)
        else:
            query += " WHERE " + " AND ".join(where_conditions)

    # Add GROUP BY for summary queries
    if extract_type == "summary_by_state":
        query += """
        GROUP BY g.state_code, g.state_name, s.scenario_name,
                 t.year_range, fl.landuse_name, tl.landuse_name
        ORDER BY g.state_name, s.scenario_name, t.year_range
        """
    elif extract_type == "summary_by_scenario":
        query += """
        GROUP BY s.scenario_name, s.rcp_scenario, s.ssp_scenario,
                 s.climate_model, fl.landuse_name, tl.landuse_name
        ORDER BY s.scenario_name, fl.landuse_name, tl.landuse_name
        """
    elif extract_type == "time_series":
        query += """
        GROUP BY t.start_year, t.end_year, t.year_range,
                 s.scenario_name, fl.landuse_name, tl.landuse_name
        ORDER BY t.start_year, s.scenario_name
        """
    else:
        query += " ORDER BY f.transition_id"

    return query

def execute_extraction_query(query, limit=None):
    """Execute extraction query and return results"""
    conn, error = get_database_connection()
    if error:
        return None, error, 0

    try:
        # Get count first
        count_query = f"SELECT COUNT(*) as count FROM ({query}) as subquery"
        count_result = conn.query(count_query, ttl=60)  # Short TTL for counts
        total_rows = count_result['count'].iloc[0]

        # Execute main query with limit if specified
        if limit:
            query += f" LIMIT {limit}"

        df = conn.query(query, ttl=300)  # 5 minute cache for data

        return df, None, total_rows
    except Exception as e:
        return None, f"Query error: {e}", 0

def convert_to_format(df, format_type):
    """Convert DataFrame to specified format"""
    if format_type == "CSV":
        return df.to_csv(index=False)

    elif format_type == "Excel":
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='LandUse_Data', index=False)
        return output.getvalue()

    elif format_type == "JSON":
        return df.to_json(orient='records', indent=2)

    elif format_type == "Parquet":
        output = io.BytesIO()
        df.to_parquet(output, index=False)
        return output.getvalue()

    else:
        return df.to_csv(index=False)

def show_predefined_extracts():
    """Show predefined data extract options"""
    st.markdown("### 📦 Predefined Data Extracts")
    st.markdown("**Quick access to commonly requested data extracts**")

    # Extract templates
    extract_templates = {
        "🌾 Agricultural Transitions": {
            "description": "All transitions involving agricultural land (crop and pasture)",
            "type": "transitions",
            "filters": {
                "from_landuse": ["Crop", "Pasture"],
                "transition_type": "change"
            }
        },
        "🏙️ Urbanization Data": {
            "description": "All transitions to urban land use",
            "type": "transitions",
            "filters": {
                "to_landuse": ["Urban"],
                "transition_type": "change"
            }
        },
        "🌲 Forest Changes": {
            "description": "All transitions involving forests",
            "type": "transitions",
            "filters": {
                "from_landuse": ["Forest"],
                "transition_type": "change"
            }
        },
        "📊 State Summaries": {
            "description": "Aggregated transitions by state",
            "type": "summary_by_state",
            "filters": {}
        },
        "🌡️ Climate Scenario Comparison": {
            "description": "Summary by climate scenario",
            "type": "summary_by_scenario",
            "filters": {}
        },
        "📈 Time Series Data": {
            "description": "Transitions over time periods",
            "type": "time_series",
            "filters": {}
        }
    }

    # Template selector
    selected_template = st.selectbox(
        "Select a predefined extract:",
        list(extract_templates.keys()),
        help="Choose a predefined data extract template",
        key="template_selector"
    )

    if selected_template:
        template = extract_templates[selected_template]
        st.info(f"**Description:** {template['description']}")

        # Format selector
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            export_format = st.selectbox(
                "Export format:",
                ["CSV", "Excel", "JSON", "Parquet"],
                help="Choose the file format for your export",
                key="template_export_format"
            )

        with col2:
            # Preview option
            preview_rows = st.number_input(
                "Preview rows:",
                min_value=10,
                max_value=1000,
                value=100,
                step=10,
                help="Number of rows to preview",
                key="template_preview_rows"
            )

        with col3:
            # Export limit
            export_limit = st.number_input(
                "Export limit:",
                min_value=1000,
                max_value=1000000,
                value=100000,
                step=1000,
                help="Maximum rows to export",
                key="template_export_limit"
            )

        # Action buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.button("👁️ Preview Data", use_container_width=True, key="template_preview_data"):
                with st.spinner("Loading preview..."):
                    query = build_extraction_query(template['type'], template['filters'])
                    df, error, total_rows = execute_extraction_query(query, limit=preview_rows)

                    if error:
                        st.error(f"❌ {error}")
                    elif df is not None:
                        st.success(f"✅ Preview showing {len(df)} of {total_rows:,} total rows")
                        st.dataframe(df, use_container_width=True, hide_index=True)

        with col2:
            if st.button("📥 Export Data", type="primary", use_container_width=True, key="template_export_data"):
                with st.spinner(f"Preparing {export_format} export..."):
                    query = build_extraction_query(template['type'], template['filters'])
                    df, error, total_rows = execute_extraction_query(query, limit=export_limit)

                    if error:
                        st.error(f"❌ {error}")
                    elif df is not None:
                        # Convert to selected format
                        file_data = convert_to_format(df, export_format)

                        # Set appropriate file extension and MIME type
                        file_extensions = {
                            "CSV": "csv",
                            "Excel": "xlsx",
                            "JSON": "json",
                            "Parquet": "parquet"
                        }

                        mime_types = {
                            "CSV": "text/csv",
                            "Excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "JSON": "application/json",
                            "Parquet": "application/octet-stream"
                        }

                        # Generate filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"landuse_{selected_template.lower().replace(' ', '_')}_{timestamp}.{file_extensions[export_format]}"

                        # Download button
                        st.download_button(
                            label=f"💾 Download {export_format} ({len(df):,} rows)",
                            data=file_data,
                            file_name=filename,
                            mime=mime_types[export_format]
                        )

                        if len(df) < total_rows:
                            st.warning(f"⚠️ Exported {len(df):,} of {total_rows:,} total rows (limited by export settings)")

def show_custom_extraction():
    """Show custom data extraction interface"""
    st.markdown("### 🔧 Custom Data Extraction")
    st.markdown("**Build your own custom data extract with filters**")

    # Load filter options
    filters, error = get_filter_options()
    if error:
        st.error(f"❌ {error}")
        return

    # Extraction type selector
    extract_type = st.selectbox(
        "Select extraction type:",
        [
            ("Raw Transitions", "transitions"),
            ("Summary by State", "summary_by_state"),
            ("Summary by Scenario", "summary_by_scenario"),
            ("Time Series", "time_series")
        ],
        format_func=lambda x: x[0],
        help="Choose the type of data extraction",
        key="custom_extract_type"
    )[1]

    # Filter interface
    st.markdown("#### 🎯 Apply Filters")

    # Create filter columns
    col1, col2 = st.columns(2)

    selected_filters = {}

    with col1:
        # Scenario filters
        st.markdown("##### Climate Scenarios")

        # RCP filter
        rcp_options = filters['scenarios']['rcp_scenario'].unique()
        selected_rcp = st.multiselect(
            "RCP Scenarios:",
            rcp_options,
            help="Select RCP scenarios to include"
        )

        # SSP filter
        ssp_options = filters['scenarios']['ssp_scenario'].unique()
        selected_ssp = st.multiselect(
            "SSP Scenarios:",
            ssp_options,
            help="Select SSP scenarios to include"
        )

        # Filter scenarios based on RCP/SSP selection
        if selected_rcp or selected_ssp:
            scenario_mask = True
            if selected_rcp:
                scenario_mask &= filters['scenarios']['rcp_scenario'].isin(selected_rcp)
            if selected_ssp:
                scenario_mask &= filters['scenarios']['ssp_scenario'].isin(selected_ssp)

            filtered_scenarios = filters['scenarios'][scenario_mask]['scenario_name'].tolist()
            selected_filters['scenarios'] = filtered_scenarios

        # Time period filter
        st.markdown("##### Time Periods")
        selected_periods = st.multiselect(
            "Time Periods:",
            filters['time_periods']['year_range'].tolist(),
            help="Select time periods to include"
        )
        if selected_periods:
            selected_filters['time_periods'] = selected_periods

        # Transition type filter (for raw transitions)
        if extract_type == "transitions":
            st.markdown("##### Transition Type")
            transition_type = st.selectbox(
                "Transition Type:",
                ["All", "change", "same"],
                help="Select transition type",
                key="custom_transition_type"
            )
            if transition_type != "All":
                selected_filters['transition_type'] = transition_type

    with col2:
        # Geographic filters
        st.markdown("##### Geographic Filters")

        # State filter
        state_options = filters['states']['state_name'].tolist()
        selected_states = st.multiselect(
            "States:",
            state_options,
            help="Select states to include"
        )
        if selected_states:
            # Convert state names to codes
            state_codes = filters['states'][filters['states']['state_name'].isin(selected_states)]['state_code'].tolist()
            selected_filters['states'] = state_codes

        # Land use filters
        st.markdown("##### Land Use Types")

        landuse_options = filters['landuse_types']['landuse_name'].tolist()

        # From land use
        selected_from = st.multiselect(
            "From Land Use:",
            landuse_options,
            help="Select source land use types"
        )
        if selected_from:
            selected_filters['from_landuse'] = selected_from

        # To land use
        selected_to = st.multiselect(
            "To Land Use:",
            landuse_options,
            help="Select destination land use types"
        )
        if selected_to:
            selected_filters['to_landuse'] = selected_to

    # Export options
    st.markdown("#### 📤 Export Options")

    col1, col2, col3 = st.columns(3)

    with col1:
        export_format = st.selectbox(
            "Export format:",
            ["CSV", "Excel", "JSON", "Parquet"],
            help="Choose the file format for your export",
            key="custom_export_format"
        )

    with col2:
        preview_limit = st.number_input(
            "Preview rows:",
            min_value=10,
            max_value=1000,
            value=100,
            step=10,
            key="custom_preview_rows"
        )

    with col3:
        export_limit = st.number_input(
            "Export limit:",
            min_value=1000,
            max_value=5000000,
            value=500000,
            key="custom_export_limit",
            step=10000,
            help="Maximum rows to export"
        )

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔍 Preview Query", use_container_width=True, key="custom_preview_query"):
            query = build_extraction_query(extract_type, selected_filters)
            st.code(query, language='sql')

    with col2:
        if st.button("👁️ Preview Data", use_container_width=True, key="custom_preview_data"):
            with st.spinner("Loading preview..."):
                query = build_extraction_query(extract_type, selected_filters)
                df, error, total_rows = execute_extraction_query(query, limit=preview_limit)

                if error:
                    st.error(f"❌ {error}")
                elif df is not None:
                    st.success(f"✅ Preview showing {len(df)} of {total_rows:,} total rows")
                    st.dataframe(df, use_container_width=True, hide_index=True)

    with col3:
        if st.button("📥 Export Data", type="primary", use_container_width=True, key="custom_export_data"):
            with st.spinner(f"Preparing {export_format} export..."):
                query = build_extraction_query(extract_type, selected_filters)
                df, error, total_rows = execute_extraction_query(query, limit=export_limit)

                if error:
                    st.error(f"❌ {error}")
                elif df is not None:
                    # Convert to selected format
                    file_data = convert_to_format(df, export_format)

                    # Set appropriate file extension and MIME type
                    file_extensions = {
                        "CSV": "csv",
                        "Excel": "xlsx",
                        "JSON": "json",
                        "Parquet": "parquet"
                    }

                    mime_types = {
                        "CSV": "text/csv",
                        "Excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "JSON": "application/json",
                        "Parquet": "application/octet-stream"
                    }

                    # Generate filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"landuse_custom_extract_{timestamp}.{file_extensions[export_format]}"

                    # Download button
                    st.download_button(
                        label=f"💾 Download {export_format} ({len(df):,} rows)",
                        data=file_data,
                        file_name=filename,
                        mime=mime_types[export_format]
                    )

                    if len(df) < total_rows:
                        st.warning(f"⚠️ Exported {len(df):,} of {total_rows:,} total rows (limited by export settings)")

def show_bulk_export():
    """Show bulk export options"""
    st.markdown("### 📚 Bulk Data Export")
    st.markdown("**Export complete datasets or multiple extracts at once**")

    # Bulk export options
    bulk_options = {
        "Complete Transitions Dataset": {
            "description": "Export the entire fact table with all dimension data joined",
            "queries": {
                "transitions": build_extraction_query("transitions", {})
            }
        },
        "All State Summaries": {
            "description": "Export summaries for all states across all scenarios",
            "queries": {
                "state_summaries": build_extraction_query("summary_by_state", {})
            }
        },
        "Scenario Comparison Package": {
            "description": "Export comparison data for all scenarios",
            "queries": {
                "scenario_summaries": build_extraction_query("summary_by_scenario", {}),
                "rcp_comparison": """
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
                """,
                "ssp_comparison": """
                    SELECT
                        s.ssp_scenario,
                        fl.landuse_name as from_landuse,
                        tl.landuse_name as to_landuse,
                        SUM(f.acres) as total_acres
                    FROM fact_landuse_transitions f
                    JOIN dim_scenario s ON f.scenario_id = s.scenario_id
                    JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
                    JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
                    WHERE f.transition_type = 'change'
                    GROUP BY s.ssp_scenario, fl.landuse_name, tl.landuse_name
                """
            }
        },
        "Reference Data": {
            "description": "Export all dimension tables for reference",
            "queries": {
                "dim_scenario": "SELECT * FROM dim_scenario",
                "dim_time": "SELECT * FROM dim_time",
                "dim_geography": "SELECT * FROM dim_geography",
                "dim_landuse": "SELECT * FROM dim_landuse"
            }
        }
    }

    # Bulk export selector
    selected_bulk = st.selectbox(
        "Select bulk export option:",
        list(bulk_options.keys()),
        help="Choose a bulk export package",
        key="bulk_extract_type"
    )

    if selected_bulk:
        option = bulk_options[selected_bulk]
        st.info(f"**Description:** {option['description']}")

        # Export format
        col1, col2 = st.columns(2)

        with col1:
            export_format = st.selectbox(
                "Export format:",
                ["CSV (ZIP)", "Excel", "Parquet (ZIP)"],
                help="Choose the format for bulk export",
                key="bulk_export_format"
            )

        with col2:
            row_limit = st.number_input(
                "Row limit per dataset:",
                min_value=10000,
                max_value=10000000,
                value=1000000,
                step=100000,
                help="Maximum rows per dataset",
                key="bulk_row_limit"
            )

        # Export button
        if st.button("📦 Generate Bulk Export", type="primary", use_container_width=True, key="bulk_generate_export"):
            with st.spinner("Preparing bulk export..."):
                try:
                    if export_format == "CSV (ZIP)":
                        # Create ZIP file with CSV files
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for dataset_name, query in option['queries'].items():
                                df, error, _ = execute_extraction_query(query, limit=row_limit)
                                if df is not None:
                                    csv_data = df.to_csv(index=False)
                                    zip_file.writestr(f"{dataset_name}.csv", csv_data)
                                    st.success(f"✅ Added {dataset_name} ({len(df):,} rows)")

                        # Download ZIP
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.download_button(
                            label="💾 Download CSV ZIP Archive",
                            data=zip_buffer.getvalue(),
                            file_name=f"landuse_bulk_export_{timestamp}.zip",
                            mime="application/zip"
                        )

                    elif export_format == "Excel":
                        # Create Excel file with multiple sheets
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                            for dataset_name, query in option['queries'].items():
                                df, error, _ = execute_extraction_query(query, limit=row_limit)
                                if df is not None:
                                    # Excel sheet names have a 31 character limit
                                    sheet_name = dataset_name[:31]
                                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                                    st.success(f"✅ Added {dataset_name} ({len(df):,} rows)")

                        # Download Excel
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.download_button(
                            label="💾 Download Excel File",
                            data=excel_buffer.getvalue(),
                            file_name=f"landuse_bulk_export_{timestamp}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    elif export_format == "Parquet (ZIP)":
                        # Create ZIP file with Parquet files
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for dataset_name, query in option['queries'].items():
                                df, error, _ = execute_extraction_query(query, limit=row_limit)
                                if df is not None:
                                    parquet_buffer = io.BytesIO()
                                    df.to_parquet(parquet_buffer, index=False)
                                    zip_file.writestr(f"{dataset_name}.parquet", parquet_buffer.getvalue())
                                    st.success(f"✅ Added {dataset_name} ({len(df):,} rows)")

                        # Download ZIP
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.download_button(
                            label="💾 Download Parquet ZIP Archive",
                            data=zip_buffer.getvalue(),
                            file_name=f"landuse_bulk_export_{timestamp}.zip",
                            mime="application/zip"
                        )

                except Exception as e:
                    st.error(f"❌ Export error: {e}")

def main():
    """Main data extraction interface"""
    st.title("🔄 RPA Assessment Data Extraction")
    st.markdown("**Extract, filter, and export RPA land use transition data**")

    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "📦 Predefined Extracts",
        "🔧 Custom Extraction",
        "📚 Bulk Export"
    ])

    with tab1:
        show_predefined_extracts()

    with tab2:
        show_custom_extraction()

    with tab3:
        show_bulk_export()

    # Information section
    st.markdown("---")
    st.markdown("### ℹ️ Export Information")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📄 Supported Formats")
        st.markdown("""
        - **CSV**: Comma-separated values (universal compatibility)
        - **Excel**: Microsoft Excel format (includes formatting)
        - **JSON**: JavaScript Object Notation (for APIs)
        - **Parquet**: Columnar storage format (efficient for analysis)
        """)

    with col2:
        st.markdown("#### 🔍 Data Dictionary")
        st.markdown("""
        - **transition_type**: 'change' or 'same'
        - **landuse codes**: cr=Crop, ps=Pasture, fr=Forest, ur=Urban, rg=Rangeland
        - **scenarios**: RCP (4.5/8.5) × SSP (1/2/3/5)
        - **time periods**: 10-year intervals from 2012-2100
        """)

    # Tips
    st.info("""
    💡 **Pro Tips:**
    - Use **Predefined Extracts** for common data needs
    - Build **Custom Extractions** for specific analysis requirements
    - Use **Bulk Export** for comprehensive data downloads
    - Consider Parquet format for large datasets (smaller file size, faster loading)
    """)

if __name__ == "__main__":
    main()
