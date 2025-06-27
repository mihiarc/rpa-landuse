#!/usr/bin/env python3
"""
Compare traditional LangChain agent vs LangGraph agent
Demonstrates the benefits of the modern LangGraph approach
"""

import os
import time
from typing import Dict, Any, List
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns

# Add src to path for imports
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))

from landuse.agents import LanduseAgent
from landuse.agents.langgraph_agent import LangGraphLanduseAgent, LandGraphConfig

console = Console()


def benchmark_agent(agent, queries: List[str], agent_name: str) -> Dict[str, Any]:
    """Benchmark an agent with a set of queries"""
    console.print(f"\n🔬 Benchmarking {agent_name}...")
    
    results = {
        "agent_name": agent_name,
        "total_time": 0,
        "successful_queries": 0,
        "failed_queries": 0,
        "average_time": 0,
        "query_results": []
    }
    
    for i, query in enumerate(queries, 1):
        console.print(f"   Query {i}/{len(queries)}: {query[:50]}...")
        
        start_time = time.time()
        try:
            if hasattr(agent, 'query'):
                response = agent.query(query)
            else:
                response = "Agent doesn't support query method"
            
            execution_time = time.time() - start_time
            
            # Check if response indicates success
            if "❌" not in response and "Error" not in response:
                results["successful_queries"] += 1
                status = "✅"
            else:
                results["failed_queries"] += 1
                status = "❌"
            
            results["total_time"] += execution_time
            results["query_results"].append({
                "query": query,
                "time": execution_time,
                "status": status,
                "response_length": len(response)
            })
            
        except Exception as e:
            execution_time = time.time() - start_time
            results["failed_queries"] += 1
            results["total_time"] += execution_time
            results["query_results"].append({
                "query": query,
                "time": execution_time,
                "status": "❌",
                "error": str(e)
            })
    
    # Calculate average
    if len(queries) > 0:
        results["average_time"] = results["total_time"] / len(queries)
    
    return results


