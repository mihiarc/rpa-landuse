#!/usr/bin/env python3
"""
Natural Language Chat Interface for Landuse Analysis
Modern Streamlit chat interface integrating with the landuse natural language agent
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import third-party libraries after sys.path modification
import streamlit as st  # noqa: E402


def initialize_agent():
    """Initialize the landuse agent with gpt-4o-mini"""
    try:
        from landuse.agents import LanduseAgent
        from landuse.config import LanduseConfig

        # Show loading message
        with st.spinner("🤖 Initializing AI agent with gpt-4o-mini..."):
            # Create config for Streamlit
            config = LanduseConfig.for_agent_type('streamlit', debug=True)
            agent = LanduseAgent(config)
            print("DEBUG: Agent initialized with gpt-4o-mini")

        return agent, None
    except FileNotFoundError as e:
        error_msg = f"Database not found: {e}"
        return None, error_msg
    except Exception as e:
        error_msg = f"Failed to initialize agent: {e}"
        print(f"DEBUG: Agent initialization error: {e}")
        import traceback
        traceback.print_exc()
        return None, error_msg

@st.cache_resource(ttl=300)  # 5 minute TTL to prevent stale agent
def get_agent():
    """Get cached agent instance with TTL"""
    agent, error = initialize_agent()
    if error:
        # Don't cache errors
        st.cache_resource.clear()
        print(f"DEBUG: Clearing cache due to error: {error}")
    return agent, error

def initialize_session_state():
    """Initialize session state for chat"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "agent_initialized" not in st.session_state:
        st.session_state.agent_initialized = False

    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True

    # Always use gpt-4o-mini - no model selection needed

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
    # Get agent instance
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

                    # Debug logging
                    print(f"DEBUG Chat: Query '{prompt}' returned response of length {len(response) if response else 0}")
                    print(f"DEBUG Chat: Response type: {type(response)}")
                    if response:
                        print(f"DEBUG Chat: Response preview: {response[:100]}...")

                    # Ensure response is a string
                    if not isinstance(response, str):
                        if isinstance(response, list):
                            response = ' '.join(str(item) for item in response)
                        else:
                            response = str(response)

                    # Check if response is empty after conversion
                    if not response or response.isspace():
                        response = "I apologize, but I couldn't generate a response. Please try rephrasing your question or check the logs for more details."
                        print(f"DEBUG Chat: Empty response detected for query: {prompt}")

                    # Stream the response for better UX
                    response_container = st.empty()

                    # Display the response directly - simple and clean
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



def main():
    """Main chat interface with single-column layout for cleaner UX"""
    # Add custom CSS for chat layout
    st.markdown("""
    <style>
    /* Chat container styling */
    .chat-container {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    /* Quick action buttons */
    .quick-action {
        background: #e3f2fd;
        border: 1px solid #2196f3;
        border-radius: 8px;
        padding: 0.75rem;
        margin-bottom: 0.5rem;
        cursor: pointer;
        transition: all 0.2s;
    }

    .quick-action:hover {
        background: #bbdefb;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("💬 Natural Language Chat")
    st.markdown("**AI-powered analysis of USDA Forest Service RPA land use data**")

    # Initialize session state
    initialize_session_state()

    # Check agent status
    agent, error = get_agent()

    if error:
        st.error(f"❌ {error}")
        st.info("💡 Please check the Settings page for configuration help.")
        return

    # Show agent status
    status_col1, status_col2, status_col3 = st.columns([2, 1, 1])
    with status_col1:
        st.success("✅ AI Agent Ready - Ask me anything about landuse data!")
    with status_col2:
        if agent:
            st.info(f"🤖 {agent.model_name.split('/')[-1]}")
    with status_col3:
        total_queries = len([m for m in st.session_state.messages if m["role"] == "user"])
        st.metric("Queries", total_queries)

    # Quick actions at the top
    with st.container():
        st.markdown("### 🚀 Quick Actions")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            if st.button("🔄 Clear Chat", use_container_width=True, help="Clear conversation history"):
                st.session_state.messages = []
                st.session_state.show_welcome = True
                st.rerun()

        with col2:
            if st.button("💡 Examples", use_container_width=True, help="Show example queries"):
                st.session_state.show_welcome = True
                st.rerun()

        with col3:
            if st.button("📊 Schema", use_container_width=True, help="View database schema"):
                if agent:
                    schema_info = agent._get_schema_help()
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"📊 **Database Schema:**\n\n{schema_info}"
                    })
                    st.rerun()

        with col4:
            # Export chat button
            chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
            st.download_button(
                "📥 Export",
                data=chat_text,
                file_name="landuse_chat_history.txt",
                mime="text/plain",
                use_container_width=True,
                help="Download chat history"
            )

        with col5:
            # Quick query dropdown
            quick_queries = [
                "Select a quick query...",
                "How much agricultural land is being lost?",
                "Which states have the most urban expansion?",
                "Compare forest loss between RCP45 and RCP85",
                "Show crop to pasture transitions by state",
                "What are the top 5 counties by land change?",
                "Analyze California land transitions"
            ]
            selected_query = st.selectbox(
                "Quick Query",
                quick_queries,
                label_visibility="collapsed",
                help="Select a pre-built query"
            )
            if selected_query != "Select a quick query...":
                st.session_state.messages.append({"role": "user", "content": selected_query})
                st.rerun()

    st.divider()

    # Main chat area
    with st.container():
        # Show welcome message
        show_welcome_message()

        # Display chat history
        display_chat_history()

        # Handle user input
        handle_user_input()

    # Show additional info in sidebar
    with st.sidebar:
        import os

        st.markdown("### 📊 Session Statistics")
        total_queries = len([m for m in st.session_state.messages if m["role"] == "user"])
        successful_queries = len([m for m in st.session_state.messages if m["role"] == "assistant" and not m["content"].startswith("❌")])

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Queries", total_queries)
        with col2:
            success_rate = (successful_queries / total_queries * 100) if total_queries > 0 else 0
            st.metric("Success Rate", f"{success_rate:.0f}%")

        if hasattr(st.session_state, 'last_query_time') and st.session_state.last_query_time:
            st.caption(f"⏱️ Last query: {st.session_state.last_query_time:.1f}s")

        st.divider()

        st.markdown("### ℹ️ System Information")

        # API key status
        has_openai = bool(os.getenv('OPENAI_API_KEY'))
        if has_openai:
            st.success("✅ OpenAI API Key configured")
        else:
            st.error("❌ OpenAI API Key missing")

        # Model info
        st.info("🤖 Model: GPT-4O Mini")

        st.divider()

        # Configuration info
        st.markdown("### ⚙️ Configuration")
        st.caption(f"🔄 Max iterations: {os.getenv('LANDUSE_MAX_ITERATIONS', '5')}")
        st.caption(f"⏱️ Max query time: {os.getenv('LANDUSE_MAX_EXECUTION_TIME', '120')}s")
        st.caption(f"📊 Max rows: {os.getenv('LANDUSE_MAX_QUERY_ROWS', '1000')}")

        st.divider()

        st.markdown("### 💡 Tips")
        st.info("""
        **Query Tips:**
        - Be specific about what you want to analyze
        - Mention states, scenarios, or time periods
        - Ask follow-up questions for details
        - Use "compare" to analyze differences

        **If you hit rate limits:**
        - Wait 10-60 seconds between queries
        - Use simpler, more specific queries
        """)

if __name__ == "__main__":
    main()
