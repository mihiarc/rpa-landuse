#!/usr/bin/env python3
"""
Landuse Natural Language Query Agent with Conversation Memory
This agent remembers previous questions and can handle follow-up queries
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, TypedDict, Annotated
from datetime import datetime
import duckdb
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.table import Table

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.memory import MemorySaver
from pydantic import BaseModel, Field

# Load environment variables
env_path = Path(__file__).parent.parent.parent / "config" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

class ConversationState(TypedDict):
    """State for the conversation graph"""
    messages: Annotated[List, add_messages]
    current_query: str
    sql_query: str
    query_result: str
    context_summary: str

class LanduseMemoryAgent:
    """Natural Language to DuckDB SQL Agent with Conversation Memory"""
    
    def __init__(self, 
                 db_path: str = "data/processed/landuse_analytics.duckdb",
                 memory_type: str = "sqlite",
                 memory_path: str = "landuse_conversations.db"):
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
        
        # Initialize memory/checkpointer
        if memory_type == "memory":
            self.checkpointer = MemorySaver()
        else:  # sqlite
            self.checkpointer = SqliteSaver.from_conn_string(memory_path)
        
        # Get database schema
        self.schema_info = self._get_schema_info()
        
        # Create the graph
        self.graph = self._create_graph()
        
        # Thread ID for conversation continuity
        self.thread_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def _get_schema_info(self) -> str:
        """Get database schema information"""
        if not self.db_path.exists():
            return "Database file not found"
        
        try:
            conn = duckdb.connect(str(self.db_path))
            
            schema_info = """
# Landuse Database Schema

## Fact Table
- **fact_landuse_transitions**: transition_id, scenario_id, time_id, geography_id, from_landuse_id, to_landuse_id, acres, transition_type

## Dimension Tables
- **dim_scenario**: scenario_id, scenario_name, climate_model, rcp_scenario (rcp45/rcp85), ssp_scenario (ssp1/ssp5)
- **dim_time**: time_id, year_range, start_year, end_year
- **dim_geography**: geography_id, fips_code, state_code
- **dim_landuse**: landuse_id, landuse_code (cr/ps/rg/fr/ur), landuse_name (Crop/Pasture/Rangeland/Forest/Urban)
"""
            conn.close()
            return schema_info
        except Exception as e:
            return f"Error getting schema: {str(e)}"
    
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
                return f"Query returned no results.\nSQL: {sql_query}"
            
            # Format results
            output = f"Found {len(df)} results\n\n"
            if len(df) <= 20:
                output += df.to_string(index=False)
            else:
                output += df.head(20).to_string(index=False)
                output += f"\n\n... and {len(df) - 20} more rows"
            
            return output
            
        except Exception as e:
            return f"Error executing query: {str(e)}\nSQL: {sql_query}"
    
    def _create_graph(self):
        """Create the LangGraph workflow with memory"""
        
        # Define the workflow
        workflow = StateGraph(ConversationState)
        
        # Node 1: Understand the query with conversation context
        def understand_query(state: ConversationState) -> Dict:
            """Understand user query in context of conversation"""
            
            # Build context from recent messages
            recent_context = ""
            if len(state["messages"]) > 1:
                # Get last 3 exchanges (6 messages)
                recent_msgs = state["messages"][-7:-1] if len(state["messages"]) > 6 else state["messages"][:-1]
                for msg in recent_msgs:
                    if isinstance(msg, HumanMessage):
                        recent_context += f"\nUser: {msg.content}"
                    elif isinstance(msg, AIMessage):
                        # Extract key info from AI responses
                        content = msg.content
                        if "SQL:" in content:
                            sql_start = content.find("SQL:") + 4
                            sql_end = content.find("\n", sql_start)
                            if sql_end > sql_start:
                                recent_context += f"\nPrevious SQL: {content[sql_start:sql_end]}"
            
            # Create prompt with context
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a SQL expert for landuse data analysis. 
                
DATABASE SCHEMA:
{schema}

CONVERSATION CONTEXT:
{context}

Analyze the user's query and determine:
1. Is this a follow-up to the previous conversation?
2. What specific data are they asking for?
3. What SQL query would answer their question?

For follow-up questions like "what about in California?" or "show me more details", 
refer to the conversation context to understand what they're asking about.

Respond with your analysis and the SQL query."""),
                ("human", "{query}")
            ])
            
            response = self.llm.invoke(
                prompt.format_messages(
                    schema=self.schema_info,
                    context=recent_context if recent_context else "No previous context",
                    query=state["current_query"]
                )
            )
            
            # Extract SQL from response
            sql_query = ""
            if "```sql" in response.content:
                sql_start = response.content.find("```sql") + 6
                sql_end = response.content.find("```", sql_start)
                sql_query = response.content[sql_start:sql_end].strip()
            elif "SQL:" in response.content:
                sql_start = response.content.find("SQL:") + 4
                sql_end = response.content.find("\n\n", sql_start)
                if sql_end == -1:
                    sql_end = len(response.content)
                sql_query = response.content[sql_start:sql_end].strip()
            
            return {
                "messages": [response],
                "sql_query": sql_query,
                "context_summary": response.content
            }
        
        # Node 2: Execute the SQL query
        def execute_query(state: ConversationState) -> Dict:
            """Execute the SQL query"""
            if not state["sql_query"]:
                return {"query_result": "No SQL query was generated"}
            
            result = self._execute_sql(state["sql_query"])
            return {"query_result": result}
        
        # Node 3: Generate final response
        def generate_response(state: ConversationState) -> Dict:
            """Generate user-friendly response"""
            
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful landuse data analyst. 
                
