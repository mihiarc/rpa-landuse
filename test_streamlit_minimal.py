#!/usr/bin/env python3
"""
Minimal Streamlit app to test rate limit issue
"""

import streamlit as st
import sys
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Load environment
from dotenv import load_dotenv
load_dotenv("config/.env")
load_dotenv()

from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent

st.title("🧪 Rate Limit Test")

# Initialize session state
if "query_count" not in st.session_state:
    st.session_state.query_count = 0
if "agent" not in st.session_state:
    with st.spinner("Initializing agent..."):
        st.session_state.agent = LanduseNaturalLanguageAgent()
    st.success("Agent initialized!")

# Display query count
st.metric("Queries Made", st.session_state.query_count)

# Query input
query = st.text_input("Enter your query:", value="How many scenarios are in the database?")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🚀 Send Query", type="primary"):
        st.session_state.query_count += 1
        
        with st.spinner(f"Processing query #{st.session_state.query_count}..."):
            start_time = time.time()
            try:
                response = st.session_state.agent.query(query)
                elapsed = time.time() - start_time
                
                st.success(f"✅ Query #{st.session_state.query_count} succeeded in {elapsed:.2f}s")
                
                # Show response
                with st.expander("Response", expanded=True):
                    st.markdown(response)
                    
            except Exception as e:
                elapsed = time.time() - start_time
                st.error(f"❌ Query #{st.session_state.query_count} failed after {elapsed:.2f}s")
                st.error(f"Error: {str(e)}")
                
                # Check for rate limit
                if any(x in str(e).lower() for x in ['rate', '429', 'limit', 'quota']):
                    st.warning("🚨 This looks like a rate limit error!")
                    st.info("Try waiting 60 seconds before the next query.")

with col2:
    if st.button("🔄 Reset Count"):
        st.session_state.query_count = 0
        st.rerun()

with col3:
    if st.button("🆕 New Agent"):
        del st.session_state.agent
        st.rerun()

# Debug info
with st.expander("Debug Information"):
    st.write(f"Model: {st.session_state.agent.model_name}")
    st.write(f"Agent type: {type(st.session_state.agent)}")
    st.write(f"Session state keys: {list(st.session_state.keys())}")
    
# Instructions
st.markdown("""
---
### 🧪 Test Instructions:
1. Click "Send Query" to make the first query
2. Immediately click "Send Query" again for the second query
3. If you get a rate limit error, note which query number failed
4. Try "New Agent" to create a fresh agent instance
""")

if __name__ == "__main__":
    # This allows running with: streamlit run test_streamlit_minimal.py
    pass