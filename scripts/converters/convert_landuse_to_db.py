#!/usr/bin/env python3
"""
Convert large county landuse projections JSON to SQLite database
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

def analyze_json_structure(json_path, sample_size=5):
    """Analyze JSON structure by reading a small sample"""
    console.print(Panel.fit("🔍 [bold blue]Analyzing JSON structure...[/bold blue]", border_style="blue"))

    with open(json_path, 'rb') as f:
        # Try to detect if it's an array or object
        first_char = f.read(1).decode('utf-8').strip()
        f.seek(0)

        if first_char == '[':
            # It's an array
            parser = ijson.items(f, 'item')
            samples = []
            for i, item in enumerate(parser):
                if i < sample_size:
                    samples.append(item)
                else:
                    break
            return 'array', samples
        else:
            # It's an object, need to find the data key
            parser = ijson.parse(f)
            path = []
            samples = []

            for _prefix, event, value in parser:
                if event == 'map_key':
                    path.append(value)
                elif event == 'start_map':
                    if len(path) > 0:
                        # We're inside a nested structure
                        pass
                elif event == 'end_map':
                    if path:
                        path.pop()
                elif event == 'start_array':
                    # Found an array, let's check if it contains data
                    array_path = '.'.join(path)
                    f.seek(0)
                    array_parser = ijson.items(f, f"{array_path}.item")
                    for i, item in enumerate(array_parser):
                        if i < sample_size:
                            samples.append(item)
                        else:
                            break
                    if samples:
                        return array_path, samples

    return None, []

def infer_schema(samples):
    """Infer SQL schema from sample data"""
    schema = {}

    for sample in samples:
        if isinstance(sample, dict):
            for key, value in sample.items():
                if key not in schema:
                    if isinstance(value, int):
                        schema[key] = "INTEGER"
                    elif isinstance(value, (float, Decimal)):
                        schema[key] = "REAL"
                    elif isinstance(value, bool):
                        schema[key] = "INTEGER"  # SQLite doesn't have boolean
                    else:
                        schema[key] = "TEXT"

    return schema

def convert_json_to_sqlite(json_path, db_path, table_name='landuse_data', chunk_size=10000):
    """Convert JSON file to SQLite database"""
    start_time = time.time()

    # Analyze JSON structure
    data_path, samples = analyze_json_structure(json_path)

    if not samples:
        console.print("[red]Error: Could not find data in JSON file[/red]")
        return

    # Display sample data
    table = Table(title="📊 Sample Data Structure", show_header=True, header_style="bold magenta")
    if samples:
        for key in samples[0].keys():
            table.add_column(key, style="cyan", no_wrap=True)

        for sample in samples[:3]:
            table.add_row(*[str(sample.get(k, ''))[:50] for k in samples[0].keys()])

    console.print(table)

    # Infer schema
    schema = infer_schema(samples)
    console.print(f"\n[green]Detected schema with {len(schema)} columns[/green]")

    # Create database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Drop table if exists
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Create table
    columns_sql = ", ".join([f"{key} {dtype}" for key, dtype in schema.items()])
    create_table_sql = f"CREATE TABLE {table_name} ({columns_sql})"
    cursor.execute(create_table_sql)
    console.print(f"[green]✓ Created table '{table_name}'[/green]")

    # Process JSON file
    console.print("\n[bold blue]Converting JSON to SQLite...[/bold blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:

        # Get total file size for progress tracking
        file_size = Path(json_path).stat().st_size

        task = progress.add_task("Processing JSON...", total=file_size)

        with open(json_path, 'rb') as f:
            if data_path == 'array':
                parser = ijson.items(f, 'item')
            else:
                parser = ijson.items(f, f"{data_path}.item")

            batch = []
            total_rows = 0

            for item in parser:
                # Convert item to tuple in correct column order, handling Decimal types
                row_data = []
                for key in schema.keys():
                    value = item.get(key, None)
                    if isinstance(value, Decimal):
                        value = float(value)
                    row_data.append(value)
                batch.append(tuple(row_data))

                if len(batch) >= chunk_size:
                    # Insert batch
                    placeholders = ", ".join(["?" for _ in schema])
                    insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                    cursor.executemany(insert_sql, batch)
                    conn.commit()

                    total_rows += len(batch)
                    progress.update(task, advance=f.tell() - progress.tasks[task].completed)
                    progress.update(task, description=f"Processed {total_rows:,} rows...")
                    batch = []

            # Insert remaining rows
            if batch:
                placeholders = ", ".join(["?" for _ in schema])
                insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                cursor.executemany(insert_sql, batch)
                conn.commit()
                total_rows += len(batch)

            progress.update(task, completed=file_size)

    # Create indexes on common columns
    console.print("\n[bold blue]Creating indexes...[/bold blue]")

    index_columns = ['id', 'county', 'state', 'year', 'date', 'fips', 'geoid']
    created_indexes = []

    for col in index_columns:
        if col in schema:
            try:
                cursor.execute(f"CREATE INDEX idx_{table_name}_{col} ON {table_name}({col})")
                created_indexes.append(col)
            except:
                pass

    if created_indexes:
        console.print(f"[green]✓ Created indexes on: {', '.join(created_indexes)}[/green]")

    # Get statistics
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]

    # Analyze table for query optimization
    cursor.execute(f"ANALYZE {table_name}")

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
🔢 Rows: {row_count:,}
📈 Compression: {((json_size_mb - db_size_mb) / json_size_mb * 100):.1f}%
⏱️  Time: {elapsed_time:.2f} seconds
📍 Indexes: {', '.join(created_indexes) if created_indexes else 'None'}

[yellow]Example queries:[/yellow]
• SELECT COUNT(*) FROM {table_name}
• SELECT * FROM {table_name} LIMIT 10
• SELECT DISTINCT county FROM {table_name}
• SELECT * FROM {table_name} WHERE year = 2020""",
        title="📋 Conversion Summary",
        border_style="green"
    )

    console.print(summary)

if __name__ == "__main__":
    json_file = "./data/county_landuse_projections_RPA.json"
    db_file = "./data/landuse_projections.db"

    console.print(Panel.fit(
        "🚀 [bold blue]County Landuse Projections JSON to SQLite Converter[/bold blue]",
        border_style="blue"
    ))

    convert_json_to_sqlite(json_file, db_file)
