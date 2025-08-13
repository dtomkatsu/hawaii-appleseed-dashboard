"""
Utility functions for ensuring full-width layout in Streamlit apps.
This is specifically designed to work around container width issues in Cloud Run/Docker environments.
"""
import streamlit as st

def set_full_width_layout():
    """
    Applies CSS to ensure full-width layout in all environments.
    This should be called at the beginning of your Streamlit app.
    """
    st.markdown("""
    <style>
        /* Base container adjustments */
        .stApp {
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* Main content area */
        .main .block-container {
            max-width: 100% !important;
            padding: 2rem 1rem 2rem 1rem !important;
            margin: 0 !important;
        }
        
        /* Override any max-width constraints */
        .stApp > div,
        .stApp > div > div,
        .stApp > div > div > div,
        .stApp > div > div > div > div,
        .stApp > div > div > div > div > div {
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* Ensure all direct children of main container are full width */
        .main .block-container > * {
            max-width: 100% !important;
            width: 100% !important;
        }
        
        /* Fix for Streamlit's default max-width */
        .stApp > div > div > div > div > div > div {
            max-width: 100% !important;
        }
        
        /* Viewport settings */
        @media (min-width: 576px) {
            .main .block-container {
                padding: 2rem 1.5rem 2rem 1.5rem !important;
            }
        }
        
        @media (min-width: 768px) {
            .main .block-container {
                padding: 2rem 2rem 2rem 2rem !important;
            }
        }
        
        @media (min-width: 1200px) {
            .main .block-container {
                padding: 2rem 5rem 2rem 5rem !important;
            }
        }
        
        /* Force full width on all containers */
        .stContainer > div,
        .stContainer > div > div,
        .element-container,
        .stMarkdown,
        .stDataFrame,
        .stPlotlyChart,
        .stImage,
        .stMap {
            width: 100% !important;
            max-width: 100% !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* Remove any horizontal scroll */
        html, body, #root, #root > div {
            width: 100% !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Add viewport configuration via JavaScript for better compatibility
    st.markdown("""
    <script>
        // Ensure viewport is set correctly for containerized environments
        if (!document.querySelector('meta[name="viewport"]')) {
            var viewport = document.createElement('meta');
            viewport.name = 'viewport';
            viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0';
            document.head.appendChild(viewport);
        }
    </script>
    """, unsafe_allow_html=True)
