"""
Map Generation Tool for LangGraph Agent
Enables the agent to create various types of maps based on user queries
"""

import datetime
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Literal, Optional

import duckdb
import geopandas as gpd
import matplotlib
import pandas as pd
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from shapely import wkt

from landuse.utilities.state_mappings import StateMapper

matplotlib.use('Agg')  # Use non-GUI backend for threading safety
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class MapRequest(BaseModel):
    """Schema for map generation requests"""
    map_type: Literal["state_counties", "regional", "national", "transitions", "scenario_comparison"] = Field(
        description="Type of map to generate"
    )
    state_name: Optional[str] = Field(
        default=None,
        description="State name for state-level maps (e.g., 'Texas', 'California')"
    )
    landuse_type: Optional[str] = Field(
        default="Forest",
        description="Land use type to visualize: 'Forest', 'Urban', 'Crop', 'Pasture', 'Rangeland'"
    )
    from_landuse: Optional[str] = Field(
        default=None,
        description="Source land use type for transition maps"
    )
    to_landuse: Optional[str] = Field(
        default=None,
        description="Target land use type for transition maps"
    )
    scenario: Optional[str] = Field(
        default=None,
        description="Climate scenario name (if not specified, uses first available)"
    )
    time_period: Optional[str] = Field(
        default=None,
        description="Time period (e.g., '2060-2070'). If not specified, uses latest."
    )
    output_format: Literal["png", "html"] = Field(
        default="png",
        description="Output format for the map"
    )


