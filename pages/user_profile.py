import streamlit as st
import sys
import os
import sqlite3
import hashlib
from datetime import datetime

# Add the root directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auth import require_auth, get_current_user
from sidebar import render_sidebar
from theme_utils import apply_custom_theme

# Constants
DB_FILE = "fraud_detection.db"

# Set page config
st.set_page_config(page_title="User Profile", page_icon="👤", layout="wide", menu_items=None)

# Render sidebar navigation
render_sidebar()

# Apply custom theme
apply_custom_theme()

@require_auth
def main():
    user_info = get_current_user()
    
    st.title("👤 User Profile")
    
    # Layout with columns
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Account Information")
        st.info(f"""
        **Username:** {user_info['username']}  
        **Full Name:** {user_info['full_name']}  
        **Role:** {user_info['role'].capitalize()}
        """)
        
        st.divider()
        
        # User activity
        st.subheader("Recent Activity")
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Get last login time
            cursor.execute(
                "SELECT last_login FROM users WHERE username = ?", 
                (user_info['username'],)
            )
            last_login = cursor.fetchone()
            
            if last_login:
                st.write(f"**Last Login:** {last_login[0]}")
            
            # Could add more activity metrics here
            
            conn.close()
        except Exception as e:
            st.error(f"Error loading user activity: {str(e)}")
    
    with col2:
        st.subheader("Update Profile")
        
        # Password change form
        with st.form("password_change_form"):
            st.write("**Change Password**")
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            submit = st.form_submit_button("Update Password")
            
            if submit:
                if not current_password or not new_password or not confirm_password:
                    st.error("All fields are required")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    success = change_password(user_info['username'], current_password, new_password)
                    if success:
                        st.success("Password updated successfully!")
                    else:
                        st.error("Current password is incorrect")
        
        # Profile information update
        with st.form("profile_update_form"):
            st.write("**Update Personal Information**")
            
            # Get current info
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT full_name FROM users WHERE username = ?", 
                    (user_info['username'],)
                )
                current_info = cursor.fetchone()
                conn.close()
                
                current_full_name = current_info[0] if current_info else user_info['full_name']
            except:
                current_full_name = user_info['full_name']
            
            new_full_name = st.text_input("Full Name", value=current_full_name)
            
            submit = st.form_submit_button("Update Profile")
            
            if submit:
                if not new_full_name:
                    st.error("Name cannot be empty")
                elif new_full_name != current_full_name:
                    success = update_profile(user_info['username'], new_full_name)
                    if success:
                        st.success("Profile updated successfully! Please refresh to see changes.")
                        # Update session state
                        st.session_state.user_info['full_name'] = new_full_name
                    else:
                        st.error("Error updating profile")
                else:
                    st.info("No changes detected")

def change_password(username, current_password, new_password):
    """Change user password if current password is correct"""
    try:
        # Hash passwords
        current_password_hash = hashlib.sha256(current_password.encode()).hexdigest()
        new_password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        # Verify current password
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM users WHERE username = ? AND password_hash = ?",
            (username, current_password_hash)
        )
        
        user_id = cursor.fetchone()
        
        if not user_id:
            conn.close()
            return False
        
        # Update password
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_password_hash, user_id[0])
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error changing password: {str(e)}")
        return False

def update_profile(username, new_full_name):
    """Update user profile information"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET full_name = ? WHERE username = ?",
            (new_full_name, username)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating profile: {str(e)}")
        return False

if __name__ == "__main__":
    main()