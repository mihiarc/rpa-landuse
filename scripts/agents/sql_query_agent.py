"""
SQL Query Agent for Local Database Analysis
This agent specializes in SQL querying and database analysis for your project.
Focuses on SQLite databases with support for data files (CSV, JSON, Parquet) via SQL queries.
"""

import os
import json
import pandas as pd
import geopandas as gpd
import sqlite3
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, validator

from dotenv import load_dotenv
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import FileManagementToolkit
from langchain_core.tools import Tool
from langchain.prompts import PromptTemplate
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables from config directory
env_path = Path(__file__).parent.parent.parent / "config" / ".env"
load_dotenv(dotenv_path=env_path)

class FileQueryParams(BaseModel):
    """Parameters for file-based SQL queries"""
    file_path: str = Field(..., description="Path to the file")
    query: str = Field(..., description="SQL query to execute")

class DatabaseQueryParams(BaseModel):
    """Parameters for database SQL queries"""
    db_path: str = Field(..., description="Path to the database file")
    query: str = Field(..., description="SQL query to execute")
    limit: Optional[int] = Field(1000, description="Maximum number of rows to return")

class DatabaseExportParams(BaseModel):
    """Parameters for exporting database query results"""
    db_path: str = Field(..., description="Path to the database file")
    table_name: str = Field(..., description="Table name to export")
    output_path: str = Field(..., description="Output file path")
    output_format: str = Field(default="csv", description="Output format: csv, json, parquet")
    where_clause: Optional[str] = Field(None, description="Optional WHERE clause for filtering")
    limit: Optional[int] = Field(None, description="Optional limit on number of rows")

class VisualizationParams(BaseModel):
    """Parameters for creating visualizations from SQL results"""
    file_path: str = Field(..., description="Path to the file")
    plot_type: str = Field(default="scatter", description="Type of plot")
    x: Optional[str] = Field(None, description="X-axis column")
    y: Optional[str] = Field(None, description="Y-axis column")

class TransformParams(BaseModel):
    """Parameters for data transformation via SQL"""
    input_path: str = Field(..., description="Input file path")
    output_path: str = Field(..., description="Output file path")
    output_format: str = Field(..., description="Output format: parquet, csv, json, geoparquet")
    compression: Optional[str] = Field(None, description="Compression type: gzip, snappy, brotli")
    
    @validator('output_format')
    def validate_format(cls, v):
        valid_formats = ['parquet', 'csv', 'json', 'geoparquet']
        if v not in valid_formats:
            raise ValueError(f"Format must be one of {valid_formats}")
        return v

