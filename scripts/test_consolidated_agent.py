#!/usr/bin/env python3
"""
Test the new consolidated agent to ensure it works correctly
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from landuse.agents import LanduseAgent
from landuse.models import AgentConfig
from rich.console import Console

console = Console()


def test_basic_agent():
    """Test basic agent functionality"""
    console.print("\n[bold cyan]Testing Basic Agent[/bold cyan]")
    console.print("-" * 50)
    
    try:
        # Create basic agent
        config = AgentConfig()
        agent = LanduseAgent(config=config)
        
        console.print("✅ Agent created successfully")
        
        # Test simple query
        console.print("\n📊 Testing query: 'How many land use types are there?'")
        response = agent.query("How many land use types are there?")
        
        console.print(f"\n[green]Response:[/green]\n{response[:200]}...")
        
        # Check response quality
        if response and len(response) > 10 and "error" not in response.lower():
            console.print("\n✅ Query executed successfully")
            return True
        else:
            console.print(f"\n❌ Query failed: {response}")
            return False
            
    except Exception as e:
        console.print(f"\n❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_map_agent():
    """Test map-enabled agent"""
    console.print("\n[bold cyan]Testing Map-Enabled Agent[/bold cyan]")
    console.print("-" * 50)
    
    try:
        # Create map agent
        config = AgentConfig()
        agent = LanduseAgent(config=config, enable_maps=True)
        
        console.print("✅ Map agent created successfully")
        
        # Check map tools
        tool_names = [tool.name for tool in agent.tools]
        console.print(f"\n📌 Available tools: {tool_names}")
        
        if "create_choropleth_map" in tool_names:
            console.print("✅ Map generation tool available")
            return True
        else:
            console.print("❌ Map generation tool not found")
            return False
            
    except Exception as e:
        console.print(f"\n❌ Error creating map agent: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_compatibility():
    """Test backward compatibility"""
    console.print("\n[bold cyan]Testing Backward Compatibility[/bold cyan]")
    console.print("-" * 50)
    
    try:
        # Test direct instantiation
        agent = LanduseAgent()
        console.print("✅ Direct instantiation works")
        
        # Test with parameters
        agent2 = LanduseAgent(
            model_name="gpt-4o-mini",
            temperature=0.1,
            enable_maps=False
        )
        console.print("✅ Parameter-based instantiation works")
        
        return True
        
    except Exception as e:
        console.print(f"\n❌ Compatibility error: {e}")
        return False


def main():
    """Run all tests"""
    console.print("[bold yellow]🧪 Testing Consolidated Agent[/bold yellow]")
    
    results = {
        "Basic Agent": test_basic_agent(),
        "Map Agent": test_map_agent(),
        "Compatibility": test_compatibility()
    }
    
    # Summary
    console.print("\n[bold cyan]Test Summary[/bold cyan]")
    console.print("-" * 50)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        console.print(f"{test_name}: {status}")
    
    console.print(f"\n[bold]Total: {passed}/{total} tests passed[/bold]")
    
    if passed == total:
        console.print("\n[bold green]🎉 All tests passed! The consolidated agent is working correctly.[/bold green]")
    else:
        console.print("\n[bold red]⚠️ Some tests failed. Please check the errors above.[/bold red]")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)