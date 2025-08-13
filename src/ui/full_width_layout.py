"""Shared CSS for full-width layout across all pages."""
import streamlit as st

def apply_full_width_layout():
    """Apply full-width layout CSS to the current Streamlit page."""
    st.markdown("""
        <style>
            /* Main container adjustments */
            .main .block-container {
                padding: 2rem 1rem !important;
                max-width: 100% !important;
                width: 100% !important;
            }
            
            /* Full width for the main content area */
            .main {
                padding: 0 !important;
                max-width: 100% !important;
            }
            
            /* Map container styles */
            .stMap, .map-container, .leaflet-container {
                width: 100% !important;
                height: 70vh !important;
                min-height: 500px;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                margin-bottom: 20px;
            }
            
            /* Adjust sidebar */
            section[data-testid="stSidebar"] {
                width: 300px !important;
                background: #f8f9fa;
                padding: 1.5rem;
                border-radius: 10px;
                margin: 1rem 0 1rem 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            /* Ensure content takes full width */
            .stApp {
                max-width: 100% !important;
                padding: 0 !important;
            }
            
            /* Fix for streamlit report view */
            .reportview-container .main .block-container {
                padding: 0 !important;
                max-width: 100% !important;
            }
            
            /* Make sure all direct children take full width */
            .stApp > div {
                max-width: 100% !important;
            }
            
            /* Chart and content containers */
            .stPlotlyChart, .stDataFrame, .element-container {
                width: 100% !important;
            }
            
            /* Responsive adjustments */
            @media (max-width: 768px) {
                .main .block-container {
                    padding: 1rem 0.5rem !important;
                }
                
                section[data-testid="stSidebar"] {
                    width: 280px !important;
                    margin: 0.5rem 0 0.5rem 0.5rem;
                }
            }
        </style>
    """, unsafe_allow_html=True)
