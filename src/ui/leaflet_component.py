"""Custom Streamlit component for Leaflet map integration."""
import streamlit as st
import streamlit.components.v1 as components
import json
import os
from pathlib import Path

def create_leaflet_map(
    geojson_data, 
    variable="poverty_rate", 
    color_scheme="blue", 
    height=600, 
    key=None
):
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
    <div style="height:{height}px; width:100%; margin-bottom:20px;">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        
        <div id="{map_id}" style="height:100%; width:100%;"></div>
        <div id="{map_id}-legend" class="map-legend">
            <div class="legend-title">Legend</div>
            <div class="legend-items" id="{map_id}-legend-items"></div>
        </div>
        
        <script>
            // Initialize the map
            const map = L.map('{map_id}').setView([20.7984, -156.3319], 7);
            
            // Add tile layer
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '© OpenStreetMap contributors'
            }}).addTo(map);
            
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
                const value = feature.properties['{variable}'];
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
                const name = properties.name || properties.NAME || 'Unknown';
                const value = properties['{variable}'] || 'N/A';
                
                // Format the value based on the variable type
                let formattedValue = value;
                if ('{variable}'.includes('rate') || '{variable}'.includes('pct')) {{
                    formattedValue = value + '%';
                }} else if ('{variable}'.includes('income') || '{variable}'.includes('value')) {{
                    formattedValue = '$' + value.toLocaleString();
                }}
                
                layer.bindPopup(`<strong>${{name}}</strong><br>${{'{variable}'.replace('_', ' ')}}: ${{formattedValue}}<br>Click for details`);
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
                const grades = [0, 2.5, 5, 7.5, 10, 12.5, 15, 17.5, 20];
                let labels = [];
                
                // Format labels based on variable type
                if ('{variable}'.includes('rate') || '{variable}'.includes('pct')) {{
                    for (let i = 0; i < grades.length; i++) {{
                        const from = grades[i];
                        const to = grades[i + 1];
                        
                        if (i === grades.length - 1) {{
                            labels.push(`<div class="legend-item">
                                <i style="background:${{colors[i]}}"></i>
                                ${{from}}%+
                            </div>`);
                        }} else {{
                            labels.push(`<div class="legend-item">
                                <i style="background:${{colors[i]}}"></i>
                                ${{from}}% – ${{to}}%
                            </div>`);
                        }}
                    }}
                }} else if ('{variable}'.includes('income') || '{variable}'.includes('value')) {{
                    // Adjust ranges for income/value variables
                    const incomeGrades = [0, 25000, 50000, 75000, 100000, 125000, 150000, 175000, 200000];
                    for (let i = 0; i < incomeGrades.length; i++) {{
                        const from = incomeGrades[i];
                        const to = incomeGrades[i + 1];
                        
                        if (i === incomeGrades.length - 1) {{
                            labels.push(`<div class="legend-item">
                                <i style="background:${{colors[i]}}"></i>
                                $${{from.toLocaleString()}}+
                            </div>`);
                        }} else {{
                            labels.push(`<div class="legend-item">
                                <i style="background:${{colors[i]}}"></i>
                                $${{from.toLocaleString()}} – $${{to.toLocaleString()}}
                            </div>`);
                        }}
                    }}
                }} else {{
                    // Generic legend for other variables
                    for (let i = 0; i < grades.length; i++) {{
                        const from = grades[i];
                        const to = grades[i + 1];
                        
                        if (i === grades.length - 1) {{
                            labels.push(`<div class="legend-item">
                                <i style="background:${{colors[i]}}"></i>
                                ${{from}}+
                            </div>`);
                        }} else {{
                            labels.push(`<div class="legend-item">
                                <i style="background:${{colors[i]}}"></i>
                                ${{from}} – ${{to}}
                            </div>`);
                        }}
                    }}
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
        height=height+50,
        scrolling=False
    )
