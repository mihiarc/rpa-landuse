#!/usr/bin/env python3
"""
RPA Land Use Analytics - Simple Version for Testing
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="RPA Land Use Analytics",
    page_icon="🌲",
    layout="wide"
)

# Add src to path
try:
    project_root = Path(__file__).parent.resolve()
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
except Exception as e:
    st.error(f"Path setup error: {e}")

# Load environment
try:
    if hasattr(st, 'secrets') and len(st.secrets) > 0:
        for key, value in st.secrets.items():
            os.environ[key] = str(value)
        st.success(f"Loaded {len(st.secrets)} secrets")
except Exception as e:
    st.warning(f"Secrets error: {e}")

# Main app
st.title("🌲 RPA Land Use Analytics - Simple Test")

# Test imports
col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("System Info")
    st.write(f"Python: {sys.version.split()[0]}")
    st.write(f"Streamlit: {st.__version__}")
    st.write(f"Working dir: {os.getcwd()}")

with col2:
    st.subheader("Path Info")
    st.write(f"Project root: {project_root}")
    st.write(f"Source path exists: {src_path.exists()}")
    if src_path.exists():
        items = os.listdir(src_path)
        st.write(f"Source contents: {len(items)} items")

with col3:
    st.subheader("Environment")
    api_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    for key in api_keys:
        val = os.getenv(key)
        if val:
            st.write(f"✅ {key} set")
        else:
            st.write(f"❌ {key} missing")

# Test database
st.header("Database Test")
db_path = project_root / "data" / "processed" / "landuse_analytics.duckdb"
if db_path.exists():
    st.success(f"Database found at: {db_path}")
    try:
        import duckdb
        conn = duckdb.connect(str(db_path), read_only=True)
        result = conn.execute("SELECT COUNT(*) as count FROM fact_landuse_transitions").fetchone()
        st.metric("Total Records", f"{result[0]:,}")
        conn.close()
    except Exception as e:
        st.error(f"Database error: {e}")
else:
    st.error(f"Database not found at: {db_path}")

# Test landuse import
st.header("Module Import Test")
try:
    from landuse.config import LanduseConfig
    st.success("✅ Landuse module imported successfully")
except Exception as e:
    st.error(f"❌ Landuse import failed: {e}")
    st.code(f"sys.path: {sys.path[:3]}")

st.info("This is a simplified version without navigation API. If this works, the issue is with st.navigation.")