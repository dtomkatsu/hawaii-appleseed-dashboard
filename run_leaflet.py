"""Hawaii Appleseed Dashboard - Leaflet Version."""
import sys
import logging
from pathlib import Path
import streamlit as st

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent / "src"))

# Import local modules
from utils.logging_utils import setup_logging, log_error
from ui.sidebar import create_sidebar
from ui.leaflet_map_view import create_leaflet_map_view, create_data_summary

# Set page config
st.set_page_config(
    page_title="Hawaii Appleseed Dashboard",
    page_icon="🌴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add diagnostic script to identify text cutoff issues
st.components.v1.html("""
<script>
// Debug script to identify text cutoff issues
document.addEventListener('DOMContentLoaded', function() {
    // Function to log element dimensions and styles
    const logElementInfo = (element) => {
        if (!element) return;
        
        const styles = window.getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        
        console.log('Element info:', {
            tag: element.tagName,
            class: element.className,
            dimensions: {
                width: rect.width,
                height: rect.height,
                contentHeight: element.scrollHeight,
                padding: styles.padding,
                margin: styles.margin,
                border: styles.border
            },
            textStyles: {
                lineHeight: styles.lineHeight,
                fontSize: styles.fontSize,
                fontFamily: styles.fontFamily,
                overflow: styles.overflow,
                textOverflow: styles.textOverflow,
                whiteSpace: styles.whiteSpace,
                display: styles.display,
                alignItems: styles.alignItems,
                justifyContent: styles.justifyContent
            },
            parent: element.parentElement ? {
                tag: element.parentElement.tagName,
                class: element.parentElement.className,
                height: element.parentElement.offsetHeight,
                overflow: window.getComputedStyle(element.parentElement).overflow
            } : null
        });
    };

    // Log when dropdown opens
    document.body.addEventListener('click', function(e) {
        if (e.target.closest('[data-baseweb="select"]')) {
            setTimeout(() => {
                const menu = document.querySelector('[data-baseweb="menu"]');
                if (menu) {
                    console.log('Dropdown menu found, checking dimensions...');
                    logElementInfo(menu);
                    
                    // Log first menu item
                    const firstItem = menu.querySelector('[role="option"]');
                    if (firstItem) {
                        console.log('First menu item:');
                        logElementInfo(firstItem);
                        
                        // Log text node
                        const textNode = firstItem.querySelector('div');
                        if (textNode) {
                            console.log('Text node:');
                            logElementInfo(textNode);
                        }
                    }
                }
            }, 300);
        }
    });

    // Add visual debugging
    const style = document.createElement('style');
    style.textContent = `
        /* Visual debugging */
        [data-baseweb="menu"] {
            outline: 2px dashed red !important;
            overflow: visible !important;
        }
        [data-baseweb="menu"] [role="option"] {
            outline: 1px solid blue !important;
            background-color: rgba(0,0,255,0.1) !important;
        }
        [data-baseweb="menu"] [role="option"] > div {
            outline: 1px solid green !important;
            background-color: rgba(0,255,0,0.1) !important;
        }
    `;
    document.head.appendChild(style);
});
</script>
""", height=0)

def main():
    """Main application function for the Leaflet version."""
    # Set up logging with debug level
    logger = setup_logging(level=logging.DEBUG)
    logger.info("Starting Hawaii Appleseed Dashboard - Leaflet Version with DEBUG logging")
    
    # Enhanced dropdown styling with borders and hover effects
    st.markdown("""
    <style>
        /* Remove borders from Streamlit's generated classes */
        .st-au,
        .st-ax,
        .st-av,
        .st-aw,
        .st-bb,
        .st-bd,
        .st-b8,
        .st-b3,
        .st-b4,
        .st-be,
        .st-bf,
        .st-bg,
        .st-bh,
        .st-bi,
        .st-bj,
        .st-bk,
        .st-bl,
        .st-bm,
        .st-bn,
        .st-b1,
        .st-bo,
        .st-bp,
        .st-e7,
        .st-e8,
        .st-e9,
        .st-ea,
        .st-eb,
        .st-bv,
        .st-bc,
        .st-bw,
        .st-bx,
        .st-by,
        .st-bz,
        .st-c0,
        .st-c1,
        .st-c2,
        .st-c3,
        .st-c4,
        .st-c6,
        .st-b6,
        .st-c7,
        .st-c8,
        .st-c9,
        .st-ca,
        .st-cb {
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }
        
        /* Target the dropdown menu container */
        .st-bc.st-bd.st-bx.st-by.st-bz.st-b3.st-c0.st-c1.st-be.st-c2.st-c3.st-c4.st-c5 {
            position: relative;
            z-index: 1000;
        }
        
        /* Target menu items and text content */
        .st-bc.st-bd.st-bx.st-by.st-bz.st-b3.st-c0.st-c1.st-be.st-c2.st-c3.st-c4.st-c5 > div,
        .st-c5.st-bb.st-b6.st-c6.st-c7.st-bd.st-c8.st-c9.st-ca {
            transition: all 0.2s ease !important;
            opacity: 0;
            transform: translateY(-5px);
            animation: itemFadeIn 0.2s forwards;
            transform-origin: left center !important;
            cursor: pointer;
            padding: 12px 16px !important;
            line-height: 1.5 !important;
            min-height: 44px !important;
            display: flex !important;
            align-items: center !important;
            overflow: visible !important;
            white-space: normal !important;
            text-overflow: clip !important;
            height: auto !important;
        }
        
        /* Ensure text container doesn't clip content */
        .st-c5.st-bb.st-b6.st-c6.st-c7.st-bd.st-c8.st-c9.st-ca {
            padding: 8px 16px !important;
            display: inline-flex !important;
            align-items: center !important;
            height: 100% !important;
        }
        
        /* Hover effect for menu items */
        .st-bc.st-bd.st-bx.st-by.st-bz.st-b3.st-c0.st-c1.st-be.st-c2.st-c3.st-c4.st-c5 > div:hover {
            background-color: var(--hover-color, #f5f8ff) !important;
            transform: translateY(0) translateX(8px) !important;
            padding-left: 24px !important;
        }
        /* Base dropdown styles */
        .stSelectbox {
            color: var(--text-color) !important;
            margin-bottom: 1rem;
        }
        
        /* Dropdown container */
        [data-baseweb="select"] {
            min-height: 38px;
            border: 1px solid var(--border-color, #ccc);
            border-radius: 4px;
            transition: all 0.2s ease;
            background-color: var(--background-color, #fff);
        }
        
        /* Hover state */
        [data-baseweb="select"]:hover {
            border-color: var(--primary-color, #4c9ffe);
            box-shadow: 0 0 0 1px var(--primary-color, #4c9ffe);
        }
        
        /* Focus state */
        [data-baseweb="select"]:focus-within {
            border-color: var(--primary-color, #4c9ffe);
            box-shadow: 0 0 0 2px rgba(76, 159, 254, 0.2);
        }
        
        /* Dropdown text */
        [data-baseweb="select"] > div > div {
            color: var(--text-color) !important;
            line-height: 1.5;
            padding: 8px 12px;
        }
        
        /* Dropdown menu - remove all borders */
        [data-baseweb="popover"],
        [data-baseweb="popover"] *,
        [data-baseweb="popover"]::before,
        [data-baseweb="popover"]::after,
        [data-baseweb="popover"] > div,
        [data-baseweb="popover"] > div > *,
        [data-baseweb="popover"] [role="listbox"],
        [data-baseweb="popover"] [role="listbox"] * {
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
            --border-width: 0 !important;
            border-width: 0 !important;
            border-style: none !important;
            border-image: none !important;
        }
        
        /* Add back box-shadow to popover only */
        [data-baseweb="popover"] {
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15) !important;
        }
        
        /* Menu items */
        [data-baseweb="menu"] {
            padding: 4px 0;
            opacity: 0;
            transform: translateY(-10px);
            animation: menuFadeIn 0.2s forwards;
        }
        
        @keyframes menuFadeIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        [data-baseweb="menu"] [role="option"] {
            padding: 8px 16px;
            transition: all 0.2s ease;
            opacity: 0;
            transform: translateY(-5px);
            animation: itemFadeIn 0.2s forwards;
            transform-origin: left center;
        }
        
        /* Stagger the animation for each menu item */
        [data-baseweb="menu"] [role="option"]:nth-child(1) { animation-delay: 0.05s; }
        [data-baseweb="menu"] [role="option"]:nth-child(2) { animation-delay: 0.1s; }
        [data-baseweb="menu"] [role="option"]:nth-child(3) { animation-delay: 0.15s; }
        [data-baseweb="menu"] [role="option"]:nth-child(4) { animation-delay: 0.2s; }
        [data-baseweb="menu"] [role="option"]:nth-child(5) { animation-delay: 0.25s; }
        
        @keyframes itemFadeIn {
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        [data-baseweb="menu"] [role="option"]:hover {
            background-color: var(--hover-color, #f5f8ff);
            transform: translateY(0) translateX(8px);
            padding-left: 20px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Add diagnostic script to inspect dropdown styles
    st.markdown("""
    <script>
    // Run after the page loads
    window.addEventListener('load', function() {
        // Create a style element for our diagnostic border
        const style = document.createElement('style');
        style.textContent = `
            /* Highlight all potential border elements */
            [data-baseweb="popover"],
            [data-baseweb="popover"] * {
                outline: 2px solid red !important;
                outline-offset: -1px;
            }
        `;
        document.head.appendChild(style);
        
        // Log the computed styles of the dropdown
        const logStyles = () => {
            const dropdown = document.querySelector('[data-baseweb="popover"]');
            if (dropdown) {
                const styles = window.getComputedStyle(dropdown);
                console.log('Dropdown styles:', {
                    border: styles.border,
                    outline: styles.outline,
                    boxShadow: styles.boxShadow,
                    borderImage: styles.borderImage,
                    borderWidth: styles.borderWidth,
                    borderStyle: styles.borderStyle,
                    borderColor: styles.borderColor
                });
            }
        };
        
        // Log styles when dropdown opens
        document.body.addEventListener('click', function(e) {
            if (e.target.closest('[data-baseweb="select"]')) {
                setTimeout(logStyles, 300);
            }
        });
    });
    </script>
    """, unsafe_allow_html=True)
    
    # Load additional custom CSS if needed
    with open(Path(__file__).parent / "src" / "ui" / "custom.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    
    try:
        # Initialize session state for county layer if not already set
        if 'active_layer' not in st.session_state:
            st.session_state.active_layer = 'Counties'
            logger.info("Initializing session state with Counties layer")
        
        # Create sidebar and get user selections
        sidebar_config = create_sidebar()
        
        # Main content area
        st.title("Hawaii Geographic Data Explorer (Leaflet)")
        st.markdown("---")
        
        # Create two columns for the main content
        col1, col2 = st.columns([2, 1])
        
        # Left column - Leaflet Map View
        with col1:
            create_leaflet_map_view(
                debug_info=sidebar_config.get('debug_info', False)
            )
        
        # Right column - Data Summary
        with col2:
            create_data_summary()
        
    except Exception as e:
        error_msg = f"An unexpected error occurred: {str(e)}"
        logger.error(error_msg, exc_info=True)
        st.error(error_msg)

if __name__ == "__main__":
    main()
