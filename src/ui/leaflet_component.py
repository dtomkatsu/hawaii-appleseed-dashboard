"""Custom Streamlit component for Leaflet map integration."""
import streamlit as st
import streamlit.components.v1 as components
import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, Union

from .leaflet_legend import get_legend_js
from src.config.variable_registry import (
    get_default_metrics,
    get_special_variable_keys,
    get_info_panel_categories_json,
    get_color_thresholds_json,
    get_default_color_thresholds_json,
)


class LeafletMapComponent:
    """A class to handle Leaflet map creation and configuration."""
    
    # Color schemes for the map
    COLOR_SCHEMES = {
        'blue': ['#f7fbff', '#deebf7', '#c6dbef', '#9ecae1', '#6baed6', '#4292c6', '#2171b5', '#08519c', '#08306b'],
        'green': ['#f7fcf5', '#e5f5e0', '#c7e9c0', '#a1d99b', '#74c476', '#41ab5d', '#238b45', '#006d2c', '#00441b'],
        'red': ['#fff5f0', '#fee0d2', '#fcbba1', '#fc9272', '#fb6a4a', '#ef3b2c', '#cb181d', '#a50f15', '#67000d'],
        'purple': ['#fcfbfd', '#efedf5', '#dadaeb', '#bcbddc', '#9e9ac8', '#807dba', '#6a51a3', '#54278f', '#3f007d']
    }
    
    # Default metrics loaded from centralized registry
    DEFAULT_METRICS = get_default_metrics()
    
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
        
        # Special variables that might be merged later — loaded from registry
        special_variables = get_special_variable_keys()
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
                box-shadow: -2px 0 10px rgba(0,0,0,0.1);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 13px;
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
                box-shadow: -2px 0 10px rgba(0,0,0,0.1);
            }
            
            /* Scroll indicator arrow */
            .scroll-indicator {
                position: fixed;
                bottom: 25px;
                right: 25px;
                width: 36px;
                height: 36px;
                background: #3a7710;
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
                background: #2a5a0c;
                transform: scale(1.1);
                box-shadow: 0 4px 12px rgba(42, 90, 12, 0.4);
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
                font-size: 13px;
                color: #1a73e8;
            }
            .legend-item {
                display: flex;
                align-items: center;
                margin: 3px 0;
                font-size: 12px;
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
                font-size: 12px;
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
                font-size: 12px;
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
                background-color: rgba(255, 255, 255, 0.97);
                border: 1px solid rgba(26, 115, 232, 0.35);
                border-radius: 6px;
                box-shadow: 0 3px 12px rgba(0, 0, 0, 0.12);
                padding: 8px 12px;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 13px;
                line-height: 1.3;
                white-space: nowrap;
                pointer-events: none;
                min-width: 140px;
            }
            .tt-name {
                font-weight: 700;
                font-size: 14px;
                color: #1a3a6b;
                margin-bottom: 3px;
            }
            .tt-stat {
                font-size: 13px;
                color: #444;
                font-weight: 500;
            }
            .tt-divider {
                height: 1px;
                background: rgba(0, 0, 0, 0.1);
                margin: 6px 0;
            }
            .tt-rep {
                font-size: 13px;
                color: #555;
                font-weight: 600;
                margin-bottom: 4px;
            }
            .tt-areas {
                font-size: 13px;
                color: #777;
                margin-top: 2px;
                line-height: 1.4;
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
        """
    
    def _get_javascript_code(self, map_id: str, geojson_str: str, selected_variable: str,
                           variable_display_name: str, color_scheme: str, show_side_panel: bool = True,
                           rep_data_json: str = "{}") -> str:
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
                    
                    // Special handling for text types - return as-is
                    if (variableType === 'text' || variableType === 'cep_display') {{
                        return value;  // Already formatted (e.g., "35/55 CEP schools")
                    }}
                    
                    const numValue = parseFloat(value);
                    if (isNaN(numValue)) return 'N/A';
                    
                    // Check for percentage types
                    if (variableType === 'percentage' || 
                        variableType.includes('rate') || 
                        variableType.includes('pct') ||
                        variableType.includes('percent')) {{
                        return numValue.toFixed(1) + '%';
                    }} 
                    // Check for currency types — always round to nearest dollar
                    else if (variableType === 'currency' ||
                             variableType.includes('income') ||
                             variableType.includes('value') ||
                             variableType.includes('benefit')) {{
                        return '$' + Math.round(numValue).toLocaleString();
                    }}
                    // Check for minutes types
                    else if (variableType === 'minutes') {{
                        return numValue.toFixed(1) + ' min';
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

                    // Thresholds loaded from centralized variable registry
                    const THRESHOLD_MAP = {get_color_thresholds_json()};
                    const DEFAULT_THRESHOLDS = {get_default_color_thresholds_json()};
                    const thresholds = THRESHOLD_MAP[SELECTED_VARIABLE] || DEFAULT_THRESHOLDS;

                    for (let i = thresholds.length - 1; i >= 0; i--) {{
                        if (numValue >= thresholds[i]) {{
                            return colors[Math.min(i, colors.length - 1)];
                        }}
                    }}
                    return colors[0];
                }},
                
                createCategorizedMetricsHtml(properties) {{
                    // Categories loaded from centralized variable registry
                    const categories = {get_info_panel_categories_json()};
                    
                    let html = '';
                    let categoryCount = 0;

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
                            // Skip if undefined/null, or if it's a number type and NaN
                            if (value === undefined || value === null) continue;
                            if (metric.type !== 'text' && isNaN(value)) continue;
                            
                            hasCategoryData = true;
                            const isSelected = metric.key === SELECTED_VARIABLE;
                            const bg = isSelected
                                ? 'linear-gradient(135deg, #e8f3df 0%, #d4ebc4 100%)'
                                : 'linear-gradient(135deg, #f8faf5 0%, #f0f4eb 100%)';
                            const accentBar = isSelected
                                ? 'background:#3a7710; height:3px; border-radius:3px 3px 0 0; margin:-1px -1px 4px -1px;'
                                : 'height:0px; margin:0;';
                            const borderColor = isSelected ? '#3a7710' : '#ddebd1';
                            const valueColor = isSelected ? '#1a4a08' : '#2a3a1a';
                            const valueFontSize = isSelected ? '22px' : '18px';

                            // Start new row if needed
                            if (metricCount % 2 === 0) {{
                                rowHtml = '<div style="display: flex; margin: 0 -3px;">';
                            }}

                            // For cep_display, strip redundant "CEP schools" text since label covers it
                            let displayValue = utils.formatValue(value, metric.type);
                            if (metric.key === 'cep_display') {{
                                displayValue = String(value).replace(/\\s*CEP\\s*schools?/i, '').trim();
                            }}

                            // Add metric card — stat-first layout: big number, label beneath
                            rowHtml += [
                                '<div style="flex: 1; min-width: 0; margin: 3px; display: flex; flex-direction: column;">',
                                '<div style="flex: 1; background:', bg, '; border: 1px solid ', borderColor, ';',
                                'border-radius: 8px; padding: 7px 10px 6px; display: flex; flex-direction: column; justify-content: center;">',
                                '<div style="', accentBar, '"></div>',
                                '<div style="font-size:', valueFontSize, '; font-weight: 800; color:', valueColor, ';',
                                'letter-spacing: -0.02em; line-height: 1.1; margin-bottom: 2px;">',
                                displayValue, '</div>',
                                '<div style="font-size: 10px; font-weight: 600; color: #6a8a5a;',
                                'text-transform: uppercase; letter-spacing: 0.06em;',
                                'white-space: normal; line-height: 1.3;">',
                                metric.label, '</div>',
                                '</div></div>'
                            ].join('');
                            
                            metricCount++;

                            // Close row after every pair
                            if (metricCount % 2 === 0) {{
                                rowHtml += '</div>';
                                categoryHtml += rowHtml;
                                rowHtml = '';
                            }}
                        }}

                        // Flush any open row (odd number of metrics) — invisible spacer keeps solo card half-width
                        if (rowHtml) {{
                            rowHtml += '<div style="flex: 1; min-width: 0; margin: 3px; visibility: hidden;"></div></div>';
                            categoryHtml += rowHtml;
                            rowHtml = '';
                        }}
                        
                        // Add category to HTML if it has data
                        if (hasCategoryData) {{
                            const topGap = categoryCount > 0 ? 'margin-top: 28px;' : '';
                            categoryCount++;
                            html += [
                                '<div style="margin-bottom: 18px;' + topGap + '">',
                                '<div style="font-size: 12px; font-weight: 700; color: #2a5a0c;',
                                'text-transform: uppercase; letter-spacing: 0.05em;',
                                'margin-bottom: 8px; padding-bottom: 5px; border-bottom: 2px solid #c8e6b0;">',
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
                    // Representative data loaded from CSV files via Python and injected at render time
                    const repData = {rep_data_json};
                    
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
                                '<div style="margin-bottom: 14px; padding: 10px 12px; background-color: #f0f7e9; border-left: 3px solid #3a7710; border-radius: 6px;">',
                                '  <div style="font-size: 11px; font-weight: 700; color: #2a5a0c; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 5px;">Representative</div>',
                                '  <div style="font-size: 13px; font-weight: 600; color: #1a2e10; margin-bottom: 3px;">' + rep.name + ' <span style="font-weight: 400; color: #6a8a5a;">(' + rep.party + ')</span></div>',
                                '  <div style="font-size: 12px; color: #5a7a4a;">' + rep.areas + '</div>',
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
                        {{'key': 'snap_benefits_annual_total', 'label': 'Total Annual Benefits', 'type': 'currency'}},
                        {{'key': 'cep_percentage', 'label': 'Schools with CEP', 'type': 'percentage'}},
                        {{'key': 'cep_display', 'label': 'CEP Schools', 'type': 'text'}}
                    ];
                    
                    let html = '';
                    let hasData = false;
                    
                    snapMetrics.forEach(metric => {{
                        const value = properties[metric.key];
                        // Allow text fields or numeric fields
                        const isValid = value !== undefined && value !== null && (metric.type === 'text' || !isNaN(value));
                        if (isValid) {{
                            hasData = true;
                            const isSelected = metric.key === SELECTED_VARIABLE;
                            const bgColor = isSelected ? '#e8f0fe' : '#f8f9fa';
                            const borderColor = isSelected ? '#1a73e8' : '#e0e0e0';
                            const fontWeight = isSelected ? 'bold' : 'normal';
                            
                            const formattedValue = utils.formatValue(value, metric.type);
                            
                            html += 
                                '<div style="background: ' + bgColor + '; ' +
                                'border: 1px solid ' + borderColor + '; ' +
                                'border-radius: 4px; padding: 6px 8px; margin: 3px 0; ' +
                                'font-weight: ' + fontWeight + ';">' +
                                '<div style="font-size: 12px; color: #666; margin-bottom: 2px;">' +
                                metric.label + '</div>' +
                                '<div style="font-size: 13px; color: #333;">' +
                                formattedValue + '</div>' +
                                '</div>';
                        }}
                    }});
                    
                    if (!hasData) {{
                        html = '<div style="color: #999; text-align: center; font-style: italic;">No SNAP data available</div>';
                    }}
                    
                    console.log('SNAP HTML length:', html.length, 'hasData:', hasData);
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
                    // Use cep_percentage for coloring when cep_display is selected
                    const colorVariable = SELECTED_VARIABLE === 'cep_display' ? 'cep_percentage' : SELECTED_VARIABLE;
                    return {{
                        fillColor: utils.getColorForValue(feature.properties[colorVariable]),
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
                    // Remove '(2022)' or similar year annotations
                    name = name.replace(/\\s*\\(\\d{{4}}\\)\\s*/g, '').trim();
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
                            }} else if (window.location.search.includes('state') || rawId === '15' || rawId === 15) {{
                                // State level - don't add prefix
                                prefix = null;
                            }}
                            featureId = prefix ? (prefix + '_' + rawId) : rawId;
                        }}
                    }}
                    
                    console.log('Feature properties:', props);
                    console.log('Selected feature ID:', featureId);
                    
                    let detailLinkHtml = '';
                    if (featureId && featureId !== 'undefined' && featureId !== 'null') {{
                        detailLinkHtml = [
                            '  <div style="margin: 0 0 20px 0; text-align: center;">',
                            '    <a href="/geo_detail?geo_id=' + encodeURIComponent(String(featureId)) + '" target="_blank"',
                            '      style="display: inline-block; background: linear-gradient(135deg, #3a7710 0%, #2a5a0c 100%);',
                            '      color: white; padding: 9px 20px; border-radius: 6px; text-decoration: none;',
                            '      font-weight: 600; font-size: 13px; letter-spacing: 0.01em;',
                            '      box-shadow: 0 2px 8px rgba(42, 90, 12, 0.3);">',
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
                        '      <div style="font-size: 13px; color: #666; margin-bottom: 6px; font-weight: bold; text-align: center;">Key Metrics</div>',
                        '      ', (metricsHtml || '<div style="color: #999; text-align: center; font-style: italic;">No metrics available</div>'),
                        '    </div>',
                        '    <!-- SNAP Column -->',
                        '    <div style="width: 48%; border: 1px solid #e0e0e0; border-radius: 4px; padding: 8px;">',
                        '      <div style="font-size: 13px; color: #666; margin-bottom: 6px; font-weight: bold; text-align: center;">SNAP</div>',
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
                            '<div style="position: relative; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid #c8e6b0;">',
                            '  <button id="' + MAP_ID + '-close-panel" style="position: absolute; left: 0; top: 50%; transform: translateY(-50%); background: none; border: none; font-size: 20px; color: #6a8a5a; cursor: pointer; padding: 0; width: 28px; height: 28px; line-height: 28px; border-radius: 50%; transition: all 0.2s;">&times;</button>',
                            '  <div style="font-weight: 700; font-size: 17px; color: #1a2e10; text-align: center; line-height: 1.2;">', name, '</div>',
                            '</div>',
                            '<div style="margin-bottom: 16px; border-radius: 10px; overflow: hidden; border: 1px solid #c8e6b0;">',
                            '  <div style="background: #3a7710; padding: 3px 0; text-align: center;">',
                            '    <span style="font-size: 9px; font-weight: 700; color: rgba(255,255,255,0.85); text-transform: uppercase; letter-spacing: 0.12em;">', VARIABLE_DISPLAY_NAME, '</span>',
                            '  </div>',
                            '  <div style="background: linear-gradient(180deg, #f0f7e8 0%, #e4f0d8 100%); padding: 12px 16px; text-align: center;">',
                            '    <span style="font-size: 32px; font-weight: 900; color: #1a4008; letter-spacing: -0.03em; line-height: 1;">', formattedValue, '</span>',
                            '  </div>',
                            '</div>',
                            (repInfo && repInfo.html ? repInfo.html : ''),
                            detailLinkHtml,
                            categorizedMetrics
                        ].join('');
                        
                        // Update the info panel content
                        const infoPanel = document.getElementById(MAP_ID + '-info-panel');
                        if (infoPanel) {{
                            infoPanel.innerHTML = infoPanelContent;
                            infoPanel.style.display = 'block';
                            infoPanel.classList.add('visible');
                            
                            // Add close button handler
                            const closeBtn = document.getElementById(MAP_ID + '-close-panel');
                            if (closeBtn) {{
                                closeBtn.onclick = function(e) {{
                                    e.stopPropagation();
                                    
                                    // Remove scroll indicator immediately when closing panel
                                    const scrollIndicator = document.querySelector('.scroll-indicator');
                                    if (scrollIndicator) {{
                                        scrollIndicator.style.display = 'none';
                                        scrollIndicator.remove();
                                    }}
                                    
                                    infoPanel.classList.remove('visible');
                                    
                                    setTimeout(() => {{
                                        infoPanel.style.display = 'none';
                                        const mapInstance = window[MAP_ID];
                                        if (mapInstance) {{
                                            mapInstance.invalidateSize();
                                        }}
                                    }}, 300);
                                }};
                                
                                // Add hover effects
                                closeBtn.onmouseover = function() {{
                                    this.style.background = '#e8f3df';
                                    this.style.color = '#2a5a0c';
                                }};
                                closeBtn.onmouseout = function() {{
                                    this.style.background = 'none';
                                    this.style.color = '#6a8a5a';
                                }};
                            }}
                            
                            // Trigger map resize after panel animation
                            setTimeout(() => {{
                                const mapInstance = window[MAP_ID];
                                if (mapInstance) {{
                                    mapInstance.invalidateSize();
                                }}
                            }}, 400);
                        }}
                    }});
                    
                    // Build tooltip content with representative info if available
                    let tooltipContent = '<div class="tt-name">' + name + '</div>' +
                        '<div class="tt-stat">' + VARIABLE_DISPLAY_NAME + ': ' + formattedValue + '</div>';

                    // Add representative info to tooltip if available
                    if (repInfo && repInfo.hasData) {{
                        const tempDiv = document.createElement('div');
                        tempDiv.innerHTML = repInfo.html;
                        const repNameElement = tempDiv.querySelector('div:nth-child(2)');
                        const areasElement = tempDiv.querySelector('div:nth-child(3)');

                        if (repNameElement && areasElement) {{
                            const repName = repNameElement.textContent.trim();
                            let areas = areasElement.textContent.replace('Areas: ', '').trim();

                            // Truncate areas list if it's too long for the tooltip
                            if (areas.length > 80) {{
                                const areasList = areas.split(', ');
                                areas = areasList.slice(0, 2).join(', ');
                                if (areasList.length > 2) {{
                                    areas += ', +' + (areasList.length - 2) + ' more';
                                }}
                            }}

                            tooltipContent += '<div class="tt-divider"></div>';
                            tooltipContent += '<div class="tt-rep">' + repName + '</div>';
                            tooltipContent += '<div class="tt-areas">' + areas + '</div>';
                        }}
                    }}
                    
                    layer.bindTooltip(tooltipContent, {{ className: 'custom-tooltip', offset: [0, -10] }});
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

        # Delegate to the module-level convenience function which uses caching
        create_leaflet_map(
            geojson_data=geojson_data,
            selected_variable=selected_variable,
            variable_display_name=variable_display_name,
            color_scheme=color_scheme,
            active_layer=active_layer,
            map_height=map_height,
            key=key,
            show_side_panel=show_side_panel
        )


_CODE_VERSION = "2026-04-08-v21"  # Bump to bust @st.cache_data after code changes

@st.cache_data(show_spinner=False, max_entries=20)
def _load_rep_data_json() -> str:
    """Load house and senate legislator data from CSVs and return as a JSON string
    suitable for injection into the JS repData object."""
    base = Path(__file__).parent.parent.parent / "data" / "processed"
    rep = {}

    # House districts
    house_csv = base / "hawaii_house_districts_2025_complete.csv"
    if house_csv.exists():
        df = pd.read_csv(house_csv, skiprows=1)
        for _, row in df.iterrows():
            key = f"house_{int(row['District'])}"
            rep[key] = {
                "name": str(row["Representative_Name"]).strip(),
                "party": str(row["Party"]).strip(),
                "areas": str(row["Areas_Covered"]).strip(),
            }

    # Senate districts
    senate_csv = base / "hawaii_senate_districts_2025_complete.csv"
    if senate_csv.exists():
        df = pd.read_csv(senate_csv)
        for _, row in df.iterrows():
            key = f"senate_{int(row['District'])}"
            rep[key] = {
                "name": str(row["Senator_Name"]).strip(),
                "party": str(row["Party"]).strip(),
                "areas": str(row["Areas_Covered"]).strip(),
            }

    return json.dumps(rep)


def _build_cached_map_html(
    geojson_str: str,
    selected_variable: str,
    variable_display_name: str,
    color_scheme: str,
    map_height: int,
    map_id: str,
    show_side_panel: bool,
    rep_data_json: str = "{}",
    _code_version: str = _CODE_VERSION
) -> str:
    """Build and cache the complete HTML string for the map component.

    This is a module-level cached function so that repeated renders with
    the same parameters return the cached HTML instantly instead of
    regenerating ~40 KB of JavaScript and re-serializing CSS.
    """
    component = LeafletMapComponent()
    css_styles = component._get_css_styles()
    js_code = component._get_javascript_code(
        map_id, geojson_str, selected_variable,
        variable_display_name, color_scheme, show_side_panel,
        rep_data_json
    )

    current_color_scheme = color_scheme
    info_panel_html = (
        f'<div id="{map_id}-info-panel" class="info-panel" style="display:none;">'
        f'<div style="text-align: center; color: #666; font-style: italic;">'
        f'Click on a geography to see details</div></div>'
    ) if show_side_panel else ''

    component_html = f"""
    <div style="height:{map_height}px; width:100%; margin-bottom:20px; position:relative; display:flex;">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

        <style>{css_styles}</style>

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
        {info_panel_html}

        <script>
            {js_code}
        </script>
    </div>
    """
    return component_html


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

    This is a convenience function that builds (or retrieves cached) HTML
    and renders it via components.html.

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
    # Convert GeoJSON to dict if it's a string
    if isinstance(geojson_data, str):
        geojson_data = json.loads(geojson_data)

    # Serialize GeoJSON to string (used as both cache key and inline data)
    geojson_str = json.dumps(geojson_data)
    map_id = f"leaflet-map-{key}" if key else "leaflet-map"

    # Format display name
    if variable_display_name is None:
        variable_display_name = selected_variable.replace('_', ' ').title()

    current_color_scheme = st.session_state.get('color_scheme', color_scheme)

    # Load legislator data from CSVs (cached)
    rep_data_json = _load_rep_data_json()

    # Build or retrieve cached HTML
    component_html = _build_cached_map_html(
        geojson_str=geojson_str,
        selected_variable=selected_variable,
        variable_display_name=variable_display_name,
        color_scheme=current_color_scheme,
        map_height=map_height,
        map_id=map_id,
        show_side_panel=show_side_panel,
        rep_data_json=rep_data_json
    )

    # Render component
    components.html(
        component_html,
        height=map_height,
        scrolling=False
    )