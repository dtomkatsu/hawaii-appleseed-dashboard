"""
Variable Data View for displaying detailed information about selected features.
"""
import streamlit as st
import pandas as pd
import json
from typing import Dict, Any, Optional

# Set up logging
import logging
logger = logging.getLogger(__name__)

def create_variable_data_view() -> None:
    """
    Create and display the variable data view.
    Shows detailed information about the currently selected feature.
    """
    st.header("Variable Data Explorer")
    
    # Debug: Log the current session state keys
    logger.debug(f"Session state keys: {list(st.session_state.keys())}")
    
    # Check if we have a selected feature in session state
    if 'selected_feature' not in st.session_state or st.session_state.selected_feature is None:
        logger.warning("No selected_feature found in session state")
        st.info("👈 Select a feature on the map to view its variable data")
        return
    
    # Debug: Log the selected feature
    logger.debug(f"Selected feature: {st.session_state.selected_feature}")
    
    try:
        feature = st.session_state.selected_feature
        props = feature.get('properties', {})
        
        # Display feature header
        col1, col2 = st.columns([1, 3])
        with col1:
            st.subheader("Feature Details")
        with col2:
            if st.button("⬅️ Back to Map", key="back_to_map_btn"):
                # Clear selection and switch to map tab (tab index 0)
                st.session_state.active_tab = 0
                st.rerun()
        
        # Display basic feature info
        st.markdown(f"**Layer:** {feature.get('layer', 'N/A')}")
        st.markdown(f"**ID:** {props.get('id', 'N/A')}")
        
        # Display all properties in a table
        if props:
            st.subheader("All Variables")
            
            # Filter out geometry and other non-data properties
            exclude_keys = {'geometry', 'id', 'layer', 'geojson'}
            data_props = {k: v for k, v in props.items() if k not in exclude_keys}
            
            if data_props:
                # Convert to DataFrame for better display
                df = pd.DataFrame({
                    'Variable': data_props.keys(),
                    'Value': data_props.values()
                })
                
                # Add filtering
                search_term = st.text_input("Search variables:", "")
                if search_term:
                    df = df[df['Variable'].str.contains(search_term, case=False, na=False) | 
                           df['Value'].astype(str).str.contains(search_term, case=False, na=False)]
                
                # Display the table
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Variable": "Variable",
                        "Value": st.column_config.TextColumn("Value")
                    }
                )
                
                # Add download button
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 Download as CSV",
                    data=csv,
                    file_name=f"{props.get('id', 'feature')}_variables.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No variable data available for this feature.")
        else:
            st.warning("No properties available for this feature.")
            
    except Exception as e:
        logger.error(f"Error in variable data view: {str(e)}", exc_info=True)
        st.error("An error occurred while displaying variable data. Please try again.")

# For testing the view directly
if __name__ == "__main__":
    # Add test data to session state for testing
    if 'selected_feature' not in st.session_state:
        st.session_state.selected_feature = {
            'id': 'test_feature_1',
            'layer': 'Test Layer',
            'properties': {
                'id': 'test_feature_1',
                'name': 'Test Feature',
                'population': 1000,
                'area': 50.5,
                'description': 'This is a test feature for development.'
            }
        }
    
    create_variable_data_view()
