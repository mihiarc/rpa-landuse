#!/usr/bin/env python3
"""
Convert nested county landuse projections JSON to SQLite database
Handles the nested structure: scenario -> time_period -> county -> data
"""

import json
import sqlite3
import time
from decimal import Decimal
from pathlib import Path

import ijson
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()

def flatten_nested_json(json_path, db_path, table_name='landuse_projections'):
    """Convert nested JSON structure to flat SQLite table"""
    start_time = time.time()

    console.print(Panel.fit("🔍 [bold blue]Analyzing nested JSON structure...[/bold blue]", border_style="blue"))

    # Create database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop table if exists
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Create table with flattened schema
    create_table_sql = f"""
    CREATE TABLE {table_name} (
        scenario TEXT,
        time_period TEXT,
        county_fips TEXT,
        cr REAL,
        ps REAL,
        rg REAL,
        fr REAL,
        ur REAL,
        t1 REAL,
        row_type TEXT
    )
    """
    cursor.execute(create_table_sql)
    console.print(f"[green]✓ Created table '{table_name}' with flattened structure[/green]")

    # Get file size for progress tracking
    file_size = Path(json_path).stat().st_size

    # Process JSON file
    console.print("\n[bold blue]Converting nested JSON to SQLite...[/bold blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        task = progress.add_task("Processing JSON...", total=100)  # We'll update based on scenarios

        batch = []
        total_rows = 0
        batch_size = 10000

        with open(json_path) as f:
            # Parse the top-level object
            data = json.load(f)

            scenarios = list(data.keys())
            console.print(f"[cyan]Found {len(scenarios)} climate scenarios[/cyan]")

            scenario_count = 0

            for scenario in scenarios:
                scenario_data = data[scenario]
                scenario_count += 1

                for time_period in scenario_data:
                    time_data = scenario_data[time_period]

                    for county_fips in time_data:
                        county_records = time_data[county_fips]

                        for record in county_records:
                            # Convert Decimal values to float
                            row_data = (
                                scenario,
                                time_period,
                                county_fips,
                                float(record.get('cr', 0)) if isinstance(record.get('cr'), Decimal) else record.get('cr', 0),
                                float(record.get('ps', 0)) if isinstance(record.get('ps'), Decimal) else record.get('ps', 0),
                                float(record.get('rg', 0)) if isinstance(record.get('rg'), Decimal) else record.get('rg', 0),
                                float(record.get('fr', 0)) if isinstance(record.get('fr'), Decimal) else record.get('fr', 0),
                                float(record.get('ur', 0)) if isinstance(record.get('ur'), Decimal) else record.get('ur', 0),
                                float(record.get('t1', 0)) if isinstance(record.get('t1'), Decimal) else record.get('t1', 0),
                                record.get('_row', '')
                            )
                            batch.append(row_data)

                            if len(batch) >= batch_size:
                                # Insert batch
                                cursor.executemany(
                                    f"INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                    batch
                                )
                                conn.commit()
                                total_rows += len(batch)
                                batch = []

                                progress.update(
                                    task,
                                    completed=(scenario_count / len(scenarios)) * 100,
                                    description=f"Processed {total_rows:,} rows from {scenario_count}/{len(scenarios)} scenarios..."
                                )

        # Insert remaining rows
        if batch:
            cursor.executemany(
                f"INSERT INTO {table_name} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                batch
            )
            conn.commit()
            total_rows += len(batch)

        progress.update(task, completed=100)

    # Create indexes
    console.print("\n[bold blue]Creating indexes...[/bold blue]")

    indexes = [
        f"CREATE INDEX idx_{table_name}_scenario ON {table_name}(scenario)",
        f"CREATE INDEX idx_{table_name}_time_period ON {table_name}(time_period)",
        f"CREATE INDEX idx_{table_name}_county_fips ON {table_name}(county_fips)",
        f"CREATE INDEX idx_{table_name}_row_type ON {table_name}(row_type)",
        f"CREATE INDEX idx_{table_name}_composite ON {table_name}(scenario, time_period, county_fips)"
    ]

    for idx_sql in indexes:
        cursor.execute(idx_sql)

    console.print(f"[green]✓ Created {len(indexes)} indexes[/green]")

    # Analyze table for query optimization
    cursor.execute(f"ANALYZE {table_name}")

    # Get statistics
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(DISTINCT scenario) FROM {table_name}")
    scenario_count = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(DISTINCT time_period) FROM {table_name}")
    time_period_count = cursor.fetchone()[0]

    cursor.execute(f"SELECT COUNT(DISTINCT county_fips) FROM {table_name}")
    county_count = cursor.fetchone()[0]

    conn.commit()
    conn.close()

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
🔢 Total Rows: {row_count:,}
🌡️  Scenarios: {scenario_count}
📅 Time Periods: {time_period_count}
🏛️  Counties: {county_count}
📈 Compression: {((json_size_mb - db_size_mb) / json_size_mb * 100):.1f}%
⏱️  Time: {elapsed_time:.2f} seconds

[yellow]Example queries:[/yellow]
• SELECT * FROM {table_name} WHERE county_fips = '01001' LIMIT 10
• SELECT DISTINCT scenario FROM {table_name}
• SELECT SUM(ur) as urban_area FROM {table_name} WHERE time_period = '2012-2020' GROUP BY county_fips
• SELECT * FROM {table_name} WHERE scenario LIKE '%rcp45%' AND row_type = 'cr'""",
        title="📋 Conversion Summary",
        border_style="green"
    )

    console.print(summary)

    # Show sample data
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(f"SELECT * FROM {table_name} LIMIT 5")
    rows = cursor.fetchall()

    if rows:
        table = Table(title="📊 Sample Data", show_header=True, header_style="bold magenta")
        columns = ['scenario', 'time_period', 'county_fips', 'cr', 'ps', 'rg', 'fr', 'ur', 't1', 'row_type']

        for col in columns:
            table.add_column(col, style="cyan", no_wrap=True)

        for row in rows:
            # Truncate scenario name for display
            display_row = list(row)
            display_row[0] = display_row[0][:20] + "..." if len(display_row[0]) > 20 else display_row[0]
            table.add_row(*[str(x) for x in display_row])

        console.print("\n", table)

    conn.close()

if __name__ == "__main__":
    json_file = "./data/county_landuse_projections_RPA.json"
    db_file = "./data/landuse_projections.db"

    console.print(Panel.fit(
        "🚀 [bold blue]County Landuse Projections JSON to SQLite Converter[/bold blue]\n[cyan]Handles nested structure: scenario → time_period → county → data[/cyan]",
        border_style="blue"
    ))

    flatten_nested_json(json_file, db_file)
