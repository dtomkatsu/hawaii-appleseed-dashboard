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
    """Build maps for the Hawaii Appleseed Dashboard."""
    
    def __init__(self, active_layers: List[str] = None, selected_variable: str = 'poverty_rate'):
        """Initialize the map builder with active layers and selected variable.
        
        Args:
            active_layers: List of layer names to display
            selected_variable: Variable to use for coloring the map
        """
        self.active_layers = active_layers or []
        self.selected_variable = selected_variable
        self.m = None
        self.base_dir = Path(__file__).parent.parent.parent
        self.feature_groups: Dict[str, folium.FeatureGroup] = {}
        self.data_loader = DataLoader()
        
        # Initialize the map object early
        self._init_map()
        
        # Get available variables for reference
        self.available_variables = self.data_loader.get_available_variables()
        
    def _init_map(self) -> None:
        """Initialize the base map with default settings."""
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
            logger.debug("Base map initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing map: {str(e)}")
            logger.error(traceback.format_exc())
            self.m = None
        
    def _get_js_format_script(self, variable_name: str) -> str:
        """Get JavaScript code to format variable values for display."""
        if variable_name in ['poverty_rate', 'unemployment_rate', 'no_health_insurance', 'bachelors_degree', 'renter_occupied']:
            return 'if (typeof value === "number") return value.toFixed(1) + "%";'
        elif variable_name in ['median_income', 'median_rent', 'median_home_value']:
            return 'if (typeof value === "number") return "$" + value.toLocaleString(undefined, {maximumFractionDigits: 0});'
        elif variable_name == 'population':
            return 'if (typeof value === "number") return value.toLocaleString();'
        elif variable_name == 'median_age':
            return 'if (typeof value === "number") return value.toFixed(1);'
        return ''
        
    def _get_choropleth_style(self, value: float, max_value: float) -> Dict[str, Any]:
        """Get style for choropleth based on value."""
        if pd.isna(value):
            return {
                'fillColor': '#cccccc',
                'color': '#000000',
                'weight': 1,
                'fillOpacity': 0.3
            }
        
        # Normalize the value to a 0-1 range
        normalized = value / max_value if max_value > 0 else 0
        
        # Use a color scale from light to dark red
        red = 255
        green = int(255 * (1 - normalized))
        blue = int(255 * (1 - normalized))
        
        return {
            'fillColor': f'#{red:02x}{green:02x}{blue:02x}',
            'color': '#000000',
            'weight': 1,
            'fillOpacity': 0.7
        }
        
    def _add_choropleth_layer(self, geo_level: str, layer_name: str) -> None:
        """Add a choropleth layer to the map.
        
        Args:
            geo_level: Geographic level ('state', 'county', 'house', 'senate')
            layer_name: Display name for the layer
        """
        if self.m is None:
            logger.error("Cannot add choropleth layer: Map object is None")
            return
            
        try:
            logger.debug(f"Adding choropleth layer for {geo_level} as '{layer_name}'")
            
            # Get the GeoJSON path
            geojson_path = self.data_loader.get_geojson_path(geo_level)
            if not geojson_path:
                logger.error(f"No GeoJSON path found for {geo_level}")
                return
                
            logger.debug(f"Found GeoJSON at: {geojson_path}")
            
            # Load the data
            df = self.data_loader.get_data(geo_level)
            if df is None or df.empty:
                logger.warning(f"No data found for {geo_level}, will use basic visualization")
                has_data = False
            else:
                logger.debug(f"Loaded data for {geo_level}: {len(df)} rows")
                has_data = True
            
            # Create a feature group for this layer
            fg = folium.FeatureGroup(name=layer_name, show=True)
            
            # IMPORTANT: Add the feature group to the map before adding the choropleth
            fg.add_to(self.m)
            
            # Add the GeoJSON data to the map
            try:
                # Load GeoJSON file
                with open(geojson_path, 'r', encoding='utf-8') as f:
                    geojson_data = json.load(f)
                
                # Standardize the GeoJSON IDs to match CSV data
                geo_level_short = geo_level.lower().split()[0]  # 'State Boundary' -> 'state'
                geojson_data = self.data_loader._standardize_geojson_ids(geojson_data, geo_level_short)
                
                # Get the first feature to check available properties
                first_feature = geojson_data.get('features', [{}])[0].get('properties', {})
                
                # Determine which fields to show in the tooltip
                tooltip_fields = []
                for field in ['NAME', 'name', 'DISTRICT', 'district', 'COUNTY', 'county']:
                    if field in first_feature:
                        tooltip_fields.append(field)
                
                # Check if the selected variable exists in the data
                variable_exists = has_data and self.selected_variable in df.columns
                
                if variable_exists:
                    logger.debug(f"Using variable {self.selected_variable} for coloring")
                    
                    # Get the display name for the selected variable
                    var_display_name = self.available_variables.get(self.selected_variable, self.selected_variable)
                    
                    # Format the variable value for display
                    def format_value(value):
                        if pd.isna(value):
                            return 'N/A'
                        if self.selected_variable in ['poverty_rate', 'unemployment_rate', 'no_health_insurance', 'bachelors_degree', 'renter_occupied']:
                            return f"{value:.1f}%"
                        elif self.selected_variable in ['median_income', 'median_rent', 'median_home_value']:
                            return f"${value:,.0f}"
                        elif self.selected_variable == 'population':
                            return f"{value:,.0f}"
                        elif self.selected_variable == 'median_age':
                            return f"{value:.1f}"
                        return str(value)
                    
                    # Add formatted variable to tooltip fields
                    tooltip_fields_with_var = tooltip_fields.copy()
                    tooltip_fields_with_var.append(self.selected_variable)
                    
                    # Determine the correct ID field based on geographic level
                    geo_id_map = {
                        'state': 'state_fips',
                        'county': 'county_fips',
                        'house': 'house_id',
                        'senate': 'senate_id'
                    }
                    
                    # Get the appropriate ID field for this geographic level
                    geo_level_short = geo_level.lower().split()[0]  # 'State Boundary' -> 'state'
                    id_field = geo_id_map.get(geo_level_short, 'GEOID')
                    
                    # Create a simple GeoJSON layer with basic styling
                    try:
                        logger.debug(f"Creating simple GeoJSON layer for {layer_name}")
                        
                        # Prepare data for coloring
                        color_data = {}
                        max_value = 0
                        
                        # Get the maximum value for normalization
                        if self.selected_variable in df.columns:
                            max_value = df[self.selected_variable].max()
                            
                            # Create a mapping from geoid to value
                            for _, row in df.iterrows():
                                if 'geoid' in row and self.selected_variable in row:
                                    color_data[str(row['geoid'])] = row[self.selected_variable]
                        
                        # Create a simple style function
                        def style_function(feature):
                            feature_id = str(feature['properties'].get(id_field, ''))
                            
                            if feature_id in color_data:
                                value = color_data[feature_id]
                                # Normalize the value (0-1 range)
                                normalized = value / max_value if max_value > 0 else 0
                                
                                # Generate color based on value (yellow to red)
                                r = 255
                                g = int(255 * (1 - normalized * 0.8))
                                b = int(100 * (1 - normalized))
                                
                                return {
                                    'fillColor': f'rgb({r},{g},{b})',
                                    'color': '#000000',
                                    'weight': 1,
                                    'fillOpacity': 0.7
                                }
                            else:
                                return {
                                    'fillColor': '#cccccc',
                                    'color': '#000000',
                                    'weight': 1,
                                    'fillOpacity': 0.3
                                }
                        
                        # Create a simple GeoJSON layer
                        geo_layer = folium.GeoJson(
                            data=geojson_data,
                            name=layer_name,
                            style_function=style_function
                        ).add_to(self.m)
                        
                        # Add a simple popup with region name
                        name_field_map = {
                            'state': 'state_name',
                            'county': 'county_name',
                            'house': 'house_name',
                            'senate': 'senate_name'
                        }
                        
                        geo_level_short = geo_level.lower().split()[0]
                        name_field = name_field_map.get(geo_level_short, 'GEOID')
                        
                        # Add a simple popup to each feature
                        for feature in geojson_data['features']:
                            feature_id = str(feature['properties'].get(id_field, ''))
                            region_name = feature['properties'].get(name_field, 'Unknown')
                            
                            # Create popup content
                            popup_content = f"<b>{region_name}</b>"
                            
                            # Add variable value if available
                            if feature_id in color_data:
                                value = color_data[feature_id]
                                var_name = self.available_variables.get(self.selected_variable, self.selected_variable)
                                
                                # Format the value based on variable type
                                if self.selected_variable in ['poverty_rate', 'bachelors_rate', 'renter_rate']:
                                    formatted_value = f"{value:.1f}%"
                                elif self.selected_variable == 'median_income':
                                    formatted_value = f"${value:,.0f}"
                                else:
                                    formatted_value = f"{value:,}"
                                    
                                popup_content += f"<br>{var_name}: {formatted_value}"
                            
                            # Add a popup to the feature
                            geo_layer.add_child(folium.Popup(popup_content, max_width=300))
                        
                        logger.debug(f"Successfully added GeoJSON layer with tooltips for {layer_name} to the map")
                    except Exception as e:
                        logger.error(f"Error creating choropleth for {layer_name}: {str(e)}")
                        logger.error(traceback.format_exc())
                        
                        # Fall back to basic GeoJSON if choropleth fails
                        try:
                            folium.GeoJson(
                                data=geojson_data,
                                name=layer_name,
                                style_function=lambda x: {
                                    'fillColor': '#ffffff',
                                    'color': '#000000',
                                    'weight': 1,
                                    'fillOpacity': 0.3
                                }
                            ).add_to(fg)
                            logger.debug(f"Added fallback GeoJSON for {layer_name}")
                        except Exception as e2:
                            logger.error(f"Failed to add fallback GeoJSON: {str(e2)}")
                    
                    # We're now using the geo_layer approach instead of choropleth
                    # This section is no longer needed as tooltips are handled in the geo_layer creation
                    pass
                    
                else:
                    logger.warning(f"Variable {self.selected_variable} not found in {geo_level} data, using basic styling")
                    # Add basic GeoJSON with static styling
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
        
        # Add feature groups to the map if it exists
        if self.m is not None:
            for fg in self.feature_groups.values():
                fg.add_to(self.m)
        
    def create_map(self) -> folium.Map:
        """Create and return a map with configured layers."""
        try:
            logger.debug("Starting map creation...")
            
            # Ensure we have a valid map object
            if self.m is None:
                logger.error("Map object is None, cannot create map")
                return None
                
            try:
                # Create feature groups for each layer type
                logger.debug("Creating feature groups...")
                self._create_feature_groups()
                
                # Add feature groups to the map
                logger.debug("Adding feature groups to map...")
                for name, fg in self.feature_groups.items():
                    try:
                        logger.debug(f"Adding feature group: {name}")
                        fg.add_to(self.m)
                    except Exception as e:
                        logger.error(f"Error adding feature group {name}: {str(e)}")
                
                # Add layers
                logger.debug("Adding map layers...")
                self._add_state_boundary()
                self._add_county_boundaries()
                self._add_house_districts()
                self._add_state_senate_districts()
                
                # Add layer control to the map
                logger.debug("Adding layer control...")
                folium.LayerControl().add_to(self.m)
                
                logger.debug(f"Map creation complete. Feature groups: {len(self.feature_groups)}")
                
                return self.m
                
            except Exception as e:
                logger.error(f"Error configuring map layers: {str(e)}")
                logger.error(traceback.format_exc())
                return self.m  # Return the base map even if layers fail
                
        except Exception as e:
            logger.error(f"Critical error in create_map: {str(e)}")
            logger.error(traceback.format_exc())
            return None
            
    # This duplicate method has been removed
    
    # Removed unused methods to simplify the code
