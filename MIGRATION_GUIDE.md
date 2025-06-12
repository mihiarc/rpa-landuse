# Streamlit App Modularization Migration Guide

This guide explains the new modular structure for the RPA Land Use Viewer Streamlit application.

## Overview

The monolithic `streamlit_app.py` (3,183 lines) has been refactored into a modular structure following Streamlit best practices. This improves maintainability, testability, and developer experience.

## New Directory Structure

```
streamlit_components/
├── __init__.py
├── config/
│   ├── __init__.py
│   └── constants.py          # Configuration constants
├── utils/
│   ├── __init__.py
│   └── data_loader.py        # Data loading functions
├── components/
│   ├── __init__.py
│   └── visualizations.py     # Reusable visualization components
└── pages/
    ├── __init__.py
    ├── overview.py            # Overview tab
    ├── data_explorer.py       # Data Explorer tab
    ├── urbanization_trends.py # Urbanization analysis
    └── natural_language_query.py # AI chat interface
```

## Key Benefits

1. **Modularity**: Each page is a separate module, making it easy to work on individual features
2. **Reusability**: Common functions are extracted to utils and components
3. **Maintainability**: Easier to debug and update specific functionality
4. **Testability**: Individual modules can be unit tested
5. **Performance**: Better caching strategies with modular data loading

## Migration Steps

### 1. Testing the New Structure

First, test the modular version alongside the original:

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the modular version
streamlit run streamlit_app_modular.py

# Compare with original
streamlit run streamlit_app.py
```

### 2. Gradual Migration

The modular app currently implements:
- ✅ Overview page
- ✅ Data Explorer
- ✅ Urbanization Trends
- ✅ Natural Language Query
- ⏳ Land Use Flow Diagrams (placeholder)
- ⏳ Forest Transitions (placeholder)
- ⏳ Agricultural Transitions (placeholder)
- ⏳ State Map (placeholder)

### 3. Completing the Migration

To complete the migration, the remaining pages need to be extracted:

```python
# Example: Creating forest_transitions.py
# 1. Copy the forest transitions tab code from streamlit_app.py
# 2. Create streamlit_components/pages/forest_transitions.py
# 3. Wrap the code in a render_forest_transitions_page() function
# 4. Import required dependencies
# 5. Update streamlit_app_modular.py to import and use the new page
```

### 4. Configuration Management

All constants are now in `config/constants.py`:
- Page configuration
- Data file mappings
- Scenario names
- Color schemes
- Cache settings

### 5. Data Loading

Data loading is centralized in `utils/data_loader.py`:
- `load_parquet_data()` - Loads all datasets
- `load_us_states()` - Loads geographic data
- `load_rpa_docs()` - Loads documentation
- Helper functions for filtering and aggregation

### 6. Visualization Components

Reusable visualizations in `components/visualizations.py`:
- `create_bar_chart()` - Bar charts
- `create_time_series_plot()` - Time series
- `create_land_use_sankey()` - Sankey diagrams
- `create_state_choropleth()` - Map visualizations
- `display_metrics_row()` - Metric cards

## Best Practices Implemented

1. **Separation of Concerns**: Each module has a single responsibility
2. **DRY Principle**: Common code is extracted to reusable functions
3. **Caching Strategy**: `@st.cache_data` decorators on data loading functions
4. **Type Hints**: Functions include type annotations
5. **Documentation**: Each module has docstrings
6. **Error Handling**: Proper error messages and fallbacks

## Next Steps

1. **Complete Page Migrations**: Extract remaining tabs to separate modules
2. **Add Tests**: Create unit tests for each module
3. **Enhance Components**: Add more reusable visualization components
4. **Optimize Performance**: Profile and optimize slow operations
5. **Add Logging**: Implement structured logging
6. **Create CI/CD**: Set up automated testing and deployment

## Development Workflow

When adding new features:

1. Create new modules in appropriate directories
2. Use existing components and utilities
3. Follow the established patterns
4. Add constants to `config/constants.py`
5. Update imports in main app file

## Running Tests

Once tests are created:

```bash
# Run tests for specific modules
pytest tests/test_data_loader.py
pytest tests/test_visualizations.py

# Run all tests with coverage
pytest --cov=streamlit_components
```

## Deployment

The modular structure is deployment-ready:

```bash
# The same command works for both versions
streamlit run streamlit_app_modular.py

# Or use the original during transition
streamlit run streamlit_app.py
```

## Troubleshooting

Common issues and solutions:

1. **Import Errors**: Ensure you're running from the project root
2. **Data Not Found**: Check data file paths in constants.py
3. **Cache Issues**: Clear cache with `st.cache_data.clear()`
4. **Performance**: Monitor with `streamlit run --logger.level=debug`

## Resources

- [Streamlit Multipage Apps Documentation](https://docs.streamlit.io/develop/concepts/multipage-apps)
- [Streamlit Best Practices](https://docs.streamlit.io/develop/concepts/architecture)
- [Component Development](https://docs.streamlit.io/develop/concepts/custom-components)