#!/usr/bin/env python3
"""Debug Streamlit app to test basic functionality"""
import streamlit as st
import sys
import os

st.set_page_config(page_title="Debug RPA Land Use")

st.title("Debug Information")

# Check Streamlit version
st.write(f"Streamlit version: {st.__version__}")

# Check Python version
st.write(f"Python version: {sys.version}")

# Check working directory
st.write(f"Working directory: {os.getcwd()}")

# Check if data files exist
st.write("## File System Check")
data_files = [
    "data/processed/landuse_analytics.duckdb",
    "data/chroma_db/chroma.sqlite3",
    ".streamlit/config.toml"
]

for file in data_files:
    exists = os.path.exists(file)
    st.write(f"- {file}: {'✅ Exists' if exists else '❌ Not found'}")

# Check environment variables
st.write("## Environment Variables")
env_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "LANDUSE_MODEL"]
for var in env_vars:
    value = os.getenv(var)
    if value:
        st.write(f"- {var}: ✅ Set ({len(value)} chars)")
    else:
        st.write(f"- {var}: ❌ Not set")

# Test navigation API
st.write("## Navigation API Test")
try:
    st.write(f"Has st.navigation: {hasattr(st, 'navigation')}")
    st.write(f"Has st.Page: {hasattr(st, 'Page')}")
    
    if hasattr(st, 'Page') and hasattr(st, 'navigation'):
        # Create a simple test page
        test_page = st.Page(
            lambda: st.write("Test page content"),
            title="Test",
            icon="🧪"
        )
        nav = st.navigation([test_page])
        st.success("Navigation API is available!")
    else:
        st.error("Navigation API not found!")
except Exception as e:
    st.error(f"Navigation test failed: {e}")

st.write("## Debug Complete")
st.info("If all checks pass, the main app should work after fixing the config.toml issue.")