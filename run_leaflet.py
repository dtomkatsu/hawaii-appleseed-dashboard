"""Hawaii Appleseed Dashboard - Leaflet Version."""
import sys
import logging
from pathlib import Path
import streamlit as st

# Add the src directory to the Python path (use insert to prioritize it)
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import local modules
from utils.logging_utils import setup_logging, log_error
from ui.leaflet_map_view import create_leaflet_map_view, create_data_summary
from config.theme_registry import get_color_scheme_labels, get_typography
from config.ui_strings_registry import get_string, get_strings_section

# Set page config with wide layout and viewport settings
st.set_page_config(
    page_title=get_string("app_title", "Hawaii Appleseed Dashboard"),
    page_icon=get_string("app_icon", "🌴"),
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': get_string("help_url", "https://www.hawaiiappleseed.org/"),
        'About': get_string("app_about", "### Hawaii Appleseed Dashboard")
    }
)

# Suppress deprecation warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Import and apply full-width layout utility
from src.ui.full_width_utils import set_full_width_layout
set_full_width_layout()

# Load all app-level custom styles from a single CSS file
with open(Path(__file__).parent / "src" / "ui" / "app_style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def load_css():
    """Load custom CSS to force light theme."""
    css_file = Path(__file__).parent / "static" / "css" / "force-light-theme.css"
    with open(css_file) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def main():
    """Main application function for the Leaflet version."""
    # Set up logging and load CSS
    logger = logging.getLogger(__name__)
    load_css()
    
    logger.info("Starting Hawaii Appleseed Dashboard - Leaflet Version")
    
    # Load font from theme config
    font_url = get_typography()["font_url"]
    st.markdown(f'<link href="{font_url}" rel="stylesheet">', unsafe_allow_html=True)
    
    # Add basic message handling for color scheme changes
    st.components.v1.html("""
        <script>
            // Handle color scheme changes from map
            window.addEventListener('message', function(event) {
                if (event.data.type === 'color_scheme_change') {
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue',
                        data: event.data
                    }, '*');
                }
            }, false);
        </script>
    """, height=0)
    
    # Handle messages from the iframe
    if 'color_scheme_change' in st.session_state:
        new_color_scheme = st.session_state.pop('color_scheme_change')
        if new_color_scheme in ['blue', 'green', 'red', 'purple']:
            st.session_state['color_scheme'] = new_color_scheme
    
    # Load enhanced component styles (dropdown theming, color variables, etc.)
    with open(Path(__file__).parent / "src" / "ui" / "enhanced_style.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    try:
        # Initialize session state defaults
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = 'Counties'
            logger.info("Initializing session state with Counties layer")
        if 'selected_variable' not in st.session_state:
            st.session_state.selected_variable = 'alice_rate'
        if 'color_scheme' not in st.session_state:
            st.session_state.color_scheme = 'blue'

        # Sidebar: title and color scheme selector
        sidebar_strings = get_strings_section("sidebar")
        st.sidebar.title(sidebar_strings.get("title", "Dashboard"))

        color_schemes = get_color_scheme_labels()

        st.sidebar.markdown(sidebar_strings.get("viz_controls", "### Visualization Controls"))

        try:
            color_index = list(color_schemes.keys()).index(st.session_state.color_scheme)
        except (ValueError, KeyError):
            color_index = 0

        selected_color = st.sidebar.selectbox(
            sidebar_strings.get("color_scheme_label", "Color Scheme:"),
            options=list(color_schemes.keys()),
            format_func=lambda x: color_schemes[x],
            index=color_index,
            key="sidebar_color_selector"
        )
        st.session_state.color_scheme = selected_color

        # Display options
        st.sidebar.markdown(sidebar_strings.get("display_options", "### Display Options"))
        show_legend = st.sidebar.checkbox(sidebar_strings.get("show_legend", "Show Legend"), value=True)
        show_labels = st.sidebar.checkbox(sidebar_strings.get("show_labels", "Show Area Labels"), value=True)
        debug_info = st.sidebar.checkbox(sidebar_strings.get("debug_info", "Show Debug Info"), value=False)

        # Add minimal space before tabs
        st.markdown("<div style='margin-top: 0.1rem;'></div>", unsafe_allow_html=True)
        
        # Create tabs for different views
        tabs_config = get_strings_section("tabs")
        tab1, tab2 = st.tabs([tabs_config.get("map", "Map View"), tabs_config.get("data", "Data Analysis")])
        
        # Map View Tab
        with tab1:
            create_leaflet_map_view(debug_info=debug_info)
        
        # Data Analysis Tab
        with tab2:
            create_data_summary()
        
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        logger.error(error_msg, exc_info=True)
        st.error(error_msg)

if __name__ == "__main__":
    main()
