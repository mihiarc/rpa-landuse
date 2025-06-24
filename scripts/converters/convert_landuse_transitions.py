#!/usr/bin/env python3
"""
Convert county landuse projections JSON to SQLite database with land use transitions focus
Follows the same approach as the Parquet converter - creating a long format with transitions
"""

import json
import sqlite3
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
import time
from decimal import Decimal

console = Console()

# Land use type mapping
LAND_USE_MAP = {
    'cr': 'Crop',
    'ps': 'Pasture',
    'rg': 'Range',
    'fr': 'Forest',
    'ur': 'Urban',
    't1': 'Total',  # Total row sum
    't2': 'Total'   # Total column sum
}

def extract_end_year(year_range):
    """Extract the end year from a year range string (e.g., '2012-2020' -> 2020)."""
    return int(year_range.split('-')[1])

def convert_value(value):
    """Convert Decimal or other numeric types to float"""
    if isinstance(value, Decimal):
        return float(value)
    return float(value) if value is not None else 0.0

def process_matrix_data(matrix_data, scenario, year, year_range, fips):
    """Convert the matrix data to transition records."""
    transitions = []
    
    for row in matrix_data:
        from_type = LAND_USE_MAP.get(row.get('_row', ''), row.get('_row', ''))
        
        if from_type != 'Total':  # Skip the total row
            for col, value in row.items():
                if col not in ['_row', 't1'] and col in LAND_USE_MAP:  # Skip row identifier and total
                    to_type = LAND_USE_MAP[col]
                    if to_type != 'Total':  # Skip total column
                        acres = convert_value(value)
                        if acres > 0:  # Only include non-zero transitions
                            transitions.append({
                                'scenario': scenario,
                                'year': year,
                                'year_range': year_range,
                                'fips': fips,
                                'from_land_use': from_type,
                                'to_land_use': to_type,
                                'acres': acres
                            })
    
    return transitions

