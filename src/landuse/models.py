#!/usr/bin/env python3
"""
Pydantic models for landuse data structures
Provides comprehensive data validation and type safety
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Enums for controlled vocabularies
class LandUseType(str, Enum):
    """Land use types with standardized codes"""

    CROP = "cr"
    PASTURE = "ps"
    RANGELAND = "rg"
    FOREST = "fr"
    URBAN = "ur"

    @classmethod
    def from_name(cls, name: str) -> "LandUseType":
        """Get enum from display name"""
        mapping = {
            "Crop": cls.CROP,
            "Pasture": cls.PASTURE,
            "Rangeland": cls.RANGELAND,
            "Forest": cls.FOREST,
            "Urban": cls.URBAN,
        }
        return mapping.get(name, cls.CROP)


class LandUseCategory(str, Enum):
    """Land use categories"""

    AGRICULTURE = "Agriculture"
    NATURAL = "Natural"
    DEVELOPED = "Developed"


class RCPScenario(str, Enum):
    """Representative Concentration Pathways"""

    RCP45 = "4.5"
    RCP85 = "8.5"


class SSPScenario(str, Enum):
    """Shared Socioeconomic Pathways"""

    SSP1 = "SSP1"
    SSP2 = "SSP2"
    SSP3 = "SSP3"
    SSP5 = "SSP5"


class TransitionType(str, Enum):
    """Types of land use transitions"""

    CHANGE = "change"
    STABLE = "same"  # Fixed to match database values


class IndicatorType(str, Enum):
    """Types of socioeconomic indicators"""

    DEMOGRAPHIC = "Demographic"
    ECONOMIC = "Economic"


class GrowthTrend(str, Enum):
    """Growth trend classifications"""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class UrbanizationLevel(str, Enum):
    """Urbanization level classifications"""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# Data Models
class AgentConfig(BaseModel):
    """Configuration for landuse agents"""

    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    # Database configuration
    db_path: Path = Field(
        default=Path("data/processed/landuse_analytics.duckdb"), description="Path to DuckDB database"
    )

    # Model configuration
    model_name: str = Field(default="gpt-4o-mini", description="LLM model to use")
    temperature: float = Field(default=0.1, ge=0, le=2, description="Model temperature")
    max_tokens: int = Field(default=4000, gt=0, description="Maximum tokens in response")

    # Query execution limits
    max_iterations: int = Field(default=5, gt=0, le=20, description="Maximum agent iterations")
    max_execution_time: int = Field(default=120, gt=0, le=600, description="Maximum query execution time in seconds")
    max_query_rows: int = Field(default=1000, gt=0, le=10000, description="Maximum rows returned by queries")
    default_display_limit: int = Field(default=50, gt=0, le=500, description="Default number of rows to display")

    # Rate limiting
    rate_limit_calls: int = Field(default=60, gt=0, description="Maximum API calls per time window")
    rate_limit_window: int = Field(default=60, gt=0, description="Rate limit time window in seconds")

    @field_validator("db_path")
    @classmethod
    def validate_db_path(cls, v: Path) -> Path:
        """Ensure database path exists"""
        if not v.exists():
            raise ValueError(f"Database not found at {v}")
        return v


class QueryInput(BaseModel):
    """Input for natural language queries"""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=1000, description="Natural language query about land use")
    include_assumptions: bool = Field(default=True, description="Include default assumptions in response")

    @field_validator("query")
    @classmethod
    def clean_query(cls, v: str) -> str:
        """Clean and validate query"""
        return v.strip()


class SQLQuery(BaseModel):
    """Validated SQL query"""

    model_config = ConfigDict(extra="forbid")

    sql: str = Field(..., min_length=1, description="SQL query to execute")
    description: Optional[str] = Field(None, description="Human-readable description of query")

    @field_validator("sql")
    @classmethod
    def validate_sql(cls, v: str) -> str:
        """Basic SQL validation"""
        v = v.strip()
        if not v.upper().startswith(("SELECT", "WITH")):
            raise ValueError("Only SELECT and WITH queries are allowed")
        if "DELETE" in v.upper() or "DROP" in v.upper() or "UPDATE" in v.upper():
            raise ValueError("Destructive operations not allowed")
        return v


class QueryResult(BaseModel):
    """Result from query execution"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool
    data: Optional[pd.DataFrame] = Field(None, exclude=True)  # Exclude from serialization
    error: Optional[str] = None
    row_count: int = 0
    column_count: int = 0
    execution_time: float = 0.0
    query: Optional[str] = None

    @model_validator(mode="after")
    def set_counts(self) -> "QueryResult":
        """Set row and column counts from dataframe"""
        if self.data is not None:
            self.row_count = len(self.data)
            self.column_count = len(self.data.columns)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with data as list of dicts"""
        result = self.model_dump(exclude={"data"})
        if self.data is not None:
            result["data"] = self.data.to_dict(orient="records")
        return result


class DimensionTable(BaseModel):
    """Base model for dimension tables"""

    model_config = ConfigDict(extra="forbid")


class ScenarioDimension(DimensionTable):
    """Scenario dimension data"""

    scenario_id: int
    scenario_name: str
    climate_model: str
    rcp_scenario: RCPScenario
    ssp_scenario: SSPScenario


class TimeDimension(DimensionTable):
    """Time dimension data"""

    time_id: int
    year_range: str
    start_year: int
    end_year: int
    period_length: int = 10


class GeographyDimension(DimensionTable):
    """Geography dimension data"""

    geography_id: int
    fips_code: str
    county_name: str
    state_code: str
    state_name: Optional[str] = None
    region: Optional[str] = None

    @field_validator("fips_code")
    @classmethod
    def validate_fips(cls, v: str) -> str:
        """Validate FIPS code format"""
        if not v.isdigit() or len(v) != 5:
            raise ValueError("FIPS code must be 5 digits")
        return v


class LandUseDimension(DimensionTable):
    """Land use dimension data"""

    landuse_id: int
    landuse_code: LandUseType
    landuse_name: str
    landuse_category: LandUseCategory


class LandUseTransition(BaseModel):
    """Fact table record for land use transitions"""

    model_config = ConfigDict(extra="forbid")

    transition_id: int
    scenario_id: int
    time_id: int
    geography_id: int
    from_landuse_id: int
    to_landuse_id: int
    acres: float = Field(ge=0)
    transition_type: TransitionType

    @model_validator(mode="after")
    def validate_transition(self) -> "LandUseTransition":
        """Validate transition logic"""
        if self.transition_type == TransitionType.STABLE:
            if self.from_landuse_id != self.to_landuse_id:
                raise ValueError("Stable transitions must have same from/to landuse")
        elif self.from_landuse_id == self.to_landuse_id:
            raise ValueError("Change transitions must have different from/to landuse")
        return self


class AnalysisRequest(BaseModel):
    """Request for data analysis"""

    model_config = ConfigDict(extra="forbid")

    analysis_type: Literal[
        "agricultural_loss", "urban_expansion", "forest_change", "climate_comparison", "geographic_summary"
    ]
    scenarios: Optional[list[str]] = None
    states: Optional[list[str]] = None
    time_periods: Optional[list[str]] = None
    group_by: Optional[list[str]] = Field(default=None, description="Fields to group results by")
    limit: int = Field(default=100, gt=0, le=1000)


class AnalysisResult(BaseModel):
    """Result from analysis request"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    request: AnalysisRequest
    data: pd.DataFrame = Field(exclude=True)
    summary_stats: dict[str, float]
    insights: list[str]
    visualization_data: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = self.model_dump(exclude={"data"})
        result["data"] = self.data.to_dict(orient="records")
        return result


