#!/usr/bin/env python3
"""
Natural Language Chat Interface for Landuse Analysis
Modern Streamlit chat interface integrating with the landuse natural language agent
"""

import os
import sys
import time
from pathlib import Path

import streamlit as st

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def initialize_agent():
    """Initialize the landuse agent with caching"""
    try:
        from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent

        # Show loading message
        with st.spinner("🤖 Initializing AI agent..."):
            agent = LanduseNaturalLanguageAgent()

        return agent, None
    except FileNotFoundError as e:
        error_msg = f"Database not found: {e}"
        return None, error_msg
    except Exception as e:
        error_msg = f"Failed to initialize agent: {e}"
        return None, error_msg

@st.cache_resource
def get_agent():
    """Get cached agent instance"""
    return initialize_agent()

def initialize_session_state():
    """Initialize session state for chat"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent_initialized" not in st.session_state:
        st.session_state.agent_initialized = False

    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True

def show_welcome_message():
    """Show welcome message and example queries"""
    if st.session_state.show_welcome:
        with st.chat_message("assistant"):
            st.markdown("""
            👋 **Welcome to the Landuse Natural Language Interface!**

            I can help you analyze land use transitions across the United States. Ask me questions in plain English and I'll convert them to SQL queries and provide insights.

            **🌟 Try these example questions:**

            🌾 **Agricultural Analysis:**
            - "How much agricultural land is being lost?"
            - "Which scenarios show the most agricultural land loss?"
            - "Show me crop to pasture transitions by state"

            🏙️ **Urban Development:**
            - "Which states have the most urban expansion?"
            - "What land types are being converted to urban use?"

            🌡️ **Climate Scenarios:**
            - "Compare forest loss between RCP45 and RCP85 scenarios"
            - "What are the biggest differences between climate pathways?"

            🗺️ **Geographic Analysis:**
            - "Show me agricultural changes in California"
            - "Which counties have the most land use change?"

            **💡 Smart Defaults:** When you don't specify scenarios or time periods, I'll use intelligent defaults and clearly explain my assumptions.
            """)

        st.session_state.show_welcome = False

def display_chat_history():
    """Display the chat message history"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "thinking" in message:
                # Show thinking process if available
                with st.expander("🧠 Agent Reasoning", expanded=False):
                    st.text(message["thinking"])

            st.markdown(message["content"])

@st.fragment
def handle_user_input():
    """Handle user input and generate response - runs in isolation"""
    # Get agent
    agent, error = get_agent()

    if error:
        st.error(f"❌ {error}")
        st.info("💡 Please check the Settings page for help with configuration.")
        return

    if prompt := st.chat_input("Ask me about landuse transitions..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("🔍 Analyzing your query..."):
                try:
                    # Get response from agent with timing
                    query_start = time.time()
                    response = agent.query(prompt)
                    query_time = time.time() - query_start

                    # Stream the response for better UX
                    response_container = st.empty()
                    words = response.split()
                    displayed_words = []

                    for i, word in enumerate(words):
                        displayed_words.append(word)
                        response_container.markdown(" ".join(displayed_words) + "▊")
                        time.sleep(0.02)  # Small delay for streaming effect

                    # Final response without cursor
                    response_container.markdown(response)

                    # Store query time in session state for sidebar display
                    st.session_state.last_query_time = query_time

                    # Add assistant response to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })

                except Exception as e:
                    error_str = str(e)
                    error_type = type(e).__name__

                    # Detailed error diagnosis
                    if any(indicator in error_str.lower() for indicator in ['rate', '429', 'limit', 'quota']):
                        # Rate limit error
                        st.error("🚨 **Rate Limit Detected**")

                        if "429" in error_str:
                            st.info("This is an HTTP 429 (Too Many Requests) error from the API provider.")

                        st.warning("""
                        **Possible causes:**
                        1. Too many requests in a short time
                        2. Token limit exceeded for the current minute
                        3. Daily quota reached

                        **Solutions:**
                        - Wait 60 seconds before trying again
                        - Reduce query complexity
                        - Check your API tier/limits
                        """)

                        # Add cooldown timer
                        with st.empty():
                            for i in range(10, 0, -1):
                                st.info(f"⏱️ Suggested cooldown: {i} seconds...")
                                time.sleep(1)
                            st.success("✅ You can try again now!")

                        error_message = f"❌ Rate limit error: {error_str[:200]}..."

                    elif "timeout" in error_str.lower():
                        # Timeout error
                        st.error("⏱️ **Query Timeout**")
                        st.info(f"The query took too long to process (>{os.getenv('LANDUSE_MAX_EXECUTION_TIME', '120')}s)")
                        st.warning("Try a simpler query or increase LANDUSE_MAX_EXECUTION_TIME")
                        error_message = "❌ Timeout error: Query exceeded time limit"

                    elif "connection" in error_str.lower() or "network" in error_str.lower():
                        # Network error
                        st.error("🌐 **Network Error**")
                        st.info("Check your internet connection and API endpoint accessibility")
                        error_message = f"❌ Network error: {error_str[:200]}..."

                    else:
                        # Generic error
                        st.error(f"❌ **{error_type}**")
                        st.error(error_str[:500])  # Show first 500 chars

                        # Add debug info in expander
                        with st.expander("🐛 Debug Information"):
                            st.code(f"""
Error Type: {error_type}
Error Message: {error_str}
Model: {agent.model_name}
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}
                            """)

                        error_message = f"❌ Error: {error_str[:200]}..."

                    # Add error to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_message
                    })

