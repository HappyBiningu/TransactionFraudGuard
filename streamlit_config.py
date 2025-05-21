"""
Shared configuration settings for the Streamlit application.
"""

import streamlit as st

def remove_streamlit_sidebar():
    """
    Permanently remove the default Streamlit sidebar by setting an empty sidebar
    and adjusting the main content area padding
    """
    # First ensure there's nothing in the sidebar
    with st.sidebar:
        pass  # Empty sidebar
    
    # Then add padding for the main content and remove all sidebar elements
    st.markdown("""
    <style>
        /* Remove sidebar expansion arrow */
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        
        /* Remove the entire sidebar */
        section[data-testid="stSidebar"] {
            display: none !important;
            width: 0px !important;
        }
        
        /* Ensure sidebar width is zero */
        .css-1d391kg, .css-1p47miq {
            width: 0px !important;
        }
        
        /* Expand main content to full width */
        .main .block-container {
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 100%;
            padding-top: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)