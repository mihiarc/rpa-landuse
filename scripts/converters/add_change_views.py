#!/usr/bin/env python3
"""
Add views to the landuse transitions database that focus only on changes
(excluding same-to-same transitions)
"""

import sqlite3
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def add_change_views(db_path):
    """Add views that focus only on land use changes"""

    console.print(Panel.fit("🔄 [bold blue]Adding Land Use Change Views[/bold blue]", border_style="blue"))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create view for individual land use changes only
    console.print("[cyan]Creating view for individual land use changes...[/cyan]")
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS individual_changes AS
        SELECT * FROM landuse_transitions
        WHERE category = 'individual'
        AND from_land_use != to_land_use
    """)

    # Create view for agriculture-aggregated changes only
    console.print("[cyan]Creating view for agriculture-aggregated changes...[/cyan]")
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS agriculture_changes AS
        SELECT * FROM landuse_transitions
        WHERE category = 'agriculture_aggregated'
        AND from_land_use != to_land_use
    """)

    # Create a summary view for net changes by land use type
    console.print("[cyan]Creating net change summary views...[/cyan]")

    # Net changes for individual land uses
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS individual_net_changes AS
        SELECT
            scenario,
            year,
            fips,
            land_use,
            SUM(acres_change) as net_change
        FROM (
            -- Losses (negative)
            SELECT scenario, year, fips, from_land_use as land_use, -SUM(acres) as acres_change
            FROM individual_changes
            GROUP BY scenario, year, fips, from_land_use

            UNION ALL

            -- Gains (positive)
            SELECT scenario, year, fips, to_land_use as land_use, SUM(acres) as acres_change
            FROM individual_changes
            GROUP BY scenario, year, fips, to_land_use
        )
        GROUP BY scenario, year, fips, land_use
    """)

    # Net changes for agriculture-aggregated land uses
    cursor.execute("""
        CREATE VIEW IF NOT EXISTS agriculture_net_changes AS
        SELECT
            scenario,
            year,
            fips,
            land_use,
            SUM(acres_change) as net_change
        FROM (
            -- Losses (negative)
            SELECT scenario, year, fips, from_land_use as land_use, -SUM(acres) as acres_change
            FROM agriculture_changes
            GROUP BY scenario, year, fips, from_land_use

            UNION ALL

            -- Gains (positive)
            SELECT scenario, year, fips, to_land_use as land_use, SUM(acres) as acres_change
            FROM agriculture_changes
            GROUP BY scenario, year, fips, to_land_use
        )
        GROUP BY scenario, year, fips, land_use
    """)

    conn.commit()
    console.print("[green]✓ Created change-focused views[/green]")

    # Get statistics
    console.print("\n[bold blue]Analyzing change data...[/bold blue]")

    # Count changes vs non-changes
    cursor.execute("""
        SELECT
            'Individual Same-to-Same' as type,
            COUNT(*) as count,
            SUM(acres) as total_acres
        FROM individual_transitions
        WHERE from_land_use = to_land_use

        UNION ALL

        SELECT
            'Individual Changes' as type,
            COUNT(*) as count,
            SUM(acres) as total_acres
        FROM individual_changes

        UNION ALL

        SELECT
            'Agriculture Same-to-Same' as type,
            COUNT(*) as count,
            SUM(acres) as total_acres
        FROM agriculture_transitions
        WHERE from_land_use = to_land_use

        UNION ALL

        SELECT
            'Agriculture Changes' as type,
            COUNT(*) as count,
            SUM(acres) as total_acres
        FROM agriculture_changes
    """)

    stats = cursor.fetchall()

    # Display statistics
    table = Table(title="📊 Transition Statistics", show_header=True, header_style="bold magenta")
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right", style="yellow")
    table.add_column("Total Acres", justify="right", style="green")

    for type_name, count, acres in stats:
        table.add_row(type_name, f"{count:,}", f"{acres:,.0f}")

    console.print(table)

    # Get top changes
    console.print("\n[bold blue]Top Land Use Changes[/bold blue]")

    # Individual top changes
    cursor.execute("""
        SELECT
            from_land_use || ' → ' || to_land_use as transition,
            COUNT(*) as count,
            SUM(acres) as total_acres
        FROM individual_changes
        GROUP BY from_land_use, to_land_use
        ORDER BY total_acres DESC
        LIMIT 10
    """)

    individual_top = cursor.fetchall()

    table = Table(title="🔄 Top Individual Land Use Changes", show_header=True, header_style="bold magenta")
    table.add_column("Transition", style="cyan")
    table.add_column("Count", justify="right", style="yellow")
    table.add_column("Total Acres", justify="right", style="green")

    for transition, count, acres in individual_top:
        table.add_row(transition, f"{count:,}", f"{acres:,.0f}")

    console.print(table)

    # Agriculture top changes
    cursor.execute("""
        SELECT
            from_land_use || ' → ' || to_land_use as transition,
            COUNT(*) as count,
            SUM(acres) as total_acres
        FROM agriculture_changes
        GROUP BY from_land_use, to_land_use
        ORDER BY total_acres DESC
        LIMIT 10
    """)

    ag_top = cursor.fetchall()

    table = Table(title="🌾 Top Agriculture-Aggregated Changes", show_header=True, header_style="bold magenta")
    table.add_column("Transition", style="cyan")
    table.add_column("Count", justify="right", style="yellow")
    table.add_column("Total Acres", justify="right", style="green")

    for transition, count, acres in ag_top:
        table.add_row(transition, f"{count:,}", f"{acres:,.0f}")

    console.print(table)

    # Example queries
    summary = Panel(
        """[bold green]✅ Change-Focused Views Created![/bold green]

[yellow]New Views:[/yellow]
• individual_changes - Only transitions where land use changed (crop/pasture separate)
• agriculture_changes - Only transitions where land use changed (agriculture combined)
• individual_net_changes - Net gains/losses by land use type
• agriculture_net_changes - Net gains/losses with agriculture aggregated

[yellow]Example Queries:[/yellow]
• Total urban expansion:
  SELECT year, SUM(acres) as urban_gain
  FROM agriculture_changes
  WHERE to_land_use = 'Urban'
  GROUP BY year

• Net forest change by county:
  SELECT fips, SUM(net_change) as forest_change
  FROM agriculture_net_changes
  WHERE land_use = 'Forest'
  GROUP BY fips
  ORDER BY forest_change

• Most dynamic counties:
  SELECT fips, SUM(acres) as total_change
  FROM individual_changes
  GROUP BY fips
  ORDER BY total_change DESC
  LIMIT 10

• Agriculture to urban conversion by scenario:
  SELECT scenario, SUM(acres) as ag_to_urban
  FROM agriculture_changes
  WHERE from_land_use = 'Agriculture' AND to_land_use = 'Urban'
  GROUP BY scenario""",
        title="📋 Summary",
        border_style="green"
    )

    console.print("\n", summary)

    conn.close()

if __name__ == "__main__":
    db_path = "./data/landuse_transitions_with_ag.db"

    console.print(Panel.fit(
        "🚀 [bold blue]Land Use Change Views Creator[/bold blue]\n[cyan]Filters out same-to-same transitions to focus on actual changes[/cyan]",
        border_style="blue"
    ))

    add_change_views(db_path)
