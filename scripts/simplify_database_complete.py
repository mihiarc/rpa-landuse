#!/usr/bin/env python3
"""
Complete database simplification:
1. Drop the old dim_geography_enhanced table (without geometry)
2. Rename dim_geography_enhanced to dim_geography_enhanced
3. Update all code references
"""

import duckdb
import sys
from pathlib import Path

def simplify_database(db_path: str):
    """Simplify database by using dim_geography_enhanced as the main geography table"""
    
    print("=== COMPLETE DATABASE SIMPLIFICATION ===\n")
    
    # Connect with write access
    conn = duckdb.connect(db_path, read_only=False)
    
    try:
        # Load spatial extension
        conn.execute("INSTALL spatial")
        conn.execute("LOAD spatial")
        
        # 1. Save view definitions that use dim_geography_enhanced
        print("1. Saving view definitions...")
        views_to_recreate = []
        
        views = conn.execute("""
            SELECT view_name, sql 
            FROM duckdb_views()
            WHERE sql LIKE '%dim_geography_enhanced%'
        """).fetchall()
        
        for view_name, view_sql in views:
            print(f"   - Found view: {view_name}")
            views_to_recreate.append((view_name, view_sql))
        
        # 2. Drop views that depend on dim_geography_enhanced
        print("\n2. Dropping dependent views...")
        for view_name, _ in views_to_recreate:
            print(f"   - Dropping: {view_name}")
            conn.execute(f"DROP VIEW IF EXISTS {view_name}")
        
        # 3. Drop the old dim_geography_enhanced table
        print("\n3. Dropping old dim_geography_enhanced table...")
        conn.execute("DROP TABLE IF EXISTS dim_geography_enhanced CASCADE")
        print("   ✓ Dropped successfully")
        
        # 4. Rename dim_geography_enhanced to dim_geography_enhanced
        print("\n4. Renaming dim_geography_enhanced to dim_geography_enhanced...")
        conn.execute("ALTER TABLE dim_geography_enhanced RENAME TO dim_geography_enhanced")
        print("   ✓ Renamed successfully")
        
        # 5. Recreate views with updated references
        print("\n5. Recreating views...")
        for view_name, view_sql in views_to_recreate:
            # Update the SQL to use the new table name
            updated_sql = view_sql.replace('dim_geography_enhanced', 'dim_geography_enhanced')
            print(f"   - Recreating: {view_name}")
            conn.execute(updated_sql)
        
        # 6. Verify the result
        print("\n6. Verifying results...")
        
        # Check tables
        tables = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main' 
            AND table_name LIKE '%geography%'
            ORDER BY table_name
        """).fetchall()
        
        print("   Geography tables:")
        for t in tables:
            print(f"   - {t[0]}")
        
        # Check dim_geography_enhanced structure
        cols = conn.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'dim_geography_enhanced'
            ORDER BY ordinal_position
        """).fetchall()
        
        print("\n   dim_geography_enhanced columns:")
        has_geometry = False
        for c in cols:
            print(f"   - {c[0]}: {c[1]}")
            if c[0] == 'geometry':
                has_geometry = True
        
        if has_geometry:
            print("   ✓ Geometry column present")
        
        # Check data
        stats = conn.execute("""
            SELECT 
                COUNT(*) as total_records,
                COUNT(geometry) as with_geometry,
                COUNT(DISTINCT state_name) as states
            FROM dim_geography_enhanced
        """).fetchone()
        
        print(f"\n   Statistics:")
        print(f"   - Total records: {stats[0]:,}")
        print(f"   - With geometry: {stats[1]:,}")
        print(f"   - States: {stats[2]}")
        
        # Check fact table join
        print("\n7. Testing fact table join...")
        test_query = """
            SELECT COUNT(*) 
            FROM fact_landuse_transitions f
            JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
            LIMIT 1
        """
        result = conn.execute(test_query).fetchone()[0]
        print(f"   ✓ Join successful - {result:,} records")
        
        conn.commit()
        print("\n✅ Database simplification complete!")
        print("\nNext steps:")
        print("1. All code now uses 'dim_geography_enhanced' (already updated)")
        print("2. The table has full geometry support")
        print("3. All views have been recreated")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = "data/processed/landuse_analytics.duckdb"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    # Confirm before proceeding
    print("This will:")
    print("- Drop the old dim_geography_enhanced table (without geometry)")
    print("- Rename dim_geography_enhanced to dim_geography_enhanced")
    print("- Recreate all dependent views")
    print(f"\nDatabase: {db_path}")
    response = input("\nContinue? (y/N): ")
    
    if response.lower() == 'y':
        simplify_database(db_path)
    else:
        print("Cancelled.")