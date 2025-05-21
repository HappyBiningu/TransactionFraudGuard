import streamlit as st
from datetime import datetime

def render_left_navigation():
    """Render a vertical navigation bar on the left side of the application"""
    
    # Only show navigation if user is logged in
    if st.session_state.get("user_info"):
        # User info display
        user_info = st.session_state.user_info
        
        # Custom CSS for left navigation
        st.markdown("""
        <style>
            /* Main content positioning */
            .block-container {
                padding-left: 1rem !important;
                padding-right: 1rem !important;
            }
            
            /* Nav link styling */
            div[data-testid="stVerticalBlock"] div.element-container div.stButton > button {
                width: 100%;
                text-align: left;
                padding: 0.5rem 1rem;
                background-color: #1E3A8A;
                color: white;
                border: none;
                border-radius: 5px;
                margin-bottom: 0.5rem;
                display: flex;
                align-items: center;
                justify-content: flex-start;
                font-weight: 500;
                height: auto;
            }
            
            div[data-testid="stVerticalBlock"] div.element-container div.stButton > button:hover {
                background-color: #2D4A9A;
                color: white;
                border: none;
            }
            
            /* Add space for icons */
            div[data-testid="stVerticalBlock"] div.element-container div.stButton > button p {
                display: flex;
                align-items: center;
                margin: 0;
            }
            
            /* User info styling */
            .user-info {
                margin-top: 1.5rem;
                padding-top: 1rem;
                border-top: 1px solid #ccc;
                font-size: 0.8rem;
            }
        </style>
        """, unsafe_allow_html=True)
        
        
            
            # Display user info in sidebar
            st.markdown(f"""
            <div class="user-info">
                <p>Logged in as:<br/>
                <b>{user_info.get('full_name', 'User')}</b><br/>
                <small>Role: {user_info.get('role', 'Analyst').capitalize()}</small></p>
            </div>
            """, unsafe_allow_html=True)

# For backward compatibility
render_top_navigation = render_left_navigation