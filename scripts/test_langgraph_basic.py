#!/usr/bin/env python3
"""
Basic test for LangGraph agents - quick validation
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.landuse.agents.landuse_natural_language_agent_v2 import LanduseNaturalLanguageAgent
from src.landuse.agents.langgraph_map_agent_v2 import LangGraphMapAgent
from src.landuse.config import LanduseConfig


def test_agent_creation():
    """Test that agents can be created"""
    print("Testing agent creation...")
    
    try:
        # Create natural language agent
        config = LanduseConfig.for_agent_type('basic', enable_memory=False)
        nl_agent = LanduseAgent(config)
        print("✅ Natural language agent created")
        
        # Create map agent
        config_map = LanduseConfig.for_agent_type('map', enable_memory=False)
        map_agent = LanduseAgent(enable_maps=True, config)
        print("✅ Map agent created")
        
        # Check key attributes
        assert hasattr(nl_agent, 'query'), "Missing query method"
        assert hasattr(nl_agent, 'chat'), "Missing chat method"
        assert hasattr(nl_agent, 'tools'), "Missing tools"
        assert hasattr(nl_agent, 'graph'), "Missing graph"
        print("✅ All required attributes present")
        
        # Check tools were created
        assert len(nl_agent.tools) >= 3, f"Expected at least 3 tools, got {len(nl_agent.tools)}"
        assert len(map_agent.tools) >= 4, f"Expected at least 4 tools for map agent, got {len(map_agent.tools)}"
        print(f"✅ Tools created - NL: {len(nl_agent.tools)}, Map: {len(map_agent.tools)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simple_query():
    """Test a very simple query"""
    print("\nTesting simple query execution...")
    
    try:
        config = LanduseConfig.for_agent_type('basic', enable_memory=False, max_iterations=3)
        agent = LanduseAgent(config)
        
        # Use a simple query that should work
        response = agent.query("How many land use types are there?")
        
        # Check response
        assert response is not None, "No response received"
        assert len(response) > 0, "Empty response"
        assert "Error" not in response or "❌" not in response, f"Error in response: {response}"
        
        print(f"✅ Query executed successfully (response length: {len(response)})")
        return True
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_compilation():
    """Test that the graph compiles correctly"""
    print("\nTesting graph compilation...")
    
    try:
        config = LanduseConfig.for_agent_type('basic', enable_memory=False)
        agent = LanduseAgent(config)
        
        # Check graph structure
        assert agent.graph is not None, "Graph not created"
        assert hasattr(agent.graph, 'invoke'), "Graph missing invoke method"
        
        # Get graph nodes
        # Note: This is implementation-specific and may need adjustment
        print("✅ Graph compiled successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Graph compilation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run basic tests"""
    print("🧪 Basic LangGraph Agent Tests")
    print("=" * 50)
    
    tests = [
        test_agent_creation,
        test_graph_compilation,
        test_simple_query
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ Test crashed: {e}")
            results.append(False)
    
    # Summary
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ Basic tests passed! The LangGraph agents are working.")
    else:
        print("\n❌ Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()