import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

# Database files
DBS = {
    "Accounts Analysis": "transactions.db",
    "Limit Monitoring": "transaction_monitoring.db",
    "Fraud Detection": "fraud_detection.db"
}

# Helper functions
def fetch_metric(db_file, query):
    """Fetch a single metric from the database."""
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error fetching metric: {str(e)}")
        return f"Error: {e}"

def fetch_date_range(db_file, table, date_column="timestamp"):
    """Fetch the date range for a table."""
    try:
        conn = sqlite3.connect(db_file)
        df = pd.read_sql_query(f"SELECT MIN({date_column}), MAX({date_column}) FROM {table}", conn)
        conn.close()
        return df.iloc[0, 0], df.iloc[0, 1]
    except Exception as e:
        logger.error(f"Error fetching date range: {str(e)}")
        return None, None

def check_database_exists(db_file):
    """Check if a database file exists."""
    return os.path.exists(db_file)

# Page layout
st.set_page_config(
    page_title="📊 Unified Financial Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Unified Financial Intelligence Dashboard")
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2091/2091751.png", width=100)
st.sidebar.header("Navigation")
st.sidebar.page_link("app.py", label="📈 Dashboard Home", icon="🏠")
st.sidebar.page_link("pages/1_multiple_accounts.py", label="👥 Multiple Accounts Analysis", icon="🔍")
st.sidebar.page_link("pages/2_limit_monitoring.py", label="🚦 Limit Monitoring", icon="⚠️")
st.sidebar.page_link("pages/3_fraud_detection.py", label="🛡️ Fraud Detection System", icon="🔒")

# System status
st.sidebar.markdown("---")
st.sidebar.subheader("System Status")

# Check database status
db_status = {}
for name, db_file in DBS.items():
    exists = check_database_exists(db_file)
    db_status[name] = "✅ Connected" if exists else "❌ Not Found"
    
status_df = pd.DataFrame({
    "Module": db_status.keys(),
    "Status": db_status.values()
})
st.sidebar.dataframe(status_df, hide_index=True, use_container_width=True)

# Summary cards
st.markdown("### 🔍 Summary Overview")
cols = st.columns(3)

# --- Transactions.db ---
with cols[0]:
    st.subheader("👥 Accounts Analysis")
    if check_database_exists(DBS["Accounts Analysis"]):
        total_tx = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(*) FROM transactions")
        unique_individuals = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(DISTINCT individual_id) FROM transactions")
        total_amt = fetch_metric(DBS["Accounts Analysis"], "SELECT SUM(amount) FROM transactions")
        
        st.metric("Transactions", f"{total_tx:,}" if isinstance(total_tx, (int, float)) else total_tx)
        st.metric("Individuals", f"{unique_individuals:,}" if isinstance(unique_individuals, (int, float)) else unique_individuals)
        st.metric("Total Amount", f"${total_amt:,.2f}" if isinstance(total_amt, (int, float)) else total_amt)
    else:
        st.warning("Database not found. Please initialize the module first.")

# --- transaction_monitoring.db ---
with cols[1]:
    st.subheader("🚦 Limit Monitoring")
    if check_database_exists(DBS["Limit Monitoring"]):
        violations = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM violations")
        files = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM uploaded_files")
        settings = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM settings")
        
        st.metric("Violations Logged", f"{violations:,}" if isinstance(violations, (int, float)) else violations)
        st.metric("Files Uploaded", f"{files:,}" if isinstance(files, (int, float)) else files)
        st.metric("Settings Count", f"{settings:,}" if isinstance(settings, (int, float)) else settings)
    else:
        st.warning("Database not found. Please initialize the module first.")

# --- fraud_detection.db ---
with cols[2]:
    st.subheader("🛡️ Fraud Detection")
    if check_database_exists(DBS["Fraud Detection"]):
        frauds = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results")
        suspicious = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1")
        users = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM users")
        
        st.metric("Total Analyses", f"{frauds:,}" if isinstance(frauds, (int, float)) else frauds)
        st.metric("Suspicious Detected", f"{suspicious:,}" if isinstance(suspicious, (int, float)) else suspicious)
        st.metric("Users", f"{users:,}" if isinstance(users, (int, float)) else users)
    else:
        st.warning("Database not found. Please initialize the module first.")

# Data range overview
st.markdown("### 🗓️ Data Ranges")
dr_cols = st.columns(3)

with dr_cols[0]:
    st.markdown("**Accounts Analysis**")
    if check_database_exists(DBS["Accounts Analysis"]):
        s, e = fetch_date_range(DBS["Accounts Analysis"], "transactions")
        st.write(f"{s or 'N/A'} ➡️ {e or 'N/A'}")
    else:
        st.write("Database not found")

with dr_cols[1]:
    st.markdown("**Limit Monitoring**")
    if check_database_exists(DBS["Limit Monitoring"]):
        s, e = fetch_date_range(DBS["Limit Monitoring"], "violations", "created_at")
        st.write(f"{s or 'N/A'} ➡️ {e or 'N/A'}")
    else:
        st.write("Database not found")

with dr_cols[2]:
    st.markdown("**Fraud Detection**")
    if check_database_exists(DBS["Fraud Detection"]):
        s, e = fetch_date_range(DBS["Fraud Detection"], "fraud_detection_results", "timestamp")
        st.write(f"{s or 'N/A'} ➡️ {e or 'N/A'}")
    else:
        st.write("Database not found")

# Module navigation cards
st.markdown("---")
st.header("📁 Open Modules")

col_mod1, col_mod2, col_mod3 = st.columns(3)
with col_mod1:
    st.page_link("pages/1_multiple_accounts.py", label="🔍 Multiple Accounts Analysis", icon="🔗")
    st.markdown("""
    - Track individuals with multiple accounts
    - Identify potential account structuring
    - Analyze transaction patterns
    """)
    
with col_mod2:
    st.page_link("pages/2_limit_monitoring.py", label="🚦 Limit Monitoring", icon="🔗")
    st.markdown("""
    - Monitor daily, weekly, monthly limits
    - Detect limit violations and circumvention
    - Configure threshold settings
    """)
    
with col_mod3:
    st.page_link("pages/3_fraud_detection.py", label="🛡️ Fraud Detection System", icon="🔗")
    st.markdown("""
    - ML-based transaction risk scoring
    - Batch processing of transactions
    - Visualize suspicious activity
    """)

st.markdown("---")
st.info("This dashboard provides a snapshot of all transaction monitoring systems. Visit each module for full analysis, management, and exports.")

# Version and last updated info
st.sidebar.markdown("---")
st.sidebar.caption(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
st.sidebar.caption("Version 1.0.0")
