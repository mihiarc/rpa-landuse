#!/usr/bin/env python3
"""
Convert nested landuse JSON data to a well-structured DuckDB database
This script normalizes the data into proper relational tables following modern data warehousing principles
"""

import json
import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import tempfile
from pathlib import Path
from rich.console import Console
from rich.progress import track, Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
import time
from typing import Dict, List, Tuple, Any, Union
import os

console = Console()

class LanduseDataConverter:
    """Convert nested landuse JSON to normalized DuckDB database using modern bulk loading techniques"""
    
    def __init__(self, input_file: str, output_file: str, use_bulk_copy: bool = True):
        self.input_file = Path(input_file)
        self.output_file = Path(output_file)
        self.conn = None
        self.use_bulk_copy = use_bulk_copy
        self.temp_dir = tempfile.mkdtemp(prefix="landuse_convert_")
        
        # Land use type mappings
        self.landuse_types = {
            'cr': 'Crop',
            'ps': 'Pasture', 
            'rg': 'Rangeland',
            'fr': 'Forest',
            'ur': 'Urban'
        }
        
        console.print(f"🚀 Using {'bulk COPY' if use_bulk_copy else 'traditional INSERT'} loading method")
        
    def create_schema(self):
        """Create the normalized database schema"""
        console.print(Panel.fit("🏗️ [bold blue]Creating DuckDB Schema[/bold blue]", border_style="blue"))
        
        # Connect to DuckDB
        self.conn = duckdb.connect(str(self.output_file))
        
        # Create dimension tables
        self._create_scenario_dim()
        self._create_time_dim()
        self._create_geography_dim()
        self._create_landuse_dim()
        
        # Create fact table
        self._create_landuse_transitions_fact()
        
        # Create indexes for performance
        self._create_indexes()
        
        console.print("✅ [green]Schema created successfully[/green]")
    
    def _create_scenario_dim(self):
        """Create scenario dimension table"""
        self.conn.execute("DROP TABLE IF EXISTS dim_scenario")
        self.conn.execute("""
            CREATE TABLE dim_scenario (
                scenario_id INTEGER PRIMARY KEY,
                scenario_name VARCHAR(100) NOT NULL,
                climate_model VARCHAR(50),
                rcp_scenario VARCHAR(20),
                ssp_scenario VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
    def _create_time_dim(self):
        """Create time dimension table"""
        self.conn.execute("DROP TABLE IF EXISTS dim_time")
        self.conn.execute("""
            CREATE TABLE dim_time (
                time_id INTEGER PRIMARY KEY,
                year_range VARCHAR(20) NOT NULL,
                start_year INTEGER,
                end_year INTEGER,
                period_length INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
    def _create_geography_dim(self):
        """Create geography dimension table"""
        self.conn.execute("DROP TABLE IF EXISTS dim_geography_enhanced")
        self.conn.execute("""
            CREATE TABLE dim_geography_enhanced (
                geography_id INTEGER PRIMARY KEY,
                fips_code VARCHAR(10) NOT NULL UNIQUE,
                county_name VARCHAR(100),
                state_code VARCHAR(2),
                state_name VARCHAR(50),
                region VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
    def _create_landuse_dim(self):
        """Create landuse dimension table"""
        self.conn.execute("DROP TABLE IF EXISTS dim_landuse")
        self.conn.execute("""
            CREATE TABLE dim_landuse (
                landuse_id INTEGER PRIMARY KEY,
                landuse_code VARCHAR(10) NOT NULL UNIQUE,
                landuse_name VARCHAR(50) NOT NULL,
                landuse_category VARCHAR(30),
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Insert landuse types
        for i, (code, name) in enumerate(self.landuse_types.items(), 1):
            category = self._get_landuse_category(name)
            self.conn.execute("""
                INSERT INTO dim_landuse (landuse_id, landuse_code, landuse_name, landuse_category, description)
                VALUES (?, ?, ?, ?, ?)
            """, (i, code, name, category, f"{name} land use type"))
    
    def _create_landuse_transitions_fact(self):
        """Create the main fact table for landuse transitions"""
        self.conn.execute("DROP TABLE IF EXISTS fact_landuse_transitions")
        self.conn.execute("""
            CREATE TABLE fact_landuse_transitions (
                transition_id BIGINT PRIMARY KEY,
                scenario_id INTEGER NOT NULL,
                time_id INTEGER NOT NULL,
                geography_id INTEGER NOT NULL,
                from_landuse_id INTEGER NOT NULL,
                to_landuse_id INTEGER NOT NULL,
                acres DECIMAL(15,4) NOT NULL,
                transition_type VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (scenario_id) REFERENCES dim_scenario(scenario_id),
                FOREIGN KEY (time_id) REFERENCES dim_time(time_id),
                FOREIGN KEY (geography_id) REFERENCES dim_geography_enhanced(geography_id),
                FOREIGN KEY (from_landuse_id) REFERENCES dim_landuse(landuse_id),
                FOREIGN KEY (to_landuse_id) REFERENCES dim_landuse(landuse_id)
            )
        """)
    
    def _create_indexes(self):
        """Create performance indexes"""
        indexes = [
            "CREATE INDEX idx_scenario_name ON dim_scenario(scenario_name)",
            "CREATE INDEX idx_time_range ON dim_time(year_range)",
            "CREATE INDEX idx_geography_fips ON dim_geography_enhanced(fips_code)",
            "CREATE INDEX idx_landuse_code ON dim_landuse(landuse_code)",
            "CREATE INDEX idx_fact_scenario ON fact_landuse_transitions(scenario_id)",
            "CREATE INDEX idx_fact_time ON fact_landuse_transitions(time_id)",
            "CREATE INDEX idx_fact_geography ON fact_landuse_transitions(geography_id)",
            "CREATE INDEX idx_fact_from_landuse ON fact_landuse_transitions(from_landuse_id)",
            "CREATE INDEX idx_fact_to_landuse ON fact_landuse_transitions(to_landuse_id)",
            "CREATE INDEX idx_fact_composite ON fact_landuse_transitions(scenario_id, time_id, geography_id)"
        ]
        
        for idx in indexes:
            self.conn.execute(idx)
    
    def _get_landuse_category(self, landuse_name: str) -> str:
        """Categorize landuse types"""
        if landuse_name in ['Crop', 'Pasture']:
            return 'Agriculture'
        elif landuse_name == 'Forest':
            return 'Natural'
        elif landuse_name == 'Urban':
            return 'Developed'
        elif landuse_name == 'Rangeland':
            return 'Natural'
        else:
            return 'Other'
    
    def load_data(self):
        """Load and transform the JSON data into the normalized database"""
        console.print(Panel.fit("📊 [bold yellow]Loading Data[/bold yellow]", border_style="yellow"))
        
        # Load JSON data
        with open(self.input_file, 'r') as f:
            data = json.load(f)
        
        # Extract and load dimension data
        scenarios = self._extract_scenarios(data)
        time_periods = self._extract_time_periods(data)
        geographies = self._extract_geographies(data)
        
        self._load_scenarios(scenarios)
        self._load_time_periods(time_periods)
        self._load_geographies(geographies)
        
        # Load fact data
        self._load_transitions(data)
        
        console.print("✅ [green]Data loaded successfully[/green]")
    
    def _extract_scenarios(self, data: Dict) -> List[str]:
        """Extract unique scenarios from the data"""
        return list(data.keys())
    
    def _extract_time_periods(self, data: Dict) -> List[str]:
        """Extract unique time periods from the data"""
        time_periods = set()
        for scenario_data in data.values():
            time_periods.update(scenario_data.keys())
        return list(time_periods)
    
    def _extract_geographies(self, data: Dict) -> List[str]:
        """Extract unique FIPS codes from the data"""
        fips_codes = set()
        for scenario_data in data.values():
            for time_data in scenario_data.values():
                fips_codes.update(time_data.keys())
        return list(fips_codes)
    
    def _load_scenarios(self, scenarios: List[str]):
        """Load scenario dimension data using bulk copy"""
        if self.use_bulk_copy:
            # Prepare data for bulk loading
            scenario_data = []
            for i, scenario in enumerate(scenarios):
                # Parse scenario components
                parts = scenario.split('_')
                climate_model = parts[0] if len(parts) > 0 else None
                rcp = parts[2] if len(parts) > 2 else None
                ssp = parts[3] if len(parts) > 3 else None
                
                scenario_data.append({
                    'scenario_id': i + 1,
                    'scenario_name': scenario,
                    'climate_model': climate_model,
                    'rcp_scenario': rcp,
                    'ssp_scenario': ssp
                })
            
            # Create DataFrame and use DuckDB COPY
            df = pd.DataFrame(scenario_data)
            temp_file = Path(self.temp_dir) / "scenarios.parquet"
            df.to_parquet(temp_file, index=False)
            
            console.print(f"📥 Loading {len(scenarios)} scenarios via COPY...")
            self.conn.execute(f"""
                COPY dim_scenario (scenario_id, scenario_name, climate_model, rcp_scenario, ssp_scenario)
                FROM '{temp_file}' (FORMAT PARQUET)
            """)
        else:
            # Traditional method for comparison
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Loading scenarios...", total=len(scenarios))
                
                for i, scenario in enumerate(scenarios):
                    # Parse scenario components
                    parts = scenario.split('_')
                    climate_model = parts[0] if len(parts) > 0 else None
                    rcp = parts[2] if len(parts) > 2 else None
                    ssp = parts[3] if len(parts) > 3 else None
                    
                    self.conn.execute("""
                        INSERT INTO dim_scenario (scenario_id, scenario_name, climate_model, rcp_scenario, ssp_scenario)
                        VALUES (?, ?, ?, ?, ?)
                    """, (i + 1, scenario, climate_model, rcp, ssp))
                    
                    progress.update(task, advance=1)
    
    def _load_time_periods(self, time_periods: List[str]):
        """Load time dimension data using bulk copy"""
        if self.use_bulk_copy:
            # Prepare data for bulk loading
            time_data = []
            for i, period in enumerate(time_periods):
                # Parse year range
                start_year, end_year = map(int, period.split('-'))
                period_length = end_year - start_year
                
                time_data.append({
                    'time_id': i + 1,
                    'year_range': period,
                    'start_year': start_year,
                    'end_year': end_year,
                    'period_length': period_length
                })
            
            # Create DataFrame and use DuckDB COPY
            df = pd.DataFrame(time_data)
            temp_file = Path(self.temp_dir) / "time_periods.parquet"
            df.to_parquet(temp_file, index=False)
            
            console.print(f"📥 Loading {len(time_periods)} time periods via COPY...")
            self.conn.execute(f"""
                COPY dim_time (time_id, year_range, start_year, end_year, period_length)
                FROM '{temp_file}' (FORMAT PARQUET)
            """)
        else:
            # Traditional method for comparison
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Loading time periods...", total=len(time_periods))
                
                for i, period in enumerate(time_periods):
                    # Parse year range
                    start_year, end_year = map(int, period.split('-'))
                    period_length = end_year - start_year
                    
                    self.conn.execute("""
                        INSERT INTO dim_time (time_id, year_range, start_year, end_year, period_length)
                        VALUES (?, ?, ?, ?, ?)
                    """, (i + 1, period, start_year, end_year, period_length))
                    
                    progress.update(task, advance=1)
    
    def _load_geographies(self, fips_codes: List[str]):
        """Load geography dimension data using bulk copy"""
        if self.use_bulk_copy:
            # Prepare data for bulk loading
            geo_data = []
            for i, fips in enumerate(fips_codes):
                # Extract state and county info from FIPS
                state_code = fips[:2]
                county_code = fips[2:]
                
                geo_data.append({
                    'geography_id': i + 1,
                    'fips_code': fips,
                    'state_code': state_code,
                    'county_name': None,  # Will be populated later if needed
                    'state_name': None,   # Will be populated later if needed
                    'region': None        # Will be populated later if needed
                })
            
            # Create DataFrame and use DuckDB COPY
            df = pd.DataFrame(geo_data)
            temp_file = Path(self.temp_dir) / "geographies.parquet"
            df.to_parquet(temp_file, index=False)
            
            console.print(f"📥 Loading {len(fips_codes)} geographies via COPY...")
            self.conn.execute(f"""
                COPY dim_geography_enhanced (geography_id, fips_code, state_code, county_name, state_name, region)
                FROM '{temp_file}' (FORMAT PARQUET)
            """)
        else:
            # Traditional method for comparison
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Loading geographies...", total=len(fips_codes))
                
                for i, fips in enumerate(fips_codes):
                    # Extract state and county info from FIPS
                    state_code = fips[:2]
                    county_code = fips[2:]
                    
                    self.conn.execute("""
                        INSERT INTO dim_geography_enhanced (geography_id, fips_code, state_code)
                        VALUES (?, ?, ?)
                    """, (i + 1, fips, state_code))
                    
                    progress.update(task, advance=1)
    
    def _load_transitions(self, data: Dict):
        """Load the main fact table data using bulk copy for maximum performance"""
        console.print("🔄 [cyan]Processing transitions data...[/cyan]")
        
        # Get dimension lookups
        scenario_lookup = {row[1]: row[0] for row in self.conn.execute("SELECT scenario_id, scenario_name FROM dim_scenario").fetchall()}
        time_lookup = {row[1]: row[0] for row in self.conn.execute("SELECT time_id, year_range FROM dim_time").fetchall()}
        geography_lookup = {row[1]: row[0] for row in self.conn.execute("SELECT geography_id, fips_code FROM dim_geography_enhanced").fetchall()}
        landuse_lookup = {row[1]: row[0] for row in self.conn.execute("SELECT landuse_id, landuse_code FROM dim_landuse").fetchall()}
        
        if self.use_bulk_copy:
            # Use bulk copy method with Parquet files
            self._load_transitions_bulk_copy(data, scenario_lookup, time_lookup, geography_lookup, landuse_lookup)
        else:
            # Traditional batch insert method
            self._load_transitions_traditional(data, scenario_lookup, time_lookup, geography_lookup, landuse_lookup)
    
    def _load_transitions_bulk_copy(self, data: Dict, scenario_lookup: Dict, time_lookup: Dict, geography_lookup: Dict, landuse_lookup: Dict):
        """Load transitions using DuckDB COPY from Parquet files"""
        console.print("🚀 [bold cyan]Using optimized bulk COPY loading...[/bold cyan]")
        
        transition_id = 1
        batch_size = 100000  # Larger batches for bulk loading
        current_batch = []
        batch_num = 0
        
        # Calculate total for progress
        total_transitions = self._count_total_transitions(data)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Bulk loading transitions...", total=total_transitions)
            processed = 0
            
            for scenario, scenario_data in data.items():
                scenario_id = scenario_lookup[scenario]
                
                for time_range, time_data in scenario_data.items():
                    time_id = time_lookup[time_range]
                    
                    for fips, fips_data in time_data.items():
                        geography_id = geography_lookup[fips]
                        
                        if isinstance(fips_data, list):
                            for transition in fips_data:
                                from_landuse = transition.get('_row')
                                if from_landuse in landuse_lookup:
                                    from_landuse_id = landuse_lookup[from_landuse]
                                    
                                    for to_code, acres in transition.items():
                                        if to_code not in ['_row', 't1'] and to_code in landuse_lookup:
                                            to_landuse_id = landuse_lookup[to_code]
                                            
                                            if acres > 0:
                                                transition_type = 'same' if from_landuse == to_code else 'change'
                                                
                                                current_batch.append({
                                                    'transition_id': transition_id,
                                                    'scenario_id': scenario_id,
                                                    'time_id': time_id,
                                                    'geography_id': geography_id,
                                                    'from_landuse_id': from_landuse_id,
                                                    'to_landuse_id': to_landuse_id,
                                                    'acres': float(acres),
                                                    'transition_type': transition_type
                                                })
                                                
                                                transition_id += 1
                                                processed += 1
                                                
                                                if len(current_batch) >= batch_size:
                                                    self._write_and_copy_batch(current_batch, batch_num)
                                                    current_batch = []
                                                    batch_num += 1
                                                    
                                                if processed % 50000 == 0:  # Update less frequently for performance
                                                    progress.update(task, completed=processed)
            
            # Handle remaining data
            if current_batch:
                self._write_and_copy_batch(current_batch, batch_num)
            
            progress.update(task, completed=processed)
    
    def _load_transitions_traditional(self, data: Dict, scenario_lookup: Dict, time_lookup: Dict, geography_lookup: Dict, landuse_lookup: Dict):
        """Traditional batch insert method for comparison"""
        console.print("🐌 [yellow]Using traditional INSERT method...[/yellow]")
        
        transition_id = 1
        batch_size = 10000
        batch_data = []
        
        # Calculate total records for progress
        total_transitions = self._count_total_transitions(data)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Loading transitions...", total=total_transitions)
            processed = 0
            
            for scenario, scenario_data in data.items():
                scenario_id = scenario_lookup[scenario]
                
                for time_range, time_data in scenario_data.items():
                    time_id = time_lookup[time_range]
                    
                    for fips, fips_data in time_data.items():
                        geography_id = geography_lookup[fips]
                        
                        if isinstance(fips_data, list):
                            for transition in fips_data:
                                from_landuse = transition.get('_row')
                                if from_landuse in landuse_lookup:
                                    from_landuse_id = landuse_lookup[from_landuse]
                                    
                                    for to_code, acres in transition.items():
                                        if to_code not in ['_row', 't1'] and to_code in landuse_lookup:
                                            to_landuse_id = landuse_lookup[to_code]
                                            
                                            if acres > 0:
                                                transition_type = 'same' if from_landuse == to_code else 'change'
                                                
                                                batch_data.append((
                                                    transition_id,
                                                    scenario_id,
                                                    time_id,
                                                    geography_id,
                                                    from_landuse_id,
                                                    to_landuse_id,
                                                    float(acres),
                                                    transition_type
                                                ))
                                                
                                                transition_id += 1
                                                processed += 1
                                                
                                                if len(batch_data) >= batch_size:
                                                    self._insert_batch(batch_data)
                                                    batch_data = []
                                                    
                                                progress.update(task, completed=processed)
            
            # Insert remaining data
            if batch_data:
                self._insert_batch(batch_data)
    
    def _count_total_transitions(self, data: Dict) -> int:
        """Count total transitions for progress tracking"""
        total = 0
        for scenario_data in data.values():
            for time_data in scenario_data.values():
                for fips_data in time_data.values():
                    if isinstance(fips_data, list):
                        for transition in fips_data:
                            total += len([k for k in transition.keys() if k not in ['_row', 't1']])
        return total
    
    def _write_and_copy_batch(self, batch_data: List[Dict], batch_num: int):
        """Write batch to Parquet file and use DuckDB COPY to load it"""
        # Create DataFrame from batch
        df = pd.DataFrame(batch_data)
        
        # Write to temporary Parquet file
        temp_file = Path(self.temp_dir) / f"transitions_batch_{batch_num}.parquet"
        df.to_parquet(temp_file, index=False)
        
        # Use DuckDB COPY to load the batch
        self.conn.execute(f"""
            COPY fact_landuse_transitions 
            (transition_id, scenario_id, time_id, geography_id, from_landuse_id, to_landuse_id, acres, transition_type)
            FROM '{temp_file}' (FORMAT PARQUET)
        """)
        
        # Clean up temporary file to save space
        temp_file.unlink()
    
    def _insert_batch(self, batch_data: List[Tuple]):
        """Insert a batch of transition records"""
        self.conn.executemany("""
            INSERT INTO fact_landuse_transitions 
            (transition_id, scenario_id, time_id, geography_id, from_landuse_id, to_landuse_id, acres, transition_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, batch_data)
    
    def create_views(self):
        """Create useful analytical views"""
        console.print(Panel.fit("📊 [bold green]Creating Analytical Views[/bold green]", border_style="green"))
        
        # Agriculture transitions view
        self.conn.execute("""
            CREATE VIEW v_agriculture_transitions AS
            SELECT 
                s.scenario_name,
                t.year_range,
                g.fips_code,
                g.state_code,
                fl.landuse_name as from_landuse,
                tl.landuse_name as to_landuse,
                f.acres,
                f.transition_type
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            WHERE fl.landuse_category = 'Agriculture' OR tl.landuse_category = 'Agriculture'
        """)
        
        # Summary by scenario view
        self.conn.execute("""
            CREATE VIEW v_scenario_summary AS
            SELECT 
                s.scenario_name,
                t.year_range,
                fl.landuse_name as from_landuse,
                tl.landuse_name as to_landuse,
                COUNT(*) as transition_count,
                SUM(f.acres) as total_acres,
                AVG(f.acres) as avg_acres
            FROM fact_landuse_transitions f
            JOIN dim_scenario s ON f.scenario_id = s.scenario_id
            JOIN dim_time t ON f.time_id = t.time_id
            JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
            JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
            GROUP BY s.scenario_name, t.year_range, fl.landuse_name, tl.landuse_name
        """)
        
        # Total land area view for percentage calculations
        self.conn.execute("""
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
        
        console.print("✅ [green]Views created successfully[/green]")
    
    def generate_summary(self):
        """Generate a summary of the converted database"""
        console.print(Panel.fit("📈 [bold magenta]Database Summary[/bold magenta]", border_style="magenta"))
        
        # Create summary table
        table = Table(title="🦆 DuckDB Database Summary", show_header=True, header_style="bold cyan")
        table.add_column("Table", style="yellow", no_wrap=True)
        table.add_column("Records", justify="right", style="green")
        table.add_column("Description", style="white")
        
        tables = [
            ("dim_scenario", "Climate scenarios and models"),
            ("dim_time", "Time periods and ranges"),
            ("dim_geography_enhanced", "Geographic locations (FIPS codes)"),
            ("dim_landuse", "Land use types and categories"),
            ("fact_landuse_transitions", "Main fact table with all transitions")
        ]
        
        for table_name, description in tables:
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            table.add_row(table_name, f"{count:,}", description)
        
        console.print(table)
        
        # Show file size
        file_size = self.output_file.stat().st_size / (1024 * 1024)  # MB
        console.print(f"\n📁 Database file size: [bold cyan]{file_size:.2f} MB[/bold cyan]")
    
    def close(self):
        """Close database connection and clean up temporary files"""
        if self.conn:
            self.conn.close()
        
        # Clean up temporary directory
        import shutil
        if os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                console.print(f"🧹 Cleaned up temporary files from {self.temp_dir}")
            except Exception as e:
                console.print(f"⚠️ Warning: Could not clean up temp directory: {e}")

def main():
    """Main conversion function with performance options"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Convert landuse JSON to DuckDB")
    parser.add_argument("--no-bulk-copy", action="store_true", 
                       help="Use traditional INSERT instead of bulk COPY (for performance comparison)")
    parser.add_argument("--input", default="data/raw/county_landuse_projections_RPA.json",
                       help="Input JSON file path")
    parser.add_argument("--output", default="data/processed/landuse_analytics.duckdb",
                       help="Output DuckDB file path")
    
    args = parser.parse_args()
    use_bulk_copy = not args.no_bulk_copy
    
    console.print(Panel.fit(
        "🦆 [bold blue]DuckDB Landuse Database Converter[/bold blue]\n"
        f"[yellow]Converting nested JSON to normalized relational database[/yellow]\n"
        f"[cyan]Method: {'Bulk COPY (optimized)' if use_bulk_copy else 'Traditional INSERT'}[/cyan]",
        border_style="blue"
    ))
    
    converter = LanduseDataConverter(args.input, args.output, use_bulk_copy=use_bulk_copy)
    
    try:
        start_time = time.time()
        
        # Create schema
        converter.create_schema()
        
        # Load data
        converter.load_data()
        
        # Create views
        converter.create_views()
        
        # Generate summary
        converter.generate_summary()
        
        end_time = time.time()
        duration = end_time - start_time
        
        console.print(Panel.fit(
            f"✅ [bold green]Conversion Complete![/bold green]\n"
            f"⏱️ Duration: {duration:.2f} seconds\n"
            f"📁 Output: {output_file}",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(Panel.fit(f"❌ [bold red]Error: {str(e)}[/bold red]", border_style="red"))
        raise
    finally:
        converter.close()

if __name__ == "__main__":
    main() 