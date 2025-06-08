# Hawaii Appleseed Data Dashboard 🌺

An interactive data visualization dashboard for Hawaii Appleseed built with Streamlit and Leaflet.js.

## Main Application

The main application is `run_leaflet.py`, which serves as the entry point for the Leaflet-based dashboard. It provides an interactive map interface with various data visualization capabilities.

### Key Components

1. **Leaflet Map View** (`src/ui/leaflet_map_view.py`)
   - Main component for rendering interactive maps
   - Handles layer management and data visualization
   - Supports multiple geographic levels (State, Counties, House Districts, Senate Districts)

2. **Leaflet Component** (`src/ui/leaflet_component.py`)
   - Core map rendering and interaction logic
   - Manages color schemes and map styling
   - Handles user interactions and events

3. **Data Loading** (`src/data/data_loader.py`)
   - Loads and processes demographic and economic data
   - Handles GeoJSON and CSV data sources
   - Manages data caching and retrieval

4. **UI Components**
   - `sidebar.py`: Handles user interface controls and filters
   - `leaflet_legend.py`: Manages map legend generation
   - `leaflet_style.css`: Custom styling for the Leaflet map components

## Features

- Interactive choropleth maps with multiple data layers
- Real-time data visualization with tooltips and popups
- Responsive design that works on all devices
- Multiple geographic levels (State, Counties, Legislative Districts)
- Customizable color schemes and data variables
- Detailed data exploration and comparison tools

## 🚀 Setup

### Automatic Virtual Environment Activation (Recommended)

1. **Windows PowerShell**:
   - Simply right-click in the project folder and select "Open in Terminal" or "Open in Integrated Terminal" (VSCode).
   - The virtual environment will activate automatically.

2. **Manual Activation**:
   ```powershell
   # In PowerShell
   .\Activate.ps1
   ```

   Or if using Command Prompt:
   ```cmd
   venv\Scripts\activate
   ```

3. Install dependencies (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

4. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```

5. The app will open automatically in your default web browser at `http://localhost:8501`

### Note for Cascade Users
- The virtual environment will automatically activate when you open a terminal in the project directory.
- If you get a permission error, you may need to change the execution policy first:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
  ```

## Project Structure

- `app.py` - Main Streamlit application
- `requirements.txt` - Python dependencies
- `debug.log` - Error and debug logs
- `data/` - Directory for data files (create and add your data here)
- `assets/` - Directory for static assets (optional)

## 📊 Data Requirements

Place your data files in the `data/` directory. The app currently supports:
- CSV files with latitude/longitude columns for mapping
- Excel files with location data
- GeoJSON files for custom map layers

## 🤝 Contributing

1. Create a new branch for your feature
2. Make your changes
3. Test thoroughly
4. Submit a pull request
