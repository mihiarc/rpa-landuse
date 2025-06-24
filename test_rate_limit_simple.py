#!/usr/bin/env python3
"""
Simple test to reproduce the rate limit issue
"""

import os
import sys
import time
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv
load_dotenv("config/.env")
load_dotenv()

from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent

def test_two_queries():
    """Test exactly what happens with two queries in succession"""
    print("🔍 Testing Two Queries in Succession\n")
    print(f"Model: {os.getenv('LANDUSE_MODEL', 'gpt-4o-mini')}")
    
    # Create agent once
    print("Creating agent...")
    agent = LanduseNaturalLanguageAgent()
    print("Agent created successfully\n")
    
    queries = [
        "How many scenarios are in the database?",
        "How many counties are in the database?"
    ]
    
    for i, query in enumerate(queries):
        print(f"{'='*60}")
        print(f"Query {i+1}: {query}")
        print('='*60)
        
        start = time.time()
        try:
            response = agent.query(query)
            elapsed = time.time() - start
            
            print(f"✅ Success in {elapsed:.2f}s")
            print(f"Response preview: {response[:150]}...")
            
            # Log the agent state
            if hasattr(agent.agent, 'iterations'):
                print(f"Agent iterations used: {agent.agent.iterations}")
            
        except Exception as e:
            elapsed = time.time() - start
            print(f"❌ Error after {elapsed:.2f}s")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            
            # Check for rate limit
            error_str = str(e).lower()
            if any(x in error_str for x in ['rate', '429', 'limit', 'quota', 'exceeded']):
                print("\n🚨 RATE LIMIT ERROR DETECTED!")
                
                # Try to extract more info
                if hasattr(e, 'response'):
                    print(f"Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
                    print(f"Response headers: {e.response.headers if hasattr(e.response, 'headers') else 'N/A'}")
            
            return False
        
        print(f"\nWaiting 1 second before next query...")
        time.sleep(1)
    
    print("\n✅ Both queries completed successfully!")
    return True

def test_with_delays():
    """Test with different delays between queries"""
    print("\n🔍 Testing Different Delays\n")
    
    delays = [0, 1, 2, 5]
    
    for delay in delays:
        print(f"\nTesting with {delay}s delay...")
        
        agent = LanduseNaturalLanguageAgent()
        success = True
        
        for i in range(3):
            try:
                response = agent.query("Count the scenarios")
                print(f"  Query {i+1}: ✅")
                if i < 2:
                    time.sleep(delay)
            except Exception as e:
                print(f"  Query {i+1}: ❌ {type(e).__name__}")
                success = False
                break
        
        if success:
            print(f"  Result: All queries succeeded with {delay}s delay")
        else:
            print(f"  Result: Failed with {delay}s delay")

if __name__ == "__main__":
    # First test: Two queries as you described
    success = test_two_queries()
    
    # Second test: Try different delays
    if not success:
        test_with_delays()