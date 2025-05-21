import streamlit as st

def render_sidebar():
    """Render the application sidebar with navigation links"""
    
    st.sidebar.markdown("## 📊 Navigation")
    
    st.sidebar.markdown("### 🧭 Main Modules")
    
    # Main navigation links
    st.sidebar.page_link("app.py", label="📊 Dashboard", icon="🏠")
    st.sidebar.page_link("pages/1_multiple_accounts.py", label="🔍 Multiple Accounts", icon="🔗")
    st.sidebar.page_link("pages/2_limit_monitoring.py", label="🚦 Limit Monitoring", icon="🔗")
    st.sidebar.page_link("pages/3_fraud_detection.py", label="🛡️ Fraud Detection", icon="🔗")
    
    # User section
    if st.session_state.get("user_info"):
        st.sidebar.divider()
        st.sidebar.markdown("### 👤 User Area")
        st.sidebar.page_link("pages/user_profile.py", label="👤 Profile Settings", icon="⚙️")
    
    # App information
    st.sidebar.divider()
    st.sidebar.markdown("### ℹ️ App Info")
    st.sidebar.info("""
    **Financial Intelligence Platform**  
    Version 1.0  
    © 2025
    """)