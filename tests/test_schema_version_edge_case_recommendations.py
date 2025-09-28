"""Additional test recommendations for achieving 100% schema version coverage."""

import tempfile
from pathlib import Path

import duckdb
import pytest

from landuse.database.schema_version import SchemaVersion, SchemaVersionManager


class TestSchemaVersionFullCoverage:
    """Tests to achieve 100% coverage for remaining edge cases."""

    def test_is_compatible_default_app_version(self):
        """Test is_compatible with default app_version parameter (line 43)."""
        # Test with None app_version (should use CURRENT_VERSION)
        assert SchemaVersion.is_compatible('2.2.0', None)
        assert SchemaVersion.is_compatible('2.1.0', None)
        assert not SchemaVersion.is_compatible('1.0.0', None)

        # Test without app_version parameter at all (uses default)
        assert SchemaVersion.is_compatible('2.2.0')
        assert SchemaVersion.is_compatible('2.1.0')
        assert not SchemaVersion.is_compatible('1.0.0')

    def test_get_current_version_catalog_exception(self):
        """Test get_current_version when schema_version table doesn't exist (lines 135-137)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'no_version_table.duckdb'
            conn = duckdb.connect(str(db_path))

            # Don't create SchemaVersionManager (which would create the table)
            # Instead, manually test the method
            manager = SchemaVersionManager.__new__(SchemaVersionManager)
            manager.connection = conn

            # Call get_current_version without the version table existing
            result = manager.get_current_version()
            assert result is None  # Should handle CatalogException gracefully

            conn.close()

    def test_get_version_history_catalog_exception(self):
        """Test get_version_history when schema_version table doesn't exist (lines 151-152)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'no_version_table.duckdb'
            conn = duckdb.connect(str(db_path))

            # Create manager instance without initializing (to avoid table creation)
            manager = SchemaVersionManager.__new__(SchemaVersionManager)
            manager.connection = conn

            # Call get_version_history without the version table existing
            result = manager.get_version_history()
            assert result == []  # Should return empty list on CatalogException

            conn.close()

    def test_check_compatibility_default_required_version(self):
        """Test check_compatibility with default required_version parameter (line 164)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'default_version.duckdb'
            conn = duckdb.connect(str(db_path))

            manager = SchemaVersionManager(conn)
            manager.apply_version('2.1.0', 'test')

            # Test with None required_version (should use CURRENT_VERSION)
            is_compatible, current_version = manager.check_compatibility(None)
            assert is_compatible
            assert current_version == '2.1.0'

            # Test without required_version parameter at all (uses default)
            is_compatible, current_version = manager.check_compatibility()
            assert is_compatible
            assert current_version == '2.1.0'

            conn.close()

    def test_check_compatibility_no_version(self):
        """Test check_compatibility when no version is set (line 170)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'no_version.duckdb'
            conn = duckdb.connect(str(db_path))

            # Create manager but don't apply any version
            manager = SchemaVersionManager(conn)

            # Should return False, None for unversioned database
            is_compatible, current_version = manager.check_compatibility()
            assert not is_compatible
            assert current_version is None

            conn.close()

    def test_detect_schema_version_exception_handling(self):
        """Test detect_schema_version exception handling (lines 208-209)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'bad_schema.duckdb'
            conn = duckdb.connect(str(db_path))

            # Create a schema that will cause errors during detection
            # Don't create the expected tables
            manager = SchemaVersionManager(conn)

            # Should handle exceptions gracefully and return None
            detected_version = manager.detect_schema_version()
            assert detected_version is None

            conn.close()


class TestSchemaVersionRobustness:
    """Additional robustness tests for production scenarios."""

    def test_version_application_with_constraint_exception(self):
        """Test version application handling of ConstraintException (lines 116-118)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'constraint_test.duckdb'
            conn = duckdb.connect(str(db_path))

            manager = SchemaVersionManager(conn)

            # Apply version first time - should succeed
            manager.apply_version('2.0.0', 'user1')

            # Apply same version again - should handle ConstraintException gracefully
            manager.apply_version('2.0.0', 'user2')  # Should not raise exception

            # Verify only one record exists
            history = manager.get_version_history()
            assert len(history) == 1
            assert history[0][3] == 'user1'  # First user should be preserved

            conn.close()

    def test_schema_detection_with_missing_columns(self):
        """Test schema detection with incomplete table structures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'incomplete_schema.duckdb'
            conn = duckdb.connect(str(db_path))

            # Create dim_scenario table but without OVERALL scenario
            conn.execute("""
                CREATE TABLE dim_scenario (
                    scenario_id INTEGER PRIMARY KEY,
                    scenario_name VARCHAR(100)
                )
            """)

            # Don't insert any data
            manager = SchemaVersionManager(conn)

            # Should detect as 1.0.0 (no OVERALL scenario)
            detected_version = manager.detect_schema_version()
            assert detected_version == '1.0.0'

            conn.close()

    def test_version_manager_initialization_robustness(self):
        """Test version manager initialization in various states."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'robust_init.duckdb'

            # Test with completely new database file
            conn = duckdb.connect(str(db_path))
            manager = SchemaVersionManager(conn)

            # Should create version table successfully
            result = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_name = 'schema_version'
            """).fetchone()
            assert result[0] == 1

            conn.close()

    def test_large_version_description_handling(self):
        """Test handling of large version descriptions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / 'large_desc.duckdb'
            conn = duckdb.connect(str(db_path))

            manager = SchemaVersionManager(conn)

            # Test with a version that might have a very long description
            long_description = "A" * 1000  # Very long description
            test_version = "99.99.99"

            # Temporarily add to SCHEMA_VERSIONS for testing
            original_versions = SchemaVersion.SCHEMA_VERSIONS.copy()
            SchemaVersion.SCHEMA_VERSIONS[test_version] = long_description

            try:
                manager.apply_version(test_version, 'test_user')
                history = manager.get_version_history()

                # Find our test version
                test_record = [h for h in history if h[0] == test_version][0]
                assert test_record[1] == long_description

            finally:
                # Restore original versions
                SchemaVersion.SCHEMA_VERSIONS = original_versions

            conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])