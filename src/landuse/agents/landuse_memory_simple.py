#!/usr/bin/env python3
"""
Landuse Natural Language Query Agent with Simple Conversation Memory
Uses LangChain's ConversationSummaryBufferMemory for memory management
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import duckdb
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationSummaryBufferMemory
from langchain.schema import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Load environment variables
env_path = Path(__file__).parent.parent.parent / "config" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

class SimpleLanduseMemoryAgent:
    """Natural Language to DuckDB SQL Agent with Simple Memory"""
    
    def __init__(self, db_path: str = "data/processed/landuse_analytics.duckdb"):
        self.db_path = Path(db_path)
        self.console = Console()
        
        # Initialize LLM
        model_name = os.getenv("LANDUSE_MODEL", "claude-3-5-sonnet-20241022")
        if "claude" in model_name.lower():
            self.llm = ChatAnthropic(
                model=model_name,
                temperature=0.1,
                max_tokens=2000
            )
        else:
            self.llm = ChatOpenAI(
                model=model_name,
                temperature=0.1,
                max_tokens=2000
            )
        
        # Initialize memory with summary buffer (keeps recent messages + summary of older ones)
        self.memory = ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=1000,  # Keep last ~1000 tokens of conversation
            return_messages=True
        )
        
        # Get database schema
        self.schema_info = self._get_schema_info()
    
    def _get_schema_info(self) -> str:
        """Get database schema information"""
        if not self.db_path.exists():
            return "Database file not found"
        
        return """
# Landuse Database Schema

## Fact Table
- **fact_landuse_transitions**: transition_id, scenario_id, time_id, geography_id, from_landuse_id, to_landuse_id, acres, transition_type

## Dimension Tables
- **dim_scenario**: scenario_id, scenario_name, climate_model, rcp_scenario (rcp45/rcp85), ssp_scenario (ssp1/ssp5)
- **dim_time**: time_id, year_range, start_year, end_year
- **dim_geography**: geography_id, fips_code, state_code
- **dim_landuse**: landuse_id, landuse_code (cr/ps/rg/fr/ur), landuse_name (Crop/Pasture/Rangeland/Forest/Urban)

## Default Assumptions
- Time: Full range (2012-2100) unless specified
- Scenarios: Average across all 20 scenarios unless specified
- Geography: All states/counties unless specified
- Focus on 'change' transitions (not same-to-same)
"""
    
    def _execute_sql(self, sql_query: str) -> str:
        """Execute SQL query and return formatted results"""
        try:
            conn = duckdb.connect(str(self.db_path), read_only=True)
            
            # Add LIMIT if not present
            if sql_query.upper().startswith('SELECT') and 'LIMIT' not in sql_query.upper():
                sql_query = f"{sql_query.rstrip(';')} LIMIT 100"
            
            result = conn.execute(sql_query)
            df = result.df()
            conn.close()
            
            if df.empty:
                return "Query returned no results."
            
            # Format results
            output = f"**Query Results** ({len(df)} rows)\n\n"
            if len(df) <= 20:
                output += df.to_string(index=False)
            else:
                output += df.head(20).to_string(index=False)
                output += f"\n\n... and {len(df) - 20} more rows"
            
            # Add summary stats for numeric columns
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0 and len(df) > 1:
                output += f"\n\n**Summary Statistics:**\n"
                output += df[numeric_cols].describe().to_string()
            
            return output
            
        except Exception as e:
            return f"Error executing query: {str(e)}"
    
    def ask(self, question: str) -> str:
        """Process a question with conversation memory"""
        
        # Get conversation history
        messages = self.memory.chat_memory.messages
        
        # Build context from recent conversation
        context = "Previous conversation:\n"
        for msg in messages[-6:]:  # Last 3 exchanges
            if isinstance(msg, HumanMessage):
                context += f"User: {msg.content}\n"
            elif isinstance(msg, AIMessage):
                # Extract key info from AI response
                content = str(msg.content)[:200] + "..." if len(str(msg.content)) > 200 else str(msg.content)
                context += f"Assistant: {content}\n"
        
        # Create prompt
        prompt = f"""You are a SQL expert for landuse data analysis.

DATABASE SCHEMA:
{self.schema_info}

CONVERSATION CONTEXT:
{context}

Current Question: {question}

Instructions:
1. Understand the question in context of the conversation
2. Generate appropriate SQL query
3. For follow-up questions (like "what about in California?"), refer to the context
4. Always state your assumptions clearly

Provide:
1. The SQL query (marked with ```sql)
2. Brief explanation of what the query does
"""
        
        # Get LLM response
        response = self.llm.invoke(prompt)
        response_text = response.content
        
        # Extract SQL query
        sql_query = ""
        if "```sql" in response_text:
            sql_start = response_text.find("```sql") + 6
            sql_end = response_text.find("```", sql_start)
            sql_query = response_text[sql_start:sql_end].strip()
        
        # Execute query if found
        if sql_query:
            self.console.print(f"\n[dim]Executing SQL: {sql_query[:100]}...[/dim]")
            query_results = self._execute_sql(sql_query)
            
            # Generate final response
            final_prompt = f"""Based on these query results, provide a clear answer to the user's question.

Question: {question}
SQL Query: {sql_query}
Results: {query_results}

Provide:
1. Direct answer to the question
2. Key insights from the data
3. Any patterns or trends
4. Suggestions for follow-up questions"""
            
            final_response = self.llm.invoke(final_prompt)
            full_response = f"{final_response.content}\n\n**SQL Query Used:**\n```sql\n{sql_query}\n```"
        else:
            full_response = response_text
        
        # Save to memory
        self.memory.save_context({"input": question}, {"output": full_response})
        
        return full_response
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()
        self.console.print("[yellow]Conversation memory cleared[/yellow]")
    
    def chat(self):
        """Interactive chat interface"""
        self.console.print(Panel.fit(
            "[bold blue]🌾 Landuse Agent with Memory (Simple)[/bold blue]\n"
            "I remember our conversation! Ask follow-up questions naturally.\n"
            "Commands: 'clear' (clear memory), 'exit' (quit)",
            border_style="blue"
        ))
        
        # Show example questions
        self.console.print("\n[dim]Example questions:[/dim]")
        self.console.print("[dim]- How much agricultural land is being lost?[/dim]")
        self.console.print("[dim]- What about in California?[/dim]")
        self.console.print("[dim]- Which states are losing the most?[/dim]")
        
        while True:
            try:
                # Get user input
                question = Prompt.ask("\n[green]Ask[/green]")
                
                if question.lower() == 'exit':
                    self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
                    break
                elif question.lower() == 'clear':
                    self.clear_memory()
                    continue
                elif not question.strip():
                    continue
                
                # Process question
                self.console.print("\n[dim]Thinking...[/dim]")
                response = self.ask(question)
                
                # Display response
                self.console.print("\n" + Markdown(response))
                
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Use 'exit' to quit[/yellow]")
            except Exception as e:
                self.console.print(f"\n[red]Error: {str(e)}[/red]")

def main():
    """Main entry point"""
    agent = SimpleLanduseMemoryAgent()
    agent.chat()

if __name__ == "__main__":
    main()