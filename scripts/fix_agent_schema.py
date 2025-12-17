#!/usr/bin/env python3
"""
Quick fix to help agent use combined scenarios by creating proper aliases.
"""

import sys

import duckdb


def fix_agent_schema():
    """Create aliases so agent uses combined scenarios."""
    try:
        conn = duckdb.connect('data/processed/landuse_analytics.duckdb')

        # Create views that alias combined tables to expected names
        # This ensures the agent uses combined scenarios by default

        print("Creating agent-friendly views...")

        # Drop existing problematic views first
        conn.execute("DROP VIEW IF EXISTS agent_scenarios")
        conn.execute("DROP VIEW IF EXISTS agent_transitions")

        # Create clean views for the agent to use
        conn.execute("""
            CREATE VIEW agent_scenarios AS
            SELECT * FROM dim_scenario_combined
        """)

        conn.execute("""
            CREATE VIEW agent_transitions AS
            SELECT * FROM fact_landuse_combined
        """)

        # Verify the views work
        result = conn.execute("SELECT COUNT(*) FROM agent_scenarios").fetchone()
        print(f"✓ agent_scenarios: {result[0]} scenarios")

        result = conn.execute("SELECT COUNT(*) FROM agent_transitions").fetchone()
        print(f"✓ agent_transitions: {result[0]} transitions")

        # Check scenarios
        result = conn.execute("SELECT scenario_name FROM agent_scenarios ORDER BY scenario_id").fetchall()
        print("Available scenarios:")
        for (name,) in result:
            print(f"  - {name}")

        conn.close()
        print("✓ Agent schema fixed")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = fix_agent_schema()
    sys.exit(0 if success else 1)
