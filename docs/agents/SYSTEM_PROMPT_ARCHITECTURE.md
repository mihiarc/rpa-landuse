# Modern System Prompt Architecture

## Location and Design

The system prompt system has been **modernized with a centralized, modular approach**. Instead of being hardcoded in agent files, prompts are now managed through a dedicated `prompts.py` module with configurable variations and domain specialization.

## Modern Modular Architecture

```mermaid
graph TD
    A[prompts.py] --> B[get_system_prompt\\(\\)]
    C[LanduseConfig] --> B
    D[constants.py] --> E[SCHEMA_INFO_TEMPLATE]
    E --> B
    
    B --> F[SYSTEM_PROMPT_BASE]
    B --> G[Analysis Style Variants]
    B --> H[Domain Focus Variants]
    B --> I[Map Generation Section]
    
    F --> J[Complete System Prompt]
    G --> J
    H --> J
    I --> J
    
    J --> K[LanduseAgent]
    
    subgraph "Prompt Templates"
        F
        L[DETAILED_ANALYSIS_PROMPT]
        M[EXECUTIVE_SUMMARY_PROMPT]
        N[AGRICULTURAL_FOCUS_PROMPT]
        O[CLIMATE_FOCUS_PROMPT]
        P[URBAN_PLANNING_PROMPT]
    end
    
    subgraph "Configuration-Driven"
        C
        Q[analysis_style]
        R[domain_focus]
        S[include_maps]
    end
    
    L --> G
    M --> G
    N --> H
    O --> H
    P --> H
    
    Q --> G
    R --> H
    S --> I
```

## Modular Prompt System

### 1. **Base Prompt Template** (From prompts.py)
```python
# From src/landuse/agents/prompts.py
SYSTEM_PROMPT_BASE = """You are a land use analytics expert with access to the RPA Assessment database.

The database contains projections for land use changes across US counties from 2012-2100 under different climate scenarios.

KEY CONTEXT:
- Land use categories: crop, pasture, forest, urban, rangeland
- Scenarios combine climate (RCP45/85) and socioeconomic (SSP1-5) pathways
- Development is irreversible - once land becomes urban, it stays urban

DATABASE SCHEMA:
{schema_info}  # <-- Injected from constants.py

CRITICAL INSTRUCTION: ALWAYS EXECUTE ANALYTICAL QUERIES, NOT JUST DATA CHECKS!

When a user asks analytical questions like "compare forest loss across scenarios", you MUST:
1. Execute SQL queries that provide the actual comparison data
2. Show numerical results, not just confirm data exists
3. Analyze the differences between scenarios
4. Provide specific insights based on the actual numbers

IMPORTANT - GEOGRAPHIC QUERIES:
When users mention states by name or abbreviation:
1. Use the lookup_state_info tool to resolve the correct state_code (FIPS code)
2. The tool will return the proper SQL condition (e.g., "state_code = '06' -- California")
3. Use this in your WHERE clause
"""
```

### 2. **Analysis Style Variations**
```python
# Detailed analysis mode
DETAILED_ANALYSIS_PROMPT = """
DETAILED ANALYSIS MODE:
When providing results:
1. Include summary statistics (mean, median, std dev)
2. Identify outliers and anomalies
3. Suggest statistical significance where relevant
4. Provide confidence intervals if applicable
5. Compare results to historical baselines"""

# Executive summary mode
EXECUTIVE_SUMMARY_PROMPT = """
EXECUTIVE SUMMARY MODE:
When providing results:
1. Lead with the key finding in one sentence
2. Use user-friendly language (avoid technical jargon)
3. Focus on implications rather than raw numbers
4. Provide actionable insights
5. Keep responses concise (3-5 key points max)
6. Use the create_map tool when appropriate"""
```

### 3. **Domain Focus Specializations**
```python
# Agricultural analysis focus
AGRICULTURAL_FOCUS_PROMPT = """
AGRICULTURAL ANALYSIS FOCUS:
You are particularly focused on agricultural land use:
1. Pay special attention to Crop and Pasture transitions
2. Highlight food security implications
3. Consider agricultural productivity impacts
4. Note irrigation and water resource connections
5. Flag significant agricultural land losses (>10%)"""

# Climate scenario focus
CLIMATE_FOCUS_PROMPT = """
CLIMATE SCENARIO FOCUS:
You are analyzing climate impacts on land use:
1. Always compare RCP4.5 vs RCP8.5 scenarios
2. Highlight differences between SSP pathways
3. Emphasize climate-driven transitions
4. Note temperature and precipitation influences
5. Project long-term trends (2050, 2070, 2100)"""
```

