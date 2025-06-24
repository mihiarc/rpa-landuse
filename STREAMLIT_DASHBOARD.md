# 🌾 Landuse Analytics - Streamlit Dashboard

Modern web interface for exploring land use transition data with natural language queries and interactive visualizations.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
# Install all dependencies including Streamlit
uv sync
```

### 2. Configure Environment
```bash
# Create config/.env file with your API keys
cat > config/.env << EOF
# Required: At least one API key
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional: Model configuration
LANDUSE_MODEL=gpt-4o-mini
TEMPERATURE=0.1
MAX_TOKENS=4000

# Database path (default shown)
LANDUSE_DB_PATH=data/processed/landuse_analytics.duckdb
EOF
```

### 3. Launch Dashboard
```bash
# Option 1: Direct command
uv run streamlit run streamlit_app.py

# Option 2: Using shortcut (after uv sync)
uv run landuse-dashboard

# The dashboard will open at http://localhost:8501
```

## 📊 Dashboard Features

### 🏠 Home Page
- **System Status**: Database, API keys, dependencies check
- **Dataset Overview**: Key statistics and metrics
- **Feature Introduction**: Guide to available tools
- **Quick Start**: Getting started instructions

### 💬 Natural Language Chat
- **Real-time Queries**: Ask questions in plain English
- **Streaming Responses**: Word-by-word response delivery
- **Conversation History**: Persistent chat session
- **Quick Queries**: Pre-built example questions
- **Smart Defaults**: Intelligent assumptions when details aren't specified

**Example Questions:**
- "How much agricultural land is being lost?"
- "Which scenarios show the most urban expansion?"
- "Compare forest loss between RCP45 and RCP85 scenarios"
- "Show me crop to pasture transitions by state"

### 📊 Analytics Dashboard
Pre-built visualizations with interactive Plotly charts:

- **🌾 Agricultural Analysis**: Land loss by scenario, impact trends
- **🏙️ Urbanization Trends**: State-level urban expansion patterns
- **🌡️ Climate Scenarios**: RCP/SSP pathway comparisons
- **📈 Time Series**: Trends over projection periods

**Features:**
- Interactive charts with zoom, pan, hover details
- Downloadable data tables
- Key insights and business intelligence
- Cross-scenario comparisons

### 🔍 Data Explorer
Advanced tools for data scientists and researchers:

- **📊 Schema Browser**: Interactive table structure exploration
- **🔧 SQL Interface**: Custom query execution with syntax highlighting
- **💡 Query Examples**: Pre-built queries organized by category
- **📚 Data Dictionary**: Field definitions and land use categories
- **📥 Data Export**: Download query results as CSV

**Query Categories:**
- Basic queries (row counts, schema exploration)
- Agricultural analysis (land loss, crop transitions)
- Climate analysis (RCP/SSP comparisons)
- Geographic analysis (state/county patterns)
- Time series (trends, acceleration)

### ⚙️ Settings & Help
Configuration and troubleshooting tools:

- **🔧 System Status**: Real-time component health checks
- **⚙️ Configuration**: Environment variable management
- **📚 Help & Docs**: Feature guides and examples
- **🔧 Troubleshooting**: Common issues and solutions

## 🎨 Modern UI Features

### Design Principles
- **Material Design Icons**: Consistent iconography using `:material/icon:`
- **Responsive Layout**: Mobile-friendly with `st.columns()` and adaptive sizing
- **Modern Navigation**: Latest `st.Page` and `st.navigation` API (Streamlit 1.32+)
- **Rich Visualizations**: Plotly charts with interactive features
- **Status Indicators**: Real-time system health and progress tracking

### User Experience
- **Streaming Responses**: Real-time chat with typing indicators
- **Caching**: Optimized performance with `@st.cache_data` and `@st.cache_resource`
- **Error Handling**: Helpful error messages with suggested solutions
- **Progressive Disclosure**: Expandable sections for advanced features
- **Contextual Help**: Tooltips, info boxes, and inline documentation

### Accessibility
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader Friendly**: Proper ARIA labels and semantic HTML
- **High Contrast**: Clear visual hierarchy and readable color scheme
- **Mobile Responsive**: Touch-friendly interface for tablets and phones

## 🛠️ Technical Architecture

### Frontend Stack
- **Streamlit 1.32+**: Modern multipage app framework
- **Plotly 5.17+**: Interactive visualizations
- **Custom CSS**: Enhanced styling and modern appearance
- **Material Icons**: Consistent iconography

### Backend Integration
- **LangChain Agents**: Seamless integration with existing natural language agents
- **DuckDB**: High-performance analytics database
- **Caching Layer**: Optimized data loading and agent initialization
- **Session Management**: Persistent conversation state

### File Structure
```
streamlit_app.py           # Main entry point with navigation
pages/
├── chat.py               # Natural language chat interface
├── analytics.py          # Pre-built visualizations dashboard
├── explorer.py           # Data exploration and SQL interface
└── settings.py           # Configuration and help
.streamlit/
└── config.toml          # Streamlit configuration
```

## 🔧 Configuration Options

### Environment Variables
```bash
# Core Configuration
LANDUSE_DB_PATH=data/processed/landuse_analytics.duckdb
LANDUSE_MODEL=gpt-4o-mini
TEMPERATURE=0.1
MAX_TOKENS=4000

