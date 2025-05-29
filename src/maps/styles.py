"""Map styling utilities for the Hawaii Appleseed Dashboard."""
from typing import Dict, Any, Optional

def get_layer_color(layer_name: str) -> str:
    """Get a distinct color for each layer type."""
    colors = {
        'State': '#3186cc',
        'Counties': '#31a354',
        'State House Districts': '#756bb1',
        'State Senate Districts': '#e6550d'
    }
    return colors.get(layer_name, '#3186cc')

def get_style_function(layer_name: str) -> Dict[str, Any]:
    """Get the style function for a layer."""
    return {
        'fillColor': get_layer_color(layer_name),
        'color': 'black',
        'weight': 1,
        'fillOpacity': 0.6,
        'opacity': 0.8,
        'dashArray': '5, 5' if 'Districts' in layer_name else None
    }

def get_highlight_function() -> Dict[str, Any]:
    """Get the highlight style for layers."""
    return {
        'fillColor': '#ff0000',  # Red highlight on hover
        'color': 'yellow',
        'weight': 3,
        'fillOpacity': 0.8,
        'opacity': 1
    }
