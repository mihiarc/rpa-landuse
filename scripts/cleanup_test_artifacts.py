#!/usr/bin/env python3
"""
Cleanup script to remove test artifacts from the production database.
Run this when the Streamlit app is not running.
"""

import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

import duckdb
from rich.console import Console
from rich.panel import Panel

console = Console()

def cleanup_test_artifacts():
    """Remove test tables and other artifacts from the production database"""

    db_path = "data/processed/landuse_analytics.duckdb"

    try:
        console.print(Panel("Database Cleanup Tool", style="bold blue"))
        console.print(f"\n📁 Database: {db_path}")

        # Connect to the database
        with duckdb.connect(db_path) as conn:
            # Check if test_table exists
            result = conn.execute("""
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_name = 'test_table'
            """).fetchone()

            if result[0] > 0:
                console.print("\n🔍 Found test_table in database")

                # Show table info
                row_count = conn.execute("SELECT COUNT(*) FROM test_table").fetchone()[0]
                console.print(f"   - Rows: {row_count}")

                # Drop the table
                conn.execute("DROP TABLE test_table")
                console.print("[green]✅ Successfully removed test_table[/green]")
            else:
                console.print("\n[yellow]ℹ️ No test artifacts found in database[/yellow]")

            # Check for any other suspicious tables
            tables = conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                AND table_name NOT IN (
                    'dim_geography', 'dim_indicators', 'dim_landuse', 'dim_scenario',
                    'dim_socioeconomic', 'dim_time', 'fact_landuse_transitions',
                    'fact_socioeconomic_projections', 'v_full_projection_period',
                    'v_income_trends', 'v_landuse_socioeconomic', 'v_population_trends',
                    'v_scenarios_combined'
                )
                ORDER BY table_name
            """).fetchall()

            if tables:
                console.print("\n[yellow]⚠️ Found additional non-standard tables:[/yellow]")
                for table in tables:
                    console.print(f"   - {table[0]}")
                console.print("\n[dim]These tables were not removed. Review them manually if needed.[/dim]")

            # Vacuum to reclaim space
            console.print("\n🔧 Vacuuming database to reclaim space...")
            conn.execute("VACUUM")
            console.print("[green]✅ Database vacuumed successfully[/green]")

    except duckdb.IOException as e:
        if "Conflicting lock" in str(e):
            console.print("\n[red]❌ Error: Database is currently in use[/red]")
            console.print("[yellow]Please stop the Streamlit app and try again.[/yellow]")
            return False
        else:
            console.print(f"\n[red]❌ Database error: {e}[/red]")
            return False
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
        return False

    console.print("\n[green]✨ Cleanup completed successfully![/green]")
    return True

if __name__ == "__main__":
    import sys
    success = cleanup_test_artifacts()
    sys.exit(0 if success else 1)