# Performance Tuning
LANDUSE_MAX_ITERATIONS=5
LANDUSE_MAX_EXECUTION_TIME=120
LANDUSE_MAX_QUERY_ROWS=1000
LANDUSE_DEFAULT_DISPLAY_LIMIT=50

# Rate Limiting
LANDUSE_RATE_LIMIT_CALLS=60
LANDUSE_RATE_LIMIT_WINDOW=60
```

### Streamlit Configuration
The `.streamlit/config.toml` file includes:
- Modern theme with custom colors
- Browser settings and CORS configuration
- File upload limits and security settings
- Navigation and toolbar preferences

## 🚀 Deployment Options

### Local Development
```bash
# Development mode with auto-reload
uv run streamlit run streamlit_app.py --server.runOnSave true
```

### Production Deployment
```bash
# Production mode
uv run streamlit run streamlit_app.py --server.port 8501 --server.headless true
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
```

## 💡 Best Practices

### Performance Optimization
- Use `@st.cache_data` for expensive database queries
- Use `@st.cache_resource` for agent initialization
- Implement query limits to prevent runaway operations
- Add loading spinners for long-running operations

### User Experience
- Provide immediate feedback with status indicators
- Use progressive disclosure for complex features
- Include helpful error messages with suggested solutions
- Maintain conversation context in chat interface

### Security
- Never expose API keys in the interface
- Validate and sanitize SQL queries
- Use read-only database connections
- Implement rate limiting for API calls

## 🆘 Troubleshooting

### Common Issues

**Dashboard won't start:**
- Check that Streamlit is installed: `uv run streamlit --version`
- Verify Python path includes src directory
- Ensure all dependencies are installed: `uv sync`

**Database connection errors:**
- Verify database file exists at configured path
- Check file permissions for read access
- Run database conversion if needed: `uv run python scripts/converters/convert_to_duckdb.py`

**Chat interface not working:**
- Verify API keys are configured in `config/.env`
- Check API key validity and credits
- Review error messages in the Settings page

**Visualizations not loading:**
- Ensure Plotly is installed: `uv run python -c "import plotly; print(plotly.__version__)"`
- Check browser JavaScript console for errors
- Verify data queries are returning results

### Getting Help
- Check the **Settings & Help** page in the dashboard
- Review system status indicators
- Run `uv run python quickstart.py` for environment verification
- Check the project documentation in `docs/`

## 🎯 Next Steps

1. **Explore the Chat Interface**: Start with simple questions to understand the data
2. **Review Analytics Dashboard**: Examine pre-built visualizations for insights
3. **Try Data Explorer**: Run custom SQL queries for advanced analysis
4. **Customize Configuration**: Adjust settings for your specific use case
5. **Extend Functionality**: Add new visualizations or analysis tools

Happy analyzing! 🌾📊