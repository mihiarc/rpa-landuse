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


def initialize_agent(model_name: str = None):
    """Initialize the landuse agent with specified model"""
    try:
        from landuse.agents import LanduseAgent
        from landuse.config import LanduseConfig

        # Show loading message
        with st.spinner(f"🤖 Initializing AI agent with {model_name or 'default model'}..."):
            # Create config for Streamlit with specified model
            config_kwargs = {'debug': True}
            if model_name:
                config_kwargs['model_name'] = model_name

            config = LanduseConfig.for_agent_type('streamlit', **config_kwargs)
            agent = LanduseAgent(config)
            print(f"DEBUG: Agent initialized with model {agent.model_name}")

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
def get_agent(model_name: str = None):
    """Get cached agent instance with TTL"""
    agent, error = initialize_agent(model_name)
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

    if "selected_model" not in st.session_state:
        # Default to OpenAI
        # st.session_state.selected_model = "gpt-4o-mini"
        st.session_state.selected_model = "bedrock"

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
    # Get agent with selected model
    agent, error = get_agent(st.session_state.selected_model)

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
                        print(f"DEBUG Chat: Response preview: {response}...")

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
                agent, _ = get_agent(st.session_state.selected_model)
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


def main():
    """Main chat interface with two-column layout for wide screens"""
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

    /* Context panel styling */
    .context-panel {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        height: 100%;
    }

    .context-header {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #2c3e50;
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

    # Check agent status with selected model
    agent, error = get_agent(st.session_state.selected_model)

    if error:
        st.error(f"❌ {error}")
        st.info("💡 Please check the Settings page for configuration help.")
        return

    # Create two-column layout for chat interface
    chat_col, context_col = st.columns([3, 2])

    with chat_col:
        # Show agent status
        status_col1, status_col2 = st.columns([3, 1])
        with status_col1:
            st.success("✅ AI Agent Ready - Ask me anything about landuse data!")
        with status_col2:
            if agent:
                st.info(f"🤖 {agent.model_name.split('/')[-1]}")

        # Show welcome message
        show_welcome_message()

        # Display chat history
        display_chat_history()

        # Handle user input
        handle_user_input()

    with context_col:
        # Context panel with query insights and quick actions
        st.markdown('<div class="context-panel">', unsafe_allow_html=True)

        # Model selection at top of context panel
        st.markdown('<div class="context-header">🤖 Model Selection</div>', unsafe_allow_html=True)

        # Model options
        model_options = {
            "gpt-4o-mini": "GPT-4O Mini",
            "gpt-4o": "GPT-4O",
            "gpt-3.5-turbo": "GPT-3.5 Turbo",
            "claude-3-5-sonnet-20241022": "Claude 3.5 Sonnet",
            "claude-3-opus-20240229": "Claude 3 Opus",
            "bedrock": "Nova Lite (Bedrock)",
        }

        # Check which API keys are available
        import os
        has_openai = bool(os.getenv('OPENAI_API_KEY'))
        has_anthropic = bool(os.getenv('ANTHROPIC_API_KEY'))

        # Filter available models
        available_models = {}
        for model_id, model_name in model_options.items():
            if model_id.startswith("gpt") and has_openai:
                available_models[model_id] = f"✅ {model_name}"
            elif model_id.startswith("claude") and has_anthropic:
                available_models[model_id] = f"✅ {model_name}"
            else:
                available_models[model_id] = f"❌ {model_name}"

        # Model selector
        selected_model = st.selectbox(
            "Choose AI Model:",
            options=list(model_options.keys()),
            format_func=lambda x: available_models[x],
            index=list(model_options.keys()).index(st.session_state.selected_model),
            help="Select the AI model to use for chat"
        )

        # Update model if changed
        if selected_model != st.session_state.selected_model:
            st.session_state.selected_model = selected_model
            st.session_state.messages = []  # Clear chat history
            st.session_state.show_welcome = True
            st.cache_resource.clear()  # Clear agent cache
            st.rerun()

        st.markdown("---")

        # Quick actions section
        st.markdown('<div class="context-header">🚀 Quick Actions</div>', unsafe_allow_html=True)

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("🔄 Clear Chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.show_welcome = True
                st.rerun()

            if st.button("📊 View Schema", use_container_width=True):
                if agent:
                    schema_info = agent._get_schema_help()
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"📊 **Database Schema:**\n\n{schema_info}"
                    })
                    st.rerun()

        with action_col2:
            if st.button("💡 Show Examples", use_container_width=True):
                st.session_state.show_welcome = True
                st.rerun()

            if st.button("📥 Export Chat", use_container_width=True):
                # Export chat history
                chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
                st.download_button(
                    label="Download Chat",
                    data=chat_text,
                    file_name="landuse_chat_history.txt",
                    mime="text/plain"
                )

        st.markdown("---")

        # Session statistics
        st.markdown('<div class="context-header">📊 Session Statistics</div>', unsafe_allow_html=True)

        total_queries = len([m for m in st.session_state.messages if m["role"] == "user"])
        successful_queries = len([m for m in st.session_state.messages if m["role"] == "assistant" and not m["content"].startswith("❌")])

        metric_col1, metric_col2 = st.columns(2)
        with metric_col1:
            st.metric("Total Queries", total_queries)
        with metric_col2:
            success_rate = (successful_queries / total_queries * 100) if total_queries > 0 else 0
            st.metric("Success Rate", f"{success_rate:.0f}%")

        if hasattr(st.session_state, 'last_query_time') and st.session_state.last_query_time:
            st.caption(f"⏱️ Last query: {st.session_state.last_query_time:.1f}s")

        st.markdown("---")

        # Quick query suggestions
        st.markdown('<div class="context-header">💡 Try These Queries</div>', unsafe_allow_html=True)

        quick_queries = [
            "How much agricultural land is being lost?",
            "Which states have the most urban expansion?",
            "Compare forest loss between RCP45 and RCP85",
            "Show crop to pasture transitions by state",
            "What are the top 5 counties by land change?",
            "Analyze California land transitions"
        ]

        for query in quick_queries:
            if st.button(f"🔍 {query}", key=f"quick_{query[:20]}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": query})
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    # Show additional controls in sidebar
    with st.sidebar:
        st.markdown("### ℹ️ System Information")

        # API key status
        st.markdown("**API Key Status:**")
        if has_openai:
            st.success("✅ OpenAI API Key configured")
        else:
            st.error("❌ OpenAI API Key missing")

        if has_anthropic:
            st.success("✅ Anthropic API Key configured")
        else:
            st.error("❌ Anthropic API Key missing")

        st.markdown("---")

        # Configuration info
        st.markdown("### ⚙️ Configuration")
        st.caption(f"🤖 Current Model: {st.session_state.selected_model}")
        st.caption(f"🔄 Max iterations: {os.getenv('LANDUSE_MAX_ITERATIONS', '5')}")
        st.caption(f"⏱️ Max query time: {os.getenv('LANDUSE_MAX_EXECUTION_TIME', '120')}s")
        st.caption(f"📊 Max rows: {os.getenv('LANDUSE_MAX_QUERY_ROWS', '1000')}")

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
