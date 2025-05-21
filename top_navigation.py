import streamlit as st
from datetime import datetime

def render_top_navigation():
    """Render a horizontal navigation bar at the top of the application"""
    
    # Only show navigation if user is logged in
    if st.session_state.get("user_info"):
        # User info display
        user_info = st.session_state.user_info
        
        # Create horizontal navigation with columns
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        
        with col1:
            st.page_link("app.py", label="📊 Dashboard", use_container_width=True)
        with col2:
            st.page_link("pages/1_multiple_accounts.py", label="🔍 Multiple Accounts", use_container_width=True)
        with col3:
            st.page_link("pages/2_limit_monitoring.py", label="🚦 Limit Monitoring", use_container_width=True)
        with col4:
            st.page_link("pages/3_fraud_detection.py", label="🛡️ Fraud Detection", use_container_width=True)
        with col5:
            st.page_link("pages/4_financial_alerts.py", label="🔔 Financial Alerts", use_container_width=True)
        with col6:
            st.page_link("pages/user_profile.py", label="👤 User Profile", use_container_width=True)
        
        # Add divider below navigation
        st.divider()
        
        # Display user info in compact form
        st.markdown(f"""
        <div style="text-align: right; font-size: 0.8em; margin-bottom: 10px;">
            👤 <b>{user_info.get('full_name', 'User')}</b> | {user_info.get('role', 'Analyst').capitalize()}
        </div>
        """, unsafe_allow_html=True)