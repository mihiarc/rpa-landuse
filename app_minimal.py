#!/usr/bin/env python3
"""Minimal app to test basic functionality"""

import streamlit as st
import os
import sys
from pathlib import Path

# Page config must be first
st.set_page_config(page_title="RPA Land Use - Minimal", page_icon="🌲")

# Add src to path
try:
    project_root = Path(__file__).parent.resolve()
    src_path = project_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    st.success(f"Path setup successful. Project root: {project_root}")
except Exception as e:
    st.error(f"Path setup failed: {e}")

st.title("🌲 RPA Land Use Analytics - Minimal Test")

# Test basic functionality
tab1, tab2, tab3 = st.tabs(["System Info", "Database Test", "Import Test"])

with tab1:
    st.header("System Information")
    st.write(f"**Python version:** {sys.version}")
    st.write(f"**Streamlit version:** {st.__version__}")
    st.write(f"**Working directory:** {os.getcwd()}")
    st.write(f"**__file__:** {__file__ if '__file__' in globals() else 'Not defined'}")
    
    # Check for important files
    st.subheader("File System Check")
    important_files = [
        "data/processed/landuse_analytics.duckdb",
        "data/chroma_db/chroma.sqlite3",
        "requirements.txt",
        "src/landuse/__init__.py"
    ]
    
    for file in important_files:
        path = project_root / file
        if path.exists():
            st.success(f"✅ {file} exists")
        else:
            st.error(f"❌ {file} not found")

with tab2:
    st.header("Database Connection Test")
    db_path = project_root / "data" / "processed" / "landuse_analytics.duckdb"
    
    if db_path.exists():
        try:
            import duckdb
            conn = duckdb.connect(str(db_path), read_only=True)
            
            # Test query
            result = conn.execute("SELECT COUNT(*) as count FROM fact_landuse_transitions").fetchone()
            st.success(f"✅ Database connected successfully!")
            st.metric("Total Records", f"{result[0]:,}")
            
            # Show tables
            tables = conn.execute("SHOW TABLES").fetchall()
            st.write("**Available tables:**")
            for table in tables:
                st.write(f"- {table[0]}")
            
            conn.close()
        except Exception as e:
            st.error(f"Database error: {e}")
            import traceback
            st.code(traceback.format_exc())
    else:
        st.error(f"Database not found at: {db_path}")

with tab3:
    st.header("Module Import Test")
    
    # Test critical imports
    imports = [
        ("pandas", "Basic data processing"),
        ("numpy", "Numerical operations"),
        ("plotly", "Visualizations"),
        ("langchain", "LLM framework"),
        ("pydantic", "Data validation"),
        ("rich", "Terminal UI"),
        ("geopandas", "Geographic data"),
    ]
    
    col1, col2 = st.columns(2)
    
    for i, (module, desc) in enumerate(imports):
        col = col1 if i % 2 == 0 else col2
        with col:
            try:
                __import__(module)
                st.success(f"✅ {module}")
                st.caption(desc)
            except Exception as e:
                st.error(f"❌ {module}")
                st.caption(str(e))
    
    # Test landuse module
    st.subheader("Landuse Module Test")
    try:
        from landuse.config import LanduseConfig
        st.success("✅ landuse.config imported successfully")
        
        # Try to create config
        config = LanduseConfig()
        st.write(f"Model: {config.model}")
        st.write(f"Temperature: {config.temperature}")
    except Exception as e:
        st.error(f"❌ landuse module import failed: {e}")
        import traceback
        st.code(traceback.format_exc())

# Environment variables
st.header("Environment Check")
env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "STREAMLIT_RUNTIME_ENV"]
for var in env_vars:
    value = os.getenv(var)
    if value:
        if "KEY" in var:
            st.write(f"**{var}:** {'*' * 10} ({len(value)} chars)")
        else:
            st.write(f"**{var}:** {value}")
    else:
        st.write(f"**{var}:** Not set")

st.info("This minimal app tests basic functionality without the navigation API.")