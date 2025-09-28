#!/usr/bin/env python3
"""
Simple wrapper script to test prompt versions.

Usage:
    # Test active prompt version
    python prompts/test_prompt.py

    # Test specific version
    python prompts/test_prompt.py --version v1.0.1

    # Test specific categories
    python prompts/test_prompt.py --category basic_queries --category edge_cases

    # Verbose output
    python prompts/test_prompt.py --verbose

    # Save results to file
    python prompts/test_prompt.py --save-results
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from prompts.tests.prompt_test_runner import main

if __name__ == "__main__":
    main()