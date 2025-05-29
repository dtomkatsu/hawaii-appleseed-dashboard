"""
Hawaii Appleseed Dashboard - Main Entry Point

This file serves as the main entry point for the Streamlit application.
Run this file using: streamlit run run.py
"""
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent))

# Import the main application
from src.app import main

# Streamlit will automatically call the main() function when this script is run with 'streamlit run'
main()
