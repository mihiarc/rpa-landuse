"""
Pytest configuration and shared fixtures
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import duckdb
import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts"))


def is_valid_duckdb(path: str) -> bool:
    """Check if file is a valid DuckDB database (not an LFS pointer)."""
    try:
        conn = duckdb.connect(path, read_only=True)
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return True
    except Exception:
        return False


# Determine test database path - use fixture if valid, otherwise skip
_fixture_db_path = "tests/fixtures/test_landuse.duckdb"
_fixture_valid = Path(_fixture_db_path).exists() and is_valid_duckdb(_fixture_db_path)

# Test environment variables
TEST_ENV = {
    "OPENAI_API_KEY": "sk-test1234567890123456789012345678901234567890123456",
    "LANDUSE_MODEL": "gpt-4o-mini",
    "TEMPERATURE": "0.1",
    "MAX_TOKENS": "1000",
    "DEFAULT_QUERY_LIMIT": "100",
    "LOG_LEVEL": "DEBUG",
    "LANDUSE_DB_PATH": _fixture_db_path if _fixture_valid else "",
}


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Set up test environment variables"""
    for key, value in TEST_ENV.items():
        monkeypatch.setenv(key, value)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_db_path(temp_dir):
    """Create a test database path"""
    return temp_dir / "test_landuse.duckdb"


@pytest.fixture
def test_database(test_db_path):
    """Create a test DuckDB database with sample schema"""
    conn = duckdb.connect(str(test_db_path))

    # Create dimension tables
    conn.execute("""
        CREATE TABLE dim_scenario (
            scenario_id INTEGER PRIMARY KEY,
            scenario_name VARCHAR(100) NOT NULL,
            climate_model VARCHAR(50),
            rcp_scenario VARCHAR(20),
            ssp_scenario VARCHAR(20)
        )
    """)

    conn.execute("""
        CREATE TABLE dim_time (
            time_id INTEGER PRIMARY KEY,
            year_range VARCHAR(20) NOT NULL,
            start_year INTEGER,
            end_year INTEGER,
            period_length INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE dim_geography (
            geography_id INTEGER PRIMARY KEY,
            fips_code VARCHAR(10) NOT NULL UNIQUE,
            state_code VARCHAR(2)
        )
    """)

    conn.execute("""
        CREATE TABLE dim_landuse (
            landuse_id INTEGER PRIMARY KEY,
            landuse_code VARCHAR(10) NOT NULL UNIQUE,
            landuse_name VARCHAR(50) NOT NULL,
            landuse_category VARCHAR(30)
        )
    """)

    conn.execute("""
        CREATE TABLE fact_landuse_transitions (
            transition_id BIGINT PRIMARY KEY,
            scenario_id INTEGER NOT NULL,
            time_id INTEGER NOT NULL,
            geography_id INTEGER NOT NULL,
            from_landuse_id INTEGER NOT NULL,
            to_landuse_id INTEGER NOT NULL,
            acres DECIMAL(15,4) NOT NULL,
            transition_type VARCHAR(20) NOT NULL,
            FOREIGN KEY (scenario_id) REFERENCES dim_scenario(scenario_id),
            FOREIGN KEY (time_id) REFERENCES dim_time(time_id),
            FOREIGN KEY (geography_id) REFERENCES dim_geography(geography_id),
            FOREIGN KEY (from_landuse_id) REFERENCES dim_landuse(landuse_id),
            FOREIGN KEY (to_landuse_id) REFERENCES dim_landuse(landuse_id)
        )
    """)

    # Insert sample data
    conn.execute("""
        INSERT INTO dim_scenario VALUES
        (1, 'CNRM_CM5_rcp45_ssp1', 'CNRM_CM5', 'rcp45', 'ssp1'),
        (2, 'CNRM_CM5_rcp85_ssp5', 'CNRM_CM5', 'rcp85', 'ssp5')
    """)

    conn.execute("""
        INSERT INTO dim_time VALUES
        (1, '2012-2020', 2012, 2020, 8),
        (2, '2020-2030', 2020, 2030, 10)
    """)

    conn.execute("""
        INSERT INTO dim_geography VALUES
        (1, '01001', 'AL'),
        (2, '06001', 'CA')
    """)

    conn.execute("""
        INSERT INTO dim_landuse VALUES
        (1, 'cr', 'Crop', 'Agriculture'),
        (2, 'ps', 'Pasture', 'Agriculture'),
        (3, 'fr', 'Forest', 'Natural'),
        (4, 'ur', 'Urban', 'Developed')
    """)

    conn.execute("""
        INSERT INTO fact_landuse_transitions VALUES
        (1, 1, 1, 1, 1, 4, 1000.5, 'change'),
        (2, 1, 1, 1, 3, 4, 500.25, 'change'),
        (3, 2, 2, 2, 2, 4, 2000.75, 'change')
    """)

    conn.close()

    yield test_db_path

    # Cleanup is handled by temp_dir fixture