def display_comparison(traditional_results: Dict[str, Any], langgraph_results: Dict[str, Any]):
    """Display comparison results"""
    console.print("\n" + "="*80)
    console.print(Panel(
        "[bold cyan]🏁 Agent Performance Comparison[/bold cyan]",
        border_style="cyan"
    ))
    
    # Summary table
    table = Table(title="📊 Performance Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="yellow", no_wrap=True)
    table.add_column("Traditional LangChain", justify="right", style="blue")
    table.add_column("LangGraph", justify="right", style="green")
    table.add_column("Improvement", justify="right", style="magenta")
    
    # Calculate improvements
    def calc_improvement(old_val, new_val, higher_is_better=True):
        if old_val == 0:
            return "N/A"
        if higher_is_better:
            improvement = ((new_val - old_val) / old_val) * 100
            return f"+{improvement:.1f}%" if improvement > 0 else f"{improvement:.1f}%"
        else:
            improvement = ((old_val - new_val) / old_val) * 100
            return f"-{improvement:.1f}%" if improvement > 0 else f"+{-improvement:.1f}%"
    
    # Add rows
    table.add_row(
        "Successful Queries",
        str(traditional_results["successful_queries"]),
        str(langgraph_results["successful_queries"]),
        calc_improvement(traditional_results["successful_queries"], langgraph_results["successful_queries"])
    )
    
    table.add_row(
        "Failed Queries",
        str(traditional_results["failed_queries"]),
        str(langgraph_results["failed_queries"]),
        calc_improvement(traditional_results["failed_queries"], langgraph_results["failed_queries"], False)
    )
    
    table.add_row(
        "Total Time (s)",
        f"{traditional_results['total_time']:.2f}",
        f"{langgraph_results['total_time']:.2f}",
        calc_improvement(traditional_results["total_time"], langgraph_results["total_time"], False)
    )
    
    table.add_row(
        "Average Time (s)",
        f"{traditional_results['average_time']:.2f}",
        f"{langgraph_results['average_time']:.2f}",
        calc_improvement(traditional_results["average_time"], langgraph_results["average_time"], False)
    )
    
    console.print(table)
    
    # Detailed results
    console.print("\n📋 Detailed Query Results:")
    
    for i, (trad_result, lg_result) in enumerate(zip(
        traditional_results["query_results"], 
        langgraph_results["query_results"]
    ), 1):
        query = trad_result["query"]
        
        detail_table = Table(title=f"Query {i}: {query[:60]}...", show_header=True)
        detail_table.add_column("Agent", style="yellow")
        detail_table.add_column("Status", justify="center")
        detail_table.add_column("Time (s)", justify="right", style="blue")
        detail_table.add_column("Response Length", justify="right", style="green")
        
        detail_table.add_row(
            "Traditional",
            trad_result["status"],
            f"{trad_result['time']:.2f}",
            str(trad_result.get("response_length", "N/A"))
        )
        
        detail_table.add_row(
            "LangGraph",
            lg_result["status"],
            f"{lg_result['time']:.2f}",
            str(lg_result.get("response_length", "N/A"))
        )
        
        console.print(detail_table)
        console.print()


def main():
    """Main comparison function"""
    console.print(Panel(
        "[bold cyan]🔬 LangChain vs LangGraph Agent Comparison[/bold cyan]\n\n"
        "[yellow]This script compares the performance and capabilities of:[/yellow]\n"
        "• Traditional LangChain REACT Agent\n"
        "• Modern LangGraph State-based Agent\n\n"
        "[green]Testing with realistic landuse queries...[/green]",
        title="🚀 Agent Benchmark",
        border_style="blue"
    ))
    
    # Test queries
    test_queries = [
        "How much agricultural land is being lost?",
        "Which states have the most urban expansion?",
        "Compare forest loss between RCP45 and RCP85 scenarios",
        "What are the top 5 counties for land use changes in Texas?",
        "Show me crop to pasture transitions in California"
    ]
    
    console.print("\n📝 Test Queries:")
    for i, query in enumerate(test_queries, 1):
        console.print(f"   {i}. {query}")
    
    # Check if database exists
    db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
    if not Path(db_path).exists():
        console.print(f"\n❌ Database not found at {db_path}")
        console.print("Please run the data conversion script first:")
        console.print("uv run python scripts/converters/convert_to_duckdb.py")
        return
    
    try:
        # Initialize agents
        console.print("\n🔧 Initializing agents...")
        
        # Traditional agent
        console.print("   Initializing Traditional LangChain agent...")
        traditional_agent = LanduseAgent()
        
        # LangGraph agent
        console.print("   Initializing LangGraph agent...")
        langgraph_config = LandGraphConfig(
            db_path=db_path,
            verbose=False,
            max_iterations=6
        )
        langgraph_agent = LangGraphLanduseAgent(langgraph_config)
        
        # Run benchmarks
        traditional_results = benchmark_agent(traditional_agent, test_queries, "Traditional LangChain")
        langgraph_results = benchmark_agent(langgraph_agent, test_queries, "LangGraph")
        
        # Display results
        display_comparison(traditional_results, langgraph_results)
        
        # Key differences panel
        differences_panel = Panel(
            """[bold cyan]🔍 Key Architectural Differences[/bold cyan]

[yellow]Traditional LangChain REACT Agent:[/yellow]
• Linear execution with tool calls
• Limited state management
• Basic error handling
• No conversation memory
• Fixed iteration patterns

[green]LangGraph State-Based Agent:[/green]
• Graph-based execution flow
• Rich state management with TypedDict
• Advanced error handling and recovery
• Built-in conversation memory (checkpointing)
• Flexible node composition
• Streaming support for real-time updates
• Better tool orchestration

[magenta]Benefits of LangGraph:[/magenta]
• More reliable execution
• Better conversation continuity
• Enhanced debugging capabilities
• Easier to extend and customize
• Production-ready features""",
            title="🏗️ Architecture Comparison",
            border_style="green"
        )
        console.print(differences_panel)
        
        # Recommendations
        recommendations_panel = Panel(
            """[bold cyan]📈 Recommendations[/bold cyan]

[green]✅ Use LangGraph for:[/green]
• Production applications
• Complex multi-step workflows
• Applications requiring conversation memory
• Real-time streaming responses
• Advanced error recovery

[yellow]⚠️ Consider Traditional LangChain for:[/yellow]
• Simple, one-off queries
• Prototyping and experimentation
• Very resource-constrained environments

[bold green]🚀 Migration Path:[/bold green]
1. Test LangGraph agent with your queries
2. Gradually migrate high-value use cases
3. Leverage conversation memory for better UX
4. Implement streaming for real-time responses""",
            title="💡 Migration Strategy",
            border_style="blue"
        )
        console.print(recommendations_panel)
        
    except Exception as e:
        console.print(f"\n❌ Error during comparison: {e}")
        console.print("Make sure you have the required API keys configured:")
        console.print("- ANTHROPIC_API_KEY or OPENAI_API_KEY")
        console.print("- Proper database path in LANDUSE_DB_PATH")


if __name__ == "__main__":
    main()