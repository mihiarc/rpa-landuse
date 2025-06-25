#!/usr/bin/env python3
"""
RPA Land Use Analytics - Streamlit Dashboard
AI-powered analytics tool for USDA Forest Service RPA Assessment land use data
"""

import streamlit as st
from pathlib import Path
import sys

# Add src to path so we can import our landuse modules
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Configure page settings - must be first Streamlit command
st.set_page_config(
    page_title="RPA Land Use Analytics",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/rpa-landuse-analytics',
        'Report a bug': 'https://github.com/your-repo/rpa-landuse-analytics/issues',
        'About': """
        # RPA Land Use Analytics
        
        AI-powered analytics tool for USDA Forest Service RPA Assessment data.
        
        **Features:**
        - 🤖 Natural language querying with AI agents
        - 📊 Interactive data visualizations
        - 🦆 DuckDB-powered analytics
        - 🌍 Climate scenario analysis (RCP45/85, SSP1-5)
        
        Data source: USDA Forest Service 2020 RPA Assessment
        Built with LangChain, DuckDB, and Streamlit.
        """
    }
)

# Load environment variables
from dotenv import load_dotenv
load_dotenv("config/.env")
load_dotenv()

# Custom CSS for modern styling
st.markdown("""
<style>
    /* Main app styling */
    .main-header {
        padding: 1rem 0;
        border-bottom: 1px solid #e0e0e0;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    
    .feature-card {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s ease;
    }
    
    .feature-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    
    /* Status indicators */
    .status-ok { color: #28a745; font-weight: bold; }
    .status-warning { color: #ffc107; font-weight: bold; }
    .status-error { color: #dc3545; font-weight: bold; }
    
    /* Navigation improvements */
    .nav-link {
        display: flex;
        align-items: center;
        padding: 0.75rem 1rem;
        margin: 0.25rem 0;
        border-radius: 6px;
        text-decoration: none;
        transition: all 0.2s ease;
    }
    
    .nav-link:hover {
        background-color: #f8f9fa;
        transform: translateX(4px);
    }
</style>
""", unsafe_allow_html=True)

