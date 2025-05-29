#!/usr/bin/env python3
"""
Create spatial aggregation views step by step.
"""

import duckdb
from pathlib import Path

def create_views_step_by_step():
    """Create views one by one in the correct order."""
    
    db_path = Path(__file__).parent.parent / "data" / "database" / "rpa.db"
    conn = duckdb.connect(str(db_path))
    
    try:
        print("Creating spatial aggregation views...")
        
        # Step 1: Create county level view
        print("1. Creating county_level_transitions...")
        conn.execute("""
            CREATE OR REPLACE VIEW county_level_transitions AS
            SELECT 
                s.scenario_name,
                d.decade_name,
                c.fips_code,
                c.county_name,
                c.state_name,
                c.region,
                c.subregion,
                lt_from.landuse_type_name as from_category,
                lt_to.landuse_type_name as to_category,
                lc.area_hundreds_acres * 100 as total_area
            FROM landuse_change lc
            JOIN scenarios s ON lc.scenario_id = s.scenario_id
            JOIN decades d ON lc.decade_id = d.decade_id
            JOIN counties c ON lc.fips_code = c.fips_code
            JOIN landuse_types lt_from ON lc.from_landuse = lt_from.landuse_type_code
            JOIN landuse_types lt_to ON lc.to_landuse = lt_to.landuse_type_code
        """)
        
        # Step 2: Create state level view
        print("2. Creating state_level_transitions...")
        conn.execute("""
            CREATE OR REPLACE VIEW state_level_transitions AS
            SELECT 
                scenario_name,
                decade_name,
                state_name,
                region,
                subregion,
                lt_from.landuse_type_name as from_category,
                lt_to.landuse_type_name as to_category,
                total_area * 100 as total_area
            FROM mat_state_transitions mst
            JOIN landuse_types lt_from ON mst.from_landuse = lt_from.landuse_type_code
            JOIN landuse_types lt_to ON mst.to_landuse = lt_to.landuse_type_code
        """)
        
        # Step 3: Create region level view  
        print("3. Creating region_level_transitions...")
        conn.execute("""
            CREATE OR REPLACE VIEW region_level_transitions AS
            SELECT 
                scenario_name,
                decade_name,
                region,
                lt_from.landuse_type_name as from_category,
                lt_to.landuse_type_name as to_category,
                SUM(total_area * 100) as total_area
            FROM mat_region_transitions mrt
            JOIN landuse_types lt_from ON mrt.from_landuse = lt_from.landuse_type_code
            JOIN landuse_types lt_to ON mrt.to_landuse = lt_to.landuse_type_code
            GROUP BY 
                scenario_name,
                decade_name,
                region,
                lt_from.landuse_type_name,
                lt_to.landuse_type_name
        """)
        
        # Step 4: Create subregion level view
        print("4. Creating subregion_level_transitions...")
        conn.execute("""
            CREATE OR REPLACE VIEW subregion_level_transitions AS
            SELECT 
                scenario_name,
                decade_name,
                subregion,
                lt_from.landuse_type_name as from_category,
                lt_to.landuse_type_name as to_category,
                SUM(total_area * 100) as total_area
            FROM mat_subregion_transitions msrt
            JOIN landuse_types lt_from ON msrt.from_landuse = lt_from.landuse_type_code
            JOIN landuse_types lt_to ON msrt.to_landuse = lt_to.landuse_type_code
            GROUP BY 
                scenario_name,
                decade_name,
                subregion,
                lt_from.landuse_type_name,
                lt_to.landuse_type_name
        """)
        
        # Step 5: Create national level view
        print("5. Creating national_level_transitions...")
        conn.execute("""
            CREATE OR REPLACE VIEW national_level_transitions AS
            SELECT 
                scenario_name,
                decade_name,
                'United States' as country,
                from_category,
                to_category,
                SUM(total_area) as total_area
            FROM state_level_transitions
            GROUP BY 
                scenario_name,
                decade_name,
                from_category,
                to_category
        """)
        
        # Step 6: Create dataset mapping views for Streamlit app
        print("6. Creating dataset mapping views...")
        
        conn.execute('CREATE OR REPLACE VIEW "County-Level Land Use Transitions" AS SELECT * FROM county_level_transitions')
        conn.execute('CREATE OR REPLACE VIEW "State-Level Land Use Transitions" AS SELECT * FROM state_level_transitions')
        conn.execute('CREATE OR REPLACE VIEW "Region-Level Land Use Transitions" AS SELECT * FROM region_level_transitions')
        conn.execute('CREATE OR REPLACE VIEW "Subregion-Level Land Use Transitions" AS SELECT * FROM subregion_level_transitions')
        conn.execute('CREATE OR REPLACE VIEW "National-Level Land Use Transitions" AS SELECT * FROM national_level_transitions')
        
        # Step 7: Test all views
        print("\n=== Testing Views ===")
        views = [
            'county_level_transitions',
            'state_level_transitions', 
            'region_level_transitions',
            'subregion_level_transitions',
            'national_level_transitions',
            '"County-Level Land Use Transitions"',
            '"State-Level Land Use Transitions"',
            '"Region-Level Land Use Transitions"',
            '"Subregion-Level Land Use Transitions"',
            '"National-Level Land Use Transitions"'
        ]
        
        for view in views:
            try:
                result = conn.execute(f"SELECT COUNT(*) FROM {view}").fetchone()
                count = result[0] if result else 0
                print(f"  ✓ {view}: {count:,} rows")
            except Exception as e:
                print(f"  ✗ {view}: Error - {e}")
        
        print("\n✅ All spatial views created successfully!")
        
        # Show sample data
        print("\n=== Sample Data ===")
        print("State level sample:")
        sample = conn.execute("SELECT * FROM state_level_transitions LIMIT 3").fetchall()
        for row in sample:
            print(f"  {row}")
            
        print("\nAvailable scenarios:")
        scenarios = conn.execute("SELECT DISTINCT scenario_name FROM state_level_transitions ORDER BY scenario_name LIMIT 5").fetchall()
        for row in scenarios:
            print(f"  {row[0]}")
            
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        conn.close()
    
    return True

if __name__ == "__main__":
    success = create_views_step_by_step()
    if not success:
        exit(1) 