#!/usr/bin/env python3
"""
Quick Start Script for Landuse Natural Language Agent
Checks environment setup and provides instructions for getting started
"""

import os
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()


def check_api_keys():
    """Check if required API keys are configured"""
    # Check multiple possible locations for API keys
    api_key_sources = []
    
    # 1. Check config/.env (recommended)
    config_env = Path("config/.env")
    if config_env.exists():
        from dotenv import load_dotenv
        load_dotenv(config_env)
        api_key_sources.append("config/.env")
    
    # 2. Check root .env
    root_env = Path(".env")
    if root_env.exists():
        from dotenv import load_dotenv
        load_dotenv(root_env, override=True)
        api_key_sources.append(".env")
    
    # 3. Check environment variables
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    return {
        "openai": openai_key,
        "anthropic": anthropic_key,
        "sources": api_key_sources
    }


def check_database():
    """Check if the landuse database exists"""
    db_path = Path(os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'))
    return db_path.exists(), db_path


def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import langchain
        import duckdb
        import pandas
        import rich
        return True
    except ImportError:
        return False


def main():
    """Run the quick start checks and provide instructions"""
    console.print("\n[bold cyan]🚀 Landuse Natural Language Agent - Quick Start[/bold cyan]\n")
    
    # Create status table
    status_table = Table(title="Environment Check", show_header=True)
    status_table.add_column("Component", style="cyan")
    status_table.add_column("Status", style="green")
    status_table.add_column("Details")
    
    all_good = True
    
    # 1. Check dependencies
    deps_ok = check_dependencies()
    if deps_ok:
        status_table.add_row(
            "Dependencies",
            "✅ Installed",
            "All required packages found"
        )
    else:
        status_table.add_row(
            "Dependencies",
            "❌ Missing",
            "Run: [yellow]uv sync[/yellow]"
        )
        all_good = False
    
    # 2. Check API keys
    api_keys = check_api_keys()
    
    # OpenAI API Key
    if api_keys["openai"]:
        key_preview = api_keys["openai"][:8] + "..." + api_keys["openai"][-4:]
        status_table.add_row(
            "OpenAI API Key",
            "✅ Found",
            f"[dim]{key_preview}[/dim]"
        )
    else:
        status_table.add_row(
            "OpenAI API Key",
            "❌ Missing",
            "Required for GPT-4 models"
        )
        all_good = False
    
    # Anthropic API Key (optional)
    if api_keys["anthropic"]:
        key_preview = api_keys["anthropic"][:8] + "..." + api_keys["anthropic"][-4:]
        status_table.add_row(
            "Anthropic API Key",
            "✅ Found",
            f"[dim]{key_preview}[/dim] (for Claude models)"
        )
    else:
        status_table.add_row(
            "Anthropic API Key",
            "⚠️  Optional",
            "Add for Claude model support"
        )
    
    # API Key Sources
    if api_keys["sources"]:
        status_table.add_row(
            "Config Location",
            "📁 Found",
            ", ".join(api_keys["sources"])
        )
    
    # 3. Check database
    db_exists, db_path = check_database()
    if db_exists:
        status_table.add_row(
            "Database",
            "✅ Found",
            f"[dim]{db_path}[/dim]"
        )
    else:
        status_table.add_row(
            "Database",
            "❌ Missing",
            "Run: [yellow]uv run python scripts/converters/convert_to_duckdb.py[/yellow]"
        )
        all_good = False
    
    console.print(status_table)
    console.print()
    
    # Provide instructions based on status
    if not all_good:
        console.print(Panel.fit(
            "[bold red]⚠️  Setup Required[/bold red]\n\n"
            "Please complete the following steps:\n\n"
            "1. **Install dependencies** (if missing):\n"
            "   [cyan]uv sync[/cyan]\n\n"
            "2. **Configure API keys** (if missing):\n"
            "   [cyan]cp .env.example config/.env[/cyan]\n"
            "   Then edit [cyan]config/.env[/cyan] and add your API keys\n\n"
            "3. **Create database** (if missing):\n"
            "   [cyan]uv run python scripts/converters/convert_to_duckdb.py[/cyan]\n\n"
            "After completing setup, run this script again to verify.",
            border_style="red"
        ))
    else:
        # Everything is ready!
        # Check if shortcut command is available
        try:
            import subprocess
            result = subprocess.run(["uv", "run", "which", "landuse-agent"], 
                                  capture_output=True, text=True)
            has_shortcut = result.returncode == 0
        except:
            has_shortcut = False
        
        if has_shortcut:
            start_text = (
                "[bold green]✅ Ready to go![/bold green]\n\n"
                "Start the agent with:\n"
                "[bold cyan]uv run landuse-agent[/bold cyan]\n\n"
                "Or use the full path:\n"
                "[bold cyan]uv run python src/landuse/agents/landuse_natural_language_agent.py[/bold cyan]"
            )
        else:
            start_text = (
                "[bold green]✅ Ready to go![/bold green]\n\n"
                "Start the agent with:\n"
                "[bold cyan]uv run python src/landuse/agents/landuse_natural_language_agent.py[/bold cyan]"
            )
        
        console.print(Panel.fit(start_text, border_style="green"))
        
        # Show example queries
        console.print("\n[bold]Example queries to try:[/bold]")
        examples = [
            "How much agricultural land is being lost?",
            "Which scenarios show the most forest loss?",
            "Compare urban expansion between California and Texas",
            "What are the biggest land use changes over time?"
        ]
        for example in examples:
            console.print(f"  • [yellow]{example}[/yellow]")
        
        console.print("\n[dim]Type 'exit' to quit, 'help' for more info, 'schema' for database details[/dim]\n")
    
    # Show additional resources
    if all_good:
        console.print(Panel(
            "[bold]📚 Additional Resources[/bold]\n\n"
            "• **Documentation**: [cyan]mkdocs serve[/cyan] (http://localhost:8000)\n"
            "• **Database UI**: [cyan]duckdb data/processed/landuse_analytics.duckdb -ui[/cyan]\n"
            "• **Run tests**: [cyan]uv run pytest tests/[/cyan]\n"
            "• **Project info**: See README.md and CLAUDE.md",
            title="Next Steps",
            border_style="blue"
        ))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Quick start cancelled[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)