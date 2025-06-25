#!/usr/bin/env python3
"""
Simplify database nomenclature by renaming dim_geography_enhanced to dim_geography_enhanced
and updating all references.
"""

import sys
from pathlib import Path

import duckdb


def simplify_geography_table(db_path: str):
    """Rename dim_geography_enhanced to dim_geography_enhanced"""

    print("=== SIMPLIFYING GEOGRAPHY TABLE NOMENCLATURE ===\n")

    # Connect with write access
    conn = duckdb.connect(db_path, read_only=False)

    try:
        # Load spatial extension
        conn.execute("INSTALL spatial")
        conn.execute("LOAD spatial")

        # 1. Check current state
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

        # 2. Check if dim_geography_enhanced exists
        has_old_geography = any(t[0] == 'dim_geography_enhanced' for t in tables)
        has_enhanced = any(t[0] == 'dim_geography_enhanced' for t in tables)

        if not has_enhanced:
            print("\n✓ Database already simplified - dim_geography_enhanced not found")
            return

        if has_old_geography:
            print("\n2. Backing up original dim_geography_enhanced...")
            # Rename old table to backup
            conn.execute("ALTER TABLE dim_geography_enhanced RENAME TO dim_geography_original")
            print("   ✓ Renamed dim_geography_enhanced to dim_geography_original")

        # 3. Rename enhanced table
        print("\n3. Renaming dim_geography_enhanced to dim_geography_enhanced...")
        conn.execute("ALTER TABLE dim_geography_enhanced RENAME TO dim_geography_enhanced")
        print("   ✓ Renamed successfully")

        # 4. Update views if any
        print("\n4. Checking for views that need updating...")
        views = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_type = 'VIEW'
            AND table_schema = 'main'
        """).fetchall()

        for view in views:
            view_name = view[0]
            # Get view definition
            view_def = conn.execute(f"SELECT sql FROM duckdb_views() WHERE view_name = '{view_name}'").fetchone()
            if view_def and 'dim_geography_enhanced' in view_def[0]:
                print(f"   - Updating view: {view_name}")
                # Would need to recreate the view with updated reference
                # For now, just note it needs updating
                print(f"     ⚠️  View {view_name} may need manual update")

        # 5. Verify the change
        print("\n5. Verifying changes...")
        new_tables = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
            AND table_name LIKE '%geography%'
            ORDER BY table_name
        """).fetchall()

        print("   Updated geography tables:")
        for t in new_tables:
            print(f"   - {t[0]}")

        # Check the new dim_geography_enhanced has all columns
        cols = conn.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'dim_geography_enhanced'
            ORDER BY ordinal_position
        """).fetchall()

        print("\n   dim_geography_enhanced columns:")
        for c in cols:
            print(f"   - {c[0]}: {c[1]}")

        # Verify geometry data
        geo_check = conn.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(geometry) as with_geometry
            FROM dim_geography_enhanced
        """).fetchone()

        print(f"\n   Total records: {geo_check[0]:,}")
        print(f"   With geometry: {geo_check[1]:,}")

        conn.commit()
        print("\n✅ Database simplification complete!")

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
    print(f"This will rename dim_geography_enhanced to dim_geography_enhanced in: {db_path}")
    response = input("Continue? (y/N): ")

    if response.lower() == 'y':
        simplify_geography_table(db_path)
    else:
        print("Cancelled.")
