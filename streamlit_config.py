"""
Shared configuration settings for the Streamlit application.
"""

import streamlit as st

def enable_left_sidebar():
    """
    Configure the Streamlit interface to use our custom left sidebar navigation
    by ensuring the sidebar is visible but customized
    """
    # Add padding for the main content and style the sidebar
    st.markdown("""
    <style>
        /* Style the sidebar */
        section[data-testid="stSidebar"] {
            width: 250px !important;
            background-color: #f8f9fa;
            border-right: 1px solid #dee2e6;
        }
        
        /* Style sidebar content */
        section[data-testid="stSidebar"] > div {
            padding-top: 1rem;
            background-color: #f8f9fa;
        }
        
        /* Set main content margins */
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 2rem;
            max-width: 100%;
        }
        
        /* Remove overflow hidden to prevent content cutoff */
        .main, .element-container {
            overflow: visible !important;
        }
    </style>
    """, unsafe_allow_html=True)

# For backward compatibility with existing code
remove_streamlit_sidebar = enable_left_sidebar