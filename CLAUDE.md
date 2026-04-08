---
name: hawaii-appleseed-dashboard
description: Interactive data dashboard for Hawaii Appleseed with maps and visualizations
---

# Hawaii Appleseed Data Dashboard

An interactive data visualization dashboard built with Streamlit and Leaflet.js, visualizing demographics, economics, and policy data for Hawaii.

## Project Overview

- **Purpose**: Interactive dashboard for Hawaii Appleseed staff and partners to explore state, county, and district-level data
- **Stack**: Python, Streamlit, Leaflet.js, GeoJSON, CSV data
- **Entry point**: `run_leaflet.py`
- **Location**: `/Users/devinthomas/hawaii-appleseed-dashboard/`

## Key Components

### UI Layer
- `src/ui/leaflet_map_view.py` — Main interactive map interface
- `src/ui/leaflet_component.py` — Map rendering and interaction logic
- `src/ui/sidebar.py` — Filters and controls
- `src/ui/leaflet_legend.py` — Map legend
- `src/ui/leaflet_style.css` — Custom styling

### Data Layer
- `src/data/data_loader.py` — Loads and caches data (GeoJSON, CSV)
- Data sources: GeoJSON for boundaries, CSV for metrics
- Geographic levels: State, Counties, House Districts, Senate Districts

## Running the App

```bash
streamlit run run_leaflet.py
```

Access at `http://localhost:8501`

## Common Tasks

- Add new data layer (GeoJSON boundary + CSV metrics)
- Update color schemes or legends
- Fix data loading errors
- Improve map interactivity or performance

## Data Structure

Each visualization layer needs:
1. **GeoJSON file** — geographic boundaries (state, county, district)
2. **CSV file** — metrics keyed to geographic units
3. **Style config** — colors, legend, tooltips

## Style

- Accessible color schemes (colorblind-friendly when possible)
- Clear legends and tooltips
- Responsive to different screen sizes
- Fast load times (cache data)

## Development

- Use `src/` for modular components
- Keep data loading separate from UI logic
- Test with different data sizes
