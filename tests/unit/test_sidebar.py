"""
Unit tests for the sidebar component.
"""
import pytest
from unittest.mock import patch, MagicMock

# Import the modules to test
from ui.sidebar import create_sidebar

# Create a SessionState class to mock Streamlit's session state
class SessionState(dict):
    def __getattr__(self, key):
        if key in self:
            return self[key]
        return None
    
    def __setattr__(self, key, value):
        self[key] = value

class TestSidebar:
    """Test suite for sidebar functionality."""
    
    @patch('ui.sidebar.st')
    def test_create_sidebar(self, mock_st):
        """Test creating the sidebar."""
        # Use the SessionState class
        mock_st.session_state = SessionState()
        
        # Call the function
        result = create_sidebar()
        
        # Verify that the sidebar was created
        mock_st.sidebar.title.assert_called_once_with("🌴 Hawaii Appleseed Dashboard")
        
        # Verify that the correct components were added
        mock_st.sidebar.markdown.assert_called()
        
        # Verify that the function returns a dictionary with the expected keys
        assert isinstance(result, dict), "create_sidebar should return a dictionary"
        expected_keys = ['active_layer', 'selected_variable', 'color_scheme', 'show_legend', 'show_labels', 'debug_info']
        for key in expected_keys:
            assert key in result, f"Result should contain '{key}' key"
    
    @patch('ui.sidebar.st')
    def test_layer_selection(self, mock_st):
        """Test layer selection in the sidebar."""
        # Use the SessionState class
        mock_st.session_state = SessionState(active_layer='State Boundary')
        
        # Mock selectbox to return a different layer
        mock_st.sidebar.selectbox.side_effect = ['Counties', 'poverty_rate', 'blue']
        
        # Call the function
        result = create_sidebar()
        
        # Verify that session state was updated
        assert mock_st.session_state['active_layer'] == 'Counties'
        assert result['active_layer'] == 'Counties'
    
    @patch('ui.sidebar.st')
    def test_variable_selection(self, mock_st):
        """Test variable selection in the sidebar."""
        # Use the SessionState class
        mock_st.session_state = SessionState(
            active_layer='State Boundary',
            selected_variable='poverty_rate',
            color_scheme='blue'
        )
        
        # Mock selectbox to return values
        mock_st.sidebar.selectbox.side_effect = ['State Boundary', 'median_income', 'blue']
        
        # Call the function
        result = create_sidebar()
        
        # Verify that session state was updated
        assert mock_st.session_state['selected_variable'] == 'median_income'
        assert result['selected_variable'] == 'median_income'
    
    @patch('ui.sidebar.st')
    def test_color_scheme_selection(self, mock_st):
        """Test color scheme selection in the sidebar."""
        # Use the SessionState class
        mock_st.session_state = SessionState(
            active_layer='State Boundary',
            selected_variable='poverty_rate',
            color_scheme='blue'
        )
        
        # Mock selectbox to return values
        mock_st.sidebar.selectbox.side_effect = ['State Boundary', 'poverty_rate', 'green']
        
        # Call the function
        result = create_sidebar()
        
        # Verify that session state was updated
        assert mock_st.session_state['color_scheme'] == 'green'
        assert result['color_scheme'] == 'green'
        
    @patch('ui.sidebar.st')
    def test_sidebar_about_section(self, mock_st):
        """Test the about section in the sidebar."""
        # Use the SessionState class
        mock_st.session_state = SessionState(
            active_layer='State Boundary',
            selected_variable='poverty_rate',
            color_scheme='blue'
        )
        
        # Call the function
        create_sidebar()
        
        # Verify that the about section was created using info
        # The actual implementation uses st.sidebar.info() not an expander
        about_content_shown = False
        for call in mock_st.sidebar.info.call_args_list:
            if 'About' in str(call):
                about_content_shown = True
                break
        
        assert about_content_shown, "About content should be shown in the sidebar using info()"
