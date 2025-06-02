"""Map builder for the Hawaii Appleseed Dashboard."""
import logging
import folium
import branca.colormap as cm
import json
import traceback
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from folium.plugins import MarkerCluster
from folium.features import GeoJsonTooltip
from branca.element import Figure, MacroElement, Template, Element
from jinja2 import Template as JinjaTemplate
from src.data.data_loader import DataLoader
from src.debug_log import log_layer_selection, log_geojson_loading, log_error

logger = logging.getLogger(__name__)

class MapBuilder:
    """Build maps for the Hawaii Appleseed Dashboard."""
    
    def __init__(self, active_layers: List[str] = None, selected_variable: str = 'poverty_rate', color_scheme: str = 'YlOrRd', show_labels: bool = True):
        """Initialize the map builder with active layers and selected variable.
        
        Args:
            active_layers: List of layer names to display
            selected_variable: Variable to use for coloring the map
            color_scheme: Color scheme to use for choropleth maps (e.g., 'YlOrRd', 'BuGn')
            show_labels: Whether to show labels on the map
        """
        self.active_layers = active_layers or []
        self.selected_variable = selected_variable
        self.color_scheme = color_scheme
        self.show_labels = show_labels
        self.m = None
        self.base_dir = Path(__file__).parent.parent.parent
        self.feature_groups: Dict[str, folium.FeatureGroup] = {}
        self.data_loader = DataLoader()
        
        # Log active layers for debugging
        logger.debug(f"MapBuilder initialized with active_layers: {self.active_layers}")
        logger.debug(f"MapBuilder initialized with selected_variable: {self.selected_variable}")
        logger.debug(f"MapBuilder initialized with color_scheme: {self.color_scheme}")
        logger.debug(f"MapBuilder initialized with show_labels: {self.show_labels}")
        
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
            
            # Create a basic map centered on Hawaii with white background
            self.m = folium.Map(
                location=[20.8, -157.3],  # Center of Hawaii
                zoom_start=7,             # Reasonable zoom level for Hawaii
                tiles=None,               # No background tiles
                control_scale=True,
                min_zoom=6,               # Prevent zooming out too far
                max_bounds=True,           # Restrict panning to these bounds
                max_bounds_viscosity=1.0,  # Strict bounds enforcement
                prefer_canvas=True,        # Better performance
                zoom_control=True,         # Enable zoom controls
                attr='Hawaii Appleseed Dashboard'
            )
            
            # Add custom CSS to ensure the background is white while keeping controls visible
            css = '''
            <style>
                .leaflet-container {
                    background: #fff !important;
                }
                .leaflet-tile-container {
                    opacity: 0 !important;
                }
                .leaflet-control-zoom {
                    display: block !important;
                }
            </style>
            '''
            self.m.get_root().header.add_child(folium.Element(css))
            
            # Add a transparent tile layer to satisfy folium's requirements
            folium.TileLayer(
                tiles='',
                attr='Hawaii Appleseed Dashboard',
                name='Background',
                overlay=False,
                control=False,
                opacity=0
            ).add_to(self.m)
            
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
        logger.debug(f"_add_choropleth_layer called for geo_level={geo_level}, layer_name={layer_name}")
        
        if self.m is None:
            logger.error("Cannot add choropleth layer: Map object is None")
            return
            
        try:
            logger.debug(f"Adding choropleth layer for {geo_level} as '{layer_name}'")
            
            # Get the GeoJSON path
            geojson_path = self.data_loader.get_geojson_path(geo_level)
            if not geojson_path:
                error_msg = f"No GeoJSON path found for {geo_level}"
                logger.error(error_msg)
                log_error(error_msg, source=f"MapBuilder._add_choropleth_layer({geo_level})")
                return
                
            logger.debug(f"Found GeoJSON at: {geojson_path}")
            
            # Log GeoJSON loading attempt
            if not Path(geojson_path).exists():
                error_msg = f"GeoJSON file not found: {geojson_path}"
                logger.error(error_msg)
                log_geojson_loading(geo_level, str(geojson_path), success=False, error=error_msg)
                return
            
            # Log successful GeoJSON path resolution
            log_geojson_loading(geo_level, str(geojson_path), success=True)
            
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
                try:
                    with open(geojson_path, 'r', encoding='utf-8') as f:
                        geojson_data = json.load(f)
                    
                    # Log successful GeoJSON loading
                    feature_count = len(geojson_data.get('features', []))
                    logger.debug(f"Successfully loaded GeoJSON with {feature_count} features for {geo_level}")
                    
                    # Log the first feature for debugging
                    if feature_count > 0:
                        first_feature = geojson_data['features'][0]
                        logger.debug(f"First feature properties: {first_feature.get('properties', {})}")
                        
                    # Use enhanced logging
                    log_geojson_loading(
                        geo_level, 
                        str(geojson_path), 
                        success=True, 
                        error=None
                    )
                except Exception as e:
                    error_msg = f"Error loading GeoJSON file: {str(e)}"
                    logger.error(error_msg)
                    log_error(error_msg, exception=e, source=f"MapBuilder._add_choropleth_layer({geo_level})")
                    log_geojson_loading(geo_level, str(geojson_path), success=False, error=str(e))
                    return
                
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
                            
                            # Create a debug log file for data matching
                            debug_log_path = Path(self.base_dir) / 'logs' / 'data_match.log'
                            debug_log_path.parent.mkdir(exist_ok=True)
                            
                            with open(debug_log_path, 'a') as debug_file:
                                debug_file.write(f"\n\n==== Data Matching for {geo_level} at {datetime.now()} ====\n")
                                debug_file.write(f"CSV data: {len(df)} rows\n")
                                debug_file.write(f"CSV columns: {list(df.columns)}\n")
                                debug_file.write(f"Selected variable: {self.selected_variable}\n")
                                
                                # Log the first few rows of CSV data
                                debug_file.write("CSV data sample:\n")
                                for i in range(min(5, len(df))):
                                    row = df.iloc[i]
                                    debug_file.write(f"  Row {i+1}: geoid={row.get('geoid', 'N/A')}, {self.selected_variable}={row.get(self.selected_variable, 'N/A')}\n")
                            
                            # Create a mapping from geoid to value with multiple key formats for matching
                            for _, row in df.iterrows():
                                if 'geoid' in row and self.selected_variable in row:
                                    # Get the geoid as string
                                    geoid_str = str(row['geoid']).strip()
                                    value = row[self.selected_variable]
                                    
                                    # Store the value with multiple key formats for flexible matching
                                    color_data[geoid_str] = value  # Full ID (e.g., '15001')
                                    
                                    # Also store without state prefix if it exists (e.g., '001' from '15001')
                                    if len(geoid_str) > 2 and geoid_str.startswith('15'):
                                        color_data[geoid_str[2:]] = value
                                    
                                    # Also store without leading zeros (e.g., '1' from '001')
                                    color_data[geoid_str.lstrip('0')] = value
                                    if len(geoid_str) > 2 and geoid_str.startswith('15'):
                                        color_data[geoid_str[2:].lstrip('0')] = value
                                        
                                    # For house and senate districts, also store with H or S prefix
                                    if geo_level == 'house' and len(geoid_str) >= 5:
                                        district_num = geoid_str[-3:].lstrip('0')
                                        color_data[f'H{district_num}'] = value
                                        
                                    if geo_level == 'senate' and len(geoid_str) >= 5:
                                        district_num = geoid_str[-3:].lstrip('0')
                                        color_data[f'S{district_num}'] = value
                                        
                                    # Store numeric district ID
                                    if geo_level in ['house', 'senate'] and len(geoid_str) >= 5:
                                        district_num = geoid_str[-3:].lstrip('0')
                                        color_data[district_num] = value
                            
                            # Log the first few entries in color_data for debugging
                            logger.debug(f"Color data keys: {list(color_data.keys())[:10]}")
                            logger.debug(f"GeoJSON ID field: {id_field}")
                            if geojson_data['features']:
                                first_feature_id = geojson_data['features'][0]['properties'].get(id_field, 'Not found')
                                logger.debug(f"First feature ID: {first_feature_id}")
                                logger.debug(f"Is in color_data: {first_feature_id in color_data}")
                            
                            # Create a debug log file to track data matching
                            debug_log_path = Path(self.base_dir) / 'logs' / 'data_match_debug.log'
                            debug_log_path.parent.mkdir(exist_ok=True)
                            
                            with open(debug_log_path, 'a') as debug_file:
                                debug_file.write(f"\n[{geo_level}] GeoJSON IDs: {[f['properties'].get(id_field, 'None') for f in geojson_data['features'][:5]]}")
                                debug_file.write(f"\n[{geo_level}] Color data keys: {list(color_data.keys())[:10]}")
                                debug_file.write(f"\n[{geo_level}] Selected variable: {self.selected_variable}")
                                debug_file.write(f"\n[{geo_level}] Max value: {max_value}\n")
                        
                        # Create a debug log file for style function
                        style_debug_path = Path(self.base_dir) / 'logs' / 'style_function.log'
                        style_debug_path.parent.mkdir(exist_ok=True)
                        
                        with open(style_debug_path, 'a') as debug_file:
                            debug_file.write(f"\n\n==== Style Function for {geo_level} at {datetime.now()} ====\n")
                            debug_file.write(f"Color data keys (sample): {list(color_data.keys())[:10]}\n")
                            debug_file.write(f"ID field: {id_field}\n")
                        
                        # Create style function for normal state
                        def style_function(feature):
                            # Get the feature properties
                            props = feature.get('properties', {})
                            
                            # Get various ID formats from the feature
                            feature_id = str(props.get(id_field, '')).strip()
                            geoid = str(props.get('geoid', '')).strip()
                            house_id = str(props.get('house_id', '')).strip()
                            senate_id = str(props.get('senate_id', '')).strip()
                            state_house = str(props.get('state_house', '')).strip()
                            state_senate = str(props.get('state_senate', '')).strip()
                            
                            # Try different ID formats to match with CSV data
                            potential_ids = []
                            
                            # Add all possible IDs
                            if feature_id:
                                potential_ids.append(feature_id)                  # Original ID
                                potential_ids.append(feature_id.lstrip('0'))      # Without leading zeros
                            
                            if geoid:
                                potential_ids.append(geoid)                        # Direct geoid match
                            
                            # For house districts
                            if geo_level == 'house':
                                if house_id:
                                    potential_ids.append(str(house_id))            # House ID
                                    potential_ids.append(f'15{str(house_id).zfill(3)}')  # FIPS format
                                if state_house:
                                    potential_ids.append(state_house)               # State house (e.g., H01)
                                    if state_house.startswith('H'):
                                        district_num = state_house[1:].lstrip('0')  # Extract number from H01
                                        potential_ids.append(district_num)          # Just the number
                                        potential_ids.append(f'15{state_house[1:].zfill(3)}')  # FIPS format
                            
                            # For senate districts
                            elif geo_level == 'senate':
                                if senate_id:
                                    potential_ids.append(str(senate_id))            # Senate ID
                                    potential_ids.append(f'15{str(senate_id).zfill(3)}')  # FIPS format
                                if state_senate:
                                    potential_ids.append(state_senate)               # State senate (e.g., S01)
                                    if state_senate.startswith('S'):
                                        district_num = state_senate[1:].lstrip('0')  # Extract number from S01
                                        potential_ids.append(district_num)          # Just the number
                                        potential_ids.append(f'15{state_senate[1:].zfill(3)}')  # FIPS format
                            
                            # Remove duplicates and empty strings
                            potential_ids = [pid for pid in potential_ids if pid]
                            potential_ids = list(dict.fromkeys(potential_ids))  # Remove duplicates while preserving order
                            
                            # Try to find a match in the color data
                            matched_id = None
                            matched_value = None
                            
                            for pid in potential_ids:
                                if pid in color_data:
                                    matched_id = pid
                                    matched_value = color_data[pid]
                                    break
                            
                            # Log the first few features for debugging
                            if len(potential_ids) > 0 and (feature_id in ['1', '2', '3', '4', '5'] or 
                                                          (state_house and state_house in ['H01', 'H02', 'H03', 'H04', 'H05']) or
                                                          (state_senate and state_senate in ['S01', 'S02', 'S03', 'S04', 'S05'])):
                                debug_msg = f"Feature: ID={feature_id}, Potential IDs={potential_ids}, Matched: {matched_id is not None}"
                                if matched_id:
                                    debug_msg += f", Value: {matched_value}"
                                logger.debug(debug_msg)
                                
                                with open(style_debug_path, 'a') as debug_file:
                                    debug_file.write(f"Feature: {feature_id}\n")
                                    debug_file.write(f"  Properties: {props}\n")
                                    debug_file.write(f"  Potential IDs: {potential_ids}\n")
                                    debug_file.write(f"  Matched: {matched_id is not None}, ID: {matched_id}, Value: {matched_value}\n")
                            
                            if matched_id:
                                value = color_data[matched_id]
                                # Normalize the value (0-1 range)
                                normalized = value / max_value if max_value > 0 else 0
                                
                                # Generate color based on selected color scheme
                                if self.color_scheme == 'YlOrRd':
                                    # Yellow to Orange to Red
                                    r = 255
                                    g = int(255 * (1 - normalized * 0.8))
                                    b = int(100 * (1 - normalized))
                                    color = f'rgb({r},{g},{b})'
                                elif self.color_scheme == 'YlGnBu':
                                    # Yellow to Green to Blue
                                    r = int(255 * (1 - normalized * 0.8))
                                    g = int(255 * (1 - normalized * 0.3))
                                    b = int(255 * normalized)
                                    color = f'rgb({r},{g},{b})'
                                elif self.color_scheme == 'BuGn':
                                    # Blue to Green
                                    r = int(100 * (1 - normalized))
                                    g = int(200 * normalized + 55)
                                    b = int(220 * (1 - normalized * 0.5) + 35)
                                    color = f'rgb({r},{g},{b})'
                                elif self.color_scheme == 'Reds':
                                    # White to Red
                                    r = 255
                                    g = int(255 * (1 - normalized))
                                    b = int(255 * (1 - normalized))
                                    color = f'rgb({r},{g},{b})'
                                elif self.color_scheme == 'Blues':
                                    # White to Blue
                                    r = int(255 * (1 - normalized))
                                    g = int(255 * (1 - normalized))
                                    b = 255
                                    color = f'rgb({r},{g},{b})'
                                elif self.color_scheme == 'Greens':
                                    # White to Green
                                    r = int(255 * (1 - normalized))
                                    g = 255
                                    b = int(255 * (1 - normalized))
                                    color = f'rgb({r},{g},{b})'
                                elif self.color_scheme == 'Purples':
                                    # White to Purple
                                    r = int(255 * (1 - normalized * 0.5))
                                    g = int(255 * (1 - normalized))
                                    b = 255
                                    color = f'rgb({r},{g},{b})'
                                else:
                                    # Default: Yellow to Red
                                    r = 255
                                    g = int(255 * (1 - normalized * 0.8))
                                    b = int(100 * (1 - normalized))
                                    color = f'rgb({r},{g},{b})'
                                
                                return {
                                    'fillColor': color,
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
                        
                        # Create highlight function for hover state
                        def highlight_function(feature):
                            base_style = style_function(feature)
                            return {
                                'fillColor': base_style['fillColor'],
                                'color': '#ffff00',  # Yellow border on hover
                                'weight': 3,         # Thicker border on hover
                                'fillOpacity': 0.9,   # More opaque on hover
                                'dashArray': '3'      # Dashed border
                            }
                        
                        # Define name field mapping for different geographic levels
                        name_field_map = {
                            'state': 'state_name',
                            'county': 'county_name',
                            'house': 'house_name',
                            'senate': 'senate_name'
                        }
                        
                        # Get the appropriate name field for this geographic level
                        geo_level_short = geo_level.lower().split()[0]
                        name_field = name_field_map.get(geo_level_short, 'GEOID')
                        logger.debug(f"Using name_field: {name_field} for geo_level: {geo_level_short}")
                        
                        # Create a GeoJSON layer with hover effects
                        geo_layer = folium.GeoJson(
                            data=geojson_data,
                            name=layer_name,
                            style_function=style_function,
                            highlight_function=highlight_function,
                            control=True,
                            smooth_factor=1.0
                        ).add_to(self.m)
                        
                        # Add hover effects and simple labels if show_labels is enabled
                        try:
                            # Create a custom tooltip that shows both the name and the selected variable
                            tooltip_html = folium.Html(
                                """
                                <div id="tooltip-content">
                                    Loading...
                                </div>
                                """, 
                                script=True
                            )
                            tooltip = folium.Tooltip(tooltip_html)
                            geo_layer.add_child(tooltip)
                            
                            # Add simple labels if show_labels is enabled
                            if self.show_labels:
                                # Add a simple label to each feature using folium.features.GeoJsonPopup
                                # This adds a permanent label without interfering with the hover functionality
                                label_field = None
                                
                                # Determine which field to use for labels based on geographic level
                                if geo_level.lower().startswith('state'):
                                    label_field = 'state_name'
                                elif geo_level.lower().startswith('county'):
                                    label_field = 'county'
                                elif geo_level.lower().startswith('house'):
                                    label_field = 'house_name'
                                elif geo_level.lower().startswith('senate'):
                                    label_field = 'senate_name'
                                
                                if label_field:
                                    # Add a script to the map that adds labels to each feature
                                    script = f"""
                                    <script>
                                    (function() {{
                                        // Create a unique ID for this map instance to prevent multiple handlers
                                        var mapId = '{geo_level}_{self.selected_variable}_{self.color_scheme}';
                                        
                                        // Only add the event listener once
                                        if (window['labelAdded_' + mapId]) return;
                                        window['labelAdded_' + mapId] = true;
                                        
                                        // Store features data globally to avoid re-parsing
                                        window['features_' + mapId] = {json.dumps([(f['properties'].get(label_field, ''), 
                                                               f['properties'].get('geoid', '')) 
                                                              for f in geojson_data['features']])};
                                        
                                        // Create a throttle function to limit execution frequency
                                        function throttle(func, limit) {{
                                            var inThrottle;
                                            return function() {{
                                                var context = this, args = arguments;
                                                if (!inThrottle) {{
                                                    func.apply(context, args);
                                                    inThrottle = true;
                                                    setTimeout(function() {{
                                                        inThrottle = false;
                                                    }}, limit);
                                                }}
                                            }};
                                        }}
                                        
                                        // Function to add labels
                                        var addLabels = function() {{
                                            // Clear existing labels first
                                            var existingLabels = document.querySelectorAll('.map-label-' + mapId);
                                            existingLabels.forEach(function(label) {{
                                                if (label && label.parentNode) {{
                                                    label.parentNode.removeChild(label);
                                                }}
                                            }});
                                            
                                            // Get all path elements in the map
                                            var paths = document.querySelectorAll('path.leaflet-interactive');
                                            var features = window['features_' + mapId];
                                            
                                            if (!features || !paths.length) return;
                                            
                                            // Create a container for all labels if it doesn't exist
                                            var labelContainer = document.getElementById('label-container-' + mapId);
                                            if (!labelContainer) {{
                                                labelContainer = document.createElement('div');
                                                labelContainer.id = 'label-container-' + mapId;
                                                labelContainer.className = 'label-container';
                                                labelContainer.style.position = 'absolute';
                                                labelContainer.style.top = '0';
                                                labelContainer.style.left = '0';
                                                labelContainer.style.pointerEvents = 'none';
                                                labelContainer.style.zIndex = '650';
                                                var overlayPane = document.querySelector('.leaflet-overlay-pane');
                                                if (overlayPane && overlayPane.parentNode) {{
                                                    overlayPane.parentNode.appendChild(labelContainer);
                                                }}
                                            }}
                                            
                                            // Add a label to each feature
                                            for (var i = 0; i < Math.min(paths.length, features.length); i++) {{
                                                var path = paths[i];
                                                var feature = features[i];
                                                var labelText = feature[0];
                                                var featureId = feature[1];
                                                
                                                if (labelText && labelText !== '[object Object]' && path && path.getBBox) {{
                                                    try {{
                                                        // Get the center of the path
                                                        var bbox = path.getBBox();
                                                        var centerX = bbox.x + bbox.width/2;
                                                        var centerY = bbox.y + bbox.height/2;
                                                        
                                                        // Create a label element
                                                        var label = document.createElement('div');
                                                        label.className = 'map-label map-label-' + mapId;
                                                        label.setAttribute('data-feature-id', featureId || '');
                                                        label.style.position = 'absolute';
                                                        label.style.left = centerX + 'px';
                                                        label.style.top = centerY + 'px';
                                                        label.style.transform = 'translate(-50%, -50%)';
                                                        label.style.fontSize = '10px';
                                                        label.style.fontWeight = 'bold';
                                                        label.style.backgroundColor = 'rgba(255,255,255,0.7)';
                                                        label.style.padding = '2px 4px';
                                                        label.style.borderRadius = '3px';
                                                        label.style.pointerEvents = 'none';
                                                        label.innerHTML = labelText;
                                                        
                                                        // Add the label to the container
                                                        if (labelContainer) {{
                                                            labelContainer.appendChild(label);
                                                        }}
                                                    }} catch (e) {{
                                                        console.error('Error adding label:', e);
                                                    }}
                                                }}
                                            }}
                                        }};
                                        
                                        // Throttled version to prevent performance issues
                                        var throttledAddLabels = throttle(addLabels, 500);
                                        
                                        // Add labels when DOM is loaded
                                        if (document.readyState === 'loading') {{
                                            document.addEventListener('DOMContentLoaded', function() {{
                                                setTimeout(throttledAddLabels, 1000);
                                            }});
                                        }} else {{
                                            setTimeout(throttledAddLabels, 1000);
                                        }}
                                        
                                        // Prevent click propagation on labels
                                        document.addEventListener('click', function(e) {{
                                            if (e.target && e.target.classList && e.target.classList.contains('map-label-' + mapId)) {{
                                                e.stopPropagation();
                                                e.preventDefault();
                                                return false;
                                            }}
                                        }}, true);
                                        
                                        // Handle map zoom and pan events to update labels
                                        var map = document.querySelector('.leaflet-container');
                                        if (map) {{
                                            // Use MutationObserver to detect DOM changes in the map
                                            var observer = new MutationObserver(throttledAddLabels);
                                            observer.observe(map, {{ childList: true, subtree: true }});
                                            
                                            // Also update on zoom end
                                            map.addEventListener('mouseup', function() {{
                                                setTimeout(throttledAddLabels, 300);
                                            }});
                                        }}
                                    }})();
                                    </script>
                                    """
                                    self.m.get_root().html.add_child(folium.Element(script))
                        except Exception as e:
                            logger.error(f"Error adding tooltip to GeoJSON layer: {str(e)}")
                            # Continue without tooltips if there's an error
                            # Create a custom tooltip that shows both the name and the selected variable
                            def get_tooltip_content(feature):
                                props = feature.get('properties', {})
                                feature_id = str(props.get(id_field, '')).strip()
                                region_name = props.get(name_field, 'Unknown')
                                
                                # Try to find a match in the color data
                                potential_ids = [
                                    feature_id,
                                    feature_id.lstrip('0'),
                                    feature_id[-5:] if len(feature_id) > 5 else feature_id
                                ]
                                
                                matched_id = None
                                for pid in potential_ids:
                                    if pid in color_data:
                                        matched_id = pid
                                        break
                                
                                # Format the value
                                if matched_id and matched_id in color_data:
                                    value = color_data[matched_id]
                                    var_name = self.available_variables.get(self.selected_variable, self.selected_variable)
                                    
                                    if self.selected_variable in ['poverty_rate', 'bachelors_rate', 'renter_rate']:
                                        formatted_value = f"{value:.1f}%"
                                    elif self.selected_variable == 'median_income':
                                        formatted_value = f"${value:,.0f}"
                                    else:
                                        formatted_value = f"{value:,}"
                                    
                                    return (f"<div style='font-family: Arial; padding: 5px;'>"
                                           f"<div style='font-weight: bold;'>{region_name}</div>"
                                           f"<div>{var_name}: {formatted_value}</div>"
                                           "</div>")
                                
                                return f"<div style='font-family: Arial; padding: 5px;'>{region_name}<br>No data available</div>"
                            
                            # Add the tooltip to the layer
                            tooltip = folium.GeoJsonTooltip(
                                fields=[],  # We're using a custom formatter instead
                                aliases=[],
                                style=(
                                    'background-color: white;'
                                    'border: 1px solid black;'
                                    'border-radius: 3px;'
                                    'box-shadow: 3px 3px 3px rgba(0, 0, 0, 0.2);'
                                    'padding: 8px;'
                                    'font-size: 12px;'
                                    'min-width: 150px;'
                                    'max-width: 300px;'
                                ),
                                sticky=True,
                                localize=True
                            )
                            
                            # Use a field that actually exists in the data
                            # First, ensure 'tooltip' field exists in all features
                            for feature in geojson_data['features']:
                                if 'tooltip' not in feature['properties']:
                                    feature['properties']['tooltip'] = get_tooltip_content(feature)
                            
                            # Now set up the tooltip with a field we know exists
                            tooltip.fields = ['tooltip']
                            tooltip.aliases = ['']  # No alias needed since we're using the content directly
                            tooltip.style = tooltip.style
                            
                            # Add the tooltip to the layer
                            geo_layer.add_child(tooltip)
                            
                            logger.debug(f"Added custom tooltip for layer: {layer_name}")
                        except Exception as e:
                            logger.error(f"Error adding tooltip: {str(e)}")
                            # Continue without tooltip if there's an error
                        
                        # Process each feature and add individual popups
                        for feature in geojson_data['features']:
                            # Get the feature ID from the GeoJSON
                            feature_id = str(feature['properties'].get(id_field, ''))
                            region_name = feature['properties'].get(name_field, 'Unknown')
                            
                            # Try different ID formats to match with CSV data
                            potential_ids = [
                                feature_id,                  # Original ID
                                feature_id.lstrip('0'),     # Without leading zeros
                                feature_id[-5:] if len(feature_id) > 5 else feature_id  # Last 5 digits
                            ]
                            
                            # Try to find a match in the color data
                            matched_id = None
                            for pid in potential_ids:
                                if pid in color_data:
                                    matched_id = pid
                                    break
                            
                            # Create popup content with more detailed information
                            popup_content = f"<div style='font-family: Arial; padding: 10px; max-width: 300px;'>"
                            popup_content += f"<h4 style='margin: 0 0 10px 0; padding-bottom: 5px; border-bottom: 1px solid #eee;'>{region_name}</h4>"
                            
                            # Add variable value if available
                            if matched_id and matched_id in color_data:
                                value = color_data[matched_id]
                                var_name = self.available_variables.get(self.selected_variable, self.selected_variable)
                                
                                # Format the value based on variable type
                                if self.selected_variable in ['poverty_rate', 'bachelors_rate', 'renter_rate']:
                                    formatted_value = f"{value:.1f}%"
                                    # Add a color indicator for poverty rate
                                    if self.selected_variable == 'poverty_rate':
                                        normalized = value / max_value if max_value > 0 else 0
                                        r = 255
                                        g = int(255 * (1 - normalized * 0.8))
                                        b = int(100 * (1 - normalized))
                                        popup_content += f"<div style='margin: 5px 0;'><b>{var_name}:</b> "
                                        popup_content += f"<span style='display: inline-block; width: 12px; height: 12px; background-color: rgb({r},{g},{b}); margin-right: 5px; border: 1px solid #333;'></span>"
                                        popup_content += f"{formatted_value}</div>"
                                    else:
                                        popup_content += f"<div style='margin: 5px 0;'><b>{var_name}:</b> {formatted_value}</div>"
                                elif self.selected_variable == 'median_income':
                                    formatted_value = f"${value:,.0f}"
                                    popup_content += f"<div style='margin: 5px 0;'><b>{var_name}:</b> {formatted_value}</div>"
                                else:
                                    formatted_value = f"{value:,}"
                                    popup_content += f"<div style='margin: 5px 0;'><b>{var_name}:</b> {formatted_value}</div>"
                                
                                # Add additional context for poverty rate
                                if self.selected_variable == 'poverty_rate' and 'poverty_total' in feature['properties']:
                                    popup_content += f"<div style='margin: 5px 0; font-size: 0.9em; color: #555;'>{feature['properties']['poverty_total']:,} people in poverty</div>"
                                
                            else:
                                popup_content += f"<div style='margin: 5px 0; color: #999;'>No data available for {self.selected_variable}</div>"
                            
                            popup_content += "<div style='margin-top: 10px; font-size: 0.8em; color: #777;'>Click for more details</div>"
                            popup_content += "</div>"
                            
                            # Create a popup for this feature
                            folium.Popup(popup_content, max_width=350).add_to(geo_layer)
                        
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
        logger.debug("Adding STATE boundary layer")
        log_layer_selection('State Boundary', 'MapBuilder._add_state_boundary')
        self._add_choropleth_layer('state', 'State Boundary')
        
    def _add_county_boundaries(self) -> None:
        """Add county boundaries to the map with ACS data."""
        logger.debug("Adding COUNTY boundaries layer")
        log_layer_selection('County Boundaries', 'MapBuilder._add_county_boundaries')
        self._add_choropleth_layer('county', 'County Boundaries')
        
    def _add_house_districts(self) -> None:
        """Add state house districts to the map with ACS data."""
        logger.debug("Adding HOUSE districts layer")
        log_layer_selection('State House Districts', 'MapBuilder._add_house_districts')
        self._add_choropleth_layer('house', 'State House Districts')
        
    def _add_state_senate_districts(self) -> None:
        """Add state senate districts to the map with ACS data."""
        logger.debug("Adding SENATE districts layer")
        log_layer_selection('State Senate Districts', 'MapBuilder._add_state_senate_districts')
        self._add_choropleth_layer('senate', 'State Senate Districts')
        
    def _create_feature_groups(self) -> None:
        """Create feature groups for map layers."""
        # Initialize all feature groups with visibility based on active_layers
        self.feature_groups = {}
        all_layers = {
            'State Boundary': 'State Boundary',
            'County Boundaries': 'County Boundaries',
            'State House Districts': 'State House Districts',
            'State Senate Districts': 'State Senate Districts'
        }
        
        # Create feature groups and set visibility based on active_layers
        for layer_name, display_name in all_layers.items():
            is_visible = layer_name in (self.active_layers or [])
            self.feature_groups[layer_name] = folium.FeatureGroup(
                name=display_name,
                show=is_visible
            )
            
            # Log the layer creation and visibility
            logger.debug(f"Created layer '{layer_name}': visible={is_visible}")
            
        # Add feature groups to the map if it exists
        if self.m is not None:
            for fg in self.feature_groups.values():
                fg.add_to(self.m)
        
    def find_feature_at_point(self, lat: float, lng: float, geo_level: str) -> dict:
        """Find the geographic feature that contains the given point.
        
        Args:
            lat: Latitude of the point
            lng: Longitude of the point
            geo_level: Geographic level (state, county, house, senate)
            
        Returns:
            dict: The feature that contains the point, or None if not found
        """
        import shapely.geometry as sg
        from shapely.geometry import Point, shape
        
        # Create a point from the clicked coordinates
        point = Point(lng, lat)  # GeoJSON uses (longitude, latitude) order
        
        # Get the GeoJSON data for the active layer
        geojson_path = self.base_dir / 'data' / 'geojson' / f'hawaii_{geo_level}.geojson'
        
        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
                
            # Check each feature to see if it contains the point
            for feature in geojson_data.get('features', []):
                if feature.get('geometry'):
                    # Convert the GeoJSON geometry to a shapely shape
                    try:
                        feature_shape = shape(feature['geometry'])
                        
                        # Check if the point is within or on the boundary of the shape
                        if feature_shape.contains(point) or feature_shape.touches(point):
                            return feature
                    except Exception as e:
                        logger.error(f"Error checking if feature contains point: {str(e)}")
                        continue
        except Exception as e:
            logger.error(f"Error loading GeoJSON to find feature at point: {str(e)}")
            
        return None
    
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
                
                # Add only the active layer
                logger.debug("Adding active layer...")
                if self.active_layers and len(self.active_layers) > 0:
                    active_layer = self.active_layers[0]
                    logger.debug(f"Active layer to be added: {active_layer}")
                    
                    # Use enhanced logging for layer selection
                    log_layer_selection(active_layer, source='MapBuilder.create_map')
                    
                    # Map layer names to their respective methods
                    layer_methods = {
                        'State Boundary': self._add_state_boundary,
                        'County Boundaries': self._add_county_boundaries,
                        'State House Districts': self._add_house_districts,
                        'State Senate Districts': self._add_state_senate_districts
                    }
                    
                    # Call the appropriate method for the active layer
                    if active_layer in layer_methods:
                        logger.debug(f"Calling method for layer: {active_layer}")
                        layer_methods[active_layer]()
                    else:
                        error_msg = f"No method found for layer: {active_layer}"
                        logger.error(error_msg)
                        logger.debug(f"Available layer methods: {list(layer_methods.keys())}")
                        log_error(error_msg, source='MapBuilder.create_map')
                else:
                    warning_msg = "No active layers specified, map will be empty"
                    logger.warning(warning_msg)
                    log_error(warning_msg, source='MapBuilder.create_map')
                
                # No need for layer control since we're only showing one layer at a time
                logger.debug("Skipping layer control for single layer view")
                
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
