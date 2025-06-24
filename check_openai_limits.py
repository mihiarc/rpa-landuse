#!/usr/bin/env python3
"""
Check OpenAI rate limits and test rapid queries
"""

import os
import time
from dotenv import load_dotenv

load_dotenv("config/.env")
load_dotenv()

def test_rapid_queries():
    """Test making rapid queries to identify rate limit"""
    import sys
    from pathlib import Path
    
    # Add src to path
    project_root = Path(__file__).parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    
    from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent
    
    print("🔍 Testing OpenAI Rate Limits\n")
    print(f"Model: {os.getenv('LANDUSE_MODEL', 'gpt-4o-mini')}")
    print(f"API Key: {os.getenv('OPENAI_API_KEY', 'Not set')[:20]}...")
    
    agent = LanduseNaturalLanguageAgent()
    
    # Simple queries that should be fast
    queries = [
        "Count the scenarios",
        "Count the counties",
        "Count the time periods",
        "Count the land use types",
        "What's the earliest year?",
        "What's the latest year?"
    ]
    
    successful_queries = 0
    
    for i, query in enumerate(queries):
        print(f"\n{'='*40}")
        print(f"Query {i+1}: {query}")
        print('='*40)
        
        try:
            start = time.time()
            response = agent.query(query)
            elapsed = time.time() - start
            
            successful_queries += 1
            print(f"✅ Success in {elapsed:.2f}s")
            print(f"Response preview: {response[:100]}...")
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ Error after {successful_queries} successful queries")
            print(f"Error: {error_str}")
            
            # Check for rate limit indicators
            if any(indicator in error_str.lower() for indicator in ['rate', '429', 'limit', 'quota']):
                print("\n🚨 RATE LIMIT DETECTED!")
                print(f"Successfully completed: {successful_queries} queries")
                print(f"Failed on query: {i+1}")
                
                # Parse error for details
                if "429" in error_str:
                    print("\nHTTP 429: Too Many Requests")
                
                return successful_queries
            else:
                print("\n⚠️ Non-rate-limit error occurred")
    
    print(f"\n✅ All {successful_queries} queries completed without rate limits!")
    return successful_queries

def check_openai_tier():
    """Information about OpenAI rate limits by tier"""
    print("\n📊 OpenAI Rate Limits by Model and Tier:\n")
    
    limits = {
        "gpt-4o-mini": {
            "Tier 1": "500 RPM, 30,000 RPD, 30,000,000 TPM",
            "Tier 2": "5,000 RPM, 100,000 RPD, 150,000,000 TPM",
        },
        "gpt-4o": {
            "Tier 1": "500 RPM, 10,000 TPM, 30,000,000 TPD",
            "Tier 2": "5,000 RPM, 450,000 TPM",
        },
        "gpt-3.5-turbo": {
            "Tier 1": "3,500 RPM, 60,000 TPM, 200,000 RPD",
            "Tier 2": "3,500 RPM, 80,000 TPM",
        }
    }
    
    model = os.getenv('LANDUSE_MODEL', 'gpt-4o-mini')
    
    if model in limits:
        print(f"Model: {model}")
        for tier, limit in limits[model].items():
            print(f"  {tier}: {limit}")
        
        print(f"\n💡 With 3 API calls per query:")
        if model == "gpt-4o-mini":
            print(f"  Tier 1: ~166 queries/minute max")
            print(f"  Tier 2: ~1,666 queries/minute max")
    
    print("\nRPM = Requests Per Minute")
    print("RPD = Requests Per Day") 
    print("TPM = Tokens Per Minute")
    print("TPD = Tokens Per Day")

if __name__ == "__main__":
    check_openai_tier()
    print("\n" + "="*60 + "\n")
    
    successful = test_rapid_queries()
    
    if successful < 6:
        print(f"\n⚠️ Hit rate limit after only {successful} queries!")
        print("This suggests you may be on a lower tier or have hit token limits.")
    else:
        print("\n✅ No rate limits detected in rapid succession!")
        print("The issue might be token limits rather than request limits.")