@st.fragment
def show_chat_controls():
    """Show chat control buttons - runs in isolation"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("🔄 Clear Chat", help="Clear conversation history"):
            st.session_state.messages = []
            st.session_state.show_welcome = True
            st.rerun()

    with col2:
        if st.button("💡 Show Examples", help="Show example queries"):
            st.session_state.show_welcome = True
            st.rerun()

    with col3:
        if st.button("📊 View Schema", help="Show database schema"):
            if "agent_initialized" in st.session_state:
                agent, _ = get_agent()
                if agent:
                    schema_info = agent._get_schema_help()
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"📊 **Database Schema:**\n\n{schema_info}"
                    })
                    st.rerun()

    with col4:
        message_count = len([m for m in st.session_state.messages if m["role"] == "user"])
        st.metric("Questions Asked", message_count)

@st.fragment
def show_quick_queries():
    """Show quick query buttons - runs in isolation"""
    st.markdown("### 🚀 Quick Queries")

    quick_queries = [
        "How much agricultural land is being lost?",
        "Which states have the most urban expansion?",
        "Compare forest loss between RCP45 and RCP85 scenarios",
        "Show me crop to pasture transitions by state"
    ]

    cols = st.columns(2)
    for i, query in enumerate(quick_queries):
        with cols[i % 2]:
            if st.button(f"🔍 {query}", key=f"quick_{i}", use_container_width=True):
                # Add to chat and process
                st.session_state.messages.append({"role": "user", "content": query})
                st.rerun()

def main():
    """Main chat interface"""
    st.title("💬 Natural Language Chat")
    st.markdown("**Ask questions about landuse transitions in plain English**")

    # Initialize session state
    initialize_session_state()

    # Check agent status
    agent, error = get_agent()

    if error:
        st.error(f"❌ {error}")
        st.info("💡 Please check the Settings page for configuration help.")
        return

    # Show agent status
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success("✅ AI Agent Ready - Ask me anything about landuse data!")
    with col2:
        if agent:
            st.info(f"🤖 Model: {agent.model_name}")

    # Show welcome message
    show_welcome_message()

    # Display chat history
    display_chat_history()

    # Handle user input
    handle_user_input()

    # Show controls in sidebar
    with st.sidebar:
        st.markdown("### 🎛️ Chat Controls")
        show_chat_controls()

        st.markdown("---")

        # Query statistics
        st.markdown("### 📊 Session Stats")
        total_queries = len([m for m in st.session_state.messages if m["role"] == "user"])
        successful_queries = len([m for m in st.session_state.messages if m["role"] == "assistant" and not m["content"].startswith("❌")])

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Queries", total_queries)
        with col2:
            st.metric("Successful", successful_queries)

        # Query performance
        if hasattr(st.session_state, 'last_query_time') and st.session_state.last_query_time:
            st.caption(f"⏱️ Last query: {st.session_state.last_query_time:.1f}s")

        # Model info
        st.caption(f"🤖 Model: {agent.model_name}")
        st.caption(f"⚙️ Max iterations: {os.getenv('LANDUSE_MAX_ITERATIONS', '5')}")

        st.markdown("---")
        show_quick_queries()

        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.info("""
        **Query Tips:**
        - Be specific about what you want to analyze
        - Mention states, scenarios, or time periods for focused results
        - Ask follow-up questions to drill down into details
        - Use "compare" to analyze differences between scenarios

        **If you hit rate limits:**
        - Wait 10-60 seconds between queries
        - Use simpler, more specific queries
        - Check Settings page for configuration options
        """)

if __name__ == "__main__":
    main()
