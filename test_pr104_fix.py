#!/usr/bin/env python3
"""Test script to verify PR #104 fix for Urban expansion test failure."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from landuse.agents.landuse_agent import LanduseAgent
from landuse.core.app_config import AppConfig
from landuse.config.landuse_config import LanduseConfig


def test_with_appconfig():
    """Test agent with AppConfig (modern config)."""
    print("\n=== Testing with AppConfig (modern) ===")
    try:
        config = AppConfig()
        with LanduseAgent(config) as agent:
            response = agent.query("Which states have the most urban expansion?")
            print(f"✅ AppConfig test passed")
            print(f"Response preview: {response[:200]}...")

            # Check for expected content
            has_data = any(word in response.lower() for word in ['acres', 'california', 'texas'])
            print(f"Contains expected data: {has_data}")
            return True
    except AttributeError as e:
        if "'AppConfig' object has no attribute 'debug'" in str(e):
            print(f"❌ AppConfig test failed with known issue: {e}")
            return False
        else:
            print(f"❌ AppConfig test failed with unexpected error: {e}")
            return False
    except Exception as e:
        print(f"❌ AppConfig test failed: {e}")
        return False


def test_with_legacy_config():
    """Test agent with legacy LanduseConfig."""
    print("\n=== Testing with LanduseConfig (legacy) ===")
    try:
        config = LanduseConfig()
        with LanduseAgent(config) as agent:
            response = agent.query("Which states have the most urban expansion?")
            print(f"✅ LanduseConfig test passed")
            print(f"Response preview: {response[:200]}...")

            # Check for expected content
            has_data = any(word in response.lower() for word in ['acres', 'california', 'texas'])
            print(f"Contains expected data: {has_data}")
            return True
    except Exception as e:
        print(f"❌ LanduseConfig test failed: {e}")
        return False


def test_debug_attribute_access():
    """Test that debug attribute is properly handled."""
    print("\n=== Testing debug attribute access ===")

    # Test with AppConfig
    try:
        app_config = AppConfig()
        agent = LanduseAgent(app_config)

        # Test debug attribute access (this is where the bug was)
        debug_value = agent.debug
        print(f"✅ AppConfig: agent.debug = {debug_value}")

        # Also test that config conversion worked
        assert hasattr(agent, 'config'), "Agent should have config attribute"
        assert hasattr(agent, 'app_config'), "Agent should have app_config attribute"
        print(f"✅ AppConfig: Config conversion successful")

    except Exception as e:
        print(f"❌ AppConfig debug test failed: {e}")
        return False

    # Test with LanduseConfig
    try:
        legacy_config = LanduseConfig()
        agent = LanduseAgent(legacy_config)

        # Test debug attribute access
        debug_value = agent.debug
        print(f"✅ LanduseConfig: agent.debug = {debug_value}")

        # Check that app_config is None for legacy
        assert agent.app_config is None, "Legacy config should not have app_config"
        print(f"✅ LanduseConfig: No app_config as expected")

    except Exception as e:
        print(f"❌ LanduseConfig debug test failed: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("PR #104 Fix Verification")
    print("=" * 50)

    results = []

    # Test debug attribute handling
    results.append(test_debug_attribute_access())

    # Test actual query execution
    results.append(test_with_appconfig())
    results.append(test_with_legacy_config())

    print("\n" + "=" * 50)
    print("Test Summary:")
    if all(results):
        print("✅ All tests passed! PR #104 fix is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Fix may be incomplete.")
        return 1


if __name__ == "__main__":
    sys.exit(main())