import streamlit as st
from auth import get_current_user

def render_left_navigation():
    """Render a vertical navigation bar on the left side of the application"""
    # Get current user info
    user_info = get_current_user() or {}
    
    # Empty function since we're using default Streamlit navigation
    pass

# For backward compatibility
render_top_navigation = render_left_navigation