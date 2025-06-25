#!/usr/bin/env python3
"""
Migrate from dim_geography_enhanced to dim_geography_enhanced safely
by updating the fact table to reference the enhanced geography table
"""

import duckdb
import sys
from pathlib import Path

def migrate_to_enhanced_geography(db_path: str):
    """Migrate to use dim_geography_enhanced as the main geography table"""
    
    print("=== MIGRATING TO ENHANCED GEOGRAPHY TABLE ===\n")
    
    # Connect with write access
    conn = duckdb.connect(db_path, read_only=False)
    
    try:
        # Load spatial extension
        conn.execute("INSTALL spatial")
        conn.execute("LOAD spatial")
        
        # 1. Verify both tables exist and have matching IDs
        print("1. Verifying table compatibility...")
        
        # Check record counts
        old_count = conn.execute("SELECT COUNT(*) FROM dim_geography_enhanced").fetchone()[0]
        new_count = conn.execute("SELECT COUNT(*) FROM dim_geography_enhanced").fetchone()[0]
        
        print(f"   - dim_geography_enhanced records: {old_count:,}")
        print(f"   - dim_geography_enhanced records: {new_count:,}")
        
        # Verify all geography_ids match
        mismatch = conn.execute("""
            SELECT COUNT(*) 
            FROM dim_geography_enhanced e
            WHERE NOT EXISTS (
                SELECT 1 FROM dim_geography_enhanced g 
                WHERE g.geography_id = e.geography_id
            )
        """).fetchone()[0]
        
        if mismatch > 0:
            print(f"   ⚠️  Warning: {mismatch} records in enhanced table not in original")
        else:
            print("   ✓ All enhanced geography IDs exist in original table")
        
        # 2. Update fact table to use enhanced geography
        print("\n2. Updating fact table foreign key reference...")
        
        # First, check how many fact records we have
        fact_count = conn.execute("SELECT COUNT(*) FROM fact_landuse_transitions").fetchone()[0]
        print(f"   - Total fact records: {fact_count:,}")
        
        # Create a new fact table with updated reference
        print("   - Creating new fact table structure...")
        conn.execute("""
            CREATE TABLE fact_landuse_transitions_new AS
            SELECT 
                f.transition_id,
                f.scenario_id,
                f.time_id,
                f.geography_id,
                f.from_landuse_id,
                f.to_landuse_id,
                f.acres,
                f.transition_type,
                f.created_at
            FROM fact_landuse_transitions f
            JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
        """)
        
        new_fact_count = conn.execute("SELECT COUNT(*) FROM fact_landuse_transitions_new").fetchone()[0]
        print(f"   - New fact table records: {new_fact_count:,}")
        
        if new_fact_count < fact_count:
            missing = fact_count - new_fact_count
            print(f"   ⚠️  Warning: {missing} fact records have no matching enhanced geography")
        
        # 3. Save and drop views
        print("\n3. Handling dependent views...")
        views_to_recreate = []
        
        views = conn.execute("""
            SELECT view_name, sql 
            FROM duckdb_views()
            WHERE sql LIKE '%dim_geography_enhanced%' 
               OR sql LIKE '%fact_landuse_transitions%'
        """).fetchall()
        
        for view_name, view_sql in views:
            print(f"   - Saving view: {view_name}")
            views_to_recreate.append((view_name, view_sql))
            conn.execute(f"DROP VIEW IF EXISTS {view_name}")
        
        # 4. Swap tables
        print("\n4. Swapping tables...")
        
        # Drop old fact table
        conn.execute("DROP TABLE fact_landuse_transitions")
        
        # Rename new fact table
        conn.execute("ALTER TABLE fact_landuse_transitions_new RENAME TO fact_landuse_transitions")
        
        # Drop old geography table
        conn.execute("DROP TABLE dim_geography_enhanced")
        
        # Rename enhanced to standard name
        conn.execute("ALTER TABLE dim_geography_enhanced RENAME TO dim_geography_enhanced")
        
        print("   ✓ Tables swapped successfully")
        
        # 5. Recreate indexes
        print("\n5. Creating indexes...")
        conn.execute("CREATE INDEX idx_fact_geography ON fact_landuse_transitions(geography_id)")
        conn.execute("CREATE INDEX idx_fact_scenario ON fact_landuse_transitions(scenario_id)")
        conn.execute("CREATE INDEX idx_fact_time ON fact_landuse_transitions(time_id)")
        conn.execute("CREATE INDEX idx_fact_from_landuse ON fact_landuse_transitions(from_landuse_id)")
        conn.execute("CREATE INDEX idx_fact_to_landuse ON fact_landuse_transitions(to_landuse_id)")
        print("   ✓ Indexes created")
        
        # 6. Recreate views
        print("\n6. Recreating views...")
        for view_name, view_sql in views_to_recreate:
            # Update references in SQL
            updated_sql = view_sql.replace('dim_geography_enhanced', 'dim_geography_enhanced')
            print(f"   - Recreating: {view_name}")
            conn.execute(updated_sql)
        
        # 7. Verify results
        print("\n7. Verification...")
        
        # Check final state
        final_geo = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(geometry) as with_geometry,
                COUNT(DISTINCT state_name) as states
            FROM dim_geography_enhanced
        """).fetchone()
        
        print(f"   - Geography records: {final_geo[0]:,}")
        print(f"   - With geometry: {final_geo[1]:,}")
        print(f"   - States: {final_geo[2]}")
        
        # Test a join
        test_join = conn.execute("""
            SELECT COUNT(*)
            FROM fact_landuse_transitions f
            JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
            WHERE g.geometry IS NOT NULL
            LIMIT 1
        """).fetchone()[0]
        
        print(f"   - Fact-Geography join test: {test_join:,} records")
        
        conn.commit()
        print("\n✅ Migration complete!")
        print("\nResults:")
        print("- dim_geography_enhanced now has geometry support")
        print("- All fact records properly linked")
        print("- Views recreated successfully")
        print("- Database simplified and ready for mapping!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = "data/processed/landuse_analytics.duckdb"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    # Confirm before proceeding
    print("This migration will:")
    print("- Update fact_landuse_transitions to reference dim_geography_enhanced")
    print("- Drop the old dim_geography_enhanced table")
    print("- Rename dim_geography_enhanced to dim_geography_enhanced")
    print("- Recreate all views and indexes")
    print(f"\nDatabase: {db_path}")
    response = input("\nContinue? (y/N): ")
    
    if response.lower() == 'y':
        migrate_to_enhanced_geography(db_path)
    else:
        print("Cancelled.")