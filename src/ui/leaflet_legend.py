"""Legend functionality for Leaflet maps."""

LEGEND_TEMPLATE = """
const legendManager = {
    update() {
        const legendItems = document.getElementById(MAP_ID + '-legend-items');
        if (!legendItems) return;
        
        const colorSchemeSelect = document.getElementById('color-scheme-select');
        const currentScheme = colorSchemeSelect ? colorSchemeSelect.value : '{color_scheme}';
        const colors = COLOR_SCHEMES[currentScheme] || COLOR_SCHEMES.blue;
        
        let title = SELECTED_VARIABLE.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        let labels = [];
        let grades;
        
        if (SELECTED_VARIABLE.includes('poverty') || SELECTED_VARIABLE.includes('rate')) {
            title += ' (%)';
            grades = [[5, 10], [10, 15], [15, 20], [20, 25], [25, 30], [30, 35], [35, 40], [40, 50]];
            
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i][0];
                const to = grades[i][1];
                const isLast = i === grades.length - 1;
                const range = isLast ? from + '%+' : from + '-' + to + '%';
                
                labels.push(
                    '<div class="legend-item">' +
                    '<i style="background:' + colors[i] + '"></i>' + range +
                    '</div>'
                );
            }
        } else if (SELECTED_VARIABLE.includes('income') || SELECTED_VARIABLE.includes('value')) {
            title += ' ($)';
            grades = [40, 50, 60, 70, 80, 90, 100, 110];
            
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast ? from + 'k+' : from + '-' + grades[i+1] + 'k';
                
                labels.push(
                    '<div class="legend-item">' +
                    '<i style="background:' + colors[i] + '"></i>' + range +
                    '</div>'
                );
            }
        } else {
            title += ' (Count)';
            grades = [
                [0, 1], [1, 5], [5, 10], [10, 25], 
                [25, 50], [50, 100], [100, 250], [250, 500]
            ];
            
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i][0];
                const to = grades[i][1];
                const isLast = i === grades.length - 1;
                let range;
                
                if (isLast) {
                    range = from + 'k+';
                } else if (to >= 1) {
                    range = from + 'k-' + to + 'k';
                } else {
                    range = from + '-' + to;
                }
                
                labels.push(
                    '<div class="legend-item">' +
                    '<i style="background:' + colors[i] + '"></i>' + range +
                    '</div>'
                );
            }
        }
        
        const legendTitle = document.querySelector('#' + MAP_ID + '-legend .legend-title');
        if (legendTitle) {
            legendTitle.textContent = title;
        }
        legendItems.innerHTML = labels.join('');
    },
    
    setupColorSchemeHandler() {
        const select = document.getElementById('color-scheme-select');
        if (select) {
            select.addEventListener('change', function(e) {
                const newScheme = e.target.value;
                
                // Update map colors
                map.eachLayer(layer => {
                    if (layer.feature) {
                        const value = layer.feature.properties[SELECTED_VARIABLE];
                        if (value !== undefined) {
                            layer.setStyle({ 
                                fillColor: utils.getColorForValue(value, newScheme) 
                            });
                        }
                    }
                });
                
                legendManager.update();
                
                window.parent.postMessage({
                    type: 'color_scheme_change',
                    color_scheme: newScheme,
                    map_id: MAP_ID
                }, '*');
            });
        }
    }
};
"""

def get_legend_js() -> str:
    """Return the JavaScript code for the legend functionality."""
    return LEGEND_TEMPLATE
