#!/usr/bin/env python3
"""
Landuse Natural Language Agent
Specialized agent for converting natural language queries about land use transitions
into optimized DuckDB SQL queries with business context and insights
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field

from dotenv import load_dotenv
from langchain.agents import create_react_agent, AgentExecutor
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import Tool
from langchain.prompts import PromptTemplate

from .base_agent import BaseLanduseAgent
from .constants import STATE_NAMES, SCHEMA_INFO_TEMPLATE, DEFAULT_ASSUMPTIONS
from .formatting import clean_sql_query, format_query_results

# Load environment variables from config/.env
load_dotenv("config/.env")
load_dotenv()  # Also load from root .env as fallback

class LanduseQueryParams(BaseModel):
    """Parameters for landuse database queries"""
    query: str = Field(..., description="Natural language query about landuse data")
    limit: Optional[int] = Field(50, description="Maximum number of rows to return")
    include_summary: Optional[bool] = Field(True, description="Include summary statistics")

class LanduseNaturalLanguageAgent(BaseLanduseAgent):
    """Natural Language to DuckDB SQL Agent for Landuse Data Analysis"""
    
    def __init__(self, db_path: Optional[str] = None, model_name: Optional[str] = None, 
                 temperature: float = 0.1, max_tokens: int = 2000):
        # Use environment variable or default if not provided
        if db_path is None:
            db_path = os.getenv('LANDUSE_DB_PATH', 'data/processed/landuse_analytics.duckdb')
        
        # Call parent constructor
        super().__init__(
            db_path=db_path,
            model_name=model_name or "claude-3-5-sonnet-20241022",
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Agent will be created by base class using our prompt
    
    def _create_tools(self) -> List[Tool]:
        """Create specialized tools for landuse queries"""
        return [
            Tool(
                name="execute_landuse_query",
                func=self._execute_landuse_query,
                description="🦆 Execute DuckDB SQL query on the landuse database. Input should be a SQL query string."
            ),
            Tool(
                name="get_schema_info",
                func=self._get_schema_help,
                description="📊 Get detailed schema information about the landuse database tables and relationships."
            ),
            Tool(
                name="suggest_query_examples",
                func=self._suggest_query_examples,
                description="💡 Get example queries for common landuse analysis patterns."
            ),
            Tool(
                name="explain_query_results",
                func=self._explain_query_results,
                description="📈 Explain and interpret query results in business context."
            ),
            Tool(
                name="get_default_assumptions",
                func=self._get_default_assumptions,
                description="📋 Get the default assumptions used when user doesn't specify scenarios, time periods, or geographic scope."
            )
        ]
    
    
    def _suggest_query_examples(self, category: str = "general") -> str:
        """Suggest example queries for common patterns"""
        examples = {
            "agricultural_loss": """
-- Agricultural land loss (default: averaged across all scenarios, full time period)
SELECT 
    AVG(f.acres) as avg_acres_lost_per_scenario,
    SUM(f.acres) as total_acres_lost,
    COUNT(DISTINCT s.scenario_id) as scenarios_included,
    MIN(t.start_year) as start_year,
    MAX(t.end_year) as end_year
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE fl.landuse_category = 'Agriculture' 
  AND tl.landuse_category != 'Agriculture'
  AND f.transition_type = 'change';
""",
            "urbanization": """
-- Urbanization pressure (default: averaged across scenarios, full time period)
SELECT 
    g.state_code,
    fl.landuse_name as from_landuse,
    AVG(f.acres) as avg_acres_urbanized_per_scenario,
    SUM(f.acres) as total_acres_urbanized,
    COUNT(DISTINCT s.scenario_id) as scenarios_included
FROM fact_landuse_transitions f
JOIN dim_geography g ON f.geography_id = g.geography_id
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE tl.landuse_name = 'Urban'
  AND f.transition_type = 'change'
GROUP BY g.state_code, fl.landuse_name
ORDER BY total_acres_urbanized DESC;
""",
            "climate_comparison": """
