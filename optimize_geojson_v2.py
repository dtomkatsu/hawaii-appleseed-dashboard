#!/usr/bin/env python3
"""
Enhanced GeoJSON Optimization Script v2

Improvements over v1:
1. Geometry simplification using Douglas-Peucker algorithm
2. Property whitelisting to remove unused fields
3. Coordinate precision reduction
4. Gzip compression
5. Detailed size comparison report

Expected savings: 80-90% reduction in file size
"""

import json
import gzip
import os
import math
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional, Set

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Coordinate precision (4 = ~11m accuracy, sufficient for state-level maps)
COORDINATE_PRECISION = 4

# Simplification tolerance in degrees (~0.001 = ~100m at Hawaii's latitude)
# Adjust based on your zoom levels:
#   0.0001 = ~10m (very detailed)
#   0.001  = ~100m (good for zoom 6-10)
#   0.005  = ~500m (coarse, for thumbnails)
SIMPLIFICATION_TOLERANCE = 0.001

# Properties to keep for each layer type
PROPERTY_WHITELIST = {
    'state': {'state_name', 'state_fips', 'state_abbr', 'NAME', 'GEOID', 'name', 'id'},
    'county': {'county_name', 'county_fips', 'state_fips', 'NAME', 'GEOID', 'name', 'id'},
    'house': {'house_id', 'house_name', 'house_abbr', 'county', 'state_house', 'NAME', 'GEOID', 'name', 'id'},
    'senate': {'senate_id', 'senate_name', 'senate_abbr', 'county', 'state_senate', 'NAME', 'GEOID', 'name', 'id'},
}

# File configurations
GEOJSON_FILES = {
    'hawaii_state_boundary.geojson': 'state',
    'hawaii_county_boundaries.geojson': 'county',
    'Hawaii_State_House_Districts_2022.geojson': 'house',
    'Hawaii_State_Senate_Districts_2022.geojson': 'senate',
}


# =============================================================================
# DOUGLAS-PEUCKER SIMPLIFICATION
# =============================================================================

def perpendicular_distance(point: List[float], line_start: List[float], line_end: List[float]) -> float:
    """Calculate perpendicular distance from a point to a line segment."""
    if line_start == line_end:
        return math.sqrt((point[0] - line_start[0])**2 + (point[1] - line_start[1])**2)
    
    # Line length squared
    line_len_sq = (line_end[0] - line_start[0])**2 + (line_end[1] - line_start[1])**2
    
    # Parameter t for projection onto line
    t = max(0, min(1, (
        (point[0] - line_start[0]) * (line_end[0] - line_start[0]) +
        (point[1] - line_start[1]) * (line_end[1] - line_start[1])
    ) / line_len_sq))
    
    # Projection point
    proj_x = line_start[0] + t * (line_end[0] - line_start[0])
    proj_y = line_start[1] + t * (line_end[1] - line_start[1])
    
    return math.sqrt((point[0] - proj_x)**2 + (point[1] - proj_y)**2)


def douglas_peucker(points: List[List[float]], tolerance: float) -> List[List[float]]:
    """
    Simplify a polyline using the Douglas-Peucker algorithm.
    
    Args:
        points: List of [lon, lat] coordinate pairs
        tolerance: Maximum distance threshold in degrees
    
    Returns:
        Simplified list of coordinate pairs
    """
    if len(points) <= 2:
        return points
    
    # Find the point with maximum distance from the line between first and last
    max_dist = 0
    max_idx = 0
    
    for i in range(1, len(points) - 1):
        dist = perpendicular_distance(points[i], points[0], points[-1])
        if dist > max_dist:
            max_dist = dist
            max_idx = i
    
    # If max distance exceeds tolerance, recursively simplify
    if max_dist > tolerance:
        left = douglas_peucker(points[:max_idx + 1], tolerance)
        right = douglas_peucker(points[max_idx:], tolerance)
        return left[:-1] + right
    else:
        # All points between first and last can be removed
        return [points[0], points[-1]]


