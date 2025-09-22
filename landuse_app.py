#!/usr/bin/env python3
"""
RPA Land Use Analytics - Streamlit Dashboard
AI-powered analytics tool for USDA Forest Service RPA Assessment land use data
"""

# Very early debug output - only in development
import os
import sys
from pathlib import Path

if os.getenv("STREAMLIT_RUNTIME_ENV") != "cloud":
    print("DEBUG: Starting landuse_app.py")
    print(f"DEBUG: Python executable: {sys.executable}")
    print(f"DEBUG: Python version: {sys.version}")

# Add src to path so we can import our landuse modules
try:
    project_root = Path(__file__).parent.resolve()
    src_path = project_root / "src"

    # Add to path if not already there
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Debug output for deployment
    print(f"DEBUG: Working directory: {os.getcwd()}")
    print(f"DEBUG: Project root: {project_root}")
    print(f"DEBUG: Source path: {src_path}")
    print(f"DEBUG: Source exists: {src_path.exists()}")
except Exception as e:
    print(f"ERROR setting up paths: {e}")
    import traceback
    traceback.print_exc()

# Import third-party libraries after sys.path modification
import streamlit as st  # noqa: E402

# Configure page settings - must be first Streamlit command
st.set_page_config(
    page_title="USDA Forest Service RPA Assessment",
    page_icon="🌲",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo/rpa-landuse-analytics',
        'Report a bug': 'https://github.com/your-repo/rpa-landuse-analytics/issues',
        'About': """
        # USDA Forest Service RPA Assessment

        Resources Planning Act (RPA) Assessment Analytics Dashboard

        **Features:**
        - 🤖 Natural language querying with AI agents
        - 📊 Interactive data visualizations
        - 🦆 DuckDB-powered analytics
        - 🌍 Climate scenario analysis (RCP45/85, SSP1-5)

        Data source: USDA Forest Service 2020 RPA Assessment
        Built with LangGraph, DuckDB, and Streamlit.
        """
    }
)

# Load environment variables (already imported at top)

# Try to load from .env if it exists (local development)
try:
    from dotenv import load_dotenv  # noqa: E402

    # Try multiple possible env file locations
    possible_env_paths = [
        project_root / "config" / ".env",
        project_root / ".env",
        Path("config/.env"),
        Path(".env")
    ]

    env_loaded = False
    for env_path in possible_env_paths:
        try:
            if env_path.exists():
                load_dotenv(env_path)
                print(f"DEBUG: Loaded .env from {env_path}")
                env_loaded = True
                break
        except Exception as e:
            print(f"DEBUG: Could not load {env_path}: {e}")

    if not env_loaded:
        print("DEBUG: No .env file found, will use st.secrets if available")

except ImportError:
    print("DEBUG: python-dotenv not available, using st.secrets")
except Exception as e:
    print(f"ERROR loading environment: {e}")

# Use Streamlit secrets in deployment (if available)
try:
    if hasattr(st, 'secrets'):
        # Check if secrets exist before trying to access them
        try:
            if len(st.secrets) > 0:
                for key, value in st.secrets.items():
                    os.environ[key] = str(value)
                print(f"DEBUG: Loaded {len(st.secrets)} secrets from Streamlit Cloud")
            else:
                print("DEBUG: No secrets found in st.secrets (this is fine if using .env)")
        except FileNotFoundError:
            # This is expected when running locally without secrets.toml
            print("DEBUG: No secrets.toml file found (using .env instead)")
except Exception as e:
    # Only show error if it's not about missing secrets file
    if "No secrets found" not in str(e):
        print(f"ERROR loading st.secrets: {e}")

