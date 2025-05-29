"""Map builder for the Hawaii Appleseed Dashboard."""
import folium
import logging
import traceback
import json
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class MapBuilder:
    """Builds and configures the Folium map with layers."""
    
    def __init__(self, active_layers: Optional[List[str]] = None):
        self.active_layers = active_layers or ['State']
        self.m = None
        self.base_dir = Path(__file__).parent.parent.parent
        self.feature_groups: Dict[str, folium.FeatureGroup] = {}
        
    def _add_state_boundary(self) -> None:
        """Add Hawaii state boundary to the map with hover highlighting."""
        try:
            state_geojson_path = self.base_dir / 'data' / 'Processed GeoJsons' / 'hawaii_state_boundary.geojson'
            
            if not state_geojson_path.exists():
                logger.error(f"State boundary GeoJSON not found at {state_geojson_path}")
                return
            
            # Base style
            def style_function(feature):
                return {
                    'fillColor': '#ffffff',
                    'color': '#000000',
                    'weight': 2,
                    'fillOpacity': 0.1
                }
                
            # Create the GeoJSON layer with highlighting
            geojson = folium.GeoJson(
                data=json.loads(state_geojson_path.read_text()),
                style_function=style_function,
                highlight_function=lambda x: {
                    'fillColor': '#ffffff',
                    'color': '#000000',
                    'weight': 4,
                    'fillOpacity': 0.3
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['state_name'],
                    aliases=['State:'],
                    style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 2px;")
                ),
                name='State Boundary'
            )
            
            # Add to the feature group
            geojson.add_to(self.feature_groups['state'])
            logger.info("Successfully added state boundary layer")
            
        except Exception as e:
            logger.error(f"Error adding state boundary: {str(e)}")
            logger.error(traceback.format_exc())
            
    def _add_county_boundaries(self) -> None:
        """Add county boundaries to the map with hover highlighting."""
        try:
            county_geojson_path = self.base_dir / 'data' / 'Processed GeoJsons' / 'hawaii_county_boundaries.geojson'
            
            if not county_geojson_path.exists():
                logger.error(f"County boundaries GeoJSON not found at {county_geojson_path}")
                return
            
            # Base style
            def style_function(feature):
                return {
                    'fillColor': '#f7f7f7',
                    'color': '#666666',
                    'weight': 1,
                    'fillOpacity': 0.3,
                    'dashArray': '5, 5'
                }
                
            # Highlight style
            def highlight_function(feature):
                return {
                    'fillColor': '#e0e0e0',
                    'color': '#333333',
                    'weight': 2.5,
                    'fillOpacity': 0.5,
                    'dashArray': '5, 5'
                }
            
            # Create the GeoJSON layer with highlighting
            geojson = folium.GeoJson(
                data=json.loads(county_geojson_path.read_text()),
                style_function=style_function,
                highlight_function=lambda x: {
                    'fillColor': '#e0e0e0',
                    'color': '#333333',
                    'weight': 2.5,
                    'fillOpacity': 0.5,
                    'dashArray': '5, 5'
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['county_name', 'county_fips'],
                    aliases=['County: ', 'FIPS Code: '],
                    style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 2px;")
                )
            )
            
            # Add to the feature group
            geojson.add_to(self.feature_groups['counties'])
            
            logger.info("Successfully added county boundaries layer")
            
        except Exception as e:
            logger.error(f"Error adding county boundaries: {str(e)}")
            logger.error(traceback.format_exc())
            
    def _add_house_districts(self) -> None:
        """Add state house districts to the map with hover highlighting."""
        try:
            house_geojson_path = self.base_dir / 'data' / 'Processed GeoJsons' / 'Hawaii_State_House_Districts_2022.geojson'
            
            if not house_geojson_path.exists():
                logger.error(f"House districts GeoJSON not found at {house_geojson_path}")
                return
            
            # Base style
            def style_function(feature):
                return {
                    'fillColor': '#9ecae1',
                    'color': '#3182bd',
                    'weight': 1,
                    'fillOpacity': 0.4,
                    'dashArray': '3, 3'
                }
                
            # Create the GeoJSON layer with highlighting
            geojson = folium.GeoJson(
                data=json.loads(house_geojson_path.read_text()),
                style_function=style_function,
                highlight_function=lambda x: {
                    'fillColor': '#6baed6',
                    'color': '#2171b5',
                    'weight': 2.5,
                    'fillOpacity': 0.7,
                    'dashArray': '3, 3'
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['state_house', 'house_name'],
                    aliases=['District: ', 'Representative: '],
                    style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 2px;")
                )
            )
            
            # Add to the feature group
            geojson.add_to(self.feature_groups['house_districts'])
            
            logger.info("Successfully added state house districts layer")
            
        except Exception as e:
            logger.error(f"Error adding house districts: {str(e)}")
            logger.error(traceback.format_exc())
            
    def _add_senate_districts(self) -> None:
        """Add state senate districts to the map with hover highlighting."""
        try:
            senate_geojson_path = self.base_dir / 'data' / 'Processed GeoJsons' / 'Hawaii_State_Senate_Districts_2022.geojson'
            
            if not senate_geojson_path.exists():
                logger.error(f"Senate districts GeoJSON not found at {senate_geojson_path}")
                return
            
            # Base style
            def style_function(feature):
                return {
                    'fillColor': '#a1d99b',
                    'color': '#31a354',
                    'weight': 1.5,
                    'fillOpacity': 0.3,
                    'dashArray': '4, 4'
                }
                
            # Create the GeoJSON layer with highlighting
            geojson = folium.GeoJson(
                data=json.loads(senate_geojson_path.read_text()),
                style_function=style_function,
                highlight_function=lambda x: {
                    'fillColor': '#74c476',
                    'color': '#238b45',
                    'weight': 2.5,
                    'fillOpacity': 0.6,
                    'dashArray': '4, 4'
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['state_senate', 'senate_name'],
                    aliases=['District: ', 'Name: '],
                    style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 2px;")
                )
            )
            
            # Add to the feature group
            geojson.add_to(self.feature_groups['senate_districts'])
            
            logger.info("Successfully added state senate districts layer")
            
        except Exception as e:
            logger.error(f"Error adding senate districts: {str(e)}")
            logger.error(traceback.format_exc())
    
    def create_map(self) -> folium.Map:
        """Create and return a map with configured layers."""
        try:
            # Define bounds for Hawaii (southwest and northeast corners)
            hawaii_bounds = [
                [18.9, -160.2],  # Southwest coordinates
                [22.2, -154.8]    # Northeast coordinates
            ]
            
            # Create a basic map centered on Hawaii with CartoDB tiles
            self.m = folium.Map(
                location=[20.8, -157.3],  # Center of Hawaii
                zoom_start=7,             # Reasonable zoom level for Hawaii
                tiles='CartoDB Positron',  # Use CartoDB Positron tiles
                control_scale=True,
                min_zoom=6,               # Prevent zooming out too far
                max_bounds=True,           # Restrict panning to these bounds
                max_bounds_viscosity=1.0,  # Strict bounds enforcement
                prefer_canvas=True,        # Better performance
                zoom_control=True          # Enable zoom controls
            )
            
            # Set the map bounds to Hawaii
            self.m.fit_bounds(hawaii_bounds)
            
            # Create feature groups for each layer type
            self._create_feature_groups()
            
            # Add layers based on active layers
            if 'State' in self.active_layers:
                self._add_state_boundary()
            if 'Counties' in self.active_layers:
                self._add_county_boundaries()
            if 'House' in self.active_layers:
                self._add_house_districts()
            if 'Senate' in self.active_layers:
                self._add_senate_districts()
            
            # Only add the base layer and active feature groups to the map
            self.feature_groups['base'].add_to(self.m)  # Always add base layer
            
            # Add only the active layers
            for layer_name, group in self.feature_groups.items():
                if layer_name != 'base':  # Skip base layer as it's already added
                    if layer_name in ['state', 'counties', 'house_districts', 'senate_districts']:
                        if (layer_name == 'state' and 'State' in self.active_layers) or \
                           (layer_name == 'counties' and 'Counties' in self.active_layers) or \
                           (layer_name == 'house_districts' and 'House' in self.active_layers) or \
                           (layer_name == 'senate_districts' and 'Senate' in self.active_layers):
                            group.add_to(self.m)
            
            return self.m
            
        except Exception as e:
            logger.error(f"Error creating map: {str(e)}")
            logger.error(traceback.format_exc())
            return None
            
    def _create_feature_groups(self) -> None:
        """Create feature groups for different map layers."""
        self.feature_groups = {
            'base': folium.FeatureGroup(name='Base Map'),
            'state': folium.FeatureGroup(name='State Boundary'),
            'counties': folium.FeatureGroup(name='County Boundaries'),
            'house_districts': folium.FeatureGroup(name='State House Districts'),
            'senate_districts': folium.FeatureGroup(name='State Senate Districts'),
        }
    
    # Removed unused methods to simplify the code
