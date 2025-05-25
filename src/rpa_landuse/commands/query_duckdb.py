#!/usr/bin/env python3
"""
Database query tool for the RPA Land Use Viewer.

This script provides a command-line interface for querying
the RPA Land Use database using common query patterns.
"""

import sys
import argparse
import duckdb
import pandas as pd
from pathlib import Path

# Default database path
DB_PATH = "data/database/rpa.db"


def get_connection(db_path=DB_PATH):
    """Get a DuckDB connection."""
    try:
        conn = duckdb.connect(db_path)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)


def execute_query(conn, query, params=None):
    """Execute a query and return the results as a DataFrame."""
    try:
        if params:
            return conn.execute(query, params).fetchdf()
        else:
            return conn.execute(query).fetchdf()
    except Exception as e:
        print(f"Error executing query: {e}")
        print(f"Query: {query}")
        if params:
            print(f"Parameters: {params}")
        return pd.DataFrame()


def list_tables(conn):
    """List all tables in the database."""
    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'main'
    """
    return execute_query(conn, query)


def describe_table(conn, table_name):
    """Describe the structure of a table."""
    query = f"""
    PRAGMA table_info('{table_name}')
    """
    return execute_query(conn, query)


def get_scenarios(conn):
    """Get all available scenarios."""
    query = """
    SELECT 
        scenario_id,
        scenario_name,
        gcm,
        rcp,
        ssp
    FROM 
        scenarios
    ORDER BY 
        scenario_name
    """
    return execute_query(conn, query)


def get_time_steps(conn):
    """Get all available time steps."""
    query = """
    SELECT 
        decade_id as time_step_id,
        start_year,
        end_year
    FROM 
        decades
    ORDER BY 
        start_year
    """
    return execute_query(conn, query)


def get_land_use_types(conn):
    """Get all land use types."""
    query = """
    SELECT DISTINCT from_landuse as land_use_type FROM landuse_change
    UNION
    SELECT DISTINCT to_landuse as land_use_type FROM landuse_change
    ORDER BY land_use_type
    """
    return execute_query(conn, query)


def get_counties(conn, state=None):
    """Get all counties, optionally filtered by state."""
    query = """
    SELECT 
        fips_code,
        county_name,
        state_name
    FROM 
        counties
    """
    if state:
        query += " WHERE state_name = ?"
        return execute_query(conn, query, [state])
    
    query += " ORDER BY state_name, county_name"
    return execute_query(conn, query)


def get_transitions(conn, scenario_id, time_step_id, fips_code=None, 
                   from_land_use=None, to_land_use=None, limit=20):
    """
    Get land use transitions with filtering options.
    """
    query = """
    SELECT 
        c.county_name,
        c.state_name,
        t.from_landuse,
        t.to_landuse,
        t.area_hundreds_acres * 100 as acres_changed
    FROM 
        landuse_change t
    JOIN
        counties c ON t.fips_code = c.fips_code
    WHERE 
        t.scenario_id = ?
        AND t.decade_id = ?
    """
    
    params = [scenario_id, time_step_id]
    
    if fips_code:
        query += " AND t.fips_code = ?"
        params.append(fips_code)
        
    if from_land_use:
        query += " AND t.from_landuse = ?"
        params.append(from_land_use)
        
    if to_land_use:
        query += " AND t.to_landuse = ?"
        params.append(to_land_use)
        
    query += """
    ORDER BY 
        acres_changed DESC
    LIMIT ?
    """
    params.append(limit)
    
    return execute_query(conn, query, params)


def run_custom_query(conn, query, params=None):
    """Run a custom SQL query."""
    return execute_query(conn, query, params)


def interactive_mode(conn):
    """Run in interactive SQL query mode."""
    print("\n--- Interactive DuckDB Query Mode ---")
    print("Enter SQL queries (type 'exit' to quit).")
    print("Available tables: " + ", ".join(list_tables(conn)['table_name'].tolist()))
    
    while True:
        try:
            query = input("\nSQL> ")
            if query.lower() in ('exit', 'quit'):
                break
                
            if not query.strip():
                continue
                
            result = execute_query(conn, query)
            if not result.empty:
                print("\nResults:")
                print(result.to_string())
                print(f"\n[{len(result)} rows returned]")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    """Run the DuckDB query tool."""
    parser = argparse.ArgumentParser(description="RPA Land Use Database Query Tool")
    parser.add_argument('--db', default=DB_PATH, help='Path to DuckDB database file')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List tables command
    subparsers.add_parser('tables', help='List all tables in the database')
    
    # Describe table command
    describe_parser = subparsers.add_parser('describe', help='Describe a table structure')
    describe_parser.add_argument('table', help='Table name to describe')
    
    # List scenarios command
    subparsers.add_parser('scenarios', help='List all scenarios')
    
    # List time steps command
    subparsers.add_parser('timesteps', help='List all time steps')
    
    # List land use types command
    subparsers.add_parser('landuse', help='List all land use types')
    
    # List counties command
    counties_parser = subparsers.add_parser('counties', help='List counties')
    counties_parser.add_argument('--state', help='Filter by state name')
    
    # Get transitions command
    transitions_parser = subparsers.add_parser('transitions', 
                                            help='Get land use transitions')
    transitions_parser.add_argument('--scenario', type=int, required=True,
                                  help='Scenario ID')
    transitions_parser.add_argument('--timestep', type=int, required=True,
                                  help='Time step ID')
    transitions_parser.add_argument('--county', help='County FIPS code')
    transitions_parser.add_argument('--from', dest='from_land_use', 
                                  help='Source land use type')
    transitions_parser.add_argument('--to', dest='to_land_use',
                                  help='Target land use type')
    transitions_parser.add_argument('--limit', type=int, default=20,
                                  help='Maximum number of results')
    
    # Interactive mode command
    subparsers.add_parser('interactive', help='Enter interactive query mode')
    
    # SQL query command
    sql_parser = subparsers.add_parser('sql', help='Run a SQL query')
    sql_parser.add_argument('query', help='SQL query to execute')
    
    args = parser.parse_args()
    
    conn = get_connection(args.db)
    
    if args.command == 'tables':
        df = list_tables(conn)
        print(df.to_string(index=False))
        
    elif args.command == 'describe':
        df = describe_table(conn, args.table)
        print(df.to_string(index=False))
        
    elif args.command == 'scenarios':
        df = get_scenarios(conn)
        print(df.to_string(index=False))
        
    elif args.command == 'timesteps':
        df = get_time_steps(conn)
        print(df.to_string(index=False))
        
    elif args.command == 'landuse':
        df = get_land_use_types(conn)
        print(df.to_string(index=False))
        
    elif args.command == 'counties':
        df = get_counties(conn, args.state)
        print(df.to_string(index=False))
        
    elif args.command == 'transitions':
        df = get_transitions(conn, args.scenario, args.timestep, args.county,
                          args.from_land_use, args.to_land_use, args.limit)
        print(df.to_string(index=False))
        
    elif args.command == 'interactive':
        interactive_mode(conn)
        
    elif args.command == 'sql':
        df = run_custom_query(conn, args.query)
        print(df.to_string(index=False))
        
    else:
        parser.print_help()
    
    conn.close()


if __name__ == "__main__":
    main() 