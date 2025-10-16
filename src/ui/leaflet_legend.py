"""Legend functionality for Leaflet maps."""

LEGEND_TEMPLATE = """
const legendManager = {
    update() {
        const legendItems = document.getElementById(MAP_ID + '-legend-items');
        if (!legendItems) return;
        
        const colorSchemeSelect = document.getElementById('color-scheme-select');
        const currentScheme = colorSchemeSelect ? colorSchemeSelect.value : '{color_scheme}';
        
        // Use the selected color scheme (default to blue)
        const colors = COLOR_SCHEMES[currentScheme] || COLOR_SCHEMES.blue;
        
        let title = SELECTED_VARIABLE.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        let labels = [];
        let grades;
        
        // Match thresholds with getColorForValue function
        if (SELECTED_VARIABLE === 'travel_time_to_work_minutes') {
            title = 'Travel Time to Work (minutes)';
            grades = [30, 35, 40, 45, 50];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast ? from + '+' : from + '-' + grades[i+1];
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else if (SELECTED_VARIABLE === 'public_transportation_pct') {
            title = 'Public Transportation (%)';
            grades = [0.5, 1.0, 2.0, 4.0, 6.0];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast ? from + '%+' : from + '-' + grades[i+1] + '%';
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else if (SELECTED_VARIABLE === 'ctc_avg_amount' || SELECTED_VARIABLE === 'federal_eitc_avg_amount' || SELECTED_VARIABLE === 'state_eitc_avg_amount') {
            title += ' ($)';
            grades = [500, 750, 1000, 1250, 1500, 2000, 2500, 3000, 4000];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast ? '$' + (from/1000).toFixed(1) + 'k+' : '$' + (from/1000).toFixed(1) + 'k-' + (grades[i+1]/1000).toFixed(1) + 'k';
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else if (SELECTED_VARIABLE === 'ctc_participation_rate' || SELECTED_VARIABLE === 'eitc_participation_rate') {
            title += ' (%)';
            grades = [5, 8, 10, 12, 15, 18, 20, 22, 25];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast ? from + '%+' : from + '-' + grades[i+1] + '%';
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else if (SELECTED_VARIABLE === 'cep_percentage') {
            title = 'Schools with CEP (%)';
            grades = [10, 20, 30, 40, 50, 60, 70, 80, 90];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast ? from + '%+' : from + '-' + grades[i+1] + '%';
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else if (SELECTED_VARIABLE === 'cep_schools' || SELECTED_VARIABLE === 'total_schools' || SELECTED_VARIABLE === 'cep_display') {
            title = 'Number of Schools';
            grades = [5, 10, 15, 20, 25, 30, 40, 50, 60];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast ? from + '+' : from + '-' + grades[i+1];
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else if (SELECTED_VARIABLE === 'snap_benefit_annual_per_household') {
            title = 'Average Annual SNAP Benefit ($)';
            // More distinct thresholds for average SNAP benefits ($2,500 to $7,000+)
            grades = [2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 7000];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast 
                    ? '$' + from.toLocaleString() + '+' 
                    : '$' + from.toLocaleString() + '-' + (grades[i+1]-1).toLocaleString();
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else if (SELECTED_VARIABLE === 'snap_benefits_annual_total') {
            title = 'Total Annual SNAP Benefits ($)';
            grades = [1000000, 2000000, 5000000, 10000000, 15000000, 20000000, 30000000, 50000000, 75000000];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast 
                    ? '$' + (from/1000000).toFixed(1) + 'M+' 
                    : '$' + (from/1000000).toFixed(1) + 'M-' + (grades[i+1]/1000000).toFixed(1) + 'M';
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else if (SELECTED_VARIABLE.includes('poverty') || SELECTED_VARIABLE.includes('rate')) {
            title += ' (%)';
            grades = [5, 10, 15, 20, 25, 30, 35, 40, 45];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast ? from + '%+' : from + '-' + grades[i+1] + '%';
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else if (SELECTED_VARIABLE.includes('income')) {
            title += ' ($)';
            grades = [40000, 50000, 60000, 70000, 80000, 90000, 100000, 110000, 120000];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                const range = isLast ? '$' + (from/1000) + 'k+' : '$' + (from/1000) + 'k-' + (grades[i+1]/1000) + 'k';
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
            }
        } else {
            title += ' (Count)';
            grades = [0, 1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000];
            for (let i = 0; i < grades.length; i++) {
                const from = grades[i];
                const isLast = i === grades.length - 1;
                let range;
                if (isLast) {
                    range = (from/1000) + 'k+';
                } else if (from >= 1000) {
                    range = (from/1000) + 'k-' + (grades[i+1]/1000) + 'k';
                } else {
                    range = from + '-' + grades[i+1];
                }
                labels.push('<div class="legend-item"><i style="background:' + colors[i] + '; width: 15px; height: 15px; margin-right: 5px; display: inline-block; border: 1px solid #666;"></i>' + range + '</div>');
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
                
                // Update legend
                legendManager.update();
                
                // Notify parent if in iframe
                if (window.parent !== window) {
                    window.parent.postMessage({
                        type: 'color_scheme_change',
                        color_scheme: newScheme,
                        map_id: MAP_ID
                    }, '*');
                }
            });
        }
    }
};
"""

def get_legend_js() -> str:
    """Return the JavaScript code for the legend functionality."""
    return LEGEND_TEMPLATE
