#!/usr/bin/env python3
"""Test only imports without Streamlit UI"""

print("Starting import test...")

try:
    import sys
    print(f"✓ sys imported, Python {sys.version}")
except Exception as e:
    print(f"✗ sys import failed: {e}")
    exit(1)

try:
    import os
    print(f"✓ os imported, cwd: {os.getcwd()}")
except Exception as e:
    print(f"✗ os import failed: {e}")

try:
    import streamlit
    print(f"✓ streamlit imported, version: {streamlit.__version__}")
except Exception as e:
    print(f"✗ streamlit import failed: {e}")
    exit(1)

# Test other critical imports
test_imports = [
    "pandas",
    "numpy", 
    "duckdb",
    "plotly",
    "pydantic",
    "langchain",
    "geopandas"
]

for module in test_imports:
    try:
        __import__(module)
        print(f"✓ {module} imported")
    except Exception as e:
        print(f"✗ {module} import failed: {e}")

print("\nImport test complete. If streamlit imported successfully, the issue is elsewhere.")

# Now try minimal Streamlit
try:
    import streamlit as st
    st.set_page_config(page_title="Import Test")
    st.write("Streamlit is working after imports!")
except Exception as e:
    print(f"\nStreamlit runtime error: {e}")
    import traceback
    traceback.print_exc()