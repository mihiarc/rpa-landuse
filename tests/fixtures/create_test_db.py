#!/usr/bin/env python3
"""Create test database fixture"""

import duckdb

# Create test database with minimal schema
conn = duckdb.connect('test_landuse.duckdb')

# Create dimension tables
conn.execute("""
    CREATE TABLE dim_scenario (
        scenario_id INTEGER PRIMARY KEY,
        scenario_name VARCHAR
    )
""")

conn.execute("""
    CREATE TABLE dim_time (
        time_id INTEGER PRIMARY KEY,
        year_range VARCHAR
    )
""")

conn.execute("""
    CREATE TABLE dim_geography (
        geography_id INTEGER PRIMARY KEY,
        fips_code VARCHAR,
        state_code VARCHAR
    )
""")

conn.execute("""
    CREATE TABLE dim_landuse (
        landuse_id INTEGER PRIMARY KEY,
        landuse_code VARCHAR,
        landuse_name VARCHAR
    )
""")

conn.execute("""
    CREATE TABLE fact_landuse_transitions (
        transition_id BIGINT PRIMARY KEY,
        scenario_id INTEGER,
        time_id INTEGER,
        geography_id INTEGER,
        from_landuse_id INTEGER,
        to_landuse_id INTEGER,
        acres DECIMAL,
        transition_type VARCHAR
    )
""")

# Insert minimal test data
conn.execute("INSERT INTO dim_scenario VALUES (1, 'test_scenario')")
conn.execute("INSERT INTO dim_time VALUES (1, '2020-2030')")
conn.execute("INSERT INTO dim_geography VALUES (1, '00001', 'XX')")
conn.execute("INSERT INTO dim_landuse VALUES (1, 'cr', 'Crop')")
conn.execute("INSERT INTO fact_landuse_transitions VALUES (1, 1, 1, 1, 1, 1, 100.0, 'same')")

conn.close()
print("Created test_landuse.duckdb")