"""
ACS Data Dashboard for Hawaii Appleseed
"""
import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from pathlib import Path
import json
from typing import Dict, List, Optional

# Import the ACS data fetcher
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from data.acs_data import ACSDataFetcher

class ACSDashboard:
    """ACS Data Dashboard for Hawaii."""
    
    def __init__(self):
        """Initialize the dashboard."""
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir.parent / 'data'
        self.processed_dir = self.data_dir / 'processed'
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Available metrics and their display names
        self.metrics = {
            'poverty_rate': 'Poverty Rate',
            'median_income': 'Median Income',
            'bachelors_degree': "Bachelor's Degree or Higher",
            'renter_occupied': 'Renter-Occupied Housing Units'
        }
        
        # Geographic levels
        self.levels = {
            'tract': 'Census Tract',
            'county': 'County',
            'block group': 'Block Group'
        }
    
    def load_geojson(self, filename: str) -> Optional[gpd.GeoDataFrame]:
        """Load a GeoJSON file."""
        try:
            path = self.processed_dir / f"{filename}.geojson"
            if path.exists():
                return gpd.read_file(path)
            return None
        except Exception as e:
            st.error(f"Error loading GeoJSON: {str(e)}")
            return None
    
    def create_choropleth_map(
        self, 
        gdf: gpd.GeoDataFrame, 
        column: str,
        legend_name: str,
        fill_color: str = 'YlOrRd',
        fill_opacity: float = 0.7,
        line_opacity: float = 0.2,
        legend_scale: tuple = (0, 1)
    ) -> folium.Map:
        """Create a choropleth map from a GeoDataFrame."""
        # Create a map centered on Hawaii
        m = folium.Map(
            location=[20.8, -157.3],
            zoom_start=7,
            tiles='CartoDB positron'
        )
        
        # Add choropleth layer
        folium.Choropleth(
            geo_data=gdf,
            name='choropleth',
            data=gdf,
            columns=['GEOID', column],
            key_on='feature.properties.GEOID',
            fill_color=fill_color,
            fill_opacity=fill_opacity,
            line_opacity=line_opacity,
            legend_name=legend_name,
            highlight=True,
            reset=True
        ).add_to(m)
        
        # Add tooltip
        tooltip = folium.GeoJsonTooltip(
            fields=['NAME', column],
            aliases=['Location: ', f'{legend_name}: '],
            localize=True,
            sticky=False,
            labels=True,
            style=(
                'background-color: white; color: #333333; '
                'font-family: arial; font-size: 12px; padding: 8px;'
            )
        )
        
        # Add GeoJson layer for interactivity
        geojson_layer = folium.GeoJson(
            gdf,
            style_function=lambda x: {
                'fillColor': 'transparent',
                'color': 'black',
                'weight': 0.5,
                'fillOpacity': 0
            },
            tooltip=tooltip
        )
        geojson_layer.add_to(m)
        
        # Add layer control
        folium.LayerControl().add_to(m)
        
        return m
    
    def render(self):
        """Render the dashboard."""
        st.title("Hawaii ACS Data Explorer")
        
        # Sidebar controls
        st.sidebar.header("Data Options")
        
        # Select metric
        selected_metric = st.sidebar.selectbox(
            "Select a metric:",
            list(self.metrics.values()),
            index=0
        )
        
        # Get the metric key from display name
        metric_key = [k for k, v in self.metrics.items() if v == selected_metric][0]
        
        # Select geographic level
        selected_level = st.sidebar.selectbox(
            "Select geographic level:",
            list(self.levels.values()),
            index=0
        )
        level_key = [k for k, v in self.levels.items() if v == selected_level][0]
        
        # Load the data
        st.sidebar.info("Loading data...")
        gdf = self.load_geojson(f'hi_acs_{level_key}')
        
        if gdf is not None and not gdf.empty:
            st.sidebar.success("Data loaded successfully!")
            
            # Display map
            st.subheader(f"{selected_metric} by {selected_level}")
            
            # Create and display the map
            m = self.create_choropleth_map(
                gdf=gdf,
                column=metric_key,
                legend_name=selected_metric,
                fill_color='YlOrRd',
                fill_opacity=0.7,
                line_opacity=0.2
            )
            
            # Display the map
            folium_static(m, width=900, height=600)
            
            # Display data table
            st.subheader("Data Table")
            st.dataframe(
                gdf[[
                    'NAME', 
                    metric_key,
                    'geometry'
                ]].drop(columns=['geometry']).sort_values(by=metric_key, ascending=False)
            )
            
            # Download button
            st.download_button(
                label="Download Data (CSV)",
                data=gdf.drop(columns=['geometry']).to_csv(index=False).encode('utf-8'),
                file_name=f"hawaii_{metric_key}_{level_key}.csv",
                mime='text/csv'
            )
        else:
            st.warning("No data available. Please run the data pipeline first.")
            
            if st.button("Run Data Pipeline"):
                with st.spinner("Fetching ACS data... This may take a few minutes."):
                    try:
                        # Import and run the data pipeline
                        from data.acs_data import main as run_pipeline
                        run_pipeline()
                        st.success("Data pipeline completed successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error running data pipeline: {str(e)}")

def main():
    """Run the dashboard."""
    dashboard = ACSDashboard()
    dashboard.render()

if __name__ == "__main__":
    main()
