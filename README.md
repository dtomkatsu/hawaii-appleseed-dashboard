# Hawaii Appleseed Data Dashboard 🌺

An interactive data visualization dashboard for Hawaii Appleseed built with Streamlit and Folium.

## Features

- Interactive map of Hawaii with data points
- Real-time data visualization
- Responsive design for all devices
- Data filtering and exploration tools

## 🚀 Setup

1. Activate the virtual environment:
   ```bash
   .\venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the Streamlit application:
   ```bash
   streamlit run app.py
   ```

4. The app will open automatically in your default web browser at `http://localhost:8501`

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
