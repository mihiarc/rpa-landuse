#!/usr/bin/env python3
"""
Enhanced LangGraph Map Agent - Unified Architecture
Combines natural language processing with map generation capabilities
"""

from pathlib import Path
from typing import Any, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from rich.panel import Panel

from ..config import LanduseConfig
from ..tools.map_generation_tool import create_map_generation_tool
from .landuse_natural_language_agent_v2 import LanduseNaturalLanguageAgent, NaturalLanguageState


class MapAgentState(NaturalLanguageState):
    """Extended state for map-capable agent"""
    generated_maps: list[dict[str, Any]]
    visualization_requested: bool


class LangGraphMapAgent(LanduseNaturalLanguageAgent):
    """
    Enhanced LangGraph agent that extends natural language capabilities with map generation.
    
    This unified agent provides:
    - All natural language query capabilities
    - Map generation for states, regions, and transitions
    - Automatic visualization suggestions
    - Integrated response formatting with map links
    """
    
    def __init__(self, config: Optional[LanduseConfig] = None):
        """Initialize the map-enabled agent"""
        # Use 'map' agent type configuration
        if config is None:
            config = LanduseConfig.for_agent_type('map')
        
        # Ensure map generation is enabled
        config.enable_map_generation = True
        
        # Create map output directory
        self.map_output_dir = Path(config.map_output_dir)
        self.map_output_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize parent class
        super().__init__(config)
        
        self.logger.info("Map agent initialized with visualization capabilities")
    
    def _get_state_class(self):
        """Return the extended state class for map agent"""
        return MapAgentState
    
    def _get_additional_initial_state(self) -> dict[str, Any]:
        """Add map-specific initial state"""
        parent_state = super()._get_additional_initial_state()
        parent_state.update({
            "generated_maps": [],
            "visualization_requested": False
        })
        return parent_state
    
    def _get_system_prompt(self) -> str:
        """Get the enhanced system prompt with map capabilities"""
        # Get base prompt from parent
        base_prompt = super()._get_system_prompt()
        
        # Add map-specific instructions
        map_instructions = """

MAP GENERATION CAPABILITIES:
You can create visualizations using the generate_landuse_map tool:
- **state_counties**: County-level maps for specific states (e.g., "Texas forest coverage by county")
- **regional**: Regional maps showing all states (e.g., "National urban distribution")
- **transitions**: Maps showing land use changes (e.g., "Forest to urban transitions")

WHEN TO GENERATE MAPS:
1. User explicitly asks for a map, visualization, or to "show" something
2. Geographic patterns would benefit from visualization
3. Comparing states or regions
4. Showing spatial distribution of land use

MAP INTEGRATION:
- Always mention generated map files in your response
- Explain what the map shows
- Suggest maps when they would enhance understanding
- Include map file paths so users can view them"""
        
        return base_prompt + map_instructions
    
    def _get_additional_tools(self) -> list:
        """Add map generation tool to the parent's tools"""
        # Get parent tools
        parent_tools = super()._get_additional_tools()
        
        # Add map generation tool
        map_tool = create_map_generation_tool(
            str(self.db_path),
            str(self.map_output_dir)
        )
        
        # Also create a tool to check if visualization would be helpful
        @tool
        def suggest_visualization(query_context: str, data_summary: str) -> str:
            """
            Suggest whether a visualization would be helpful for the current analysis.
            
            Args:
                query_context: What the user is asking about
                data_summary: Summary of the data/results
            """
            # Keywords that suggest visualization would help
            spatial_keywords = ['state', 'county', 'geographic', 'where', 'location', 'distribution']
            comparison_keywords = ['compare', 'versus', 'between', 'difference']
            pattern_keywords = ['pattern', 'trend', 'cluster', 'concentration']
            
            context_lower = query_context.lower()
            
            # Check if visualization would be helpful
            reasons = []
            if any(kw in context_lower for kw in spatial_keywords):
                reasons.append("spatial distribution")
            if any(kw in context_lower for kw in comparison_keywords):
                reasons.append("visual comparison")
            if any(kw in context_lower for kw in pattern_keywords):
                reasons.append("pattern identification")
            
            if reasons:
                return f"📊 A map visualization would help show {', '.join(reasons)}. Consider using generate_landuse_map tool."
            
            return "📊 The data is well-represented in tabular format."
        
        return parent_tools + [map_tool, suggest_visualization]
    
    def _show_chat_intro(self):
        """Show enhanced intro with map examples"""
        intro_panel = Panel(
            """[bold cyan]Natural Language + Map Visualization[/bold cyan]
            
This enhanced agent combines data analysis with visualization:
• All natural language query capabilities
• 🗺️ Automatic map generation when helpful
• 📊 County, state, and regional visualizations
• 🔄 Land use transition mapping

[yellow]Example queries with maps:[/yellow]
• "Show me forest coverage in Texas"
• "Visualize urban expansion in California counties"
• "Map agricultural land changes nationally"
• "Display forest to urban transitions"

💡 [dim]Maps are saved to: output/maps/[/dim]""",
            title="🌾 Land Use Analytics with Maps",
            border_style="green"
        )
        self.console.print(intro_panel)
    
    def _post_query_hook(self, output: str, full_state: dict[str, Any]) -> str:
        """Process output to include map information"""
        # First apply parent's post-processing
        output = super()._post_query_hook(output, full_state)
        
        # Check for generated maps in the state
        messages = full_state.get("messages", [])
        map_paths = []
        
        # Look for map generation tool calls and their results
        for i, msg in enumerate(messages):
            if hasattr(msg, 'tool_calls'):
                for tool_call in msg.tool_calls:
                    if tool_call.get('name') == 'generate_landuse_map':
                        # Look for the corresponding tool response
                        if i + 1 < len(messages):
                            tool_response = messages[i + 1]
                            if hasattr(tool_response, 'content'):
                                # Parse the response for map path
                                content = tool_response.content
                                if "Map saved to:" in content:
                                    start = content.find("Map saved to:") + 13
                                    end = content.find("\n", start) if "\n" in content[start:] else len(content)
                                    map_path = content[start:end].strip()
                                    map_paths.append(map_path)
        
        # Add map information if maps were generated
        if map_paths and "Generated Visualizations:" not in output:
            output += "\n\n📊 **Generated Visualizations:**\n"
            for path in map_paths:
                output += f"- Map saved to: `{path}`\n"
        
        return output


def main():
    """Main entry point for the enhanced map agent"""
    try:
        config = LanduseConfig.for_agent_type('map')
        agent = LangGraphMapAgent(config)
        agent.chat()
    except KeyboardInterrupt:
        print("\n👋 Happy analyzing!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()