### 4. **Optional Features** (Configuration-Driven)
```python
# Map generation (when enabled)
MAP_GENERATION_PROMPT = """
MAP GENERATION:
When results include geographic data (state_code), consider creating choropleth maps to visualize patterns.
Use the create_choropleth_map tool when appropriate.
Use the create_map tool when appropriate."""
```

## Configuration-Driven Prompt Assembly

```python
# In landuse_agent.py initialization:
from landuse.agents.prompts import get_system_prompt

# Agent assembles prompt based on configuration
self.system_prompt = get_system_prompt(
    include_maps=self.config.enable_map_generation,
    analysis_style=self.config.analysis_style,  # "standard", "detailed", "executive"
    domain_focus=None if self.config.domain_focus == 'none' else self.config.domain_focus,
    schema_info=self.schema
)

# Function signature from prompts.py:
def get_system_prompt(
    include_maps: bool = False,
    analysis_style: str = "standard",
    domain_focus: str = None,
    schema_info: str = ""
) -> str:
    """Generate a system prompt with the specified configuration."""
    prompt = SYSTEM_PROMPT_BASE.format(schema_info=schema_info)
    
    # Add analysis style modifications
    if analysis_style == "detailed":
        prompt += DETAILED_ANALYSIS_PROMPT
    elif analysis_style == "executive":
        prompt += EXECUTIVE_SUMMARY_PROMPT
    
    # Add domain focus if specified
    if domain_focus == "agricultural":
        prompt += AGRICULTURAL_FOCUS_PROMPT
    elif domain_focus == "climate":
        prompt += CLIMATE_FOCUS_PROMPT
    elif domain_focus == "urban":
        prompt += URBAN_PLANNING_PROMPT
    
    # Add map generation if enabled
    if include_maps:
        prompt += MAP_GENERATION_PROMPT
    
    return prompt
```

## Benefits of Modular Design

### Configuration Advantages
1. **Flexible Specialization**: Easy domain-specific customization
2. **Environment-Driven**: Behavior changes via configuration
3. **Reusability**: Shared prompt components across use cases
4. **Maintainability**: Centralized prompt management

### Development Benefits
1. **Version Control**: Clear prompt evolution tracking
2. **Testing**: Isolated prompt testing and validation
3. **Documentation**: Self-documenting prompt variations
4. **Extensibility**: Easy addition of new specializations

### Production Advantages
1. **Consistency**: Standardized prompt patterns
2. **Performance**: Pre-compiled prompt templates
3. **Monitoring**: Configuration-aware prompt selection
4. **Debugging**: Clear prompt composition visibility

## Integration with Configuration System

### Schema Integration
```python
# constants.py provides comprehensive schema documentation
SCHEMA_INFO_TEMPLATE = """
# RPA Land Use Transitions Database Schema
## Overview
This database contains USDA Forest Service 2020 RPA Assessment...
## RPA Scenarios Quick Reference
- **LM (RCP4.5-SSP1)**: Lower warming, moderate growth...
"""

# Injected into all prompt variations
prompt = SYSTEM_PROMPT_BASE.format(schema_info=SCHEMA_INFO_TEMPLATE)
```

### Configuration Mapping
```python
# LanduseConfig drives prompt selection
@dataclass
class LanduseConfig:
    analysis_style: str = "standard"  # → prompt variation
    domain_focus: str = "none"        # → domain specialization
    enable_map_generation: bool = True # → feature inclusion
    
# Automatic prompt assembly
system_prompt = get_system_prompt(
    analysis_style=config.analysis_style,
    domain_focus=config.domain_focus,
    include_maps=config.enable_map_generation,
    schema_info=SCHEMA_INFO_TEMPLATE
)
```

### Environment Variable Control
```bash
# Prompt behavior via environment
export LANDUSE_ANALYSIS_STYLE=detailed
export LANDUSE_DOMAIN_FOCUS=agricultural
export LANDUSE_ENABLE_MAPS=true

# Results in specialized agricultural analyst with detailed analysis and maps
```

