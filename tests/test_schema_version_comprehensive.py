"""Comprehensive test coverage for schema versioning system edge cases and integrations."""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch

import duckdb
import pytest

from landuse.agents.database_manager import DatabaseManager
from landuse.core.app_config import AppConfig
from landuse.database.schema_version import SchemaVersion, SchemaVersionManager


class TestSchemaVersionEdgeCases:
    """Test edge cases and error conditions for schema versioning."""

    def test_invalid_version_parameters(self):
        """Test handling of invalid version parameters."""
        # Test invalid version in is_compatible
        assert not SchemaVersion.is_compatible("invalid.version", "2.2.0")
        assert not SchemaVersion.is_compatible("2.2.0", "invalid.version")

        # Test empty/None versions
        assert not SchemaVersion.is_compatible("", "2.2.0")
        assert not SchemaVersion.is_compatible(None, "2.2.0")

        # Test non-existent versions in compatibility matrix
        assert not SchemaVersion.is_compatible("99.99.99", "2.2.0")

    def test_breaking_changes_with_invalid_versions(self):
        """Test breaking changes with invalid version combinations."""
        # Non-existent version combinations
        changes = SchemaVersion.get_breaking_changes("99.0.0", "99.1.0")
        assert changes == []

        # Reverse version order (should return empty)
        changes = SchemaVersion.get_breaking_changes("2.2.0", "2.0.0")
        assert changes == []

        # Same version
        changes = SchemaVersion.get_breaking_changes("2.2.0", "2.2.0")
        assert changes == []

    def test_version_manager_with_corrupted_database(self):
        """Test version manager behavior with corrupted database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "corrupted.duckdb"

            # Create a valid database first
            conn = duckdb.connect(str(db_path))
            manager = SchemaVersionManager(conn)
            manager.apply_version("2.0.0", "test")
            conn.close()

            # Simulate corruption by truncating the file
            with open(db_path, "wb") as f:
                f.write(b"corrupted")

            # Should handle corruption gracefully
            with pytest.raises(duckdb.Error):
                conn = duckdb.connect(str(db_path))
                SchemaVersionManager(conn)

    def test_read_only_database_operations(self):
        """Test version manager operations on read-only database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "readonly.duckdb"

            # Create database with some data
            conn = duckdb.connect(str(db_path))
            manager = SchemaVersionManager(conn)
            manager.apply_version("2.1.0", "setup")
            conn.close()

            # Test that read-only connection fails gracefully when trying to create version table
            ro_conn = duckdb.connect(str(db_path), read_only=True)

            # Should fail when trying to ensure version table in read-only mode
            with pytest.raises(duckdb.InvalidInputException, match="read-only mode"):
                SchemaVersionManager(ro_conn)

            ro_conn.close()

    def test_concurrent_version_application(self):
        """Test concurrent version application scenarios."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "concurrent.duckdb"

            # Pre-create the database and version table to avoid creation conflicts
            conn = duckdb.connect(str(db_path))
            manager = SchemaVersionManager(conn)
            conn.close()

            results = []
            errors = []

            def apply_version_worker(version: str, user: str):
                try:
                    conn = duckdb.connect(str(db_path))
                    manager = SchemaVersionManager(conn)
                    manager.apply_version(version, user)
                    results.append((version, user))
                    conn.close()
                except Exception as e:
                    errors.append(e)

            # Start multiple threads trying to apply the same version
            threads = []
            for i in range(5):
                thread = threading.Thread(target=apply_version_worker, args=("2.2.0", f"user_{i}"))
                threads.append(thread)
                thread.start()

            # Wait for all threads
            for thread in threads:
                thread.join()

            # Some errors are expected due to concurrent access, but should be handled gracefully
            # The important thing is that the final state is consistent

            # Check final state
            conn = duckdb.connect(str(db_path))
            manager = SchemaVersionManager(conn)
            history = manager.get_version_history()

            # Only one version record should exist (due to UNIQUE constraint)
            assert len(history) == 1
            assert history[0][0] == "2.2.0"

            # At least one thread should have succeeded
            assert len(results) >= 1
            conn.close()

    def test_schema_detection_edge_cases(self):
        """Test schema detection with edge cases."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "edge_cases.duckdb"
            conn = duckdb.connect(str(db_path))

            # Test detection with minimal schema
            manager = SchemaVersionManager(conn)
            assert manager.detect_schema_version() is None

            # Test with only dim_scenario table but no OVERALL scenario
            conn.execute("""
                CREATE TABLE dim_scenario (
                    scenario_id INTEGER PRIMARY KEY,
                    scenario_name VARCHAR(100)
                )
            """)
            conn.execute("INSERT INTO dim_scenario VALUES (1, 'RCP45_SSP2')")

            # Should detect as 1.0.0
            manager_v1 = SchemaVersionManager(conn)
            assert manager_v1.detect_schema_version() == "1.0.0"

            # Test with OVERALL scenario but missing fact table
            conn.execute("INSERT INTO dim_scenario VALUES (2, 'OVERALL')")
            manager_v2 = SchemaVersionManager(conn)
            # Should still detect as 2.0.0 even without fact table
            assert manager_v2.detect_schema_version() == "2.0.0"

            conn.close()

    def test_version_history_with_large_dataset(self):
        """Test version history operations with many version records."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "large_history.duckdb"
            conn = duckdb.connect(str(db_path))

            manager = SchemaVersionManager(conn)

            # Apply many versions (simulate migration history)
            versions = ["1.0.0", "2.0.0", "2.1.0", "2.2.0"]
            for i, version in enumerate(versions):
                manager.apply_version(version, f"user_{i}")

            # Get history
            history = manager.get_version_history()
            assert len(history) == 4

            # Check ordering (should be by version_id)
            version_numbers = [record[0] for record in history]
            assert version_numbers == versions

            # Current version should be the last one
            assert manager.get_current_version() == "2.2.0"

            conn.close()

    def test_malformed_version_table(self):
        """Test behavior with malformed version table."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "malformed.duckdb"
            conn = duckdb.connect(str(db_path))

            # Create malformed version table (missing required columns)
            conn.execute("""
                CREATE TABLE schema_version (
                    version_number VARCHAR(20)
                    -- Missing other required columns like version_id
                )
            """)

            # Manager should handle malformed table gracefully
            manager = SchemaVersionManager(conn)

            # Operations should fail gracefully with malformed table structure
            with pytest.raises(duckdb.BinderException):
                manager.get_current_version()

            with pytest.raises(duckdb.BinderException):
                manager.get_version_history()

            conn.close()


