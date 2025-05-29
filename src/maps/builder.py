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
        """Add Hawaii state boundary to the map."""
        try:
            state_geojson_path = self.base_dir / 'data' / 'Processed GeoJsons' / 'hawaii_state_boundary.geojson'
            
            if not state_geojson_path.exists():
                logger.error(f"State boundary GeoJSON not found at {state_geojson_path}")
                return
                
            # Style for the state boundary
            style_function = lambda x: {
                'fillColor': '#ffffff',
                'color': '#000000',
                'weight': 2,
                'fillOpacity': 0.1
            }
            
            # Add the GeoJSON layer to the state feature group
            folium.GeoJson(
                data=json.loads(state_geojson_path.read_text()),
                style_function=style_function,
                tooltip=folium.GeoJsonTooltip(
                    fields=['state_name'],
                    aliases=['State:'],
                    style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 2px;")
                )
            ).add_to(self.feature_groups['state'])
            
            logger.info("Successfully added state boundary layer")
            
        except Exception as e:
            logger.error(f"Error adding state boundary: {str(e)}")
            logger.error(traceback.format_exc())
            
    def _add_county_boundaries(self) -> None:
        """Add county boundaries to the map."""
        try:
            county_geojson_path = self.base_dir / 'data' / 'Processed GeoJsons' / 'hawaii_county_boundaries.geojson'
            
            if not county_geojson_path.exists():
                logger.error(f"County boundaries GeoJSON not found at {county_geojson_path}")
                return
                
            # Style for county boundaries
            def style_function(feature):
                return {
                    'fillColor': '#f7f7f7',
                    'color': '#666666',
                    'weight': 1,
                    'fillOpacity': 0.3,
                    'dashArray': '5, 5'
                }
            
            # Add the GeoJSON layer to the counties feature group
            folium.GeoJson(
                data=json.loads(county_geojson_path.read_text()),
                style_function=style_function,
                tooltip=folium.GeoJsonTooltip(
                    fields=['county_name', 'county_fips'],
                    aliases=['County: ', 'FIPS Code: '],
                    style=("background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 2px;")
                )
            ).add_to(self.feature_groups['counties'])
            
            logger.info("Successfully added county boundaries layer")
            
        except Exception as e:
            logger.error(f"Error adding county boundaries: {str(e)}")
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
            
            # Add all feature groups to the map
            for group in self.feature_groups.values():
                group.add_to(self.m)
            
            # Add layer control
            folium.LayerControl(collapsed=False).add_to(self.m)
            
            return self.m
            
        except Exception as e:
            logger.error(f"Error creating map: {str(e)}")
            logger.error(traceback.format_exc())
            return None
            
    def _create_feature_groups(self) -> None:
        """Create feature groups for different map layers."""
        self.feature_groups = {
            'base': folium.FeatureGroup(name='Base Map', show=True),
            'state': folium.FeatureGroup(name='State Boundary', show='State' in self.active_layers),
            'counties': folium.FeatureGroup(name='County Boundaries', show='Counties' in self.active_layers),
        }
    
    # Removed unused methods to simplify the code
