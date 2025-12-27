#!/usr/bin/env python3
"""
Main entry point for RPA Land Use Analytics agents.
Provides command-line interface for the natural language agent.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

from landuse.agents.landuse_agent import LandUseAgent
from landuse.core.app_config import AppConfig


def main() -> None:
    """Main entry point for the RPA analytics agent."""
    parser = argparse.ArgumentParser(
        description="RPA Land Use Analytics - Natural Language Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rpa-analytics                    # Start interactive session
  rpa-analytics --model claude-sonnet-4-5-20250929  # Use specific model
  rpa-analytics --verbose          # Enable verbose output

For more information, visit: https://github.com/yourusername/rpa-landuse
        """,
    )

    parser.add_argument("--config-file", type=str, help="Path to configuration file (.env format)", metavar="PATH")

    parser.add_argument("--model", type=str, help="Model name to use (overrides config)", metavar="MODEL")

    parser.add_argument("--temperature", type=float, help="Model temperature (0.0-2.0)", metavar="TEMP")

    parser.add_argument("--max-iterations", type=int, help="Maximum agent iterations", metavar="N")

    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")

    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    parser.add_argument("--db-path", type=str, help="Path to DuckDB database file", metavar="PATH")

    parser.add_argument("--version", action="version", version="RPA Land Use Analytics 0.1.0")

    args = parser.parse_args()

    console = Console()

    try:
        # Load configuration file if specified
        if args.config_file:
            config_path = Path(args.config_file)
            if not config_path.exists():
                console.print(f"[red]Error: Configuration file not found: {args.config_file}[/red]")
                sys.exit(1)
            # TODO: Implement config file loading

        # Create configuration with overrides
        config_overrides = {}
        if args.model:
            config_overrides["llm__model_name"] = args.model
        if args.temperature is not None:
            config_overrides["llm__temperature"] = args.temperature
        if args.max_iterations:
            config_overrides["agent__max_iterations"] = args.max_iterations
        if args.verbose:
            config_overrides["agent__verbose"] = True
        if args.debug:
            config_overrides["agent__debug"] = True
        if args.db_path:
            config_overrides["database__path"] = args.db_path

        # Create agent configuration
        config = AppConfig.from_env(**config_overrides)

        # Initialize and start the agent
        with LandUseAgent(config=config) as agent:
            if args.verbose:
                console.print("[green]Starting RPA Land Use Analytics Agent...[/green]")
                console.print(f"Model: {config.llm.model_name}")
                console.print(f"Database: {config.database.path}")
                console.print(f"Max iterations: {config.agent.max_iterations}")
                console.print()

            agent.chat()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        sys.exit(0)
    except FileNotFoundError as e:
        console.print(f"[red]Database file not found: {e}[/red]")
        console.print("[yellow]Make sure you have run the data conversion script first.[/yellow]")
        console.print("[yellow]See the installation guide for details.[/yellow]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        if args.debug:
            console.print_exception()
        else:
            console.print(f"[red]Error: {e}[/red]")
            console.print("[yellow]Use --debug for more details.[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
