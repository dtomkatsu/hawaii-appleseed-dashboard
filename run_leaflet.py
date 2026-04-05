"""Hawaii Appleseed Dashboard - Leaflet Version."""
import os
import sys
import logging
import json
from datetime import datetime
from pathlib import Path
from functools import lru_cache
import streamlit as st

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Import local modules
from utils.logging_utils import setup_logging, log_error
from ui.sidebar import create_sidebar
from ui.leaflet_map_view import create_leaflet_map_view, create_data_summary

# Set page config with wide layout and viewport settings
st.set_page_config(
    page_title="Data Dashboard",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'https://www.hawaiiappleseed.org/',
        'About': "Interactive data visualization tool for Hawaii"
    }
)

# Suppress deprecation warnings
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

# Import and apply full-width layout utility
from src.ui.full_width_utils import set_full_width_layout
set_full_width_layout()



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

@lru_cache(maxsize=1)
def _get_all_css() -> str:
    """Return the complete consolidated CSS for the app, cached.

    Combines all styles into one string so that a single st.markdown()
    call injects everything — no repeated parsing of scattered blocks.
    Also includes Google Fonts as a single preconnect + combined request.

    NOTE: CSS file contents are concatenated (not interpolated) to avoid
    f-string interpreting { } characters in the CSS as format expressions.
    """
    base_dir = Path(__file__).parent

    # Read external CSS files once (cached after first call)
    force_light = (base_dir / "static" / "css" / "force-light-theme.css").read_text()
    enhanced = (base_dir / "src" / "ui" / "enhanced_style.css").read_text()

    # Static CSS — uses plain string (no f-string) so { } aren't interpreted
    static_css = """
        /* ── Layout & spacing ── */
        html, body, #root, #root > div, #root > div > div,
        .stApp, .appview-container, .main, .block-container,
        [data-testid="stAppViewContainer"],
        [data-testid="stSidebar"],
        [data-testid="stSidebarContent"],
        [data-testid="stVerticalBlock"],
        [data-testid="stVerticalBlockBorderWrapper"] {
            margin-top: 0 !important;
            padding-top: 0 !important;
            min-height: 0 !important;
        }
        .stApp > div:first-child,
        .appview-container > div:first-child,
        [data-testid="stAppViewContainer"] > div:first-child,
        .main > div:first-child {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlockBorderWrapper"] > div {
            margin-top: 0 !important;
            padding-top: 0 !important;
            gap: 0 !important;
        }
        [data-testid="stVerticalBlock"] { gap: 0.25rem !important; row-gap: 0.25rem !important; }
        h1 { margin-bottom: 0.5rem !important; padding-bottom: 0 !important; }
        [role="tablist"] { margin-top: 0.5rem !important; }
        .main .block-container { padding-left: 1rem; padding-right: 1rem; max-width: 100% !important; }
        .stApp > div:first-child { margin-top: -1rem; }

        /* ── Sidebar: hidden (collapsed via set_page_config) ── */
        section[data-testid="stSidebar"],
        div[data-testid="stSidebarNav"],
        [data-testid="stSidebarCollapsedControl"],
        [data-testid="stLogoSpacer"],
        div[data-testid="collapsedControl"],
        button[title="View app navigation"],
        header[data-testid="stHeader"] {
            display: none !important;
        }

        /* ── Map container ── */
        .stMap, .map-container, .leaflet-container {
            width: 100% !important; height: 70vh !important; min-height: 500px;
            border-radius: 10px; overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); margin-bottom: 20px;
        }

        /* ── Typography ── */
        h1, h2, h3, h4, h5, h6,
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3,
        .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {
            font-family: 'Roboto', sans-serif !important;
        }
        .stSelectbox > label, .stRadio > label, .stButton > button,
        .stTextInput > label, .stNumberInput > label, .stSlider > label,
        .stMultiSelect > label, div[data-testid='stForm'] label,
        div[data-baseweb='form-control'] > div:first-child {
            font-family: 'Roboto', sans-serif !important;
            color: #2a5a0c !important;
            font-weight: 600 !important;
        }
        .stSelectbox > label > div:first-child,
        div[data-testid='stForm'] label > div:first-child { color: #2a5a0c !important; }
        .dashboard-title {
            font-family: 'Poppins', sans-serif; color: #3a7710;
            margin: 0; padding: 0; line-height: 1; font-weight: 600; letter-spacing: -0.5px;
        }

        /* ── Dropdowns ── */
        .stSelectbox > div > div { min-height: 40px; display: flex !important; align-items: center !important; }
        [data-baseweb="select"] { color: #000 !important; }
        [data-baseweb="menu"] {
            background: white !important; color: #000 !important;
            padding: 4px 0; opacity: 0; transform: translateY(-10px);
            animation: menuFadeIn 0.2s forwards;
        }
        [data-baseweb="menu"] [role="option"] {
            min-height: 40px !important; padding: 8px 16px !important;
            white-space: normal !important; line-height: 1.4 !important; color: #000 !important;
            transition: all 0.2s ease; opacity: 0; transform: translateY(-5px);
            animation: itemFadeIn 0.2s forwards;
        }
        [data-baseweb="menu"] [role="option"]:hover {
            background-color: #f5f8ff; transform: translateY(0) translateX(8px); padding-left: 20px;
        }
        [data-baseweb="menu"] [role="option"]:nth-child(1) { animation-delay: 0.05s; }
        [data-baseweb="menu"] [role="option"]:nth-child(2) { animation-delay: 0.1s; }
        [data-baseweb="menu"] [role="option"]:nth-child(3) { animation-delay: 0.15s; }
        [data-baseweb="menu"] [role="option"]:nth-child(4) { animation-delay: 0.2s; }
        [data-baseweb="menu"] [role="option"]:nth-child(5) { animation-delay: 0.25s; }
        [data-baseweb="popover"] {
            z-index: 1000 !important; border-radius: 4px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
            padding: 4px 0 !important; margin: 0 !important;
        }
        [data-baseweb="popover"] > div {
            max-height: 400px !important; border-radius: 4px !important;
            padding: 0 !important; margin: 0 !important; border: none !important;
        }
        [data-baseweb="popover"] ul[role="listbox"] { padding: 0 !important; margin: 0 !important; list-style: none !important; }
        [data-baseweb="popover"] li[role="option"] {
            all: unset !important; display: block !important; padding: 8px 16px !important;
            background: white !important; border-left: 3px solid transparent !important;
            transition: all 0.2s ease !important; cursor: pointer !important;
            line-height: 1.5 !important; min-height: 36px !important;
            box-sizing: border-box !important; white-space: nowrap !important; overflow: hidden !important;
        }
        [data-baseweb="popover"] li[role="option"]:hover {
            background-color: #f5f8ff !important; border-left-color: #1E88E5 !important;
            transform: translateX(8px) !important; padding-left: 20px !important;
        }
        [data-baseweb="popover"] li[aria-selected="true"] { background-color: #e3f2fd !important; font-weight: 500 !important; }
        @keyframes menuFadeIn { to { opacity: 1; transform: translateY(0); } }
        @keyframes itemFadeIn { to { opacity: 1; transform: translateY(0); } }
    """

    return (
        "<style>\n"
        "@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600"
        "&family=Roboto:wght@400;500;700&display=swap');\n"
        "/* ── Force light theme ── */\n"
        + force_light + "\n"
        "/* ── Enhanced component styles ── */\n"
        + enhanced + "\n"
        + static_css
        + "\n</style>"
    )


