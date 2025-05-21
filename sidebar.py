import streamlit as st

def render_sidebar():
    """Render the application sidebar with navigation links"""
    
    # Main navigation - exactly 6 items as requested
    st.sidebar.page_link("app.py", label="Dashboard")
    st.sidebar.page_link("pages/1_multiple_accounts.py", label="Multiple Accounts")
    st.sidebar.page_link("pages/2_limit_monitoring.py", label="Limit Monitoring")
    st.sidebar.page_link("pages/3_fraud_detection.py", label="Fraud Detection")
    st.sidebar.page_link("pages/4_financial_alerts.py", label="Financial Alerts")
    
    # User profile - the 6th item
    if st.session_state.get("user_info"):
        st.sidebar.page_link("pages/user_profile.py", label="User Profile")
        
        # Logout button
        if st.sidebar.button("Logout", key="main_sidebar_logout", use_container_width=True):
            st.session_state.user_info = None
            st.rerun()