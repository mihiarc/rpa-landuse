#!/usr/bin/env python3
"""Test all imports to find what's failing"""

import sys
print(f"Python: {sys.version}")

# Test imports one by one
imports_to_test = [
    ("streamlit", "st"),
    ("pandas", "pd"),
    ("numpy", "np"),
    ("duckdb", "duckdb"),
    ("plotly", "plotly"),
    ("matplotlib", "matplotlib"),
    ("geopandas", "gpd"),
    ("langchain", "langchain"),
    ("langchain_openai", "langchain_openai"),
    ("langchain_anthropic", "langchain_anthropic"),
    ("langgraph", "langgraph"),
    ("pydantic", "pydantic"),
    ("rich", "rich"),
]

failed = []
for module, alias in imports_to_test:
    try:
        exec(f"import {module} as {alias}")
        print(f"✓ {module}")
    except Exception as e:
        print(f"✗ {module}: {e}")
        failed.append((module, str(e)))

if failed:
    print(f"\nFAILED IMPORTS: {len(failed)}")
    for module, error in failed:
        print(f"  - {module}: {error}")
else:
    print("\nAll imports successful!")

# Now test Streamlit specifically
try:
    import streamlit as st
    st.set_page_config(page_title="Import Test")
    st.write("If you see this, Streamlit is working!")
except Exception as e:
    print(f"\nStreamlit error: {e}")
    import traceback
    traceback.print_exc()