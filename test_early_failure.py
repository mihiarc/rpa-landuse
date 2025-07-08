#!/usr/bin/env python3
"""Test for very early failures"""

# Print immediately 
print("STARTUP: test_early_failure.py is starting", flush=True)

# Test basic imports
try:
    import sys
    print(f"STARTUP: Python {sys.version}", flush=True)
except Exception as e:
    print(f"STARTUP ERROR: Cannot import sys: {e}", flush=True)
    exit(1)

# Test if we're in the right place
try:
    import os
    print(f"STARTUP: Working directory: {os.getcwd()}", flush=True)
    print(f"STARTUP: Directory contents: {os.listdir('.')[:10]}", flush=True)
except Exception as e:
    print(f"STARTUP ERROR: OS operations failed: {e}", flush=True)

# Test streamlit import
try:
    print("STARTUP: Attempting to import streamlit...", flush=True)
    import streamlit as st
    print(f"STARTUP: Streamlit {st.__version__} imported successfully", flush=True)
except Exception as e:
    print(f"STARTUP ERROR: Cannot import streamlit: {e}", flush=True)
    import traceback
    traceback.print_exc()
    exit(1)

# Try the most basic streamlit operation
try:
    print("STARTUP: Attempting st.write...", flush=True)
    st.write("Hello from Streamlit!")
    print("STARTUP: st.write completed", flush=True)
except Exception as e:
    print(f"STARTUP ERROR: st.write failed: {e}", flush=True)
    import traceback
    traceback.print_exc()

print("STARTUP: Script completed", flush=True)