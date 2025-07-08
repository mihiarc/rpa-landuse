# Dependency Analysis for RPA Land Use Analytics

## Currently Declared Dependencies

From `pyproject.toml`:
1. **langchain** - ✅ Used (agents, chains)
2. **langchain-anthropic** - ✅ Used (Claude models)
3. **langchain-openai** - ✅ Used (GPT models)
4. **langchain-community** - ✅ Used (document loaders, vectorstores)
5. **langgraph** - ✅ Used (graph-based agents)
6. **langgraph-checkpoint** - ✅ Used (memory management)
7. **langgraph-checkpoint-sqlite** - ✅ Used (SQLite checkpoint storage)
8. **pandas** - ✅ Used (data manipulation)
9. **openpyxl** - ❓ Not found in imports (Excel file support)
10. **python-dotenv** - ✅ Used (environment variables)
11. **numpy** - ✅ Used (numerical operations)
12. **matplotlib** - ✅ Used (map generation)
13. **seaborn** - ❌ Not found in imports
14. **sqlalchemy** - ❌ Not found in imports (replaced by DuckDB)
15. **duckdb** - ✅ Used (primary database)
16. **pyarrow** - ✅ Used (Parquet support)
17. **jupyter** - ❓ Not needed for deployment
18. **ipykernel** - ❓ Not needed for deployment
19. **geopandas** - ✅ Used (geographic data)
20. **fastparquet** - ❌ Not found in imports (using pyarrow instead)
21. **rich** - ✅ Used (terminal UI)
22. **pydantic** - ✅ Used (data validation)
23. **ijson** - ✅ Used (JSON streaming)
24. **streamlit** - ✅ Used (web UI)
25. **plotly** - ✅ Used (visualizations)

## Analysis Results

### Unused Dependencies (Tech Debt)
1. **seaborn** - Not used anywhere, matplotlib is sufficient
2. **sqlalchemy** - Replaced by direct DuckDB usage
3. **fastparquet** - Using pyarrow for Parquet files
4. **openpyxl** - May be used for Excel export (need to verify)

### Development-Only Dependencies
1. **jupyter** - Only needed for notebooks
2. **ipykernel** - Only needed for notebooks

### Additional Imports Found (Already included as sub-dependencies)
- shapely (comes with geopandas)
- Various standard library modules (no install needed)

## Recommended Cleaned Dependencies

```toml
dependencies = [
    # Core AI/LLM
    "langchain>=0.3.0",
    "langchain-anthropic>=0.2.0",
    "langchain-openai>=0.2.0",
    "langchain-community>=0.3.0",
    "langgraph>=0.2.0",
    "langgraph-checkpoint>=2.0.0",
    "langgraph-checkpoint-sqlite>=2.0.0",
    
    # Data processing
    "pandas>=2.2.0",
    "numpy>=1.26.0",
    "duckdb>=1.0.0",
    "pyarrow>=15.0.0",
    "ijson>=3.0.0",
    
    # Visualization
    "matplotlib>=3.8.0",
    "plotly>=5.17.0",
    "geopandas>=1.0.0",
    
    # Web UI
    "streamlit>=1.46.0",
    
    # Utilities
    "python-dotenv>=1.0.0",
    "rich>=14.0.0",
    "pydantic>=2.0.0",
]

# Move to optional dependencies
[project.optional-dependencies]
dev = [
    "jupyter>=1.0.0",
    "ipykernel>=6.29.0",
    "openpyxl>=3.1.0",  # If Excel export is needed
]
```

## Size Impact

Removing unused dependencies will:
1. Reduce deployment size
2. Speed up installation
3. Reduce potential security vulnerabilities
4. Simplify dependency resolution

## Action Items

1. Remove seaborn, sqlalchemy, fastparquet from main dependencies
2. Move jupyter and ipykernel to dev dependencies
3. Verify if openpyxl is needed for Excel export functionality
4. Update requirements.txt after cleaning pyproject.toml