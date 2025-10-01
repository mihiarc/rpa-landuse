"""Schema versioning system for database evolution tracking."""

from datetime import datetime
from typing import Dict, Optional, Tuple
import duckdb
from pathlib import Path


class SchemaVersion:
    """Schema version definitions and compatibility matrix."""

    # Version history with descriptions
    SCHEMA_VERSIONS: Dict[str, str] = {
        '1.0.0': 'Original 20 GCM scenarios',
        '2.0.0': 'Combined scenarios with OVERALL default',
        '2.1.0': 'Added statistical fields (std_dev, min, max)',
        '2.2.0': 'Added schema versioning system'
    }

    # Current version
    CURRENT_VERSION = '2.2.0'

    # Compatibility matrix: which versions are compatible with each other
    COMPATIBILITY_MATRIX: Dict[str, Tuple[str, ...]] = {
        '2.2.0': ('2.0.0', '2.1.0', '2.2.0'),  # Current version works with 2.0+
        '2.1.0': ('2.0.0', '2.1.0'),
        '2.0.0': ('2.0.0',),
        '1.0.0': ('1.0.0',)
    }

    @classmethod
    def is_compatible(cls, db_version: str, app_version: str = None) -> bool:
        """Check if database version is compatible with application version.

        Args:
            db_version: Version of the database
            app_version: Version of the application (defaults to CURRENT_VERSION)

        Returns:
            True if versions are compatible, False otherwise
        """
        if app_version is None:
            app_version = cls.CURRENT_VERSION

        compatible_versions = cls.COMPATIBILITY_MATRIX.get(app_version, ())
        return db_version in compatible_versions

    @classmethod
    def get_breaking_changes(cls, from_version: str, to_version: str) -> list:
        """Get list of breaking changes between versions.

        Args:
            from_version: Starting version
            to_version: Target version

        Returns:
            List of breaking changes between versions
        """
        breaking_changes = {
            ('1.0.0', '2.0.0'): [
                'Schema restructured for combined scenarios',
                'dim_scenario table modified',
                'New OVERALL scenario added'
            ],
            ('2.0.0', '2.1.0'): [
                'Statistical fields added to fact table'
            ],
            ('2.1.0', '2.2.0'): [
                'Schema versioning table added'
            ]
        }

        return breaking_changes.get((from_version, to_version), [])


class SchemaVersionManager:
    """Manages schema versioning for the database."""

    def __init__(self, connection: duckdb.DuckDBPyConnection):
        """Initialize the schema version manager.

        Args:
            connection: DuckDB connection
        """
        self.connection = connection
        self._ensure_version_table()

    def _ensure_version_table(self):
        """Ensure the schema_version table exists."""
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version_id INTEGER PRIMARY KEY,
                version_number VARCHAR(20) NOT NULL,
                description TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                applied_by VARCHAR(100),
                UNIQUE(version_number)
            )
        """)

    def apply_version(self, version: str, applied_by: str = 'system') -> None:
        """Apply a version to the database.

        Args:
            version: Version number to apply
            applied_by: User or system applying the version

        Raises:
            ValueError: If version is already applied or invalid
        """
        # Check if version already exists first
        existing = self.connection.execute("""
            SELECT COUNT(*) FROM schema_version WHERE version_number = ?
        """, [version]).fetchone()[0]

        if existing > 0:
            # Log but don't fail - idempotent operation
            return

        description = SchemaVersion.SCHEMA_VERSIONS.get(version, 'Unknown version')

        self.connection.execute("""
            INSERT INTO schema_version (version_id, version_number, description, applied_by)
            SELECT COALESCE(MAX(version_id), 0) + 1, ?, ?, ?
            FROM schema_version
        """, [version, description, applied_by])

    def get_current_version(self) -> Optional[str]:
        """Get the current database schema version.

        Returns:
            Current version number or None if not versioned
        """
        try:
            result = self.connection.execute("""
                SELECT version_number
                FROM schema_version
                ORDER BY version_id DESC
                LIMIT 1
            """).fetchone()

            return result[0] if result else None
        except duckdb.CatalogException:
            # Table doesn't exist
            return None

    def get_version_history(self) -> list:
        """Get complete version history.

        Returns:
            List of version records with timestamps
        """
        try:
            return self.connection.execute("""
                SELECT version_number, description, applied_at, applied_by
                FROM schema_version
                ORDER BY version_id
            """).fetchall()
        except duckdb.CatalogException:
            return []

    def check_compatibility(self, required_version: str = None) -> Tuple[bool, Optional[str]]:
        """Check if database version is compatible with required version.

        Args:
            required_version: Required version (defaults to CURRENT_VERSION)

        Returns:
            Tuple of (is_compatible, current_db_version)
        """
        if required_version is None:
            required_version = SchemaVersion.CURRENT_VERSION

        current_version = self.get_current_version()

        if current_version is None:
            # No version - assume old database
            return False, None

        is_compatible = SchemaVersion.is_compatible(current_version, required_version)
        return is_compatible, current_version

    def detect_schema_version(self) -> Optional[str]:
        """Try to detect schema version based on database structure.

        Returns:
            Detected version or None if cannot determine
        """
        try:
            # Check for combined scenarios features
            result = self.connection.execute("""
                SELECT COUNT(*)
                FROM dim_scenario
                WHERE scenario_name = 'OVERALL'
            """).fetchone()

            if result and result[0] > 0:
                # Has OVERALL scenario - at least 2.0.0

                # Check for statistical fields
                result = self.connection.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.columns
                    WHERE table_name = 'fact_landuse_transitions'
                    AND column_name = 'acres_std_dev'
                """).fetchone()

                if result and result[0] > 0:
                    return '2.1.0'  # Has statistical fields
                else:
                    return '2.0.0'  # Combined scenarios but no stats
            else:
                # No OVERALL scenario - original version
                return '1.0.0'

        except duckdb.CatalogException:
            # Table doesn't exist - return None
            return None
        except Exception as e:
            # Log unexpected errors but don't fail
            import warnings
            warnings.warn(f"Unexpected error during schema detection: {e}")
            return None