#!/usr/bin/env python3
"""
Test script to verify the agent fixes
"""

import sys
sys.path.append('src')

from landuse.agents.langgraph_map_agent import LangGraphMapAgent

def test_forest_query():
    """Test the forest query that was causing issues"""
    try:
        # Create agent
        agent = LangGraphMapAgent()
        
        # Test the problematic query
        query = "how much forestland is there in texas?"
        print(f"Testing query: {query}")
        
        # Query the agent
        result = agent.query(query)
        
        # Check the response
        if result:
            print(f"Response: {result[:500]}...")
            
            # Check if there was an error
            if "GROUP BY" in result and "ERROR" in result:
                print("❌ Still getting GROUP BY error")
                return False
            elif "Error executing query" in result:
                print("❌ SQL execution error")
                return False
            else:
                print("✅ Query completed successfully")
                return True
        else:
            print("❌ No response received")
            return False
            
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False

if __name__ == "__main__":
    success = test_forest_query()
    sys.exit(0 if success else 1)