def convert_to_transitions_db(json_path, db_path, table_name='landuse_transitions'):
    """Convert nested JSON structure to SQLite database with land use transitions"""
    start_time = time.time()
    
    console.print(Panel.fit("🔍 [bold blue]Converting to Land Use Transitions Database...[/bold blue]", border_style="blue"))
    
    # Create database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop table if exists
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    # Create table for transitions
    create_table_sql = f"""
    CREATE TABLE {table_name} (
        scenario TEXT NOT NULL,
        year INTEGER NOT NULL,
        year_range TEXT NOT NULL,
        fips TEXT NOT NULL,
        from_land_use TEXT NOT NULL,
        to_land_use TEXT NOT NULL,
        acres REAL NOT NULL,
        PRIMARY KEY (scenario, year_range, fips, from_land_use, to_land_use)
    )
    """
    cursor.execute(create_table_sql)
    console.print(f"[green]✓ Created table '{table_name}' for land use transitions[/green]")
    
    # Process JSON file
    console.print("\n[bold blue]Processing land use transitions...[/bold blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        # Load JSON data
        console.print("[cyan]Loading JSON data...[/cyan]")
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        scenarios = list(data.keys())
        console.print(f"[cyan]Found {len(scenarios)} climate scenarios[/cyan]")
        
        task = progress.add_task("Processing transitions...", total=len(scenarios))
        
        batch = []
        total_transitions = 0
        batch_size = 10000
        
        for scenario_idx, scenario in enumerate(scenarios):
            scenario_data = data[scenario]
            progress.update(task, description=f"Processing {scenario}...")
            
            for year_range in scenario_data:
                year = extract_end_year(year_range)
                year_data = scenario_data[year_range]
                
                for fips in year_data:
                    county_data = year_data[fips]
                    
                    # Process matrix data to get transitions
                    transitions = process_matrix_data(county_data, scenario, year, year_range, fips)
                    
                    for trans in transitions:
                        batch.append((
                            trans['scenario'],
                            trans['year'],
                            trans['year_range'],
                            trans['fips'],
                            trans['from_land_use'],
                            trans['to_land_use'],
                            trans['acres']
                        ))
                        
                        if len(batch) >= batch_size:
                            cursor.executemany(
                                f"INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?)",
                                batch
                            )
                            conn.commit()
                            total_transitions += len(batch)
                            batch = []
            
            progress.update(task, advance=1)
        
        # Insert remaining records
        if batch:
            cursor.executemany(
                f"INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?)",
                batch
            )
            conn.commit()
            total_transitions += len(batch)
    
    # Create indexes for efficient querying
    console.print("\n[bold blue]Creating indexes...[/bold blue]")
    
    indexes = [
        f"CREATE INDEX idx_{table_name}_scenario ON {table_name}(scenario)",
        f"CREATE INDEX idx_{table_name}_year ON {table_name}(year)",
        f"CREATE INDEX idx_{table_name}_fips ON {table_name}(fips)",
        f"CREATE INDEX idx_{table_name}_from ON {table_name}(from_land_use)",
        f"CREATE INDEX idx_{table_name}_to ON {table_name}(to_land_use)",
        f"CREATE INDEX idx_{table_name}_scenario_year ON {table_name}(scenario, year)",
        f"CREATE INDEX idx_{table_name}_fips_year ON {table_name}(fips, year)",
        f"CREATE INDEX idx_{table_name}_transition ON {table_name}(from_land_use, to_land_use)"
    ]
    
    for idx_sql in indexes:
        cursor.execute(idx_sql)
    
    console.print(f"[green]✓ Created {len(indexes)} indexes[/green]")
    
    # Analyze table for query optimization
    cursor.execute(f"ANALYZE {table_name}")
    
    # Get statistics
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    transition_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(DISTINCT scenario) FROM {table_name}")
    scenario_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(DISTINCT year) FROM {table_name}")
    year_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(DISTINCT fips) FROM {table_name}")
    county_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT SUM(acres) FROM {table_name}")
    total_acres = cursor.fetchone()[0]
    
    # Get top transitions
    cursor.execute(f"""
        SELECT from_land_use || ' → ' || to_land_use as transition, 
               COUNT(*) as count,
               SUM(acres) as total_acres
        FROM {table_name}
        GROUP BY from_land_use, to_land_use
        ORDER BY total_acres DESC
        LIMIT 10
    """)
    top_transitions = cursor.fetchall()
    
    conn.commit()
    
    # Final statistics
    elapsed_time = time.time() - start_time
    json_size_mb = Path(json_path).stat().st_size / (1024 * 1024)
    db_size_mb = Path(db_path).stat().st_size / (1024 * 1024)
    
    # Summary panel
    summary = Panel(
        f"""[bold green]✅ Conversion Complete![/bold green]
        
📄 Source: {Path(json_path).name} ({json_size_mb:.2f} MB)
💾 Database: {Path(db_path).name} ({db_size_mb:.2f} MB)
📊 Table: {table_name}
🔄 Total Transitions: {transition_count:,}
🌡️  Scenarios: {scenario_count}
📅 Years: {year_count}
🏛️  Counties: {county_count}
🌾 Total Acres: {total_acres:,.2f}
📈 Compression: {((json_size_mb - db_size_mb) / json_size_mb * 100):.1f}%
⏱️  Time: {elapsed_time:.2f} seconds

[yellow]Example queries:[/yellow]
• SELECT * FROM {table_name} WHERE fips = '01001' AND year = 2020
• SELECT from_land_use, to_land_use, SUM(acres) FROM {table_name} GROUP BY from_land_use, to_land_use
• SELECT fips, SUM(acres) as urban_growth FROM {table_name} WHERE to_land_use = 'Urban' GROUP BY fips
• SELECT year, SUM(acres) as forest_loss FROM {table_name} WHERE from_land_use = 'Forest' AND to_land_use != 'Forest' GROUP BY year""",
        title="📋 Conversion Summary",
        border_style="green"
    )
    
    console.print(summary)
    
    # Show top transitions
    if top_transitions:
        table = Table(title="🔄 Top Land Use Transitions", show_header=True, header_style="bold magenta")
        table.add_column("Transition", style="cyan", no_wrap=True)
        table.add_column("Count", justify="right", style="yellow")
        table.add_column("Total Acres", justify="right", style="green")
        
        for transition, count, acres in top_transitions:
            table.add_row(transition, f"{count:,}", f"{acres:,.2f}")
        
        console.print("\n", table)
    
    # Show sample data
    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
    rows = cursor.fetchall()
    
    if rows:
        table = Table(title="📊 Sample Transition Data", show_header=True, header_style="bold magenta")
        columns = ['scenario', 'year', 'year_range', 'fips', 'from_land_use', 'to_land_use', 'acres']
        
        for col in columns:
            table.add_column(col, style="cyan", no_wrap=True)
        
        for row in rows:
            # Truncate scenario name for display
            display_row = list(row)
            display_row[0] = display_row[0][:20] + "..." if len(display_row[0]) > 20 else display_row[0]
            display_row[6] = f"{display_row[6]:,.2f}"  # Format acres
            table.add_row(*[str(x) for x in display_row])
        
        console.print("\n", table)
    
    conn.close()

if __name__ == "__main__":
    json_file = "./data/county_landuse_projections_RPA.json"
    db_file = "./data/landuse_transitions.db"
    
    console.print(Panel.fit(
        "🚀 [bold blue]Land Use Transitions Database Converter[/bold blue]\n[cyan]Converts matrix data to transition format for analysis[/cyan]",
        border_style="blue"
    ))
    
    convert_to_transitions_db(json_file, db_file)