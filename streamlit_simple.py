#!/usr/bin/env python3
"""Simple Streamlit app without page navigation to test deployment"""
import streamlit as st
import sys
import os
from pathlib import Path

# Add src to path before any landuse imports
project_root = Path(__file__).parent
src_path = project_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

st.set_page_config(
    page_title="RPA Land Use Analytics - Simple",
    page_icon="🌲",
    layout="wide"
)

st.title("🌲 RPA Land Use Analytics")
st.write("Simple version for testing deployment")

# Test imports
col1, col2, col3 = st.columns(3)

with col1:
    try:
        import duckdb
        st.success("✅ DuckDB available")
    except:
        st.error("❌ DuckDB not available")

with col2:
    try:
        from landuse.config import LanduseConfig
        st.success("✅ Landuse module available")
    except Exception as e:
        st.error(f"❌ Landuse module error: {e}")

with col3:
    db_path = "data/processed/landuse_analytics.duckdb"
    if os.path.exists(db_path):
        st.success("✅ Database file exists")
    else:
        st.error("❌ Database file not found")

# Simple functionality test
st.header("Database Connection Test")
try:
    import duckdb
    conn = duckdb.connect(database='data/processed/landuse_analytics.duckdb', read_only=True)
    result = conn.execute("SELECT COUNT(*) as count FROM fact_landuse_transitions").fetchone()
    st.metric("Total Records", f"{result[0]:,}")
    conn.close()
    st.success("Database connection successful!")
except Exception as e:
    st.error(f"Database connection failed: {e}")

st.info("If this simple app works, we can debug the navigation issue separately.")