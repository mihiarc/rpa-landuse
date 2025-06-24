"""
Landuse analysis package
"""

__version__ = "0.1.0"

# Import models for easier access
from .models import (
    AgentConfig,
    QueryInput,
    SQLQuery,
    QueryResult,
    ChatMessage,
    SystemStatus,
    AnalysisRequest,
    AnalysisResult,
    LandUseType,
    LandUseCategory,
    RCPScenario,
    SSPScenario,
    TransitionType
)

from .converter_models import (
    ConversionConfig,
    ConversionMode,
    ConversionStats,
    ProcessedTransition,
    ValidationResult
)

__all__ = [
    # Core models
    'AgentConfig',
    'QueryInput', 
    'SQLQuery',
    'QueryResult',
    'ChatMessage',
    'SystemStatus',
    
    # Analysis models
    'AnalysisRequest',
    'AnalysisResult',
    
    # Enums
    'LandUseType',
    'LandUseCategory',
    'RCPScenario',
    'SSPScenario',
    'TransitionType',
    
    # Converter models
    'ConversionConfig',
    'ConversionMode',
    'ConversionStats',
    'ProcessedTransition',
    'ValidationResult'
]