class SQLQueryAgent:
    """Agent specialized in SQL querying and database analysis"""
    
    def __init__(self, root_dir: str = None):
        """
        Initialize the SQL Query Agent
        
        Args:
            root_dir: Root directory for file operations (defaults to PROJECT_ROOT_DIR from .env)
        """
        self.root_dir = root_dir or os.getenv("PROJECT_ROOT_DIR", "./data")
        self.llm = ChatOpenAI(
            model=os.getenv("AGENT_MODEL", "gpt-4-turbo-preview"),
            temperature=float(os.getenv("TEMPERATURE", "0.1")),
            max_tokens=int(os.getenv("MAX_TOKENS", "4000"))
        )
        self.memory = MemorySaver()
        self.tools = self._create_tools()
        self.agent = self._create_agent()
        
    def _create_tools(self) -> List[Tool]:
        """Create SQL-focused tools for the agent"""
        tools = []
        
        # File management tools (for database file operations)
        file_toolkit = FileManagementToolkit(root_dir=self.root_dir)
        tools.extend(file_toolkit.get_tools())
        
        # SQL-focused tools
        tools.extend([
            # Database Schema & Structure Tools
            Tool(
                name="list_database_tables",
                func=self._list_database_tables,
                description="🗂️ List all tables in a SQLite database with row counts. Input: db_path"
            ),
            Tool(
                name="describe_database_table",
                func=self._describe_database_table,
                description="📋 Get detailed schema, indexes, and sample data for a database table. Input: {'db_path': 'path', 'table_name': 'table'}"
            ),
            Tool(
                name="database_statistics",
                func=self._database_statistics,
                description="📊 Get comprehensive database statistics (size, tables, rows, etc.). Input: db_path"
            ),
            
            # SQL Query Tools
            Tool(
                name="query_database",
                func=self._query_database,
                description="🔍 Execute SQL queries on SQLite databases. Input: {'db_path': 'path', 'query': 'SQL query', 'limit': 1000}"
            ),
            Tool(
                name="query_data_file",
                func=self._query_data,
                description="📄 Query data files (CSV, JSON, Parquet) using SQL. Input: {'file_path': 'path', 'query': 'SQL query'}"
            ),
            
            # Data Export & Analysis Tools
            Tool(
                name="export_query_results",
                func=self._export_database_table,
                description="💾 Export SQL query results to files. Input: {'db_path': 'path', 'table_name': 'table', 'output_path': 'path', 'output_format': 'csv', 'where_clause': 'optional', 'limit': 'optional'}"
            ),
            Tool(
                name="analyze_data_file",
                func=self._analyze_dataframe,
                description="📈 Analyze data files and get statistical summaries. Input: file_path"
            ),
            
            # File Reading Tools (for SQL context)
            Tool(
                name="read_csv_info",
                func=self._read_csv,
                description="📊 Read CSV file structure and preview data. Input: file_path"
            ),
            Tool(
                name="read_json_info",
                func=self._read_json,
                description="🔧 Read JSON file structure and preview data. Input: file_path"
            ),
            Tool(
                name="read_parquet_info",
                func=self._read_parquet,
                description="⚡ Read Parquet file structure and preview data. Input: file_path"
            ),
            
            # Data Transformation Tools
            Tool(
                name="transform_data",
                func=self._transform_data,
                description="🔄 Transform data between formats (CSV, JSON, Parquet). Input: {'input_path': 'path', 'output_path': 'path', 'output_format': 'format', 'compression': 'optional'}"
            ),
            Tool(
                name="json_to_database",
                func=self._json_to_database,
                description="🗄️ Convert JSON files to SQLite database for efficient querying. Input: {'json_path': 'path', 'db_path': 'output.db', 'table_name': 'data', 'chunk_size': 10000}"
            ),
            
            # Visualization Tools
            Tool(
                name="create_chart",
                func=self._create_visualization,
                description="📊 Create charts from data files. Input: {'file_path': 'path', 'plot_type': 'type', 'x': 'column', 'y': 'column'}"
            ),
            Tool(
                name="optimize_storage",
                func=self._optimize_storage,
                description="⚡ Analyze and suggest optimal storage format for data. Input: file_path"
            )
        ])
        
        return tools
    
    def _read_csv(self, file_path: str) -> str:
        """Read CSV file and return basic information"""
        try:
            full_path = Path(self.root_dir) / file_path
            df = pd.read_csv(full_path)
            return self._get_dataframe_info(df)
        except Exception as e:
            return f"Error reading CSV: {str(e)}"
    
    def _read_excel(self, file_path: str) -> str:
        """Read Excel file and return basic information"""
        try:
            full_path = Path(self.root_dir) / file_path
            df = pd.read_excel(full_path)
            return self._get_dataframe_info(df)
        except Exception as e:
            return f"Error reading Excel: {str(e)}"
    
    def _read_json(self, file_path: str) -> str:
        """Read JSON file and return basic information"""
        try:
            full_path = Path(self.root_dir) / file_path
            
            # Check file size first
            file_size_mb = full_path.stat().st_size / (1024 * 1024)
            max_size_mb = float(os.getenv("MAX_FILE_SIZE_MB", "100"))
            
            if file_size_mb > max_size_mb:
                # For large files, read only a sample
                import ijson
                
                sample_rows = []
                with open(full_path, 'rb') as f:
                    parser = ijson.items(f, 'item')
                    for i, item in enumerate(parser):
                        if i < 1000:  # Read first 1000 items
                            sample_rows.append(item)
                        else:
                            break
                
                df = pd.DataFrame(sample_rows)
                info = self._get_dataframe_info(df)
                return f"LARGE FILE ({file_size_mb:.2f} MB) - Showing sample of first 1000 rows\n{info}"
            else:
                # Try different JSON reading strategies for smaller files
                try:
                    # Try reading as JSON records
                    df = pd.read_json(full_path, orient='records')
                    return self._get_dataframe_info(df)
                except:
                    # Try reading as regular JSON
                    with open(full_path, 'r') as f:
                        data = json.load(f)
                    
                    if isinstance(data, list):
                        df = pd.DataFrame(data)
                        return self._get_dataframe_info(df)
                    else:
                        return f"JSON Structure:\nType: {type(data)}\nKeys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}\nPreview: {str(data)[:500]}..."
                    
        except Exception as e:
            return f"Error reading JSON: {str(e)}"
    
    def _read_parquet(self, file_path: str) -> str:
        """Read Parquet file and return basic information"""
        try:
            full_path = Path(self.root_dir) / file_path
            df = pd.read_parquet(full_path)
            return self._get_dataframe_info(df)
        except Exception as e:
            return f"Error reading Parquet: {str(e)}"
    
    def _read_geoparquet(self, file_path: str) -> str:
        """Read GeoParquet file and return GeoDataFrame information"""
        try:
            full_path = Path(self.root_dir) / file_path
            gdf = gpd.read_parquet(full_path)
            
            info = self._get_dataframe_info(gdf)
            
            # Add geometry-specific information
            geo_info = f"""
            
            Geometry Information:
            CRS: {gdf.crs}
            Geometry Type: {gdf.geometry.type.value_counts().to_dict()}
            Total Bounds: {gdf.total_bounds}
            """
            
            return info + geo_info
            
        except Exception as e:
            return f"Error reading GeoParquet: {str(e)}"
    
    def _get_dataframe_info(self, df: Union[pd.DataFrame, gpd.GeoDataFrame]) -> str:
        """Get information about a DataFrame"""
        info = f"""
        Shape: {df.shape}
        Columns: {list(df.columns)}
        Data Types: {df.dtypes.to_dict()}
        Missing Values: {df.isnull().sum().to_dict()}
        Memory Usage: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB
        
        First 5 rows:
        {df.head().to_string()}
        
        Basic Statistics:
        {df.describe().to_string() if len(df.select_dtypes(include=['number']).columns) > 0 else 'No numeric columns'}
        """
        return info
    
    def _analyze_dataframe(self, file_path: str) -> str:
        """Perform detailed analysis on a dataframe"""
        try:
            full_path = Path(self.root_dir) / file_path
            
            # Determine file type and read
            if file_path.endswith('.csv'):
                df = pd.read_csv(full_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(full_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(full_path)
            elif file_path.endswith('.parquet'):
                if 'geo' in file_path.lower():
                    df = gpd.read_parquet(full_path)
                else:
                    df = pd.read_parquet(full_path)
            else:
                return "Unsupported file type. Please use CSV, Excel, JSON, Parquet, or GeoParquet files."
            
            analysis = {
                "shape": df.shape,
                "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024**2,
                "duplicate_rows": df.duplicated().sum(),
                "column_analysis": {}
            }
            
            for col in df.columns:
                if col == 'geometry' and isinstance(df, gpd.GeoDataFrame):
                    col_info = {
                        "dtype": "geometry",
                        "null_count": df[col].isnull().sum(),
                        "geometry_types": df[col].type.value_counts().to_dict()
                    }
                else:
                    col_info = {
                        "dtype": str(df[col].dtype),
                        "null_count": df[col].isnull().sum(),
                        "null_percentage": (df[col].isnull().sum() / len(df)) * 100,
                        "unique_values": df[col].nunique(),
                        "cardinality": df[col].nunique() / len(df) if len(df) > 0 else 0
                    }
                    
                    if pd.api.types.is_numeric_dtype(df[col]):
                        col_info.update({
                            "mean": float(df[col].mean()),
                            "std": float(df[col].std()),
                            "min": float(df[col].min()),
                            "max": float(df[col].max())
                        })
                
                analysis["column_analysis"][col] = col_info
            
            return json.dumps(analysis, indent=2)
            
        except Exception as e:
            return f"Error analyzing dataframe: {str(e)}"
    
    def _query_data(self, params: Union[Dict[str, str], str]) -> str:
        """Query data using SQL"""
        try:
            import duckdb
            
            # Handle both dict and string inputs
            if isinstance(params, str):
                # Try to parse as JSON
                try:
                    params = json.loads(params)
                except:
                    return "Error: Invalid input format. Expected JSON with 'file_path' and 'query' keys"
            
            validated_params = FileQueryParams(**params)
            file_path = validated_params.file_path
            query = validated_params.query
            
            full_path = Path(self.root_dir) / file_path
            
            # Create DuckDB connection
            conn = duckdb.connect(':memory:')
            
            # Install and load spatial extension for GeoParquet
            if file_path.endswith('.geoparquet') or 'geo' in file_path.lower():
                conn.execute("INSTALL spatial")
                conn.execute("LOAD spatial")
            
            # Load data based on file type
            if file_path.endswith('.csv'):
                conn.execute(f"CREATE TABLE data AS SELECT * FROM read_csv_auto('{full_path}')")
            elif file_path.endswith('.parquet'):
                conn.execute(f"CREATE TABLE data AS SELECT * FROM read_parquet('{full_path}')")
            elif file_path.endswith('.json'):
                conn.execute(f"CREATE TABLE data AS SELECT * FROM read_json_auto('{full_path}')")
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(full_path)
                conn.register('data', df)
            else:
                return "Unsupported file type for SQL queries"
            
            # Execute query
            result = conn.execute(query).fetchdf()
            conn.close()
            
            return f"Query Result ({len(result)} rows):\n{result.to_string()}"
            
        except Exception as e:
            return f"Error executing query: {str(e)}"
    
    def _transform_data(self, params: Union[Dict[str, str], str]) -> str:
        """Transform data between different formats"""
        try:
            # Handle both dict and string inputs
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    return "Error: Invalid input format. Expected JSON with transformation parameters"
            
            validated_params = TransformParams(**params)
            
            input_path = Path(self.root_dir) / validated_params.input_path
            output_path = Path(self.root_dir) / validated_params.output_path
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read input data
            if validated_params.input_path.endswith('.csv'):
                df = pd.read_csv(input_path)
            elif validated_params.input_path.endswith('.json'):
                df = pd.read_json(input_path)
            elif validated_params.input_path.endswith('.parquet'):
                if 'geo' in validated_params.input_path.lower():
                    df = gpd.read_parquet(input_path)
                else:
                    df = pd.read_parquet(input_path)
            elif validated_params.input_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(input_path)
            else:
                return "Unsupported input file format"
            
            # Write output data
            if validated_params.output_format == 'parquet':
                df.to_parquet(output_path, compression=validated_params.compression)
            elif validated_params.output_format == 'csv':
                df.to_csv(output_path, index=False)
            elif validated_params.output_format == 'json':
                df.to_json(output_path, orient='records', indent=2)
            elif validated_params.output_format == 'geoparquet':
                if isinstance(df, gpd.GeoDataFrame):
                    df.to_parquet(output_path, compression=validated_params.compression)
                else:
                    return "Cannot convert non-spatial data to GeoParquet"
            
            # Get file sizes
            input_size = input_path.stat().st_size / 1024**2  # MB
            output_size = output_path.stat().st_size / 1024**2  # MB
            
            return f"""
            Transformation completed successfully!
            Input: {validated_params.input_path} ({input_size:.2f} MB)
            Output: {validated_params.output_path} ({output_size:.2f} MB)
            Format: {validated_params.output_format}
            Compression: {validated_params.compression or 'None'}
            Size reduction: {((input_size - output_size) / input_size * 100):.1f}%
            """
            
        except Exception as e:
            return f"Error transforming data: {str(e)}"
    
    def _optimize_storage(self, file_path: str) -> str:
        """Analyze data and suggest optimal storage format"""
        try:
            full_path = Path(self.root_dir) / file_path
            
            # Read the file
            if file_path.endswith('.csv'):
                df = pd.read_csv(full_path)
            elif file_path.endswith('.json'):
                df = pd.read_json(full_path)
            elif file_path.endswith('.parquet'):
                df = pd.read_parquet(full_path)
            elif file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(full_path)
            else:
                return "Unsupported file type"
            
            # Analyze characteristics
            analysis = {
                "current_format": file_path.split('.')[-1],
                "current_size_mb": full_path.stat().st_size / 1024**2,
                "rows": len(df),
                "columns": len(df.columns),
                "numeric_columns": len(df.select_dtypes(include=['number']).columns),
                "string_columns": len(df.select_dtypes(include=['object']).columns),
                "has_datetime": any(pd.api.types.is_datetime64_any_dtype(df[col]) for col in df.columns),
                "has_geometry": 'geometry' in df.columns,
                "compression_ratio": len(df.columns) / df.memory_usage(deep=True).sum() * 1000000
            }
            
            # Recommendations
            recommendations = []
            
            if analysis["current_format"] != "parquet":
                recommendations.append({
                    "format": "parquet",
                    "reason": "Best for analytics with columnar storage and compression",
                    "estimated_size_reduction": "60-80%"
                })
            
            if analysis["has_geometry"]:
                recommendations.append({
                    "format": "geoparquet",
                    "reason": "Optimized for spatial data with geometry support",
                    "estimated_size_reduction": "50-70%"
                })
            
            if analysis["rows"] < 10000 and analysis["compression_ratio"] < 0.5:
                recommendations.append({
                    "format": "csv",
                    "reason": "Small dataset, human-readable format sufficient",
                    "estimated_size_reduction": "0%"
                })
            
            if analysis["numeric_columns"] > analysis["string_columns"] * 2:
                recommendations.append({
                    "format": "parquet with snappy",
                    "reason": "Numeric-heavy data benefits from fast compression",
                    "estimated_size_reduction": "70-85%"
                })
            
            return f"""
            Storage Optimization Analysis:
            
            Current Status:
            {json.dumps(analysis, indent=2)}
            
            Recommendations:
            {json.dumps(recommendations, indent=2)}
            
            To implement: use transform_data tool with suggested format
            """
            
        except Exception as e:
            return f"Error analyzing storage: {str(e)}"
    
    def _create_visualization(self, params: Union[Dict[str, str], str]) -> str:
        """Create data visualizations"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            # Handle both dict and string inputs
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    return "Error: Invalid input format"
            
            validated_params = VisualizationParams(**params)
            
            full_path = Path(self.root_dir) / validated_params.file_path
            
            # Read data
            if validated_params.file_path.endswith('.csv'):
                df = pd.read_csv(full_path)
            elif validated_params.file_path.endswith('.parquet'):
                df = pd.read_parquet(full_path)
            elif validated_params.file_path.endswith('.json'):
                df = pd.read_json(full_path)
            elif validated_params.file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(full_path)
            else:
                return "Unsupported file type"
            
            # Create visualization
            plt.figure(figsize=(10, 6))
            
            if validated_params.plot_type == 'scatter' and validated_params.x and validated_params.y:
                plt.scatter(df[validated_params.x], df[validated_params.y])
                plt.xlabel(validated_params.x)
                plt.ylabel(validated_params.y)
            elif validated_params.plot_type == 'line' and validated_params.x and validated_params.y:
                plt.plot(df[validated_params.x], df[validated_params.y])
                plt.xlabel(validated_params.x)
                plt.ylabel(validated_params.y)
            elif validated_params.plot_type == 'histogram' and validated_params.x:
                plt.hist(df[validated_params.x], bins=30)
                plt.xlabel(validated_params.x)
                plt.ylabel('Frequency')
            elif validated_params.plot_type == 'correlation':
                numeric_df = df.select_dtypes(include=['float64', 'int64'])
                sns.heatmap(numeric_df.corr(), annot=True, cmap='coolwarm')
            else:
                return "Invalid plot type or missing parameters"
            
            plt.title(f"{validated_params.plot_type.capitalize()} Plot")
            plt.tight_layout()
            
            # Save plot
            output_path = Path(self.root_dir) / f"{validated_params.plot_type}_plot.png"
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return f"Visualization saved to: {output_path}"
            
        except Exception as e:
            return f"Error creating visualization: {str(e)}"
    
    def _json_to_database(self, params: Union[Dict[str, Any], str]) -> str:
        """Convert large JSON files to database format efficiently"""
        try:
            import sqlite3
            import ijson
            
            # Handle both dict and string inputs
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    return "Error: Invalid input format. Expected JSON with parameters"
            
            json_path = params.get('json_path')
            db_path = params.get('db_path', 'output.db')
            table_name = params.get('table_name', 'data')
            chunk_size = params.get('chunk_size', 10000)
            
            if not json_path:
                return "Error: json_path is required"
            
            full_json_path = Path(self.root_dir) / json_path
            full_db_path = Path(self.root_dir) / db_path
            
            # Get file size
            file_size_mb = full_json_path.stat().st_size / (1024 * 1024)
            
            # Create database connection
            conn = sqlite3.connect(full_db_path)
            cursor = conn.cursor()
            
            # Process JSON file in chunks
            from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn
            from rich.console import Console
            
            console = Console()
            
            with console.status(f"[bold green]Converting {json_path} ({file_size_mb:.2f} MB) to database...", spinner="dots") as status:
                # Read first item to determine schema
                with open(full_json_path, 'rb') as f:
                    parser = ijson.items(f, 'item')
                    first_item = next(parser)
                    
                    # Create table based on first item
                    columns = []
                    for key, value in first_item.items():
                        if isinstance(value, int):
                            columns.append(f"{key} INTEGER")
                        elif isinstance(value, float):
                            columns.append(f"{key} REAL")
                        else:
                            columns.append(f"{key} TEXT")
                    
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(columns)})"
                    cursor.execute(create_table_sql)
                
                # Process file in chunks
                with open(full_json_path, 'rb') as f:
                    parser = ijson.items(f, 'item')
                    
                    batch = []
                    total_rows = 0
                    
                    for item in parser:
                        batch.append(tuple(item.values()))
                        
                        if len(batch) >= chunk_size:
                            # Insert batch
                            placeholders = ', '.join(['?' for _ in first_item.keys()])
                            insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                            cursor.executemany(insert_sql, batch)
                            conn.commit()
                            
                            total_rows += len(batch)
                            status.update(f"[bold green]Processed {total_rows:,} rows...")
                            batch = []
                    
                    # Insert remaining items
                    if batch:
                        placeholders = ', '.join(['?' for _ in first_item.keys()])
                        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                        cursor.executemany(insert_sql, batch)
                        conn.commit()
                        total_rows += len(batch)
            
            # Create indexes on common columns
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 1")
            column_names = [description[0] for description in cursor.description]
            
            for col in ['id', 'date', 'timestamp', 'created_at', 'updated_at']:
                if col in column_names:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_{col} ON {table_name}({col})")
            
            conn.commit()
            conn.close()
            
            # Get database size
            db_size_mb = full_db_path.stat().st_size / (1024 * 1024)
            
            return f"""
            Successfully converted JSON to database!
            
            Source: {json_path} ({file_size_mb:.2f} MB)
            Output: {db_path} ({db_size_mb:.2f} MB)
            Table: {table_name}
            Rows: {total_rows:,}
            Compression: {((file_size_mb - db_size_mb) / file_size_mb * 100):.1f}%
            
            You can now query the data using SQL:
            Example: "Query {db_path}: SELECT COUNT(*) FROM {table_name}"
            """
            
        except Exception as e:
            return f"Error converting JSON to database: {str(e)}"
    
    def _list_database_tables(self, db_path: str) -> str:
        """List all tables in a SQLite database"""
        try:
            full_path = Path(self.root_dir) / db_path
            
            if not full_path.exists():
                return f"Database file not found: {db_path}"
            
            conn = sqlite3.connect(full_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = cursor.fetchall()
            
            if not tables:
                conn.close()
                return "No tables found in database"
            
            # Get row counts for each table
            table_info = []
            for (table_name,) in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                table_info.append(f"  • {table_name}: {row_count:,} rows")
            
            conn.close()
            
            return f"Database: {db_path}\nTables:\n" + "\n".join(table_info)
            
        except Exception as e:
            return f"Error listing database tables: {str(e)}"
    
    def _describe_database_table(self, params: Union[Dict[str, str], str]) -> str:
        """Get schema and information for a database table"""
        try:
            # Handle both dict and string inputs
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    return "Error: Invalid input format. Expected JSON with 'db_path' and 'table_name' keys"
            
            db_path = params.get('db_path')
            table_name = params.get('table_name')
            
            if not db_path or not table_name:
                return "Error: Both 'db_path' and 'table_name' are required"
            
            full_path = Path(self.root_dir) / db_path
            
            if not full_path.exists():
                return f"Database file not found: {db_path}"
            
            conn = sqlite3.connect(full_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                conn.close()
                return f"Table '{table_name}' not found in database"
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            
            # Get indexes
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            
            # Get sample data
            cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
            sample_data = cursor.fetchall()
            
            conn.close()
            
            # Format response
            schema_info = []
            for col in columns:
                col_info = f"  {col[1]} ({col[2]})"
                if col[3]:  # NOT NULL
                    col_info += " NOT NULL"
                if col[5]:  # PRIMARY KEY
                    col_info += " PRIMARY KEY"
                schema_info.append(col_info)
            
            index_info = [f"  • {idx[1]}" for idx in indexes if not idx[1].startswith('sqlite_')]
            
            result = f"""Table: {table_name}
Rows: {row_count:,}

Schema:
{chr(10).join(schema_info)}

Indexes:
{chr(10).join(index_info) if index_info else "  None"}

Sample Data (first 5 rows):
{chr(10).join([str(row) for row in sample_data[:5]])}"""
            
            return result
            
        except Exception as e:
            return f"Error describing table: {str(e)}"
    
    def _query_database(self, params: Union[Dict[str, str], str]) -> str:
        """Query a SQLite database using SQL"""
        try:
            # Handle both dict and string inputs
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    return "Error: Invalid input format. Expected JSON with 'db_path' and 'query' keys"
            
            validated_params = DatabaseQueryParams(**params)
            db_path = validated_params.db_path
            query = validated_params.query
            limit = validated_params.limit
            
            full_path = Path(self.root_dir) / db_path
            
            if not full_path.exists():
                return f"Database file not found: {db_path}"
            
            conn = sqlite3.connect(full_path)
            
            # Add LIMIT if not already in query and limit is specified
            if limit and 'LIMIT' not in query.upper():
                query = f"{query} LIMIT {limit}"
            
            # Execute query and get results as DataFrame for better formatting
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) == 0:
                return "Query returned no results"
            
            # Format response
            result = f"""Query: {query}
Results: {len(df):,} rows

{df.to_string(max_rows=50, max_cols=10)}"""
            
            if len(df) > 50:
                result += f"\n\n... (showing first 50 of {len(df):,} rows)"
            
            return result
            
        except Exception as e:
            return f"Error executing database query: {str(e)}"
    
    def _export_database_table(self, params: Union[Dict[str, str], str]) -> str:
        """Export database table to file"""
        try:
            # Handle both dict and string inputs
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    return "Error: Invalid input format. Expected JSON with required parameters"
            
            validated_params = DatabaseExportParams(**params)
            db_path = validated_params.db_path
            table_name = validated_params.table_name
            output_path = validated_params.output_path
            output_format = validated_params.output_format
            where_clause = validated_params.where_clause
            limit = validated_params.limit
            
            full_db_path = Path(self.root_dir) / db_path
            full_output_path = Path(self.root_dir) / output_path
            
            if not full_db_path.exists():
                return f"Database file not found: {db_path}"
            
            # Ensure output directory exists
            full_output_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(full_db_path)
            
            # Build query
            query = f"SELECT * FROM {table_name}"
            if where_clause:
                query += f" WHERE {where_clause}"
            if limit:
                query += f" LIMIT {limit}"
            
            # Execute query and get DataFrame
            df = pd.read_sql_query(query, conn)
            conn.close()
            
            if len(df) == 0:
                return "No data to export (query returned empty result)"
            
            # Export based on format
            if output_format == 'csv':
                df.to_csv(full_output_path, index=False)
            elif output_format == 'json':
                df.to_json(full_output_path, orient='records', indent=2)
            elif output_format == 'parquet':
                df.to_parquet(full_output_path, compression='snappy')
            else:
                return f"Unsupported output format: {output_format}"
            
            # Get file size
            output_size = full_output_path.stat().st_size / 1024**2  # MB
            
            return f"""Successfully exported {len(df):,} rows from table '{table_name}'
Output: {output_path} ({output_size:.2f} MB)
Format: {output_format}
Query: {query}"""
            
        except Exception as e:
            return f"Error exporting database table: {str(e)}"
    
    def _database_statistics(self, db_path: str) -> str:
        """Get comprehensive statistics about a database"""
        try:
            full_path = Path(self.root_dir) / db_path
            
            if not full_path.exists():
                return f"Database file not found: {db_path}"
            
            # Get file size
            file_size_mb = full_path.stat().st_size / (1024 * 1024)
            
            conn = sqlite3.connect(full_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                conn.close()
                return f"Database: {db_path}\nSize: {file_size_mb:.2f} MB\nNo user tables found"
            
            # Get statistics for each table
            table_stats = []
            total_rows = 0
            
            for table in tables:
                # Row count
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                total_rows += row_count
                
                # Column count
                cursor.execute(f"PRAGMA table_info({table})")
                col_count = len(cursor.fetchall())
                
                # Index count
                cursor.execute(f"PRAGMA index_list({table})")
                index_count = len([idx for idx in cursor.fetchall() if not idx[1].startswith('sqlite_')])
                
                table_stats.append(f"  • {table}: {row_count:,} rows, {col_count} columns, {index_count} indexes")
            
            # Get database schema version if available
            try:
                cursor.execute("PRAGMA user_version")
                schema_version = cursor.fetchone()[0]
            except:
                schema_version = "Unknown"
            
            conn.close()
            
            return f"""Database Statistics: {db_path}
File Size: {file_size_mb:.2f} MB
Schema Version: {schema_version}
Total Tables: {len(tables)}
Total Rows: {total_rows:,}

Table Details:
{chr(10).join(table_stats)}"""
            
        except Exception as e:
            return f"Error getting database statistics: {str(e)}"
    
    def _create_agent(self):
        """Create the SQL-focused agent with tools"""
        # Create agent prompt with required variables
        prompt = PromptTemplate.from_template("""Answer the following questions as best you can. You have access to the following tools:

{tools}

You are a SQL Query Agent specializing in database analysis and SQL querying.
You excel at exploring database schemas, writing efficient SQL queries, and analyzing data.
Current working directory: {root_dir}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

SQL Query Best Practices:
1. Always explore database schema first (list tables, describe structure)
2. Use appropriate LIMIT clauses for large datasets
3. Write efficient queries with proper WHERE clauses
4. Suggest indexes for performance optimization
5. Export results when analysis is complete

Begin!

Question: {input}
Thought:{agent_scratchpad}""")
        
        # Create the agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10
        )
        
        return agent_executor
    
    def run(self, query: str) -> str:
        """Run the agent with a query"""
        try:
            response = self.agent.invoke({
                "input": query,
                "root_dir": self.root_dir
            })
            return response.get("output", "No response generated")
        except Exception as e:
            return f"Error running agent: {str(e)}"
    
    def chat(self):
        """Interactive SQL query chat mode with rich terminal output"""
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        
        console = Console()
        
        console.print(Panel.fit(
            f"🔍 [bold cyan]SQL Query Agent[/bold cyan]\n[yellow]Database directory:[/yellow] {self.root_dir}",
            border_style="cyan"
        ))
        console.print("Type [bold red]'exit'[/bold red] to quit, [bold yellow]'help'[/bold yellow] for SQL commands\n")
        
        while True:
            user_input = console.input("[bold cyan]SQL>[/bold cyan] ").strip()
            
            if user_input.lower() == 'exit':
                console.print("\n[bold red]👋 Happy querying![/bold red]")
                break
            elif user_input.lower() == 'help':
                help_panel = Panel(
                    """[bold cyan]🔍 SQL Query Agent Capabilities:[/bold cyan]

[bold yellow]🗂️ Database Schema Exploration:[/bold yellow]
  • List all tables with row counts
  • Describe table structures, columns, indexes
  • Get comprehensive database statistics

[bold yellow]🔍 SQL Query Execution:[/bold yellow]
  • Execute SQL queries on SQLite databases
  • Query data files (CSV, JSON, Parquet) using SQL
  • Smart query optimization and suggestions

[bold yellow]💾 Data Export & Analysis:[/bold yellow]
  • Export query results to various formats
  • Statistical analysis of query results
  • Performance optimization recommendations

[bold yellow]🔧 Database Operations:[/bold yellow]
  • Convert JSON to SQLite for better querying
  • Transform data between formats
  • File structure analysis

[bold green]🚀 Example SQL Commands:[/bold green]
  • [white]"Show me all tables in landuse_transitions.db"[/white]
  • [white]"Describe the landuse_transitions table"[/white]
  • [white]"Query landuse_transitions.db: SELECT scenario, COUNT(*) FROM landuse_transitions GROUP BY scenario LIMIT 10"[/white]
  • [white]"Get database statistics for landuse_projections.db"[/white]
  • [white]"Export results WHERE scenario='Baseline' to CSV"[/white]
  • [white]"Find all tables with more than 1000 rows"[/white]
  • [white]"Show me the schema for all databases in processed/"[/white]

[bold blue]💡 Pro Tips:[/bold blue]
  • Always explore schema first with [italic]"list tables"[/italic]
  • Use LIMIT for large datasets
  • Try aggregate functions: COUNT, SUM, AVG, GROUP BY
""",
                    title="📚 SQL Query Help",
                    border_style="yellow"
                )
                console.print(help_panel)
            else:
                with console.status(f"[bold cyan]Executing SQL query...[/bold cyan]", spinner="dots"):
                    response = self.run(user_input)
                
                # Format response
                if "Error" in response:
                    console.print(Panel(response, title="❌ SQL Error", border_style="red"))
                else:
                    console.print(Panel(response, title="🔍 Query Results", border_style="green"))
                console.print()


if __name__ == "__main__":
    # Example usage
    agent = SQLQueryAgent()
    
    # You can run specific SQL queries
    # result = agent.run("Show me all tables in landuse_transitions.db")
    # print(result)
    
    # Or start interactive SQL chat
    agent.chat()