def check_environment():
    """Check if the environment is properly configured"""
    import os
    from pathlib import Path
    
    checks = {
        "database": False,
        "api_keys": False,
        "dependencies": False
    }
    
    # Check database
    db_path = Path(os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'))
    checks["database"] = db_path.exists()
    
    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    checks["api_keys"] = bool(openai_key or anthropic_key)
    
    # Check dependencies
    try:
        import langchain
        import duckdb
        import pandas
        checks["dependencies"] = True
    except ImportError:
        checks["dependencies"] = False
    
    return checks

def show_welcome_page():
    """Display the welcome/home page"""
    
    # Header section
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🌲 RPA Land Use Analytics")
        st.markdown("""
        **AI-powered analytics tool for USDA Forest Service RPA Assessment data**
        
        Explore county-level land use projections from 2012-2070 across 20 climate scenarios from the 2020 Resources Planning Act Assessment.
        """)
    
    with col2:
        # Environment status
        checks = check_environment()
        st.markdown("### 🔧 System Status")
        
        status_icon = "✅" if checks["database"] else "❌"
        st.markdown(f"{status_icon} **Database:** {'Ready' if checks['database'] else 'Missing'}")
        
        status_icon = "✅" if checks["api_keys"] else "❌" 
        st.markdown(f"{status_icon} **API Keys:** {'Configured' if checks['api_keys'] else 'Missing'}")
        
        status_icon = "✅" if checks["dependencies"] else "❌"
        st.markdown(f"{status_icon} **Dependencies:** {'Installed' if checks['dependencies'] else 'Missing'}")
        
        if not all(checks.values()):
            st.warning("⚠️ Some components need setup. Check the Settings page for help.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Feature overview
    st.markdown("## 🚀 Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h3>💬 Natural Language Queries</h3>
            <p>Ask questions in plain English about land use changes:</p>
            <ul>
                <li>"Which scenarios show the most agricultural land loss?"</li>
                <li>"Compare forest loss between climate scenarios"</li>
                <li>"Show urban expansion by state"</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card">
            <h3>📊 Interactive Analytics</h3>
            <p>Explore pre-built visualizations and insights:</p>
            <ul>
                <li>Climate scenario comparisons</li>
                <li>Geographic trend analysis</li>
                <li>Time series visualizations</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="feature-card">
            <h3>🔍 Data Explorer</h3>
            <p>Advanced tools for data scientists:</p>
            <ul>
                <li>Database schema browser</li>
                <li>Direct SQL interface</li>
                <li>Query examples and templates</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Quick stats
    if checks["database"]:
        try:
            import duckdb
            import os
            
            db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
            conn = duckdb.connect(str(db_path), read_only=True)
            
            # Get basic stats
            stats = {}
            try:
                stats["counties"] = conn.execute("SELECT COUNT(DISTINCT fips_code) FROM dim_geography").fetchone()[0]
                stats["scenarios"] = conn.execute("SELECT COUNT(*) FROM dim_scenario").fetchone()[0]
                stats["transitions"] = conn.execute("SELECT COUNT(*) FROM fact_landuse_transitions").fetchone()[0]
                stats["time_periods"] = conn.execute("SELECT COUNT(*) FROM dim_time").fetchone()[0]
                
                st.markdown("## 📈 Dataset Overview")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("US Counties", f"{stats['counties']:,}")
                with col2:
                    st.metric("Climate Scenarios", stats['scenarios'])
                with col3:
                    st.metric("Land Transitions", f"{stats['transitions']:,}")
                with col4:
                    st.metric("Time Periods", stats['time_periods'])
                    
            except Exception as e:
                st.warning(f"Could not load dataset statistics: {e}")
            finally:
                conn.close()
                
        except Exception as e:
            st.error(f"Database connection error: {e}")
    
    # Getting started
    st.markdown("## 🎯 Getting Started")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### Quick Start Options:
        
        1. **💬 Chat Interface** - Start asking questions in natural language
        2. **📊 Analytics Dashboard** - Explore pre-built visualizations  
        3. **🔍 Data Explorer** - Browse the database schema and run custom queries
        4. **⚙️ Settings** - Configure API keys and check system status
        
        ### Example Questions:
        - "How much agricultural land is being lost?"
        - "Which states have the most urban expansion?"
        - "Compare forest loss between RCP45 and RCP85 scenarios"
        - "Show me crop to pasture transitions by state"
        """)
    
    with col2:
        st.info("""
        💡 **Tip:** The natural language interface uses intelligent defaults:
        
        - **Scenarios:** Averages across all 20 climate scenarios
        - **Time Period:** Full range (2012-2100) 
        - **Geography:** All US counties
        - **Transitions:** Only actual changes (not same-to-same)
        
        The AI will clearly state these assumptions in each response.
        """)

# Define pages using modern st.Page API
def create_pages():
    """Create page definitions for navigation"""
    
    # Main dashboard (home page)
    home_page = st.Page(
        show_welcome_page,
        title="Home",
        icon=":material/home:",
        default=True
    )
    
    # Chat interface page
    chat_page = st.Page(
        "pages/chat.py",
        title="Natural Language Chat",
        icon=":material/chat:"
    )
    
    # Analytics dashboard page
    analytics_page = st.Page(
        "pages/analytics.py", 
        title="Analytics Dashboard",
        icon=":material/analytics:"
    )
    
    # Data explorer page
    explorer_page = st.Page(
        "pages/explorer.py",
        title="Data Explorer", 
        icon=":material/search:"
    )
    
    # Data extraction page
    extraction_page = st.Page(
        "pages/extraction.py",
        title="Data Extraction",
        icon=":material/download:"
    )
    
    # Settings page
    settings_page = st.Page(
        "pages/settings.py",
        title="Settings & Help",
        icon=":material/settings:"
    )
    
    return {
        "Main": [home_page],
        "Analysis": [chat_page, analytics_page, explorer_page, extraction_page], 
        "Configuration": [settings_page]
    }

# Main navigation using modern st.navigation
def main():
    """Main application entry point with modern navigation"""
    
    # Create navigation structure
    pages = create_pages()
    
    # Use modern st.navigation API
    pg = st.navigation(pages)
    
    # Run the selected page
    pg.run()
    
    # Add footer with attribution
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666666; padding: 20px;'>
        <p><strong>RPA Land Use Analytics</strong></p>
        <p>Data source: <a href='https://www.fs.usda.gov/research/rpa' target='_blank'>USDA Forest Service 2020 RPA Assessment</a></p>
        <p style='font-size: 0.9em;'>Transforming America's land use data into actionable insights</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()