import streamlit as st

def render_sidebar():
    """Render the application sidebar with navigation links"""
    
    # Application title
    st.sidebar.title("Financial Intelligence")
    
    # Main navigation links
    st.sidebar.page_link("app.py", label="📊 Dashboard", icon="🏠")
    
    # Module navigation
    st.sidebar.header("📈 Analysis Modules")
    st.sidebar.page_link("pages/1_multiple_accounts.py", label="🔍 Multiple Accounts", icon="🔎")
    st.sidebar.page_link("pages/2_limit_monitoring.py", label="🚦 Limit Monitoring", icon="⚠️")
    st.sidebar.page_link("pages/3_fraud_detection.py", label="🛡️ Fraud Detection", icon="🔒")
    
    # User section
    if st.session_state.get("user_info"):
        st.sidebar.divider()
        st.sidebar.header("👤 User Area")
        st.sidebar.page_link("pages/user_profile.py", label="Profile Settings", icon="⚙️")
    
    # App information
    st.sidebar.divider()
    st.sidebar.caption("""
    **Financial Intelligence Platform**  
    Version 1.0  
    © 2025
    """)