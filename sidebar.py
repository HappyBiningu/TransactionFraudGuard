import streamlit as st
from datetime import datetime

def render_sidebar():
    """Render the application sidebar with navigation links"""
    
    # Only show navigation if user is logged in
    if st.session_state.get("user_info"):
        with st.sidebar:
            # Add user info at the top of sidebar
            user_info = st.session_state.user_info
            st.write(f"👤 **Welcome, {user_info.get('full_name', 'User')}!**")
            st.write(f"Role: {user_info.get('role', 'Analyst').capitalize()}")
            st.divider()
            
            # Add the main navigation links with proper capitalization - exactly 6 items
            st.page_link("app.py", label="📊 Dashboard", use_container_width=True)
            st.page_link("pages/1_multiple_accounts.py", label="🔍 Multiple Accounts", use_container_width=True)
            st.page_link("pages/2_limit_monitoring.py", label="🚦 Limit Monitoring", use_container_width=True)
            st.page_link("pages/3_fraud_detection.py", label="🛡️ Fraud Detection", use_container_width=True)
            st.page_link("pages/4_financial_alerts.py", label="🔔 Financial Alerts", use_container_width=True)
            st.page_link("pages/user_profile.py", label="👤 User Profile", use_container_width=True)
            
            # Add footer info
            st.divider()
            st.caption("Unified Financial Intelligence Platform")
            st.caption(f"© {datetime.now().year} - All rights reserved")
    
    # Otherwise don't render anything - login screen handles itself