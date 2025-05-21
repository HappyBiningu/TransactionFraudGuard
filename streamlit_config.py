"""
Shared configuration settings for the Streamlit application.
"""

import streamlit as st

def hide_streamlit_sidebar():
    """Hide the default Streamlit sidebar completely"""
    st.markdown("""
    <style>
        [data-testid="collapsedControl"] {
            display: none
        }
        
        section[data-testid="stSidebar"] {
            display: none;
        }
        
        /* Add more vertical space for the main content */
        .main .block-container {
            padding-top: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)