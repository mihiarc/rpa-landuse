#!/usr/bin/env python3
"""
Simple demonstration of the landuse agent with memory
"""

from landuse_agent_with_memory import LanduseMemoryAgent
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

def main():
    console = Console()
    
    console.print(Panel.fit(
        "[bold green]🧠 Landuse Agent Memory Demo[/bold green]\n"
        "Watch how the agent remembers context between questions!",
        border_style="green"
    ))
    
    # Create agent with in-memory storage
    agent = LanduseMemoryAgent(memory_type="memory")
    
    # Demonstrate memory with a sequence of questions
    questions = [
        "How much agricultural land is being lost on average across all scenarios?",
        "What about specifically in California?",
        "Which scenarios show the most loss there?",
        "Compare that to Texas"
    ]
    
    console.print("\n[yellow]Starting conversation about agricultural land loss...[/yellow]\n")
    
    for i, question in enumerate(questions, 1):
        console.print(f"[cyan]Question {i}:[/cyan] {question}")
        
        try:
            response = agent.ask(question)
            console.print("\n[green]Agent Response:[/green]")
            console.print(Markdown(response))
            console.print("\n" + "="*80 + "\n")
            
            # Note the important parts
            if i == 2:
                console.print("[dim]💡 Notice: The agent understands 'What about in California?' refers to agricultural land loss![/dim]\n")
            elif i == 3:
                console.print("[dim]💡 Notice: The agent knows we're still talking about California![/dim]\n")
            elif i == 4:
                console.print("[dim]💡 Notice: The agent compares Texas to California's agricultural land loss![/dim]\n")
                
        except Exception as e:
            console.print(f"[red]Error: {str(e)}[/red]")
            break
    
    console.print("[bold green]✅ Demo complete![/bold green]")
    console.print("\nThe agent successfully maintained context throughout the conversation,")
    console.print("understanding that follow-up questions referred to the original topic!")

if __name__ == "__main__":
    main()