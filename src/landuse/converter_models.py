#!/usr/bin/env python3
"""
Pydantic models for data conversion and ETL processes
Provides validation for the landuse data conversion pipeline
"""

from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConversionMode(str, Enum):
    """Available conversion modes"""

    STREAMING = "streaming"
    BATCH = "batch"
    PARALLEL = "parallel"
    BULK_COPY = "bulk_copy"


class ConversionConfig(BaseModel):
    """Configuration for data conversion process"""

    model_config = ConfigDict(extra="forbid")

    # Input/Output paths
    input_file: Path = Field(default=Path("data/raw/landuse_transitions.json"), description="Path to input JSON file")
    output_file: Path = Field(
        default=Path("data/processed/landuse_analytics.duckdb"), description="Path to output DuckDB database"
    )

    # Processing configuration
    mode: ConversionMode = Field(
        default=ConversionMode.BULK_COPY, description="Processing mode (bulk_copy recommended for performance)"
    )
    batch_size: int = Field(
        default=100000, gt=0, le=1000000, description="Batch size for processing (larger for bulk loading)"
    )
    parallel_workers: int = Field(default=4, gt=0, le=16, description="Number of parallel workers")

    # Bulk loading options
    use_bulk_copy: bool = Field(default=True, description="Use DuckDB COPY command for bulk loading")
    parquet_compression: str = Field(
        default="snappy", description="Parquet compression (snappy, gzip, brotli, lz4, zstd)"
    )
    temp_dir: Optional[Path] = Field(default=None, description="Temporary directory for bulk operations")
    optimize_after_load: bool = Field(default=True, description="Run ANALYZE on tables after bulk loading")

    # DuckDB configuration
    memory_limit: str = Field(default="8GB", description="DuckDB memory limit")
    threads: int = Field(default=8, gt=0, description="DuckDB thread count")

    # Progress tracking
    show_progress: bool = Field(default=True, description="Show progress bars")
    checkpoint_interval: int = Field(default=100000, gt=0, description="Records between checkpoints")

    @field_validator("input_file")
    @classmethod
    def validate_input_file(cls, v: Path) -> Path:
        """Ensure input file exists"""
        if not v.exists():
            raise ValueError(f"Input file not found: {v}")
        if not v.suffix == ".json":
            raise ValueError(f"Input file must be JSON: {v}")
        return v

    @field_validator("memory_limit")
    @classmethod
    def validate_memory_limit(cls, v: str) -> str:
        """Validate memory limit format"""
        import re

        if not re.match(r"^\d+[MG]B$", v):
            raise ValueError(f"Invalid memory limit format: {v}. Use format like '8GB' or '512MB'")
        return v


class RawLandUseData(BaseModel):
    """Raw land use data from JSON"""

    model_config = ConfigDict(extra="allow")

    scenario: str
    time_period: str
    geography: str
    transitions: dict[str, dict[str, float]]


class ProcessedTransition(BaseModel):
    """Processed transition record ready for database"""

    model_config = ConfigDict(extra="forbid")

    scenario_name: str
    climate_model: str
    rcp_scenario: str
    ssp_scenario: str
    time_period: str
    start_year: int
    end_year: int
    fips_code: str
    county_name: str
    state_code: str
    from_landuse: str
    to_landuse: str
    acres: float = Field(ge=0)
    transition_type: str

    @field_validator("fips_code")
    @classmethod
    def validate_fips_code(cls, v: str) -> str:
        """Validate FIPS code"""
        if not v.isdigit() or len(v) != 5:
            raise ValueError(f"Invalid FIPS code: {v}")
        return v

    @field_validator("transition_type")
    @classmethod
    def validate_transition_type(cls, v: str) -> str:
        """Validate transition type"""
        if v not in ["change", "stable"]:
            raise ValueError(f"Invalid transition type: {v}")
        return v


class ConversionStats(BaseModel):
    """Statistics from conversion process"""

    model_config = ConfigDict(extra="forbid")

    total_records: int = 0
    processed_records: int = 0
    failed_records: int = 0
    total_scenarios: int = 0
    total_counties: int = 0
    total_time_periods: int = 0
    processing_time: float = 0.0
    memory_peak_mb: float = 0.0

    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_records == 0:
            return 0.0
        return (self.processed_records / self.total_records) * 100

    def records_per_second(self) -> float:
        """Calculate processing rate"""
        if self.processing_time == 0:
            return 0.0
        return self.processed_records / self.processing_time


class ValidationResult(BaseModel):
    """Result from data validation"""

    model_config = ConfigDict(extra="forbid")

    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(warning)


class CheckpointData(BaseModel):
    """Checkpoint data for recovery"""

    model_config = ConfigDict(extra="forbid")

    timestamp: str
    records_processed: int
    last_scenario: Optional[str] = None
    last_time_period: Optional[str] = None
    last_geography: Optional[str] = None
    stats: ConversionStats