Based on the query results, provide a clear, insightful response to the user.
Include:
1. Direct answer to their question
2. Key insights from the data
3. Any relevant patterns or trends
4. Suggestions for follow-up questions

Keep the response concise but informative."""),
                ("human", """Query: {query}
                
SQL Used: {sql}

Results:
{results}

Please provide a clear summary of these results.""")
            ])
            
            response = self.llm.invoke(
                prompt.format_messages(
                    query=state["current_query"],
                    sql=state["sql_query"],
                    results=state["query_result"]
                )
            )
            
            # Combine SQL and response for full context
            full_response = f"{response.content}\n\n**SQL Query Used:**\n```sql\n{state['sql_query']}\n```"
            
            return {"messages": [AIMessage(content=full_response)]}
        
        # Add nodes
        workflow.add_node("understand", understand_query)
        workflow.add_node("execute", execute_query)
        workflow.add_node("respond", generate_response)
        
        # Add edges
        workflow.add_edge(START, "understand")
        workflow.add_edge("understand", "execute")
        workflow.add_edge("execute", "respond")
        workflow.add_edge("respond", END)
        
        # Compile with checkpointer for memory
        return workflow.compile(checkpointer=self.checkpointer)
    
    def ask(self, question: str) -> str:
        """Process a single question with conversation memory"""
        
        # Configuration with thread ID for conversation continuity
        config = {
            "configurable": {
                "thread_id": self.thread_id
            }
        }
        
        # Run the graph
        result = self.graph.invoke(
            {
                "messages": [HumanMessage(content=question)],
                "current_query": question
            },
            config=config
        )
        
        # Get the last AI message
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                return msg.content
        
        return "No response generated"
    
    def new_conversation(self):
        """Start a new conversation thread"""
        self.thread_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.console.print("[yellow]Started new conversation[/yellow]")
    
    def chat(self):
        """Interactive chat interface"""
        self.console.print(Panel.fit(
            "[bold blue]🌾 Landuse Agent with Memory[/bold blue]\n"
            "I remember our conversation! Ask follow-up questions naturally.\n"
            "Commands: 'new' (new conversation), 'exit' (quit)",
            border_style="blue"
        ))
        
        while True:
            try:
                # Get user input
                question = Prompt.ask("\n[green]Ask[/green]")
                
                if question.lower() == 'exit':
                    self.console.print("\n[yellow]Goodbye! 👋[/yellow]")
                    break
                elif question.lower() == 'new':
                    self.new_conversation()
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
    import argparse
    
    parser = argparse.ArgumentParser(description="Landuse Query Agent with Memory")
    parser.add_argument("--memory", choices=["sqlite", "memory"], default="sqlite",
                      help="Memory backend type")
    parser.add_argument("--memory-path", default="landuse_conversations.db",
                      help="Path for SQLite memory storage")
    parser.add_argument("--new", action="store_true",
                      help="Start a new conversation")
    
    args = parser.parse_args()
    
    # Create and run agent
    agent = LanduseMemoryAgent(
        memory_type=args.memory,
        memory_path=args.memory_path
    )
    
    if args.new:
        agent.new_conversation()
    
    agent.chat()

if __name__ == "__main__":
    main()