"""Custom Streamlit component for Leaflet map integration."""
import streamlit as st
import streamlit.components.v1 as components
import json
import logging
from typing import Dict, Any, Optional, Union

from .leaflet_legend import get_legend_js


class LeafletMapComponent:
    """A class to handle Leaflet map creation and configuration."""
    
    # Color schemes for the map
    COLOR_SCHEMES = {
        'blue': ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'],
        'green': ['#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b', '#74c476', '#41ab5d', '#238b45', '#006d2c', '#00441b'],
        'red': ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d'],
        'purple': ['#fcfbfd', '#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#807dba', '#6a51a3', '#54278f', '#3f007d']
    }
    
    # Default metrics to display in popups
    DEFAULT_METRICS = [
        {'key': 'population', 'label': 'Population', 'type': 'count'},
        {'key': 'poverty_rate', 'label': 'Poverty Rate', 'type': 'percentage'},
        {'key': 'median_income', 'label': 'Median Income', 'type': 'currency'},
        {'key': 'unemployment_rate', 'label': 'Unemployment Rate', 'type': 'percentage'},
        {'key': 'college_educated_pct', 'label': 'College Educated', 'type': 'percentage'},
        {'key': 'median_home_value', 'label': 'Median Home Value', 'type': 'currency'},
        {'key': 'alice_rate', 'label': 'ALICE Households', 'type': 'percentage'},
        {'key': 'rent_burden_rate', 'label': 'Housing Cost Burden', 'type': 'percentage'},
        {'key': 'snap_household_rate', 'label': 'SNAP Households', 'type': 'percentage'},
        {'key': 'snap_benefit_annual_per_household', 'label': 'Avg Annual SNAP Benefit', 'type': 'currency'},
        {'key': 'snap_benefits_annual_total', 'label': 'Total Annual SNAP Benefits', 'type': 'currency'}
    ]
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _validate_geojson_data(self, geojson_data: Dict[str, Any], selected_variable: str) -> bool:
        """Validate GeoJSON data and check if selected variable exists."""
        if not geojson_data or 'features' not in geojson_data or not geojson_data['features']:
            self.logger.warning("No features found in GeoJSON data")
            return False
        
        # Check if selected_variable exists in any feature properties
        for feature in geojson_data['features']:
            if selected_variable in feature.get('properties', {}):
                self.logger.info(f"Found {selected_variable} in feature properties")
                return True
        
        # For SNAP variables, be more lenient since they might be merged later
        snap_variables = ['snap_household_rate', 'snap_benefit_annual_per_household', 'snap_benefits_annual_total']
        if selected_variable in snap_variables:
            self.logger.info(f"SNAP variable '{selected_variable}' expected to be merged - proceeding")
            return True
        
        self.logger.warning(f"Selected variable '{selected_variable}' not found in feature properties")
        # Log available properties for debugging
        if geojson_data['features']:
            first_feature_props = list(geojson_data['features'][0].get('properties', {}).keys())
            self.logger.info(f"Available properties: {first_feature_props}")
        return True  # Still proceed even if variable not found
    
    def _format_variable_name(self, variable: str, variable_display_name: Optional[str] = None) -> str:
        """Format variable name for display."""
        if variable_display_name:
            return variable_display_name
        return variable.replace('_', ' ').title()
    
    def _get_css_styles(self) -> str:
        """Return CSS styles for the map component."""
        return """
            .map-legend {
                position: absolute;
                bottom: 20px;
                right: 10px;
                z-index: 1000;
                background: rgba(255, 255, 255, 0.95);
                padding: 8px 10px;
                border-radius: 6px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.15);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 11px;
                line-height: 1.3;
                color: #333;
                border: 1px solid rgba(0,0,0,0.1);
                min-width: 140px;
                max-width: 200px;
            }
            .legend-title {
                font-weight: 600;
                margin-bottom: 6px;
                text-align: center;
                font-size: 12px;
                color: #1a73e8;
            }
            .legend-item {
                display: flex;
                align-items: center;
                margin: 3px 0;
                font-size: 10px;
            }
            .legend-item i {
                display: inline-block;
                width: 18px;
                height: 10px;
                margin-right: 6px;
                border: 1px solid rgba(0,0,0,0.2);
                border-radius: 2px;
            }
            .color-scheme-selector {
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px solid rgba(0,0,0,0.1);
            }
            .color-scheme-selector select {
                width: 100%;
                font-size: 10px;
                padding: 4px 6px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
                margin-top: 2px;
                cursor: pointer;
                transition: border-color 0.2s;
            }
            .color-scheme-selector select:focus {
                outline: none;
                border-color: #1a73e8;
                box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
            }
            .color-scheme-selector label {
                font-size: 10px;
                font-weight: 600;
                color: #555;
                display: block;
                margin-bottom: 2px;
            }
            .custom-popup {
                opacity: 0.92 !important;
            }
            .custom-popup .leaflet-popup-content {
                margin: 10px 12px;
                line-height: 1.4;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .custom-tooltip {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid #1a73e8;
                border-radius: 4px;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
                padding: 6px 10px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 12px;
                line-height: 1.4;
                white-space: nowrap;
                pointer-events: none;
            }
            
            /* Remove focus outline from map features */
            .leaflet-container:focus,
            .leaflet-container:focus-within,
            .leaflet-container:focus-visible,
            .leaflet-container:focus-visible *,
            .leaflet-container *:focus,
            .leaflet-container *:focus-within,
            .leaflet-container *:focus-visible {
                outline: none !important;
                box-shadow: none !important;
            }
            
            /* Remove focus outline from interactive elements */
            .leaflet-interactive:focus,
            .leaflet-interactive:focus-within,
            .leaflet-interactive:focus-visible {
                outline: none !important;
                box-shadow: none !important;
            }
            .custom-tooltip strong {
                color: #1a73e8;
                display: block;
                margin-bottom: 2px;
                font-size: 13px;
            }
            .tooltip-data {
                color: #333;
                font-weight: 500;
            }
        """
    
    def _get_javascript_code(self, map_id: str, geojson_str: str, selected_variable: str, 
                           variable_display_name: str, color_scheme: str) -> str:
        """Generate JavaScript code for the map."""
        return f"""
        (function() {{
            // Configuration constants
            const MAP_CONFIG = {{
                center: [20.7984, -156.3319],
                zoom: 7,
                zoomSnap: 0.1,
                zoomDelta: 0.5
            }};
            
            const COLOR_SCHEMES = {json.dumps(self.COLOR_SCHEMES)};
            const SELECTED_VARIABLE = '{selected_variable}';
            const VARIABLE_DISPLAY_NAME = '{variable_display_name}';
            const MAP_ID = '{map_id}';
            
            // Utility functions
            const utils = {{
                formatValue(value, variableType) {{
                    if (value === undefined || value === null) return 'N/A';
                    
                    const numValue = parseFloat(value);
                    if (isNaN(numValue)) return 'N/A';
                    
                    // Check for percentage types
                    if (variableType === 'percentage' || 
                        variableType.includes('rate') || 
                        variableType.includes('pct') ||
                        variableType.includes('percent')) {{
                        return numValue.toFixed(1) + '%';
                    }} 
                    // Check for currency types
                    else if (variableType === 'currency' || 
                             variableType.includes('income') || 
                             variableType.includes('value') ||
                             variableType.includes('benefit')) {{
                        return '$' + numValue.toLocaleString();
                    }}
                    // Check for count types (population, etc.)
                    else if (variableType === 'count') {{
                        return numValue.toLocaleString();
                    }}
                    
                    return numValue.toLocaleString();
                }},
                
                getColorForValue(value, scheme = '{color_scheme}') {{
                    const numValue = parseFloat(value) || 0;
                    const colors = COLOR_SCHEMES[scheme] || COLOR_SCHEMES.blue;
                    
                    // Dynamic thresholds based on variable type
                    let thresholds;
                    if (SELECTED_VARIABLE.includes('poverty') || SELECTED_VARIABLE.includes('rate')) {{
                        thresholds = [5, 10, 15, 20, 25, 30, 35, 40, 45];
                    }} else if (SELECTED_VARIABLE.includes('income')) {{
                        thresholds = [40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000];
                    }} else if (SELECTED_VARIABLE === 'snap_benefits_annual_total') {{
                        // Custom scale for total SNAP benefits to show more variation
                        // Using logarithmic-like scale for better distribution
                        thresholds = [1000000, 2000000, 5000000, 10000000, 15000000, 20000000, 30000000, 50000000, 75000000];
                    }} else {{
                        thresholds = [0, 1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000];
                    }}
                    
                    for (let i = thresholds.length - 1; i >= 0; i--) {{
                        if (numValue >= thresholds[i]) {{
                            return colors[Math.min(i, colors.length - 1)];
                        }}
                    }}
                    return colors[0];
                }},
                
                createMetricHtml(metrics, properties) {{
                    const metricsConfig = {json.dumps(self.DEFAULT_METRICS)};
                    const snapKeys = ['snap_household_rate', 'snap_benefit_annual_per_household', 'snap_benefits_annual_total'];
                    let html = '';
                    
                    metricsConfig.forEach(metric => {{
                        // Skip SNAP metrics as they have their own column
                        if (snapKeys.includes(metric.key)) {{
                            return;
                        }}
                        
                        const value = properties[metric.key];
                        if (value !== undefined && value !== null) {{
                            const isSelected = metric.key === SELECTED_VARIABLE;
                            const bgColor = isSelected ? '#e8f0fe' : '#f8f9fa';
                            const borderColor = isSelected ? '#1a73e8' : '#e0e0e0';
                            const fontWeight = isSelected ? 'bold' : 'normal';
                            
                            html += 
                                '<div style="background: ' + bgColor + '; ' +
                                'border: 1px solid ' + borderColor + '; ' +
                                'border-radius: 4px; padding: 6px 8px; margin: 3px 0; ' +
                                'font-weight: ' + fontWeight + ';">' +
                                '<div style="font-size: 10px; color: #666; margin-bottom: 2px;">' + 
                                metric.label + '</div>' +
                                '<div style="font-size: 12px; color: #333;">' + 
                                utils.formatValue(value, metric.type) + '</div>' +
                                '</div>';
                        }}
                    }});
                    return html;
                }},
                
                createSnapHtml(properties) {{
                    const snapMetrics = [
                        {{'key': 'snap_household_rate', 'label': 'SNAP Households', 'type': 'percentage'}},
                        {{'key': 'snap_benefit_annual_per_household', 'label': 'Avg Annual Benefit', 'type': 'currency'}},
                        {{'key': 'snap_benefits_annual_total', 'label': 'Total Annual Benefits', 'type': 'currency'}}
                    ];
                    
                    let html = '';
                    let hasData = false;
                    
                    snapMetrics.forEach(metric => {{
                        const value = properties[metric.key];
                        if (value !== undefined && value !== null && !isNaN(value)) {{
                            hasData = true;
                            const isSelected = metric.key === SELECTED_VARIABLE;
                            const bgColor = isSelected ? '#e8f0fe' : '#f8f9fa';
                            const borderColor = isSelected ? '#1a73e8' : '#e0e0e0';
                            const fontWeight = isSelected ? 'bold' : 'normal';
                            
                            html += 
                                '<div style="background: ' + bgColor + '; ' +
                                'border: 1px solid ' + borderColor + '; ' +
                                'border-radius: 4px; padding: 6px 8px; margin: 3px 0; ' +
                                'font-weight: ' + fontWeight + ';">' +
                                '<div style="font-size: 10px; color: #666; margin-bottom: 2px;">' + 
                                metric.label + '</div>' +
                                '<div style="font-size: 12px; color: #333;">' + 
                                utils.formatValue(value, metric.type) + '</div>' +
                                '</div>';
                        }}
                    }});
                    
                    if (!hasData) {{
                        html = '<div style="color: #999; text-align: center; font-style: italic;">No SNAP data available</div>';
                    }}
                    
                    return html;
                }}
            }};
            
            // Initialize map
            const map = L.map(MAP_ID, {{
                center: MAP_CONFIG.center,
                zoom: MAP_CONFIG.zoom,
                zoomControl: false,
                attributionControl: false,
                zoomSnap: MAP_CONFIG.zoomSnap,
                zoomDelta: MAP_CONFIG.zoomDelta
            }});
            
            // Set background color
            document.getElementById(MAP_ID).style.backgroundColor = 'white';
            
            // Add zoom control
            L.control.zoom({{ position: 'topleft' }}).addTo(map);
            
            // Map interaction handlers
            let geoJsonLayer;
            
            const mapHandlers = {{
                style(feature) {{
                    return {{
                        fillColor: utils.getColorForValue(feature.properties[SELECTED_VARIABLE]),
                        weight: 1,
                        opacity: 1,
                        color: '#666',
                        fillOpacity: 0.7
                    }};
                }},
                
                highlightFeature(e) {{
                    const layer = e.target;
                    layer.setStyle({{
                        weight: 3,
                        color: '#333',
                        fillOpacity: 0.9
                    }});
                    layer.bringToFront();
                }},
                
                resetHighlight(e) {{
                    geoJsonLayer.resetStyle(e.target);
                }},
                
                zoomToFeature(e) {{
                    if (e.originalEvent && e.originalEvent.target && 
                        e.originalEvent.target.closest('.leaflet-popup-content')) {{
                        return;
                    }}
                    
                    map.fitBounds(e.target.getBounds());
                    
                    const featureId = e.target.feature.properties.id || 
                                    e.target.feature.properties.GEOID || 
                                    e.target.feature.properties.geoid || 
                                    e.target.feature.properties.fips || 
                                    e.target.feature.properties.FIPS || 
                                    e.target.feature.properties.feature_id ||
                                    e.target.feature.properties.geo_id ||
                                    e.target.feature.id;
                    
                    if (featureId) {{
                        localStorage.setItem('hawaii_dashboard_selected_feature', featureId);
                        window.parent.postMessage({{
                            type: 'feature_selected',
                            featureId: featureId
                        }}, '*');
                    }}
                }},
                
                onEachFeature(feature, layer) {{
                    layer.on({{
                        mouseover: mapHandlers.highlightFeature,
                        mouseout: mapHandlers.resetHighlight,
                        click: mapHandlers.zoomToFeature
                    }});
                    
                    const props = feature.properties;
                    let name = props.display_name || props.NAME || 'Unknown';
                    // Remove ', Hawaii' or '; Hawaii' from anywhere in the name
                    name = name.replace(/[,;]\\s*Hawaii/g, '').trim();
                    const value = props[SELECTED_VARIABLE];
                    const formattedValue = utils.formatValue(value, SELECTED_VARIABLE);
                    const metricsHtml = utils.createMetricHtml(null, props);
                    const snapHtml = utils.createSnapHtml(props);
                    
                    // Create three columns for the popup content
                    // Use unique_id first, but add fallback with geo level prefix
                    let featureId = props.unique_id;
                    
                    // If unique_id is not available, create a prefixed ID based on current layer
                    if (!featureId || featureId === 'undefined' || featureId === 'null') {{
                        const rawId = props.GEOID || props.geoid || props.id || feature.id;
                        if (rawId) {{
                            // Determine prefix based on active layer or feature properties
                            let prefix = 'county'; // default to county
                            if (window.location.search.includes('house') || props.DISTRICT || props.house_id) {{
                                prefix = 'house';
                            }} else if (window.location.search.includes('senate') || props.senate_id) {{
                                prefix = 'senate';
                            }}
                            featureId = prefix + '_' + rawId;
                        }}
                    }}
                    
                    console.log('Feature properties:', props);
                    console.log('Selected feature ID:', featureId);
                    
                    let detailLinkHtml = '';
                    if (featureId && featureId !== 'undefined' && featureId !== 'null') {{
                        detailLinkHtml = [
                            '  <div style="margin-top: 12px; text-align: center;">',
                            '    <a href="/geo_detail?geo_id=' + encodeURIComponent(String(featureId)) + '" target="_blank" style="display: inline-block; background-color: #3a7710; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-weight: bold;">',
                            '      View Detailed Data',
                            '    </a>',
                            '  </div>'
                        ].join('');
                    }} else {{
                        detailLinkHtml = [
                            '  <div style="margin-top: 12px; text-align: center;">',
                            '    <span style="display: inline-block; background-color: #ccc; color: #666; padding: 8px 16px; border-radius: 4px; font-style: italic;">',
                            '      Detailed data unavailable (no ID)',
                            '    </span>',
                            '  </div>'
                        ].join('');
                    }}
                    
                    // Create popup content with string concatenation
                    const popupContent = [
                        '<div style="max-width: 500px; padding: 12px;">',
                        '  <div style="margin-bottom: 10px; text-align: center; font-weight: 600; font-size: 15px; color: #222;">',
                        '    ', name,
                        '  </div>',
                        '  <div style="background: #1a73e8; color: white; padding: 6px 8px; border-radius: 4px; text-align: center; margin-bottom: 12px;">',
                        '    <strong>', VARIABLE_DISPLAY_NAME, ': ', formattedValue, '</strong>',
                        '  </div>',
                        '  <div style="display: flex; gap: 10px; margin-top: 8px; justify-content: space-between;">',
                        '    <!-- Key Metrics Column -->',
                        '    <div style="width: 48%; border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px;">',
                        '      <div style="font-size: 12px; color: #666; margin-bottom: 6px; font-weight: bold; text-align: center;">Key Metrics</div>',
                        '      ', (metricsHtml || '<div style="color: #999; text-align: center; font-style: italic;">No metrics available</div>'),
                        '    </div>',
                        '    <!-- SNAP Column -->',
                        '    <div style="width: 48%; border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px;">',
                        '      <div style="font-size: 12px; color: #666; margin-bottom: 6px; font-weight: bold; text-align: center;">SNAP</div>',
                        '      ', (snapHtml || ''),
                        '    </div>',
                        '  </div>',
                        detailLinkHtml,
                        '</div>'
                    ].join('');
                    
                    // Handle click to show popup at screen center while keeping feature visible
                    layer.on('click', function(e) {{
                        console.log('Layer clicked');
                        L.DomEvent.stop(e);
                        
                        // Close any existing popup first
                        map.closePopup();
                        console.log('Closed existing popup');
                        
                        // Get feature bounds
                        const featureBounds = layer.getBounds ? layer.getBounds() : 
                                            (layer.getLatLng ? L.latLngBounds([layer.getLatLng(), layer.getLatLng()]) : null);
                        
                        if (featureBounds) {{
                            // First, adjust the view to show the feature with extra space for popup
                            const featurePadding = [100, 100]; // Extra padding for popup space
                            map.fitBounds(featureBounds, {{
                                padding: featurePadding,
                                animate: true,
                                duration: 0.12
                            }});
                            
                            // After view adjustment, calculate optimal popup position
                            setTimeout(() => {{
                                const mapContainer = map.getContainer();
                                const containerBounds = mapContainer.getBoundingClientRect();
                                
                                // Calculate position that's centered horizontally and 85% down from the top
                                const popupPosition = map.containerPointToLatLng([
                                    containerBounds.width / 2,  // Centered horizontally
                                    containerBounds.height * 0.85  // 85% down from top
                                ]);
                                
                                // Create popup at the calculated position
                                const popup = L.popup({{
                                    maxWidth: 500,
                                    className: 'custom-popup',
                                    autoPan: false,
                                    closeOnClick: false
                                }})
                                .setLatLng(popupPosition)
                                .setContent(popupContent);
                                
                                console.log('Opening popup at position:', popupPosition);
                                console.log('Popup content:', popupContent);
                                popup.openOn(map);
                                console.log('Popup should be visible now');
                            }}, 300); // Wait for map animation to complete
                        }}
                    }});
                    
                    layer.bindTooltip(
                        '<strong>' + name + '</strong><br><span class="tooltip-data">' + 
                        VARIABLE_DISPLAY_NAME + ': ' + formattedValue + '</span>',
                        {{ className: 'custom-tooltip', offset: [0, -10] }}
                    );
                }}
            }};
            
            // Create GeoJSON layer
            const geoJsonData = {geojson_str};
            geoJsonLayer = L.geoJSON(geoJsonData, {{
                style: mapHandlers.style,
                onEachFeature: mapHandlers.onEachFeature
            }}).addTo(map);
            
            map.fitBounds(geoJsonLayer.getBounds());
            
            // Import legend functionality
            {get_legend_js()}
            
            // Initialize legend
            legendManager.update();
            legendManager.setupColorSchemeHandler();
            
            // Store map reference for debugging
            window[MAP_ID] = map;
        }})();
        """
    
    def create_map(
        self,
        geojson_data: Union[Dict[str, Any], str],
        selected_variable: str,
        variable_display_name: Optional[str] = None,
        color_scheme: str = "blue",
        active_layer: str = "Counties",
        map_height: int = 500,
        key: Optional[str] = None
    ) -> None:
        """
        Create a Leaflet map component in Streamlit.
        
        Args:
            geojson_data: GeoJSON data to display on the map
            selected_variable: Variable to display (e.g., 'poverty_rate')
            variable_display_name: Display name for the variable
            color_scheme: Color scheme for the map ('blue', 'green', 'red', 'purple')
            active_layer: Active layer name (for future use)
            map_height: Height of the map in pixels
            key: Unique key for the component
        
        Returns:
            None
        """
        self.logger.info(f"Creating Leaflet map with variable: {selected_variable}")
        
        # Convert GeoJSON to dict if it's a string
        if isinstance(geojson_data, str):
            geojson_data = json.loads(geojson_data)
        
        # Validate data
        self._validate_geojson_data(geojson_data, selected_variable)
        
        # Prepare data
        geojson_str = json.dumps(geojson_data)
        map_id = f"leaflet-map-{key}" if key else "leaflet-map"
        variable_display_name = self._format_variable_name(selected_variable, variable_display_name)
        current_color_scheme = st.session_state.get('color_scheme', color_scheme)
        
        # Build HTML component
        component_html = f"""
        <div style="height:{map_height}px; width:100%; margin-bottom:20px; position:relative;">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            
            <style>{self._get_css_styles()}</style>
            
            <div id="{map_id}" style="height:100%; width:100%;"></div>
            <div id="{map_id}-legend" class="map-legend">
                <div class="legend-title">{variable_display_name}</div>
                <div class="legend-items" id="{map_id}-legend-items"></div>
                <div class="color-scheme-selector">
                    <label for="color-scheme-select">Color Scheme:</label>
                    <select id="color-scheme-select">
                        <option value="blue" {'selected' if current_color_scheme == 'blue' else ''}>Blue Scale</option>
                        <option value="green" {'selected' if current_color_scheme == 'green' else ''}>Green Scale</option>
                        <option value="red" {'selected' if current_color_scheme == 'red' else ''}>Red Scale</option>
                        <option value="purple" {'selected' if current_color_scheme == 'purple' else ''}>Purple Scale</option>
                    </select>
                </div>
            </div>
            
            <script>
                {self._get_javascript_code(map_id, geojson_str, selected_variable, variable_display_name, current_color_scheme)}
            </script>
        </div>
        """
        
        # Render component with extra height for popups
        components.html(
            component_html,
            height=map_height + 200,
            scrolling=False
        )


def create_leaflet_map(
    geojson_data: Union[Dict[str, Any], str], 
    selected_variable: str, 
    variable_display_name: Optional[str] = None, 
    color_scheme: str = "blue", 
    active_layer: str = "Counties",
    map_height: int = 500, 
    key: Optional[str] = None
) -> None:
    """
    Create a Leaflet map component in Streamlit.
    
    This is a convenience function that creates a LeafletMapComponent instance
    and calls its create_map method.
    
    Args:
        geojson_data: GeoJSON data to display on the map
        selected_variable: Variable to display (e.g., 'poverty_rate')
        variable_display_name: Display name for the variable
        color_scheme: Color scheme for the map ('blue', 'green', 'red', 'purple')
        active_layer: Active layer name (for future use)
        map_height: Height of the map in pixels
        key: Unique key for the component
    
    Returns:
        None
    """
    component = LeafletMapComponent()
    component.create_map(
        geojson_data=geojson_data,
        selected_variable=selected_variable,
        variable_display_name=variable_display_name,
        color_scheme=color_scheme,
        active_layer=active_layer,
        map_height=map_height,
        key=key
    )