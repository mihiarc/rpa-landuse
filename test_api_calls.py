#!/usr/bin/env python3
"""
Test to count API calls per query
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv
load_dotenv("config/.env")
load_dotenv()

class APICallCounter:
    def __init__(self):
        self.calls = 0
        self.original_create = None
    
    def counting_create(self, *args, **kwargs):
        self.calls += 1
        print(f"🔵 API Call #{self.calls}")
        return self.original_create(*args, **kwargs)

def count_api_calls_per_query():
    """Count how many API calls each query makes"""
    from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent
    
    print("Initializing agent...")
    agent = LanduseNaturalLanguageAgent()
    
    # Simple queries that should require different numbers of tool calls
    queries = [
        ("Simple count", "How many scenarios are in the database?"),
        ("Complex aggregation", "What is the total agricultural land loss?"),
        ("Multi-step analysis", "Compare forest loss between RCP45 and RCP85 scenarios")
    ]
    
    for query_type, query in queries:
        print(f"\n{'='*60}")
        print(f"Query Type: {query_type}")
        print(f"Query: {query}")
        print('='*60)
        
        # Patch the API call
        counter = APICallCounter()
        
        # Find the actual method to patch based on the model
        if agent.model_name.startswith("claude"):
            # Anthropic client
            counter.original_create = agent.llm._client.messages.create
            agent.llm._client.messages.create = counter.counting_create
        else:
            # OpenAI client
            counter.original_create = agent.llm.client.chat.completions.create
            agent.llm.client.chat.completions.create = counter.counting_create
        
        try:
            response = agent.query(query)
            print(f"\n✅ Success!")
            print(f"Total API calls: {counter.calls}")
            print(f"Response length: {len(response)} chars")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print(f"API calls before error: {counter.calls}")
        finally:
            # Restore original method
            if agent.model_name.startswith("claude"):
                agent.llm._client.messages.create = counter.original_create
            else:
                agent.llm.client.chat.completions.create = counter.original_create

def analyze_rate_limits():
    """Analyze rate limit implications"""
    print("\n" + "="*60)
    print("📊 Rate Limit Analysis")
    print("="*60)
    
    model = os.getenv('LANDUSE_MODEL', 'gpt-4o-mini')
    
    if model.startswith("claude"):
        print("\n🤖 Anthropic Claude Rate Limits:")
        print("- Requests: 50 per minute")
        print("- If each query uses 3 API calls:")
        print("  - Max queries per minute: 16")
        print("  - Time between queries needed: 3.75 seconds")
        print("- If each query uses 5 API calls:")
        print("  - Max queries per minute: 10") 
        print("  - Time between queries needed: 6 seconds")
    else:
        print("\n🤖 OpenAI GPT Rate Limits:")
        print("- Varies by model and tier")
        print("- GPT-4: Typically 500 RPM for tier 1")
        print("- GPT-3.5: Typically 3,500 RPM for tier 1")
    
    max_iterations = int(os.getenv('LANDUSE_MAX_ITERATIONS', '5'))
    print(f"\n⚙️ Current Settings:")
    print(f"- Max iterations (tool calls): {max_iterations}")
    print(f"- Worst case API calls per query: {max_iterations + 1}")
    
    print("\n💡 Recommendations:")
    print("1. Add delay between queries in chat interface")
    print("2. Reduce LANDUSE_MAX_ITERATIONS to 3")
    print("3. Switch to a model with higher rate limits")
    print("4. Implement query result caching")

if __name__ == "__main__":
    print("🔍 API Call Counter for Landuse Agent\n")
    
    count_api_calls_per_query()
    analyze_rate_limits()