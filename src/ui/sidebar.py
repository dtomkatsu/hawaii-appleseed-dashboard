"""Sidebar components for the Hawaii Appleseed Dashboard."""
import streamlit as st
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def create_sidebar() -> Dict[str, Any]:
    """
    Create the sidebar with layer selection and other controls.
    
    Returns:
        Dict containing the user selections
    """
    st.sidebar.title("Hawaii Appleseed Dashboard")
    
    # Layer selection
    st.sidebar.subheader("Map Layers")
    active_layer = st.sidebar.radio(
        "Select Layer",
        options=['State', 'Counties', 'State House Districts', 'State Senate Districts'],
        index=0
    )
    
    # Map settings
    st.sidebar.subheader("Map Settings")
    show_legend = st.sidebar.checkbox("Show Legend", value=True)
    
    # Debug options
    if st.sidebar.checkbox("Show Debug Info", value=False):
        debug_info = True
        st.sidebar.warning("Debug mode is enabled")
    else:
        debug_info = False
    
    # About section
    st.sidebar.markdown("---")
    st.sidebar.info(
        "Hawaii Appleseed Dashboard\n\n"
        "Explore geographic data for Hawaii."
    )
    
    return {
        'active_layer': active_layer,
        'show_legend': show_legend,
        'debug_info': debug_info
    }
