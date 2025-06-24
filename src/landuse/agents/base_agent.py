#!/usr/bin/env python3
"""
Base agent class for landuse analysis
Provides common functionality for all landuse agents
"""

import os
import logging
import duckdb
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_react_agent, AgentExecutor
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.tools import Tool
from langchain.prompts import PromptTemplate
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from .constants import (
    SCHEMA_INFO_TEMPLATE, DB_CONFIG, MODEL_CONFIG,
    QUERY_EXAMPLES, DEFAULT_ASSUMPTIONS, RESPONSE_SECTIONS
)
from .formatting import (
    clean_sql_query, format_query_results, create_welcome_panel,
    create_examples_panel, format_error, format_response
)

# Load environment variables
load_dotenv("config/.env")
load_dotenv()


class BaseLanduseAgent(ABC):
    """Base class for landuse natural language agents"""
    
    def __init__(
        self,
        db_path: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        verbose: bool = False
    ):
        """Initialize the base agent"""
        self.console = Console()
        self.verbose = verbose
        
        # Setup logging
        self._setup_logging()
        
        # Database configuration
        self.db_path = Path(db_path or os.getenv('LANDUSE_DB_PATH', DB_CONFIG['default_path']))
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        # Model configuration
        self.model_name = model_name or os.getenv('LANDUSE_MODEL', MODEL_CONFIG['default_openai_model'])
        self.temperature = temperature or float(os.getenv('TEMPERATURE', str(MODEL_CONFIG['default_temperature'])))
        self.max_tokens = max_tokens or int(os.getenv('MAX_TOKENS', str(MODEL_CONFIG['default_max_tokens'])))
        
        # Initialize LLM
        self._init_llm()
        
        # Get database schema
        self.schema_info = self._get_schema_info()
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create agent
        self.agent = self._create_agent()
        
        self.logger.info(f"Agent initialized with model: {self.model_name}")
    
    def _setup_logging(self):
        """Setup logging configuration"""
        log_level = logging.ERROR if not self.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(log_level)
        
        # Suppress noisy libraries
        logging.getLogger("httpx").setLevel(logging.CRITICAL)
        logging.getLogger("langchain").setLevel(logging.WARNING)
    
    def _init_llm(self):
        """Initialize the language model"""
        if self.model_name.startswith("claude"):
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("Anthropic API key required for Claude models")
            
            self.llm = ChatAnthropic(
                api_key=api_key,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            self.api_key_masked = self._mask_api_key(api_key)
        else:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OpenAI API key required for GPT models")
            
            self.llm = ChatOpenAI(
                api_key=api_key,
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            self.api_key_masked = self._mask_api_key(api_key)
    
    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for display"""
        if len(api_key) <= 8:
            return "****"
        return f"{api_key[:4]}...{api_key[-4:]}"
    
    def _get_schema_info(self) -> str:
        """Get comprehensive schema information for the agent"""
        try:
            conn = duckdb.connect(str(self.db_path), read_only=True)
            
            # Start with template
            schema_info = SCHEMA_INFO_TEMPLATE
            
            # Add actual table counts
            tables_info = []
            tables = ['dim_scenario', 'dim_time', 'dim_geography', 'dim_landuse', 'fact_landuse_transitions']
            
            for table in tables:
                try:
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    tables_info.append(f"- {table}: {count:,} records")
                except Exception:
                    pass
            
            if tables_info:
                schema_info += f"\n## Current Data Counts\n" + "\n".join(tables_info)
            
            # Get sample scenarios
            try:
                scenarios = conn.execute("SELECT scenario_name FROM dim_scenario LIMIT 5").fetchall()
                scenario_names = [s[0] for s in scenarios]
                if scenario_names:
                    schema_info += f"\n\n## Sample Scenarios\n" + "\n".join([f"- {s}" for s in scenario_names])
            except Exception:
                pass
            
            conn.close()
            return schema_info
            
        except Exception as e:
            self.logger.error(f"Error getting schema info: {e}")
            return f"Error getting schema info: {str(e)}"
    
    def _create_tools(self) -> List[Tool]:
        """Create tools for the agent - can be overridden by subclasses"""
        tools = [
            Tool(
                name="execute_landuse_query",
                func=self._execute_landuse_query,
                description="🦆 Execute DuckDB SQL query on the landuse database. Input should be a SQL query string."
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
        
        # Allow subclasses to add additional tools
        additional_tools = self._get_additional_tools()
        if additional_tools:
            tools.extend(additional_tools)
        
        return tools
    
    def _get_additional_tools(self) -> Optional[List[Tool]]:
        """Hook for subclasses to add additional tools"""
        return None
    
    def _execute_landuse_query(self, sql_query: str) -> str:
        """Execute SQL query on the landuse database"""
        try:
            # Clean the SQL query
            sql_query = clean_sql_query(sql_query)
            
            # Validate query if needed (hook for subclasses)
            validation_result = self._validate_query(sql_query)
            if validation_result:
                return validation_result
            
            # Connect to database
            conn = duckdb.connect(str(self.db_path), read_only=True)
            
            # Add LIMIT if not present
            if sql_query.upper().startswith('SELECT') and 'LIMIT' not in sql_query.upper():
                sql_query = f"{sql_query.rstrip(';')} LIMIT {DB_CONFIG['max_query_limit']}"
            
            # Execute query
            result = conn.execute(sql_query)
            if result is None:
                conn.close()
                return f"❌ Query returned no result object.\nSQL: {sql_query}"
            
            df = result.df()
            conn.close()
            
            # Format results
            return format_query_results(
                df, sql_query,
                max_display_rows=DB_CONFIG['default_display_limit']
            )
            
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            return f"❌ Error executing query: {str(e)}\nSQL: {sql_query}"
    
    def _validate_query(self, sql_query: str) -> Optional[str]:
        """Hook for subclasses to validate queries before execution"""
        return None
    
    def _get_schema_help(self, query: str = "") -> str:
        """Get schema information"""
        return self.schema_info
    
    def _suggest_query_examples(self, category: str = "general") -> str:
        """Suggest example queries for common patterns"""
        if category.lower() in QUERY_EXAMPLES:
            return f"💡 **Example Query - {category.title()}:**\n```sql\n{QUERY_EXAMPLES[category.lower()]}\n```"
        
        result = "💡 **Common Query Examples:**\n\n"
        for name, sql in QUERY_EXAMPLES.items():
            result += f"**{name.replace('_', ' ').title()}:**\n```sql\n{sql}\n```\n\n"
        
        return result
    
    @abstractmethod
    def _get_agent_prompt(self) -> str:
        """Get the prompt template for the agent - must be implemented by subclasses"""
        pass
    
    def _create_agent(self):
        """Create the natural language to SQL agent"""
        prompt_text = self._get_agent_prompt()
        prompt = PromptTemplate.from_template(prompt_text)
        
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
            verbose=self.verbose,
            handle_parsing_errors=True,
            max_iterations=MODEL_CONFIG['max_iterations'],
            return_intermediate_steps=False
        )
        
        return agent_executor
    
    def query(self, natural_language_query: str) -> str:
        """Process a natural language query"""
        try:
            # Pre-query hook
            pre_result = self._pre_query_hook(natural_language_query)
            if pre_result:
                return pre_result
            
            # Process query
            response = self.agent.invoke({
                "input": natural_language_query,
                "schema_info": self.schema_info
            })
            
            # Post-query hook
            output = response.get("output", "No response generated")
            return self._post_query_hook(output)
            
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return f"❌ Error processing query: {str(e)}"
    
    def _pre_query_hook(self, query: str) -> Optional[str]:
        """Hook called before query processing"""
        return None
    
    def _post_query_hook(self, output: str) -> str:
        """Hook called after query processing"""
        return output
    
    def chat(self):
        """Interactive chat mode for landuse queries"""
        # Welcome message
        self.console.print(create_welcome_panel(
            str(self.db_path),
            self.model_name,
            self.api_key_masked
        ))
        
        # Show additional info if needed (hook for subclasses)
        self._show_chat_intro()
        
        # Show examples
        examples_panel = create_examples_panel()
        self.console.print(examples_panel)
        
        while True:
            try:
                user_input = self.console.input("[bold green]🌾 Agent>[/bold green] ").strip()
                
                if user_input.lower() == 'exit':
                    self.console.print("\n[bold red]👋 Happy analyzing![/bold red]")
                    break
                elif user_input.lower() == 'help':
                    self.console.print(examples_panel)
                elif user_input.lower() == 'schema':
                    schema_md = Markdown(self.schema_info)
                    self.console.print(Panel(schema_md, title="📊 Database Schema", border_style="cyan"))
                elif user_input:
                    # Show processing message
                    self.console.print()
                    with self.console.status("[bold cyan]🔍 Analyzing your query...[/bold cyan]", spinner="dots"):
                        response = self.query(user_input)
                    
                    # Format and display response
                    self.console.print()
                    self.console.print(format_response(response))
                    self.console.print()
                
            except KeyboardInterrupt:
                self.console.print("\n[bold red]👋 Happy analyzing![/bold red]")
                break
            except Exception as e:
                self.logger.error(f"Chat error: {e}")
                self.console.print(format_error(e))
    
    def _show_chat_intro(self):
        """Hook for subclasses to show additional intro information"""
        pass
