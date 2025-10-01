#!/usr/bin/env python3
"""
Settings and Help Page for Landuse Dashboard
Configuration, system status, and help information
"""

import html
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import third-party libraries after sys.path modification
import streamlit as st  # noqa: E402


def check_system_status():
    """Check overall system status"""
    status = {
        "database": {"status": False, "message": "", "path": ""},
        "api_keys": {"status": False, "message": "", "details": {}},
        "dependencies": {"status": False, "message": "", "details": {}},
        "agent": {"status": False, "message": ""}
    }

    # Check database
    db_path = Path(os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'))
    if db_path.exists():
        status["database"]["status"] = True
        status["database"]["message"] = "Database found and accessible"
        status["database"]["path"] = str(db_path)

        # Check database size
        size_mb = db_path.stat().st_size / (1024 * 1024)
        status["database"]["size"] = f"{size_mb:.1f} MB"
    else:
        status["database"]["message"] = f"Database not found at {db_path}"

    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")

    if openai_key:
        status["api_keys"]["details"]["openai"] = {
            "configured": True,
            "preview": f"{openai_key[:8]}...{openai_key[-4:]}" if len(openai_key) > 12 else "****"
        }
        status["api_keys"]["status"] = True
        status["api_keys"]["message"] = "OpenAI API key configured"
    else:
        status["api_keys"]["details"]["openai"] = {"configured": False}
        status["api_keys"]["message"] = "OpenAI API key not found"

    # Check dependencies
    try:
        import duckdb
        import langchain
        import pandas
        import plotly
        import rich

        status["dependencies"]["status"] = True
        status["dependencies"]["message"] = "All required packages installed"
        status["dependencies"]["details"] = {
            "langchain": langchain.__version__,
            "duckdb": duckdb.__version__,
            "pandas": pandas.__version__,
            "plotly": plotly.__version__,
        }
    except ImportError as e:
        status["dependencies"]["message"] = f"Missing packages: {e}"

    # Check agent initialization
    if status["database"]["status"] and status["api_keys"]["status"]:
        try:
            from landuse.agents import LanduseAgent
            # Don't actually initialize to avoid overhead, just check imports
            status["agent"]["status"] = True
            status["agent"]["message"] = "Agent can be initialized"
        except Exception as e:
            status["agent"]["message"] = f"Agent initialization error: {e}"
    else:
        status["agent"]["message"] = "Database or API keys not configured"

    return status

def show_system_status():
    """Display system status dashboard"""
    st.markdown("### 🔧 System Status")

    status = check_system_status()

    # Overall status
    all_good = all([
        status["database"]["status"],
        status["api_keys"]["status"],
        status["dependencies"]["status"],
        status["agent"]["status"]
    ])

    if all_good:
        st.success("✅ **System Ready** - All components are properly configured!")
    else:
        st.warning("⚠️ **Configuration Needed** - Some components require setup.")

    # Detailed status
    col1, col2 = st.columns(2)

    with col1:
        # Database status
        st.markdown("#### 🗄️ Database")
        if status["database"]["status"]:
            st.success(f"✅ {status['database']['message']}")
            st.info(f"📍 **Location:** `{status['database']['path']}`")
            if "size" in status["database"]:
                st.info(f"💾 **Size:** {status['database']['size']}")
        else:
            st.error(f"❌ {status['database']['message']}")
            with st.expander("💡 How to fix"):
                st.markdown("""
                **To set up the database:**
                1. Download the raw data from the RPA Assessment
                2. Run the data conversion script:
                   ```bash
                   uv run python scripts/converters/convert_to_duckdb.py
                   ```
                3. Or set `LANDUSE_DB_PATH` environment variable to your database location
                """)

        # Dependencies status
        st.markdown("#### 📦 Dependencies")
        if status["dependencies"]["status"]:
            st.success(f"✅ {status['dependencies']['message']}")
            with st.expander("📋 Package versions"):
                for pkg, version in status["dependencies"]["details"].items():
                    st.text(f"{pkg}: {version}")
        else:
            st.error(f"❌ {status['dependencies']['message']}")
            with st.expander("💡 How to fix"):
                st.markdown("""
                **To install dependencies:**
                ```bash
                uv sync
                ```
                """)

    with col2:
        # API Keys status
        st.markdown("#### 🔑 API Keys")
        if status["api_keys"]["status"]:
            st.success(f"✅ {status['api_keys']['message']}")

            for provider, details in status["api_keys"]["details"].items():
                if details["configured"]:
                    st.info(f"🔐 **{provider.title()}:** {details['preview']}")
                else:
                    st.warning(f"⚠️ **{provider.title()}:** Not configured")
        else:
            st.error(f"❌ {status['api_keys']['message']}")
            with st.expander("💡 How to configure"):
                st.markdown("""
                **To configure API keys:**
                1. Create `config/.env` file
                2. Add your API keys:
                   ```
                   OPENAI_API_KEY=your_openai_key_here
                   ```
                3. Restart the application
                """)

        # Agent status
        st.markdown("#### 🤖 AI Agent")
        if status["agent"]["status"]:
            st.success(f"✅ {status['agent']['message']}")

            # Show model configuration
            model_name = os.getenv('LANDUSE_MODEL', 'gpt-4o-mini')
            st.info(f"🧠 **Model:** {model_name}")
        else:
            st.error(f"❌ {status['agent']['message']}")

def show_configuration():
    """Display configuration options"""
    st.markdown("### ⚙️ Configuration")

    # Environment variables
    st.markdown("#### 🌍 Environment Variables")

    env_vars = {
        "LANDUSE_DB_PATH": {
            "current": os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'),
            "description": "Path to the DuckDB database file"
        },
        "LANDUSE_MODEL": {
            "current": os.getenv('LANDUSE_MODEL', 'gpt-4o-mini'),
            "description": "AI model to use (gpt-4o-mini, gpt-4o, gpt-3.5-turbo)"
        },
        "TEMPERATURE": {
            "current": os.getenv('TEMPERATURE', '0.1'),
            "description": "Model temperature (0.0-1.0, lower = more deterministic)"
        },
        "MAX_TOKENS": {
            "current": os.getenv('MAX_TOKENS', '4000'),
            "description": "Maximum tokens for model responses"
        },
        "LANDUSE_MAX_ITERATIONS": {
            "current": os.getenv('LANDUSE_MAX_ITERATIONS', '5'),
            "description": "Maximum agent iterations per query"
        },
        "LANDUSE_MAX_EXECUTION_TIME": {
            "current": os.getenv('LANDUSE_MAX_EXECUTION_TIME', '120'),
            "description": "Maximum query execution time (seconds)"
        }
    }

    for var_name, var_info in env_vars.items():
        col1, col2 = st.columns([1, 2])
        with col1:
            st.code(var_name)
        with col2:
            st.text(f"Current: {var_info['current']}")
            st.caption(var_info['description'])

    # Configuration file example
    st.markdown("#### 📝 Configuration File Example")
    with st.expander("Example config/.env file"):
        st.code("""
# API Keys (required)
OPENAI_API_KEY=your_openai_api_key_here

# Model Configuration
LANDUSE_MODEL=gpt-4o-mini
TEMPERATURE=0.1
MAX_TOKENS=4000

# Database Path
LANDUSE_DB_PATH=data/processed/landuse_analytics.duckdb

# Query Limits
LANDUSE_MAX_ITERATIONS=5
LANDUSE_MAX_EXECUTION_TIME=120
LANDUSE_MAX_QUERY_ROWS=1000
LANDUSE_DEFAULT_DISPLAY_LIMIT=50

# Rate Limiting
LANDUSE_RATE_LIMIT_CALLS=60
LANDUSE_RATE_LIMIT_WINDOW=60
""", language="bash")

def show_help_documentation():
    """Display help and documentation"""

    # Quick start
    st.markdown("## 🚀 Quick Start Guide")
    with st.expander("Getting Started", expanded=True):
        st.markdown("""
        **Welcome to the RPA Land Use Analytics Platform!**

        This platform provides AI-powered analytics for USDA Forest Service RPA Assessment land use data.

        **1. Start with Natural Language Chat**
        - Navigate to the "💬 Natural Language Chat" page
        - Ask questions in plain English like: "How much agricultural land is being lost?"
        - The AI will interpret your question and provide data-driven insights

        **2. Explore Pre-built Analytics**
        - Visit the "📊 Analytics Dashboard" for interactive visualizations
        - View trends across different climate scenarios and time periods
        - Compare land use transitions between states and regions

        **3. Extract Custom Data**
        - Use the "🔄 Data Extraction" page to export specific datasets
        - Choose from predefined extracts or create custom filters
        - Export data in CSV, Excel, or Parquet formats

        **4. Advanced SQL Analysis**
        - For technical users: Use the "🔍 Data Explorer" for custom SQL queries
        - Browse the database schema and run complex queries
        - Export query results for further analysis
        """)

    # Feature overview
    st.markdown("## ✨ Feature Overview")

    features = {
        "💬 Natural Language Chat": {
            "description": "Ask questions in plain English about land use data",
            "details": "Our AI assistant understands natural language queries and converts them to data analysis. Perfect for quick insights without needing SQL knowledge."
        },
        "📊 Analytics Dashboard": {
            "description": "Interactive visualizations and pre-built insights",
            "details": "Explore 6 different visualization types including agricultural impact analysis, forest transitions, climate comparisons, and geographic patterns."
        },
        "🔄 Data Extraction": {
            "description": "Export land use data in multiple formats",
            "details": "Access predefined extracts, create custom filters, or bulk export entire datasets. Supports CSV, Excel, and Parquet formats."
        },
        "🔍 Data Explorer": {
            "description": "Advanced SQL queries for technical users",
            "details": "Direct database access with schema browser, example queries, and export capabilities for custom analysis."
        }
    }

    for feature, info in features.items():
        with st.expander(f"{feature}"):
            st.markdown(f"**{info['description']}**")
            st.markdown(info['details'])
            st.markdown("")

    # Example queries
    st.markdown("## 💡 Example Queries")
    with st.expander("Natural Language Examples", expanded=False):
        st.markdown("""
        **Agricultural Analysis:**
        - "How much agricultural land is being lost?"
        - "Which scenarios show the most crop land conversion?"
        - "Show me crop to pasture transitions by state"

        **Climate Analysis:**
        - "Compare forest loss between RCP45 and RCP85 scenarios"
        - "What are the differences between climate pathways?"

        **Geographic Analysis:**
        - "Which states have the most urban expansion?"
        - "Show me land use changes in California"
        - "What counties have the most development?"

        **Time Series:**
        - "How do land use patterns change over time?"
        - "Show trends from 2020 to 2100"
        """)

    # Data information
    st.markdown("## 📊 About the Data")
    with st.expander("Dataset Information", expanded=False):
        st.markdown("""
        **Source:** USDA Forest Service RPA 2020 Assessment

        **Coverage:**
        - 3,075+ US counties (conterminous United States)
        - 20 climate scenarios (RCP4.5/8.5 × SSP1/2/3/5 × 5 climate models)
        - 6 time periods (2012-2100)
        - 5 land use categories (Crop, Pasture, Rangeland, Forest, Urban)

        **Data Size:**
        - 5.4M+ land use transition records
        - 1.2GB DuckDB database
        - Star schema optimized for analytics

        **Citation:**
        Mihiar, A.J.; Lewis, D.J.; Coulston, J.W. 2023. Land use projections for the 2020 RPA Assessment.
        Fort Collins, CO: Forest Service Research Data Archive. https://doi.org/10.2737/RDS-2023-0026
        """)

def show_troubleshooting():
    """Display troubleshooting guide"""
    st.markdown("### 🔧 Troubleshooting")

    # Common issues
    issues = {
        "Database not found": {
            "symptoms": "Error messages about missing database file",
            "solutions": [
                "Check that the database file exists at the configured path",
                "Run the data conversion script: `uv run python scripts/converters/convert_to_duckdb.py`",
                "Set LANDUSE_DB_PATH environment variable to correct location"
            ]
        },
        "API key errors": {
            "symptoms": "Authentication errors or missing API key messages",
            "solutions": [
                "Create config/.env file with your API keys",
                "Ensure API keys are valid and have sufficient credits",
                "Check that environment variables are loaded correctly"
            ]
        },
        "Query timeouts": {
            "symptoms": "Queries taking too long or timing out",
            "solutions": [
                "Increase LANDUSE_MAX_EXECUTION_TIME environment variable",
                "Add more specific WHERE clauses to limit data",
                "Use LIMIT clauses in custom SQL queries"
            ]
        },
        "Import errors": {
            "symptoms": "Module not found or import errors",
            "solutions": [
                "Run `uv sync` to install all dependencies",
                "Check that virtual environment is activated",
                "Verify Python path includes src directory"
            ]
        }
    }

    for issue, details in issues.items():
        with st.expander(f"❓ {issue}"):
            st.markdown(f"**Symptoms:** {details['symptoms']}")
            st.markdown("**Solutions:**")
            for solution in details['solutions']:
                st.markdown(f"- {solution}")

def show_feedback_form():
    """Display feedback form for users to submit questions or issues"""
    st.markdown("### 📝 Submit Feedback")
    st.markdown("Have questions, suggestions, or found a bug? Let us know!")

    with st.form("feedback_form", clear_on_submit=True):
        # Feedback type
        feedback_type = st.selectbox(
            "Feedback Type",
            ["Question", "Bug Report", "Feature Request", "General Feedback"]
        )

        # User contact (optional)
        user_email = st.text_input(
            "Your Email (optional)",
            placeholder="your.email@example.com",
            help="Provide your email if you'd like a response",
            max_chars=100
        )

        # Subject - REQUIRED
        subject = st.text_input(
            "Subject *",
            placeholder="Brief description of your feedback",
            help="Required field",
            max_chars=100
        )

        # Message - REQUIRED
        message = st.text_area(
            "Message *",
            placeholder="Please provide details...",
            help="Required field",
            height=150,
            max_chars=2000
        )

        # Submit button
        submitted = st.form_submit_button("Submit Feedback")

        if submitted:
            # Validate required fields with specific messages
            errors = []
            if not subject or not subject.strip():
                errors.append("📌 Subject is required")
            if not message or not message.strip():
                errors.append("📌 Message is required")

            if errors:
                for error in errors:
                    st.error(error)
            else:
                try:
                    # Sanitize inputs to prevent injection attacks
                    subject_clean = html.escape(subject.strip())
                    message_clean = html.escape(message.strip())
                    user_email_clean = html.escape(user_email.strip()) if user_email else None

                    # Validate input lengths for URL
                    if len(subject_clean) > 100:
                        st.error("Subject is too long. Please keep it under 100 characters.")
                        return
                    if len(message_clean) > 2000:
                        st.error("Message is too long. Please keep it under 2000 characters.")
                        return

                    # Create GitHub issue URL with pre-filled content
                    github_issue_url = "https://github.com/mihiarc/rpa-landuse/issues/new"
                    issue_title = f"[{feedback_type}] {subject_clean}"
                    issue_body = f"""**Feedback Type:** {feedback_type}

**Contact:** {user_email_clean if user_email_clean else 'Not provided'}

**Description:**
{message_clean}

---
*Submitted via RPA Land Use Analytics feedback form*
"""

                    # Encode parameters for URL with error handling
                    params = urllib.parse.urlencode({
                        'title': issue_title,
                        'body': issue_body
                    })
                    full_url = f"{github_issue_url}?{params}"

                    # Validate URL length (GitHub has limits)
                    if len(full_url) > 8192:
                        st.error("Your feedback is too long for direct submission. Please shorten your message or submit directly on GitHub.")
                        return

                    st.success("✅ Thank you for your feedback!")
                    st.markdown(f"""
                    Your feedback has been prepared. Please click the button below to submit it to GitHub:

                    [🐛 Create GitHub Issue]({full_url})

                    *Note: You'll need a GitHub account to submit the issue. If you don't have one,
                    please contact the project maintainer directly.*
                    """)

                except Exception as e:
                    st.error(f"An error occurred while preparing your feedback: {str(e)}")
                    st.info("Please try submitting your feedback directly on [GitHub Issues](https://github.com/mihiarc/rpa-landuse/issues/new).")

def main():
    """Main settings interface"""
    st.title("📚 RPA Assessment Help & Documentation")
    st.markdown("**User guide and documentation for the RPA Land Use Analytics platform**")

    # Only show Help & Documentation for production deployment
    show_help_documentation()

    # Feedback form section
    st.markdown("---")
    show_feedback_form()

    # Footer with updated contact information
    st.markdown("---")
    st.markdown("""
    **🆘 Need more help?**

    **📧 Contact & Support:**
    - **GitHub Issues:** [Report bugs or request features](https://github.com/mihiarc/rpa-landuse/issues)
    - **Project Repository:** [mihiarc/rpa-landuse](https://github.com/mihiarc/rpa-landuse)
    - **Discussions:** [Ask questions in GitHub Discussions](https://github.com/mihiarc/rpa-landuse/discussions)

    **📚 Resources:**
    - **Documentation:** [Project README and Wiki](https://github.com/mihiarc/rpa-landuse/blob/main/README.md)
    - **Releases & Updates:** [View changelog and announcements](https://github.com/mihiarc/rpa-landuse/releases)
    - **USDA RPA Assessment:** [Learn more about the data source](https://www.fs.usda.gov/rds/archive/catalog/RDS-2023-0026)

    **💡 Quick Actions:**
    - Use the feedback form above to submit questions or issues
    - Check the troubleshooting guide for common problems
    - Review system status for configuration details
    """)

if __name__ == "__main__":
    main()