-- Compare RCP scenarios
SELECT 
    s.rcp_scenario,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
GROUP BY s.rcp_scenario, fl.landuse_name, tl.landuse_name
ORDER BY total_acres DESC;
""",
            "time_series": """
-- Time series of land use changes
SELECT 
    t.start_year,
    t.end_year,
    fl.landuse_name as from_landuse,
    tl.landuse_name as to_landuse,
    SUM(f.acres) as total_acres
FROM fact_landuse_transitions f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
WHERE f.transition_type = 'change'
GROUP BY t.start_year, t.end_year, fl.landuse_name, tl.landuse_name
ORDER BY t.start_year, total_acres DESC;
"""
        }
        
        if category.lower() in examples:
            return f"💡 **Example Query - {category.title()}:**\n```sql\n{examples[category.lower()]}\n```"
        
        result = "💡 **Common Query Examples:**\n\n"
        for name, sql in examples.items():
            result += f"**{name.replace('_', ' ').title()}:**\n```sql\n{sql}\n```\n\n"
        
        return result
    
    def _explain_query_results(self, results: str) -> str:
        """Explain query results in business context"""
        return """
📈 **Interpreting Landuse Transition Results:**

**Key Metrics to Look For:**
- **Large acre values**: Indicate significant land use changes
- **Crop ↔ Pasture**: Normal agricultural rotation
- **→ Urban transitions**: Development pressure
- **→ Forest transitions**: Conservation/reforestation efforts
- **RCP85 vs RCP45**: Higher emissions scenarios typically show more extreme changes
- **SSP5 vs SSP1**: Different socioeconomic pathways affect development patterns

**Business Insights:**
- High agricultural loss may indicate food security concerns
- Urban expansion shows development patterns
- Forest transitions indicate environmental policies
- State-level differences show regional trends
"""
    
    def _get_default_assumptions(self, query: str = "") -> str:
        """Get default assumptions used in analysis"""
        return """
📋 **Default Analysis Assumptions:**

When users don't specify certain parameters, the agent uses these intelligent defaults:

**🌡️ Climate Scenarios:**
- **Default**: Average across all 20 scenarios (mean outcome)
- **Rationale**: Provides typical/expected outcome rather than extreme cases
- **Available**: 20 scenarios covering RCP45/85 and SSP1/5 combinations

**📅 Time Periods:**
- **Default**: Full time range (2012-2100)
- **Rationale**: Shows complete transition picture over all available years
- **Available**: 6 time periods from 2012 to 2100

**🗺️ Geographic Scope:**
- **Default**: All US counties (3,075 counties)
- **Rationale**: National-level analysis unless user specifies states/regions
- **Available**: County-level (FIPS codes) and state-level aggregation

**🔄 Transition Types:**
- **Default**: Only 'change' transitions (excludes same-to-same)
- **Rationale**: Focus on actual land use changes, not static areas
- **Available**: 'change' and 'same' transition types

**📊 Example Default Query Pattern:**
```
SELECT 
    AVG(acres) as avg_acres_per_scenario,
    COUNT(DISTINCT scenario_id) as scenarios_included,
    MIN(start_year) as time_start,
    MAX(end_year) as time_end
FROM fact_landuse_transitions f
JOIN dim_scenario s ON f.scenario_id = s.scenario_id
JOIN dim_time t ON f.time_id = t.time_id
WHERE transition_type = 'change'
```

The agent will always clearly state which defaults were applied in each response.
"""
    
    def _get_agent_prompt(self) -> str:
        """Get the specialized prompt for landuse analysis"""
        return """
You are a specialized Landuse Data Analyst AI that converts natural language questions into DuckDB SQL queries for a landuse transitions database.

AVAILABLE TOOLS:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

DATABASE SCHEMA:
{schema_info}

