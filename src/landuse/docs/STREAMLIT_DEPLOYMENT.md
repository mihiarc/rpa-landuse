# Streamlit Community Cloud Deployment Guide

This guide explains how to deploy the RPA Land Use Analytics dashboard to Streamlit Community Cloud.

## Prerequisites

1. **GitHub Repository**: Your code must be in a public GitHub repository
2. **Streamlit Account**: Sign up at [share.streamlit.io](https://share.streamlit.io)
3. **Git LFS**: Large files (DuckDB) are tracked with Git LFS

## Repository Setup

### Git LFS Configuration

The repository is configured with Git LFS to handle large files:
- `*.duckdb` - DuckDB database files (312MB)
- `data/chroma_db/` - Chroma vector database (36MB) containing domain knowledge for the query agent:
  - `chroma.sqlite3` - SQLite database
  - `*.bin` files - Vector embeddings
  - `*.pickle` files - Index metadata

### Required Files

Ensure these files are present in your repository:
- `landuse_app.py` - Main Streamlit application with modern navigation
- `views/` directory - Individual page implementations:
  - `views/chat.py` - Natural language chat interface
  - `views/analytics.py` - Pre-built analytics dashboard
  - `views/explorer.py` - Data exploration interface
  - `views/extraction.py` - Data export functionality
  - `views/settings.py` - System status and configuration
- `pyproject.toml` - Python dependencies managed by uv
- `data/processed/landuse_analytics.duckdb` - Analytics database (via Git LFS)
- `data/chroma_db/` - Vector database for domain knowledge (via Git LFS)
- `src/landuse/` - Source code modules
- `.streamlit/config.toml` - Streamlit configuration (optional)

## Deployment Steps

### 1. Push to GitHub

```bash
# Ensure all changes are committed
git add .
git commit -m "Prepare for Streamlit deployment"

# Push with Git LFS files
git push origin main
```

### 2. Create Streamlit App

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Click "New app"
3. Connect your GitHub account if not already connected
4. Select your repository: `rpa-landuse`
5. Select branch: `main`
6. Main file path: `landuse_app.py`

### 3. Configure Secrets

Add your API keys in the Streamlit Cloud secrets management:

```toml
# In Streamlit Cloud Secrets (Advanced Settings)
OPENAI_API_KEY = "your-openai-api-key"
ANTHROPIC_API_KEY = "your-anthropic-api-key"  # Optional

# Optional configuration
LANDUSE_MODEL = "gpt-4o-mini"
TEMPERATURE = "0.1"
MAX_TOKENS = "4000"
```

### 4. Advanced Settings

In the advanced settings, you may need to:

1. **Python version**: Ensure it matches your local version (3.11+)
2. **Install command**: The default should work with `pyproject.toml`
3. **Resource limits**: The free tier should be sufficient

## Environment Variables

The app reads from Streamlit secrets automatically. Configure these in the Streamlit Cloud dashboard:

```python
# Required
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

# Optional (with defaults)
ANTHROPIC_API_KEY = st.secrets.get("ANTHROPIC_API_KEY", "")
LANDUSE_MODEL = st.secrets.get("LANDUSE_MODEL", "gpt-4o-mini")
```

## Troubleshooting

### Large File Issues

If you encounter issues with the DuckDB file:

1. Ensure Git LFS is properly configured:
   ```bash
   git lfs ls-files  # Should show data/processed/landuse_analytics.duckdb
   ```

2. Verify the file is uploaded:
   ```bash
   git lfs push origin main --all
   ```

### Memory Issues

If the app runs out of memory:

1. The DuckDB file (312MB) and Chroma DB (36MB) should fit in the free tier
2. Consider implementing query result limits
3. Use DuckDB's efficient query processing
4. The Chroma vector database is loaded on-demand for semantic search

### Connection Issues

The app uses a custom DuckDB connection implementing st.connection pattern:
- **Custom Connection Class**: `DuckDBConnection` extends `BaseConnection`
- **Automatic Caching**: Query results cached with configurable TTL (default: 3600s)
- **Retry Logic**: Database operations use exponential backoff retry pattern
- **Read-only Mode**: Safe database access with connection validation
- **Thread Safety**: Concurrent access support for multi-user environments
- **Path Resolution**: Automatic database path detection with environment variable fallback

### Navigation Issues

The app requires Streamlit 1.36.0+ for the modern navigation API:
- Uses `st.navigation()` with organized page groups
- Graceful fallback to welcome page if navigation is unavailable
- Check Streamlit version if navigation errors occur

## Local Testing

Before deploying, test locally to match the cloud environment:

```bash
# Install dependencies
uv sync

# Create local environment file
cp config/.env.example config/.env
# Edit config/.env to add your API keys

# Run the app
uv run streamlit run landuse_app.py

# Or run with environment variables directly
OPENAI_API_KEY="your-key" uv run streamlit run landuse_app.py
```

### Streamlit Version Requirements

The app uses modern Streamlit features:
- **Streamlit 1.36.0+**: Required for `st.navigation()` API
- **st.connection pattern**: Custom DuckDB connection implementation
- **st.fragment**: Performance optimization for chat interface
- **Modern CSS**: Responsive design with mobile optimization

## Monitoring

Once deployed:
1. Check the app logs in Streamlit Cloud dashboard
2. Monitor usage and performance metrics
3. Set up error notifications

## Updates

To update the deployed app:
1. Make changes locally
2. Commit and push to GitHub
3. Streamlit Cloud will automatically redeploy

## Security Notes

- Never commit API keys to the repository
- Use Streamlit secrets for all sensitive data
- The DuckDB file is read-only in the app
- User queries are validated before execution

## Support

For issues specific to:
- **Streamlit deployment**: Check [Streamlit documentation](https://docs.streamlit.io/streamlit-community-cloud)
- **Git LFS**: See [Git LFS documentation](https://git-lfs.github.com/)
- **App functionality**: See the main README.md