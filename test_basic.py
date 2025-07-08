#!/usr/bin/env python3
"""Most basic Streamlit test"""

print("Starting test_basic.py")

try:
    import streamlit as st
    print("Streamlit imported successfully")
    
    st.write("# Basic Test")
    st.write("If you see this, Streamlit is working!")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()