def simplify_ring(ring: List[List[float]], tolerance: float) -> List[List[float]]:
    """Simplify a polygon ring (closed loop)."""
    if len(ring) <= 4:  # Minimum valid polygon
        return ring
    
    # Remove closing point, simplify, then re-close
    simplified = douglas_peucker(ring[:-1], tolerance)
    
    # Ensure we have at least 3 points for a valid polygon
    if len(simplified) < 3:
        return ring  # Return original if too simplified
    
    # Re-close the ring
    if simplified[0] != simplified[-1]:
        simplified.append(simplified[0])
    
    return simplified


def simplify_coordinates(coords: Any, tolerance: float, is_polygon: bool = False) -> Any:
    """Recursively simplify coordinates based on geometry type."""
    if not coords:
        return coords
    
    # Check if this is a coordinate pair [lon, lat]
    if isinstance(coords[0], (int, float)):
        return coords
    
    # Check if this is a ring (list of coordinate pairs)
    if isinstance(coords[0][0], (int, float)):
        if is_polygon:
            return simplify_ring(coords, tolerance)
        else:
            return douglas_peucker(coords, tolerance)
    
    # Otherwise, recurse into nested structure
    return [simplify_coordinates(c, tolerance, is_polygon) for c in coords]


def simplify_geometry(geometry: Dict[str, Any], tolerance: float) -> Dict[str, Any]:
    """Simplify a GeoJSON geometry object."""
    if not geometry or 'coordinates' not in geometry:
        return geometry
    
    geom_type = geometry.get('type', '')
    coords = geometry['coordinates']
    
    is_polygon = geom_type in ('Polygon', 'MultiPolygon')
    
    simplified_coords = simplify_coordinates(coords, tolerance, is_polygon)
    
    return {
        'type': geom_type,
        'coordinates': simplified_coords
    }


# =============================================================================
# COORDINATE PRECISION
# =============================================================================

def round_coordinates(coords: Any, precision: int) -> Any:
    """Recursively round coordinate precision."""
    if isinstance(coords, (int, float)):
        return round(coords, precision)
    elif isinstance(coords, list):
        return [round_coordinates(c, precision) for c in coords]
    return coords


# =============================================================================
# PROPERTY FILTERING
# =============================================================================

def filter_properties(properties: Dict[str, Any], whitelist: Set[str]) -> Dict[str, Any]:
    """Keep only whitelisted properties."""
    if not properties:
        return {}
    
    filtered = {}
    for key, value in properties.items():
        # Keep if in whitelist (case-insensitive check)
        if key in whitelist or key.lower() in {w.lower() for w in whitelist}:
            filtered[key] = value
    
    # Ensure we always have an id/name for the map
    if 'id' not in filtered and 'GEOID' in filtered:
        filtered['id'] = filtered['GEOID']
    if 'name' not in filtered:
        for name_key in ['NAME', 'house_name', 'senate_name', 'county_name', 'state_name']:
            if name_key in filtered:
                filtered['name'] = filtered[name_key]
                break
    
    return filtered


# =============================================================================
# MAIN OPTIMIZATION
# =============================================================================

def count_coordinates(coords: Any) -> int:
    """Count total coordinate points in a geometry."""
    if isinstance(coords, (int, float)):
        return 0
    if isinstance(coords[0], (int, float)):
        return 1
    return sum(count_coordinates(c) for c in coords)


