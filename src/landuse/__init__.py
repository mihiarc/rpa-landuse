"""
Landuse analysis package
"""

__version__ = "0.1.0"

# Import models for easier access
from .converter_models import ConversionConfig, ConversionMode, ConversionStats, ProcessedTransition, ValidationResult
from .models import (
    AgentConfig,
    AnalysisRequest,
    AnalysisResult,
    ChatMessage,
    LandUseCategory,
    LandUseType,
    QueryInput,
    QueryResult,
    RCPScenario,
    SQLQuery,
    SSPScenario,
    SystemStatus,
    TransitionType,
)

__all__ = [
    # Core models
    "AgentConfig",
    "QueryInput",
    "SQLQuery",
    "QueryResult",
    "ChatMessage",
    "SystemStatus",
    # Analysis models
    "AnalysisRequest",
    "AnalysisResult",
    # Enums
    "LandUseType",
    "LandUseCategory",
    "RCPScenario",
    "SSPScenario",
    "TransitionType",
    # Converter models
    "ConversionConfig",
    "ConversionMode",
    "ConversionStats",
    "ProcessedTransition",
    "ValidationResult",
]
