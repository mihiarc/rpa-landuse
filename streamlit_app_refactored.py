"""
Refactored RPA Land Use Viewer Streamlit Application

This is the new entry point for the refactored application.
The original streamlit_app.py has been broken down into a modular structure
following software engineering best practices.

To run this application:
    streamlit run streamlit_app_refactored.py
"""

from src.rpa_landuse.app.main import main

if __name__ == "__main__":
    main() 