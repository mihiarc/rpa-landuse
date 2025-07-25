# Jupyter Notebook Examples

Interactive Jupyter notebooks for exploring land use data with the LangChain agent.

## Overview

Jupyter notebooks provide an interactive environment for data exploration, visualization, and analysis. This page contains example notebooks demonstrating various use cases.

## Getting Started with Notebooks

### Setup

```bash
# Install Jupyter
uv pip install jupyter ipykernel

# Create kernel for this project
uv run python -m ipykernel install --name langchain-landuse --user

# Start Jupyter
uv run jupyter notebook
```

## Example Notebooks

### 1. Basic Agent Interaction

**Notebook:** `01_basic_agent_usage.ipynb`

```python
# Cell 1: Setup
from scripts.agents.data_engineering_agent import DataEngineeringAgent
import pandas as pd
from rich.console import Console

console = Console()
agent = DataEngineeringAgent()

# Cell 2: Basic Query
result = agent.run("Show me all tables in landuse_transitions.db")
print(result)

# Cell 3: Explore Schema
result = agent.run("Describe the landuse_transitions table")
print(result)

# Cell 4: Simple Analysis
result = agent.run("What are the total land areas by type in 2050?")
print(result)
```

### 2. Land Use Transition Analysis

**Notebook:** `02_transition_analysis.ipynb`

```python
# Cell 1: Import and Setup
from scripts.agents.data_engineering_agent import DataEngineeringAgent
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

agent = DataEngineeringAgent()

# Cell 2: Query Transition Data
query = """
Query processed/landuse_transitions.db:
SELECT from_land_use, to_land_use, SUM(area_1000_acres) as total_area
FROM landuse_transitions
WHERE scenario = 'Baseline' AND year = 2050
GROUP BY from_land_use, to_land_use
ORDER BY total_area DESC
"""
result = agent.run(query)

# Cell 3: Parse Results to DataFrame
# Extract data from agent response
# This would need parsing logic based on agent output format

# Cell 4: Create Transition Matrix Visualization
# Create pivot table
transition_matrix = df.pivot(
    index='from_land_use', 
    columns='to_land_use', 
    values='total_area'
)

# Heatmap
plt.figure(figsize=(10, 8))
sns.heatmap(transition_matrix, annot=True, fmt='.0f', cmap='YlOrRd')
plt.title('Land Use Transition Matrix (1000 acres)')
plt.xlabel('To Land Use')
plt.ylabel('From Land Use')
plt.show()
```

### 3. Scenario Comparison

**Notebook:** `03_scenario_comparison.ipynb`

```python
# Cell 1: Setup
from scripts.agents.data_engineering_agent import DataEngineeringAgent
import pandas as pd
import matplotlib.pyplot as plt

agent = DataEngineeringAgent()
scenarios = ['Baseline', 'High Crop Demand', 'High Forest', 'High Urban']

# Cell 2: Query Multiple Scenarios
results = {}
for scenario in scenarios:
    query = f"""
    Query processed/landuse_transitions.db:
    SELECT year, to_land_use, SUM(area_1000_acres) as area
    FROM landuse_transitions
    WHERE scenario = '{scenario}' 
      AND from_land_use = to_land_use
      AND to_land_use != 'Total'
    GROUP BY year, to_land_use
    """
    results[scenario] = agent.run(query)

# Cell 3: Process and Visualize
# Parse results into DataFrames
# Create multi-panel plot
fig, axes = plt.subplots(2, 2, figsize=(15, 12))
axes = axes.flatten()

for idx, scenario in enumerate(scenarios):
    ax = axes[idx]
    # Plot logic here
    ax.set_title(f'{scenario} Scenario')
    ax.set_xlabel('Year')
    ax.set_ylabel('Area (1000 acres)')
    ax.legend()

plt.tight_layout()
plt.show()
```

### 4. Geographic Analysis

**Notebook:** `04_geographic_patterns.ipynb`

```python
# Cell 1: Setup with Geospatial Libraries
from scripts.agents.data_engineering_agent import DataEngineeringAgent
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

agent = DataEngineeringAgent()

# Cell 2: Query County-Level Changes
query = """
Query processed/landuse_transitions.db:
SELECT fips, 
       SUM(CASE WHEN to_land_use = 'Urban' THEN area_1000_acres ELSE 0 END) -
       SUM(CASE WHEN from_land_use = 'Urban' THEN area_1000_acres ELSE 0 END) as urban_change
FROM landuse_transitions
WHERE scenario = 'Baseline' AND year = 2050
GROUP BY fips
"""
result = agent.run(query)

# Cell 3: Load County Boundaries
# Assuming you have county shapefiles
counties = gpd.read_file('data/counties.shp')

# Cell 4: Create Choropleth Map
fig, ax = plt.subplots(1, 1, figsize=(15, 10))

# Merge data with geometries
# Create map
counties.plot(
    column='urban_change',
    ax=ax,
    legend=True,
    cmap='RdYlBu_r',
    legend_kwds={'label': 'Urban Change (1000 acres)'}
)

ax.set_title('Urban Land Change by County (2020-2050)', fontsize=16)
ax.axis('off')
plt.show()
```

### 5. Time Series Analysis

**Notebook:** `05_time_series.ipynb`

```python
# Cell 1: Setup
from scripts.agents.data_engineering_agent import DataEngineeringAgent
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from IPython.display import HTML

agent = DataEngineeringAgent()

# Cell 2: Query Time Series Data
query = """
Query processed/landuse_transitions.db:
SELECT year, to_land_use, SUM(area_1000_acres) as total_area
FROM landuse_transitions
WHERE scenario = 'Baseline' 
  AND from_land_use = to_land_use
  AND to_land_use IN ('Crop', 'Forest', 'Urban', 'Pasture')
GROUP BY year, to_land_use
ORDER BY year, to_land_use
"""
result = agent.run(query)

# Cell 3: Create Animated Visualization
# Parse data
# Create animation showing land use change over time

# Cell 4: Trend Analysis
# Calculate growth rates
# Fit trend lines
# Project future values
```

