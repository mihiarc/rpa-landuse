"""
Natural Language Query page for the RPA Land Use Viewer application.

Provides AI-powered natural language interface for data exploration.
"""
import streamlit as st
import os
from typing import Dict
import pandas as pd
from pandas.io.formats.style import Styler
from src.rpa_landuse.pandasai.natural_language_query import NaturalLanguageQuery
from ..config.constants import NLQ_EXAMPLES, DB_PATH


def render_natural_language_query_page():
    """Render the natural language query interface."""
    
    # Custom CSS for glassmorphism effect
    st.markdown("""
    <style>
    .glass-container {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.1), rgba(255, 255, 255, 0.05));
        border-radius: 20px;
        padding: 30px;
        margin: 20px 0;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.37);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.18);
    }
    
    .chat-header {
        text-align: center;
        background: linear-gradient(90deg, #ff6b6b, #4ecdc4, #45b7d1, #96ceb4);
        background-size: 400% 400%;
        animation: gradient 15s ease infinite;
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5em;
        font-weight: bold;
        margin-bottom: 20px;
    }
    
    @keyframes gradient {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    
    .info-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin: 15px 0;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    
    .example-question {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px 15px;
        border-radius: 10px;
        margin: 5px 0;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .example-question:hover {
        background: rgba(255, 255, 255, 0.1);
        transform: translateX(5px);
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown('<div class="chat-header">🤖 AI-Powered Data Analysis Assistant</div>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'nlq_messages' not in st.session_state:
        st.session_state.nlq_messages = []
    if 'nlq_instance' not in st.session_state:
        st.session_state.nlq_instance = None
    
    # API key check
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("⚠️ OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        st.info("To use this feature, you need to set up your OpenAI API key:")
        st.code("export OPENAI_API_KEY='your-api-key-here'", language="bash")
        return
    
    # Initialize NLQ
    if st.session_state.nlq_instance is None:
        with st.spinner("🔄 Initializing AI assistant..."):
            try:
                st.session_state.nlq_instance = NaturalLanguageQuery(db_path=DB_PATH)
                st.success("✅ AI assistant ready!")
            except Exception as e:
                st.error(f"Failed to initialize: {str(e)}")
                return
    
    # Info box
    st.markdown("""
    <div class="info-box">
        <h4>💡 How to use this feature</h4>
        <ul>
            <li>Ask questions about land use data in natural language</li>
            <li>The AI will analyze the data and provide insights</li>
            <li>You can request charts, tables, and statistical analyses</li>
            <li>Try the example questions below to get started!</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Example questions
    st.markdown("### 📝 Example Questions")
    example_cols = st.columns(2)
    
    for i, example in enumerate(NLQ_EXAMPLES):
        col = example_cols[i % 2]
        with col:
            if st.button(example, key=f"example_{i}", use_container_width=True):
                st.session_state.nlq_messages.append({"role": "user", "content": example})
    
    # Chat interface
    st.markdown("### 💬 Chat with Your Data")
    
    # Display chat history
    for message in st.session_state.nlq_messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                if isinstance(message["content"], Styler):
                    st.write(message["content"])
                elif isinstance(message["content"], tuple) and message["content"][0] == "chart":
                    st.image(message["content"][1])
                else:
                    st.markdown(message["content"])
            else:
                st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about the land use data..."):
        # Add user message
        st.session_state.nlq_messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analyzing data..."):
                try:
                    response = st.session_state.nlq_instance.ask(prompt)
                    
                    # Handle different response types
                    if isinstance(response, Styler):
                        st.write(response)
                    elif isinstance(response, tuple) and response[0] == "chart":
                        st.image(response[1])
                        st.caption("📊 Generated chart based on your query")
                    elif isinstance(response, pd.DataFrame):
                        st.dataframe(response)
                    else:
                        st.markdown(response)
                    
                    # Add to history
                    st.session_state.nlq_messages.append({"role": "assistant", "content": response})
                    
                except Exception as e:
                    error_msg = f"❌ Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.nlq_messages.append({"role": "assistant", "content": error_msg})
    
    # Sidebar controls
    with st.sidebar:
        st.markdown("### 🎛️ Chat Controls")
        
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.nlq_messages = []
            st.rerun()
        
        st.markdown("### 📊 Data Info")
        if st.session_state.nlq_instance:
            data_info = st.session_state.nlq_instance.get_data_info()
            st.json(data_info)
        
        st.markdown("### 💾 Export Chat")
        if st.session_state.nlq_messages:
            chat_text = "\n\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in st.session_state.nlq_messages 
                if isinstance(msg['content'], str)
            ])
            st.download_button(
                label="Download Chat History",
                data=chat_text,
                file_name="chat_history.txt",
                mime="text/plain"
            )