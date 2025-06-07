"""Custom Streamlit component for Leaflet map integration."""
import streamlit as st
import streamlit.components.v1 as components
import json
import os
from pathlib import Path

def create_leaflet_map(
    geojson_data, 
    selected_variable, 
    variable_display_name=None, 
    color_scheme="blue", 
    active_layer="Counties",
    map_height=500, 
    key=None
):
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Creating Leaflet map with variable: {selected_variable}")
    
    # Check if selected_variable exists in any feature properties
    has_variable = False
    if geojson_data and 'features' in geojson_data and len(geojson_data['features']) > 0:
        for feature in geojson_data['features']:
            if selected_variable in feature.get('properties', {}):
                has_variable = True
                logger.info(f"Found {selected_variable} in feature {feature['properties'].get('display_name', 'Unknown')}: {feature['properties'][selected_variable]}")
                break
        
        if not has_variable:
            logger.warning(f"Selected variable '{selected_variable}' not found in any feature properties")
            # Log the first feature's properties to see what's available
            if len(geojson_data['features']) > 0:
                logger.info(f"Available properties in first feature: {list(geojson_data['features'][0].get('properties', {}).keys())}")
                logger.info(f"First feature properties: {geojson_data['features'][0].get('properties', {})}")
    else:
        logger.warning("No features found in GeoJSON data")
    """
    Create a Leaflet map component in Streamlit.
    
    Args:
        geojson_data: GeoJSON data to display on the map
        variable: Variable to display (e.g., 'poverty_rate')
        color_scheme: Color scheme for the map
        height: Height of the map in pixels
        key: Unique key for the component
    
    Returns:
        Selected feature ID if a feature was clicked, None otherwise
    """
    # Convert GeoJSON to string if it's a dictionary
    if isinstance(geojson_data, dict):
        geojson_str = json.dumps(geojson_data)
    else:
        geojson_str = geojson_data
    
    # Create a unique ID for this map instance
    map_id = f"leaflet-map-{key}" if key else "leaflet-map"
    
    # Color scheme options for the dropdown
    color_schemes = {
        'blue': 'Blue Scale',
        'green': 'Green Scale',
        'red': 'Red Scale',
        'purple': 'Purple Scale'
    }
    
    # Get the current color scheme from session state
    current_color_scheme = st.session_state.get('color_scheme', 'blue')
    
    # HTML and JavaScript for the Leaflet map
    component_html = f"""
    <div style="height:{map_height}px; width:100%; margin-bottom:20px; position:relative;">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        
        <style>
            .map-legend {{
                position: absolute;
                bottom: 20px;
                right: 10px;
                z-index: 1000;
                background: rgba(255, 255, 255, 0.95);
                padding: 8px 10px 10px 10px;
                border-radius: 4px;
                box-shadow: 0 1px 5px rgba(0,0,0,0.2);
                font-family: Arial, sans-serif;
                font-size: 11px;
                line-height: 1.3;
                color: #333;
                border: 1px solid rgba(0,0,0,0.1);
                min-width: 140px;
                max-width: 200px;
            }}
            .legend-title {{
                font-weight: bold;
                margin-bottom: 6px;
                text-align: center;
                font-size: 12px;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                margin: 3px 0;
            }}
            .legend-item i {{
                display: inline-block;
                width: 18px;
                height: 10px;
                margin-right: 6px;
                opacity: 0.9;
                border: 1px solid rgba(0,0,0,0.2);
                border-radius: 2px;
            }}
            .color-scheme-selector {{
                margin-top: 8px;
                padding-top: 8px;
                border-top: 1px solid rgba(0,0,0,0.1);
            }}
            .color-scheme-selector select {{
                width: 100%;
                font-size: 11px;
                padding: 4px 6px;
                border: 1px solid #ccc;
                border-radius: 3px;
                background-color: white;
                margin-top: 2px;
                height: 24px;
                cursor: pointer;
                -webkit-appearance: none;
                -moz-appearance: none;
                appearance: none;
                background-image: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23333%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E");
                background-repeat: no-repeat;
                background-position: right 5px top 50%;
                background-size: 10px auto;
                padding-right: 20px;
            }}
            .color-scheme-selector select:focus {{
                outline: none;
                border-color: #4c9ffe;
                box-shadow: 0 0 0 2px rgba(76, 159, 254, 0.2);
            }}
            .color-scheme-selector label {{
                font-size: 11px;
                font-weight: bold;
                color: #555;
                display: block;
                margin-bottom: 2px;
            }}
            
            .custom-popup .leaflet-popup-content {{
                margin: 8px 10px;
                line-height: 1.4;
            }}
            
            .enhanced-popup .leaflet-popup-content {{
                margin: 10px 12px;
                line-height: 1.4;
                max-height: 400px;
                overflow-y: auto;
            }}
            
            .enhanced-popup .leaflet-popup-content-wrapper {{
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }}
            
            .enhanced-popup .leaflet-popup-tip {{
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
        </style>
        
        <div id="{map_id}" style="height:100%; width:100%;"></div>
        <div id="{map_id}-legend" class="map-legend">
            <div class="legend-title">Poverty Rate (%)</div>
            <div class="legend-items" id="{map_id}-legend-items"></div>
            <div class="color-scheme-selector">
                <label for="color-scheme-select">Color Scheme:</label>
                <select id="color-scheme-select">
                    <option value="blue" {'selected' if color_scheme == 'blue' else ''}>Blue Scale</option>
                    <option value="green" {'selected' if color_scheme == 'green' else ''}>Green Scale</option>
                    <option value="red" {'selected' if color_scheme == 'red' else ''}>Red Scale</option>
                    <option value="purple" {'selected' if color_scheme == 'purple' else ''}>Purple Scale</option>
                </select>
            </div>
        </div>
        
        <script>
            // Initialize the map with a white background
            const map = L.map('{map_id}', {{
                zoomControl: false,
                attributionControl: false,
                zoomSnap: 0.1,
                zoomDelta: 0.5,
                zoom: 7,
                center: [20.7984, -156.3319],
                layers: [],
                zoomAnimation: true,
                fadeAnimation: true,
                markerZoomAnimation: true
            }});
            
            // Set the map's background to white
            const mapDiv = document.getElementById('{map_id}');
            if (mapDiv) {{
                mapDiv.style.backgroundColor = 'white';
            }}
            
            // Add custom zoom controls
            const zoomControl = L.control.zoom({{ position: 'topleft' }});
            zoomControl.addTo(map);
            
            // Style the zoom controls
            const zoomControlContainer = document.querySelector('.leaflet-control-zoom');
            if (zoomControlContainer) {{
                zoomControlContainer.style.border = 'none';
                zoomControlContainer.style.background = 'rgba(255, 255, 255, 0.7)';
                zoomControlContainer.style.borderRadius = '4px';
                zoomControlContainer.style.overflow = 'hidden';
                zoomControlContainer.style.boxShadow = '0 1px 5px rgba(0,0,0,0.2)';
                
                // Style the zoom buttons
                const zoomIn = zoomControlContainer.querySelector('.leaflet-control-zoom-in');
                const zoomOut = zoomControlContainer.querySelector('.leaflet-control-zoom-out');
                
                if (zoomIn && zoomOut) {{
                    [zoomIn, zoomOut].forEach(btn => {{
                        btn.style.background = 'rgba(255, 255, 255, 0.8)';
                        btn.style.borderBottom = '1px solid rgba(0,0,0,0.1)';
                        btn.style.width = '30px';
                        btn.style.height = '30px';
                        btn.style.lineHeight = '30px';
                        btn.style.fontSize = '20px';
                        btn.style.color = '#333';
                        btn.style.transition = 'all 0.2s';
                        
                        btn.onmouseover = () => {{ btn.style.background = 'rgba(255, 255, 255, 1)'; }};
                        btn.onmouseout = () => {{ btn.style.background = 'rgba(255, 255, 255, 0.8)'; }};
                    }});
                    
                    // Remove the border from the last button
                    zoomOut.style.borderBottom = 'none';
                }}
            }}
            
            // Function to determine color based on value and color scheme
            function getColorForValue(value, scheme = '{color_scheme}') {{
                // Ensure value is a number
                value = parseFloat(value) || 0;
                
                // Define color schemes with more distinct steps
                const schemes = {{
                    blue: ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'],
                    green: ['#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b', '#74c476', '#41ab5d', '#238b45', '#006d2c', '#00441b'],
                    red: ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d'],
                    purple: ['#fcfbfd', '#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#807dba', '#6a51a3', '#54278f', '#3f007d']
                }};
                
                // Get the appropriate color scheme or default to blue
                const colors = schemes[scheme] || schemes.blue;
                
                // Determine color based on value (adjust these thresholds as needed)
                if (value >= 80) return colors[8];
                if (value >= 70) return colors[7];
                if (value >= 60) return colors[6];
                if (value >= 50) return colors[5];
                if (value >= 40) return colors[4];
                if (value >= 30) return colors[3];
                if (value >= 20) return colors[2];
                if (value >= 10) return colors[1];
                return colors[0];
            }}
            
            // Store the current color scheme in the window object for the map
            window['{map_id}_color_scheme'] = '{current_color_scheme}';
            
            // Set up color scheme change handler
            const colorSchemeSelect = document.getElementById('color-scheme-select');
            if (colorSchemeSelect) {{
                colorSchemeSelect.addEventListener('change', function(event) {{
                    const newColorScheme = event.target.value;
                    // Send message to Streamlit with the new color scheme
                    window.parent.postMessage({{
                        type: 'color_scheme_change',
                        color_scheme: newColorScheme,
                        map_id: '{map_id}'
                    }}, '*');
                    
                    // Update the map with the new color scheme
                    updateMapColors(map, newColorScheme);
                }});
            }}
            
            // Function to update map colors when color scheme changes
            function updateMapColors(map, colorScheme) {{
                if (!map) return;
                
                // Get all layers and update their styles
                map.eachLayer(function(layer) {{
                    if (layer.feature) {{
                        const value = layer.feature.properties['{selected_variable}'];
                        if (value !== undefined) {{
                            const color = getColorForValue(value, colorScheme);
                            layer.setStyle({{ fillColor: color }});
                        }}
                    }}
                }});
                
                // Update the legend to reflect the new color scheme
                updateLegend();
            }}
            
            // Store the map instance in the window object for debugging
            window['{map_id}'] = map;
            
            // Style function for features
            function style(feature) {{
                const value = feature.properties['{selected_variable}'];
                return {{
                    fillColor: getColorForValue(value),
                    weight: 1,  
                    opacity: 1,
                    color: '#666',
                    dashArray: '',
                    fillOpacity: 0.7
                }};
            }}
            
            // Highlight feature on hover
            function highlightFeature(e) {{
                const layer = e.target;
                
                layer.setStyle({{
                    weight: 3,
                    color: '#333',
                    dashArray: '',
                    fillOpacity: 0.9
                }});
                
                layer.bringToFront();
            }}
            
            // Reset highlight on mouseout
            function resetHighlight(e) {{
                geoJsonLayer.resetStyle(e.target);
            }}
            
            // Click handler
            function zoomToFeature(e) {{
                // Check if click originated from popup content
                if (e.originalEvent && e.originalEvent.target) {{
                    const target = e.originalEvent.target;
                    if (target.closest('.leaflet-popup-content')) {{
                        console.log('Click originated from popup, ignoring zoom');
                        return;
                    }}
                }}
                
                map.fitBounds(e.target.getBounds());
                
                // Send the clicked feature ID to Streamlit via URL parameter
                const featureId = e.target.feature.properties.id || e.target.feature.id;
                if (featureId) {{
                    // Store in localStorage and trigger a page event
                    localStorage.setItem('hawaii_dashboard_selected_feature', featureId);
                    
                    // Trigger a custom event
                    window.parent.postMessage({{
                        type: 'feature_selected',
                        featureId: featureId
                    }}, '*');
                }}
            }}
            
            // Add interaction to each feature
            function onEachFeature(feature, layer) {{
                layer.on({{
                    mouseover: highlightFeature,
                    mouseout: resetHighlight,
                    click: zoomToFeature
                }});
                
                // Create popup content
                const properties = feature.properties;
                const name = properties.display_name || properties.NAME || 'Unknown';
                let value = properties['{selected_variable}'];
                
                // Format the value based on the variable type
                let formattedValue = 'N/A';
                if (value !== undefined && value !== null) {{
                    if ('{selected_variable}'.includes('rate') || '{selected_variable}'.includes('pct')) {{
                        formattedValue = parseFloat(value).toFixed(1) + '%';
                    }} else if ('{selected_variable}'.includes('income') || '{selected_variable}'.includes('value')) {{
                        formattedValue = '$' + parseFloat(value).toLocaleString();
                    }} else {{
                        formattedValue = value.toLocaleString();
                    }}
                }}
                
                const displayName = '{variable_display_name}' || '{selected_variable}'.replace('_', ' ').replace(/\\b\\w/g, l => l.toUpperCase());
                // Create comprehensive popup content with all available data
                let additionalData = '';
                const props = feature.properties;
                
                // Add key metrics if available
                const keyMetrics = [
                    {{ key: 'population', label: 'Population', format: (v) => v ? v.toLocaleString() : 'N/A' }},
                    {{ key: 'poverty_rate', label: 'Poverty Rate', format: (v) => v ? v.toFixed(1) + '%' : 'N/A' }},
                    {{ key: 'median_income', label: 'Median Income', format: (v) => v ? '$' + v.toLocaleString() : 'N/A' }},
                    {{ key: 'unemployment_rate', label: 'Unemployment Rate', format: (v) => v ? v.toFixed(1) + '%' : 'N/A' }},
                    {{ key: 'college_educated_pct', label: 'College Educated', format: (v) => v ? v.toFixed(1) + '%' : 'N/A' }},
                    {{ key: 'median_home_value', label: 'Median Home Value', format: (v) => v ? '$' + v.toLocaleString() : 'N/A' }}
                ];
                
                let metricsHtml = '';
                keyMetrics.forEach(metric => {{
                    const value = props[metric.key];
                    if (value !== undefined && value !== null) {{
                        const isSelected = metric.key === '{selected_variable}';
                        const bgColor = isSelected ? '#e3f2fd' : '#f9f9f9';
                        const borderColor = isSelected ? '#1E88E5' : '#e0e0e0';
                        const fontWeight = isSelected ? 'bold' : 'normal';
                        
                        metricsHtml += `
                            <div style="
                                background: ${{bgColor}}; 
                                border: 1px solid ${{borderColor}}; 
                                border-radius: 4px; 
                                padding: 6px 8px; 
                                margin: 3px 0;
                                font-weight: ${{fontWeight}};
                                ${{isSelected ? 'box-shadow: 0 1px 3px rgba(30,136,229,0.3);' : ''}}
                            ">
                                <div style="font-size: 11px; color: #666; margin-bottom: 2px;">${{metric.label}}</div>
                                <div style="font-size: 13px; color: #333;">${{metric.format(value)}}</div>
                            </div>
                        `;
                    }}
                }});
                
                const popupContent = `
                    <div style="font-family: Arial, sans-serif; font-size: 13px; line-height: 1.4; min-width: 200px;">
                        <div style="text-align: center; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 2px solid #1E88E5;">
                            <strong style="font-size: 15px; color: #1E88E5;">${{name}}</strong>
                        </div>
                        <div style="margin-bottom: 8px;">
                            <div style="font-size: 12px; color: #666; margin-bottom: 4px;">
                                📊 Currently viewing: <strong>{variable_display_name}</strong>
                            </div>
                            <div style="background: #1E88E5; color: white; padding: 6px 8px; border-radius: 4px; text-align: center;">
                                <strong>${{displayName}}: ${{formattedValue}}</strong>
                            </div>
                        </div>
                        ${{metricsHtml ? `
                            <div style="border-top: 1px solid #eee; padding-top: 8px; margin-top: 8px;">
                                <div style="font-size: 11px; color: #666; margin-bottom: 4px; font-weight: bold;">
                                    📋 Key Demographics & Economics
                                </div>
                                ${{metricsHtml}}
                            </div>
                        ` : ''}}
                        <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #eee; text-align: center;">
                            <div style="font-size: 10px; color: #999;">
                                Click elsewhere to close • Data from ACS 2023
                            </div>
                        </div>
                    </div>
                `;
                
                // Bind popup with larger configuration
                layer.bindPopup(popupContent, {{
                    closeOnClick: false,
                    autoClose: false,
                    closeButton: true,
                    maxWidth: 280,
                    minWidth: 200,
                    className: 'custom-popup enhanced-popup'
                }});
            }}
            
            // Parse GeoJSON and add to map
            const geoJsonData = {geojson_str};
            const geoJsonLayer = L.geoJSON(geoJsonData, {{
                style: style,
                onEachFeature: onEachFeature
            }}).addTo(map);
            
            // Fit map to GeoJSON bounds
            map.fitBounds(geoJsonLayer.getBounds());
            
            // Create legend
            function updateLegend() {{
                const legendItems = document.getElementById('{map_id}-legend-items');
                if (!legendItems) return;
                
                legendItems.innerHTML = '';
                
                // Get the current color scheme
                const colorSchemeSelect = document.getElementById('color-scheme-select');
                const currentScheme = colorSchemeSelect ? colorSchemeSelect.value : '{color_scheme}';
                
                // Define color schemes with more distinct steps
                const schemes = {{
                    blue: ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'],
                    green: ['#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b', '#74c476', '#41ab5d', '#238b45', '#006d2c', '#00441b'],
                    red: ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d'],
                    purple: ['#fcfbfd', '#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#807dba', '#6a51a3', '#54278f', '#3f007d']
                }};
                
                const colors = schemes[currentScheme] || schemes.blue;
                
                // Create legend items based on the variable
                const grades = [0, 5, 10, 15, 20, 25, 30, 35, 40];
                let labels = [];
                
                // Update the getColor function to be dynamic based on the variable type
                function getColor(value) {{
                    if (value === null || isNaN(value)) return '#ccc';
                    
                    // Normalize the value based on variable type
                    let normalizedValue;
                    
                    if ('{selected_variable}'.includes('poverty') || '{selected_variable}'.includes('pct') || '{selected_variable}'.includes('rate')) {{
                        // For percentages (0-100%)
                        normalizedValue = Math.min(Math.max(value, 0), 100);
                        const percent = normalizedValue / 100;
                        return colors[Math.min(Math.floor(percent * 8), 8)];
                    }} else if ('{selected_variable}'.includes('income') || '{selected_variable}'.includes('value')) {{
                        // For income values (40k-120k) - adjusted for Hawaii's income range
                        const minIncome = 40000;
                        const maxIncome = 120000;
                        normalizedValue = Math.min(Math.max(value, minIncome), maxIncome);
                        const percent = (normalizedValue - minIncome) / (maxIncome - minIncome);
                        return colors[Math.min(Math.floor(percent * 8), 8)];
                    }} else {{
                        // For counts (0-500k)
                        normalizedValue = Math.min(Math.max(value, 0), 500000);
                        const percent = normalizedValue / 500000;
                        return colors[Math.min(Math.floor(percent * 8), 8)];
                    }}
                }}
                
                // Update legend title based on variable type
                const legendTitle = document.querySelector('#{map_id}-legend .legend-title');
                let title = '{selected_variable}'.replace(/_/g, ' ').replace(/\\b\\w/g, function(l) {{ return l.toUpperCase(); }});
                
                if ('{selected_variable}'.includes('poverty') || '{selected_variable}'.includes('pct') || '{selected_variable}'.includes('rate')) {{
                    // For poverty rates (5-25% range)
                    title = title + ' (%)';
                    const povertyGrades = [5, 8, 11, 14, 17, 20, 23, 26, 29];
                    for (let i = 0; i < povertyGrades.length - 1; i++) {{
                        const from = povertyGrades[i];
                        const to = povertyGrades[i + 1];
                        const isLast = i === povertyGrades.length - 2;
                        const color = getColor(from + 1);
                        const range = isLast ? from + '%+' : from + '-' + to + '%';
                        
                        labels.push('<div class="legend-item">' +
                            '<i style="background:' + color + '"></i>' +
                            range +
                            '</div>');
                    }}
                }} else if ('{selected_variable}'.includes('income') || '{selected_variable}'.includes('value')) {{
                    // For income/value variables (in dollars) - adjusted for Hawaii's income range
                    title = title + ' ($)';
                    const incomeGrades = [40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000];
                    for (let i = 0; i < incomeGrades.length - 1; i++) {{
                        const from = incomeGrades[i];
                        const to = incomeGrades[i + 1];
                        const isLast = i === incomeGrades.length - 2;
                        const color = getColor(from + (to - from) / 2);
                        let range;
                        
                        if (isLast) {{
                            range = '$' + (from/1000) + 'k+';
                        }} else if (to - from === 10000) {{
                            // For 10k ranges, show as single number (e.g., 50k)
                            range = '$' + (from/1000) + 'k';
                        }} else {{
                            range = '$' + (from/1000) + 'k-$' + (to/1000) + 'k';
                        }}
                        
                        labels.push('<div class="legend-item">' +
                            '<i style="background:' + color + '"></i>' +
                            range +
                            '</div>');
                    }}
                }} else {{
                    // For count variables
                    title = title + ' (Count)';
                    const countGrades = [0, 1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000];
                    for (let i = 0; i < countGrades.length - 1; i++) {{
                        const from = countGrades[i];
                        const to = countGrades[i + 1];
                        const isLast = i === countGrades.length - 2;
                        const color = getColor(from + (to - from) / 2);
                        let range;
                        
                        if (isLast) {{
                            range = from.toLocaleString() + '+';
                        }} else if (to >= 1000) {{
                            range = (from/1000) + 'k-' + (to/1000) + 'k';
                        }} else {{
                            range = from + '-' + to;
                        }}
                        
                        labels.push('<div class="legend-item">' +
                            '<i style="background:' + color + '"></i>' +
                            range +
                            '</div>');
                    }}
                }}
                
                // Update the legend title
                if (legendTitle) {{
                    legendTitle.textContent = title;
                }}
                
                legendItems.innerHTML = labels.join('');
                
                // Update the colors in the legend items
                const legendItemElements = legendItems.querySelectorAll('.legend-item i');
                legendItemElements.forEach((item, i) => {{
                    if (i < colors.length) {{
                        item.style.backgroundColor = colors[i];
                    }}
                }});
            }}
            
            updateLegend();
        </script>
    </div>
    """
    
    # Use Streamlit's component functionality to render the HTML/JS
    components.html(
        component_html,
        height=map_height+50,
        scrolling=False
    )
    
    # Return None since we're using localStorage and postMessage for communication
    return None
