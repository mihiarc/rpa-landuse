#!/usr/bin/env python3
"""
Simple direct rename of dim_geography_enhanced to dim_geography_enhanced
"""

import sys
from pathlib import Path

import duckdb


def simple_rename(db_path: str):
    """Simple rename without complex dependency handling"""

    print("=== SIMPLE GEOGRAPHY TABLE RENAME ===\n")

    # Connect with write access
    conn = duckdb.connect(db_path, read_only=False)

    try:
        # Load spatial extension
        conn.execute("INSTALL spatial")
        conn.execute("LOAD spatial")

        # Check current state
        print("1. Checking current tables...")
        tables = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            AND table_name LIKE '%geography%'
            ORDER BY table_name
        """).fetchall()

        print("   Current geography tables:")
        for t in tables:
            print(f"   - {t[0]}")

        if any('dim_geography_enhanced' in t[0] for t in tables):
            print("\n2. Found dim_geography_enhanced, proceeding with rename...")

            # Drop the old dim_geography_enhanced if it exists
            print("\n3. Dropping old dim_geography_enhanced (if exists)...")
            conn.execute("DROP TABLE IF EXISTS dim_geography_enhanced CASCADE")
            print("   ✓ Dropped")

            # Simple rename
            print("\n4. Renaming dim_geography_enhanced to dim_geography_enhanced...")
            conn.execute("ALTER TABLE dim_geography_enhanced RENAME TO dim_geography_enhanced")
            print("   ✓ Renamed successfully")

            # Verify
            print("\n5. Verifying...")
            tables_after = conn.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'main'
                AND table_name LIKE '%geography%'
                ORDER BY table_name
            """).fetchall()

            print("   Geography tables after rename:")
            for t in tables_after:
                print(f"   - {t[0]}")

            # Check if we can query it
            count = conn.execute("SELECT COUNT(*) FROM dim_geography_enhanced").fetchone()[0]
            print(f"\n   ✓ Successfully queried dim_geography_enhanced: {count:,} records")

            # Test join with fact table
            print("\n6. Testing fact table join...")
            join_count = conn.execute("""
                SELECT COUNT(*)
                FROM fact_landuse_transitions f
                JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
                LIMIT 1
            """).fetchone()[0]
            print(f"   ✓ Join successful: {join_count:,} records")

            conn.commit()
            print("\n✅ Rename completed successfully!")

        else:
            print("\n✓ dim_geography_enhanced already exists, no rename needed")

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

    simple_rename(db_path)
