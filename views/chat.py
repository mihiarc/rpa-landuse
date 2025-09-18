#!/usr/bin/env python3
"""
Natural Language Chat Interface for Landuse Analysis
Simplified Streamlit chat interface with the landuse natural language agent
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import streamlit as st  # noqa: E402


@st.cache_resource(ttl=300)  # 5 minute TTL
def get_agent():
    """Get cached agent instance"""
    try:
        from landuse.agents import LanduseAgent
        from landuse.config import LanduseConfig

        config = LanduseConfig.for_agent_type('streamlit', debug=False)
        agent = LanduseAgent(config)
        return agent, None
    except Exception as e:
        return None, str(e)


def initialize_session_state():
    """Initialize session state for chat"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "show_welcome" not in st.session_state:
        st.session_state.show_welcome = True


def show_welcome_message():
    """Show welcome message with example queries"""
    if st.session_state.show_welcome:
        with st.chat_message("assistant"):
            st.markdown("""
            👋 **Welcome! I can help you analyze US land use transitions.**

            **Try these example questions:**
            - "How much agricultural land is being lost?"
            - "Which states have the most urban expansion?"
            - "Compare forest loss between RCP45 and RCP85 scenarios"
            - "Show me agricultural changes in California"

            I'll convert your questions to SQL queries and provide insights from the data.
            """)
        st.session_state.show_welcome = False


def display_chat_history():
    """Display chat message history"""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


@st.fragment
def handle_user_input():
    """Handle user input and generate response"""
    agent, error = get_agent()

    if error:
        st.error(f"❌ {error}")
        return

    if prompt := st.chat_input("Ask about land use transitions..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    # Track query time
                    start_time = time.time()
                    response = agent.query(prompt)
                    query_time = time.time() - start_time

                    # Ensure response is a string
                    if not isinstance(response, str):
                        response = str(response)

                    if not response or response.isspace():
                        response = "I couldn't generate a response. Please try rephrasing your question."

                    st.markdown(response)

                    # Show performance feedback
                    st.caption(f"⏱️ Response time: {query_time:.1f}s")

                    # Add to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response
                    })

                except Exception as e:
                    error_msg = str(e)

                    # Simple error handling
                    if "rate" in error_msg.lower() or "429" in error_msg:
                        st.error("⏸️ **Rate limit reached.** Please wait a moment and try again.")
                    elif "timeout" in error_msg.lower():
                        st.error("⏱️ **Query timeout.** Try a simpler query.")
                    else:
                        st.error(f"❌ Error: {error_msg[:200]}")

                    # Add error to history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"❌ Error: {error_msg[:200]}"
                    })


def main():
    """Main chat interface - simplified"""
    # Minimal CSS for accessibility and mobile
    st.markdown("""
    <style>
    /* Ensure minimum touch target size for mobile */
    .stButton > button { min-height: 44px; }
    /* Better spacing for chat messages */
    .stChatMessage { margin-bottom: 0.5rem; }
    /* Responsive columns on mobile */
    @media (max-width: 768px) {
        .stColumns { flex-direction: column; }
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("💬 RPA Assessment Natural Language Chat")
    st.caption("AI-powered analysis of USDA Forest Service RPA Assessment data")

    # Add RPA scenario context
    with st.expander("📚 Understanding RPA Scenarios", expanded=False):
        st.markdown("""
        The 2020 RPA Assessment uses **four integrated scenarios** combining climate and socioeconomic pathways:

        #### Climate Pathways (RCPs)
        - **RCP 4.5**: Lower emissions (~2.5°C warming by 2100) - assumes climate policies
        - **RCP 8.5**: High emissions (~4.5°C warming by 2100) - limited climate action

        #### Socioeconomic Pathways (SSPs)
        - **SSP1 - Sustainability**: Green growth, international cooperation
        - **SSP2 - Middle of the Road**: Historical trends continue
        - **SSP3 - Regional Rivalry**: Nationalism, resource competition
        - **SSP5 - Fossil-fueled Development**: Rapid growth, high consumption

        #### The Four RPA Scenarios
        | Code | Name | Climate | Society | U.S. Growth |
        |------|------|---------|---------|-------------|
        | **LM** | Lower-Moderate | RCP4.5-SSP1 | Sustainable | GDP: 3.0x, Pop: 1.5x |
        | **HL** | High-Low | RCP8.5-SSP3 | Regional rivalry | GDP: 1.9x, Pop: 1.0x |
        | **HM** | High-Moderate | RCP8.5-SSP2 | Middle road | GDP: 2.8x, Pop: 1.4x |
        | **HH** | High-High | RCP8.5-SSP5 | Fossil-fueled | GDP: 4.7x, Pop: 1.9x |
        """)

    # Initialize session state
    initialize_session_state()

    # Check agent status
    agent, error = get_agent()

    if error:
        st.error(f"❌ Agent initialization failed: {error}")
        st.info("Please check your API key configuration in Settings.")
        return

    # Status bar with export functionality
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.success("✅ Ready - Ask me anything about land use data!")
    with col2:
        # Export functionality restored
        if st.session_state.messages:
            chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
            st.download_button("📥 Export", chat_text, "chat_history.txt", use_container_width=True)
    with col3:
        if st.button("🔄 Clear", use_container_width=True):
            st.session_state.messages = []
            st.session_state.show_welcome = True
            st.rerun()


    # Main chat area
    show_welcome_message()
    display_chat_history()
    handle_user_input()

    # Minimal sidebar
    with st.sidebar:
        if os.getenv('OPENAI_API_KEY'):
            st.success("✅ API Key Set")
        else:
            st.error("❌ API Key Missing")

        st.markdown("### 💡 Tips")
        st.info("""
        - Be specific about what you want
        - Mention states or scenarios
        - Ask follow-up questions
        """)


if __name__ == "__main__":
    main()
