import streamlit as st

def render_sidebar():
    """Render the application sidebar with navigation links"""
    
    # Main navigation links
    st.sidebar.page_link("app.py", label="Dashboard")
    
    # Module navigation
    st.sidebar.header("Analysis Modules")
    st.sidebar.page_link("pages/1_multiple_accounts.py", label="Multiple Accounts")
    st.sidebar.page_link("pages/2_limit_monitoring.py", label="Limit Monitoring")
    st.sidebar.page_link("pages/3_fraud_detection.py", label="Fraud Detection")
    
    # User section
    if st.session_state.get("user_info"):
        st.sidebar.divider()
        st.sidebar.header("User Area")
        st.sidebar.page_link("pages/user_profile.py", label="Profile Settings")
    
    # App information
    st.sidebar.divider()
    st.sidebar.caption("""
    **Financial Intelligence Platform**  
    Version 1.0  
    © 2025
    """)