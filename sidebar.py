import streamlit as st

def render_sidebar():
    """Render the application sidebar with navigation links"""
    
    # We're going to avoid rendering the sidebar links in this function
    # since another component is already handling this
    
    # Just keep track of the user info state
    if not st.session_state.get("user_info"):
        return