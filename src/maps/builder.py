"""Map builder for the Hawaii Appleseed Dashboard."""
import folium
import logging
import traceback
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from src.data.data_loader import DataLoader

logger = logging.getLogger(__name__)

class MapBuilder:
    """Builds and configures the Folium map with layers."""
    
    def __init__(self, active_layers: Optional[List[str]] = None):
        self.active_layers = active_layers or ['State']
        self.m = None
        self.base_dir = Path(__file__).parent.parent.parent
        self.feature_groups: Dict[str, folium.FeatureGroup] = {}
        self.data_loader = DataLoader()
        
    def _get_choropleth_style(self, value: float, max_value: float) -> Dict[str, Any]:
        """Get style for choropleth based on value."""
        if pd.isna(value):
            return {
                'fillColor': '#999999',
                'color': '#666666',
                'weight': 1,
                'fillOpacity': 0.3
            }
            
        # Scale the value to 0-1 range
        normalized = min(value / max_value, 1.0)
        
        # Use a color scale from green to red
        red = int(255 * normalized)
        green = int(255 * (1 - normalized))
        blue = 0
        
        return {
            'fillColor': f'#{red:02x}{green:02x}{blue:02x}',
            'color': '#666666',
            'weight': 1,
            'fillOpacity': 0.7
        }
        
    def _add_choropleth_layer(self, geo_level: str, layer_name: str) -> None:
        """Add a choropleth layer to the map.
        
        Args:
            geo_level: Geographic level ('state', 'county', 'house', 'senate')
            layer_name: Display name for the layer
        """
        try:
            logger.debug(f"Adding choropleth layer for {geo_level} as '{layer_name}'")
            
            # Get the GeoJSON path
            geojson_path = self.data_loader.get_geojson_path(geo_level)
            if not geojson_path:
                logger.error(f"No GeoJSON path found for {geo_level}")
                return
            logger.debug(f"Found GeoJSON at: {geojson_path}")
                
            # Load the data (we'll use this for popups later)
            df = self.data_loader.get_data(geo_level)
            if df is None or df.empty:
                logger.warning(f"No data found for {geo_level}, will use basic visualization")
            else:
                logger.debug(f"Loaded data for {geo_level}: {len(df)} rows")
            
            # Create a feature group for this layer
            fg = folium.FeatureGroup(name=layer_name, show=True)
            
            # Add the GeoJSON data directly to the map with basic styling
            try:
                with open(geojson_path, 'r', encoding='utf-8') as f:
                    geojson_data = json.load(f)
                
                # Get the first feature to check available properties
                first_feature = geojson_data.get('features', [{}])[0].get('properties', {})
                
                # Determine which fields to show in the tooltip
                tooltip_fields = []
                for field in ['NAME', 'name', 'DISTRICT', 'district', 'COUNTY', 'county']:
                    if field in first_feature:
                        tooltip_fields.append(field)
                
                # Add GeoJSON to the feature group with basic styling
                folium.GeoJson(
                    data=geojson_data,
                    name=layer_name,
                    style_function=lambda feature: {
                        'fillColor': '#ff7800',
                        'color': '#000000',
                        'weight': 1,
                        'fillOpacity': 0.5
                    },
                    highlight_function=lambda feature: {
                        'weight': 3,
                        'fillOpacity': 0.7
                    },
                    tooltip=folium.GeoJsonTooltip(
                        fields=tooltip_fields[:3],  # Limit to first 3 fields
                        aliases=[f"{f.capitalize()}:" for f in tooltip_fields[:3]],
                        style="background-color: white; color: #333333; font-family: arial; font-size: 12px; padding: 10px;"
                    ) if tooltip_fields else None
                ).add_to(fg)
                
                logger.debug(f"Successfully added {layer_name} with {len(geojson_data.get('features', []))} features")
                
            except Exception as e:
                logger.error(f"Error loading GeoJSON for {layer_name}: {str(e)}")
                # Fall back to simple GeoJSON if detailed loading fails
                folium.GeoJson(
                    str(geojson_path),
                    name=layer_name
                ).add_to(fg)
            
            # Add the feature group to the map
            fg.add_to(self.m)
            self.feature_groups[layer_name] = fg
            
        except Exception as e:
            logger.error(f"Error adding {layer_name} layer: {str(e)}\n{traceback.format_exc()}")
    
    def _add_state_boundary(self) -> None:
        """Add Hawaii state boundary to the map with hover highlighting."""
        self._add_choropleth_layer('state', 'State Boundary')
        
    def _add_county_boundaries(self) -> None:
        """Add county boundaries to the map with ACS data."""
        self._add_choropleth_layer('county', 'County Boundaries')
        
    def _add_house_districts(self) -> None:
        """Add state house districts to the map with ACS data."""
        self._add_choropleth_layer('house', 'State House Districts')
        
    def _add_state_senate_districts(self) -> None:
        """Add state senate districts to the map with ACS data."""
        self._add_choropleth_layer('senate', 'State Senate Districts')
        
    def _create_feature_groups(self) -> None:
        """Create feature groups for map layers."""
        self.feature_groups = {
            'State Boundary': folium.FeatureGroup(name='State Boundary', show=False),
            'County Boundaries': folium.FeatureGroup(name='County Boundaries', show=False),
            'State House Districts': folium.FeatureGroup(name='State House Districts', show=False),
            'State Senate Districts': folium.FeatureGroup(name='State Senate Districts', show=False)
        }
        
    def create_map(self) -> folium.Map:
        """Create and return a map with configured layers."""
        try:
            # Define bounds for Hawaii (southwest and northeast corners)
            hawaii_bounds = [
                [18.9, -160.2],  # Southwest coordinates
                [22.2, -154.8]    # Northeast coordinates
            ]
            
            logger.debug(f"Active layers: {self.active_layers}")
            
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
            
            # Always add these layers regardless of active_layers
            # This ensures the layers are available in the map
            self._add_state_boundary()
            self._add_county_boundaries()
            self._add_house_districts()
            self._add_state_senate_districts()
            
            # Add layer control to the map
            folium.LayerControl().add_to(self.m)
            
            logger.debug(f"Map created with {len(self.feature_groups)} feature groups")
            
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
