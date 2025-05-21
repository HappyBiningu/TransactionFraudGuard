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
    
    # Modern styling including hiding sidebar
    modern_style = """
        <style>
            /* Hide all navigation and sidebar elements */
            [data-testid="collapsedControl"] {display: none !important;}
            section[data-testid="stSidebar"] {display: none !important;}
            #MainMenu {visibility: hidden !important;}
            footer {visibility: hidden !important;}
            header {visibility: hidden !important;}
            div[data-testid="stSidebarNav"] {display: none !important;}
            div[data-testid="baseButton-headerNoPadding"] {display: none !important;}
            button[kind="header"] {display: none !important;}
            ul[data-testid="stSidebarNavItems"] {display: none !important;}
            button[data-testid="baseButton-secondary"] {display: none !important;}
            a[data-testid="stSidebarNavLink"] {display: none !important;}
            div[data-testid="collapsedControl-container"] {display: none !important;}
            nav[data-testid="stSidebar"] {display: none !important;}
            div.embeddedapp-wrapper {margin-left: 0 !important;}
            div.viewerBadge {display: none !important;}
            div.stApp > header {display: none !important;}
            div.stApp > div[data-testid="stDecoration"] {display: none !important;}
            button.step-up, button.step-down {display: none !important;}
            
            /* Custom modern styling */
            section.main > div.block-container {
                padding: 0 !important;
                max-width: 1000px !important;
                margin: 0 auto !important;
            }
            
            .title-container {
                background-color: #1E88E5;
                color: white;
                padding: 2rem 0;
                border-radius: 0 0 10px 10px;
                margin-bottom: 2rem;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            .login-card {
                background-color: white;
                border-radius: 10px;
                box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
                padding: 2rem;
                max-width: 450px;
                margin: 0 auto;
                transition: all 0.3s ease;
            }
            
            .form-header {
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 1.5rem;
                color: #1E88E5;
                text-align: center;
            }
            
            /* Input field styling */
            div[data-baseweb="input"] input,
            div[data-baseweb="select"] {
                border-radius: 8px !important;
                border: 1px solid #E0E0E0 !important;
                padding: 10px 15px !important;
                transition: all 0.2s ease !important;
            }
            
            div[data-baseweb="input"] input:focus,
            div[data-baseweb="select"]:focus {
                border-color: #1E88E5 !important;
                box-shadow: 0 0 0 2px rgba(30, 136, 229, 0.2) !important;
            }
            
            /* Button styling */
            .stButton button {
                border-radius: 8px !important;
                font-weight: 600 !important;
                transition: all 0.2s ease !important;
                height: 45px !important;
            }
            
            .stButton button[kind="primary"] {
                background-color: #1E88E5 !important;
                color: white !important;
            }
            
            .stButton button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1) !important;
            }
            
            /* Other elements */
            .stAlert {
                border-radius: 8px !important;
            }
            
            .divider {
                text-align: center;
                margin: 1.5rem 0;
                position: relative;
            }
            
            .divider:before {
                content: "";
                position: absolute;
                top: 50%;
                left: 0;
                right: 0;
                height: 1px;
                background-color: #E0E0E0;
                z-index: 1;
            }
            
            .divider span {
                background-color: white;
                padding: 0 10px;
                position: relative;
                z-index: 5;
                color: #757575;
                font-size: 0.9rem;
            }
            
            .auth-logo {
                font-size: 2.5rem;
                margin-bottom: 0.5rem;
            }
        </style>
    """
    st.markdown(modern_style, unsafe_allow_html=True)
    
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
    
    # Title section with stylish background
    st.markdown("""
        <div class="title-container">
            <div class="auth-logo">🔐</div>
            <h1>Financial Intelligence Platform</h1>
            <p>Secure access to financial monitoring tools</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Login/Signup card
    col1, col2, col3 = st.columns([1, 10, 1])
    
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        
        # Login form
        if not st.session_state.show_signup:
            st.markdown('<div class="form-header">Log in to your account</div>', unsafe_allow_html=True)
            
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                
                col1, col2 = st.columns([1, 1])
                with col1:
                    remember = st.checkbox("Remember me")
                
                submitted = st.form_submit_button("Sign In", use_container_width=True)
                
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
            
            # Divider
            st.markdown('<div class="divider"><span>OR</span></div>', unsafe_allow_html=True)
            
            # Sign up button
            if st.button("Create a new account", use_container_width=True):
                st.session_state.show_signup = True
                st.rerun()
        
        # Sign-up form
        else:
            st.markdown('<div class="form-header">Create a new account</div>', unsafe_allow_html=True)
            
            with st.form("signup_form"):
                # Two column layout for form fields
                col1, col2 = st.columns(2)
                with col1:
                    username = st.text_input("Username", placeholder="Choose a username")
                with col2:
                    full_name = st.text_input("Full Name", placeholder="Enter your full name")
                
                # Password fields
                password = st.text_input("Password", type="password", placeholder="Choose a secure password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")
                
                # Role selection with information
                role = st.selectbox("Select your role", 
                                  ["analyst", "supervisor"], 
                                  help="Analysts can view and analyze data. Supervisors have additional permissions to manage alerts and create reports.")
                
                # Terms and conditions
                agree = st.checkbox("I agree to the Terms and Conditions")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    submitted = st.form_submit_button("Create Account", use_container_width=True)
                
                if submitted:
                    if not username or not password or not confirm_password or not full_name:
                        st.error("All fields are required")
                    elif not agree:
                        st.error("You must agree to the Terms and Conditions")
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
            
            # Divider
            st.markdown('<div class="divider"><span>OR</span></div>', unsafe_allow_html=True)
            
            # Sign in button
            if st.button("Sign in with existing account", use_container_width=True):
                st.session_state.show_signup = False
                st.rerun()
        
        # Close the card div
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Footer
        st.markdown("""
            <div style="text-align: center; margin-top: 2rem; color: #757575; font-size: 0.8rem;">
                © 2025 Financial Intelligence Platform. All rights reserved.
            </div>
        """, unsafe_allow_html=True)
    
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