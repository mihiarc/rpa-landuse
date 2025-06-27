#!/usr/bin/env python3
"""
Test the prompt modes information display after first question
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from landuse.agents import LanduseAgent
from rich.console import Console

console = Console()


def test_first_question_info():
    """Test that prompt modes info appears after first question"""
    console.print("\n[bold cyan]Testing Prompt Modes Info Display[/bold cyan]")
    console.print("-" * 50)
    
    # Create a standard agent
    agent = LanduseAgent()
    
    # Simulate what happens in chat mode
    console.print("\n[dim]Simulating first question response...[/dim]\n")
    
    # Call the info display method directly
    agent._show_prompt_modes_info()
    
    console.print("\n✅ Prompt modes info displayed successfully!")


def test_command_line_args():
    """Show how command line arguments work"""
    console.print("\n[bold cyan]Command Line Usage Examples[/bold cyan]")
    console.print("-" * 50)
    
    examples = [
        ("Standard mode (default)", "landuse-agent"),
        ("Executive summary mode", "landuse-agent --executive"),
        ("Detailed analysis", "landuse-agent --detailed"),
        ("Agricultural focus", "landuse-agent --agricultural"),
        ("Climate analysis with maps", "landuse-agent --climate --maps"),
        ("Executive urban planning", "landuse-agent --executive --urban --maps"),
        ("Show help", "landuse-agent --help")
    ]
    
    for desc, cmd in examples:
        console.print(f"\n[yellow]{desc}:[/yellow]")
        console.print(f"[cyan]$ {cmd}[/cyan]")


def demonstrate_programmatic_usage():
    """Show programmatic usage"""
    console.print("\n[bold cyan]Programmatic Usage Examples[/bold cyan]")
    console.print("-" * 50)
    
    console.print("""
[yellow]In Python scripts or Jupyter notebooks:[/yellow]

```python
from landuse.agents import LanduseAgent

# Executive summary for policy makers
exec_agent = LanduseAgent(analysis_style="executive")
response = exec_agent.query("What are the key agricultural risks?")

# Detailed climate analysis
climate_agent = LanduseAgent(
    analysis_style="detailed",
    domain_focus="climate",
    enable_maps=True
)
response = climate_agent.query("Compare RCP scenarios for forest loss")

# Agricultural specialist
ag_agent = LanduseAgent(domain_focus="agricultural")
response = ag_agent.query("Which states are losing the most cropland?")
```
""")


def main():
    """Run all demonstrations"""
    console.print("[bold yellow]🎯 Prompt Modes Information System[/bold yellow]")
    
    test_first_question_info()
    test_command_line_args()
    demonstrate_programmatic_usage()
    
    console.print("\n[bold green]✨ Summary[/bold green]")
    console.print("-" * 50)
    console.print("""
The agent now:
1. Shows available prompt modes after the first question
2. Supports command-line arguments for different modes
3. Can be configured programmatically with different styles

Users will discover these powerful features naturally!
""")


if __name__ == "__main__":
    main()