# Custom CSS for modern styling with theme-aware colors
st.markdown("""
<style>
    /* Wide layout optimizations */
    .block-container {
        max-width: 95%;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* Responsive design for different screen sizes */
    @media (max-width: 768px) {
        .block-container {
            max-width: 100%;
            padding-left: 1rem;
            padding-right: 1rem;
        }

        .hero-title {
            font-size: 2rem;
        }

        .hero-subtitle {
            font-size: 1rem;
        }

        .feature-card {
            margin: 0.25rem;
            padding: 1.5rem;
            min-height: auto;
        }
    }

    /* Large screens optimization */
    @media (min-width: 1920px) {
        .block-container {
            max-width: 1800px;
            margin: 0 auto;
        }
    }

    /* Hero section styling - RPA Assessment branding colors */
    .hero-section {
        background: linear-gradient(135deg, #496f4a 0%, #85b18b 100%);
        padding: 3rem 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }

    .hero-title {
        font-size: 3rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }

    .hero-subtitle {
        font-size: 1.25rem;
        opacity: 0.95;
    }

    /* Main app styling - theme aware */
    .main-header {
        padding: 1rem 0;
        border-bottom: 1px solid rgba(184, 208, 185, 0.3);
        margin-bottom: 2rem;
    }

    /* Metric card - RPA color gradient for visual hierarchy */
    .metric-card {
        background: linear-gradient(135deg, #61a4b5 0%, #a3cad4 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }

    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }

    /* Feature card - theme aware with RPA color backgrounds */
    .feature-card {
        background: rgba(200, 223, 229, 0.15);
        border: 1px solid rgba(163, 202, 212, 0.3);
        border-radius: 12px;
        padding: 2rem;
        margin: 0.5rem 0.5rem 1rem 0.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        height: 420px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .feature-card-container {
        display: flex;
        flex-direction: column;
        height: 100%;
    }

    .feature-card:hover {
        box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        transform: translateY(-4px);
        border-color: #496f4a;
        background: rgba(73, 111, 74, 0.05);
    }

    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }

    .feature-title {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: inherit;
    }

    .feature-description {
        color: inherit;
        opacity: 0.8;
        line-height: 1.6;
        margin-bottom: 1rem;
    }

    .feature-content {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
    }

    .feature-list {
        margin-top: auto;
        padding-left: 1.5rem;
        list-style-type: disc;
    }

    .feature-list li {
        margin-bottom: 0.5rem;
        line-height: 1.5;
        font-size: 0.95rem;
    }

    /* Navigation improvements - theme aware */
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
        background-color: rgba(184, 208, 185, 0.2);
        transform: translateX(4px);
    }

    /* Section styling - inherits theme colors */
    .section-header {
        font-size: 2rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        color: inherit;
        display: flex;
        align-items: center;
    }

    .section-icon {
        margin-right: 0.75rem;
    }

    /* Quick stats styling */
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

def check_environment():
    """Check if the environment is properly configured"""
    # os and Path already imported at top of file

    checks = {
        "database": False,
        "api_keys": False,
        "dependencies": False,
        "landuse_module": False
    }

    debug_info = []

    # Check database with multiple possible paths
    db_paths = [
        Path(os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')),
        project_root / 'data' / 'processed' / 'landuse_analytics.duckdb',
        Path('data/processed/landuse_analytics.duckdb')
    ]

    for db_path in db_paths:
        if db_path.exists():
            checks["database"] = True
            debug_info.append(f"Database found at: {db_path}")
            break
    else:
        debug_info.append(f"Database not found. Tried: {[str(p) for p in db_paths]}")

    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    checks["api_keys"] = bool(openai_key or anthropic_key)

    if openai_key:
        debug_info.append(f"OpenAI key present ({len(openai_key)} chars)")
    if anthropic_key:
        debug_info.append(f"Anthropic key present ({len(anthropic_key)} chars)")

    # Check dependencies
    try:
        import duckdb
        import langchain
        import pandas
        checks["dependencies"] = True
        debug_info.append("Core dependencies OK")
    except ImportError as e:
        checks["dependencies"] = False
        debug_info.append(f"Dependency error: {e}")

    # Check landuse module
    try:
        from landuse.config import LanduseConfig
        checks["landuse_module"] = True
        debug_info.append("Landuse module OK")
    except Exception as e:
        checks["landuse_module"] = False
        debug_info.append(f"Landuse module error: {e}")

    return checks, debug_info

def show_welcome_page():
    """Display the welcome/home page with wide layout optimization"""

    # Hero Section with gradient background
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">🌲 USDA Forest Service RPA Assessment</h1>
        <p class="hero-subtitle">Resources Planning Act Assessment Analytics Dashboard</p>
        <p class="hero-subtitle">Explore county-level land use projections from 2012-2100 across 20 climate scenarios</p>
    </div>
    """, unsafe_allow_html=True)

    # Add system check hint if there are issues
    checks, _ = check_environment()
    if not all(checks.values()):
        st.info("💡 Check **Settings** to view system status and resolve any configuration issues.")

    # Feature overview in 2x2 grid layout
    st.markdown('<h2 class="section-header"><span class="section-icon">🚀</span>Features</h2>', unsafe_allow_html=True)

    # First row of features
    col1, col2 = st.columns(2)

    with col1:
        with st.container():
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">💬</div>
                <h3 class="feature-title">Natural Language Queries</h3>
                <p class="feature-description">Ask questions in plain English about land use changes. Our AI converts your questions to SQL and provides insights.</p>
                <ul class="feature-list">
                    <li>Agricultural land loss analysis</li>
                    <li>Climate scenario comparisons</li>
                    <li>Urban expansion patterns</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            if st.button("💬 Open Chat", key="feature_chat", use_container_width=True):
                st.switch_page("views/chat.py")

    with col2:
        with st.container():
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">📊</div>
                <h3 class="feature-title">Interactive Analytics</h3>
                <p class="feature-description">Explore pre-built visualizations with real-time data from the RPA Assessment.</p>
                <ul class="feature-list">
                    <li>Climate impact dashboards</li>
                    <li>Geographic trend maps</li>
                    <li>Time series analysis</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            if st.button("📊 Open Analytics", key="feature_analytics", use_container_width=True):
                st.switch_page("views/analytics.py")

    # Second row of features
    col3, col4 = st.columns(2)

    with col3:
        with st.container():
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🔍</div>
                <h3 class="feature-title">Data Explorer</h3>
                <p class="feature-description">Advanced tools for data scientists to directly query and analyze the database.</p>
                <ul class="feature-list">
                    <li>Schema browser</li>
                    <li>SQL query interface</li>
                    <li>Export capabilities</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🔍 Open Explorer", key="feature_explorer", use_container_width=True):
                st.switch_page("views/explorer.py")

    with col4:
        with st.container():
            st.markdown("""
            <div class="feature-card">
                <div class="feature-icon">🗺️</div>
                <h3 class="feature-title">Enhanced Visualizations</h3>
                <p class="feature-description">Rich maps, flow diagrams, and advanced analytics for deeper insights.</p>
                <ul class="feature-list">
                    <li>Choropleth maps</li>
                    <li>Sankey flow diagrams</li>
                    <li>Animated timelines</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            if st.button("🗺️ Open Visualizations", key="feature_viz", use_container_width=True):
                st.switch_page("views/analytics.py")

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
        "views/chat.py",
        title="Natural Language Chat",
        icon=":material/chat:"
    )

    # Analytics dashboard page
    analytics_page = st.Page(
        "views/analytics.py",
        title="Analytics Dashboard",
        icon=":material/analytics:"
    )

    # Data explorer page
    explorer_page = st.Page(
        "views/explorer.py",
        title="Data Explorer",
        icon=":material/search:"
    )

    # Data extraction page
    extraction_page = st.Page(
        "views/extraction.py",
        title="Data Extraction",
        icon=":material/download:"
    )

    # Help & Documentation page
    help_page = st.Page(
        "views/settings.py",
        title="Help & Documentation",
        icon=":material/help:"
    )

    return {
        "Main": [home_page],
        "Analysis": [chat_page, analytics_page, explorer_page, extraction_page],
        "Help": [help_page]
    }

# Main navigation using modern st.navigation
def main():
    """Main application entry point with modern navigation"""

    try:
        # Check authentication first
        from landuse.auth import require_authentication, show_logout_button
        
        if not require_authentication():
            return  # Show login page, don't proceed with app
        
        # Add RTI logo to the top of the sidebar before navigation
        st.logo(
            image="assets/rti.svg",
            size="large"
        )
        
        # Create navigation structure
        pages = create_pages()

        # Add logout button to sidebar
        show_logout_button("sidebar")

        # Use modern st.navigation API
        pg = st.navigation(pages)

        # Run the selected page
        pg.run()

    except AttributeError as e:
        if 'navigation' in str(e):
            st.error("❌ Navigation API Error")
            st.error(f"This app requires Streamlit 1.36.0 or later. Current version: {st.__version__}")
            st.info("The app is configured to use st.navigation which was introduced in Streamlit 1.36.0")

            # Show welcome page as fallback
            show_welcome_page()
        else:
            raise

    except ImportError as e:
        st.error("❌ Import Error Detected")
        st.error(f"Failed to import: {e}")

        # Common import issues
        if "landuse" in str(e):
            st.warning("The 'landuse' module could not be imported. Checking paths...")
            st.write(f"- Working directory: {os.getcwd()}")
            st.write(f"- Project root: {project_root}")
            st.write(f"- Source path exists: {src_path.exists()}")
            st.write(f"- sys.path includes: {str(src_path) in sys.path}")

            # List src directory contents
            if src_path.exists():
                st.write("Source directory contents:")
                for item in sorted(os.listdir(src_path)):
                    st.write(f"  - {item}")

        # Show basic info
        show_welcome_page()

    except Exception as e:
        st.error("❌ Unexpected Error")
        st.error(f"{type(e).__name__}: {e}")

        # Show traceback in expander
        import traceback
        with st.expander("Show full traceback"):
            st.code(traceback.format_exc())

        # Show basic welcome page
        show_welcome_page()

    # Add footer with attribution
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #496f4a; padding: 20px;'>
        <p><strong>USDA Forest Service Resources Planning Act Assessment</strong></p>
        <p>Data source: <a href='https://www.fs.usda.gov/research/inventory/rpaa' target='_blank'>USDA Forest Service 2020 RPA Assessment</a></p>
        <p style='font-size: 0.9em;'>Analyzing America's forests and rangelands for sustainable resource management</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL ERROR in main: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

        # Try to show error in Streamlit if possible
        try:
            import streamlit as st
            st.error(f"Fatal error: {type(e).__name__}: {e}")
            with st.expander("Full traceback"):
                st.code(traceback.format_exc())
        except:
            pass

        # Re-raise to ensure proper exit
        raise
