"""
Shared fixtures for agent testing
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import pandas as pd
import duckdb


@pytest.fixture
def mock_anthropic_llm():
    """Mock Anthropic Claude LLM for testing"""
    mock = Mock()
    mock.model = "claude-3-5-sonnet-20241022"
    mock.temperature = 0.1
    mock.max_tokens = 2000
    
    # Default response for invoke
    mock.invoke.return_value = Mock(content="SELECT COUNT(*) FROM dim_scenario")
    
    return mock


@pytest.fixture
def mock_openai_llm():
    """Mock OpenAI GPT LLM for testing"""
    mock = Mock()
    mock.model = "gpt-4-turbo-preview"
    mock.temperature = 0.1
    mock.max_tokens = 4000
    
    # Default response for invoke
    mock.invoke.return_value = Mock(content="SELECT * FROM table LIMIT 10")
    
    return mock


@pytest.fixture
def mock_agent_executor():
    """Mock LangChain AgentExecutor"""
    mock = Mock()
    mock.invoke.return_value = {
        "input": "test query",
        "output": "Test response from agent"
    }
    return mock


@pytest.fixture
def sample_nl_queries():
    """Sample natural language queries for testing"""
    return {
        "agricultural": "How much agricultural land is being lost?",
        "forest": "Show me forest loss trends over time",
        "urban": "Which states have the most urban expansion?",
        "scenario": "Compare RCP45 and RCP85 scenarios",
        "geographic": "What are land use changes in California?",
        "temporal": "Show changes between 2020 and 2050",
        "complex": "Which scenarios show the most crop to urban conversion in the midwest between 2030 and 2060?"
    }


@pytest.fixture
def expected_sql_queries():
    """Expected SQL queries for natural language inputs"""
    return {
        "agricultural": """
            SELECT 
                AVG(f.acres) as avg_acres_lost_per_scenario,
                SUM(f.acres) as total_acres_lost
            FROM fact_landuse_transitions f
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE fl.landuse_category = 'Agriculture' 
              AND tl.landuse_category != 'Agriculture'
              AND f.transition_type = 'change'
        """,
        "forest": """
            SELECT 
                t.start_year,
                t.end_year,
                SUM(f.acres) as forest_loss
            FROM fact_landuse_transitions f
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            WHERE fl.landuse_name = 'Forest'
              AND f.transition_type = 'change'
            GROUP BY t.start_year, t.end_year
            ORDER BY t.start_year
        """
    }


@pytest.fixture
def mock_query_results():
    """Mock database query results"""
    return {
        "count": pd.DataFrame({"count": [5]}),
        "scenarios": pd.DataFrame({
            "scenario_name": ["CNRM_CM5_rcp45_ssp1", "CNRM_CM5_rcp85_ssp5"],
            "total_acres": [1000000, 1500000]
        }),
        "transitions": pd.DataFrame({
            "from_landuse": ["Crop", "Forest", "Pasture"],
            "to_landuse": ["Urban", "Urban", "Urban"],
            "acres": [50000, 30000, 20000]
        }),
        "time_series": pd.DataFrame({
            "year_range": ["2012-2020", "2020-2030", "2030-2040"],
            "acres_changed": [100000, 150000, 200000]
        })
    }


@pytest.fixture
def mock_file_operations():
    """Mock file operations for general data agent"""
    mock_files = {
        "data/test.csv": pd.DataFrame({
            "id": [1, 2, 3],
            "value": [10, 20, 30]
        }),
        "data/test.json": {"records": [{"id": 1}, {"id": 2}]},
        "data/test.parquet": pd.DataFrame({
            "category": ["A", "B", "A"],
            "amount": [100, 200, 150]
        })
    }
    
    def mock_read(file_path, *args, **kwargs):
        path = str(file_path)
        if path in mock_files:
            return mock_files[path]
        raise FileNotFoundError(f"Mock file not found: {path}")
    
    return mock_read, mock_files


@pytest.fixture
def mock_duckdb_operations():
    """Mock DuckDB operations"""
    class MockDuckDBConnection:
        def __init__(self):
            self.executed_queries = []
            
        def execute(self, query):
            self.executed_queries.append(query)
            
            # Return mock results based on query
            if "COUNT(*)" in query:
                return MockResult([(5,)])
            elif "SELECT * FROM" in query:
                return MockResult([
                    ("value1", "value2", "value3"),
                    ("value4", "value5", "value6")
                ])
            else:
                return MockResult([])
                
        def close(self):
            pass
            
        def df(self):
            return pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
    
    class MockResult:
        def __init__(self, data):
            self.data = data
            
        def fetchone(self):
            return self.data[0] if self.data else None
            
        def fetchall(self):
            return self.data
            
        def df(self):
            if not self.data:
                return pd.DataFrame()
            return pd.DataFrame(self.data)
    
    return MockDuckDBConnection


@pytest.fixture
def agent_test_config():
    """Test configuration for agents"""
    return {
        "database_path": "tests/fixtures/test_landuse.duckdb",
        "openai_api_key": "test-key-1234567890",
        "anthropic_api_key": "test-ant-key-1234567890",
        "temperature": 0.1,
        "max_tokens": 1000,
        "max_query_limit": 100,
        "rate_limit_calls": 60,
        "rate_limit_window": 60
    }


@pytest.fixture
def mock_rich_console():
    """Mock Rich console for testing output"""
    mock = Mock()
    mock.print = Mock()
    mock.input = Mock(return_value="test input")
    mock.status = Mock()
    return mock


@pytest.fixture
def sample_agent_responses():
    """Sample responses from agents for testing"""
    return {
        "landuse_success": """
🦆 **DuckDB Query Results** (3 rows)
**SQL:** `SELECT scenario_name, SUM(acres) FROM fact_landuse_transitions GROUP BY scenario_name LIMIT 3`

**Results:**
scenario_name           total_acres
CNRM_CM5_rcp45_ssp1    1,234,567
CNRM_CM5_rcp85_ssp5    2,345,678
GFDL_ESM4_rcp45_ssp2   1,567,890

📊 **Summary Statistics:**
Mean: 1,716,045 acres
Std: 571,994 acres
""",
        "general_success": """
Query executed successfully.
Results: 5 rows returned
Table: test_data
Columns: id, name, value
""",
        "error_response": "❌ Error executing query: Table not found",
        "security_blocked": "❌ Security Error: Dangerous keyword 'DROP' not allowed"
    }


@pytest.fixture
def mock_langchain_tools():
    """Mock LangChain tools for agents"""
    tools = []
    
    # Mock execute query tool
    execute_tool = Mock()
    execute_tool.name = "execute_query"
    execute_tool.func = Mock(return_value="Query executed successfully")
    tools.append(execute_tool)
    
    # Mock schema info tool
    schema_tool = Mock()
    schema_tool.name = "get_schema_info"
    schema_tool.func = Mock(return_value="Database schema information")
    tools.append(schema_tool)
    
    return tools