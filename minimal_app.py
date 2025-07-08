#!/usr/bin/env python3
"""Minimal Streamlit app to test deployment"""
import streamlit as st

st.set_page_config(page_title="RPA Land Use - Minimal Test")

st.title("RPA Land Use Analytics - Minimal Test")
st.write("If you can see this, Streamlit is working!")

# Test basic imports
try:
    import pandas as pd
    st.success("✅ Pandas imported successfully")
except Exception as e:
    st.error(f"❌ Pandas import failed: {e}")

try:
    import duckdb
    st.success("✅ DuckDB imported successfully")
except Exception as e:
    st.error(f"❌ DuckDB import failed: {e}")

try:
    import plotly
    st.success("✅ Plotly imported successfully")
except Exception as e:
    st.error(f"❌ Plotly import failed: {e}")

# Test file access
import os
st.write("### File System Check")
st.write(f"Current directory: {os.getcwd()}")
st.write(f"Directory contents: {os.listdir('.')}")

if os.path.exists("data/processed/landuse_analytics.duckdb"):
    st.success("✅ DuckDB file found")
else:
    st.error("❌ DuckDB file not found")

st.write("### Basic test complete!")