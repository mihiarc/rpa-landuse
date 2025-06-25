#!/usr/bin/env python3
"""
Base agent class for landuse analysis
Provides common functionality for all landuse agents
"""

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional, Union

import duckdb
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ..config import LanduseConfig
from ..models import (
    AgentConfig,
    ExecuteQueryInput,
    QueryExamplesInput,
    QueryInput,
    QueryResult,
    SchemaInfoInput,
    SQLQuery,
    StateCodeInput,
    ToolInput,
)
from ..utils.retry_decorators import api_retry, database_retry
from .constants import (
    DB_CONFIG,
    DEFAULT_ASSUMPTIONS,
    MODEL_CONFIG,
    QUERY_EXAMPLES,
    RESPONSE_SECTIONS,
    SCHEMA_INFO_TEMPLATE,
)
from .formatting import (
    clean_sql_query,
    create_examples_panel,
    create_welcome_panel,
    format_error,
    format_query_results,
    format_response,
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
        verbose: bool = False,
        config: Optional[Union[AgentConfig, LanduseConfig]] = None
    ):
        """Initialize the base agent with Pydantic configuration"""
        self.console = Console()
        self.verbose = verbose

        # Setup logging
        self._setup_logging()

        # Use provided config or create from parameters
        if config:
            # Support both old AgentConfig and new LanduseConfig
            if isinstance(config, LanduseConfig):
                self.unified_config = config
                # Convert to AgentConfig for backward compatibility
                self.config = AgentConfig(
                    db_path=Path(config.db_path),
                    model_name=config.model_name,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                    max_iterations=config.max_iterations,
                    max_execution_time=config.max_execution_time,
                    max_query_rows=config.max_query_rows,
                    default_display_limit=config.default_display_limit,
                    rate_limit_calls=config.rate_limit_calls,
                    rate_limit_window=config.rate_limit_window
                )
            else:
                self.config = config
                self.unified_config = None
        else:
            # Create new unified config first, then convert for backward compatibility
            overrides = {}
            if db_path:
                overrides['db_path'] = db_path
            if model_name:
                overrides['model_name'] = model_name
            if temperature is not None:
                overrides['temperature'] = temperature
            if max_tokens is not None:
                overrides['max_tokens'] = max_tokens
            if verbose:
                overrides['verbose'] = verbose

            self.unified_config = LanduseConfig.for_agent_type('basic', **overrides)

            # Convert to AgentConfig for backward compatibility
            self.config = AgentConfig(
                db_path=Path(self.unified_config.db_path),
                model_name=self.unified_config.model_name,
                temperature=self.unified_config.temperature,
                max_tokens=self.unified_config.max_tokens,
                max_iterations=self.unified_config.max_iterations,
                max_execution_time=self.unified_config.max_execution_time,
                max_query_rows=self.unified_config.max_query_rows,
                default_display_limit=self.unified_config.default_display_limit,
                rate_limit_calls=self.unified_config.rate_limit_calls,
                rate_limit_window=self.unified_config.rate_limit_window
            )

        # Extract commonly used values
        self.db_path = self.config.db_path
        self.model_name = self.config.model_name
        self.temperature = self.config.temperature
        self.max_tokens = self.config.max_tokens

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
            # Safe: These table names are hardcoded, not from user input
            tables = ['dim_scenario', 'dim_time', 'dim_geography_enhanced', 'dim_landuse', 'fact_landuse_transitions']

            for table in tables:
                try:
                    # Safe: table names from hardcoded list above
                    count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                    tables_info.append(f"- {table}: {count:,} records")
                except Exception:
                    pass

            if tables_info:
                schema_info += "\n## Current Data Counts\n" + "\n".join(tables_info)

            # Get sample scenarios
            try:
                scenarios = conn.execute("SELECT scenario_name FROM dim_scenario LIMIT 5").fetchall()
                scenario_names = [s[0] for s in scenarios]
                if scenario_names:
                    schema_info += "\n\n## Sample Scenarios\n" + "\n".join([f"- {s}" for s in scenario_names])
            except Exception:
                pass  # Optional info, safe to skip on error

            conn.close()
            return schema_info

        except Exception as e:
            self.logger.error(f"Error getting schema info: {e}")
            return f"Error getting schema info: {str(e)}"

    def _create_tools(self) -> list[Tool]:
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

    def _get_additional_tools(self) -> Optional[list[Tool]]:
        """Hook for subclasses to add additional tools"""
        return None

    @database_retry(max_attempts=3, min_wait=1.0, max_wait=10.0,
                   exceptions=(ConnectionError, TimeoutError, OSError))
    def _execute_landuse_query(self, sql_query: str) -> str:
        """Execute SQL query on the landuse database with validation and retry logic"""
        try:
            # Validate input using Pydantic
            input_data = ExecuteQueryInput(sql_query=sql_query)

            # Clean and validate SQL
            query_obj = SQLQuery(sql=clean_sql_query(input_data.sql_query))
            sql_query = query_obj.sql

            # Validate query if needed (hook for subclasses)
            validation_result = self._validate_query(sql_query)
            if validation_result:
                return validation_result

            # Connect to database
            conn = duckdb.connect(str(self.db_path), read_only=True)

            # Add LIMIT if not present
            if sql_query.upper().startswith('SELECT') and 'LIMIT' not in sql_query.upper():
                # Remove trailing semicolon if present
                query_trimmed = sql_query.rstrip().rstrip(';').rstrip()
                sql_query = f"{query_trimmed} LIMIT {self.config.max_query_rows}"

            # Execute query
            import time
            start_time = time.time()
            result = conn.execute(sql_query)
            execution_time = time.time() - start_time

            if result is None:
                conn.close()
                query_result = QueryResult(
                    success=False,
                    error="Query returned no result object",
                    query=sql_query
                )
                return f"❌ {query_result.error}\nSQL: {sql_query}"

            df = result.df()
            conn.close()

            # Create QueryResult object
            query_result = QueryResult(
                success=True,
                data=df,
                execution_time=execution_time,
                query=sql_query
            )

            # Format results
            return format_query_results(
                df, sql_query,
                max_display_rows=self.config.default_display_limit
            )

        except ValueError as e:
            # Pydantic validation error
            self.logger.error(f"Validation error: {e}")
            return f"❌ Invalid query: {str(e)}"
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            query_result = QueryResult(
                success=False,
                error=str(e),
                query=sql_query if 'sql_query' in locals() else 'Unknown'
            )
            return f"❌ Error executing query: {query_result.error}\nSQL: {query_result.query}"

    def _validate_query(self, sql_query: str) -> Optional[str]:
        """Hook for subclasses to validate queries before execution"""
        return None

    def _get_schema_help(self, query: str = "") -> str:
        """Get schema information"""
        return self.schema_info

    def _suggest_query_examples(self, category: str = "general") -> str:
        """Suggest example queries for common patterns with validation"""
        try:
            # Validate input
            input_data = QueryExamplesInput(category=category if category else "general")
            category = input_data.category.lower()

            if category in QUERY_EXAMPLES:
                return f"💡 **Example Query - {category.title()}:**\n```sql\n{QUERY_EXAMPLES[category]}\n```"

            result = "💡 **Common Query Examples:**\n\n"
            for name, sql in QUERY_EXAMPLES.items():
                result += f"**{name.replace('_', ' ').title()}:**\n```sql\n{sql}\n```\n\n"

            return result
        except Exception as e:
            self.logger.error(f"Error getting examples: {e}")
            return f"❌ Error getting examples: {str(e)}"

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
            max_execution_time=MODEL_CONFIG['max_execution_time'],
            return_intermediate_steps=False
        )

        return agent_executor

    def query(self, natural_language_query: str) -> str:
        """Process a natural language query with validation"""
        try:
            # Validate input
            query_input = QueryInput(query=natural_language_query)

            # Pre-query hook
            pre_result = self._pre_query_hook(query_input.query)
            if pre_result:
                return pre_result

            # Log query start
            self.logger.info(f"Processing query: {query_input.query[:100]}...")

            # Process query
            response = self.agent.invoke({
                "input": query_input.query,
                "schema_info": self.schema_info
            })

            # Check if we hit iteration limit
            if response.get("iterations", 0) >= self.config.max_iterations:
                self.logger.warning(f"Query hit iteration limit ({self.config.max_iterations})")

            # Post-query hook
            output = response.get("output", "No response generated")
            return self._post_query_hook(output)

        except TimeoutError:
            self.logger.error(f"Query timed out after {MODEL_CONFIG['max_execution_time']} seconds")
            return (f"⏱️ Query timed out after {MODEL_CONFIG['max_execution_time']} seconds. "
                   f"Try a simpler query or increase LANDUSE_MAX_EXECUTION_TIME.")
        except Exception as e:
            # Check for specific error messages
            error_msg = str(e)
            if "Agent stopped due to iteration limit" in error_msg:
                self.logger.warning(f"Agent hit iteration limit: {error_msg}")
                return (f"🔄 Query required too many steps (>{MODEL_CONFIG['max_iterations']}). "
                       f"Try a simpler query or increase LANDUSE_MAX_ITERATIONS.")
            elif "Agent stopped due to time limit" in error_msg:
                self.logger.warning(f"Agent hit time limit: {error_msg}")
                return (f"⏱️ Query took too long (>{MODEL_CONFIG['max_execution_time']}s). "
                       f"Try a simpler query or increase LANDUSE_MAX_EXECUTION_TIME.")
            else:
                self.logger.error(f"Error processing query: {e}")
                return f"❌ Error processing query: {error_msg}"

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
                user_input = self.console.input("[bold green]🌲 RPA Analytics>[/bold green] ").strip()

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
        # This is intentionally empty - subclasses can override
        return
