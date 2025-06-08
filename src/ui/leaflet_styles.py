"""CSS styles for the Leaflet map component."""

def get_css_styles() -> str:
    """Return the CSS styles for the Leaflet map component.
    
    Returns:
        str: CSS styles as a string
    """
    return """
    <style>
        /* Map container */
        .leaflet-container {
            background: #fff;
            outline: 0;
        }
        
        /* Legend styling */
        .leaflet-control.legend {
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.2);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            max-width: 200px;
        }
        
        .legend-title {
            font-weight: bold;
            margin-bottom: 8px;
            color: #333;
            font-size: 13px;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            margin: 3px 0;
        }
        
        .legend-item i {
            display: inline-block;
            width: 18px;
            height: 18px;
            margin-right: 8px;
            opacity: 0.8;
            border: 1px solid #999;
            border-radius: 3px;
        }
        
        /* Color scheme selector */
        .color-scheme-selector {
            margin-top: 10px;
        }
        
        .color-scheme-selector label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #444;
        }
        
        .color-scheme-selector select {
            width: 100%;
            padding: 5px;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 12px;
        }
        
        /* Popup styling */
        .custom-popup .leaflet-popup-content-wrapper {
            border-radius: 4px;
            padding: 0;
            overflow: hidden;
        }
        
        .custom-popup .leaflet-popup-content {
            margin: 0;
            line-height: 1.4;
        }
        
        /* Tooltip styling */
        .custom-tooltip {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 5px 8px;
            font-size: 12px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }
        
        .custom-tooltip:before {
            border-top-color: #ccc;
        }
        
        .custom-tooltip:after {
            border-top-color: white;
        }
        
        .tooltip-data {
            display: block;
            margin-top: 2px;
            padding-top: 2px;
            border-top: 1px solid #eee;
            font-size: 11px;
            color: #666;
        }
        
        /* Metric items in popup */
        .metric-item {
            margin: 5px 0;
            padding: 5px;
            border-radius: 3px;
            background: #f8f9fa;
            border: 1px solid #e9ecef;
        }
        
        .metric-item.selected {
            background: #e9f5ff;
            border-color: #b8d4f0;
        }
        
        .metric-label {
            font-size: 11px;
            color: #666;
            margin-bottom: 2px;
        }
        
        .metric-value {
            font-size: 13px;
            font-weight: 500;
            color: #333;
        }
        
        /* Responsive adjustments */
        @media (max-width: 768px) {
            .leaflet-control.legend {
                max-width: 160px;
                padding: 8px;
                font-size: 11px;
            }
            
            .legend-item i {
                width: 14px;
                height: 14px;
                margin-right: 6px;
            }
        }
    </style>
    """
