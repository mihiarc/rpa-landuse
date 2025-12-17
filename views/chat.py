#!/usr/bin/env python3
"""
Natural Language Chat Interface for Landuse Analysis
Simplified Streamlit chat interface with the landuse natural language agent
"""

import os
import sys
import time
import uuid
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import streamlit as st  # noqa: E402

from landuse.utilities.security import RateLimiter  # noqa: E402

# Rate limiting configuration: 20 AI queries per minute per session
CHAT_RATE_LIMIT_CALLS = 20
CHAT_RATE_LIMIT_WINDOW = 60  # seconds


@st.cache_resource(ttl=300)  # 5 minute TTL
def get_agent():
    """Get cached agent instance"""
    try:
        from landuse.agents import LanduseAgent
        from landuse.core.app_config import AppConfig

        config = AppConfig()
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
    if "first_visit" not in st.session_state:
        st.session_state.first_visit = True
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "rate_limiter" not in st.session_state:
        st.session_state.rate_limiter = RateLimiter(
            max_calls=CHAT_RATE_LIMIT_CALLS,
            time_window=CHAT_RATE_LIMIT_WINDOW
        )


@st.dialog("🌍 Understanding RPA Scenarios")
def show_scenario_guide():
    """Interactive scenario guide dialog"""
    st.markdown("""
    The 2020 RPA Assessment uses **four integrated scenarios** combining climate and socioeconomic pathways.
    Understanding these helps you ask better questions and interpret results accurately.
    """)

    # Climate pathways section
    st.markdown("#### 🌡️ Climate Pathways (RCPs)")
    col1, col2 = st.columns(2)
    with col1:
        st.info("""
        **RCP 4.5 - Lower Emissions**
        - ~2.5°C warming by 2100
        - Assumes climate policies
        - Moderate impacts
        """)
    with col2:
        st.warning("""
        **RCP 8.5 - High Emissions**
        - ~4.5°C warming by 2100
        - Limited climate action
        - Severe impacts
        """)

    # Socioeconomic pathways section
    st.markdown("#### 🌐 Socioeconomic Pathways (SSPs)")
    st.markdown("""
    - **SSP1 - Sustainability**: Green growth, international cooperation
    - **SSP2 - Middle of the Road**: Historical trends continue
    - **SSP3 - Regional Rivalry**: Nationalism, resource competition
    - **SSP5 - Fossil-fueled Development**: Rapid growth, high consumption
    """)

    # Four scenarios table
    st.markdown("#### 📊 The Four RPA Scenarios")
    st.markdown("""
    | Code | Name | Climate | Society | U.S. Growth |
    |------|------|---------|---------|-------------|
    | **LM** | Lower-Moderate | RCP4.5-SSP1 | Sustainable | GDP: 3.0x, Pop: 1.5x |
    | **HL** | High-Low | RCP8.5-SSP3 | Regional rivalry | GDP: 1.9x, Pop: 1.0x |
    | **HM** | High-Moderate | RCP8.5-SSP2 | Middle road | GDP: 2.8x, Pop: 1.4x |
    | **HH** | High-High | RCP8.5-SSP5 | Fossil-fueled | GDP: 4.7x, Pop: 1.9x |
    """)

    st.success("💡 **Pro Tip**: Mention these scenario codes in your questions for more specific analysis!")

    if st.button("Got it! Let's start analyzing", type="primary", use_container_width=True):
        st.session_state.first_visit = False
        st.rerun()


def show_first_time_onboarding():
    """Show engaging onboarding for first-time users"""
    # Use native Streamlit components instead of unsafe HTML
    with st.container():
        st.info("🌍 **Welcome to RPA Land Use Analytics**\n\n"
                "Understanding climate scenarios helps you ask better questions and interpret results accurately. "
                "Take 2 minutes to learn about RPA scenarios, or dive right in!")

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        if st.button("📚 Quick Scenario Guide (2 min)", type="primary", use_container_width=True):
            show_scenario_guide()
    with col2:
        with st.popover("🎯 Quick Reference", use_container_width=True):
            st.markdown("""
            **Climate Pathways:**
            - RCP4.5 = Lower emissions (2.5°C)
            - RCP8.5 = High emissions (4.5°C)

            **Scenarios:**
            - LM = Sustainable future
            - HL = Regional rivalry
            - HM = Middle road
            - HH = Fossil-fueled growth

            *Click "Quick Scenario Guide" for full details*
            """)
    with col3:
        if st.button("Skip ➡️", use_container_width=True):
            st.session_state.first_visit = False
            st.rerun()


def show_persistent_context_bar():
    """Show always-visible minimal context bar"""
    # Use native Streamlit components instead of unsafe HTML
    st.caption("📍 **Quick Reference:** RCP4.5 = Lower emissions (2.5°C) | RCP8.5 = High emissions (4.5°C) | "
               "4 scenarios: LM (sustainable), HL (rivalry), HM (middle), HH (fossil-fuel)")


