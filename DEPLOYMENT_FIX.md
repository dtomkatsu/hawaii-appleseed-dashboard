# Online Deployment Fix for GeoJSON Loading

## Problem
The online hosted version shows "Failed to load GeoJSON data for Counties" because the file paths are different in the deployment environment compared to local development.

## Solution Implemented

### 1. **Comprehensive Path Search** ✅
Added multiple fallback paths to handle different deployment environments:

```python
possible_base_paths = [
    Path(__file__).parent.parent.parent / 'data' / 'Processed GeoJsons',  # Local development
    Path(__file__).parent.parent.parent / 'data' / 'processed_geojsons',  # Alternative naming
    Path(__file__).parent.parent.parent / 'data',  # Root data directory
    Path.cwd() / 'data' / 'Processed GeoJsons',  # Current working directory
    Path.cwd() / 'data' / 'processed_geojsons',  # Alternative in cwd
    Path.cwd() / 'data',  # Root data in cwd
]
```

### 2. **File Name Variations** ✅
Try different file naming conventions that might exist in deployment:

```python
possible_files = [
    base_path / layer_files[layer_name],  # Original filename
    base_path / f"{layer_files[layer_name]}.gz",  # Compressed version
    base_path / layer_files[layer_name].lower(),  # Lowercase version
    base_path / layer_files[layer_name].replace(' ', '_'),  # Underscore version
]
```

### 3. **Enhanced Error Reporting** ✅
Added detailed logging to help debug deployment issues:

- Lists all searched paths
- Shows available files in each directory
- Reports which files were found/not found
- Provides clear error messages

### 4. **Fallback GeoJSON** ✅
If no files are found, return minimal Hawaii geometry so the app doesn't crash:

```python
def get_fallback_geojson(layer_name):
    """Return a minimal fallback GeoJSON when files are not found."""
    # Returns basic Hawaii county boundaries as rectangles
    # Allows app to function even without original files
```

### 5. **Debug Tools** ✅
Created `debug_files.py` script to run in deployment environment:

```bash
python debug_files.py
```

This will show:
- Current working directory
- Available paths and files
- Environment variables
- Python path

## Deployment Checklist

### For the hosting platform, ensure:

1. **Files are uploaded**: All GeoJSON files in `data/Processed GeoJsons/`
2. **Case sensitivity**: File names match exactly (some systems are case-sensitive)
3. **Path structure**: Maintain the `data/Processed GeoJsons/` directory structure
4. **Permissions**: Files are readable by the application
5. **Compression**: Both `.geojson` and `.geojson.gz` files are present

### Files that must be present:
- ✅ `hawaii_state_boundary.geojson` (+ .gz version)
- ✅ `hawaii_county_boundaries.geojson` (+ .gz version)  
- ✅ `Hawaii_State_House_Districts_2022.geojson` (+ .gz version)
- ✅ `Hawaii_State_Senate_Districts_2022.geojson` (+ .gz version)

## Testing

### Local Testing:
1. Rename the `data` folder temporarily to simulate missing files
2. Run the app - should show fallback geometry
3. Check logs for path searching details

### Online Testing:
1. Deploy with the new code
2. Check application logs for path search results
3. Run `debug_files.py` if needed to investigate file structure
4. Verify fallback works if files are still missing

## Expected Behavior

### If files are found:
- ✅ Normal operation with full GeoJSON data
- ✅ Compressed files used when available
- ✅ Detailed logging of successful file loading

### If files are missing:
- ⚠️ Warning messages in logs about missing files
- ✅ Fallback to basic Hawaii geometry (rectangles)
- ✅ App continues to function
- ✅ Data variables still work (loaded separately by DataLoader)

## Next Steps

1. **Deploy the updated code** with enhanced path searching
2. **Monitor logs** for file loading success/failure messages
3. **Run debug script** if issues persist to understand deployment file structure
4. **Adjust paths** based on actual deployment environment if needed

The app should now be much more resilient to different deployment environments and provide clear debugging information when files are missing.
