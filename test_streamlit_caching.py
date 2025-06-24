#!/usr/bin/env python3
"""
Test if Streamlit caching is working properly
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

def test_agent_creation():
    """Test if agent is being created multiple times"""
    from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent
    
    print("🔍 Testing Agent Creation\n")
    
    # Create agent multiple times
    agents = []
    for i in range(3):
        print(f"Creating agent instance {i+1}...")
        start = time.time()
        agent = LanduseNaturalLanguageAgent()
        elapsed = time.time() - start
        print(f"  Created in {elapsed:.2f}s")
        agents.append(agent)
        
        # Check if they're the same object
        if i > 0:
            print(f"  Same as first? {agents[i] is agents[0]}")
    
    print("\n🔍 Testing Queries on Same Agent\n")
    
    # Test multiple queries on same agent
    agent = agents[0]
    queries = ["Count scenarios", "Count counties"]
    
    for i, query in enumerate(queries):
        print(f"\nQuery {i+1}: {query}")
        start = time.time()
        try:
            response = agent.query(query)
            elapsed = time.time() - start
            print(f"✅ Success in {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"❌ Error after {elapsed:.2f}s: {e}")

def test_streamlit_scenario():
    """Simulate what happens in Streamlit"""
    print("\n🔍 Simulating Streamlit Scenario\n")
    
    # This simulates the @st.cache_resource decorator
    _cached_agent = None
    
    def get_agent():
        global _cached_agent
        if _cached_agent is None:
            print("Creating new agent (not cached)...")
            from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent
            _cached_agent = LanduseNaturalLanguageAgent()
        else:
            print("Using cached agent...")
        return _cached_agent
    
    # Simulate multiple page loads/queries
    for i in range(3):
        print(f"\n--- Page Load/Query {i+1} ---")
        agent = get_agent()
        
        query = f"Count the scenarios"
        print(f"Query: {query}")
        
        start = time.time()
        try:
            response = agent.query(query)
            elapsed = time.time() - start
            print(f"✅ Success in {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start
            print(f"❌ Error after {elapsed:.2f}s: {e}")
        
        # Small delay between "page loads"
        time.sleep(2)

def check_llm_state():
    """Check if LLM client maintains state that could cause issues"""
    from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent
    
    print("\n🔍 Checking LLM Client State\n")
    
    agent = LanduseNaturalLanguageAgent()
    
    # Check the LLM client
    print(f"Model: {agent.model_name}")
    print(f"LLM Type: {type(agent.llm)}")
    
    if hasattr(agent.llm, '_client'):
        print(f"Has _client: Yes")
        if hasattr(agent.llm._client, '_base_url'):
            print(f"Base URL: {agent.llm._client._base_url}")
    
    # Check agent executor state
    print(f"\nAgent Executor:")
    print(f"  Max iterations: {agent.agent.max_iterations}")
    print(f"  Max execution time: {agent.agent.max_execution_time}")

if __name__ == "__main__":
    test_agent_creation()
    test_streamlit_scenario()
    check_llm_state()