class ToolInput(BaseModel):
    """Base model for agent tool inputs"""

    model_config = ConfigDict(extra="forbid")


class ExecuteQueryInput(ToolInput):
    """Input for execute_landuse_query tool"""

    sql_query: str = Field(..., description="SQL query to execute on the landuse database")


class SchemaInfoInput(ToolInput):
    """Input for get_schema_info tool"""

    table_name: Optional[str] = Field(None, description="Specific table to get schema for")


class QueryExamplesInput(ToolInput):
    """Input for suggest_query_examples tool"""

    category: Optional[str] = Field(None, description="Category of examples to show")


class StateCodeInput(ToolInput):
    """Input for get_state_code tool"""

    state_name: str = Field(..., description="State name to get code for")


# Response models for API/Streamlit
class ChatMessage(BaseModel):
    """Chat message structure"""

    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    thinking: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class SystemStatus(BaseModel):
    """System status information"""

    model_config = ConfigDict(protected_namespaces=())

    database_connected: bool
    agent_initialized: bool
    model_name: str
    database_path: str
    table_count: int
    total_records: int
    last_query_time: Optional[float] = None
    error_message: Optional[str] = None


# Socioeconomic Models
class SocioeconomicDimension(DimensionTable):
    """Socioeconomic scenario dimension data"""

    socioeconomic_id: int
    ssp_scenario: SSPScenario
    scenario_name: str
    narrative_description: Optional[str] = None
    population_growth_trend: Optional[GrowthTrend] = None
    economic_growth_trend: Optional[GrowthTrend] = None
    urbanization_level: Optional[UrbanizationLevel] = None


