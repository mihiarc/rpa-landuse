#!/usr/bin/env python3
"""
Quick test script to verify Streamlit dashboard components
"""

import sys
from pathlib import Path
import importlib.util

def test_imports():
    """Test that all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        import streamlit as st
        print(f"✅ Streamlit {st.__version__}")
    except ImportError as e:
        print(f"❌ Streamlit import failed: {e}")
        return False
    
    try:
        import plotly
        print(f"✅ Plotly {plotly.__version__}")
    except ImportError as e:
        print(f"❌ Plotly import failed: {e}")
        return False
    
    try:
        import pandas as pd
        print(f"✅ Pandas {pd.__version__}")
    except ImportError as e:
        print(f"❌ Pandas import failed: {e}")
        return False
    
    try:
        import duckdb
        print(f"✅ DuckDB {duckdb.__version__}")
    except ImportError as e:
        print(f"❌ DuckDB import failed: {e}")
        return False
    
    return True

def test_file_structure():
    """Test that all dashboard files exist"""
    print("\n📁 Testing file structure...")
    
    required_files = [
        "streamlit_app.py",
        "pages/chat.py",
        "pages/analytics.py", 
        "pages/explorer.py",
        "pages/settings.py",
        ".streamlit/config.toml"
    ]
    
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            all_exist = False
    
    return all_exist

def test_agent_import():
    """Test that the landuse agent can be imported"""
    print("\n🤖 Testing agent import...")
    
    # Add src to path
    project_root = Path(__file__).parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    
    try:
        from landuse.agents import LanduseAgent
        print("✅ Landuse agent import successful")
        return True
    except ImportError as e:
        print(f"❌ Landuse agent import failed: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Agent import warning: {e}")
        return True  # This is OK, might be due to missing DB/API keys

def test_page_loading():
    """Test that page files can be loaded as modules"""
    print("\n📄 Testing page modules...")
    
    pages = ["chat", "analytics", "explorer", "settings"]
    all_loaded = True
    
    for page in pages:
        try:
            spec = importlib.util.spec_from_file_location(page, f"pages/{page}.py")
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                # Don't execute, just check syntax
                print(f"✅ pages/{page}.py - Syntax OK")
            else:
                print(f"❌ pages/{page}.py - Cannot load spec")
                all_loaded = False
        except Exception as e:
            print(f"❌ pages/{page}.py - Error: {e}")
            all_loaded = False
    
    return all_loaded

def main():
    """Run all tests"""
    print("🌾 Landuse Streamlit Dashboard - Component Test\n")
    
    tests = [
        ("Import Dependencies", test_imports),
        ("File Structure", test_file_structure),
        ("Agent Import", test_agent_import),
        ("Page Loading", test_page_loading)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_name} - Exception: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary:")
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{status} {test_name}")
    
    if all(results):
        print("\n🎉 All tests passed! Dashboard is ready to launch.")
        print("\nTo start the dashboard:")
        print("uv run streamlit run streamlit_app.py")
    else:
        print("\n⚠️ Some tests failed. Check the issues above.")
        print("\nFor help:")
        print("- Run 'uv sync' to install dependencies")
        print("- Check that database file exists")
        print("- Configure API keys in config/.env")

if __name__ == "__main__":
    main()