@pytest.fixture
def mock_llm():
    """Mock LLM for testing agents"""
    mock = Mock()
    mock.invoke.return_value = Mock(content="SELECT * FROM dim_scenario LIMIT 10")
    return mock


@pytest.fixture
def test_config_file(temp_dir):
    """Create a test .env file"""
    env_file = temp_dir / ".env"
    env_file.write_text("""
OPENAI_API_KEY=sk-test1234567890123456789012345678901234567890123456
LANDUSE_MODEL=gpt-4o-mini
TEMPERATURE=0.1
MAX_TOKENS=1000
DEFAULT_QUERY_LIMIT=100
LOG_LEVEL=DEBUG
""")
    return env_file


@pytest.fixture
def sample_queries():
    """Sample natural language queries for testing"""
    return [
        "How much agricultural land is being lost?",
        "Which states have the most urban expansion?",
        "Compare forest loss between RCP45 and RCP85",
        "Show me crop to pasture transitions",
        "What are the biggest land use changes?",
    ]


@pytest.fixture
def malicious_queries():
    """Malicious queries that should be blocked"""
    return [
        "DROP TABLE dim_scenario",
        "DELETE FROM fact_landuse_transitions",
        "UPDATE dim_scenario SET scenario_name = 'hacked'",
        "SELECT * FROM dim_scenario; DROP TABLE dim_scenario",
        "SELECT * FROM dim_scenario WHERE '1'='1' UNION ALL SELECT null,null,null,null,null--",
    ]


@pytest.fixture(autouse=True)
def cleanup_logs():
    """Clean up test logs after each test"""
    yield
    # Clean up any test logs created
    log_files = Path("logs").glob("test_*.log")
    for log_file in log_files:
        try:
            log_file.unlink()
        except:
            pass


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter that always allows requests"""
    with patch("landuse.utilities.security.RateLimiter") as mock:
        limiter = Mock()
        limiter.check_rate_limit.return_value = (True, None)
        mock.return_value = limiter
        yield limiter


# Skip markers for tests requiring external resources
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "requires_api: mark test as requiring real API keys")
    config.addinivalue_line("markers", "requires_db: mark test as requiring database")
    config.addinivalue_line("markers", "slow: mark test as slow running")


# Auto-use fixture to skip tests based on environment
@pytest.fixture(autouse=True)
def skip_tests_based_on_env(request):
    """Skip tests that require resources not available in test environment"""
    if request.node.get_closest_marker("requires_api"):
        if not os.getenv("REAL_OPENAI_API_KEY"):
            pytest.skip("Skipping test that requires real API key")

    if request.node.get_closest_marker("requires_db"):
        db_path = Path(os.getenv("LANDUSE_DB_PATH", "data/processed/landuse_analytics.duckdb"))
        if not db_path.exists():
            pytest.skip("Skipping test that requires production database")
