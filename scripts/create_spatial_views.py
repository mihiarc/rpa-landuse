#!/usr/bin/env python3
"""
Create spatial aggregation views in the RPA Land Use database.

This script creates database views for different spatial levels:
- County (base level)
- State 
- Region
- Subregion
- National

Usage:
    python create_spatial_views.py
"""

import duckdb
import os
from pathlib import Path

def create_spatial_views():
    """Create all spatial aggregation views in the database."""
    
    # Path to database
    db_path = Path(__file__).parent.parent / "data" / "database" / "rpa.db"
    sql_path = Path(__file__).parent / "create_spatial_views.sql"
    
    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        return False
        
    if not sql_path.exists():
        print(f"Error: SQL file not found at {sql_path}")
        return False
    
    print(f"Connecting to database: {db_path}")
    
    try:
        # Connect to database
        conn = duckdb.connect(str(db_path))
        
        # Read and execute the SQL script
        print(f"Reading SQL script: {sql_path}")
        with open(sql_path, 'r') as f:
            sql_script = f.read()
        
        # Split script into individual statements and execute
        statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
        
        print(f"Executing {len(statements)} SQL statements...")
        
        for i, statement in enumerate(statements):
            if statement.startswith('--') or not statement:
                continue
                
            try:
                conn.execute(statement)
                if 'CREATE' in statement.upper() and 'VIEW' in statement.upper():
                    view_name = extract_view_name(statement)
                    print(f"  ✓ Created view: {view_name}")
                elif 'CREATE' in statement.upper() and 'INDEX' in statement.upper():
                    print(f"  ✓ Created index")
            except Exception as e:
                print(f"  ✗ Error in statement {i+1}: {e}")
                print(f"    Statement: {statement[:100]}...")
        
        # Test the views
        print("\nTesting created views...")
        test_views(conn)
        
        conn.close()
        print("\n✅ Spatial views created successfully!")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def extract_view_name(statement):
    """Extract view name from CREATE VIEW statement."""
    try:
        # Find the view name between CREATE VIEW and AS
        parts = statement.upper().split()
        view_idx = parts.index('VIEW') + 1
        if parts[view_idx] == 'IF':
            view_idx += 3  # Skip IF NOT EXISTS
        return parts[view_idx]
    except:
        return "unknown"

def test_views(conn):
    """Test that the created views work correctly."""
    
    views_to_test = [
        'county_level_transitions',
        'state_level_transitions', 
        'region_level_transitions',
        'subregion_level_transitions',
        'national_level_transitions'
    ]
    
    for view_name in views_to_test:
        try:
            # Test basic count
            result = conn.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()
            row_count = result[0] if result else 0
            
            # Test data sample
            sample = conn.execute(f"SELECT * FROM {view_name} LIMIT 1").fetchone()
            
            if row_count > 0 and sample:
                print(f"  ✓ {view_name}: {row_count:,} rows")
            else:
                print(f"  ⚠ {view_name}: No data found")
                
        except Exception as e:
            print(f"  ✗ {view_name}: Error - {e}")

def show_view_info(conn):
    """Show information about available views."""
    
    print("\n" + "="*60)
    print("SPATIAL VIEWS SUMMARY")
    print("="*60)
    
    views_info = {
        'county_level_transitions': 'County-level land use transitions (base data)',
        'state_level_transitions': 'State-level aggregated transitions',
        'region_level_transitions': 'Regional-level aggregated transitions', 
        'subregion_level_transitions': 'Subregional-level aggregated transitions',
        'national_level_transitions': 'National-level aggregated transitions',
        'urbanization_by_county': 'County-level urbanization trends',
        'urbanization_by_state': 'State-level urbanization trends',
        'forest_loss_by_county': 'County-level forest loss trends',
        'forest_loss_by_state': 'State-level forest loss trends',
        'agricultural_transitions_by_county': 'County-level agricultural transitions',
        'agricultural_transitions_by_state': 'State-level agricultural transitions'
    }
    
    for view_name, description in views_info.items():
        try:
            result = conn.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()
            row_count = result[0] if result else 0
            print(f"{view_name:35} | {row_count:>8,} rows | {description}")
        except:
            print(f"{view_name:35} | {'ERROR':>8} | {description}")
    
    print("\n" + "="*60)
    print("Sample queries for testing:")
    print("="*60)
    print("-- Show all scenarios")
    print("SELECT DISTINCT scenario_name FROM county_level_transitions;")
    print("\n-- Show urbanization by state for ensemble scenario")
    print("SELECT * FROM urbanization_by_state WHERE scenario_name = 'ensemble_overall' LIMIT 10;")
    print("\n-- Compare spatial levels")
    print("SELECT COUNT(*) as county_rows FROM county_level_transitions;")
    print("SELECT COUNT(*) as state_rows FROM state_level_transitions;")
    print("SELECT COUNT(*) as national_rows FROM national_level_transitions;")

if __name__ == "__main__":
    print("RPA Land Use Viewer - Creating Spatial Views")
    print("=" * 50)
    
    success = create_spatial_views()
    
    if success:
        # Connect again to show info
        db_path = Path(__file__).parent.parent / "data" / "database" / "rpa.db"
        conn = duckdb.connect(str(db_path))
        show_view_info(conn)
        conn.close()
    else:
        print("❌ Failed to create spatial views")
        exit(1) 