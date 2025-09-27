#!/usr/bin/env python3
"""
Convert existing 20 GCM scenario database to 5 combined scenarios.

This script aggregates the existing 20 GCM-specific scenarios into 5 combined
scenarios (4 RCP-SSP combinations + 1 OVERALL) directly in the database.
"""

import argparse
import sys
from pathlib import Path

import duckdb
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


class DatabaseCombinedScenarioConverter:
    """Convert existing GCM scenarios to combined scenarios in-place."""

    # Mapping of combined scenarios
    COMBINED_SCENARIOS = {
        'OVERALL': 'Ensemble mean of all scenarios',
        'RCP45_SSP1': 'Sustainability pathway (low emissions)',
        'RCP45_SSP5': 'Fossil-fueled Development (low emissions)',
        'RCP85_SSP1': 'Sustainability (high emissions)',
        'RCP85_SSP5': 'Fossil-fueled Development (high emissions)'
    }

    def __init__(self, db_path: str, output_path: str = None):
        """Initialize converter with database paths."""
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")

        # Use separate output or backup and modify in place
        if output_path:
            self.output_path = Path(output_path)
        else:
            # Create backup with timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.db_path.parent / f"{self.db_path.stem}_backup_{timestamp}.duckdb"
            console.print(f"[yellow]Creating backup: {backup_path}[/yellow]")
            import shutil
            shutil.copy2(self.db_path, backup_path)
            self.output_path = self.db_path

        self.conn = None

    def connect(self):
        """Connect to database."""
        self.conn = duckdb.connect(str(self.output_path))
        console.print(f"✓ Connected to database: {self.output_path}")

    def analyze_current_scenarios(self):
        """Analyze current scenario structure."""
        console.print("\n[bold]Analyzing current database structure...[/bold]")

        # Get scenario count and names
        result = self.conn.execute("""
            SELECT scenario_name, COUNT(*) as transitions
            FROM dim_scenario s
            JOIN fact_landuse_transitions f ON s.scenario_id = f.scenario_id
            GROUP BY scenario_name
            ORDER BY scenario_name
        """).fetchall()

        table = Table(title="Current Scenarios")
        table.add_column("Scenario", style="cyan")
        table.add_column("Transitions", style="green")

        total_transitions = 0
        scenario_groups = {
            'RCP45_SSP1': [],
            'RCP45_SSP5': [],
            'RCP85_SSP1': [],
            'RCP85_SSP5': []
        }

        for scenario_name, count in result:
            table.add_row(scenario_name, f"{count:,}")
            total_transitions += count

            # Categorize scenarios - note SSP2 and SSP3 in data, not SSP1 and SSP5
            if 'rcp45' in scenario_name.lower() and 'ssp1' in scenario_name.lower():
                scenario_groups['RCP45_SSP1'].append(scenario_name)
            elif 'rcp45' in scenario_name.lower() and 'ssp2' in scenario_name.lower():
                # Map SSP2 to SSP5 for this dataset
                scenario_groups['RCP45_SSP5'].append(scenario_name)
            elif 'rcp85' in scenario_name.lower() and ('ssp1' in scenario_name.lower() or 'ssp2' in scenario_name.lower()):
                scenario_groups['RCP85_SSP1'].append(scenario_name)
            elif 'rcp85' in scenario_name.lower() and ('ssp3' in scenario_name.lower() or 'ssp5' in scenario_name.lower()):
                scenario_groups['RCP85_SSP5'].append(scenario_name)

        console.print(table)
        console.print(f"\nTotal transitions: [bold]{total_transitions:,}[/bold]")

        # Show grouping
        console.print("\n[bold]Scenario Grouping for Combination:[/bold]")
        for combined, scenarios in scenario_groups.items():
            if scenarios:
                console.print(f"  {combined}: {len(scenarios)} scenarios")

        return scenario_groups

    def create_combined_schema(self):
        """Create schema for combined scenarios."""
        console.print("\n[bold]Creating combined scenarios schema...[/bold]")

        # Drop existing combined tables if they exist
        self.conn.execute("DROP TABLE IF EXISTS fact_landuse_combined")
        self.conn.execute("DROP TABLE IF EXISTS dim_scenario_combined")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            # Create new tables for combined scenarios
            task = progress.add_task("Creating dim_scenario_combined...", total=1)

            self.conn.execute("""
                CREATE TABLE dim_scenario_combined (
                    scenario_id INTEGER PRIMARY KEY,
                    scenario_name VARCHAR,
                    description VARCHAR,
                    rcp_scenario VARCHAR,
                    ssp_scenario VARCHAR,
                    narrative_description VARCHAR
                )
            """)
            progress.update(task, completed=1)

            # Create fact table for combined transitions
            task = progress.add_task("Creating fact_landuse_combined...", total=1)

            self.conn.execute("""
                CREATE TABLE fact_landuse_combined (
                    transition_id INTEGER,
                    scenario_id INTEGER,
                    time_id INTEGER,
                    geography_id INTEGER,
                    from_landuse_id INTEGER,
                    to_landuse_id INTEGER,
                    acres DOUBLE,
                    std_dev DOUBLE,
                    min_value DOUBLE,
                    max_value DOUBLE,
                    transition_type VARCHAR,
                    FOREIGN KEY (scenario_id) REFERENCES dim_scenario_combined(scenario_id)
                )
            """)
            progress.update(task, completed=1)

        console.print("✓ Combined scenario schema created")

    def populate_combined_scenarios(self):
        """Populate the combined scenario dimension."""
        console.print("\n[bold]Populating combined scenarios...[/bold]")

        scenarios = [
            (1, 'OVERALL', 'Ensemble mean of all scenarios', None, None,
             'Default scenario representing the average across all GCM projections'),
            (2, 'RCP45_SSP1', 'Sustainability pathway', 'RCP45', 'SSP1',
             'Low emissions with sustainable development, reduced inequality'),
            (3, 'RCP45_SSP5', 'Fossil-fueled Development', 'RCP45', 'SSP5',
             'Low emissions with rapid economic growth, high energy demand'),
            (4, 'RCP85_SSP1', 'Sustainability with high emissions', 'RCP85', 'SSP1',
             'High emissions but with sustainable development practices'),
            (5, 'RCP85_SSP5', 'Fossil-fueled Development', 'RCP85', 'SSP5',
             'High emissions with fossil-fueled development, high growth')
        ]

        for scenario in scenarios:
            self.conn.execute("""
                INSERT INTO dim_scenario_combined VALUES (?, ?, ?, ?, ?, ?)
            """, scenario)

        console.print(f"✓ Added {len(scenarios)} combined scenarios")

    def aggregate_transitions(self, scenario_groups):
        """Aggregate GCM transitions into combined scenarios."""
        console.print("\n[bold]Aggregating transitions into combined scenarios...[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:

            # Process each combined scenario
            for combined_name, combined_id in [
                ('RCP45_SSP1', 2),
                ('RCP45_SSP5', 3),
                ('RCP85_SSP1', 4),
                ('RCP85_SSP5', 5)
            ]:
                gcm_scenarios = scenario_groups.get(combined_name, [])
                if not gcm_scenarios:
                    console.print(f"[yellow]No scenarios found for {combined_name}[/yellow]")
                    continue

                task = progress.add_task(f"Aggregating {combined_name}...", total=1)

                # Get scenario IDs for this group
                scenario_list = ", ".join([f"'{s}'" for s in gcm_scenarios])

                # Get current max transition_id
                result = self.conn.execute("SELECT COALESCE(MAX(transition_id), 0) FROM fact_landuse_combined").fetchone()
                current_max_id = result[0]

                # Aggregate transitions
                self.conn.execute(f"""
                    INSERT INTO fact_landuse_combined
                    SELECT
                        ROW_NUMBER() OVER () + {current_max_id} as transition_id,
                        {combined_id} as scenario_id,
                        time_id,
                        geography_id,
                        from_landuse_id,
                        to_landuse_id,
                        AVG(acres) as acres,
                        STDDEV(acres) as std_dev,
                        MIN(acres) as min_value,
                        MAX(acres) as max_value,
                        transition_type
                    FROM fact_landuse_transitions f
                    JOIN dim_scenario s ON f.scenario_id = s.scenario_id
                    WHERE s.scenario_name IN ({scenario_list})
                    GROUP BY time_id, geography_id, from_landuse_id, to_landuse_id, transition_type
                """)

                progress.update(task, completed=1)

            # Create OVERALL scenario (mean of all scenarios)
            task = progress.add_task("Creating OVERALL scenario...", total=1)

            self.conn.execute("""
                INSERT INTO fact_landuse_combined
                SELECT
                    ROW_NUMBER() OVER () + (SELECT MAX(transition_id) FROM fact_landuse_combined) as transition_id,
                    1 as scenario_id,  -- OVERALL
                    time_id,
                    geography_id,
                    from_landuse_id,
                    to_landuse_id,
                    AVG(acres) as acres,
                    STDDEV(acres) as std_dev,
                    MIN(acres) as min_value,
                    MAX(acres) as max_value,
                    transition_type
                FROM fact_landuse_transitions
                GROUP BY time_id, geography_id, from_landuse_id, to_landuse_id, transition_type
            """)

            progress.update(task, completed=1)

        # Get counts
        result = self.conn.execute("""
            SELECT s.scenario_name, COUNT(*) as count
            FROM fact_landuse_combined f
            JOIN dim_scenario_combined s ON f.scenario_id = s.scenario_id
            GROUP BY s.scenario_name, s.scenario_id
            ORDER BY s.scenario_id
        """).fetchall()

        console.print("\n[bold]Combined Scenario Transition Counts:[/bold]")
        for name, count in result:
            console.print(f"  {name}: {count:,} transitions")

    def create_views(self):
        """Create database views for combined scenarios."""
        console.print("\n[bold]Creating database views...[/bold]")

        # View using OVERALL as default
        self.conn.execute("""
            CREATE OR REPLACE VIEW v_default_transitions AS
            SELECT
                f.*,
                s.scenario_name,
                t.year_range,
                t.start_year,
                t.end_year,
                g.county_name,
                g.state_name,
                fl.landuse_name as from_landuse,
                tl.landuse_name as to_landuse
            FROM fact_landuse_combined f
            JOIN dim_scenario_combined s ON f.scenario_id = s.scenario_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE s.scenario_name = 'OVERALL'
        """)

        # View for scenario comparisons (exclude OVERALL)
        self.conn.execute("""
            CREATE OR REPLACE VIEW v_scenario_comparisons AS
            SELECT
                f.*,
                s.scenario_name,
                s.rcp_scenario,
                s.ssp_scenario,
                t.year_range,
                t.start_year,
                t.end_year,
                g.county_name,
                g.state_name,
                fl.landuse_name as from_landuse,
                tl.landuse_name as to_landuse
            FROM fact_landuse_combined f
            JOIN dim_scenario_combined s ON f.scenario_id = s.scenario_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_geography g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE s.scenario_name != 'OVERALL'
        """)

        console.print("✓ Created v_default_transitions view (uses OVERALL)")
        console.print("✓ Created v_scenario_comparisons view (excludes OVERALL)")

    def update_original_tables(self):
        """Update original tables to point to combined scenarios."""
        console.print("\n[bold]Updating original table references...[/bold]")

        try:
            # Drop existing views that depend on original tables
            self.conn.execute("DROP VIEW IF EXISTS v_scenarios_combined")
            self.conn.execute("DROP VIEW IF EXISTS v_population_trends")
            self.conn.execute("DROP VIEW IF EXISTS v_income_trends")
            self.conn.execute("DROP VIEW IF EXISTS v_landuse_socioeconomic")
            self.conn.execute("DROP VIEW IF EXISTS v_full_projection_period")

            # Rename original tables
            self.conn.execute("ALTER TABLE dim_scenario RENAME TO dim_scenario_original")
            self.conn.execute("ALTER TABLE fact_landuse_transitions RENAME TO fact_landuse_transitions_original")

            # Rename combined tables to standard names
            self.conn.execute("ALTER TABLE dim_scenario_combined RENAME TO dim_scenario")
            self.conn.execute("ALTER TABLE fact_landuse_combined RENAME TO fact_landuse_transitions")

            console.print("✓ Updated table references")
            console.print("  Original tables preserved with '_original' suffix")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not rename tables: {e}[/yellow]")
            console.print("  Combined tables remain with '_combined' suffix")

    def verify_conversion(self):
        """Verify the conversion was successful."""
        console.print("\n[bold]Verifying conversion...[/bold]")

        # Try with renamed tables first, fall back to _combined suffix
        try:
            scenario_table = "dim_scenario"
            fact_table = "fact_landuse_transitions"
            result = self.conn.execute(f"SELECT COUNT(*) FROM {scenario_table} WHERE scenario_name = 'OVERALL'").fetchone()
        except:
            scenario_table = "dim_scenario_combined"
            fact_table = "fact_landuse_combined"

        # Check scenario count
        result = self.conn.execute(f"SELECT COUNT(*) FROM {scenario_table}").fetchone()
        scenario_count = result[0]

        # Check for OVERALL
        result = self.conn.execute(f"SELECT COUNT(*) FROM {scenario_table} WHERE scenario_name = 'OVERALL'").fetchone()
        has_overall = result[0] > 0

        # Check transitions
        result = self.conn.execute(f"SELECT COUNT(*) FROM {fact_table}").fetchone()
        transition_count = result[0]

        # Check statistical fields
        try:
            result = self.conn.execute(f"""
                SELECT COUNT(*) FROM (
                    SELECT * FROM {fact_table}
                    WHERE std_dev IS NOT NULL
                    LIMIT 1
                )
            """).fetchone()
            has_stats = result[0] > 0
        except:
            has_stats = False

        # Summary
        table = Table(title="Conversion Verification")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")

        table.add_row("Scenario count", f"{'✓' if scenario_count == 5 else '✗'} {scenario_count} scenarios")
        table.add_row("OVERALL scenario", f"{'✓' if has_overall else '✗'} {'Present' if has_overall else 'Missing'}")
        table.add_row("Transitions", f"✓ {transition_count:,} transitions")
        table.add_row("Statistical fields", f"{'✓' if has_stats else '✗'} {'Present' if has_stats else 'Missing'}")

        console.print(table)

        return scenario_count == 5 and has_overall

    def run(self):
        """Execute the full conversion process."""
        try:
            self.connect()

            # Analyze current structure
            scenario_groups = self.analyze_current_scenarios()

            # Create combined schema
            self.create_combined_schema()

            # Populate dimensions
            self.populate_combined_scenarios()

            # Aggregate transitions
            self.aggregate_transitions(scenario_groups)

            # Create views
            self.create_views()

            # Update table references
            self.update_original_tables()

            # Verify
            success = self.verify_conversion()

            if success:
                console.print("\n[bold green]✓ Conversion completed successfully![/bold green]")
            else:
                console.print("\n[bold yellow]⚠ Conversion completed with warnings[/bold yellow]")

        except Exception as e:
            console.print(f"\n[bold red]✗ Error during conversion: {e}[/bold red]")
            raise
        finally:
            if self.conn:
                self.conn.close()


def main():
    """Execute the conversion."""
    parser = argparse.ArgumentParser(
        description="Convert existing GCM scenarios to combined scenarios"
    )
    parser.add_argument(
        "--input",
        default="data/processed/landuse_analytics.duckdb",
        help="Input database path"
    )
    parser.add_argument(
        "--output",
        help="Output database path (default: modify input in-place with backup)"
    )

    args = parser.parse_args()

    console.print(f"[bold]Converting database to combined scenarios[/bold]")
    console.print(f"Input: {args.input}")
    console.print(f"Output: {args.output or 'In-place (with backup)'}\n")

    try:
        converter = DatabaseCombinedScenarioConverter(args.input, args.output)
        converter.run()
        return 0
    except Exception as e:
        console.print(f"[red]Conversion failed: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())