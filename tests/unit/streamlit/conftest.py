"""
Pytest configuration for Streamlit tests
"""

import sys
import pytest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

@pytest.fixture(scope="session", autouse=True)
def mock_streamlit_module():
    """Mock streamlit module for all tests"""
    # Import mock here to avoid circular imports
    from tests.unit.streamlit.mock_streamlit import mock_st
    
    # Save original module if it exists
    original_streamlit = sys.modules.get('streamlit', None)
    
    # Set our mock
    sys.modules['streamlit'] = mock_st
    
    yield
    
    # Restore original module
    if original_streamlit:
        sys.modules['streamlit'] = original_streamlit
    else:
        sys.modules.pop('streamlit', None)