"""Hawaii Appleseed Dashboard - Leaflet Implementation."""
import streamlit as st
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Set up basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import local modules
from src.ui.sidebar import create_sidebar
from src.ui.leaflet_map_view import create_leaflet_map_view, create_data_summary

# Set page config
st.set_page_config(
    page_title="Hawaii Appleseed Dashboard (Leaflet)",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application function."""
    # Load Leaflet CSS
    css_path = Path(__file__).parent / "ui" / "leaflet_style.css"
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    # Initialize sidebar_config with default values
    sidebar_config = {'debug_info': False}
    
    try:
        # Create sidebar and get user selections
        sidebar_config = create_sidebar()
        
        # Main content area
        st.title("Hawaii Geographic Data Explorer")
        
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Map View", "Data Analysis", "About"])
        
        # Tab 1: Map View
        with tab1:
            # Create two columns for the main content
            col1, col2 = st.columns([3, 1])
            
            # Left column - Map View
            with col1:
                create_leaflet_map_view(
                    debug_info=sidebar_config['debug_info']
                )
            
            # Right column - Data Summary
            with col2:
                create_data_summary()
        
        # Tab 2: Data Analysis
        with tab2:
            st.header("Data Analysis")
            st.write("This section contains data tables and charts for analysis.")
            
            # Get the active layer and selected variable
            active_layer = st.session_state.get('active_layer', 'State Boundary')
            selected_variable = st.session_state.get('selected_variable', 'poverty_rate')
            
            # Display a simple data table
            from src.data.data_loader import DataLoader
            data_loader = DataLoader()
            
            # Map geo levels to their data loader equivalents
            geo_level_map = {
                'State Boundary': 'state',
                'Counties': 'county',
                'House Districts': 'house',
                'Senate Districts': 'senate'
            }
            
            geo_level = geo_level_map.get(active_layer, 'state')
            
            # Get data for the current geographic level
            data = data_loader.get_data(geo_level)
            
            # Ensure we have a name column for display
            if data is not None and 'name' not in data.columns:
                if 'NAME' in data.columns:
                    data['name'] = data['NAME']
                elif 'geoid' in data.columns:
                    data['name'] = 'Area ' + data['geoid'].astype(str)
                elif 'district' in data.columns:
                    data['name'] = 'District ' + data['district'].astype(str)
            
            if data is not None:
                # Create a bar chart of the selected variable
                st.subheader(f"{selected_variable.replace('_', ' ').title()} by {active_layer}")
                
                # Format the chart based on the variable type
                if 'rate' in selected_variable or 'pct' in selected_variable:
                    chart_data = data.set_index('name')[[selected_variable]]
                    st.bar_chart(chart_data)
                elif 'income' in selected_variable or 'value' in selected_variable:
                    chart_data = data.set_index('name')[[selected_variable]]
                    st.bar_chart(chart_data)
                else:
                    chart_data = data.set_index('name')[[selected_variable]]
                    st.bar_chart(chart_data)
                
                # Display the full data table
                st.subheader("Full Data Table")
                st.dataframe(data)
                
                # Add download button
                csv = data.to_csv(index=False)
                st.download_button(
                    label="Download Data as CSV",
                    data=csv,
                    file_name=f"hawaii_{geo_level}_data.csv",
                    mime="text/csv",
                    key="analysis_tab_download_button"
                )
            else:
                st.warning(f"No data available for {active_layer}")
        
        # Tab 3: About
        with tab3:
            st.header("About This Dashboard")
            st.write("""
            This dashboard provides interactive visualizations of demographic and socioeconomic data for Hawaii.
            
            ### Data Sources
            - American Community Survey (ACS) 5-Year Estimates
            - Geographic boundaries from the US Census Bureau
            
            ### Features
            - Interactive map with clickable regions
            - Detailed popups with demographic and socioeconomic data
            - Data analysis tools
            
            ### How to Use
            1. Use the map controls to select different geographic layers and variables
            2. Click on regions in the map to see detailed information
            3. Switch between tabs to explore different views of the data
            
            ### Technical Implementation
            This dashboard uses:
            - Streamlit for the web application framework
            - Leaflet.js for interactive mapping
            - Python for data processing and analysis
            """)
            
            # Show credits
            st.markdown("---")
            st.markdown("#### Credits")
            st.markdown("Dashboard developed for Hawaii Appleseed Center for Law & Economic Justice")
        
    except Exception as e:
        logger.error(f"Error in main application: {str(e)}")
        st.error(f"An error occurred: {str(e)}")
        if sidebar_config and sidebar_config.get('debug_info', False):
            st.exception(e)

if __name__ == "__main__":
    main()