INSTRUCTIONS:
1. When users ask questions about landuse data, convert them to appropriate SQL queries
2. Always use the star schema joins to get meaningful results
3. Focus on the most relevant metrics (acres, transition counts, geographic patterns)
4. Use appropriate aggregations (SUM, COUNT, AVG) and GROUP BY clauses
5. Add meaningful ORDER BY clauses to show most significant results first
6. Include appropriate LIMIT clauses for large datasets
7. Explain the business meaning of results
8. IMPORTANT: When using execute_landuse_query, provide ONLY the SQL query without markdown formatting (no ```sql or ```)

DEFAULT ASSUMPTIONS (apply when user doesn't specify):
- **Scenarios**: Use AVERAGE across all scenarios (represent typical/mean outcome)
- **Time Periods**: Use FULL time range (all years 2012-2100) 
- **Geographic Scope**: All states/counties unless specified
- **Transition Type**: Focus on 'change' transitions (exclude same-to-same)

ALWAYS CLEARLY STATE YOUR ASSUMPTIONS in the response, for example:
"📊 **Analysis Assumptions:**
- Scenarios: Averaged across all 20 climate scenarios (mean outcome)
- Time Period: Full range 2012-2100 (all available years)
- Geographic Scope: All US counties"

QUERY PATTERNS FOR COMMON QUESTIONS:
- "Agricultural land loss" → Agriculture → non-Agriculture transitions (DEFAULT: averaged across scenarios, full time period)
- "Forest loss" → Forest → non-Forest transitions (DEFAULT: averaged across scenarios, full time period)  
- "Urbanization" → Any → Urban transitions (DEFAULT: averaged across scenarios, full time period)
- "Climate scenarios" → Compare specific RCP/SSP scenarios (USER SPECIFIED)
- "State analysis" → Group by state_code (DEFAULT: all states unless specified)
- "Time trends" → Group by time periods (DEFAULT: full range unless specified)

EXAMPLE RESPONSES WITH DEFAULTS:
- User: "How much agricultural land is being lost?"
- Agent: "📊 **Analysis Assumptions:** Averaged across all 20 climate scenarios (mean outcome), Full time period 2012-2100, All US counties"

RESPONSE FORMAT:
1. First understand what the user is asking
2. Generate appropriate SQL query using execute_landuse_query
3. Interpret results in business context
4. Suggest follow-up analyses if relevant

Question: {input}
Thought: Let me understand what the user is asking about landuse data and convert it to an appropriate SQL query.
{agent_scratchpad}
"""
    
    
    def _show_chat_intro(self):
        """Show landuse-specific intro information"""
        # Show specialized examples for landuse queries
        from rich.panel import Panel
        
        examples_panel = Panel(
            """[bold cyan]🚀 Try these landuse-specific questions:[/bold cyan]

[yellow]Quick Analysis (uses smart defaults):[/yellow]
• "How much agricultural land is being lost?" [dim](averages all scenarios)[/dim]
• "What's the rate of forest loss?" [dim](full time period 2012-2100)[/dim]
• "How much urban expansion is happening?" [dim](all counties)[/dim]

[yellow]Agricultural Analysis:[/yellow]
• "Which scenarios show the most agricultural land loss?"
• "Show me crop to pasture transitions by state"
• "Compare agricultural changes in California vs Texas"

[yellow]Climate & Environment:[/yellow]
• "Compare forest loss between RCP45 and RCP85 scenarios"
• "Which states are seeing the most reforestation?"
• "What are the biggest land use changes over time?"

[yellow]Geographic Patterns:[/yellow]
• "Which states have the most urban expansion?"
• "Show me agricultural changes in California"
• "What are the top 10 counties for land use change?"

[bold green]💡 Smart Defaults:[/bold green]
[dim]When you don't specify scenarios/time periods, I'll use averages across all scenarios and the full time range, and clearly state my assumptions![/dim]""",
            title="🌾 Landuse-Specific Examples",
            border_style="blue"
        )
        self.console.print(examples_panel)

if __name__ == "__main__":
    # Create and run the landuse query agent
    agent = LanduseNaturalLanguageAgent()
    agent.chat() 