class IndicatorDimension(DimensionTable):
    """Socioeconomic indicator dimension data"""

    indicator_id: int
    indicator_name: str
    indicator_type: IndicatorType
    unit_of_measure: str
    description: Optional[str] = None


class SocioeconomicProjection(BaseModel):
    """Fact table record for socioeconomic projections"""

    model_config = ConfigDict(extra="forbid")

    projection_id: int
    geography_id: int
    socioeconomic_id: int
    indicator_id: int
    year: int = Field(ge=2010, le=2100)
    value: float = Field(ge=0)
    is_historical: bool = Field(default=False)

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        """Validate projection year"""
        if v < 2010 or v > 2100:
            raise ValueError("Year must be between 2010 and 2100")
        return v

    @model_validator(mode="after")
    def validate_historical_flag(self) -> "SocioeconomicProjection":
        """Validate historical flag based on year"""
        if self.year <= 2020 and not self.is_historical:
            self.is_historical = True
        elif self.year > 2020 and self.is_historical:
            self.is_historical = False
        return self


class PopulationMetric(BaseModel):
    """Population-specific validation and processing"""

    model_config = ConfigDict(extra="forbid")

    fips_code: str
    ssp_scenario: SSPScenario
    year: int
    population_thousands: float = Field(gt=0, description="Population in thousands")
    growth_rate: Optional[float] = None

    @field_validator("fips_code")
    @classmethod
    def validate_fips(cls, v: str) -> str:
        """Validate FIPS code format"""
        if not v.isdigit() or len(v) != 5:
            raise ValueError("FIPS code must be 5 digits")
        return v

    @field_validator("population_thousands")
    @classmethod
    def validate_population(cls, v: float) -> float:
        """Validate population is reasonable"""
        if v > 50000:  # 50 million people in one county seems unreasonable
            raise ValueError("Population seems unreasonably high")
        return v


class IncomeMetric(BaseModel):
    """Income-specific validation and processing"""

    model_config = ConfigDict(extra="forbid")

    fips_code: str
    ssp_scenario: SSPScenario
    year: int
    income_per_capita_2009usd: float = Field(gt=0, description="Per capita income in 2009 USD thousands")
    income_category: str = Field(default="Per Capita")

    @field_validator("fips_code")
    @classmethod
    def validate_fips(cls, v: str) -> str:
        """Validate FIPS code format"""
        if not v.isdigit() or len(v) != 5:
            raise ValueError("FIPS code must be 5 digits")
        return v

    @field_validator("income_per_capita_2009usd")
    @classmethod
    def validate_income(cls, v: float) -> float:
        """Validate income is reasonable"""
        if v < 5 or v > 500:  # $5k to $500k in 2009 USD seems reasonable
            raise ValueError("Income per capita outside reasonable range (5-500k USD)")
        return v


class SocioeconomicAnalysisRequest(BaseModel):
    """Request for socioeconomic analysis"""

    model_config = ConfigDict(extra="forbid")

    analysis_type: Literal[
        "population_growth", "income_trends", "ssp_comparison", "demographic_drivers", "economic_landuse_correlation"
    ]
    ssp_scenarios: Optional[list[SSPScenario]] = None
    states: Optional[list[str]] = None
    years: Optional[list[int]] = Field(default=None, description="Years to analyze")
    indicators: Optional[list[str]] = Field(default=None, description="Indicators to include")
    limit: int = Field(default=100, gt=0, le=1000)

    @field_validator("years")
    @classmethod
    def validate_years(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        """Validate analysis years"""
        if v is not None:
            for year in v:
                if year < 2010 or year > 2100:
                    raise ValueError("Years must be between 2010 and 2100")
        return v


class IntegratedAnalysisResult(BaseModel):
    """Result from integrated landuse + socioeconomic analysis"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    landuse_data: pd.DataFrame = Field(exclude=True)
    socioeconomic_data: pd.DataFrame = Field(exclude=True)
    correlation_metrics: dict[str, float]
    insights: list[str]
    demographic_drivers: Optional[dict[str, Any]] = None
    economic_indicators: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = self.model_dump(exclude={"landuse_data", "socioeconomic_data"})
        result["landuse_data"] = self.landuse_data.to_dict(orient="records") if self.landuse_data is not None else []
        result["socioeconomic_data"] = (
            self.socioeconomic_data.to_dict(orient="records") if self.socioeconomic_data is not None else []
        )
        return result
