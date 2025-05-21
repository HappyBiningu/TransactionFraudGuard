import streamlit as st

def render_sidebar():
    """Render the application sidebar with navigation links"""
    
    # Only show navigation if user is logged in
    if st.session_state.get("user_info"):
        # Clear any default sidebar content
        with st.sidebar:
            # Add the main navigation links with proper capitalization - exactly 6 items
            st.page_link("app.py", label="Dashboard", use_container_width=True)
            st.page_link("pages/1_multiple_accounts.py", label="Multiple Accounts", use_container_width=True)
            st.page_link("pages/2_limit_monitoring.py", label="Limit Monitoring", use_container_width=True)
            st.page_link("pages/3_fraud_detection.py", label="Fraud Detection", use_container_width=True)
            st.page_link("pages/4_financial_alerts.py", label="Financial Alerts", use_container_width=True)
            st.page_link("pages/user_profile.py", label="User Profile", use_container_width=True)
    
    # Otherwise don't render anything - login screen handles itself