class MapGenerationTool:
    """Tool for generating various land use maps"""

    def __init__(self, db_path: str, output_dir: Optional[str] = None):
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir) if output_dir else Path("maps/agent_generated")
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def _get_db_connection(self):
        """Get DuckDB connection with spatial extension"""
        conn = duckdb.connect(str(self.db_path), read_only=True)
        conn.execute("INSTALL spatial")
        conn.execute("LOAD spatial")
        return conn

    def _generate_filename(self, map_type: str, **kwargs) -> str:
        """Generate a unique filename for the map"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        parts = [map_type, timestamp]

        if kwargs.get('state_name'):
            parts.insert(1, kwargs['state_name'].lower().replace(' ', '_'))
        if kwargs.get('landuse_type'):
            parts.insert(1, kwargs['landuse_type'].lower())

        return "_".join(parts)

    def create_state_county_map(self, state_name: str, landuse_type: str = "Forest",
                               scenario: Optional[str] = None, time_period: Optional[str] = None) -> dict[str, Any]:
        """Create a county-level map for a specific state"""
        conn = self._get_db_connection()

        try:
            # Get default scenario and time period if not specified
            if not scenario:
                scenario = conn.execute("SELECT scenario_name FROM dim_scenario ORDER BY scenario_name LIMIT 1").fetchone()[0]
            if not time_period:
                time_period = conn.execute("SELECT year_range FROM dim_time ORDER BY end_year DESC LIMIT 1").fetchone()[0]

            # Query county data with geometries
            query = """
                WITH county_landuse AS (
                    SELECT
                        g.fips_code,
                        g.county_name,
                        g.state_name,
                        ST_AsText(g.geometry) as geometry_wkt,
                        g.area_sqmi,
                        SUM(CASE WHEN l.landuse_name = ? THEN f.acres ELSE 0 END) as landuse_acres,
                        SUM(f.acres) as total_acres
                    FROM dim_geography_enhanced g
                    JOIN fact_landuse_transitions f ON g.geography_id = f.geography_id
                    JOIN dim_landuse l ON f.to_landuse_id = l.landuse_id
                    JOIN dim_scenario s ON f.scenario_id = s.scenario_id
                    JOIN dim_time t ON f.time_id = t.time_id
                    WHERE g.state_name = ?
                        AND g.geometry IS NOT NULL
                        AND s.scenario_name = ?
                        AND t.year_range = ?
                        AND f.transition_type = 'same'
                    GROUP BY g.fips_code, g.county_name, g.state_name, g.geometry, g.area_sqmi
                )
                SELECT
                    *,
                    ROUND(100.0 * landuse_acres / total_acres, 2) as landuse_pct
                FROM county_landuse
            """

            df = conn.execute(query, [landuse_type, state_name, scenario, time_period]).fetchdf()
            conn.close()

            if df.empty:
                return {
                    "success": False,
                    "error": f"No data found for {state_name}",
                    "map_path": None
                }

            # Convert to GeoDataFrame
            df['geometry'] = df['geometry_wkt'].apply(wkt.loads)
            gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:4326')

            # Create map
            fig, ax = plt.subplots(1, 1, figsize=(12, 10))

            # Plot counties
            gdf.plot(column='landuse_pct',
                    cmap='YlOrRd' if landuse_type == 'Urban' else 'Greens',
                    linewidth=0.5,
                    edgecolor='white',
                    ax=ax,
                    legend=True,
                    legend_kwds={'label': f'{landuse_type} Land Use (%)',
                                'orientation': 'horizontal',
                                'pad': 0.05})

            # Add county boundaries
            gdf.boundary.plot(ax=ax, linewidth=0.2, edgecolor='gray')

            # Set title and clean up
            ax.set_title(f'{state_name} - {landuse_type} Land Use by County\n{scenario} | {time_period}',
                        fontsize=14, fontweight='bold', pad=20)
            ax.axis('off')

            plt.tight_layout()

            # Save map
            filename = self._generate_filename("county_map", state_name=state_name, landuse_type=landuse_type)
            output_path = self.output_dir / f"{filename}.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()

            return {
                "success": True,
                "map_path": str(output_path),
                "map_type": "state_county",
                "state": state_name,
                "landuse_type": landuse_type,
                "scenario": scenario,
                "time_period": time_period,
                "description": f"County-level {landuse_type} land use map for {state_name}"
            }

        except Exception as e:
            conn.close()
            return {
                "success": False,
                "error": str(e),
                "map_path": None
            }

    def create_regional_map(self, landuse_type: str = "Forest") -> dict[str, Any]:
        """Create a regional map showing land use by state"""
        conn = self._get_db_connection()

        try:
            # Get state-level data
            query = """
                WITH state_landuse AS (
                    SELECT
                        g.state_code,
                        g.state_name,
                        g.region,
                        SUM(CASE WHEN l.landuse_name = ? THEN f.acres ELSE 0 END) as landuse_acres,
                        SUM(f.acres) as total_acres
                    FROM fact_landuse_transitions f
                    JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
                    JOIN dim_landuse l ON f.to_landuse_id = l.landuse_id
                    JOIN dim_scenario s ON f.scenario_id = s.scenario_id
                    JOIN dim_time t ON f.time_id = t.time_id
                    WHERE g.state_name IS NOT NULL
                        AND f.transition_type = 'same'
                        AND s.scenario_name = (SELECT scenario_name FROM dim_scenario LIMIT 1)
                        AND t.year_range = (SELECT year_range FROM dim_time ORDER BY end_year DESC LIMIT 1)
                    GROUP BY g.state_code, g.state_name, g.region
                )
                SELECT
                    state_code,
                    state_name,
                    region,
                    ROUND(100.0 * landuse_acres / total_acres, 2) as landuse_pct
                FROM state_landuse
            """

            df = conn.execute(query, [landuse_type]).fetchdf()
            conn.close()

            # Convert state codes to abbreviations using centralized mapper
            df['state_abbrev'] = df['state_code'].map(StateMapper.FIPS_TO_ABBREV)

            # Create choropleth map
            fig = px.choropleth(
                df,
                locations='state_abbrev',
                locationmode='USA-states',
                color='landuse_pct',
                scope='usa',
                title=f'{landuse_type} Land Use by State and Region',
                color_continuous_scale='Greens' if landuse_type == 'Forest' else 'YlOrRd',
                labels={'landuse_pct': f'{landuse_type} %'},
                hover_data=['state_name', 'region']
            )

            fig.update_layout(
                width=1000,
                height=600,
                geo={
                    'showlakes': True,
                    'lakecolor': 'rgb(255, 255, 255)'
                }
            )

            # Save map
            filename = self._generate_filename("regional_map", landuse_type=landuse_type)
            output_path = self.output_dir / f"{filename}.png"
            fig.write_image(str(output_path), width=1000, height=600, scale=2)

            return {
                "success": True,
                "map_path": str(output_path),
                "map_type": "regional",
                "landuse_type": landuse_type,
                "description": f"Regional {landuse_type} land use map showing all US states"
            }

        except Exception as e:
            conn.close()
            return {
                "success": False,
                "error": str(e),
                "map_path": None
            }

    def create_transition_map(self, from_landuse: str, to_landuse: str,
                            state_name: Optional[str] = None) -> dict[str, Any]:
        """Create a map showing land use transitions"""
        conn = self._get_db_connection()

        try:
            # Build query based on whether state is specified
            base_query = """
                SELECT
                    g.state_code,
                    g.state_name,
                    SUM(f.acres) as transition_acres
                FROM fact_landuse_transitions f
                JOIN dim_geography_enhanced g ON f.geography_id = g.geography_id
                JOIN dim_landuse fl ON f.from_landuse_id = fl.landuse_id
                JOIN dim_landuse tl ON f.to_landuse_id = tl.landuse_id
                JOIN dim_scenario s ON f.scenario_id = s.scenario_id
                JOIN dim_time t ON f.time_id = t.time_id
                WHERE fl.landuse_name = ?
                    AND tl.landuse_name = ?
                    AND f.transition_type = 'change'
                    AND g.state_name IS NOT NULL
                    AND t.year_range = '2060-2070'
            """

            params = [from_landuse, to_landuse]
            if state_name:
                base_query += " AND g.state_name = ?"
                params.append(state_name)

            base_query += " GROUP BY g.state_code, g.state_name HAVING transition_acres > 0"

            df = conn.execute(base_query, params).fetchdf()
            conn.close()

            if df.empty:
                return {
                    "success": False,
                    "error": f"No transitions found from {from_landuse} to {to_landuse}",
                    "map_path": None
                }

            # Create appropriate map based on scope
            if state_name:
                # County-level map for state
                return self._create_state_transition_map(df, from_landuse, to_landuse, state_name)
            else:
                # National map
                return self._create_national_transition_map(df, from_landuse, to_landuse)

        except Exception as e:
            conn.close()
            return {
                "success": False,
                "error": str(e),
                "map_path": None
            }

    def _create_national_transition_map(self, df: pd.DataFrame, from_landuse: str,
                                      to_landuse: str) -> dict[str, Any]:
        """Create national transition map"""
        # Convert state codes to abbreviations using centralized mapper
        df['state_abbrev'] = df['state_code'].map(StateMapper.FIPS_TO_ABBREV)

        fig = px.choropleth(
            df,
            locations='state_abbrev',
            locationmode='USA-states',
            color='transition_acres',
            scope='usa',
            title=f'Projected {from_landuse} to {to_landuse} Transitions (2060-2070)',
            color_continuous_scale='Reds',
            labels={'transition_acres': 'Acres Converting'},
            hover_data=['state_name']
        )

        fig.update_layout(
            width=1000,
            height=600,
            geo={
                'showlakes': True,
                'lakecolor': 'rgb(255, 255, 255)'
            }
        )

        # Save map
        filename = self._generate_filename("transition_map",
                                         from_landuse=from_landuse,
                                         to_landuse=to_landuse)
        output_path = self.output_dir / f"{filename}.png"
        fig.write_image(str(output_path), width=1000, height=600, scale=2)

        return {
            "success": True,
            "map_path": str(output_path),
            "map_type": "transitions",
            "from_landuse": from_landuse,
            "to_landuse": to_landuse,
            "scope": "national",
            "description": f"National map showing {from_landuse} to {to_landuse} transitions"
        }


def create_map_generation_tool(db_path: str, output_dir: Optional[str] = None):
    """Factory function to create the map generation tool for LangGraph"""
    map_tool = MapGenerationTool(db_path, output_dir)

    @tool(response_format="content_and_artifact")
    def generate_landuse_map(
        map_type: Literal["state_counties", "regional", "national", "transitions", "scenario_comparison"],
        state_name: Optional[str] = None,
        landuse_type: Optional[str] = "Forest",
        from_landuse: Optional[str] = None,
        to_landuse: Optional[str] = None,
        scenario: Optional[str] = None,
        time_period: Optional[str] = None
    ) -> tuple[str, dict[str, Any]]:
        """
        Generate various types of land use maps based on the database data.

        Args:
            map_type: Type of map to generate
                - "state_counties": County-level map for a specific state
                - "regional": Regional map showing all states
                - "transitions": Map showing land use transitions
            state_name: State name for state-level maps (e.g., 'Texas', 'California')
            landuse_type: Land use type to visualize ('Forest', 'Urban', 'Crop', 'Pasture', 'Rangeland')
            from_landuse: Source land use type for transition maps
            to_landuse: Target land use type for transition maps
            scenario: Climate scenario name (optional)
            time_period: Time period (optional, e.g., '2060-2070')

        Returns:
            Tuple of (content for model, artifact with map data)
        """
        try:
            request = MapRequest(
                map_type=map_type,
                state_name=state_name,
                landuse_type=landuse_type,
                from_landuse=from_landuse,
                to_landuse=to_landuse,
                scenario=scenario,
                time_period=time_period
            )

            # Generate appropriate map based on type
            if map_type == "state_counties":
                if not state_name:
                    error_msg = "state_name is required for state_counties map type"
                    return error_msg, {"success": False, "error": error_msg}
                result = map_tool.create_state_county_map(
                    state_name, landuse_type, scenario, time_period
                )
            elif map_type == "regional":
                result = map_tool.create_regional_map(landuse_type)
            elif map_type == "transitions":
                if not from_landuse or not to_landuse:
                    error_msg = "from_landuse and to_landuse are required for transition maps"
                    return error_msg, {"success": False, "error": error_msg}
                result = map_tool.create_transition_map(from_landuse, to_landuse, state_name)
            else:
                error_msg = f"Unsupported map type: {map_type}"
                return error_msg, {"success": False, "error": error_msg}

            # Format response for model and artifact
            if result['success']:
                content = f"✅ Successfully generated {result.get('description', 'map')}. The map has been saved to: {result['map_path']}"
                return content, result
            else:
                content = f"❌ Failed to generate map: {result.get('error', 'Unknown error')}"
                return content, result

        except Exception as e:
            error_msg = f"Error generating map: {str(e)}"
            return error_msg, {
                "success": False,
                "error": str(e),
                "map_path": None
            }

    return generate_landuse_map