def show_smart_example_queries():
    """Show educational example query buttons"""
    st.markdown("##### 💡 Try these scenario-aware queries:")

    examples = [
        {
            "label": "🌡️ Compare Climate Impacts",
            "query": "Compare forest loss between RCP4.5 (lower emissions) and RCP8.5 (high emissions) scenarios",
            "tooltip": "See how different climate pathways affect forest transitions"
        },
        {
            "label": "🏙️ Urban Development Futures",
            "query": "Show urban expansion in SSP1 (sustainable) vs SSP5 (fossil-fuel) scenarios",
            "tooltip": "Compare urbanization under different socioeconomic pathways"
        },
        {
            "label": "🌾 Agricultural Impacts",
            "query": "Which scenario (LM, HL, HM, or HH) shows the most agricultural land loss?",
            "tooltip": "Identify worst-case scenario for agriculture"
        },
        {
            "label": "🌲 Regional Forest Patterns",
            "query": "Show me forest transitions in California across all RPA scenarios",
            "tooltip": "State-specific analysis across all four scenarios"
        }
    ]

    cols = st.columns(2)
    for i, example in enumerate(examples):
        with cols[i % 2]:
            if st.button(
                example["label"],
                key=f"example_{i}",
                help=example["tooltip"],
                use_container_width=True
            ):
                # Add query to messages and trigger processing
                st.session_state.messages.append({"role": "user", "content": example["query"]})
                st.session_state.show_welcome = False
                st.rerun()


def show_welcome_message():
    """Show welcome message with example queries"""
    if st.session_state.show_welcome:
        with st.chat_message("assistant"):
            st.markdown("""
            👋 **Welcome! I can help you analyze US land use transitions across climate scenarios.**

            I'll convert your questions to SQL queries and provide insights from the 2020 RPA Assessment data.
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
        # Check rate limit before processing
        allowed, rate_error = st.session_state.rate_limiter.check_rate_limit(
            st.session_state.session_id
        )
        if not allowed:
            st.warning(f"⏳ {rate_error}")
            return

        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display response
        with st.chat_message("assistant"):
            start_time = time.time()

            try:
                # Use Streamlit's native spinner with processing time estimate
                with st.spinner("🔍 Analyzing your question... (typically 5-15 seconds)"):
                    response = agent.query(prompt)
                query_time = time.time() - start_time

                # Ensure response is a string
                if not isinstance(response, str):
                    response = str(response)

                if not response or response.isspace():
                    response = "I couldn't generate a response. Please try rephrasing your question."

                st.markdown(response)

                # Show performance feedback
                st.caption(f"Response time: {query_time:.1f}s")

                # Add to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response
                })

            except Exception as e:
                error_msg = str(e)

                # Simple error handling
                if "rate" in error_msg.lower() or "429" in error_msg:
                    st.error("**Rate limit reached.** Please wait a moment and try again.")
                elif "timeout" in error_msg.lower():
                    st.error("**Query timeout.** Try a simpler query.")
                else:
                    st.error(f"Error: {error_msg[:200]}")

                # Add error to history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {error_msg[:200]}"
                })


def main():
    """Main chat interface - simplified"""
    # CSS for accessibility and mobile responsiveness
    st.markdown("""
    <style>
    /* Ensure minimum touch target size for mobile */
    .stButton > button { min-height: 44px; }
    /* Better spacing for chat messages */
    .stChatMessage { margin-bottom: 0.5rem; }
    /* Responsive status bar - stack on mobile */
    @media (max-width: 768px) {
        /* Force status bar columns to wrap into 2x2 grid on mobile */
        div[data-testid="column"] {
            min-width: 45% !important;
            flex: 1 1 45% !important;
        }
    }
    @media (max-width: 480px) {
        /* Full width on very small screens */
        div[data-testid="column"] {
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("💬 RPA Assessment Natural Language Chat")
    st.caption("AI-powered analysis of USDA Forest Service RPA Assessment data")

    # Initialize session state
    initialize_session_state()

    # Show first-time user onboarding (Progressive Disclosure)
    if st.session_state.first_visit:
        show_first_time_onboarding()

    # Show persistent context bar (always visible for all users)
    show_persistent_context_bar()

    # Check agent status
    agent, error = get_agent()

    if error:
        st.error(f"❌ Agent initialization failed: {error}")
        st.info("Please check your API key configuration in Settings.")
        return

    # Status bar with export functionality
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col1:
        st.success("✅ Ready - Ask me anything about land use data!")
    with col2:
        # Scenario guide button (always accessible)
        if st.button("📚 Scenarios", use_container_width=True, help="Learn about RPA scenarios"):
            show_scenario_guide()
    with col3:
        # Export functionality
        if st.session_state.messages:
            chat_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages])
            st.download_button("📥 Export", chat_text, "chat_history.txt", use_container_width=True)
    with col4:
        if st.button("🔄 Clear", use_container_width=True):
            st.session_state.messages = []
            st.session_state.show_welcome = True
            # Note: Do NOT reset first_visit - users should not see onboarding again after clearing chat
            st.rerun()

    # Show smart example queries (educational prompts)
    if not st.session_state.messages or len(st.session_state.messages) == 0:
        show_smart_example_queries()

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
