"""
Shared configuration settings for the Streamlit application.
"""

import streamlit as st

def use_default_navigation():
    """
    Use the default Streamlit navigation system
    """
    # Set some basic styling for the main content
    st.markdown("""
    <style>
        /* Set main content margins */
        .main .block-container {
            padding-left: 2rem;
            padding-right: 2rem;
            padding-top: 2rem;
            max-width: 100%;
        }
    </style>
    """, unsafe_allow_html=True)

# For backward compatibility with existing code
remove_streamlit_sidebar = use_default_navigation
enable_left_sidebar = use_default_navigation