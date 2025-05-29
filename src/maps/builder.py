"""Map builder for the Hawaii Appleseed Dashboard."""
import folium
from folium.plugins import Fullscreen, MeasureControl
import geopandas as gpd
import logging
from typing import Dict, Optional, Tuple, Any

from src.data.geodata import load_geojson, get_geojson_files, get_geojson_bounds
from src.maps.styles import get_style_function, get_highlight_function

logger = logging.getLogger(__name__)

class MapBuilder:
    """Builds and configures the Folium map with layers."""
    
    def __init__(self, active_layer: str = 'State'):
        """Initialize the map builder."""
        self.active_layer = active_layer
        self.geojson_files = get_geojson_files()
        self.layers: Dict[str, folium.FeatureGroup] = {}
        self.bounds = None
        
    def create_map(self) -> Optional[folium.Map]:
        """Create and configure the Folium map."""
        try:
            logger.info(f"Initializing map with active layer: {self.active_layer}")
            
            # Define Hawaii bounds
            hawaii_bounds = [
                [18.5, -160.5],  # min_lat, min_lon
                [22.5, -154.5]   # max_lat, max_lon
            ]
            
            # Initialize map with Hawaii bounds
            self.m = folium.Map(
                location=[20.5, -157.5],  # Center of Hawaii
                zoom_start=7,
                tiles='CartoDB Positron',
                control_scale=True,
                prefer_canvas=True,
                zoom_control=True,
                width='100%',
                height='100%',
                min_zoom=6,
                max_zoom=14,
                max_bounds=True
            )
            
            # Store bounds as a public attribute
            self.m.hawaii_bounds = hawaii_bounds
            
            # Add controls
            self._add_map_controls()
            
            # Add base layers
            self._add_base_layers()
            
            # Add GeoJSON layers
            self._add_geojson_layers()
            
            # Add layer control after all layers are added
            folium.LayerControl(
                position="topright",
                collapsed=False,
                autoZIndex=True
            ).add_to(self.m)
            
            # Fit map to bounds if we have any layers
            if self.bounds:
                bounds_to_use = [
                    [self.bounds[1], self.bounds[0]],  # min_lat, min_lon
                    [self.bounds[3], self.bounds[2]]   # max_lat, max_lon
                ]
                self.m.fit_bounds(bounds_to_use)
                
                # Store the bounds in the map object for access in the UI
                self.m.used_bounds = bounds_to_use
            
            return self.m
            
        except Exception as e:
            logger.error(f"Error creating map: {str(e)}", exc_info=True)
            return None
    
    def _add_map_controls(self) -> None:
        """Add map controls like fullscreen and measure."""
        Fullscreen(
            position="topleft",
            title="Fullscreen",
            title_cancel="Exit Fullscreen",
            force_separate_button=True,
        ).add_to(self.m)
        
        MeasureControl(position="bottomleft").add_to(self.m)
    
    def _add_base_layers(self) -> None:
        """Add base map layers."""
        # Only add CartoDB Positron as the base layer
        folium.TileLayer(
            'CartoDB Positron',
            name='Light Base',
            attr='CartoDB Positron',
            control=False  # Don't show in layer control since it's the only option
        ).add_to(self.m)
    
    def _add_geojson_layers(self) -> None:
        """Add GeoJSON layers to the map."""
        min_lat, min_lon = 90, 180
        max_lat, max_lon = -90, -180
        has_layers = False
        
        for layer_name, file_path in self.geojson_files.items():
            try:
                logger.info(f"Loading layer: {layer_name} from {file_path}")
                gdf = load_geojson(file_path)
                
                if gdf is not None and not gdf.empty:
                    # Update bounds
                    bounds = get_geojson_bounds(gdf)
                    min_lon = min(min_lon, bounds[0])
                    min_lat = min(min_lat, bounds[1])
                    max_lon = max(max_lon, bounds[2])
                    max_lat = max(max_lat, bounds[3])
                    
                    # Create GeoJSON layer
                    self._create_geojson_layer(gdf, layer_name)
                    has_layers = True
                    
            except Exception as e:
                logger.error(f"Error adding layer {layer_name}: {str(e)}", exc_info=True)
        
        # Store the overall bounds
        if has_layers:
            self.bounds = (min_lon, min_lat, max_lon, max_lat)
    
    def _create_geojson_layer(self, gdf: gpd.GeoDataFrame, layer_name: str) -> None:
        """Create a GeoJSON layer from a GeoDataFrame."""
        # Create a FeatureGroup for this layer
        fg = folium.FeatureGroup(name=layer_name)
        
        # Get the GeoJSON data
        geojson_data = gdf.to_json()
        
        # Create tooltip fields
        tooltip_fields = []
        tooltip_aliases = []
        
        # Add common fields we want to show in tooltips
        if 'name' in gdf.columns:
            tooltip_fields.append('name')
            tooltip_aliases.append('Name')
        if 'county_name' in gdf.columns:
            tooltip_fields.append('county_name')
            tooltip_aliases.append('County')
        if 'state_house' in gdf.columns:
            tooltip_fields.append('state_house')
            tooltip_aliases.append('District')
        if 'state_senate' in gdf.columns:
            tooltip_fields.append('state_senate')
            tooltip_aliases.append('District')
        
        # If no specific fields found, use the first few columns
        if not tooltip_fields and len(gdf.columns) > 0:
            for i, col in enumerate(gdf.columns[:3]):  # Limit to first 3 columns
                if col != 'geometry':
                    tooltip_fields.append(col)
                    tooltip_aliases.append(str(col).replace('_', ' ').title())
        
        # Create the GeoJSON layer with enhanced styling
        folium.GeoJson(
            data=geojson_data,
            name=layer_name,
            style_function=lambda x, name=layer_name: get_style_function(name),
            highlight_function=lambda x: get_highlight_function(),
            tooltip=folium.GeoJsonTooltip(
                fields=tooltip_fields,
                aliases=tooltip_aliases,
                localize=True,
                sticky=True,
                labels=True,
                style="""
                    background-color: #F0EFEF;
                    border: 2px solid black;
                    border-radius: 3px;
                    box-shadow: 3px 3px 4px gray;
                    font-size: 14px;
                    padding: 5px;
                """,
                max_width=800
            ) if tooltip_fields else None
        ).add_to(fg)
        
        # Add the FeatureGroup to the map
        fg.add_to(self.m)
        self.layers[layer_name] = fg
