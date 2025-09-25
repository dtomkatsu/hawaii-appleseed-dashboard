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
        {'key': 'poverty_rate', 'label': 'Poverty Rate', 'type': 'percentage'},
        {'key': 'median_income', 'label': 'Median Income', 'type': 'currency'},
        {'key': 'unemployment_rate', 'label': 'Unemployment Rate', 'type': 'percentage'},
        {'key': 'college_educated_pct', 'label': 'College Educated', 'type': 'percentage'},
        {'key': 'median_home_value', 'label': 'Median Home Value', 'type': 'currency'},
        {'key': 'alice_rate', 'label': 'ALICE Households', 'type': 'percentage'},
        {'key': 'rent_burden_rate', 'label': 'Housing Cost Burden', 'type': 'percentage'},
        {'key': 'snap_household_rate', 'label': 'SNAP Households', 'type': 'percentage'},
        {'key': 'snap_benefit_annual_per_household', 'label': 'Avg Annual SNAP Benefit', 'type': 'currency'},
        {'key': 'snap_benefits_annual_total', 'label': 'Total Annual SNAP Benefits', 'type': 'currency'},
        {'key': 'travel_time_to_work_minutes', 'label': 'Average Travel Time to Work', 'type': 'minutes'},
        {'key': 'ctc_avg_amount', 'label': 'Child Tax Credit - Average Amount', 'type': 'currency'},
        {'key': 'ctc_participation_rate', 'label': 'Child Tax Credit - Participation Rate', 'type': 'percentage'},
        {'key': 'federal_eitc_avg_amount', 'label': 'Federal EITC - Average Amount', 'type': 'currency'},
        {'key': 'eitc_participation_rate', 'label': 'Federal EITC - Participation Rate', 'type': 'percentage'},
        {'key': 'state_eitc_avg_amount', 'label': 'State EITC - Average Amount', 'type': 'currency'}
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
        
        # For SNAP, travel_time_to_work_minutes, and tax credit variables, be more lenient since they might be merged later
        special_variables = ['snap_household_rate', 'snap_benefit_annual_per_household', 'snap_benefits_annual_total', 
                           'travel_time_to_work_minutes', 'ctc_avg_amount', 'ctc_participation_rate', 
                           'federal_eitc_avg_amount', 'eitc_participation_rate', 'state_eitc_avg_amount', 'median_income']
        if selected_variable in special_variables:
            self.logger.info(f"Special variable '{selected_variable}' expected to be merged - proceeding")
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
                left: 10px;
                background: rgba(255, 255, 255, 0.9);
                padding: 8px 12px;
                border-radius: 4px;
                box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
                border: 1px solid rgba(0, 0, 0, 0.1);
                z-index: 1000;
                max-width: 180px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .info-panel {
                width: 0;
                height: 100vh;  /* Full viewport height */
                overflow-y: auto;  /* Enable vertical scrolling */
                overflow-x: hidden;  /* Prevent horizontal scrolling */
                background: rgba(255, 255, 255, 0.98);
                border-left: 3px solid #1a73e8;
                box-shadow: -2px 0 10px rgba(0,0,0,0.1);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 12px;
                line-height: 1.4;
                color: #333;
                transition: width 0.4s ease-in-out, padding 0.4s ease-in-out;
                position: fixed;
                right: 0;
                top: 0;
                z-index: 1000;
                padding: 0;
                margin: 0;
                box-sizing: border-box;
                /* Hide default scrollbar for WebKit */
                scrollbar-width: none;  /* Firefox */
                -ms-overflow-style: none;  /* IE and Edge */
            }
            
            /* Hide scrollbar for WebKit browsers */
            .info-panel::-webkit-scrollbar {
                display: none;
            }
            .info-panel.visible {
                width: 350px;
                padding: 20px;
                overflow-y: auto;
                height: 100vh;
                box-sizing: border-box;
                position: fixed;
                right: 0;
                top: 0;
                z-index: 1000;
                background: white;
                border-left: 3px solid #1a73e8;
                box-shadow: -2px 0 10px rgba(0,0,0,0.1);
            }
            
            /* Scroll indicator arrow */
            .scroll-indicator {
                position: fixed;
                bottom: 25px;
                right: 25px;
                width: 36px;
                height: 36px;
                background: #1a73e8;
                color: white;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                cursor: pointer;
                z-index: 2000;
                box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
                transition: all 0.3s ease;
                user-select: none;
                opacity: 0.9;
                border: 2px solid white;
            }
            
            .scroll-indicator:hover {
                background: #1557b0;
                transform: scale(1.1);
                box-shadow: 0 4px 12px rgba(26, 115, 232, 0.4);
            }
            
            .scroll-indicator.up {
                animation: pulse-up 1s ease-in-out infinite alternate;
            }
            
            .scroll-indicator.down {
                animation: pulse-down 1s ease-in-out infinite alternate;
            }
            
            @keyframes pulse-up {
                0% { transform: translateY(0); }
                100% { transform: translateY(-3px); }
            }
            
            @keyframes pulse-down {
                0% { transform: translateY(0); }
                100% { transform: translateY(3px); }
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
                           variable_display_name: str, color_scheme: str, show_side_panel: bool = True) -> str:
        """Generate JavaScript code for the map."""
        return f"""
        (function() {{
            // Configuration constants
            const MAP_CONFIG = {{
                center: [20.7984, -156.3319],
                zoom: 7,
                zoomSnap: 0.6,      // Increased from 0.1 for faster zooming
                zoomDelta: 0.8,       // Increased from 0.5 for larger zoom steps
                zoomAnimationThreshold: 4,  // Fewer animation frames
                fadeAnimation: false,       // Disable fade animation
                markerZoomAnimation: false   // Disable marker animation
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
                    if (SELECTED_VARIABLE === 'travel_time_to_work_minutes') {{
                        // Custom thresholds for travel time to work in minutes (30-50 minute range)
                        thresholds = [30, 35, 40, 45, 50];
                    }} else if (SELECTED_VARIABLE === 'public_transportation_pct') {{
                        // Custom thresholds for public transportation percentage (0-6% range)
                        thresholds = [0.5, 1.0, 2.0, 4.0, 6.0];
                    }} else if (SELECTED_VARIABLE === 'ctc_avg_amount' || SELECTED_VARIABLE === 'federal_eitc_avg_amount' || SELECTED_VARIABLE === 'state_eitc_avg_amount') {{
                        // Custom thresholds for tax credit amounts ($500-$3000 range)
                        thresholds = [500, 750, 1000, 1250, 1500, 2000, 2500, 3000, 4000];
                    }} else if (SELECTED_VARIABLE === 'ctc_participation_rate' || SELECTED_VARIABLE === 'eitc_participation_rate') {{
                        // Custom thresholds for tax credit participation rates (5-25% range)
                        thresholds = [5, 8, 10, 12, 15, 18, 20, 22, 25];
                    }} else if (SELECTED_VARIABLE.includes('poverty') || SELECTED_VARIABLE.includes('rate')) {{
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
                
                createCategorizedMetricsHtml(properties) {{
                    const categories = {{
                        'Economic Security': [
                            {{'key': 'alice_rate', 'label': 'ALICE Households', 'type': 'percentage'}},
                            {{'key': 'poverty_rate', 'label': 'Poverty Rate', 'type': 'percentage'}},
                            {{'key': 'median_income', 'label': 'Median Income', 'type': 'currency'}},
                            {{'key': 'unemployment_rate', 'label': 'Unemployment Rate', 'type': 'percentage'}}
                        ],
                        'Food Security': [
                            {{'key': 'snap_household_rate', 'label': 'SNAP Households', 'type': 'percentage'}},
                            {{'key': 'snap_benefit_annual_per_household', 'label': 'Avg Annual SNAP Benefit', 'type': 'currency'}},
                            {{'key': 'snap_benefits_annual_total', 'label': 'Total Annual SNAP Benefits', 'type': 'currency'}}
                        ],
                        'Housing': [
                            {{'key': 'median_home_value', 'label': 'Median Home Value', 'type': 'currency'}},
                            {{'key': 'median_rent', 'label': 'Median Rent', 'type': 'currency'}},
                            {{'key': 'renter_rate', 'label': 'Renter-Occupied', 'type': 'percentage'}},
                            {{'key': 'rent_burden_rate', 'label': 'Housing Cost Burden', 'type': 'percentage'}}
                        ],
                        'Transportation': [
                            {{'key': 'travel_time_to_work_minutes', 'label': 'Avg Commute Time', 'type': 'minutes'}},
                            {{'key': 'public_transportation_pct', 'label': 'Public Transportation %', 'type': 'percentage'}}
                        ],
                        'Education': [
                            {{'key': 'college_educated_pct', 'label': 'College Educated', 'type': 'percentage'}}
                        ],
                        'Tax Credits': [
                            {{'key': 'ctc_avg_amount', 'label': 'Avg Child Tax Credit', 'type': 'currency'}},
                            {{'key': 'ctc_participation_rate', 'label': 'CTC Participation', 'type': 'percentage'}},
                            {{'key': 'federal_eitc_avg_amount', 'label': 'Avg Federal EITC', 'type': 'currency'}},
                            {{'key': 'eitc_participation_rate', 'label': 'EITC Participation', 'type': 'percentage'}},
                            {{'key': 'state_eitc_avg_amount', 'label': 'Avg State EITC', 'type': 'currency'}}
                        ]
                    }};
                    
                    let html = '';
                    
                    Object.keys(categories).forEach(function(categoryName) {{
                        const metrics = categories[categoryName];
                        let categoryHtml = '';
                        let hasCategoryData = false;
                        let metricCount = 0;
                        let rowHtml = '';
                        
                        // Process metrics in pairs
                        for (let i = 0; i < metrics.length; i++) {{
                            const metric = metrics[i];
                            const value = properties[metric.key];
                            if (value === undefined || value === null || isNaN(value)) continue;
                            
                            hasCategoryData = true;
                            const isSelected = metric.key === SELECTED_VARIABLE;
                            const bgColor = isSelected ? '#e8f0fe' : '#f8f9fa';
                            const borderColor = isSelected ? '#1a73e8' : '#e0e0e0';
                            const fontWeight = isSelected ? 'bold' : 'normal';
                            
                            // Start new row if needed
                            if (metricCount % 2 === 0) {{
                                rowHtml = '<div style="display: flex; margin: 0 -3px;">';
                            }}
                            
                            // Add metric card
                            rowHtml += [
                                '<div style="flex: 1; min-width: 0; margin: 3px;">',
                                '<div style="background:', bgColor, '; border: 1px solid ', borderColor, ';',
                                'border-radius: 4px; padding: 6px 8px; height: 100%; font-weight:', fontWeight, ';">',
                                '<div style="font-size: 10px; color: #666; margin-bottom: 2px;',
                                'white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">',
                                metric.label, '</div>',
                                '<div style="font-size: 12px; color: #333;">',
                                utils.formatValue(value, metric.type), '</div>',
                                '</div></div>'
                            ].join('');
                            
                            metricCount++;
                            
                            // Close row if we have two metrics or it's the last one
                            if (metricCount % 2 === 0 || i === metrics.length - 1) {{
                                rowHtml += '</div>';
                                categoryHtml += rowHtml;
                                rowHtml = '';
                            }}
                        }}
                        
                        // Add category to HTML if it has data
                        if (hasCategoryData) {{
                            html += [
                                '<div style="margin-bottom: 16px;">',
                                '<div style="font-size: 13px; font-weight: 600; color: #1a73e8;',
                                'margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px solid #e0e0e0;">',
                                categoryName, '</div>',
                                '<div style="margin: 0 -3px;">', categoryHtml, '</div>',
                                '</div>'
                            ].join('');
                        }}
                    }});
                    
                    // Return final HTML or a message if no data
                    return html || '<div style="color: #999; text-align: center; font-style: italic;">No data available</div>';
                }},
                
                createMetricHtml(metrics, properties) {{
                    // Use the new categorized metrics function
                    return this.createCategorizedMetricsHtml(properties);
                }},
                
                getRepresentativeInfo(properties) {{
                    // Representative data with prefixed keys to distinguish House vs Senate
                    const repData = {{
                        // House Representatives (house_1 - house_51)
                        "house_1": {{"name": "Matthias Kusch", "party": "D", "areas": "Hāmākua, portion of Hilo, Ka'ūmana"}},
                        "house_2": {{"name": "Sue L. Keohokapu-Lee Loy", "party": "D", "areas": "Hilo"}},
                        "house_3": {{"name": "Chris Todd", "party": "D", "areas": "Portion of Hilo, Keaukaha, Orchidlands Estate"}},
                        "house_4": {{"name": "Greggor Ilagan", "party": "D", "areas": "Puna"}},
                        "house_5": {{"name": "Jeanné Kapela", "party": "D", "areas": "North Kona, South Kona"}},
                        "house_6": {{"name": "Nicole Lowen", "party": "D", "areas": "North Kona"}},
                        "house_7": {{"name": "David Tarnas", "party": "D", "areas": "North Kona, South Kohala"}},
                        "house_8": {{"name": "Troy Hashimoto", "party": "D", "areas": "Kahakuloa, Waiheʻe, Waiehu, Wailuku"}},
                        "house_9": {{"name": "Justin Woodson", "party": "D", "areas": "Kahului, Puʻunēnē, Old Sand Hills, Maui Lani"}},
                        "house_10": {{"name": "Angus McKelvey", "party": "D", "areas": "West Maui, Māʻalaea, North Kīhei"}},
                        "house_11": {{"name": "Tina Wildberger", "party": "D", "areas": "South Maui"}},
                        "house_12": {{"name": "Kyle Yamashita", "party": "D", "areas": "Upcountry Maui"}},
                        "house_13": {{"name": "Lynn DeCoite", "party": "D", "areas": "East Maui, Molokaʻi, Lānaʻi, Kahoʻolawe"}},
                        "house_14": {{"name": "Nadine Nakamura", "party": "D", "areas": "Hanalei, Princeville, Kilauea"}},
                        "house_15": {{"name": "James Tokioka", "party": "D", "areas": "Wailua Homesteads, Hanamāʻulu, Līhuʻe, Puhi"}},
                        "house_16": {{"name": "Luke Evslin", "party": "D", "areas": "Wailua, Kapaʻa, Anahola"}},
                        "house_17": {{"name": "Dee Morikawa", "party": "D", "areas": "Niʻihau, Lehua, Kōloa, Waimea"}},
                        "house_18": {{"name": "Mark Hashem", "party": "D", "areas": "Hahaʻione, Kuliʻouʻou, Niu Valley, ʻĀina Haina"}},
                        "house_19": {{"name": "Bertrand Kobayashi", "party": "D", "areas": "Kāhala, Kaimukī, Diamond Head"}},
                        "house_20": {{"name": "Jackson Sayama", "party": "D", "areas": "St. Louis Heights, Pālolo, Mānoa"}},
                        "house_21": {{"name": "Scot Matayoshi", "party": "D", "areas": "Kāneʻohe, Maunawili, Olomana"}},
                        "house_22": {{"name": "Diamond Garcia", "party": "D", "areas": "Waipahu, Village Park, Waikele"}},
                        "house_23": {{"name": "Lisa Kitagawa", "party": "D", "areas": "Kāneʻohe, Kāneʻohe MCAB, Kailua, Waimānalo"}},
                        "house_24": {{"name": "Adrian Tam", "party": "D", "areas": "Waikīkī, Ala Moana"}},
                        "house_25": {{"name": "Sylvia Luke", "party": "D", "areas": "Makiki, Punchbowl, Nuʻuanu, Pauoa"}},
                        "house_26": {{"name": "Della Au Belatti", "party": "D", "areas": "Makiki, Tantalus, Papakōlea, McCully"}},
                        "house_27": {{"name": "Takashi Ohno", "party": "D", "areas": "Nuʻuanu, Liliha, ʻĀlewa Heights, Puʻunui"}},
                        "house_28": {{"name": "John Mizuno", "party": "D", "areas": "Kamehameha Heights, Kalihi Valley, Fort Shafter"}},
                        "house_29": {{"name": "Daniel Holt", "party": "D", "areas": "Kalihi, Pālama, Iwilei, Chinatown"}},
                        "house_30": {{"name": "Sonny Ganaden", "party": "D", "areas": "Kalihi, Hālawa, ʻAiea, Pearlridge"}},
                        "house_31": {{"name": "Aaron Ling Johanson", "party": "D", "areas": "Moanalua, Āliamanu, Foster Village, Hickam"}},
                        "house_32": {{"name": "Linda Ichiyama", "party": "D", "areas": "Moanalua Valley, Moanalua, Āliamanu, Foster Village"}},
                        "house_33": {{"name": "Sam Kong", "party": "D", "areas": "ʻAiea, Pearl City"}},
                        "house_34": {{"name": "Gregg Takayama", "party": "D", "areas": "Pearl City, Waimalu, Pacific Palisades"}},
                        "house_35": {{"name": "Cory Chun", "party": "D", "areas": "Pearl City, Waipahu, Crestview"}},
                        "house_36": {{"name": "Rachele Lamosao", "party": "D", "areas": "Pearl City, Waipahu, Crestview, Manana"}},
                        "house_37": {{"name": "Sean Quinlan", "party": "D", "areas": "Waialua, Haleiwa, Waimea, Sunset Beach"}},
                        "house_38": {{"name": "Elijah Pierick", "party": "R", "areas": "Wahiawā, Mililani, Waipiʻo Acres"}},
                        "house_39": {{"name": "Stacelynn Eli", "party": "D", "areas": "Mililani, Waipiʻo, Waikele"}},
                        "house_40": {{"name": "Rose Martinez", "party": "D", "areas": "Makakilo, Kapolei, Ewa Villages"}},
                        "house_41": {{"name": "Matthew LoPresti", "party": "D", "areas": "Ewa Beach, Ewa by Gentry, Ocean Pointe"}},
                        "house_42": {{"name": "Sharon Har", "party": "D", "areas": "Kapolei, Makakilo, Kalaeloa, Honokai Hale"}},
                        "house_43": {{"name": "Darius Kila", "party": "D", "areas": "Honolulu, Waikīkī, Ala Moana, Kakaʻako"}},
                        "house_44": {{"name": "Cedric Asuega Gates", "party": "D", "areas": "Waianae, Nanakuli, Maili"}},
                        "house_45": {{"name": "Kanani Souza", "party": "D", "areas": "Waianae, Makaha, Makua"}},
                        "house_46": {{"name": "Elijah Pierick", "party": "R", "areas": "North Shore, Wahiawā, Whitmore Village"}},
                        "house_47": {{"name": "Della Au Belatti", "party": "D", "areas": "Kaimuki, Kāhala, Diamond Head"}},
                        "house_48": {{"name": "Patrick Branco", "party": "R", "areas": "Kailua, Waimānalo, Hawaiʻi Kai"}},
                        "house_49": {{"name": "Lisa Marten", "party": "D", "areas": "Hawaiʻi Kai, Portlock, Koko Head"}},
                        "house_50": {{"name": "Gene Ward", "party": "R", "areas": "Hawaiʻi Kai, Koko Marina, Kalama Valley"}},
                        "house_51": {{"name": "Lisa Kitagawa", "party": "D", "areas": "Kāneʻohe, Heʻeia, Ahuimanu"}},
                        
                        // Senate Representatives (senate_1 - senate_25)
                        "senate_1": {{"name": "Lorraine R. Inouye", "party": "D", "areas": "Hilo, Pauka'a, Papaikou, Pepe'ekeo"}},
                        "senate_2": {{"name": "Joy A. San Buenaventura", "party": "D", "areas": "Puna"}},
                        "senate_3": {{"name": "Dru Mamo Kanuha", "party": "D", "areas": "Kona, Ka'ū, Volcano"}},
                        "senate_4": {{"name": "Herbert M. 'Tim' Richards III", "party": "D", "areas": "North Hilo, Hāmākua, Kohala, Waimea, Waikoloa, North Kona"}},
                        "senate_5": {{"name": "Troy N. Hashimoto", "party": "D", "areas": "Wailuku, Kahului, Waihe'e, Waikapu Mauka, Wai'ehu"}},
                        "senate_6": {{"name": "Angus L.K. McKelvey", "party": "D", "areas": "West Maui, South Maui, Moloka'i, Lāna'i, Kaho'olawe"}},
                        "senate_7": {{"name": "Lynn DeCoite", "party": "D", "areas": "East Maui, Moloka'i, Lāna'i, Kaho'olawe"}},
                        "senate_8": {{"name": "Ronald D. Kouchi", "party": "D", "areas": "Kaua'i, Ni'ihau"}},
                        "senate_9": {{"name": "Stanley Chang", "party": "D", "areas": "Hawai'i Kai, Waikīkī, Ala Moana, Kaka'ako"}},
                        "senate_10": {{"name": "Les Ihara", "party": "D", "areas": "Pālolo, St. Louis Heights, Kaimukī, Kāhala"}},
                        "senate_11": {{"name": "Carol Fukunaga", "party": "D", "areas": "Makiki, Mānoa, Pūowaina, Ala Wai"}},
                        "senate_12": {{"name": "Sharon Y. Moriwaki", "party": "D", "areas": "Waikīkī, McCully, Mōʻiliʻili, Ala Wai"}},
                        "senate_13": {{"name": "Karl Rhoads", "party": "D", "areas": "Downtown, Iwilei, Kalihi, Nu'uanu"}},
                        "senate_14": {{"name": "Donna Mercado Kim", "party": "D", "areas": "Kalihi Valley, Liliha, 'Ālewa Heights, Pu'unui"}},
                        "senate_15": {{"name": "Glenn Wakai", "party": "D", "areas": "Kalihi, Mapunapuna, Airport, Salt Lake, Āliamanu"}},
                        "senate_16": {{"name": "Brandon J.C. Elefante", "party": "D", "areas": "'Aiea, Hālawa, Pearlridge, 'Aiea Heights"}},
                        "senate_17": {{"name": "Donovan M. Dela Cruz", "party": "D", "areas": "Wahiawā, Mililani, Mililani Mauka, Waipi'o Acres, Whitmore Village"}},
                        "senate_18": {{"name": "Michelle N. Kidani", "party": "D", "areas": "Mililani Town, Waipi'o Gentry, Crestview, Waikele"}},
                        "senate_19": {{"name": "Henry J.C. Aquino", "party": "D", "areas": "Waipahu, Crestview, Village Park, Waikele"}},
                        "senate_20": {{"name": "Kurt Fevella", "party": "R", "areas": "Ewa Beach, Ocean Pointe, Ewa by Gentry, Iroquois Point"}},
                        "senate_21": {{"name": "Mike Gabbard", "party": "D", "areas": "Kapolei, Makakilo, Kalaeloa, Honokai Hale, Ko Olina"}},
                        "senate_22": {{"name": "Samantha DeCorte", "party": "R", "areas": "Kapolei, 'Ewa Beach, Ocean Pointe, 'Ewa by Gentry"}},
                        "senate_23": {{"name": "Brenton Awa", "party": "R", "areas": "Ko'olauloa, Ko'olaupoko, Kahuku, La'ie, Hau'ula, Punalu'u"}},
                        "senate_24": {{"name": "Jarrett Keohokalole", "party": "D", "areas": "Kāne'ohe, Kailua, He'eia, Ahuimanu"}},
                        "senate_25": {{"name": "Chris Lee", "party": "D", "areas": "Kailua, Lanikai, Waimānalo, Hawai'i Kai"}}
                    }};
                    
                    // Determine district type and number
                    const getDistrictInfo = (properties) => {{
                        let districtType = null;
                        let districtNum = null;
                        
                        // Check if it's a House district
                        if (properties.house_id) {{
                            districtType = 'house';
                            districtNum = String(properties.house_id);
                        }}
                        // Check if it's a Senate district
                        else if (properties.senate_id) {{
                            districtType = 'senate';
                            districtNum = String(properties.senate_id);
                        }}
                        // Fallback to generic ID extraction
                        else {{
                            const rawId = properties.GEOID || properties.geoid || properties.id;
                            if (rawId) {{
                                if (String(rawId).startsWith('150') && String(rawId).length === 5) {{
                                    districtNum = String(parseInt(String(rawId).slice(3)));
                                }} else {{
                                    try {{
                                        districtNum = String(parseInt(rawId));
                                    }} catch (e) {{
                                        return {{ type: null, num: null, key: null }};
                                    }}
                                }}
                                // Default to house if we can't determine type
                                districtType = 'house';
                            }}
                        }}
                        
                        const key = districtType && districtNum ? `${{districtType}}_${{districtNum}}` : null;
                        return {{ type: districtType, num: districtNum, key: key }};
                    }};
                    
                    const districtInfo = getDistrictInfo(properties);
                    
                    if (districtInfo.key && repData[districtInfo.key]) {{
                        const rep = repData[districtInfo.key];
                        return {{
                            html: [
                                '<div style="margin-bottom: 8px; padding: 8px; background-color: #f8f9fa; border-left: 3px solid #1a73e8; border-radius: 4px;">',
                                '  <div style="font-size: 13px; font-weight: 600; color: #1a73e8; margin-bottom: 4px;">Representative</div>',
                                '  <div style="font-size: 12px; color: #333; margin-bottom: 2px;">' + rep.name + ' (' + rep.party + ')</div>',
                                '  <div style="font-size: 11px; color: #666; font-style: italic;">Areas: ' + rep.areas + '</div>',
                                '</div>'
                            ].join(''),
                            hasData: true
                        }};
                    }}
                    
                    return {{ html: '', hasData: false }};
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
                zoomDelta: MAP_CONFIG.zoomDelta,
                zoomAnimation: true,
                zoomAnimationThreshold: MAP_CONFIG.zoomAnimationThreshold,
                fadeAnimation: MAP_CONFIG.fadeAnimation,
                markerZoomAnimation: MAP_CONFIG.markerZoomAnimation,
                preferCanvas: true,  // Better performance for vector layers
                updateWhenIdle: true,  // Only update when pan/zoom ends
                updateWhenZooming: false  // Don't update during zoom animation
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
                    
                    // Only get representative/senator info for house/senate districts
                    const isHouseDistrict = window.location.search.includes('house') || props.DISTRICT || props.house_id;
                    const isSenateDistrict = window.location.search.includes('senate') || props.senate_id;
                    let repInfo = {{ html: '' }}; // Default empty
                    if (isHouseDistrict || isSenateDistrict) {{
                        const repData = utils.getRepresentativeInfo(props);
                        if (repData && repData.html) {{
                            repInfo = repData;
                        }}
                    }}
                    
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
                            '  <div style="margin: 12px 0 20px 0; text-align: center;">',
                            '    <a href="/geo_detail?geo_id=' + encodeURIComponent(String(featureId)) + '" target="_blank" style="display: inline-block; background-color: #3a7710; color: white; padding: 8px 16px; border-radius: 4px; text-decoration: none; font-weight: bold;">',
                            '      View/Print Fact Sheet',
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
                        (repInfo && repInfo.html ? repInfo.html : ''),
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
                    
                    // Handle click to update info panel (JavaScript-only approach)
                    layer.on('click', function(e) {{
                        console.log('Layer clicked');
                        L.DomEvent.stop(e);
                        
                        // Update the info panel with categorized content
                        const categorizedMetrics = utils.createCategorizedMetricsHtml(props);
                        const infoPanelContent = [
                            '<div style="margin-bottom: 15px; text-align: center; font-weight: 600; font-size: 16px; color: #222; padding-bottom: 8px; border-bottom: 2px solid #1a73e8;">',
                            '  ', name,
                            '</div>',
                            (repInfo && repInfo.html ? repInfo.html : ''),
                            '<div style="background: #1a73e8; color: white; padding: 8px 12px; border-radius: 6px; text-align: center; margin: 0 0 15px 0;">',
                            '  <strong>', VARIABLE_DISPLAY_NAME, ': ', formattedValue, '</strong>',
                            '</div>',
                            detailLinkHtml,
                            categorizedMetrics
                        ].join('');
                        
                        // Update the info panel content
                        const infoPanel = document.getElementById(MAP_ID + '-info-panel');
                        if (infoPanel) {{
                            infoPanel.innerHTML = infoPanelContent;
                            infoPanel.style.display = 'block';
                            infoPanel.classList.add('visible');
                            
                            // Trigger map resize after panel animation
                            setTimeout(() => {{
                                const mapInstance = window[MAP_ID];
                                if (mapInstance) {{
                                    mapInstance.invalidateSize();
                                }}
                            }}, 400);
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
            
            // Scroll indicator functionality - embedded directly
            (function() {{
                'use strict';

                // Scroll indicator functionality
                function initScrollIndicator() {{
                    var panel = document.querySelector('.info-panel.visible');
                    if (!panel) {{
                        console.log('No visible panel found, retrying...');
                        setTimeout(initScrollIndicator, 500);
                        return;
                    }}

                    // Remove any existing scroll indicators
                    var existingIndicator = document.querySelector('.scroll-indicator');
                    if (existingIndicator) {{
                        existingIndicator.remove();
                    }}

                    // Create scroll indicator arrow
                    var scrollArrow = document.createElement('div');
                    scrollArrow.className = 'scroll-indicator down';
                    scrollArrow.innerHTML = '▼';
                    document.body.appendChild(scrollArrow);
                    
                    console.log('Scroll indicator created:', scrollArrow);

                    function updateScrollIndicator() {{
                        var scrollTop = panel.scrollTop;
                        var scrollHeight = panel.scrollHeight;
                        var clientHeight = panel.clientHeight;
                        
                        // Check if content is scrollable
                        if (scrollHeight <= clientHeight) {{
                            scrollArrow.style.display = 'none';
                            return;
                        }}
                        
                        scrollArrow.style.display = 'flex';
                        
                        // Check if at bottom
                        var isAtBottom = scrollTop + clientHeight >= scrollHeight - 5;
                        
                        if (isAtBottom) {{
                            scrollArrow.innerHTML = '▲';
                            scrollArrow.className = 'scroll-indicator up';
                        }} else {{
                            scrollArrow.innerHTML = '▼';
                            scrollArrow.className = 'scroll-indicator down';
                        }}
                    }}

                    // Click handler for scroll arrow
                    scrollArrow.addEventListener('click', function() {{
                        var scrollTop = panel.scrollTop;
                        var scrollHeight = panel.scrollHeight;
                        var clientHeight = panel.clientHeight;
                        var isAtBottom = scrollTop + clientHeight >= scrollHeight - 5;
                        
                        if (isAtBottom) {{
                            // Scroll to top
                            panel.scrollTo({{
                                top: 0,
                                behavior: 'smooth'
                            }});
                        }} else {{
                            // Scroll to bottom
                            panel.scrollTo({{
                                top: scrollHeight,
                                behavior: 'smooth'
                            }});
                        }}
                    }});

                    // Initial update
                    updateScrollIndicator();
                    
                    // Update on scroll
                    panel.addEventListener('scroll', updateScrollIndicator);
                    
                    // Update on resize (with debounce)
                    var resizeTimer;
                    window.addEventListener('resize', function() {{
                        clearTimeout(resizeTimer);
                        resizeTimer = setTimeout(updateScrollIndicator, 100);
                    }});
                    
                    // Cleanup function
                    var cleanup = function() {{
                        console.log('Cleaning up scroll indicator');
                        panel.removeEventListener('scroll', updateScrollIndicator);
                        window.removeEventListener('resize', updateScrollIndicator);
                        if (scrollArrow && scrollArrow.parentNode) {{
                            scrollArrow.parentNode.removeChild(scrollArrow);
                        }}
                    }};
                    
                    // Clean up when panel is closed
                    var observer = new MutationObserver(function(mutations) {{
                        if (!document.body.contains(panel)) {{
                            cleanup();
                            observer.disconnect();
                        }}
                    }});
                    observer.observe(document.body, {{ childList: true, subtree: true }});
                    
                    return cleanup;
                }}

                // Initialize with a delay to ensure DOM is ready
                setTimeout(initScrollIndicator, 1000);
            }})();
            
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
        key: Optional[str] = None,
        show_side_panel: bool = True
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
            show_side_panel: Whether to show the JavaScript info panel (default True)
        
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
        <div style="height:{map_height}px; width:100%; margin-bottom:20px; position:relative; display:flex;">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            
            <style>{self._get_css_styles()}</style>
            
            <div id="{map_id}" style="height:100%; flex:1; transition: flex 0.3s ease-in-out;"></div>
            <div id="{map_id}-legend" class="map-legend">
                <div class="legend-title">{variable_display_name}</div>
                <div class="legend-items" id="{map_id}-legend-items"></div>
                <div class="color-scheme-selector">
                    <label for="color-scheme-select">Color Scheme:</label>
                    <select id="color-scheme-select">
                        <option value="blue" {'selected' if current_color_scheme == 'blue' else ''}>Blue</option>
                        <option value="red" {'selected' if current_color_scheme == 'red' else ''}>Red</option>
                        <option value="green" {'selected' if current_color_scheme == 'green' else ''}>Green</option>
                        <option value="purple" {'selected' if current_color_scheme == 'purple' else ''}>Purple</option>
                    </select>
                </div>
            </div>
            {f'<div id="{map_id}-info-panel" class="info-panel" style="display:none;"><div style="text-align: center; color: #666; font-style: italic;">Click on a geography to see details</div></div>' if show_side_panel else ''}
            
            <script>
                {self._get_javascript_code(map_id, geojson_str, selected_variable, variable_display_name, current_color_scheme, show_side_panel)}
            </script>
        </div>
        """
        
        # Render component without key parameter (not supported by st.components.v1.html)
        components.html(
            component_html,
            height=map_height,
            scrolling=False
        )


def create_leaflet_map(
    geojson_data: Union[Dict[str, Any], str], 
    selected_variable: str, 
    variable_display_name: Optional[str] = None, 
    color_scheme: str = "blue", 
    active_layer: str = "Counties",
    map_height: int = 500, 
    key: Optional[str] = None,
    show_side_panel: bool = True
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
        show_side_panel: Whether to show the JavaScript info panel (default True)
    
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
        key=key,
        show_side_panel=show_side_panel
    )