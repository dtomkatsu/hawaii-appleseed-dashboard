"""Unit tests for dropdown menu CSS styling."""
import unittest
from unittest.mock import patch, MagicMock
import re
import sys
import os
from pathlib import Path
import pytest

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import the main application
from run_leaflet import main

class TestDropdownCSS(unittest.TestCase):
    """Test class for dropdown menu CSS styling."""
    
    def extract_css_from_markdown(self, markdown_calls):
        """Extract CSS content from markdown calls."""
        css_content = ""
        for call in markdown_calls:
            if len(call[0]) > 0 and isinstance(call[0][0], str) and '<style>' in call[0][0]:
                # Extract content between <style> tags
                match = re.search(r'<style>(.*?)</style>', call[0][0], re.DOTALL)
                if match:
                    css_content += match.group(1) + "\n"
        return css_content
    
    @patch('streamlit.markdown')
    def test_dropdown_width_css(self, mock_markdown):
        """Test that CSS includes width settings for dropdowns to prevent text cutoff."""
        # Run the main function which should inject CSS
        main()
        
        # Extract CSS from markdown calls
        css = self.extract_css_from_markdown(mock_markdown.call_args_list)
        
        # Check for width-related CSS for dropdowns
        self.assertTrue(
            re.search(r'[data-baseweb="select"].*?(width|min-width):', css, re.DOTALL) or
            re.search(r'\.stSelectbox.*?(width|min-width):', css, re.DOTALL),
            "Missing width-related CSS for dropdowns"
        )
        
        # Check for specific width values that would prevent text cutoff
        self.assertTrue(
            re.search(r'(width|min-width):\s*(\d+px|100%|auto)', css),
            "Missing specific width values in CSS"
        )
    
    @patch('streamlit.markdown')
    def test_dropdown_cursor_css(self, mock_markdown):
        """Test that CSS includes cursor settings to prevent blinking cursor."""
        # Run the main function which should inject CSS
        main()
        
        # Extract CSS from markdown calls
        css = self.extract_css_from_markdown(mock_markdown.call_args_list)
        
        # Check for cursor-related CSS
        cursor_properties = [
            r'cursor:\s*(pointer|default)',
            r'caret-color:\s*(transparent|rgba\(0,\s*0,\s*0,\s*0\))',
            r'user-select:\s*none'
        ]
        
        # At least one of these properties should be present
        self.assertTrue(
            any(re.search(prop, css) for prop in cursor_properties),
            "Missing cursor-related CSS to prevent blinking cursor"
        )
    
    @patch('streamlit.markdown')
    def test_dropdown_menu_css(self, mock_markdown):
        """Test that CSS includes styling for dropdown menu to ensure proper display."""
        # Run the main function which should inject CSS
        main()
        
        # Extract CSS from markdown calls
        css = self.extract_css_from_markdown(mock_markdown.call_args_list)
        
        # Check for dropdown menu styling
        menu_selectors = [
            r'\[data-baseweb="menu"\]',
            r'\[data-baseweb="popover"\]',
            r'\.stSelectbox.*?ul'
        ]
        
        # At least one of these selectors should be present
        self.assertTrue(
            any(re.search(selector, css) for selector in menu_selectors),
            "Missing CSS for dropdown menu"
        )
        
        # Check for z-index to ensure menu appears above other elements
        self.assertTrue(
            re.search(r'z-index:\s*\d+', css),
            "Missing z-index in CSS which could cause dropdown menu to be hidden"
        )
    
    @patch('streamlit.markdown')
    def test_dropdown_hover_css(self, mock_markdown):
        """Test that CSS includes hover styling for dropdown options."""
        # Run the main function which should inject CSS
        main()
        
        # Extract CSS from markdown calls
        css = self.extract_css_from_markdown(mock_markdown.call_args_list)
        
        # Check for hover styling
        hover_selectors = [
            r'\[data-baseweb="menu"\].*?:hover',
            r'\[role="option"\].*?:hover',
            r'\.stSelectbox.*?li:hover'
        ]
        
        # At least one of these hover selectors should be present
        self.assertTrue(
            any(re.search(selector, css, re.DOTALL) for selector in hover_selectors),
            "Missing hover styling for dropdown options"
        )
    
    @patch('streamlit.markdown')
    def test_dropdown_animation_css(self, mock_markdown):
        """Test that CSS includes animation settings to prevent flickering."""
        # Run the main function which should inject CSS
        main()
        
        # Extract CSS from markdown calls
        css = self.extract_css_from_markdown(mock_markdown.call_args_list)
        
        # Check for animation-related CSS
        animation_properties = [
            r'transition:\s*[^;]+',
            r'animation:\s*none',
            r'-webkit-animation:\s*none'
        ]
        
        # These properties might be present to prevent flickering
        animation_present = any(re.search(prop, css) for prop in animation_properties)
        
        # This is not a strict requirement but log it for information
        if not animation_present:
            print("Note: No animation-related CSS found. This is not necessarily an issue but could be added to improve smoothness.")

if __name__ == "__main__":
    unittest.main()