### 6. Natural Language Query Explorer

**Notebook:** `06_query_explorer.ipynb`

```python
# Cell 1: Interactive Query Interface
from scripts.agents.data_engineering_agent import DataEngineeringAgent
from ipywidgets import interact, widgets
from IPython.display import display, HTML

agent = DataEngineeringAgent()

# Cell 2: Create Query Widget
query_input = widgets.Textarea(
    value='Show me forest loss by decade',
    placeholder='Enter your natural language query',
    description='Query:',
    layout=widgets.Layout(width='100%', height='100px')
)

output = widgets.Output()

def run_query(b):
    with output:
        output.clear_output()
        print(f"Running: {query_input.value}")
        result = agent.run(query_input.value)
        print("\nResult:")
        print(result)

button = widgets.Button(description="Run Query")
button.on_click(run_query)

display(query_input, button, output)

# Cell 3: Query Templates
templates = {
    "Forest Analysis": "Show me counties with the most forest loss",
    "Urban Growth": "Which areas have the fastest urban expansion?",
    "Agricultural": "Compare crop and pasture changes over time",
    "Scenarios": "How do the different scenarios compare for urban growth?"
}

for name, query in templates.items():
    btn = widgets.Button(description=name)
    btn.on_click(lambda b, q=query: query_input.value.update(q))
    display(btn)
```

### 7. Statistical Analysis

**Notebook:** `07_statistical_analysis.ipynb`

```python
# Cell 1: Setup
from scripts.agents.data_engineering_agent import DataEngineeringAgent
import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm

agent = DataEngineeringAgent()

# Cell 2: Get Data for Statistical Analysis
# Query for correlations between land use changes

# Cell 3: Correlation Analysis
# Calculate correlation matrix
# Test for significant correlations

# Cell 4: Regression Analysis
# Predict urban growth based on other factors

# Cell 5: Statistical Tests
# Test hypothesis about land use changes
# ANOVA for scenario comparisons
```

## Best Practices for Notebooks

### 1. Organization

```python
# Clear section headers
# %% [markdown]
# # Section 1: Data Loading

# %% 
# Code for data loading

# %% [markdown]
# # Section 2: Analysis

# %%
# Analysis code
```

### 2. Reproducibility

```python
# Cell 1: Always set random seeds
import random
import numpy as np

random.seed(42)
np.random.seed(42)

# Cell 2: Document package versions
import sys
print(f"Python: {sys.version}")
print(f"Pandas: {pd.__version__}")
```

### 3. Error Handling

```python
# Wrap agent calls in try-except
try:
    result = agent.run(query)
    # Process result
except Exception as e:
    print(f"Query failed: {e}")
    # Handle error gracefully
```

### 4. Visualization Standards

```python
# Set consistent plot style
plt.style.use('seaborn-v0_8-darkgrid')

# Create reusable plot function
def plot_land_use_trends(data, title):
    fig, ax = plt.subplots(figsize=(12, 6))
    # Plotting logic
    ax.set_title(title, fontsize=16)
    ax.set_xlabel('Year')
    ax.set_ylabel('Area (1000 acres)')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    return fig
```

## Sharing Notebooks

### Export Options

```python
# Export to HTML
jupyter nbconvert --to html notebook.ipynb

# Export to PDF
jupyter nbconvert --to pdf notebook.ipynb

# Export to Python script
jupyter nbconvert --to python notebook.ipynb
```

### Notebook Templates

Create template notebooks for common analyses:

1. `template_county_analysis.ipynb` - County-specific analysis
2. `template_scenario_comparison.ipynb` - Compare scenarios
3. `template_time_series.ipynb` - Temporal analysis
4. `template_visualization.ipynb` - Creating charts

## Interactive Dashboards

### Using Voila

```bash
# Install Voila
uv pip install voila

# Create dashboard from notebook
voila dashboard_notebook.ipynb
```

### Example Dashboard Code

```python
# Cell 1: Dashboard Setup
import ipywidgets as widgets
from IPython.display import display
import plotly.graph_objects as go

# Create controls
scenario_dropdown = widgets.Dropdown(
    options=['Baseline', 'High Crop Demand', 'High Forest', 'High Urban'],
    description='Scenario:'
)

year_slider = widgets.IntSlider(
    value=2050,
    min=2020,
    max=2100,
    step=10,
    description='Year:'
)

# Cell 2: Interactive Plot
@widgets.interact(scenario=scenario_dropdown, year=year_slider)
def update_plot(scenario, year):
    # Query data
    query = f"""
    Query processed/landuse_transitions.db:
    SELECT to_land_use, SUM(area_1000_acres) as area
    FROM landuse_transitions
    WHERE scenario = '{scenario}' AND year = {year}
    GROUP BY to_land_use
    """
    
    result = agent.run(query)
    # Parse and plot with Plotly
```

## Resources

### Example Notebook Repository

Find complete example notebooks at:
- GitHub: `examples/notebooks/`
- Each notebook includes:
  - Full code
  - Expected outputs
  - Explanations
  - Exercises

### Learning Resources

1. **Jupyter Documentation**: https://jupyter.org/documentation
2. **Pandas Tutorials**: For data manipulation
3. **Matplotlib Gallery**: For visualization ideas
4. **Geopandas Examples**: For geographic analysis

## Next Steps

- Download example notebooks from the repository
- Try modifying queries for your specific needs
- Create custom visualizations
- Share your notebooks with the community