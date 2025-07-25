#!/usr/bin/env python3
"""
Add Total Land Area View to DuckDB Database
Creates a view with total land area by geography for percentage calculations
"""

from pathlib import Path

import duckdb
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def add_land_area_view(db_path: str = "data/processed/landuse_analytics.duckdb"):
    """Add total land area view to the database"""

    console.print(Panel.fit(
        "📊 [bold green]Adding Total Land Area View[/bold green]\n"
        "[yellow]Creating v_total_land_area for percentage calculations[/yellow]",
        border_style="green"
    ))

    db_file = Path(db_path)
    if not db_file.exists():
        console.print(f"❌ Database file not found: {db_path}")
        return False

    try:
        conn = duckdb.connect(str(db_file))

        # Drop view if it exists
        conn.execute("DROP VIEW IF EXISTS v_total_land_area")

        # Create total land area view
        # This calculates the total land area for each geography by summing all transitions
        # We use the baseline scenario and earliest time period as reference
        conn.execute("""
            CREATE VIEW v_total_land_area AS
            WITH land_totals AS (
                SELECT
                    g.geography_id,
                    g.fips_code,
                    g.state_code,
                    -- Sum all land area (both 'same' and 'change' transitions give total area)
                    SUM(f.acres) as total_land_acres
                FROM fact_landuse_transitions f
                JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
                JOIN dim_time t ON f.time_id = t.time_id
                JOIN dim_scenario s ON f.scenario_id = s.scenario_id
                -- Use earliest time period as baseline (most representative of actual area)
                WHERE t.start_year = (SELECT MIN(start_year) FROM dim_time)
                  -- Use first scenario alphabetically for consistency
                  AND s.scenario_name = (SELECT MIN(scenario_name) FROM dim_scenario)
                GROUP BY g.geography_id, g.fips_code, g.state_code
            ),
            state_totals AS (
                SELECT
                    state_code,
                    SUM(total_land_acres) as state_total_acres,
                    COUNT(*) as counties_in_state
                FROM land_totals
                GROUP BY state_code
            )
            SELECT
                lt.geography_id,
                lt.fips_code,
                lt.state_code,
                lt.total_land_acres as county_total_acres,
                st.state_total_acres,
                st.counties_in_state,
                -- Calculate percentage of state that this county represents
                ROUND((lt.total_land_acres / st.state_total_acres) * 100, 2) as pct_of_state
            FROM land_totals lt
            JOIN state_totals st ON lt.state_code = st.state_code
            ORDER BY lt.state_code, lt.total_land_acres DESC
        """)

        console.print("✅ [green]v_total_land_area view created successfully[/green]")

        # Test the view and show some sample data
        console.print("\n📊 [bold cyan]Sample Data from v_total_land_area:[/bold cyan]")

        sample_data = conn.execute("""
            SELECT
                state_code,
                COUNT(*) as counties,
                ROUND(AVG(county_total_acres), 0) as avg_county_acres,
                ROUND(MAX(state_total_acres), 0) as state_total_acres,
                ROUND(MIN(county_total_acres), 0) as smallest_county,
                ROUND(MAX(county_total_acres), 0) as largest_county
            FROM v_total_land_area
            GROUP BY state_code
            ORDER BY state_total_acres DESC
            LIMIT 10
        """).fetchall()

        table = Table(title="Top 10 States by Total Land Area", show_header=True, header_style="bold cyan")
        table.add_column("State", style="yellow")
        table.add_column("Counties", justify="right", style="green")
        table.add_column("Avg County Acres", justify="right", style="blue")
        table.add_column("State Total Acres", justify="right", style="magenta")
        table.add_column("Smallest County", justify="right", style="dim")
        table.add_column("Largest County", justify="right", style="dim")

        for row in sample_data:
            table.add_row(
                row[0],
                f"{row[1]:,}",
                f"{int(row[2]):,}",
                f"{int(row[3]):,}",
                f"{int(row[4]):,}",
                f"{int(row[5]):,}"
            )

        console.print(table)

        # Show total records
        total_records = conn.execute("SELECT COUNT(*) FROM v_total_land_area").fetchone()[0]
        console.print(f"\n📈 Total records in view: [bold cyan]{total_records:,}[/bold cyan]")

        conn.close()
        return True

    except Exception as e:
        console.print(f"❌ [red]Error creating view: {str(e)}[/red]")
        return False

def create_percentage_examples():
    """Create example queries using the new view"""

    examples = """
📊 **Example Queries Using v_total_land_area:**

**1. Rank states by percentage of forest loss:**
```sql
SELECT
    tla.state_code,
    tla.state_total_acres,
    SUM(f.acres) as forest_lost_acres,
    ROUND((SUM(f.acres) / tla.state_total_acres) * 100, 2) as forest_loss_pct
FROM fact_landuse_transitions f
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
JOIN v_total_land_area tla ON f.geography_id = tla.geography_id
WHERE fl.landuse_name = 'Forest'
  AND tl.landuse_name != 'Forest'
  AND f.transition_type = 'change'
GROUP BY tla.state_code, tla.state_total_acres
ORDER BY forest_loss_pct DESC;
```

**2. Counties with highest percentage of agricultural land:**
```sql
SELECT
    tla.fips_code,
    tla.state_code,
    tla.county_total_acres,
    SUM(f.acres) as ag_acres,
    ROUND((SUM(f.acres) / tla.county_total_acres) * 100, 2) as ag_percentage
FROM fact_landuse_transitions f
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN v_total_land_area tla ON f.geography_id = tla.geography_id
WHERE fl.landuse_category = 'Agriculture'
  AND f.transition_type = 'same'  -- Current agricultural land
GROUP BY tla.fips_code, tla.state_code, tla.county_total_acres
ORDER BY ag_percentage DESC
LIMIT 20;
```

**3. Urban expansion as percentage of total land:**
```sql
SELECT
    tla.state_code,
    SUM(f.acres) as urban_expansion_acres,
    AVG(tla.state_total_acres) as state_total_acres,
    ROUND((SUM(f.acres) / AVG(tla.state_total_acres)) * 100, 4) as urban_expansion_pct
FROM fact_landuse_transitions f
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
JOIN v_total_land_area tla ON f.geography_id = tla.geography_id
WHERE tl.landuse_name = 'Urban'
  AND f.transition_type = 'change'
GROUP BY tla.state_code
ORDER BY urban_expansion_pct DESC;
```
"""

    console.print(Panel(examples, title="📝 Usage Examples", border_style="blue"))

def main():
    """Main function"""
    console.print(Panel.fit(
        "🦆 [bold blue]DuckDB Land Area View Creator[/bold blue]\n"
        "[yellow]Adding total land area calculations for percentage analysis[/yellow]",
        border_style="blue"
    ))

    if add_land_area_view():
        create_percentage_examples()

        console.print(Panel.fit(
            "✅ [bold green]View Creation Complete![/bold green]\n"
            "🎯 You can now ask percentage-based questions like:\n"
            "• 'Rank states by percentage of forest loss'\n"
            "• 'Which counties have the highest percentage of agricultural land'\n"
            "• 'Show urban expansion as percentage of total land area'",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            "❌ [bold red]View Creation Failed[/bold red]\n"
            "Check the error messages above for details.",
            border_style="red"
        ))

if __name__ == "__main__":
    main()
