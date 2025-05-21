import streamlit as st
import sqlite3
import hashlib
import re
from datetime import datetime

# Database file
DB_FILE = "fraud_detection.db"

def init_auth_database():
    """Initialize the authentication database if it doesn't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            full_name TEXT,
            role TEXT CHECK(role IN ('analyst', 'supervisor', 'admin')),
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Create SHA-256 hash of the password"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    # Check for at least one uppercase, one lowercase, and one digit
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    return True, ""

def validate_username(username):
    """Validate username format"""
    if len(username) < 4:
        return False, "Username must be at least 4 characters long"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    # Check if username already exists
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
    exists = cursor.fetchone() is not None
    conn.close()
    
    if exists:
        return False, "Username already exists. Please choose another one."
    
    return True, ""

def create_user(username, password, full_name, role="analyst"):
    """Create a new user in the database"""
    # Validate username and password
    valid_username, username_msg = validate_username(username)
    if not valid_username:
        return False, username_msg
    
    valid_password, password_msg = validate_password(password)
    if not valid_password:
        return False, password_msg
    
    # Hash the password and create user
    password_hash = hash_password(password)
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (username, password_hash, full_name, role, last_login, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, password_hash, full_name, role, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1))
        conn.commit()
        conn.close()
        return True, "User created successfully"
    except sqlite3.IntegrityError:
        return False, "Username already exists. Please choose another one."
    except Exception as e:
        return False, f"Error creating user: {str(e)}"

def authenticate_user(username, password):
    """Authenticate a user based on username and password"""
    password_hash = hash_password(password)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, username, full_name, role 
        FROM users 
        WHERE username = ? AND password_hash = ? AND is_active = 1
    ''', (username, password_hash))
    
    user_data = cursor.fetchone()
    
    if user_data:
        # Update last login time
        cursor.execute('''
            UPDATE users SET last_login = ? WHERE id = ?
        ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_data[0]))
        conn.commit()
        
        # Return user info
        user_info = {
            "id": user_data[0],
            "username": user_data[1],
            "full_name": user_data[2],
            "role": user_data[3]
        }
        conn.close()
        return True, user_info
    
    conn.close()
    return False, None

def login_page():
    """Render the login page"""
    init_auth_database()
    
    # Hide the sidebar and all navigation
    hide_sidebar_style = """
        <style>
            [data-testid="collapsedControl"] {display: none !important;}
            section[data-testid="stSidebar"] {display: none !important;}
            #MainMenu {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            header {visibility: hidden !important;}
            .block-container {
                padding-top: 2rem;
                max-width: 800px;
                margin: 0 auto;
            }
            div[data-testid="stSidebarNav"] {display: none !important;}
            div[data-testid="baseButton-headerNoPadding"] {display: none !important;}
            button[kind="header"] {display: none !important;}
            ul[data-testid="stSidebarNavItems"] {display: none !important;}
            /* Hide back arrow button */
            button[data-testid="baseButton-secondary"] {display: none !important;}
            a[data-testid="stSidebarNavLink"] {display: none !important;}
            div[data-testid="collapsedControl-container"] {display: none !important;}
            nav[data-testid="stSidebar"] {display: none !important;}
            div.embeddedapp-wrapper {
                margin-left: 0 !important;
            }
            div.viewerBadge {display: none !important;}
            /* Hide all sidebar elements */
            div.stApp > header {display: none !important;}
            div.stApp > div[data-testid="stDecoration"] {display: none !important;}
            button.step-up, button.step-down {display: none !important;}
            section.main > div.block-container {padding-left: 20px !important; padding-right: 20px !important;}
        </style>
    """
    st.markdown(hide_sidebar_style, unsafe_allow_html=True)
    
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    
    if "show_signup" not in st.session_state:
        st.session_state.show_signup = False
    
    if st.session_state.user_info:
        # Already logged in
        st.success(f"Logged in as {st.session_state.user_info['full_name']} ({st.session_state.user_info['role']})")
        
        if st.button("Logout"):
            st.session_state.user_info = None
            st.rerun()
        
        return True
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("Financial Intelligence Platform", anchor=False)
        st.markdown("<p style='text-align: center;'>Secure access to financial monitoring tools</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Login form container with styling
        login_container = st.container(border=True)
        
        with login_container:
            # Login form
            if not st.session_state.show_signup:
                st.markdown("### 🔒 Login")
                
                with st.form("login_form"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        submitted = st.form_submit_button("Login", use_container_width=True)
                    
                    if submitted:
                        if not username or not password:
                            st.error("Please provide both username and password")
                        else:
                            success, user_info = authenticate_user(username, password)
                            if success:
                                st.session_state.user_info = user_info
                                st.success(f"Welcome, {user_info['full_name']}!")
                                st.rerun()
                            else:
                                st.error("Invalid username or password")
                
                st.markdown("<div style='text-align: center; margin-top: 15px;'>Don't have an account?</div>", unsafe_allow_html=True)
                
                # Center the signup button
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("Sign Up", use_container_width=True):
                        st.session_state.show_signup = True
                        st.rerun()
            
            # Sign-up form
            else:
                st.markdown("### 📝 Create Account")
                
                with st.form("signup_form"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    confirm_password = st.text_input("Confirm Password", type="password")
                    full_name = st.text_input("Full Name")
                    role = st.selectbox("Role", ["analyst", "supervisor"])
                    
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        submitted = st.form_submit_button("Create Account", use_container_width=True)
                    
                    if submitted:
                        if not username or not password or not confirm_password or not full_name:
                            st.error("All fields are required")
                        elif password != confirm_password:
                            st.error("Passwords do not match")
                        else:
                            success, message = create_user(username, password, full_name, role)
                            if success:
                                st.success(message)
                                # Log in the user automatically
                                st.session_state.user_info = {
                                    "username": username,
                                    "full_name": full_name,
                                    "role": role
                                }
                                st.session_state.show_signup = False
                                st.rerun()
                            else:
                                st.error(message)
                
                st.markdown("<div style='text-align: center; margin-top: 15px;'>Already have an account?</div>", unsafe_allow_html=True)
                
                # Center the login button
                col1, col2, col3 = st.columns([1, 1, 1])
                with col2:
                    if st.button("Log In", use_container_width=True):
                        st.session_state.show_signup = False
                        st.rerun()
    
    return False

def require_auth(function):
    """Decorator for pages that require authentication"""
    def wrapper(*args, **kwargs):
        if not st.session_state.get("user_info"):
            st.warning("Please log in to access this page")
            st.stop()
        return function(*args, **kwargs)
    return wrapper

def get_current_user():
    """Get the current logged-in user information"""
    return st.session_state.get("user_info", None)