"""Test schema versioning system functionality."""

import tempfile
from pathlib import Path

import duckdb
import pytest

from landuse.database.schema_version import SchemaVersion, SchemaVersionManager


def test_schema_version_constants():
    """Test that schema version constants are properly defined."""
    assert SchemaVersion.CURRENT_VERSION == '2.2.0'
    assert '1.0.0' in SchemaVersion.SCHEMA_VERSIONS
    assert '2.0.0' in SchemaVersion.SCHEMA_VERSIONS
    assert '2.1.0' in SchemaVersion.SCHEMA_VERSIONS
    assert '2.2.0' in SchemaVersion.SCHEMA_VERSIONS


def test_version_compatibility():
    """Test version compatibility checking."""
    # Test current version compatibility
    assert SchemaVersion.is_compatible('2.2.0', '2.2.0')
    assert SchemaVersion.is_compatible('2.1.0', '2.2.0')
    assert SchemaVersion.is_compatible('2.0.0', '2.2.0')

    # Test incompatible versions
    assert not SchemaVersion.is_compatible('1.0.0', '2.2.0')
    assert not SchemaVersion.is_compatible('1.0.0', '2.0.0')


def test_breaking_changes():
    """Test breaking changes documentation."""
    changes = SchemaVersion.get_breaking_changes('1.0.0', '2.0.0')
    assert len(changes) > 0
    assert any('combined scenarios' in change.lower() for change in changes)

    changes = SchemaVersion.get_breaking_changes('2.1.0', '2.2.0')
    assert len(changes) > 0
    assert any('versioning' in change.lower() for change in changes)


def test_version_manager_with_empty_database():
    """Test version manager with a new empty database."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / 'test.duckdb'
        conn = duckdb.connect(str(db_path))

        # Create version manager
        manager = SchemaVersionManager(conn)

        # Check that version table was created
        result = conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'schema_version'
        """).fetchone()
        assert result[0] == 1

        # Check no version exists yet
        assert manager.get_current_version() is None

        # Apply a version
        manager.apply_version('2.2.0', 'test_user')

        # Check version was applied
        assert manager.get_current_version() == '2.2.0'

        # Check version history
        history = manager.get_version_history()
        assert len(history) == 1
        assert history[0][0] == '2.2.0'
        assert history[0][3] == 'test_user'

        conn.close()


def test_version_manager_duplicate_version():
    """Test that duplicate versions are handled gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / 'test.duckdb'
        conn = duckdb.connect(str(db_path))

        manager = SchemaVersionManager(conn)

        # Apply same version twice
        manager.apply_version('2.0.0', 'user1')
        manager.apply_version('2.0.0', 'user2')  # Should not raise error

        # Check only one version exists
        history = manager.get_version_history()
        assert len(history) == 1
        assert history[0][3] == 'user1'  # First user who applied it

        conn.close()


def test_version_detection_with_combined_scenarios():
    """Test automatic version detection based on schema structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / 'test.duckdb'
        conn = duckdb.connect(str(db_path))

        # Create schema that looks like v2.0.0 (combined scenarios)
        conn.execute("""
            CREATE TABLE dim_scenario (
                scenario_id INTEGER PRIMARY KEY,
                scenario_name VARCHAR(100),
                description TEXT
            )
        """)

        conn.execute("""
            INSERT INTO dim_scenario VALUES (1, 'OVERALL', 'Default scenario')
        """)

        conn.execute("""
            CREATE TABLE fact_landuse_transitions (
                transition_id INTEGER,
                scenario_id INTEGER,
                acres DECIMAL(18,2)
            )
        """)

        manager = SchemaVersionManager(conn)
        detected_version = manager.detect_schema_version()
        assert detected_version == '2.0.0'

        # Now add statistical fields (v2.1.0)
        conn.execute("""
            ALTER TABLE fact_landuse_transitions
            ADD COLUMN acres_std_dev DECIMAL(18,2)
        """)

        manager2 = SchemaVersionManager(conn)
        detected_version = manager2.detect_schema_version()
        assert detected_version == '2.1.0'

        conn.close()


def test_compatibility_check():
    """Test database compatibility checking."""
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / 'test.duckdb'
        conn = duckdb.connect(str(db_path))

        manager = SchemaVersionManager(conn)

        # Apply an old version
        manager.apply_version('2.0.0', 'test')

        # Check compatibility with current version
        is_compatible, db_version = manager.check_compatibility('2.2.0')
        assert is_compatible  # 2.0.0 is compatible with 2.2.0
        assert db_version == '2.0.0'

        # Apply incompatible version
        conn.execute("DELETE FROM schema_version")  # Clear version
        manager.apply_version('1.0.0', 'test')

        is_compatible, db_version = manager.check_compatibility('2.2.0')
        assert not is_compatible  # 1.0.0 is not compatible with 2.2.0
        assert db_version == '1.0.0'

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
