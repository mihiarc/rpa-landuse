#!/usr/bin/env python3
"""
Landuse Natural Language Agent - LangGraph Version
Specialized agent for natural language queries about land use data
"""

from typing import Any, Optional

from langchain_core.tools import tool
from rich.panel import Panel

from ..config import LanduseConfig
from ..models import StateCodeInput
from .constants import DEFAULT_ASSUMPTIONS, STATE_NAMES

# Create STATE_CODES as reverse mapping
STATE_CODES = {v: k for k, v in STATE_NAMES.items()}
from .langgraph_base_agent import BaseLangGraphAgent, BaseLanduseState


class NaturalLanguageState(BaseLanduseState):
    """Extended state for natural language agent"""
    default_assumptions_shown: bool = False


class LanduseNaturalLanguageAgent(BaseLangGraphAgent):
    """
    Specialized LangGraph agent for natural language queries about land use data.
    
    This agent extends the base LangGraph agent with:
    - Domain-specific prompts and knowledge
    - Additional tools for land use analysis
    - Smart default assumptions
    - Business context interpretation
    """
    
    def __init__(self, config: Optional[LanduseConfig] = None):
        """Initialize the natural language agent"""
        # Use 'basic' agent type if no config provided
        if config is None:
            config = LanduseConfig.for_agent_type('basic')
        
        super().__init__(config)
        self.logger.info("Natural language agent initialized with domain-specific tools")
    
    def _get_state_class(self):
        """Return the state class for this agent"""
        return NaturalLanguageState
    
    def _get_additional_initial_state(self) -> dict[str, Any]:
        """Add agent-specific initial state"""
        return {
            "default_assumptions_shown": False
        }
    
    def _get_system_prompt(self) -> str:
        """Get the specialized prompt for natural language land use analysis"""
        return f"""You are a specialized Landuse Data Analyst AI that converts natural language questions into DuckDB SQL queries.

DATABASE SCHEMA:
{self.schema_info}

KEY INSTRUCTIONS:
1. **ALWAYS execute SQL queries** to get real data - don't make up numbers
2. **GROUP BY Rule**: When using aggregate functions (SUM, COUNT, AVG), include ALL non-aggregate SELECT columns in GROUP BY
3. **ORDER BY Rule**: Only use columns that are either in SELECT list or are aggregated
4. **Common Pattern**: SELECT col1, col2, SUM(col3) ... GROUP BY col1, col2 ORDER BY col1

DEFAULT ASSUMPTIONS (apply these unless user specifies otherwise):
{DEFAULT_ASSUMPTIONS}

RESPONSE FORMAT:
1. First understand what data the user wants
2. Execute appropriate SQL query
3. Present results clearly with:
   - Summary statistics
   - Key insights
   - Context about what the numbers mean

EXAMPLE SQL PATTERNS:
- **Agricultural land by year**:
  ```sql
  SELECT t.year_range, SUM(f.acres) as total_ag_acres
  FROM fact_landuse_transitions f
  JOIN dim_landuse l ON f.to_landuse_id = l.landuse_id
  JOIN dim_time t ON f.time_id = t.time_id
  WHERE l.landuse_name IN ('Crop', 'Pasture') AND f.transition_type = 'same'
  GROUP BY t.year_range
  ORDER BY t.year_range
  ```

- **Forest loss by state**:
  ```sql
  SELECT g.state_name, SUM(f.acres) as forest_to_urban_acres
  FROM fact_landuse_transitions f
  JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
  JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
  JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
  WHERE fl.landuse_name = 'Forest' AND tl.landuse_name = 'Urban' AND f.transition_type = 'change'
  GROUP BY g.state_name
  ORDER BY forest_to_urban_acres DESC
  LIMIT 10
  ```

IMPORTANT REMINDERS:
- State codes: Texas='48', California='06', Florida='12', New York='36'
- Land use types: 'Crop', 'Pasture', 'Forest', 'Urban', 'Rangeland'
- For "agricultural" queries, include both 'Crop' AND 'Pasture'
- Transition types: 'same' (no change), 'change' (land use changed)

Remember to explain what the data means in business terms after showing the results."""
    
    def _get_additional_tools(self) -> list:
        """Add domain-specific tools for land use analysis"""
        
        @tool
        def explain_query_results(query_type: str, key_findings: str) -> str:
            """
            Explain query results in business context.
            
            Args:
                query_type: Type of query (e.g., 'forest_loss', 'agricultural', 'urbanization')
                key_findings: Key numerical findings to explain
            """
            explanations = {
                "forest_loss": "Forest loss typically indicates urbanization pressure or agricultural expansion. The 2020 RPA Assessment shows forest as the primary source for new development.",
                "agricultural": "Agricultural land (crops + pasture) changes reflect food security concerns and rural economic impacts. Loss of agricultural land is often irreversible.",
                "urbanization": "Urban expansion in the RPA projections is considered irreversible - once land becomes urban, it stays urban. This reflects historical development patterns.",
                "climate_scenarios": "RCP 4.5 represents moderate climate change, while RCP 8.5 is more severe. SSP scenarios represent different socioeconomic pathways affecting land use demand.",
                "transitions": "Land use transitions show the flow between categories. The most common transition is forest to urban, accounting for ~46% of new development."
            }
            
            base_explanation = explanations.get(query_type, "Land use changes reflect complex interactions between climate, policy, and economic factors.")
            
            return f"""📊 **Understanding Your Results:**

{base_explanation}

📈 **Your Key Findings:**
{key_findings}

💡 **Context:** These projections come from the 2020 RPA Assessment and represent potential futures based on different climate and socioeconomic scenarios."""
        
        @tool
        def get_default_assumptions() -> str:
            """Get the default assumptions used when user doesn't specify parameters."""
            return f"""🎯 **Default Assumptions Applied:**

{DEFAULT_ASSUMPTIONS}

💡 **Note:** These defaults help provide comprehensive results when specific parameters aren't mentioned. You can always override them by specifying what you want."""
        
        @tool
        def get_state_code(state_name: str) -> str:
            """
            Get the FIPS state code for a given state name.
            
            Args:
                state_name: Name of the state (e.g., 'Texas', 'California')
            """
            try:
                # Validate input
                input_data = StateCodeInput(state_name=state_name)
                state_name_clean = input_data.state_name.strip().title()
                
                # Check if it's already a code
                if state_name_clean in STATE_CODES.values():
                    # Find the code by value
                    for code, name in STATE_CODES.items():
                        if name == state_name_clean:
                            return f"State code for {state_name_clean}: '{code}'"
                
                # Look up the state code
                if state_name_clean in STATE_CODES.values():
                    # Find code by name
                    code = next(k for k, v in STATE_CODES.items() if v == state_name_clean)
                    return f"State code for {state_name_clean}: '{code}'"
                
                # Try to find partial matches
                matches = [(code, name) for code, name in STATE_CODES.items() 
                          if state_name_clean.lower() in name.lower()]
                
                if matches:
                    if len(matches) == 1:
                        return f"State code for {matches[0][1]}: '{matches[0][0]}'"
                    else:
                        return f"Multiple matches found: " + ", ".join([f"{name} ('{code}')" for code, name in matches])
                
                return f"❌ State '{state_name}' not found. Use full state names like 'Texas', 'California', etc."
                
            except Exception as e:
                return f"❌ Error looking up state: {str(e)}"
        
        return [explain_query_results, get_default_assumptions, get_state_code]
    
    def _show_chat_intro(self):
        """Show specialized intro for natural language agent"""
        intro_panel = Panel(
            """[bold cyan]Natural Language Interface[/bold cyan]
            
This agent specializes in converting your questions into data insights:
• Ask questions in plain English
• Automatic smart defaults for comprehensive analysis
• Business context and explanations included
• Focus on land use transitions and patterns

💡 [dim]Tip: The agent will explain default assumptions when relevant[/dim]""",
            title="🌾 Land Use Analytics",
            border_style="green"
        )
        self.console.print(intro_panel)
    
    def _post_query_hook(self, output: str, full_state: dict[str, Any]) -> str:
        """Add information about default assumptions if they were likely used"""
        # Check if the query was general enough that defaults were probably used
        original_query = full_state.get("current_query", "").lower()
        
        # Keywords that suggest specific parameters were NOT provided
        general_keywords = ["how much", "what is", "show me", "tell me", "analyze", "total", "overall"]
        specific_keywords = ["in 2050", "rcp45", "ssp1", "in texas", "by 2070", "scenario", "state"]
        
        # If query seems general and defaults not yet shown
        is_general = any(kw in original_query for kw in general_keywords)
        is_specific = any(kw in original_query for kw in specific_keywords)
        defaults_shown = full_state.get("default_assumptions_shown", False)
        
        if is_general and not is_specific and not defaults_shown:
            output += "\n\n💡 *Note: Default assumptions were applied. Use 'get_default_assumptions' tool to see details.*"
        
        return output


def main():
    """Main entry point for the natural language agent"""
    try:
        config = LanduseConfig.for_agent_type('basic')
        agent = LanduseNaturalLanguageAgent(config)
        agent.chat()
    except KeyboardInterrupt:
        print("\n👋 Happy analyzing!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()