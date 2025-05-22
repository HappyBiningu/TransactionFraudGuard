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

def set_signup_state():
    """Set the signup state to show the signup form"""
    st.session_state.show_signup = True
    st.rerun()

def login_page():
    """Render the login page"""
    init_auth_database()
    
    if "user_info" not in st.session_state:
        st.session_state.user_info = None
    
    if "show_signup" not in st.session_state:
        st.session_state.show_signup = False
    
    # Add CSS to hide the sidebar and navigation completely when not logged in
    if not st.session_state.user_info:
        hide_streamlit_style = """
            <style>
                [data-testid="collapsedControl"] {display: none;}
                div[data-testid="stSidebarNav"] {display: none;}
                section[data-testid="stSidebar"] {display: none;}
                div.stApp [data-testid="stSidebar"] {display: none;}
                button[kind="secondary"] {display: none;}
                div[data-testid="stDecoration"] {display: none;}
                .css-1d391kg {display: none;}
                footer {visibility: hidden;}
                #MainMenu {visibility: hidden;}
                div[data-testid="stToolbar"] {display: none;}
                header[data-testid="stHeader"] {display: none;}
            </style>
        """
        st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
    # User is already authenticated, so we let the app handle the UI
    if st.session_state.user_info:
        # We won't put logout in the sidebar here - it will be handled 
        # in the user profile component in the sidebar by the main app
        pass
    
    if st.session_state.user_info:
        # Already logged in
        return True
    
    # Center the title with HTML
    st.markdown("<h1 style='text-align: center;'>Unified Financial Intelligence Platform</h1>", unsafe_allow_html=True)
    
    # Login form - with column layout to control width
    if not st.session_state.show_signup:
        # Create column layout to constrain width
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.form("login_form"):
                st.subheader("🔐 Login")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Login")
                
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
        
        # Sign up option below the form with prominent styling
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.write("")
            st.markdown("<h4 style='text-align: center; margin-top: 20px;'>Don't have an account?</h4>", unsafe_allow_html=True)
            st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
            if st.button("Sign Up →", type="primary", key="signup_btn", use_container_width=True):
                st.session_state.show_signup = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Sign-up form
    else:
        # Create column layout to constrain width
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.form("signup_form"):
                st.subheader("📝 Create Account")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                full_name = st.text_input("Full Name")
                role = st.selectbox("Role", ["analyst", "supervisor"])
                
                submitted = st.form_submit_button("Create Account")
                
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
            
            # Login option below the form
            st.write("")
            st.markdown("<h4 style='text-align: center; margin-top: 20px;'>Already have an account?</h4>", unsafe_allow_html=True)
            st.markdown("<div style='display: flex; justify-content: center;'>", unsafe_allow_html=True)
            if st.button("Log In →", type="primary", key="login_btn", use_container_width=True):
                st.session_state.show_signup = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
    
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