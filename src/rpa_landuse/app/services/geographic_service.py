"""
Geographic service for handling map data and geographic operations.
"""

import json
import logging
from typing import Optional, Dict, Any
import requests
import streamlit as st

from ..config import (
    US_STATES_GEOJSON_URL,
    COUNTIES_GEOJSON_PATH,
    STATE_FIPS_TO_NAME,
    CACHE_TTL_HOURS
)

logger = logging.getLogger(__name__)


class GeographicService:
    """Service class for geographic data operations."""
    
    @staticmethod
    @st.cache_data(ttl=CACHE_TTL_HOURS)
    def load_us_states() -> Optional[Dict[str, Any]]:
        """
        Load US states geographic data without any projection system dependencies.
        
        Returns:
            GeoJSON data for US states or None if loading fails
        """
        # Method 1: Try to download remote GeoJSON and parse it directly
        try:
            st.info("Downloading US states geographic data...")
            
            # Download with SSL verification disabled
            response = requests.get(US_STATES_GEOJSON_URL, verify=False)
            response.raise_for_status()
            
            # Parse JSON directly - no GeoPandas needed for this step
            geojson_data = json.loads(response.text)
            
            st.success("✅ Downloaded US states data successfully.")
            return geojson_data  # Return raw GeoJSON for Folium
                
        except Exception as e:
            st.warning(f"Could not download remote states data: {e}")
            logger.warning(f"Failed to download remote states data: {e}")
        
        # Method 2: Try to read local counties and create states manually
        try:
            st.info("Creating states from local counties data...")
            
            if COUNTIES_GEOJSON_PATH.exists():
                # Read the file as plain JSON first
                with open(COUNTIES_GEOJSON_PATH, 'r') as f:
                    counties_geojson = json.load(f)
                
                # Group counties by state and create simplified state boundaries
                state_features = {}
                for feature in counties_geojson['features']:
                    state_fips = feature['properties']['STATE']
                    state_name = STATE_FIPS_TO_NAME.get(state_fips)
                    
                    if state_name:
                        if state_name not in state_features:
                            state_features[state_name] = {
                                "type": "Feature",
                                "properties": {"name": state_name},
                                "geometry": {
                                    "type": "MultiPolygon",
                                    "coordinates": []
                                }
                            }
                        
                        # Add county geometry to state (simplified approach)
                        geom = feature['geometry']
                        if geom['type'] == 'Polygon':
                            state_features[state_name]['geometry']['coordinates'].append(geom['coordinates'])
                        elif geom['type'] == 'MultiPolygon':
                            state_features[state_name]['geometry']['coordinates'].extend(geom['coordinates'])
                
                # Create final GeoJSON
                states_geojson = {
                    "type": "FeatureCollection",
                    "features": list(state_features.values())
                }
                
                st.success("✅ Created states from local counties data.")
                return states_geojson
                
        except Exception as e:
            st.warning(f"Could not create states from counties: {e}")
            logger.warning(f"Failed to create states from counties: {e}")
        
        # Method 3: Create a minimal hardcoded states GeoJSON
        try:
            st.info("Using minimal hardcoded states data...")
            
            # Create basic rectangular boundaries for major states
            minimal_states = {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"name": "California"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-124.0, 42.0], [-114.0, 42.0], [-114.0, 32.0], [-124.0, 32.0], [-124.0, 42.0]]]
                        }
                    },
                    {
                        "type": "Feature",
                        "properties": {"name": "Texas"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-106.0, 36.0], [-94.0, 36.0], [-94.0, 25.0], [-106.0, 25.0], [-106.0, 36.0]]]
                        }
                    },
                    {
                        "type": "Feature",
                        "properties": {"name": "Florida"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-87.0, 31.0], [-80.0, 31.0], [-80.0, 24.0], [-87.0, 24.0], [-87.0, 31.0]]]
                        }
                    },
                    {
                        "type": "Feature",
                        "properties": {"name": "New York"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-79.0, 45.0], [-71.0, 45.0], [-71.0, 40.0], [-79.0, 40.0], [-79.0, 45.0]]]
                        }
                    },
                    {
                        "type": "Feature",
                        "properties": {"name": "Illinois"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-91.0, 42.5], [-87.0, 42.5], [-87.0, 37.0], [-91.0, 37.0], [-91.0, 42.5]]]
                        }
                    }
                ]
            }
            
            st.info("✅ Using minimal geographic data (5 major states).")
            st.warning("⚠️ Limited to 5 major states due to system issues.")
            return minimal_states
            
        except Exception as e:
            st.warning(f"Minimal approach failed: {e}")
            logger.error(f"All geographic data loading methods failed: {e}")
        
        # Final fallback: return None to disable mapping
        st.error("❌ Geographic mapping is currently unavailable due to data loading issues.")
        st.info("The data table will still be available below.")
        return None 