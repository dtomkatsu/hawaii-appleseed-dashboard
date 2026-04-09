"""Detailed Geography View for Hawaii Appleseed Dashboard."""
import streamlit as st
import pandas as pd
import json
import logging
from pathlib import Path
import sys

# Import local modules
from data.data_loader import DataLoader
from config.variable_registry import get_fact_sheet_categories, get_fact_sheet_variables

# Set up logging
logger = logging.getLogger(__name__)

def display_geo_detail_view(geo_id=None):
    """
    Display detailed data for a specific geography.
    
    Args:
        geo_id: The ID of the geography to display data for.
    """
    st.title("Geography Detail View")
    
    # If no geo_id is provided, show a message
    if not geo_id:
        geo_id = st.query_params.get("geo_id")
        
    if not geo_id:
        st.warning("No geography selected. Please select a geography from the map.")
        return
    
    st.write(f"Showing detailed data for geography ID: {geo_id}")
    
    # Initialize data loader
    try:
        data_loader = DataLoader()
        
        # Get all available data for this geography
        geo_data = data_loader.get_all_data_for_geo(geo_id)
        
        if not geo_data:
            st.error(f"No data found for geography ID: {geo_id}")
            return
            
        # Display geography name and basic info
        st.header(geo_data.get("name", f"Geography {geo_id}"))
        
        # Dynamically generate tabs from centralized registry
        fact_cats = get_fact_sheet_categories()
        tab_labels = [cat["label"] for cat in fact_cats.values()]
        tabs = st.tabs(tab_labels)

        for tab, (cat_key, cat_def) in zip(tabs, fact_cats.items()):
            with tab:
                st.subheader(cat_def["label"])
                section_data = geo_data.get(cat_def["data_key"], {})
                if not section_data:
                    st.info(f"No {cat_def['label'].lower()} data available for this geography.")
                    continue

                # Render registered variables for this category
                variables = get_fact_sheet_variables(cat_key)
                if variables:
                    col1, col2 = st.columns(2)
                    for idx, var in enumerate(variables):
                        val = section_data.get(var["key"])
                        if var["data_type"] == "currency":
                            display = f"${int(val):,}" if val is not None else "N/A"
                        elif var["data_type"] == "percentage":
                            display = f"{val}%" if val is not None else "N/A"
                        else:
                            display = str(val) if val is not None else "N/A"
                        with (col1 if idx % 2 == 0 else col2):
                            st.metric(var["label"], display)

                # Special demographic widgets
                if cat_key == "demographics" and "population_by_race" in section_data:
                    st.subheader("Population by Race/Ethnicity")
                    race_df = pd.DataFrame(section_data["population_by_race"].items(),
                                          columns=["Race/Ethnicity", "Population"])
                    race_df["Percentage"] = race_df["Population"] / race_df["Population"].sum() * 100
                    st.dataframe(race_df)

                # Special economic widgets
                if cat_key == "economic" and "income_distribution" in section_data:
                    st.subheader("Income Distribution")
                    income_df = pd.DataFrame(section_data["income_distribution"].items(),
                                           columns=["Income Bracket", "Households"])
                    st.bar_chart(income_df.set_index("Income Bracket"))
        
    except Exception as e:
        logger.error(f"Error loading data for geography {geo_id}: {str(e)}")
        st.error(f"An error occurred while loading data: {str(e)}")

if __name__ == "__main__":
    display_geo_detail_view()
