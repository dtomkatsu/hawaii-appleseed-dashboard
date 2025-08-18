"""Debug logging utilities for the Hawaii Appleseed Dashboard."""

import logging

logger = logging.getLogger(__name__)

def log_layer_selection(layer_name: str, feature_count: int = None, source: str = None):
    """Log layer selection information."""
    source_info = f" (from {source})" if source else ""
    if feature_count is not None:
        logger.debug(f"Selected layer: {layer_name} with {feature_count} features{source_info}")
    else:
        logger.debug(f"Selected layer: {layer_name}{source_info}")

def log_geojson_loading(file_path: str, feature_count: int = None):
    """Log GeoJSON loading information."""
    if feature_count is not None:
        logger.debug(f"Loaded GeoJSON from {file_path} with {feature_count} features")
    else:
        logger.debug(f"Loading GeoJSON from {file_path}")

def log_error(message: str, exception: Exception = None):
    """Log error information."""
    if exception:
        logger.error(f"{message}: {str(exception)}")
    else:
        logger.error(message)
