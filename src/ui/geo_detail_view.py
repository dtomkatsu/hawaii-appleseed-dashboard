"""Detailed Geography View for Hawaii Appleseed Dashboard."""
import streamlit as st
import pandas as pd
import json
import logging
from pathlib import Path
import sys

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import local modules
from src.data.data_loader import DataLoader

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
        
        # Create tabs for different categories of data
        tabs = st.tabs(["Demographics", "Economic", "Housing", "SNAP Benefits", "Tax Credits"])
        
        # Demographics tab
        with tabs[0]:
            st.subheader("Demographics")
            demo_data = geo_data.get("demographics", {})
            if demo_data:
                st.metric("Population", demo_data.get("population", "N/A"))
                st.metric("Median Age", demo_data.get("median_age", "N/A"))
                
                # Create a dataframe for demographic breakdowns
                if "population_by_race" in demo_data:
                    st.subheader("Population by Race/Ethnicity")
                    race_df = pd.DataFrame(demo_data["population_by_race"].items(), 
                                          columns=["Race/Ethnicity", "Population"])
                    race_df["Percentage"] = race_df["Population"] / race_df["Population"].sum() * 100
                    st.dataframe(race_df)
            else:
                st.info("No demographic data available for this geography.")
        
        # Economic tab
        with tabs[1]:
            st.subheader("Economic Indicators")
            econ_data = geo_data.get("economic", {})
            if econ_data:
                col1, col2 = st.columns(2)
                with col1:
                    median_income = econ_data.get('median_income')
                    st.metric("Median Income", f"${int(median_income):,}" if median_income is not None else "N/A")
                    poverty_rate = econ_data.get('poverty_rate')
                    st.metric("Poverty Rate", f"{poverty_rate}%" if poverty_rate is not None else "N/A")
                with col2:
                    unemployment_rate = econ_data.get('unemployment_rate')
                    st.metric("Unemployment Rate", f"{unemployment_rate}%" if unemployment_rate is not None else "N/A")
                    alice_rate = econ_data.get('alice_rate')
                    st.metric("ALICE Rate", f"{alice_rate}%" if alice_rate is not None else "N/A")
                
                # Income distribution chart
                if "income_distribution" in econ_data:
                    st.subheader("Income Distribution")
                    income_df = pd.DataFrame(econ_data["income_distribution"].items(),
                                           columns=["Income Bracket", "Households"])
                    st.bar_chart(income_df.set_index("Income Bracket"))
            else:
                st.info("No economic data available for this geography.")
        
        # Housing tab
        with tabs[2]:
            st.subheader("Housing")
            housing_data = geo_data.get("housing", {})
            if housing_data:
                col1, col2 = st.columns(2)
                with col1:
                    median_home_value = housing_data.get('median_home_value')
                    st.metric("Median Home Value", f"${int(median_home_value):,}" if median_home_value is not None else "N/A")
                    median_rent = housing_data.get('median_rent')
                    st.metric("Median Rent", f"${int(median_rent):,}" if median_rent is not None else "N/A")
                with col2:
                    rent_burden = housing_data.get('rent_burden_rate')
                    st.metric("Housing Cost Burden", f"{rent_burden}%" if rent_burden is not None else "N/A")
                    homeownership_rate = housing_data.get('homeownership_rate')
                    st.metric("Homeownership Rate", f"{homeownership_rate}%" if homeownership_rate is not None else "N/A")
            else:
                st.info("No housing data available for this geography.")
        
        # SNAP Benefits tab
        with tabs[3]:
            st.subheader("SNAP Benefits")
            snap_data = geo_data.get("snap", {})
            if snap_data:
                col1, col2 = st.columns(2)
                with col1:
                    snap_rate = snap_data.get('snap_household_rate')
                    st.metric("SNAP Households", f"{snap_rate}%" if snap_rate is not None else "N/A")
                    
                    benefit_per_household = snap_data.get('snap_benefit_annual_per_household')
                    st.metric("Average Annual Benefit", 
                              f"${int(benefit_per_household):,}" if benefit_per_household is not None else "N/A")
                with col2:
                    total_benefits = snap_data.get('snap_benefits_annual_total')
                    st.metric("Total Annual Benefits", 
                              f"${int(total_benefits):,}" if total_benefits is not None else "N/A")
            else:
                st.info("No SNAP data available for this geography.")
        
        # Tax Credits tab
        with tabs[4]:
            st.subheader("Tax Credits")
            tax_data = geo_data.get("tax_credits", {})
            if tax_data:
                # Display tax credit data when available
                st.write("Tax credit data will be displayed here when available.")
            else:
                st.info("Tax credit data coming soon.")
        
    except Exception as e:
        logger.error(f"Error loading data for geography {geo_id}: {str(e)}")
        st.error(f"An error occurred while loading data: {str(e)}")

if __name__ == "__main__":
    display_geo_detail_view()
