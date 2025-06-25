#!/usr/bin/env python3
"""
Properly rename dim_geography_enhanced to dim_geography
This handles all dependencies by recreating the database structure
"""

import duckdb
import sys
from pathlib import Path
import shutil
from datetime import datetime

def rename_geography_table(db_path: str):
    """Rename dim_geography_enhanced to dim_geography throughout the database"""
    
    print("=== RENAMING TO SIMPLER NOMENCLATURE ===\n")
    
    # Create backup
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"1. Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print("   ✓ Backup created")
    
    # Connect with write access
    conn = duckdb.connect(db_path, read_only=False)
    
    try:
        # Load spatial extension
        conn.execute("INSTALL spatial")
        conn.execute("LOAD spatial")
        
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        # 2. Save all view definitions (only user views starting with 'v_')
        print("\n2. Saving view definitions...")
        views = conn.execute("""
            SELECT view_name, sql 
            FROM duckdb_views()
            WHERE schema_name = 'main'
            AND view_name LIKE 'v_%'
        """).fetchall()
        
        view_definitions = []
        for view_name, view_sql in views:
            print(f"   - Saving: {view_name}")
            # Replace dim_geography_enhanced with dim_geography in the SQL
            updated_sql = view_sql.replace('dim_geography_enhanced', 'dim_geography')
            view_definitions.append((view_name, updated_sql))
        
        # 3. Drop all views
        print("\n3. Dropping all views...")
        for view_name, _ in view_definitions:
            print(f"   - Dropping: {view_name}")
            conn.execute(f"DROP VIEW IF EXISTS {view_name}")
        
        # 4. Drop the fact table (to remove foreign key constraint)
        print("\n4. Temporarily saving fact table data...")
        conn.execute("""
            CREATE TABLE fact_landuse_transitions_temp AS 
            SELECT * FROM fact_landuse_transitions
        """)
        fact_count = conn.execute("SELECT COUNT(*) FROM fact_landuse_transitions_temp").fetchone()[0]
        print(f"   - Saved {fact_count:,} fact records")
        
        print("   - Dropping fact table...")
        conn.execute("DROP TABLE fact_landuse_transitions")
        
        # 5. Drop indexes on dim_geography_enhanced
        print("\n5. Dropping indexes on dim_geography_enhanced...")
        indexes = conn.execute("""
            SELECT index_name
            FROM duckdb_indexes()
            WHERE table_name = 'dim_geography_enhanced'
        """).fetchall()
        
        for idx in indexes:
            print(f"   - Dropping: {idx[0]}")
            conn.execute(f"DROP INDEX IF EXISTS {idx[0]}")
        
        # 6. Drop old dim_geography if it exists
        print("\n6. Dropping old dim_geography (if exists)...")
        conn.execute("DROP TABLE IF EXISTS dim_geography")
        
        # 7. Rename dim_geography_enhanced to dim_geography
        print("\n7. Renaming dim_geography_enhanced to dim_geography...")
        conn.execute("ALTER TABLE dim_geography_enhanced RENAME TO dim_geography")
        print("   ✓ Table renamed successfully")
        
        # 8. Recreate fact table with proper structure
        print("\n8. Recreating fact table...")
        conn.execute("""
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
                FOREIGN KEY (geography_id) REFERENCES dim_geography(geography_id),
                FOREIGN KEY (from_landuse_id) REFERENCES dim_landuse(landuse_id),
                FOREIGN KEY (to_landuse_id) REFERENCES dim_landuse(landuse_id)
            )
        """)
        
        # 9. Restore fact data
        print("\n9. Restoring fact table data...")
        conn.execute("""
            INSERT INTO fact_landuse_transitions
            SELECT * FROM fact_landuse_transitions_temp
        """)
        restored_count = conn.execute("SELECT COUNT(*) FROM fact_landuse_transitions").fetchone()[0]
        print(f"   - Restored {restored_count:,} fact records")
        
        # Drop temp table
        conn.execute("DROP TABLE fact_landuse_transitions_temp")
        
        # 10. Recreate indexes
        print("\n10. Recreating indexes...")
        indexes = [
            "CREATE INDEX idx_fact_scenario ON fact_landuse_transitions(scenario_id)",
            "CREATE INDEX idx_fact_time ON fact_landuse_transitions(time_id)",
            "CREATE INDEX idx_fact_geography ON fact_landuse_transitions(geography_id)",
            "CREATE INDEX idx_fact_from_landuse ON fact_landuse_transitions(from_landuse_id)",
            "CREATE INDEX idx_fact_to_landuse ON fact_landuse_transitions(to_landuse_id)",
            "CREATE INDEX idx_fact_transition_type ON fact_landuse_transitions(transition_type)",
            "CREATE INDEX idx_geography_fips ON dim_geography(fips_code)",
            "CREATE INDEX idx_geography_state ON dim_geography(state_code)"
        ]
        
        for idx_sql in indexes:
            print(f"   - {idx_sql.split()[2]}")
            conn.execute(idx_sql)
        
        # 11. Recreate views with updated references
        print("\n11. Recreating views...")
        for view_name, view_sql in view_definitions:
            print(f"   - Recreating: {view_name}")
            conn.execute(view_sql)
        
        # 12. Verify the results
        print("\n12. Verification...")
        
        # Check tables
        tables = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """).fetchall()
        
        print("\n   Tables in database:")
        for t in tables:
            print(f"   - {t[0]}")
        
        # Check dim_geography
        geo_stats = conn.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(geometry) as with_geometry,
                COUNT(DISTINCT state_name) as states
            FROM dim_geography
        """).fetchone()
        
        print(f"\n   dim_geography statistics:")
        print(f"   - Total records: {geo_stats[0]:,}")
        print(f"   - With geometry: {geo_stats[1]:,}")
        print(f"   - States: {geo_stats[2]}")
        
        # Test a join
        join_test = conn.execute("""
            SELECT COUNT(*)
            FROM fact_landuse_transitions f
            JOIN dim_geography g ON f.geography_id = g.geography_id
            WHERE g.geometry IS NOT NULL
            LIMIT 1
        """).fetchone()[0]
        
        print(f"\n   Fact-Geography join test: {join_test:,} records")
        
        # Commit the transaction
        conn.execute("COMMIT")
        print("\n✅ Database successfully updated to use simpler nomenclature!")
        
        # Now update all the code
        print("\n13. Updating code references...")
        print("   Run: python scripts/update_code_simple.py")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Rolling back changes...")
        try:
            conn.execute("ROLLBACK")
        except:
            pass
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    db_path = "data/processed/landuse_analytics.duckdb"
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    print("This will rename dim_geography_enhanced to dim_geography throughout the database")
    print("A backup will be created first")
    print(f"\nDatabase: {db_path}")
    response = input("\nContinue? (y/N): ")
    
    if response.lower() == 'y':
        rename_geography_table(db_path)
    else:
        print("Cancelled.")