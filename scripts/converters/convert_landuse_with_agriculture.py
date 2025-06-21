#!/usr/bin/env python3
"""
Convert county landuse projections JSON to SQLite database with land use transitions
Includes an Agriculture category that combines Crop and Pasture uses
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

# Agriculture components
AGRICULTURE_COMPONENTS = {'Crop', 'Pasture'}

def extract_end_year(year_range):
    """Extract the end year from a year range string (e.g., '2012-2020' -> 2020)."""
    return int(year_range.split('-')[1])

def convert_value(value):
    """Convert Decimal or other numeric types to float"""
    if isinstance(value, Decimal):
        return float(value)
    return float(value) if value is not None else 0.0

def process_matrix_data(matrix_data, scenario, year, year_range, fips):
    """Convert the matrix data to transition records, including agriculture aggregation."""
    transitions = []
    
    # First, collect all the raw transitions
    raw_transitions = {}
    
    for row in matrix_data:
        from_type = LAND_USE_MAP.get(row.get('_row', ''), row.get('_row', ''))
        
        if from_type != 'Total':  # Skip the total row
            for col, value in row.items():
                if col not in ['_row', 't1'] and col in LAND_USE_MAP:  # Skip row identifier and total
                    to_type = LAND_USE_MAP[col]
                    if to_type != 'Total':  # Skip total column
                        acres = convert_value(value)
                        if acres > 0:  # Only include non-zero transitions
                            # Store individual transitions
                            transitions.append({
                                'scenario': scenario,
                                'year': year,
                                'year_range': year_range,
                                'fips': fips,
                                'from_land_use': from_type,
                                'to_land_use': to_type,
                                'acres': acres,
                                'category': 'individual'
                            })
                            
                            # Store for agriculture aggregation
                            key = (from_type, to_type)
                            raw_transitions[key] = raw_transitions.get(key, 0) + acres
    
    # Calculate agriculture transitions
    # Agriculture = Crop + Pasture
    ag_transitions = {}
    
    for (from_type, to_type), acres in raw_transitions.items():
        # Determine aggregated from category
        if from_type in AGRICULTURE_COMPONENTS:
            from_agg = 'Agriculture'
        else:
            from_agg = from_type
            
        # Determine aggregated to category
        if to_type in AGRICULTURE_COMPONENTS:
            to_agg = 'Agriculture'
        else:
            to_agg = to_type
        
        # Add to aggregated transitions
        key = (from_agg, to_agg)
        ag_transitions[key] = ag_transitions.get(key, 0) + acres
    
    # Add agriculture transitions
    for (from_agg, to_agg), acres in ag_transitions.items():
        transitions.append({
            'scenario': scenario,
            'year': year,
            'year_range': year_range,
            'fips': fips,
            'from_land_use': from_agg,
            'to_land_use': to_agg,
            'acres': acres,
            'category': 'agriculture_aggregated'
        })
    
    return transitions

def convert_to_transitions_db(json_path, db_path, table_name='landuse_transitions'):
    """Convert nested JSON structure to SQLite database with land use transitions"""
    start_time = time.time()
    
    console.print(Panel.fit("🔍 [bold blue]Converting to Land Use Transitions Database with Agriculture Category...[/bold blue]", border_style="blue"))
    
    # Create database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop table if exists
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    
    # Create table for transitions with category column
    create_table_sql = f"""
    CREATE TABLE {table_name} (
        scenario TEXT NOT NULL,
        year INTEGER NOT NULL,
        year_range TEXT NOT NULL,
        fips TEXT NOT NULL,
        from_land_use TEXT NOT NULL,
        to_land_use TEXT NOT NULL,
        acres REAL NOT NULL,
        category TEXT NOT NULL,
        PRIMARY KEY (scenario, year_range, fips, from_land_use, to_land_use, category)
    )
    """
    cursor.execute(create_table_sql)
    console.print(f"[green]✓ Created table '{table_name}' for land use transitions with agriculture aggregation[/green]")
    
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
                            trans['acres'],
                            trans['category']
                        ))
                        
                        if len(batch) >= batch_size:
                            cursor.executemany(
                                f"INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                batch
                            )
                            conn.commit()
                            total_transitions += len(batch)
                            batch = []
            
            progress.update(task, advance=1)
        
        # Insert remaining records
        if batch:
            cursor.executemany(
                f"INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
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
        f"CREATE INDEX idx_{table_name}_category ON {table_name}(category)",
        f"CREATE INDEX idx_{table_name}_scenario_year ON {table_name}(scenario, year)",
        f"CREATE INDEX idx_{table_name}_fips_year ON {table_name}(fips, year)",
        f"CREATE INDEX idx_{table_name}_transition ON {table_name}(from_land_use, to_land_use)"
    ]
    
    for idx_sql in indexes:
        cursor.execute(idx_sql)
    
    console.print(f"[green]✓ Created {len(indexes)} indexes[/green]")
    
    # Create views for easier querying
    console.print("\n[bold blue]Creating convenience views...[/bold blue]")
    
    # View for individual land uses only
    cursor.execute(f"""
        CREATE VIEW individual_transitions AS
        SELECT * FROM {table_name} WHERE category = 'individual'
    """)
    
    # View for agriculture-aggregated transitions only
    cursor.execute(f"""
        CREATE VIEW agriculture_transitions AS
        SELECT * FROM {table_name} WHERE category = 'agriculture_aggregated'
    """)
    
    console.print(f"[green]✓ Created views for easy access to individual and aggregated data[/green]")
    
    # Analyze table for query optimization
    cursor.execute(f"ANALYZE {table_name}")
    
    # Get statistics
    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE category = 'individual'")
    individual_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE category = 'agriculture_aggregated'")
    ag_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(DISTINCT scenario) FROM {table_name}")
    scenario_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(DISTINCT year) FROM {table_name}")
    year_count = cursor.fetchone()[0]
    
    cursor.execute(f"SELECT COUNT(DISTINCT fips) FROM {table_name}")
    county_count = cursor.fetchone()[0]
    
    # Get top agriculture transitions
    cursor.execute(f"""
        SELECT from_land_use || ' → ' || to_land_use as transition, 
               SUM(acres) as total_acres
        FROM {table_name}
        WHERE category = 'agriculture_aggregated'
        GROUP BY from_land_use, to_land_use
        ORDER BY total_acres DESC
        LIMIT 10
    """)
    top_ag_transitions = cursor.fetchall()
    
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
🔄 Individual Transitions: {individual_count:,}
🌾 Agriculture-Aggregated Transitions: {ag_count:,}
🌡️  Scenarios: {scenario_count}
📅 Years: {year_count}
🏛️  Counties: {county_count}
⏱️  Time: {elapsed_time:.2f} seconds

[yellow]Views created:[/yellow]
• individual_transitions - Original crop/pasture transitions
• agriculture_transitions - With crop+pasture combined

[yellow]Example queries:[/yellow]
• SELECT * FROM agriculture_transitions WHERE fips = '01001' AND year = 2020
• SELECT from_land_use, to_land_use, SUM(acres) FROM agriculture_transitions 
  WHERE from_land_use = 'Agriculture' GROUP BY to_land_use
• SELECT year, SUM(acres) as ag_to_urban FROM agriculture_transitions 
  WHERE from_land_use = 'Agriculture' AND to_land_use = 'Urban' GROUP BY year
• Compare: SELECT SUM(acres) FROM individual_transitions 
  WHERE from_land_use IN ('Crop', 'Pasture') AND to_land_use = 'Urban'""",
        title="📋 Conversion Summary",
        border_style="green"
    )
    
    console.print(summary)
    
    # Show top agriculture transitions
    if top_ag_transitions:
        table = Table(title="🌾 Top Agriculture-Aggregated Transitions", show_header=True, header_style="bold magenta")
        table.add_column("Transition", style="cyan", no_wrap=True)
        table.add_column("Total Acres", justify="right", style="green")
        
        for transition, acres in top_ag_transitions:
            table.add_row(transition, f"{acres:,.2f}")
        
        console.print("\n", table)
    
    # Show sample data comparison
    cursor.execute(f"""
        SELECT 'Crop → Urban' as transition, SUM(acres) as acres 
        FROM individual_transitions WHERE from_land_use = 'Crop' AND to_land_use = 'Urban'
        UNION ALL
        SELECT 'Pasture → Urban', SUM(acres) 
        FROM individual_transitions WHERE from_land_use = 'Pasture' AND to_land_use = 'Urban'
        UNION ALL
        SELECT 'Agriculture → Urban', SUM(acres)
        FROM agriculture_transitions WHERE from_land_use = 'Agriculture' AND to_land_use = 'Urban'
    """)
    comparison = cursor.fetchall()
    
    if comparison:
        table = Table(title="📊 Agriculture Aggregation Example", show_header=True, header_style="bold magenta")
        table.add_column("Transition", style="cyan")
        table.add_column("Total Acres", justify="right", style="yellow")
        
        for transition, acres in comparison:
            table.add_row(transition, f"{acres:,.2f}")
        
        console.print("\n", table)
        console.print("[dim]Note: Agriculture → Urban = Crop → Urban + Pasture → Urban[/dim]")
    
    conn.close()

if __name__ == "__main__":
    json_file = "./data/county_landuse_projections_RPA.json"
    db_file = "./data/landuse_transitions_with_ag.db"
    
    console.print(Panel.fit(
        "🚀 [bold blue]Land Use Transitions Database Converter[/bold blue]\n[cyan]Includes Agriculture category (Crop + Pasture combined)[/cyan]",
        border_style="blue"
    ))
    
    convert_to_transitions_db(json_file, db_file)