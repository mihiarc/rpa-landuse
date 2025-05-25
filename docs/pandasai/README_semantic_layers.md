# RPA Land Use Viewer - Semantic Layers Implementation

This documentation explains how to use the semantic layers implementation for the RPA Land Use Viewer project. The semantic layers allow you to query the land use transition data using natural language through PandasAI.

## Prerequisites

- Python 3.12 (compatible with 3.8+)
- Python package manager (pip)
- OpenAI API key (Sign up at [openai.com](https://openai.com/))

## Setup

1. The easiest way to set up the environment is using the provided script:
   ```bash
   ./setup_venv.sh
   ```
   This script will:
   - Create a virtual environment with pip
   - Install all required dependencies
   - Configure the environment for Python 3.12 compatibility

2. Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   **IMPORTANT**: PandasAI 2.4.2 requires a standard OpenAI API key format that starts with "sk-". If you're using a different API key format (like Anthropic's "sk-ant-"), you'll need to obtain a standard OpenAI key.

3. Run the script to extract data and create semantic layers:
   ```bash
   python create_semantic_layers.py
   ```
   This script will:
   - Extract relevant data from the DuckDB database
   - Save it as Parquet files in a `land_use_parquet` directory
   - Create semantic layers in PandasAI

4. Run the example query script to see how to use the semantic layers:
   ```bash
   python query_semantic_layers.py
   ```

## Available Semantic Layers

The system creates three SmartDataframes that function as semantic layers:

1. **transitions** - Land Use Transitions Dataset
   - Aggregated land use transition data across scenarios and time periods
   - Includes scenario details, time periods, and transition areas

2. **county** - County Land Use Transitions Dataset
   - County-level land use transition data
   - Includes county details, scenario information, and transition areas

3. **urbanization** - Urbanization Trends Dataset
   - Time series data of conversion to urban land use by scenario
   - Focuses on forest, cropland, and pasture conversion to urban areas

## Example Queries

Here are some example natural language queries you can use:

- "Which scenario shows the most conversion from Forest to Urban land?"
- "Which county shows the highest agricultural land conversion to urban areas?"
- "Create a bar chart showing the top 5 scenarios with highest forest to urban conversion"
- "Compare Forest to Urban conversion across different time periods"

## Custom Queries

You can use PandasAI SmartDataframe to create your own natural language queries. Here's a simple example:

```python
import os
from dotenv import load_dotenv
import pandas as pd
from pandasai import SmartDataframe
from pandasai.llm import OpenAI

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the LLM
llm = OpenAI(api_token=api_key)

# Load your dataset from parquet
transitions_df = pd.read_parquet("land_use_parquet/transitions_summary.parquet")

# Create a SmartDataframe
smart_df = SmartDataframe(transitions_df, config={"llm": llm})

# Ask your question
response = smart_df.chat("Your natural language query here")
print(response)
```

## Troubleshooting

- **API Key Issues**: PandasAI 2.4.2 requires a standard OpenAI API key. The key:
  - Must start with "sk-" (standard OpenAI format)
  - Cannot be an Anthropic Claude API key (starts with "sk-ant-")
  - Cannot be an Azure OpenAI key

- **Python 3.12 Compatibility**: If you see Python 3.12 compatibility issues, ensure you're using numpy>=1.25.0 and pandas==1.5.3

- **PandasAI API Changes**: If you get errors about the pandasai API, check that you're using the correct API for version 2.4.2. The library has undergone significant API changes between versions.

- **Alternative LLMs**: If you want to use a different LLM provider with PandasAI:
  1. Check that pandasai 2.4.2 supports your chosen LLM
  2. Update the `src/pandasai/query.py` and `src/pandasai/layers.py` files to use the appropriate LLM class
  3. Modify the environment variable handling to match your LLM's requirements

- For more help with PandasAI, visit their [documentation](https://docs.pandasai.com/) 