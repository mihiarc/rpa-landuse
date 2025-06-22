#!/usr/bin/env python3
"""
Test script for the Landuse Natural Language Query Agent
Demonstrates various natural language queries
"""

import sys
from pathlib import Path

# Add the agents directory to the path
sys.path.append(str(Path(__file__).parent))

from landuse_natural_language_agent import LanduseNaturalLanguageAgent
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

def test_landuse_agent():
    """Test the landuse query agent with sample questions"""
    console = Console()
    
    console.print(Panel.fit(
        "🧪 [bold blue]Testing Landuse Natural Language Query Agent[/bold blue]\n"
        "[yellow]Running sample queries to demonstrate capabilities[/yellow]",
        border_style="blue"
    ))
    
    # Initialize agent
    try:
        agent = LanduseNaturalLanguageAgent()
        console.print("✅ [green]Agent initialized successfully[/green]\n")
    except Exception as e:
        console.print(f"❌ [red]Failed to initialize agent: {str(e)}[/red]")
        return
    
    # Test queries
    test_queries = [
        "Which scenarios show the most agricultural land loss?",
        "How much farmland is being converted to urban areas?",
        "Compare forest loss between RCP45 and RCP85 scenarios",
        "Which states have the most urban expansion?",
        "Show me the top 5 land use transitions by total acres"
    ]
    
    for i, query in enumerate(test_queries, 1):
        console.print(Panel(
            f"[bold cyan]Test Query {i}:[/bold cyan] {query}",
            border_style="cyan"
        ))
        
        try:
            response = agent.query(query)
            response_md = Markdown(response)
            console.print(Panel(response_md, title="🔍 Results", border_style="green"))
        except Exception as e:
            console.print(Panel(f"❌ Error: {str(e)}", border_style="red"))
        
        console.print()
        
        # Ask user if they want to continue
        if i < len(test_queries):
            user_input = console.input("[dim]Press Enter to continue to next query, or 'q' to quit: [/dim]")
            if user_input.lower() == 'q':
                break
    
    console.print(Panel.fit(
        "🎉 [bold green]Testing Complete![/bold green]\n"
        "[yellow]Try running the agent interactively:[/yellow]\n"
        "[white]uv run python scripts/agents/landuse_natural_language_agent.py[/white]",
        border_style="green"
    ))

if __name__ == "__main__":
    test_landuse_agent() 