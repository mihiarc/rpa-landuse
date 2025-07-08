#!/usr/bin/env python3
"""Test Streamlit navigation API"""
import streamlit as st

st.set_page_config(page_title="Test Navigation")

# Test if navigation is available
st.write(f"Streamlit version: {st.__version__}")
st.write(f"Has navigation: {hasattr(st, 'navigation')}")
st.write(f"Has Page: {hasattr(st, 'Page')}")

# Try creating a simple page
try:
    home = st.Page(
        lambda: st.write("Home page"),
        title="Home",
        icon=":material/home:"
    )
    
    navigation = st.navigation([home])
    navigation.run()
    
    st.success("Navigation API is working!")
except Exception as e:
    st.error(f"Navigation failed: {type(e).__name__}: {e}")
    import traceback
    st.code(traceback.format_exc())