#!/usr/bin/env python3
"""Ultra-minimal diagnostic app to find the failure point"""

# Test 1: Basic imports
try:
    import sys
    import os
    print(f"Step 1 OK: Basic imports. Python {sys.version}")
except Exception as e:
    print(f"Step 1 FAILED: {e}")
    sys.exit(1)

# Test 2: Streamlit import
try:
    import streamlit as st
    print(f"Step 2 OK: Streamlit {st.__version__} imported")
except Exception as e:
    print(f"Step 2 FAILED: Cannot import streamlit: {e}")
    sys.exit(1)

# Test 3: Page config
try:
    st.set_page_config(page_title="Diagnostic Test")
    print("Step 3 OK: Page config set")
except Exception as e:
    print(f"Step 3 FAILED: Page config error: {e}")

# Test 4: Write something
try:
    st.title("Diagnostic Test")
    st.write("If you see this, basic Streamlit is working!")
    print("Step 4 OK: Basic write operations")
except Exception as e:
    print(f"Step 4 FAILED: Write error: {e}")

# Test 5: Check file system
try:
    st.subheader("File System Check")
    cwd = os.getcwd()
    st.write(f"Working directory: {cwd}")
    
    # List root directory
    st.write("Root directory contents:")
    for item in sorted(os.listdir(".")):
        st.write(f"- {item}")
    
    print("Step 5 OK: File system accessible")
except Exception as e:
    print(f"Step 5 FAILED: File system error: {e}")
    st.error(f"File system error: {e}")

# Test 6: Check for data directory
try:
    if os.path.exists("data"):
        st.write("\nData directory found!")
        st.write("Data directory contents:")
        for item in os.listdir("data"):
            st.write(f"- data/{item}")
    else:
        st.warning("Data directory not found")
    print("Step 6 OK: Data directory check")
except Exception as e:
    print(f"Step 6 FAILED: {e}")

# Test 7: Standard library imports that landuse might need
try:
    st.subheader("Testing Standard Library Imports")
    test_imports = [
        "json",
        "pathlib", 
        "datetime",
        "typing",
        "enum",
        "dataclasses"
    ]
    
    failed = []
    for module in test_imports:
        try:
            __import__(module)
            st.write(f"✅ {module}")
        except Exception as e:
            failed.append(f"{module}: {e}")
            st.write(f"❌ {module}: {e}")
    
    if failed:
        print(f"Step 7 PARTIAL: Some imports failed: {failed}")
    else:
        print("Step 7 OK: All standard imports successful")
except Exception as e:
    print(f"Step 7 FAILED: {e}")

# Test 8: Third-party imports
try:
    st.subheader("Testing Third-Party Imports")
    third_party = [
        ("pandas", "pd"),
        ("numpy", "np"),
        ("duckdb", "duckdb"),
        ("pydantic", "pydantic"),
        ("plotly", "plotly")
    ]
    
    failed = []
    for module, alias in third_party:
        try:
            mod = __import__(module)
            st.write(f"✅ {module}")
        except Exception as e:
            failed.append(f"{module}: {e}")
            st.write(f"❌ {module}: {e}")
    
    if failed:
        print(f"Step 8 PARTIAL: Some third-party imports failed: {failed}")
    else:
        print("Step 8 OK: All third-party imports successful")
except Exception as e:
    print(f"Step 8 FAILED: {e}")

# Test 9: Environment variables
try:
    st.subheader("Environment Check")
    important_vars = ["PATH", "PYTHONPATH", "HOME", "STREAMLIT_RUNTIME_ENV"]
    
    for var in important_vars:
        val = os.getenv(var, "NOT SET")
        if var == "PATH" and val != "NOT SET":
            st.write(f"{var}: [truncated, {len(val)} chars]")
        else:
            st.write(f"{var}: {val}")
    
    print("Step 9 OK: Environment check complete")
except Exception as e:
    print(f"Step 9 FAILED: {e}")

# Final status
st.success("🎉 All basic tests completed! The issue is likely in the app-specific code.")
print("All diagnostic steps completed successfully")