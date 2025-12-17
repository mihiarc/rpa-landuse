"""
Pytest configuration for Streamlit tests
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

# Import third-party libraries after sys.path modification
import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def mock_streamlit_module():
    """Mock streamlit module for all tests"""
    # Import mock here to avoid circular imports
    from tests.unit.streamlit_tests.mock_streamlit import mock_st

    # Save original module if it exists
    original_streamlit = sys.modules.get("streamlit", None)

    # Set our mock
    sys.modules["streamlit"] = mock_st

    yield

    # Restore original module
    if original_streamlit:
        sys.modules["streamlit"] = original_streamlit
    else:
        sys.modules.pop("streamlit", None)
