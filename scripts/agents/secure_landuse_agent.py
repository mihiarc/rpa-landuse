#!/usr/bin/env python3
"""
Secure Landuse Agent
Enhanced landuse analysis agent with comprehensive security features including
input validation, SQL injection prevention, rate limiting, and audit logging
"""

import os
import sys
import json
import duckdb
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

from dotenv import load_dotenv
from langchain.agents import create_react_agent, AgentExecutor
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain.prompts import PromptTemplate
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utilities.security import (
    SQLQueryValidator, InputValidator, RateLimiter, 
    SecureConfig, SecurityLogger, mask_api_key
)

# Load environment variables
load_dotenv("config/.env")
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecureLanduseQueryParams(BaseModel):
    """Secure parameters for landuse database queries"""
    query: str = Field(..., description="Natural language query about landuse data")
    limit: Optional[int] = Field(50, description="Maximum number of rows to return", le=1000, ge=1)
    include_summary: Optional[bool] = Field(True, description="Include summary statistics")
    user_id: Optional[str] = Field(None, description="User identifier for logging")
    
    @field_validator('query')
    def validate_query_length(cls, v):
        if len(v) > 1000:
            raise ValueError("Query too long (max 1000 characters)")
        return v

class SecureLanduseAgent:
    """Secure Natural Language to DuckDB SQL Agent for Landuse Data with Enhanced Security"""
    
    def __init__(self, config_path: Optional[str] = "config/.env"):
        self.console = Console()
        self.session_start = datetime.now()
        
        # Load secure configuration
        try:
            self.config = SecureConfig.from_env(config_path)
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
        
        # Initialize security components
        self.sql_validator = SQLQueryValidator()
        self.input_validator = InputValidator()
        self.rate_limiter = RateLimiter(max_calls=60, time_window=60)
        self.security_logger = SecurityLogger("logs/security.log")
        
        # Validate database path
        self.db_path = Path(self.config.database_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        # Initialize LLM with appropriate model
        self._init_llm()
        
        # Get database schema information
        self.schema_info = self._get_schema_info()
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create agent
        self.agent = self._create_agent()
        
        logger.info(f"Secure agent initialized with model: {self.config.landuse_model}")
    
    def _init_llm(self):
        """Initialize LLM based on configuration"""
        if self.config.landuse_model.startswith("claude"):
            if not self.config.anthropic_api_key:
                raise ValueError("Anthropic API key required for Claude models")
            
            self.llm = ChatAnthropic(
                api_key=self.config.anthropic_api_key,
                model=self.config.landuse_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            logger.info(f"Using Claude model: {self.config.landuse_model}")
        else:
            if not self.config.openai_api_key:
                raise ValueError("OpenAI API key required for GPT models")
            
            self.llm = ChatOpenAI(
                api_key=self.config.openai_api_key,
                model=self.config.landuse_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            logger.info(f"Using OpenAI model: {self.config.landuse_model}")
    
    def _get_schema_info(self) -> str:
        """Get comprehensive schema information for the agent"""
        try:
            conn = duckdb.connect(str(self.db_path), read_only=True)
            
            schema_info = """
# Landuse Transitions Database Schema

## Overview
This database contains land use transition data across different climate scenarios, time periods, and geographic locations using a star schema design.

## Tables and Relationships

### Fact Table
- **fact_landuse_transitions**: Main table with transition data
  - transition_id (BIGINT): Unique identifier
  - scenario_id (INTEGER): Links to dim_scenario
  - time_id (INTEGER): Links to dim_time  
  - geography_id (INTEGER): Links to dim_geography
  - from_landuse_id (INTEGER): Source land use type
  - to_landuse_id (INTEGER): Destination land use type
  - acres (DECIMAL): Area in acres for this transition
  - transition_type (VARCHAR): 'same' or 'change'

### Dimension Tables
- **dim_scenario**: Climate and socioeconomic scenarios
  - scenario_id (INTEGER): Primary key
  - scenario_name (VARCHAR): Full scenario name (e.g., "CNRM_CM5_rcp45_ssp1")
  - climate_model (VARCHAR): Climate model (e.g., "CNRM_CM5")
  - rcp_scenario (VARCHAR): RCP pathway (e.g., "rcp45", "rcp85")
  - ssp_scenario (VARCHAR): SSP pathway (e.g., "ssp1", "ssp5")

- **dim_time**: Time periods
  - time_id (INTEGER): Primary key
  - year_range (VARCHAR): Range like "2012-2020"
  - start_year (INTEGER): Starting year
  - end_year (INTEGER): Ending year
  - period_length (INTEGER): Duration in years

- **dim_geography**: Geographic locations
  - geography_id (INTEGER): Primary key
  - fips_code (VARCHAR): 5-digit FIPS county code
  - state_code (VARCHAR): 2-digit state code

- **dim_landuse**: Land use types
  - landuse_id (INTEGER): Primary key
  - landuse_code (VARCHAR): Short code (cr, ps, rg, fr, ur)
  - landuse_name (VARCHAR): Full name (Crop, Pasture, Rangeland, Forest, Urban)
  - landuse_category (VARCHAR): Category (Agriculture, Natural, Developed)

## Security Notes
- All queries are validated for SQL injection
- Only SELECT queries are allowed
- Results are limited to prevent excessive data exposure
"""
            
            conn.close()
            return schema_info
            
        except Exception as e:
            logger.error(f"Error getting schema info: {e}")
            return f"Error getting schema info: {str(e)}"
    
    def _create_tools(self) -> List[Tool]:
        """Create specialized tools for landuse queries with security"""
        return [
            Tool(
                name="execute_secure_landuse_query",
                func=self._execute_secure_landuse_query,
                description="🦆 Execute validated DuckDB SQL query on the landuse database. Input should be a SQL query string."
            ),
            Tool(
                name="get_schema_info",
                func=self._get_schema_help,
                description="📊 Get detailed schema information about the landuse database tables and relationships."
            ),
            Tool(
                name="suggest_query_examples",
                func=self._suggest_query_examples,
                description="💡 Get example queries for common landuse analysis patterns."
            )
        ]
    
    def _execute_secure_landuse_query(self, sql_query: str) -> str:
        """Execute SQL query with security validation"""
        try:
            # Clean up SQL query
            sql_query = sql_query.strip()
            if sql_query.startswith('```sql'):
                sql_query = sql_query[6:]
            if sql_query.startswith('```'):
                sql_query = sql_query[3:]
            if sql_query.endswith('```'):
                sql_query = sql_query[:-3]
            sql_query = sql_query.strip()
            
            # Validate SQL query for security
            is_valid, error = self.sql_validator.validate_query(sql_query)
            if not is_valid:
                self.security_logger.log_query(
                    user_id="system",
                    query=sql_query,
                    status="blocked",
                    error=error
                )
                return f"❌ Security Error: {error}"
            
            # Connect with read-only mode
            conn = duckdb.connect(str(self.db_path), read_only=True)
            
            # Add LIMIT if not present
            if sql_query.upper().startswith('SELECT') and 'LIMIT' not in sql_query.upper():
                sql_query = f"{sql_query.rstrip(';')} LIMIT {self.config.max_query_limit}"
            
            # Execute query
            result = conn.execute(sql_query)
            if result is None:
                conn.close()
                return f"❌ Query returned no result object.\nSQL: {sql_query}"
            
            df = result.df()
            conn.close()
            
            # Log successful query
            self.security_logger.log_query(
                user_id="system",
                query=sql_query[:100],
                status="success",
                error=None
            )
            
            if df.empty:
                return f"✅ Query executed successfully but returned no results.\nSQL: {sql_query}"
            
            # Format results
            result = f"🦆 **DuckDB Query Results** ({len(df)} rows)\n"
            result += f"**SQL:** `{sql_query}`\n\n"
            
            # Show data with limit
            if len(df) <= 20:
                result += "**Results:**\n"
                result += df.to_string(index=False, max_colwidth=30)
            else:
                result += "**Results (first 20 rows):**\n"
                result += df.head(20).to_string(index=False, max_colwidth=30)
                result += f"\n\n... and {len(df) - 20} more rows"
            
            # Add summary statistics for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0 and len(df) > 1:
                result += f"\n\n📊 **Summary Statistics:**\n"
                summary = df[numeric_cols].describe()
                result += summary.to_string()
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            self.security_logger.log_query(
                user_id="system",
                query=sql_query[:100],
                status="error",
                error=str(e)
            )
            return f"❌ Error executing query: {str(e)}\nSQL: {sql_query}"
    
    def _get_schema_help(self, query: str = "") -> str:
        """Get schema information"""
        return self.schema_info
    
    def _suggest_query_examples(self, category: str = "general") -> str:
        """Suggest example queries for common patterns"""
        examples = {
            "agricultural_loss": """
-- Agricultural land loss (secure query example)
SELECT 
    AVG(f.acres) as avg_acres_lost_per_scenario,
    COUNT(DISTINCT s.scenario_id) as scenarios_included
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE fl.landuse_category = 'Agriculture' 
  AND tl.landuse_category != 'Agriculture'
  AND f.transition_type = 'change'
LIMIT 100;
""",
            "urbanization": """
-- Urbanization patterns (secure query example)
SELECT 
    g.state_code,
    fl.landuse_name as from_landuse,
    AVG(f.acres) as avg_acres_urbanized
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE tl.landuse_name = 'Urban'
  AND f.transition_type = 'change'
GROUP BY g.state_code, fl.landuse_name
ORDER BY avg_acres_urbanized DESC
LIMIT 20;
"""
        }
        
        if category.lower() in examples:
            return f"💡 **Example Query - {category.title()}:**\n```sql\n{examples[category.lower()]}\n```"
        
        result = "💡 **Secure Query Examples:**\n\n"
        for name, sql in examples.items():
            result += f"**{name.replace('_', ' ').title()}:**\n```sql\n{sql}\n```\n\n"
        
        return result
    
    def _create_agent(self):
        """Create the natural language to SQL agent with security focus"""
        prompt = PromptTemplate.from_template("""
You are a specialized Landuse Data Analyst AI that converts natural language questions into secure DuckDB SQL queries.

SECURITY REQUIREMENTS:
1. Only generate SELECT queries - no data modification allowed
2. Always include appropriate LIMIT clauses (max {max_limit})
3. Validate all identifiers and parameters
4. Never include user input directly in SQL strings
5. Use proper JOIN syntax instead of subqueries where possible

AVAILABLE TOOLS:
{{tools}}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{{tool_names}}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

DATABASE SCHEMA:
{{schema_info}}

INSTRUCTIONS:
1. Convert natural language to secure SQL queries
2. Always validate query structure before execution
3. Use appropriate aggregations and filters
4. Include meaningful ORDER BY and LIMIT clauses
5. Focus on read-only analysis
6. IMPORTANT: When using execute_secure_landuse_query, provide ONLY the SQL query

DEFAULT ASSUMPTIONS:
- Scenarios: Average across all scenarios unless specified
- Time Periods: Full time range unless specified
- Geographic Scope: All counties unless specified
- Transition Type: Focus on 'change' transitions

Question: {{input}}
Thought: Let me understand what the user is asking and create a secure SQL query.
{{agent_scratchpad}}
""".format(max_limit=self.config.max_query_limit))
        
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
            max_iterations=5
        )
        
        return agent_executor
    
    def query(self, natural_language_query: str, user_id: str = "anonymous") -> str:
        """Process a natural language query with security checks"""
        try:
            # Rate limiting check
            allowed, error = self.rate_limiter.check_rate_limit(user_id)
            if not allowed:
                self.security_logger.log_rate_limit(user_id, 60)
                return f"❌ {error}"
            
            # Validate query parameters
            params = SecureLanduseQueryParams(
                query=natural_language_query,
                user_id=user_id
            )
            
            # Log query attempt
            logger.info(f"Query from {user_id}: {params.query[:100]}...")
            
            # Process query
            response = self.agent.invoke({
                "input": params.query,
                "schema_info": self.schema_info
            })
            
            return response.get("output", "No response generated")
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"❌ Error processing query: {str(e)}"
    
    def chat(self):
        """Interactive chat mode with security features"""
        self.console.print(Panel.fit(
            "🌾 [bold green]Secure Landuse Natural Language Query Agent[/bold green]\n"
            "[yellow]Ask questions about landuse transitions in natural language![/yellow]\n"
            f"[dim]Database: {self.db_path}[/dim]\n"
            f"[dim]Model: {self.config.landuse_model} | "
            f"API Key: {mask_api_key(self.config.openai_api_key or self.config.anthropic_api_key or 'Not Set')}[/dim]",
            border_style="green"
        ))
        
        # Show security info
        self.console.print(Panel(
            "🔒 [bold cyan]Security Features Active:[/bold cyan]\n"
            "• SQL injection prevention\n"
            "• Query validation and sanitization\n" 
            "• Rate limiting (60 queries/minute)\n"
            "• Read-only database access\n"
            "• Audit logging enabled",
            border_style="cyan"
        ))
        
        # Show examples
        examples_panel = Panel(
            """[bold cyan]🚀 Example questions:[/bold cyan]

• "How much agricultural land is being lost?"
• "Which states have the most urban expansion?"
• "Compare forest loss between RCP45 and RCP85 scenarios"
• "Show me crop to pasture transitions by state"

[dim]Type 'exit' to quit, 'help' for more info[/dim]""",
            title="💡 Try these queries",
            border_style="blue"
        )
        self.console.print(examples_panel)
        
        while True:
            try:
                user_input = self.console.input("[bold green]🌾 Ask>[/bold green] ").strip()
                
                if user_input.lower() == 'exit':
                    self.console.print("\n[bold red]👋 Session ended securely![/bold red]")
                    break
                elif user_input.lower() == 'help':
                    self.console.print(examples_panel)
                elif user_input.lower() == 'schema':
                    schema_md = Markdown(self.schema_info)
                    self.console.print(Panel(schema_md, title="📊 Database Schema", border_style="cyan"))
                elif user_input:
                    with self.console.status(f"[bold green]🤖 Processing query securely...[/bold green]", spinner="earth"):
                        response = self.query(user_input, user_id="interactive_user")
                    
                    # Format response as markdown
                    response_md = Markdown(response)
                    self.console.print(Panel(response_md, title="🔍 Analysis Results", border_style="green"))
                    self.console.print()
                
            except KeyboardInterrupt:
                self.console.print("\n[bold red]👋 Session ended securely![/bold red]")
                break
            except Exception as e:
                logger.error(f"Chat error: {e}")
                self.console.print(Panel(f"❌ Error: {str(e)}", border_style="red"))

if __name__ == "__main__":
    # Create and run the secure landuse query agent
    try:
        agent = SecureLanduseQueryAgent()
        agent.chat()
    except Exception as e:
        console = Console()
        console.print(f"[bold red]Failed to start agent: {str(e)}[/bold red]")
        logger.error(f"Startup failed: {e}")