## Customization and Extension Patterns

### 1. Pre-Built Variations (Recommended)
```python
# Use PromptVariations class for common patterns
from landuse.agents.prompts import PromptVariations

# Research analyst configuration
research_prompt = PromptVariations.research_analyst(schema_info)

# Policy maker configuration  
policy_prompt = PromptVariations.policy_maker(schema_info)

# Agricultural analyst configuration
agricultural_prompt = PromptVariations.agricultural_analyst(schema_info)
```

### 2. Custom Prompt Creation
```python
# Create fully custom prompts for specialized use cases
from landuse.agents.prompts import create_custom_prompt

custom_prompt = create_custom_prompt(
    expertise_area="water resource management",
    expertise_description="You understand connections between land use and water resources...",
    analysis_approach="1. Consider watershed boundaries\n2. Analyze impervious surface changes...",
    response_guidelines="1. Always mention water quality implications\n2. Note stormwater management needs...",
    schema_info=schema_info
)
```

### 3. Configuration-Based Customization
```python
# Environment-driven customization
config = LanduseConfig(
    analysis_style="executive",        # Concise, actionable insights
    domain_focus="climate",           # Climate scenario emphasis
    enable_map_generation=True        # Include visualization instructions
)

# Results in climate-focused executive summary agent with maps
agent = LanduseAgent(config)
```

### 4. Adding New Specializations
```python
# Extend prompts.py with new domain focus
WATER_RESOURCES_PROMPT = """
WATER RESOURCES FOCUS:
You are analyzing land use impacts on water resources:
1. Consider watershed boundaries and drainage patterns
2. Analyze impervious surface changes (urban expansion)
3. Note agricultural irrigation implications
4. Highlight stormwater management needs
5. Connect land use to water quality impacts
"""

# Add to get_system_prompt() function
if domain_focus == "water_resources":
    prompt += WATER_RESOURCES_PROMPT
```

## Summary

The modern system prompt architecture provides:

### Location and Structure
- **Primary Module**: `src/landuse/agents/prompts.py` (centralized prompt management)
- **Configuration Integration**: `LanduseConfig` drives prompt selection
- **Schema Integration**: `constants.py` provides domain knowledge
- **Agent Integration**: `landuse_agent.py` assembles configured prompt

### Key Components
1. **Base Template**: Core RPA analysis instructions
2. **Analysis Styles**: Standard, detailed, executive variations
3. **Domain Focus**: Agricultural, climate, urban specializations
4. **Feature Sections**: Map generation, knowledge base integration
5. **Pre-built Combinations**: Research analyst, policy maker, etc.

### Configuration Flow
```
Environment Variables → LanduseConfig → get_system_prompt() → Agent
```

### Benefits Over Legacy Approach
- **Discoverability**: Clear module organization
- **Maintainability**: Separated from business logic
- **Flexibility**: Configuration-driven behavior
- **Extensibility**: Easy addition of new specializations
- **Testing**: Isolated prompt validation
- **Documentation**: Self-documenting variations

This architecture enables both simple usage (`LanduseAgent()` with defaults) and sophisticated domain specialization while maintaining clear separation of concerns and production reliability.

## Related Documentation

### 🏠 **Agent System Hub**
- **[Agent System Overview](overview.md)** - Complete guide to the agent system with navigation to all sections

### 🔧 **Core Architecture**
- **[Agent Architecture](README.md)** - Complete system overview and implementation guide
- **[Configuration](CONSTANTS_ARCHITECTURE.md)** - How constants and configuration work together
- **[Tool System](TOOL_SYSTEM_ARCHITECTURE.md)** - Tool composition and factory patterns
- **[Memory & State](MEMORY_STATE_MANAGEMENT.md)** - LangGraph state management

### 🎯 **Prompt Customization**
- **[Advanced Configuration](ADVANCED_CONFIGURATION.md)** - Environment-based prompt configuration
- **[Integration & Extension](INTEGRATION_EXTENSION.md)** - Domain-specific agent specialization

### 📚 **API Reference**
- **[Main Agent API](../api/agent.md)** - LanduseAgent class documentation
- **[Query Capabilities](../api/landuse-query-agent.md)** - Natural language processing features