def optimize_geojson(
    data: Dict[str, Any],
    layer_type: str,
    tolerance: float = SIMPLIFICATION_TOLERANCE,
    precision: int = COORDINATE_PRECISION
) -> Dict[str, Any]:
    """
    Fully optimize a GeoJSON file.
    
    Args:
        data: GeoJSON data
        layer_type: One of 'state', 'county', 'house', 'senate'
        tolerance: Simplification tolerance in degrees
        precision: Coordinate decimal places
    
    Returns:
        Optimized GeoJSON data
    """
    if 'features' not in data:
        return data
    
    whitelist = PROPERTY_WHITELIST.get(layer_type, set())
    
    original_points = 0
    simplified_points = 0
    
    optimized_features = []
    
    for feature in data['features']:
        # Count original points
        if 'geometry' in feature and feature['geometry']:
            original_points += count_coordinates(feature['geometry'].get('coordinates', []))
        
        # Simplify geometry
        simplified_geom = None
        if 'geometry' in feature and feature['geometry']:
            simplified_geom = simplify_geometry(feature['geometry'], tolerance)
            # Round coordinates
            simplified_geom['coordinates'] = round_coordinates(
                simplified_geom['coordinates'], precision
            )
            simplified_points += count_coordinates(simplified_geom.get('coordinates', []))
        
        # Filter properties
        filtered_props = filter_properties(feature.get('properties', {}), whitelist)
        
        optimized_features.append({
            'type': 'Feature',
            'properties': filtered_props,
            'geometry': simplified_geom
        })
    
    logger.info(f"  Coordinates: {original_points:,} -> {simplified_points:,} ({100*(1-simplified_points/max(1,original_points)):.1f}% reduction)")
    
    return {
        'type': 'FeatureCollection',
        'features': optimized_features
    }


def process_file(input_path: Path, output_path: Path, layer_type: str) -> Dict[str, int]:
    """Process a single GeoJSON file."""
    logger.info(f"\nProcessing: {input_path.name}")
    
    # Load original
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    original_size = os.path.getsize(input_path)
    logger.info(f"  Original size: {original_size:,} bytes ({original_size/1024/1024:.2f} MB)")
    logger.info(f"  Features: {len(data.get('features', []))}")
    
    # Optimize
    optimized = optimize_geojson(data, layer_type)
    
    # Save compressed
    with gzip.open(output_path, 'wt') as f:
        json.dump(optimized, f, separators=(',', ':'))
    
    compressed_size = os.path.getsize(output_path)
    reduction = (1 - compressed_size / original_size) * 100
    
    logger.info(f"  Compressed size: {compressed_size:,} bytes ({compressed_size/1024:.1f} KB)")
    logger.info(f"  Total reduction: {reduction:.1f}%")
    
    return {
        'original': original_size,
        'compressed': compressed_size
    }


def main():
    """Main optimization function."""
    base_path = Path(__file__).parent / 'data' / 'Processed GeoJsons'
    
    if not base_path.exists():
        logger.error(f"GeoJSON directory not found: {base_path}")
        return
    
    logger.info("=" * 60)
    logger.info("GeoJSON Optimization v2")
    logger.info("=" * 60)
    logger.info(f"Simplification tolerance: {SIMPLIFICATION_TOLERANCE} degrees (~{SIMPLIFICATION_TOLERANCE * 111000:.0f}m)")
    logger.info(f"Coordinate precision: {COORDINATE_PRECISION} decimals")
    
    total_original = 0
    total_compressed = 0
    
    for filename, layer_type in GEOJSON_FILES.items():
        input_path = base_path / filename
        output_path = base_path / f"{filename}.gz"
        
        if not input_path.exists():
            logger.warning(f"File not found: {input_path}")
            continue
        
        sizes = process_file(input_path, output_path, layer_type)
        total_original += sizes['original']
        total_compressed += sizes['compressed']
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total original:   {total_original:,} bytes ({total_original/1024/1024:.2f} MB)")
    logger.info(f"Total compressed: {total_compressed:,} bytes ({total_compressed/1024:.1f} KB)")
    logger.info(f"Total reduction:  {(1 - total_compressed/total_original)*100:.1f}%")
    logger.info(f"Space saved:      {(total_original - total_compressed)/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
