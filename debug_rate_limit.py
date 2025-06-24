#!/usr/bin/env python3
"""
Debug script to trace rate limit issues
"""

import os
import sys
import time
import logging
from pathlib import Path

# Setup verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src to path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from dotenv import load_dotenv
load_dotenv("config/.env")
load_dotenv()

# Import after setting up environment
from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent
from langchain.callbacks.base import BaseCallbackHandler

class DebugCallbackHandler(BaseCallbackHandler):
    """Callback handler to trace all LLM and tool calls"""
    
    def __init__(self):
        self.llm_calls = 0
        self.tool_calls = 0
        self.tokens_used = 0
        self.start_time = time.time()
    
    def on_llm_start(self, serialized, prompts, **kwargs):
        self.llm_calls += 1
        print(f"\n🔵 LLM Call #{self.llm_calls} at {time.time() - self.start_time:.2f}s")
        print(f"   Prompt length: {len(str(prompts))} chars")
    
    def on_llm_end(self, response, **kwargs):
        # Try to extract token usage
        if hasattr(response, 'llm_output') and response.llm_output:
            if 'token_usage' in response.llm_output:
                usage = response.llm_output['token_usage']
                self.tokens_used += usage.get('total_tokens', 0)
                print(f"   Tokens used: {usage}")
    
    def on_tool_start(self, serialized, input_str, **kwargs):
        self.tool_calls += 1
        tool_name = serialized.get('name', 'Unknown')
        print(f"\n🔧 Tool Call #{self.tool_calls}: {tool_name} at {time.time() - self.start_time:.2f}s")
        print(f"   Input preview: {str(input_str)[:100]}...")
    
    def on_tool_end(self, output, **kwargs):
        print(f"   Output length: {len(str(output))} chars")
    
    def get_summary(self):
        elapsed = time.time() - self.start_time
        return f"""
📊 Summary:
- Total time: {elapsed:.2f}s
- LLM calls: {self.llm_calls}
- Tool calls: {self.tool_calls}
- Total tokens: {self.tokens_used}
- Avg time between LLM calls: {elapsed/self.llm_calls if self.llm_calls > 0 else 0:.2f}s
"""

def test_queries_with_debug():
    """Test queries with detailed debugging"""
    print("🔍 Initializing agent with debug callbacks...")
    
    # Create agent
    agent = LanduseNaturalLanguageAgent()
    
    # Test queries
    queries = [
        "How many scenarios are in the database?",
        "What is the total agricultural land loss?"
    ]
    
    for i, query in enumerate(queries):
        print(f"\n{'='*60}")
        print(f"📝 Query {i+1}: {query}")
        print(f"{'='*60}")
        
        # Create debug handler for this query
        debug_handler = DebugCallbackHandler()
        
        # Patch the agent's callbacks
        original_callbacks = agent.agent.callbacks
        agent.agent.callbacks = [debug_handler]
        
        try:
            start = time.time()
            response = agent.query(query)
            elapsed = time.time() - start
            
            print(f"\n✅ Success in {elapsed:.2f}s")
            print(f"Response preview: {response[:200]}...")
            print(debug_handler.get_summary())
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print(f"Error type: {type(e).__name__}")
            print(debug_handler.get_summary())
            
            # Check if rate limit error
            if "rate" in str(e).lower() or "429" in str(e):
                print("\n⚠️ RATE LIMIT DETECTED!")
                print("Waiting 60 seconds before continuing...")
                time.sleep(60)
        
        finally:
            # Restore original callbacks
            agent.agent.callbacks = original_callbacks
        
        # Small delay between queries
        print(f"\n⏱️ Waiting 2 seconds before next query...")
        time.sleep(2)

def check_environment():
    """Check environment configuration"""
    print("🌍 Environment Configuration:")
    print(f"- Model: {os.getenv('LANDUSE_MODEL', 'gpt-4o-mini')}")
    print(f"- Max Iterations: {os.getenv('LANDUSE_MAX_ITERATIONS', '5')}")
    print(f"- Max Execution Time: {os.getenv('LANDUSE_MAX_EXECUTION_TIME', '120')}s")
    print(f"- Max Tokens: {os.getenv('MAX_TOKENS', '4000')}")
    print(f"- Temperature: {os.getenv('TEMPERATURE', '0.1')}")
    print(f"- Rate Limit Calls: {os.getenv('LANDUSE_RATE_LIMIT_CALLS', '60')}")
    print(f"- Rate Limit Window: {os.getenv('LANDUSE_RATE_LIMIT_WINDOW', '60')}s")
    
    # Check API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    if openai_key:
        print(f"- OpenAI API Key: {openai_key[:8]}...{openai_key[-4:]}")
    if anthropic_key:
        print(f"- Anthropic API Key: {anthropic_key[:8]}...{anthropic_key[-4:]}")

if __name__ == "__main__":
    print("🐛 Landuse Agent Rate Limit Debugger\n")
    
    check_environment()
    print("\n" + "="*60 + "\n")
    
    test_queries_with_debug()