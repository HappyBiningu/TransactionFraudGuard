import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

# Database files
DBS = {
    "Accounts Analysis": "transactions.db",
    "Limit Monitoring": "transaction_monitoring.db",
    "Fraud Detection": "fraud_detection.db"
}

# Helper functions
def fetch_metric(db_file, query):
    try:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        return f"Error: {e}"

def fetch_date_range(db_file, table, date_column="timestamp"):
    try:
        conn = sqlite3.connect(db_file)
        df = pd.read_sql_query(f"SELECT MIN({date_column}), MAX({date_column}) FROM {table}", conn)
        conn.close()
        return df.iloc[0, 0], df.iloc[0, 1]
    except:
        return None, None

# Page layout
st.set_page_config(page_title="📊 Unified Financial Dashboard", layout="wide")
st.title("📊 Unified Financial Intelligence Dashboard")

# Summary cards
st.markdown("### 🔍 Summary Overview")
cols = st.columns(3)

# --- Transactions.db ---
with cols[0]:
    st.subheader("👥 Accounts Analysis")
    total_tx = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(*) FROM transactions")
    unique_individuals = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(DISTINCT individual_id) FROM transactions")
    total_amt = fetch_metric(DBS["Accounts Analysis"], "SELECT SUM(amount) FROM transactions")
    st.metric("Transactions", f"{total_tx:,}")
    st.metric("Individuals", f"{unique_individuals:,}")
    st.metric("Total Amount", f"${total_amt:,.2f}" if isinstance(total_amt, (int, float)) else total_amt)

# --- transaction_monitoring.db ---
with cols[1]:
    st.subheader("🚦 Limit Monitoring")
    violations = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM violations")
    files = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM uploaded_files")
    settings = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM settings")
    st.metric("Violations Logged", f"{violations:,}")
    st.metric("Files Uploaded", f"{files:,}")
    st.metric("Settings Count", f"{settings:,}")

# --- fraud_detection.db ---
with cols[2]:
    st.subheader("🛡️ Fraud Detection")
    frauds = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results")
    suspicious = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1")
    users = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM users")
    st.metric("Total Analyses", f"{frauds:,}")
    st.metric("Suspicious Detected", f"{suspicious:,}")
    st.metric("Users", f"{users:,}")

# Data range overview
st.markdown("### 🗓️ Data Ranges")
dr_cols = st.columns(3)

with dr_cols[0]:
    st.markdown("**Accounts Analysis**")
    s, e = fetch_date_range(DBS["Accounts Analysis"], "transactions")
    st.write(f"{s or 'N/A'} ➡️ {e or 'N/A'}")

with dr_cols[1]:
    st.markdown("**Limit Monitoring**")
    s, e = fetch_date_range(DBS["Limit Monitoring"], "violations", "created_at")
    st.write(f"{s or 'N/A'} ➡️ {e or 'N/A'}")

with dr_cols[2]:
    st.markdown("**Fraud Detection**")
    s, e = fetch_date_range(DBS["Fraud Detection"], "fraud_detection_results", "timestamp")
    st.write(f"{s or 'N/A'} ➡️ {e or 'N/A'}")

# Navigation
st.markdown("---")
st.header("📁 Open Modules")

col_mod1, col_mod2, col_mod3 = st.columns(3)
with col_mod1:
    st.page_link("pages/1_multiple_accounts.py", label="🔍 Multiple Accounts Analysis", icon="🔗")
with col_mod2:
    st.page_link("pages/2_limit_monitoring.py", label="🚦 Limit Monitoring", icon="🔗")
with col_mod3:
    st.page_link("pages/3_fraud_detection.py", label="🛡️ Fraud Detection System", icon="🔗")

st.markdown("---")
st.info("This dashboard provides a snapshot of all transaction monitoring systems. Visit each module for full analysis, management, and exports.")
