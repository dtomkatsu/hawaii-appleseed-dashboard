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
                background: rgba(255, 255, 255, 0.8);
                padding: 10px;
                border-radius: 4px;
                box-shadow: 0 1px 5px rgba(0,0,0,0.2);
                font-family: Arial, sans-serif;
                font-size: 12px;
                line-height: 1.4;
                color: #333;
                backdrop-filter: blur(2px);
                border: 1px solid rgba(0,0,0,0.1);
            }}
            .legend-title {{
                font-weight: bold;
                margin-bottom: 5px;
                text-align: center;
                font-size: 13px;
            }}
            .legend-item {{
                display: flex;
                align-items: center;
                margin: 2px 0;
            }}
            .legend-item i {{
                display: inline-block;
                width: 20px;
                height: 12px;
                margin-right: 5px;
                opacity: 0.8;
            }}
        </style>
        
        <div id="{map_id}" style="height:100%; width:100%;"></div>
        <div id="{map_id}-legend" class="map-legend">
            <div class="legend-title">Poverty Rate (%)</div>
            <div class="legend-items" id="{map_id}-legend-items"></div>
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
            
            // Define color schemes
            const colorSchemes = {{
                blue: ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'],
                green: ['#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b', '#74c476', '#41ab5d', '#238b45', '#006d2c', '#00441b'],
                red: ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d'],
                purple: ['#fcfbfd', '#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#807dba', '#6a51a3', '#54278f', '#3f007d']
            }};
            
            // Get current color scheme
            const currentColorScheme = '{color_scheme}';
            const colors = colorSchemes[currentColorScheme] || colorSchemes.blue;
            
            // Function to get color based on value
            function getColor(value) {{
                if (value === null || isNaN(value)) return '#ccc';
                
                // Adjust these thresholds based on your data
                if (value > 20) return colors[8];
                if (value > 17.5) return colors[7];
                if (value > 15) return colors[6];
                if (value > 12.5) return colors[5];
                if (value > 10) return colors[4];
                if (value > 7.5) return colors[3];
                if (value > 5) return colors[2];
                if (value > 2.5) return colors[1];
                return colors[0];
            }}
            
            // Style function for features
            function style(feature) {{
                const value = feature.properties['{selected_variable}'];
                return {{
                    fillColor: getColor(value),
                    weight: 2,
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
                map.fitBounds(e.target.getBounds());
                
                // Send the clicked feature ID to Streamlit
                const featureId = e.target.feature.properties.id || e.target.feature.id;
                if (featureId) {{
                    // Use Streamlit's setComponentValue to communicate back to Python
                    if (window.Streamlit) {{
                        window.Streamlit.setComponentValue(featureId);
                    }}
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
                
                const displayName = '{variable_display_name}' || '{selected_variable}'.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
                layer.bindPopup(`<strong>${{name}}</strong><br>${{displayName}}: ${{formattedValue}}<br>Click for details`);
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
                legendItems.innerHTML = '';
                
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
                        // For income values (0-200k)
                        normalizedValue = Math.min(Math.max(value, 0), 200000);
                        const percent = normalizedValue / 200000;
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
                let title = '{selected_variable}'.replace(/_/g, ' ').replace(/\b\w/g, function(l) {{ return l.toUpperCase(); }});
                
                if ('{selected_variable}'.includes('poverty') || '{selected_variable}'.includes('pct') || '{selected_variable}'.includes('rate')) {{
                    // For percentage variables
                    title = title + ' (%)';
                    for (let i = 0; i < grades.length - 1; i++) {{
                        const from = grades[i];
                        const to = grades[i + 1];
                        const isLast = i === grades.length - 2;
                        const color = getColor(from + 0.1);
                        const range = isLast ? from + '%+' : from + '%-' + to + '%';
                        
                        labels.push('<div class="legend-item">' +
                            '<i style="background:' + color + '"></i>' +
                            range +
                            '</div>');
                    }}
                }} else if ('{selected_variable}'.includes('income') || '{selected_variable}'.includes('value')) {{
                    // For income/value variables (in dollars)
                    title = title + ' ($)';
                    const incomeGrades = [0, 25000, 50000, 75000, 100000, 125000, 150000, 175000, 200000];
                    for (let i = 0; i < incomeGrades.length - 1; i++) {{
                        const from = incomeGrades[i];
                        const to = incomeGrades[i + 1];
                        const isLast = i === incomeGrades.length - 2;
                        const color = getColor(from + (to - from) / 2);
                        let range;
                        
                        if (isLast) {{
                            range = '$' + (from/1000) + 'k+';
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
            }}
            
            updateLegend();
        </script>
    </div>
    """
    
    # Use Streamlit's component functionality to render the HTML/JS
    return components.html(
        component_html,
        height=map_height+50,
        scrolling=False
    )
