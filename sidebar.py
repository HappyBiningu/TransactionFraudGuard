import streamlit as st

def render_sidebar():
    """Render the application sidebar with navigation links"""
    
    # Main navigation links
    st.sidebar.page_link("app.py", label="Dashboard")
    
    # Module navigation - keep the 6 items requested
    st.sidebar.page_link("pages/1_multiple_accounts.py", label="Multiple Accounts")
    st.sidebar.page_link("pages/2_limit_monitoring.py", label="Limit Monitoring")
    st.sidebar.page_link("pages/3_fraud_detection.py", label="Fraud Detection")
    
    # User section
    if st.session_state.get("user_info"):
        st.sidebar.page_link("pages/user_profile.py", label="Profile Settings")
        
        # Logout button
        if st.sidebar.button("Logout", key="main_sidebar_logout", use_container_width=True):
            st.session_state.user_info = None
            st.rerun()
    
    # App information
    st.sidebar.caption("Financial Intelligence Platform v1.0")