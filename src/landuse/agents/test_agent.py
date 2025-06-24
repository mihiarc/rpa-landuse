#!/usr/bin/env python3
"""
Test script for the SQL Query Agent with Rich terminal output
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich.syntax import Syntax
from rich import print as rprint

# Initialize console
console = Console()

# Create sample data files for testing
data_dir = Path("./data")
data_dir.mkdir(exist_ok=True)

console.print(Panel.fit("🚀 [bold blue]Creating Sample Data Files[/bold blue]", border_style="blue"))

# Create sample CSV with progress tracking
with console.status("[bold green]Creating sample CSV data...", spinner="dots"):
    csv_data = pd.DataFrame({
        'id': range(1, 101),
        'value': np.random.randint(10, 1000, 100),
        'category': np.random.choice(['A', 'B', 'C', 'D'], 100),
        'price': np.random.uniform(10.0, 500.0, 100),
        'date': pd.date_range('2024-01-01', periods=100, freq='D')
    })
    csv_data.to_csv(data_dir / 'sample_data.csv', index=False)
console.print("✅ [green]sample_data.csv created[/green]")

# Create sample JSON
with console.status("[bold green]Creating JSON inventory data...", spinner="dots"):
    json_data = [
        {'name': f'Item_{i}', 'quantity': np.random.randint(1, 50), 'location': f'Warehouse_{np.random.randint(1, 5)}'}
        for i in range(50)
    ]
    with open(data_dir / 'inventory.json', 'w') as f:
        json.dump(json_data, f, indent=2)
console.print("✅ [green]inventory.json created[/green]")

# Create sample Parquet
with console.status("[bold green]Creating Parquet sensor data...", spinner="dots"):
    parquet_data = pd.DataFrame({
        'timestamp': pd.date_range('2024-01-01', periods=1000, freq='h'),
        'temperature': np.random.normal(20, 5, 1000),
        'humidity': np.random.uniform(30, 80, 1000),
        'sensor_id': np.random.choice(['S001', 'S002', 'S003'], 1000)
    })
    parquet_data.to_parquet(data_dir / 'sensor_data.parquet', compression='snappy')
console.print("✅ [green]sensor_data.parquet created[/green]")

# Display created files in a table
console.print("\n")
table = Table(title="📁 Created Sample Files", show_header=True, header_style="bold magenta")
table.add_column("File", style="cyan", no_wrap=True)
table.add_column("Size", justify="right", style="green")
table.add_column("Description", style="yellow")

files_info = [
    ("sample_data.csv", "CSV with 100 rows of mixed data types"),
    ("inventory.json", "JSON array with 50 inventory items"),
    ("sensor_data.parquet", "Parquet with 1000 sensor readings")
]

for filename, description in files_info:
    file_path = data_dir / filename
    size = f"{file_path.stat().st_size / 1024:.2f} KB"
    table.add_row(filename, size, description)

console.print(table)

# Display example queries
console.print("\n")
example_panel = Panel(
    """[bold cyan]Example Queries:[/bold cyan]

[bold yellow]File Operations:[/bold yellow]
• [green]'List all files in the data directory'[/green]
• [green]'Analyze the sample_data.csv file'[/green]
• [green]'Transform inventory.json to Parquet format'[/green]
• [green]'Query sensor_data.parquet: SELECT avg(temperature) FROM data GROUP BY sensor_id'[/green]

[bold yellow]Database Operations:[/bold yellow]
• [green]'Show me the tables in processed/landuse_transitions.db'[/green]
• [green]'Describe the landuse_transitions table'[/green]
• [green]'Get database statistics for processed/landuse_projections.db'[/green]
• [green]'Query processed/landuse_transitions.db: SELECT scenario, COUNT(*) FROM landuse_transitions GROUP BY scenario LIMIT 10'[/green]

[bold yellow]Data Analysis:[/bold yellow]
• [green]'Optimize storage for sample_data.csv'[/green]
• [green]'Create a correlation plot from sample_data.csv'[/green]""",
    title="💡 Try These Commands",
    border_style="cyan"
)
console.print(example_panel)

# Import and run the agent
from sql_query_agent import SQLQueryAgent

if __name__ == "__main__":
    console.rule("[bold cyan]SQL Query Agent[/bold cyan]", style="cyan")
    
    agent = SQLQueryAgent()
    
    # Override the chat method to use rich
    original_run = agent.run
    
    def rich_run(query):
        with console.status(f"[bold yellow]Processing: {query}[/bold yellow]", spinner="dots"):
            result = original_run(query)
        return result
    
    agent.run = rich_run
    
    # Enhanced chat loop with rich
    console.print(f"\n🔍 [bold]SQL Agent initialized. Database directory:[/bold] [cyan]{agent.root_dir}[/cyan]")
    console.print("Type [bold red]'exit'[/bold red] to quit, [bold yellow]'help'[/bold yellow] for SQL commands\n")
    
    while True:
        try:
            user_input = console.input("[bold cyan]SQL>[/bold cyan] ").strip()
            
            if user_input.lower() == 'exit':
                console.print("\n[bold red]👋 Happy querying![/bold red]")
                break
            elif user_input.lower() == 'help':
                help_panel = Panel(
                    """[bold cyan]🔍 SQL Query Agent Capabilities:[/bold cyan]

[bold yellow]🗂️ Database Schema Exploration:[/bold yellow]
  • List all tables with row counts
  • Describe table structures, columns, indexes
  • Get comprehensive database statistics

[bold yellow]🔍 SQL Query Execution:[/bold yellow]
  • Execute SQL queries on SQLite databases
  • Query data files (CSV, JSON, Parquet) using SQL
  • Smart query optimization and suggestions

[bold yellow]💾 Data Export & Analysis:[/bold yellow]
  • Export query results to various formats
  • Statistical analysis of query results

[bold green]🚀 Example SQL Commands:[/bold green]
  • [white]"Show me all tables in processed/landuse_transitions.db"[/white]
  • [white]"Describe the landuse_transitions table"[/white]
  • [white]"Query processed/landuse_transitions.db: SELECT scenario, COUNT(*) FROM landuse_transitions GROUP BY scenario LIMIT 10"[/white]
  • [white]"Get database statistics for processed/landuse_projections.db"[/white]""",
                    title="📚 SQL Query Help",
                    border_style="yellow"
                )
                console.print(help_panel)
            else:
                console.print()
                response = agent.run(user_input)
                
                # Format the response nicely
                if "Error" in response:
                    console.print(Panel(response, title="❌ SQL Error", border_style="red"))
                elif "```" in response:
                    # Extract code blocks
                    parts = response.split("```")
                    for i, part in enumerate(parts):
                        if i % 2 == 0:
                            console.print(part)
                        else:
                            # Try to determine language
                            lines = part.split('\n')
                            lang = lines[0] if lines[0] else "sql"
                            code = '\n'.join(lines[1:]) if len(lines) > 1 else part
                            syntax = Syntax(code, lang, theme="monokai", line_numbers=True)
                            console.print(syntax)
                else:
                    console.print(Panel(response, title="🔍 Query Results", border_style="green"))
                console.print()
        
        except KeyboardInterrupt:
            console.print("\n[yellow]Use 'exit' to quit properly[/yellow]")
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {str(e)}")