# Rate Limit Issues - Troubleshooting Guide

## Problem
You're hitting rate limits on the second question to the agent in the Streamlit dashboard.

## Understanding Rate Limits

### 1. **API Provider Rate Limits** (Most Common)
The rate limit you're hitting is likely from your AI provider (OpenAI or Anthropic), not the application:

- **OpenAI GPT-4**: 10,000 TPM (tokens per minute) for tier 1
- **OpenAI GPT-3.5**: 60,000 TPM for tier 1  
- **Anthropic Claude**: Varies by plan (typically 100k tokens/minute for standard)

### 2. **Application Rate Limits** (Currently Not Enforced)
The application has rate limit configuration but it's not actively enforced:
```python
# In constants.py
RATE_LIMIT_CONFIG = {
    "max_calls": 60,  # per identifier
    "time_window": 60  # seconds
}
```

## Solutions

### Quick Fixes

1. **Switch to a Faster/Cheaper Model**
   ```bash
   # In config/.env
   LANDUSE_MODEL=gpt-3.5-turbo  # Higher rate limits than GPT-4
   # or
   LANDUSE_MODEL=claude-3-haiku-20240307  # Faster Anthropic model
   ```

2. **Add Retry Logic with Backoff**
   Update `pages/chat.py` to add retry logic:
   ```python
   import time
   from tenacity import retry, stop_after_attempt, wait_exponential
   
   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=4, max=10)
   )
   def query_with_retry(agent, prompt):
       return agent.query(prompt)
   ```

3. **Reduce Token Usage**
   ```bash
   # In config/.env
   MAX_TOKENS=2000  # Reduce from 4000
   TEMPERATURE=0.0  # More deterministic = potentially fewer tokens
   ```

### Long-term Solutions

1. **Implement Request Queuing**
   Add a delay between requests in the chat interface:
   ```python
   # In pages/chat.py, after getting response
   time.sleep(1)  # Add 1 second delay between queries
   ```

2. **Cache Common Queries**
   The dashboard already uses `@st.cache_data` for database queries, but you could cache agent responses for common questions.

3. **Upgrade API Tier**
   - OpenAI: Higher tiers get higher rate limits
   - Anthropic: Claude Pro has higher limits

## Checking Your Current Limits

### OpenAI
Check your tier and limits at: https://platform.openai.com/account/limits

### Anthropic
Check your plan at: https://console.anthropic.com/settings/billing

## Immediate Workaround

If you're hitting rate limits frequently:

1. **Wait 60 seconds** between questions (most rate limits reset per minute)
2. **Use the command-line agent** instead for rapid queries:
   ```bash
   uv run landuse-agent
   ```
3. **Batch your questions** into a single, comprehensive query

## Configuration Updates

To make the rate limiting more forgiving, update your `config/.env`:

```bash
# Reduce concurrent load
LANDUSE_MAX_ITERATIONS=3  # Reduce from 5
LANDUSE_MAX_EXECUTION_TIME=60  # Reduce from 120

# Use a model with higher rate limits
LANDUSE_MODEL=gpt-3.5-turbo-1106  # Or claude-3-haiku-20240307

# Reduce token usage
MAX_TOKENS=2000
TEMPERATURE=0.0
```

## Testing Rate Limits

Run this test script to check your actual rate limits:

```python
# test_rate_limits.py
import time
import os
from landuse.agents.landuse_natural_language_agent import LanduseNaturalLanguageAgent

agent = LanduseNaturalLanguageAgent()

queries = [
    "Count the scenarios",
    "Count the counties", 
    "Count the time periods",
    "Count the land use types"
]

for i, query in enumerate(queries):
    print(f"\nQuery {i+1}: {query}")
    try:
        start = time.time()
        response = agent.query(query)
        elapsed = time.time() - start
        print(f"Success in {elapsed:.2f}s")
        print(f"Response length: {len(response)} chars")
    except Exception as e:
        print(f"Error: {e}")
        if "rate" in str(e).lower():
            print("Rate limit hit! Waiting 60 seconds...")
            time.sleep(60)
```

This will help identify exactly when and how rate limits are triggered.