#!/usr/bin/env python3
"""
Debug why "how many counties does texas have?" fails
"""

import os
import sys
from pathlib import Path

# Setup
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv
load_dotenv("config/.env")
load_dotenv()

from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent

# Create agent
agent = LanduseNaturalLanguageAgent()
# Enable verbose mode on the agent executor
agent.agent.verbose = True

print("🔍 Testing Texas Counties Query\n")
print("Query: 'How many counties does Texas have?'\n")
print("="*60)

try:
    response = agent.query("How many counties does Texas have?")
    print("\n✅ Success!")
    print(f"Response: {response}")
except Exception as e:
    print(f"\n❌ Error: {e}")

# Now let's test a working query to see the difference
print("\n\n🔍 Testing a simpler direct query\n")
print("Query: 'SELECT COUNT(*) FROM dim_geography WHERE state_code = \"48\"'\n")
print("="*60)

# Direct database query
import duckdb
db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
conn = duckdb.connect(str(db_path), read_only=True)

try:
    result = conn.execute("SELECT COUNT(*) as county_count FROM dim_geography WHERE state_code = '48'")
    print(f"Direct query result: {result.fetchone()}")
    
    # Also check what state_code Texas has
    result2 = conn.execute("SELECT DISTINCT state_code, state_name FROM dim_geography WHERE state_name LIKE '%Texas%' OR state_code = '48' LIMIT 5")
    print(f"\nTexas state info: {result2.fetchall()}")
    
except Exception as e:
    print(f"Database error: {e}")
finally:
    conn.close()

# Test with a more specific prompt
print("\n\n🔍 Testing more specific query\n")
print("Query: 'Count the counties in state_code 48 (Texas)'\n")
print("="*60)

try:
    response = agent.query("Count the counties in state_code 48 (Texas)")
    print(f"\n✅ Success!")
    print(f"Response: {response[:200]}...")
except Exception as e:
    print(f"\n❌ Error: {e}")