// Initialize the Leaflet map with the given data
function initializeMap(mapId, geojsonData, mapHeight) {
    // Create map instance
    const map = L.map(mapId).setView([20.7984, -156.3319], 7);
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);

    // Add GeoJSON layer with popups
    L.geoJSON(geojsonData, {
        style: {
            fillColor: '#3388ff',
            weight: 1,
            opacity: 1,
            color: 'white',
            fillOpacity: 0.7
        },
        onEachFeature: (feature, layer) => {
            const props = feature.properties || {};
            // Try to get feature ID from various possible property names
            const featureId = props.id || props.GEOID || props.geoid || 
                             props.fips || props.FIPS || props.feature_id || 
                             props.geo_id || feature.id;
            
            if (featureId) {
                // Create popup content with button
                const popupContent = `
                    <div style="min-width: 200px;">
                        <h4 style="margin: 0 0 10px 0;">${props.name || 'Feature'}</h4>
                        <div style="margin-bottom: 10px;">
                            ${Object.entries(props)
                                .filter(([key]) => !['id', 'name', 'GEOID', 'geoid', 'fips', 'FIPS', 'feature_id', 'geo_id'].includes(key))
                                .map(([key, value]) => 
                                    `<div><strong>${key.replace(/_/g, ' ')}:</strong> ${value}</div>`
                                ).join('')}
                        </div>
                        <button onclick="window.parent.location.href='/geo_detail?geo_id=${encodeURIComponent(featureId)}'" 
                                style="display: block; width: 100%; padding: 8px; background: #3a7710; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            View Detailed Data
                        </button>
                    </div>
                `;
                
                layer.bindPopup(popupContent);
            }
        }
    }).addTo(map);
    
    // Fit map to bounds if there are features
    if (geojsonData.features && geojsonData.features.length > 0) {
        const bounds = L.geoJSON(geojsonData).getBounds();
        if (bounds.isValid()) {
            map.fitBounds(bounds);
        }
    }
    
    return map;
}