def load_css():
    """Inject all app CSS in a single cached st.markdown call."""
    st.markdown(_get_all_css(), unsafe_allow_html=True)


@lru_cache(maxsize=1)
def _load_manifest() -> dict:
    """Load the data manifest with source freshness info."""
    manifest_path = Path(__file__).parent / "data" / "manifest.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text())
    return {}


def _show_data_freshness():
    """Show a compact data freshness caption below the map."""
    manifest = _load_manifest()
    acs = manifest.get("acs_5year", {})
    if not acs:
        return
    year = acs.get("year", "?")
    fetched = acs.get("fetched_at", "unknown")
    sources = [f"ACS {year} 5-Year"]
    alice = manifest.get("alice", {})
    if alice:
        sources.append(f"ALICE {alice.get('year', '?')}")
    st.caption(f"Data: {' | '.join(sources)} | Last refreshed: {fetched}")


def _init_from_query_params():
    """Initialize session state from URL query parameters for bookmarkable views."""
    params = st.query_params

    valid_layers = ['State Boundary', 'Counties', 'House Districts', 'Senate Districts']
    if "layer" in params and params["layer"] in valid_layers:
        st.session_state.active_layer = params["layer"]

    if "var" in params:
        st.session_state.selected_variable = params["var"]

    if "color" in params and params["color"] in ('blue', 'green', 'red', 'purple'):
        st.session_state.color_scheme = params["color"]


def _sync_query_params():
    """Write current session state to URL query params for sharing."""
    st.query_params["layer"] = st.session_state.get("active_layer", "Counties")
    st.query_params["var"] = st.session_state.get("selected_variable", "alice_rate")
    st.query_params["color"] = st.session_state.get("color_scheme", "blue")


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
    
    try:
        # Initialize session state defaults, then apply URL params
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = 'Counties'
            logger.info("Initializing session state with Counties layer")
        _init_from_query_params()
        
        # Create custom sidebar with green labels (title removed per design request)
        # st.sidebar.title("🌴 Hawaii Appleseed Dashboard")
        
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
        if selected_color != st.session_state.get('color_scheme'):
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
        st.markdown('<h1 class="dashboard-title">Data Dashboard</h1>', unsafe_allow_html=True)

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
            st.header("Data Analysis")
            create_data_summary()

        # Data freshness caption and URL sync
        _show_data_freshness()
        _sync_query_params()

    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        logger.error(error_msg, exc_info=True)
        st.error(error_msg)

if __name__ == "__main__":
    main()
