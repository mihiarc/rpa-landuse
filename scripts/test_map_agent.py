#!/usr/bin/env python3
"""
Test script for the enhanced LangGraph map agent
"""

import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import third-party libraries after sys.path modification
from dotenv import load_dotenv  # noqa: E402

from landuse.agents.langgraph_map_agent import LandGraphConfig, LangGraphMapAgent  # noqa: E402

# Load environment
load_dotenv("config/.env")
load_dotenv()

def test_map_generation():
    """Test various map generation queries"""

    # Initialize agent
    config = LandGraphConfig(
        db_path=os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'),
        enable_memory=True,
        verbose=True
    )

    agent = LangGraphMapAgent(config)

    # Test queries
    test_queries = [
        "Show me a map of forest coverage in Texas",
        "Create a map showing urban areas by county in California",
        "Visualize agricultural land distribution across regions",
        "Map forest to urban transitions nationally",
        "Which counties in Florida have the most forest? Show me a map",
        "Compare land use between Texas and California with maps"
    ]

    print("🚀 Testing LangGraph Map Agent")
    print("=" * 60)

    for i, query in enumerate(test_queries):
        print(f"\n📝 Test {i+1}: {query}")
        print("-" * 60)

        try:
            response = agent.query(query)
            print(response)

            # Check if map was mentioned in response
            if "maps/" in response.lower() or ".png" in response.lower():
                print("✅ Map generation appears successful!")
            else:
                print("⚠️  No map path found in response")

        except Exception as e:
            print(f"❌ Error: {e}")

        print("-" * 60)
        input("Press Enter to continue to next test...")

def test_interactive():
    """Test interactive mode"""
    print("\n🎮 Starting interactive test mode...")

    config = LandGraphConfig(
        db_path=os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb'),
        enable_memory=True
    )

    agent = LangGraphMapAgent(config)
    agent.chat()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test the LangGraph map agent")
    parser.add_argument("--interactive", "-i", action="store_true",
                       help="Run in interactive mode")

    args = parser.parse_args()

    if args.interactive:
        test_interactive()
    else:
        test_map_generation()