class TestSchemaVersionIntegration:
    """Test integration of schema versioning with other components."""

    def test_database_manager_version_checking(self):
        """Test schema version checking in DatabaseManager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "integration.duckdb"

            # Create database with version info
            conn = duckdb.connect(str(db_path))

            # Create minimal schema to avoid "no tables" error
            conn.execute("""
                CREATE TABLE dim_scenario (
                    scenario_id INTEGER PRIMARY KEY,
                    scenario_name VARCHAR(100)
                )
            """)
            conn.execute("INSERT INTO dim_scenario VALUES (1, 'OVERALL')")

            # Create fact table for complete schema
            conn.execute("""
                CREATE TABLE fact_landuse_transitions (
                    transition_id INTEGER,
                    scenario_id INTEGER,
                    acres DECIMAL(18,2)
                )
            """)

            manager = SchemaVersionManager(conn)
            manager.apply_version("2.0.0", "test")
            conn.close()

            # Test DatabaseManager integration
            config = AppConfig()
            config.database.path = str(db_path)

            db_manager = DatabaseManager(config)

            # Should successfully connect
            connection = db_manager.get_connection()
            assert connection is not None

            # DatabaseManager opens in read-only mode, so version checking will fail gracefully
            # This is expected behavior - the version manager handles read-only gracefully
            assert db_manager._db_version is None  # Can't read version in read-only mode
            assert db_manager._version_manager is None  # Manager creation failed

    def test_database_manager_error_handling(self):
        """Test DatabaseManager graceful error handling for version checking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "error_handling.duckdb"

            # Create database with schema but no version table
            conn = duckdb.connect(str(db_path))

            # Create minimal schema to avoid "no tables" error
            conn.execute("""
                CREATE TABLE dim_scenario (
                    scenario_id INTEGER PRIMARY KEY,
                    scenario_name VARCHAR(100)
                )
            """)
            conn.execute("INSERT INTO dim_scenario VALUES (1, 'RCP45_SSP2')")
            conn.close()

            # Test DatabaseManager with database that can't have version table created (read-only)
            config = AppConfig()
            config.database.path = str(db_path)

            # Should not raise exception, should handle gracefully
            db_manager = DatabaseManager(config)
            connection = db_manager.get_connection()

            # Should successfully connect despite version check failure
            assert connection is not None
            assert db_manager._db_version is None  # Version check failed gracefully
            assert db_manager._version_manager is None

    def test_schema_version_direct_operations(self):
        """Test schema version operations without read-only restrictions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "direct_ops.duckdb"

            # Create database with schema for direct testing
            conn = duckdb.connect(str(db_path))

            # Create v2.1.0 schema (with statistical fields)
            conn.execute("""
                CREATE TABLE dim_scenario (
                    scenario_id INTEGER PRIMARY KEY,
                    scenario_name VARCHAR(100)
                )
            """)
            conn.execute("INSERT INTO dim_scenario VALUES (1, 'OVERALL')")

            conn.execute("""
                CREATE TABLE fact_landuse_transitions (
                    transition_id INTEGER,
                    scenario_id INTEGER,
                    acres DECIMAL(18,2),
                    acres_std_dev DECIMAL(18,2)
                )
            """)

            # Test direct schema version operations (non-read-only)
            manager = SchemaVersionManager(conn)

            # Should auto-detect v2.1.0
            detected_version = manager.detect_schema_version()
            assert detected_version == "2.1.0"

            # Apply detected version
            manager.apply_version(detected_version, "integration_test")

            # Verify version was applied
            current_version = manager.get_current_version()
            assert current_version == "2.1.0"

            # Test compatibility
            is_compatible, version = manager.check_compatibility()
            assert is_compatible
            assert version == "2.1.0"

            conn.close()


class TestSchemaVersionPerformance:
    """Test performance aspects of schema versioning."""

    def test_version_operations_performance(self):
        """Test performance of version operations with realistic data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "performance.duckdb"
            conn = duckdb.connect(str(db_path))

            manager = SchemaVersionManager(conn)

            # Time version application
            start_time = time.time()
            manager.apply_version("2.2.0", "perf_test")
            apply_time = time.time() - start_time

            # Should be very fast (< 100ms)
            assert apply_time < 0.1

            # Time version retrieval
            start_time = time.time()
            current_version = manager.get_current_version()
            get_time = time.time() - start_time

            assert current_version == "2.2.0"
            assert get_time < 0.01  # Should be very fast

            # Time history retrieval
            start_time = time.time()
            history = manager.get_version_history()
            history_time = time.time() - start_time

            assert len(history) == 1
            assert history_time < 0.01

            conn.close()

    def test_schema_detection_performance(self):
        """Test performance of schema detection with realistic database size."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "large_schema.duckdb"
            conn = duckdb.connect(str(db_path))

            # Create realistic schema size
            conn.execute("""
                CREATE TABLE dim_scenario (
                    scenario_id INTEGER PRIMARY KEY,
                    scenario_name VARCHAR(100)
                )
            """)

            # Insert many scenarios
            for i in range(100):
                conn.execute(f"INSERT INTO dim_scenario VALUES ({i}, 'Scenario_{i}')")

            conn.execute("INSERT INTO dim_scenario VALUES (999, 'OVERALL')")

            # Create large fact table structure
            conn.execute("""
                CREATE TABLE fact_landuse_transitions (
                    transition_id INTEGER,
                    scenario_id INTEGER,
                    acres DECIMAL(18,2),
                    acres_std_dev DECIMAL(18,2)
                )
            """)

            manager = SchemaVersionManager(conn)

            # Time schema detection
            start_time = time.time()
            detected_version = manager.detect_schema_version()
            detection_time = time.time() - start_time

            assert detected_version == "2.1.0"
            # Should be reasonably fast even with large data
            assert detection_time < 1.0

            conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
