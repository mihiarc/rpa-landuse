#!/usr/bin/env python3
"""
Enhance the landuse database with additional useful information
"""

from pathlib import Path

import duckdb
from rich.console import Console
from rich.panel import Panel

console = Console()

def add_state_names_to_geography(db_path: str):
    """Add state names to the dim_geography table"""

    state_names = {
        '01': 'Alabama', '02': 'Alaska', '04': 'Arizona', '05': 'Arkansas',
        '06': 'California', '08': 'Colorado', '09': 'Connecticut', '10': 'Delaware',
        '12': 'Florida', '13': 'Georgia', '15': 'Hawaii', '16': 'Idaho',
        '17': 'Illinois', '18': 'Indiana', '19': 'Iowa', '20': 'Kansas',
        '21': 'Kentucky', '22': 'Louisiana', '23': 'Maine', '24': 'Maryland',
        '25': 'Massachusetts', '26': 'Michigan', '27': 'Minnesota', '28': 'Mississippi',
        '29': 'Missouri', '30': 'Montana', '31': 'Nebraska', '32': 'Nevada',
        '33': 'New Hampshire', '34': 'New Jersey', '35': 'New Mexico', '36': 'New York',
        '37': 'North Carolina', '38': 'North Dakota', '39': 'Ohio', '40': 'Oklahoma',
        '41': 'Oregon', '42': 'Pennsylvania', '44': 'Rhode Island', '45': 'South Carolina',
        '46': 'South Dakota', '47': 'Tennessee', '48': 'Texas', '49': 'Utah',
        '50': 'Vermont', '51': 'Virginia', '53': 'Washington', '54': 'West Virginia',
        '55': 'Wisconsin', '56': 'Wyoming', '72': 'Puerto Rico', '78': 'Virgin Islands'
    }

    console.print(Panel.fit(
        "🔧 [bold blue]Enhancing Database[/bold blue]\n"
        "[yellow]Adding state names to geography dimension[/yellow]",
        border_style="blue"
    ))

    try:
        conn = duckdb.connect(db_path)

        # Check if state_name column already exists
        columns = conn.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'dim_geography_enhanced'
            AND column_name = 'state_name'
        """).fetchall()

        if not columns:
            console.print("Adding state_name column to dim_geography_enhanced...")

            # Add the column
            conn.execute("ALTER TABLE dim_geography_enhanced ADD COLUMN state_name VARCHAR(50)")

            # Update with state names
            for code, name in state_names.items():
                conn.execute("""
                    UPDATE dim_geography_enhanced
                    SET state_name = ?
                    WHERE state_code = ?
                """, (name, code))

            # Create a view that includes state names
            conn.execute("""
                CREATE OR REPLACE VIEW v_geography_enhanced AS
                SELECT
                    geography_id,
                    fips_code,
                    state_code,
                    COALESCE(state_name, 'Unknown') as state_name,
                    county_name,
                    region
                FROM dim_geography_enhanced
            """)

            console.print("✅ State names added successfully!")

            # Show sample
            sample = conn.execute("""
                SELECT state_code, state_name, COUNT(*) as counties
                FROM dim_geography_enhanced
                WHERE state_name IS NOT NULL
                GROUP BY state_code, state_name
                ORDER BY state_name
                LIMIT 5
            """).fetchdf()

            console.print("\nSample results:")
            console.print(sample)

        else:
            console.print("✓ State names already exist in dim_geography_enhanced")

        conn.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return False

    return True

def create_enhanced_views(db_path: str):
    """Create views that include human-readable names"""

    console.print("\nCreating enhanced views...")

    try:
        conn = duckdb.connect(db_path)

        # Create a comprehensive transitions view with names
        conn.execute("""
            CREATE OR REPLACE VIEW v_transitions_with_names AS
            SELECT
                f.transition_id,
                s.scenario_name,
                s.rcp_scenario,
                s.ssp_scenario,
                t.year_range,
                t.start_year,
                t.end_year,
                g.state_code,
                COALESCE(g.state_name, 'Unknown') as state_name,
                g.fips_code,
                fl.landuse_code as from_landuse_code,
                fl.landuse_name as from_landuse_name,
                tl.landuse_code as to_landuse_code,
                tl.landuse_name as to_landuse_name,
                f.acres,
                f.transition_type
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
        """)

        console.print("✅ Enhanced views created successfully!")

        conn.close()

    except Exception as e:
        console.print(f"[red]Error creating views: {e}[/red]")
        return False

    return True

if __name__ == "__main__":
    db_path = "data/processed/landuse_analytics.duckdb"

    if Path(db_path).exists():
        add_state_names_to_geography(db_path)
        create_enhanced_views(db_path)
        console.print("\n✨ Database enhancement complete!")
    else:
        console.print(f"[red]Database not found at {db_path}[/red]")
