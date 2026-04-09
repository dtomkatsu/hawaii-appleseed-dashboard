"""Hawaii Appleseed Dashboard - Leaflet Version."""
import os
import sys
import logging
import json
from pathlib import Path
from functools import lru_cache
import streamlit as st
from streamlit.web.server.websocket_headers import _get_websocket_headers

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Import local modules
from utils.logging_utils import setup_logging, log_error
from ui.sidebar import create_sidebar
from ui.leaflet_map_view import create_leaflet_map_view, create_data_summary

# Set page config with wide layout and viewport settings
st.set_page_config(
    page_title="Hawaii Appleseed Dashboard",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.hawaiiappleseed.org/',
        'About': "### Hawaii Appleseed Dashboard\nInteractive data visualization tool for Hawaii"
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

def handle_message(message):
    """Handle messages from the iframe."""
    try:
        if message.type == 'message':
            data = message.get('data', {})
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    return
            
            if data.get('type') == 'color_scheme_change':
                new_color_scheme = data.get('color_scheme')
                if new_color_scheme and new_color_scheme in ['blue', 'green', 'red', 'purple']:
                    st.session_state['color_scheme'] = new_color_scheme
                    st.rerun()
    except Exception as e:
        logger.error(f"Error handling message: {e}")

def serve_static_file(file_path):
    """Serve a static file from the static directory."""
    static_dir = Path(__file__).parent / 'static'
    full_path = (static_dir / file_path).resolve()
    
    # Security check to prevent directory traversal
    try:
        full_path.relative_to(static_dir)
    except ValueError:
        return None
    
    if not full_path.exists():
        return None
    
    # Determine content type based on file extension
    content_type = {
        '.html': 'text/html',
        '.css': 'text/css',
        '.js': 'application/javascript',
        '.json': 'application/json',
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.svg': 'image/svg+xml',
        '.ico': 'image/x-icon',
        '.woff': 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf': 'font/ttf',
        '.eot': 'application/vnd.ms-fontobject',
        '.otf': 'font/otf'
    }.get(full_path.suffix.lower(), 'application/octet-stream')
    
    with open(full_path, 'rb') as f:
        return f.read(), content_type

@lru_cache(maxsize=128)
def get_geo_data(geo_id):
    """Get geographic data for a given ID."""
    # This is a placeholder - in a real app, you'd fetch this from your data source
    # For now, we'll return a mock response
    return {
        'id': geo_id,
        'name': f'Location {geo_id}',
        'type': 'county',
        'demographics': {
            'total_population': 100000,
            'age_distribution': {
                '0-17': 20,
                '18-34': 25,
                '35-54': 30,
                '55-64': 15,
                '65+': 10
            },
            'race_distribution': {
                'White': 40,
                'Native Hawaiian/Pacific Islander': 30,
                'Asian': 20,
                'Other': 10
            }
        },
        'economic': {
            'median_income': 75000,
            'poverty_rate': 10.5,
            'unemployment_rate': 5.2,
            'employment': {
                'employed': 65,
                'unemployed': 5,
                'not_in_labor_force': 30
            }
        },
        'housing': {
            'median_home_value': 650000,
            'homeownership_rate': 55.5,
            'median_rent': 2000,
            'median_home_value_trend': {
                '2018': 550000,
                '2019': 580000,
                '2020': 600000,
                '2021': 620000,
                '2022': 650000
            }
        },
        'geometry': {
            'type': 'Polygon',
            'coordinates': [[
                [-157.965, 21.482],
                [-157.955, 21.482],
                [-157.955, 21.492],
                [-157.965, 21.492],
                [-157.965, 21.482]
            ]]
        },
        'centroid': [-157.96, 21.487],
        'bbox': [-157.965, 21.482, -157.955, 21.492]
    }

def handle_geo_api(geo_id):
    """Handle API requests for geographic data."""
    try:
        geo_data = get_geo_data(geo_id)
        return json.dumps(geo_data), 'application/json'
    except Exception as e:
        return json.dumps({'error': str(e)}), 'application/json', 500

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
    
    # Check if this is a request for a static file or API endpoint
    query_params = st.query_params
    request_path = query_params.get('__path__', '/')
    
    # Handle static file requests
    if request_path.startswith('/static/'):
        file_path = request_path[8:]  # Remove '/static/' prefix
        response = serve_static_file(file_path)
        if response:
            content, content_type = response
            st.markdown(f'<meta http-equiv="refresh" content="0;url=/static/{file_path}">', unsafe_allow_html=True)
            return
    
    # Handle API requests
    if request_path.startswith('/api/geo/'):
        geo_id = request_path.split('/')[-1]
        content, content_type, *status = handle_geo_api(geo_id)
        st.write(content)
        st.stop()
    
    # Regular page load - render the main app
    logger.info("Starting Hawaii Appleseed Dashboard - Leaflet Version")
    
    # Load Roboto font (CSS is loaded from app_style.css at module level)
    st.markdown('<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">', unsafe_allow_html=True)
    
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
        # Initialize session state for county layer if not already set
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = 'Counties'
            logger.info("Initializing session state with Counties layer")
        
        # Create custom sidebar with green labels
        st.sidebar.title("🌴 Hawaii Appleseed Dashboard")
        
        # Define layer options
        layer_options = [
            'State Boundary',
            'Counties',
            'House Districts',
            'Senate Districts'
        ]
        
        # Initialize session state for active layer if not set
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = 'Counties'
        
        # Variable options with descriptions
        variable_options = {
            'poverty_rate': 'Poverty Rate',
            'median_income': 'Median Income',
            'college_educated_pct': 'Bachelor\'s Degree or Higher (%)',
            'rent_burden_rate': 'Housing Cost Burden (%)',
            'alice_rate': 'ALICE Households (%)',
            'white_alone_pct': 'White Alone (%)',
            'asian_alone_pct': 'Asian Alone (%)',
            'native_hawaiian_pi_pct': 'Native Hawaiian/Pacific Islander (%)',
            'snap_household_rate': 'SNAP Households (%)',
            'snap_benefit_annual_per_household': 'Avg Annual SNAP Benefit ($)',
            'snap_benefits_annual_total': 'Total Annual SNAP Benefits ($)',
            'travel_time_to_work_minutes': 'Average Travel Time to Work (minutes)',
            'public_transportation_pct': 'Public Transportation Commuters (%)',
            'ctc_avg_amount': 'Child Tax Credit - Average Amount ($)',
            'ctc_participation_rate': 'Child Tax Credit - Participation Rate (%)',
            'federal_eitc_avg_amount': 'Federal EITC - Average Amount ($)',
            'eitc_participation_rate': 'Federal EITC - Participation Rate (%)',
            'state_eitc_avg_amount': 'State EITC - Average Amount ($)'
        }
        
        # Initialize selected variable if not set
        if 'selected_variable' not in st.session_state:
            st.session_state.selected_variable = 'alice_rate'
        
        # Color scheme options with descriptive names
        color_schemes = {
            'blue': 'Blue Scale',
            'green': 'Green Scale',
            'red': 'Red Scale',
            'purple': 'Purple Scale'
        }
        
        # Initialize color scheme if not set
        if 'color_scheme' not in st.session_state:
            st.session_state.color_scheme = 'blue'
        
        # Data visualization controls
        st.sidebar.markdown("### 📊 Visualization Controls")
        
        # Note: Geography and variable selection moved to main content area
        # This provides better layout and prevents sidebar/main content conflicts
        
        # Color scheme selection
        st.sidebar.markdown('<p style="color:#2a5a0c; font-family:Roboto; font-weight:600; margin-bottom:0px;">Color Scheme:</p>', unsafe_allow_html=True)
        
        # Safe color scheme index calculation
        try:
            color_index = list(color_schemes.keys()).index(st.session_state.color_scheme)
        except (ValueError, KeyError):
            color_index = 0
            
        selected_color = st.sidebar.selectbox(
            "",
            options=list(color_schemes.keys()),
            format_func=lambda x: color_schemes[x],
            index=color_index,
            key="sidebar_color_selector"
        )
        st.session_state.color_scheme = selected_color
        
        # Display options
        st.sidebar.markdown("### 🔧 Display Options")
        show_legend = st.sidebar.checkbox("Show Legend", value=True)
        show_labels = st.sidebar.checkbox("Show Area Labels", value=True)
        debug_info = st.sidebar.checkbox("Show Debug Info", value=False)
        
        # Create sidebar config dictionary
        sidebar_config = {
            'active_layer': st.session_state.active_layer,
            'selected_variable': st.session_state.selected_variable,
            'color_scheme': st.session_state.color_scheme,
            'show_legend': show_legend,
            'show_labels': show_labels,
            'debug_info': debug_info
        }
        
        # Main content area
        
        # Apply JavaScript to ensure form labels are green
        st.markdown("""
        <script>
            // Function to change label colors
            function setLabelColors() {
                // Target all label elements
                const labels = document.querySelectorAll('.stSelectbox label, .stRadio label');
                labels.forEach(label => {
                    label.style.color = '#2a5a0c';
                    label.style.fontWeight = '600';
                    // Also target child elements
                    const children = label.querySelectorAll('*');
                    children.forEach(child => {
                        child.style.color = '#2a5a0c';
                        child.style.fontWeight = '600';
                    });
                });
            }
            
            // Run immediately and also after a short delay to catch dynamically loaded elements
            setLabelColors();
            setTimeout(setLabelColors, 500);
            setTimeout(setLabelColors, 1000);
            
            // Create a MutationObserver to watch for DOM changes
            const observer = new MutationObserver(function(mutations) {
                setLabelColors();
            });
            
            // Start observing once the DOM is fully loaded
            document.addEventListener('DOMContentLoaded', function() {
                observer.observe(document.body, { childList: true, subtree: true });
            });
        </script>
        """, unsafe_allow_html=True)
        
        # Clean and simple dashboard without complex URL handling
        
        # Add minimal space before tabs
        st.markdown("<div style='margin-top: 0.1rem;'></div>", unsafe_allow_html=True)
        
        # Create tabs for different views
        tab1, tab2 = st.tabs(["🗺️ Map View", "📊 Data Analysis"])
        
        # Map View Tab
        with tab1:
            create_leaflet_map_view(
                debug_info=sidebar_config.get('debug_info', False)
            )
        
        # Data Analysis Tab
        with tab2:
            create_data_summary()
        
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        logger.error(error_msg, exc_info=True)
        st.error(error_msg)

if __name__ == "__main__":
    main()
