#!/usr/bin/env python3
"""
Test script to demonstrate memory capabilities of the landuse agent
"""

from landuse_agent_with_memory import LanduseMemoryAgent
from rich.console import Console
from rich.panel import Panel

def main():
    console = Console()
    
    console.print(Panel.fit(
        "[bold green]🧠 Testing Landuse Agent Memory[/bold green]\n"
        "This demonstrates how the agent remembers context between questions",
        border_style="green"
    ))
    
    # Create agent with in-memory storage for testing
    agent = LanduseMemoryAgent(memory_type="memory")
    
    # Test questions that build on each other
    test_conversations = [
        {
            "title": "Agricultural Land Loss Analysis",
            "questions": [
                "How much agricultural land is being lost on average?",
                "What about specifically in California?",
                "Which scenarios show the most loss?",
                "Compare that to Texas"
            ]
        },
        {
            "title": "Forest Transitions",
            "questions": [
                "Show me forest loss by state",
                "Focus on the top 5 states",
                "What's happening in the RCP85 scenarios?",
                "How does that compare to RCP45?"
            ]
        }
    ]
    
    for conversation in test_conversations:
        console.print(f"\n[bold yellow]--- {conversation['title']} ---[/bold yellow]")
        
        # Start new conversation
        agent.new_conversation()
        
        for i, question in enumerate(conversation['questions'], 1):
            console.print(f"\n[cyan]Question {i}:[/cyan] {question}")
            
            try:
                response = agent.ask(question)
                console.print(f"\n[green]Response:[/green]\n{response}")
                console.print("\n" + "-" * 80)
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
    
    console.print("\n[bold green]✅ Memory test complete![/bold green]")
    console.print("\nNotice how follow-up questions like 'What about in California?' ")
    console.print("understand the context from previous questions!")

if __name__ == "__main__":
    main()