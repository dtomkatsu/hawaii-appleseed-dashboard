"""A simplified Leaflet map component for Streamlit."""
import json
import streamlit.components.v1 as components

class LeafletMapComponentSimple:
    """A simple Leaflet map component for Streamlit."""
    
    def __init__(self, map_height=600):
        """Initialize the Leaflet map component.
        
        Args:
            map_height (int): Height of the map in pixels.
        """
        self.map_height = map_height
    
    def _get_geojson_data(self, geojson_data):
        """Convert GeoJSON data to a JSON string.
        
        Args:
            geojson_data (dict): GeoJSON data.
            
        Returns:
            str: JSON string of the GeoJSON data.
        """
        return json.dumps(geojson_data)
    
    def create(self, geojson_data, **kwargs):
        """Create and render the Leaflet map.
        
        Args:
            geojson_data (dict): GeoJSON data to display on the map.
            **kwargs: Additional arguments (unused, for compatibility).
            
        Returns:
            None: The map is rendered directly in the Streamlit app.
        """
        # Generate a unique ID for the map container
        map_id = f"leaflet_map_{id(self)}"
        
        # Get GeoJSON data as a JSON string
        geojson_str = self._get_geojson_data(geojson_data)
        
        # Create the HTML/JS for the map
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Streamlit Leaflet Map</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body {{ margin: 0; padding: 0; }}
                #{map_id} {{
                    width: 100%;
                    height: {map_height}px;
                    border-radius: 4px;
                    overflow: hidden;
                }}
                .leaflet-popup-content-wrapper {{
                    border-radius: 6px;
                    padding: 0;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                }}
                .leaflet-popup-content {{
                    margin: 0;
                    min-width: 200px;
                }}
                .leaflet-popup-content h4 {{
                    margin: 0;
                    padding: 10px 12px 8px;
                    font-size: 15px;
                    border-bottom: 1px solid #eee;
                    background-color: #f8f9fa;
                }}
                .leaflet-popup-content .popup-body {{
                    padding: 10px 12px;
                    max-height: 300px;
                    overflow-y: auto;
                }}
                .leaflet-popup-content .popup-footer {{
                    padding: 8px 12px 10px;
                    border-top: 1px solid #eee;
                    background-color: #f8f9fa;
                    text-align: center;
                }}
                .leaflet-popup-content .popup-row {{
                    display: flex;
                    justify-content: space-between;
                    margin-bottom: 4px;
                    font-size: 13px;
                }}
                .leaflet-popup-content .popup-label {{
                    font-weight: 500;
                    color: #555;
                    margin-right: 8px;
                }}
                .leaflet-popup-content .popup-value {{
                    text-align: right;
                    color: #222;
                }}
                .leaflet-popup-content button {{
                    display: block;
                    width: 100%;
                    margin: 0;
                    padding: 8px 12px;
                    background-color: #3a7710;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-weight: 500;
                    font-size: 13px;
                }}
                .leaflet-popup-content button:hover {{
                    background-color: #2c5a0c;
                }}
            </style>
        </head>
        <body>
            <div id="{map_id}"></div>
            <script>
                // Initialize the map
                const map = L.map('{map_id}').setView([20.7984, -156.3319], 7);
                
                // Add the OpenStreetMap tile layer
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                    maxZoom: 19
                }}).addTo(map);
                
                // Function to get feature ID from properties
                function getFeatureId(feature) {{
                    const props = feature.properties || {{}};
                    return props.id || props.GEOID || props.geoid || 
                           props.fips || props.FIPS || props.feature_id || 
                           props.geo_id || feature.id;
                }}
                
                // Add GeoJSON layer
                const geojsonData = {geojson_str};
                const geoJsonLayer = L.geoJSON(geojsonData, {{
                    style: {{
                        fillColor: '#3388ff',
                        weight: 1,
                        opacity: 1,
                        color: 'white',
                        fillOpacity: 0.7
                    }},
                    onEachFeature: function(feature, layer) {{
                        const props = feature.properties || {{}};
                        const featureName = props.name || 'Feature';
                        const featureId = getFeatureId(feature);
                        
                        // Create popup content
                        let popupContent = `
                            <div>
                                <h4>${{featureName}}</h4>
                                <div class="popup-body">`;
                        
                        // Add properties to popup (except ID fields)
                        const idFields = ['id', 'GEOID', 'geoid', 'fips', 'FIPS', 'feature_id', 'geo_id'];
                        for (const [key, value] of Object.entries(props)) {{
                            if (!idFields.includes(key) && value !== null && value !== undefined) {{
                                const displayValue = typeof value === 'number' ? value.toLocaleString() : value;
                                popupContent += `
                                    <div class="popup-row">
                                        <span class="popup-label">${{key.replace(/_/g, ' ')}}:</span>
                                        <span class="popup-value">${{displayValue}}</span>
                                    </div>`;
                            }}
                        }}
                        
                        // Add View Details button if we have an ID
                        if (featureId) {{
                            popupContent += `
                                </div>
                                <div class="popup-footer">
                                    <button onclick="window.parent.location.href='/geo_detail?geo_id=${{encodeURIComponent(String(featureId))}}'">
                                        View Detailed Data
                                    </button>
                                </div>`;
                        }} else {{
                            popupContent += `</div>`;
                        }}
                        
                        popupContent += `</div>`;
                        layer.bindPopup(popupContent);
                    }}
                }}).addTo(map);
                
                // Fit map to bounds if there are features
                if (geojsonData.features && geojsonData.features.length > 0) {{
                    const bounds = geoJsonLayer.getBounds();
                    if (bounds.isValid()) {{
                        map.fitBounds(bounds);
                    }}
                }}
                
                // Set the iframe height to match the map height + some padding
                window.parent.postMessage({{
                    type: 'streamlit:setFrameHeight',
                    height: {map_height} + 10
                }}, '*');
            </script>
        </body>
        </html>
        """.format(
            map_id=map_id,
            map_height=self.map_height,
            geojson_str=geojson_str
        )
        
        # Display the map
        components.html(html_content, height=self.map_height + 10)

def create_leaflet_map(geojson_data, **kwargs):
    """Create a Leaflet map with the given GeoJSON data.
    
    Args:
        geojson_data (dict): GeoJSON data to display on the map.
        **kwargs: Additional arguments passed to the LeafletMapComponentSimple constructor.
    
    Returns:
        None: The map is rendered directly in the Streamlit app.
    """
    map_component = LeafletMapComponentSimple(**kwargs)
    return map_component.create(geojson_data)
