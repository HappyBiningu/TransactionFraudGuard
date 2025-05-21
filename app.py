import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd
from auth import login_page, require_auth
from sidebar import render_sidebar

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
st.set_page_config(page_title="📊 Unified Financial Dashboard", layout="wide", menu_items=None)

# Check if user is logged in
is_authenticated = login_page()

# Only render sidebar if user is authenticated
if is_authenticated:
    # Render sidebar navigation
    render_sidebar()
    
    # Custom CSS for modern styling
    st.markdown("""
    <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: 700;
            color: #1E3A8A;
            margin-bottom: 1.5rem;
            text-align: center;
            padding-bottom: 1rem;
            border-bottom: 2px solid #f0f2f6;
        }
        .section-header {
            font-size: 1.8rem;
            font-weight: 600;
            color: #2563EB;
            margin: 1.5rem 0 1rem 0;
            padding-bottom: 0.5rem;
        }
        .metric-card {
            background-color: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            text-align: center;
            margin-bottom: 1rem;
            transition: transform 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #3B82F6;
            margin: 0.5rem 0;
        }
        .metric-label {
            font-size: 1rem;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .module-card {
            background-color: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            height: 100%;
        }
        .module-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #1E40AF;
            margin-bottom: 1rem;
        }
        .date-card {
            background-color: #EFF6FF;
            border-radius: 8px;
            padding: 1rem;
            text-align: center;
            margin-bottom: 1rem;
        }
        .date-range {
            font-weight: 500;
            color: #3B82F6;
        }
        .feature-icon {
            font-size: 2rem;
            margin-bottom: 1rem;
            color: #2563EB;
        }
        .feature-list {
            margin-left: 1.5rem;
        }
        .highlight-card {
            background-color: #EFF6FF;
            border-left: 5px solid #3B82F6;
            padding: 1.5rem;
            border-radius: 5px;
            margin: 1.5rem 0;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header
    st.markdown('<h1 class="main-header">📊 Unified Financial Intelligence Platform</h1>', unsafe_allow_html=True)
    
    # Summary cards section
    st.markdown('<h2 class="section-header">🔍 Key Metrics Overview</h2>', unsafe_allow_html=True)
    
    # Create a container for metrics
    metrics_cols = st.columns([1,1,1])
    
    # --- Transactions.db ---
    with metrics_cols[0]:
        total_tx = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(*) FROM transactions")
        unique_individuals = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(DISTINCT individual_id) FROM transactions")
        total_amt = fetch_metric(DBS["Accounts Analysis"], "SELECT SUM(amount) FROM transactions")
        
        st.markdown("""
        <div class="metric-card">
            <div class="module-title">👥 Accounts Analysis</div>
            <div class="metric-value">{:,}</div>
            <div class="metric-label">Transactions</div>
            <div class="metric-value">{:,}</div>
            <div class="metric-label">Unique Individuals</div>
            <div class="metric-value">${:,.2f}</div>
            <div class="metric-label">Total Transaction Amount</div>
        </div>
        """.format(total_tx, unique_individuals, float(total_amt) if isinstance(total_amt, (int, float)) else 0), unsafe_allow_html=True)
    
    # --- transaction_monitoring.db ---
    with metrics_cols[1]:
        violations = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM violations")
        files = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM uploaded_files")
        settings = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM settings")
        
        st.markdown("""
        <div class="metric-card">
            <div class="module-title">🚦 Limit Monitoring</div>
            <div class="metric-value">{:,}</div>
            <div class="metric-label">Violations Logged</div>
            <div class="metric-value">{:,}</div>
            <div class="metric-label">Files Processed</div>
            <div class="metric-value">{:,}</div>
            <div class="metric-label">Active Rule Settings</div>
        </div>
        """.format(violations, files, settings), unsafe_allow_html=True)
    
    # --- fraud_detection.db ---
    with metrics_cols[2]:
        frauds = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results")
        suspicious = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1")
        users = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM users")
        
        st.markdown("""
        <div class="metric-card">
            <div class="module-title">🛡️ Fraud Detection</div>
            <div class="metric-value">{:,}</div>
            <div class="metric-label">Total Analyses</div>
            <div class="metric-value">{:,}</div>
            <div class="metric-label">Suspicious Detected</div>
            <div class="metric-value">{:,}</div>
            <div class="metric-label">Registered Users</div>
        </div>
        """.format(frauds, suspicious, users), unsafe_allow_html=True)
    
    # Data range overview
    st.markdown('<h2 class="section-header">🗓️ Activity Timeline</h2>', unsafe_allow_html=True)
    date_cols = st.columns(3)
    
    with date_cols[0]:
        s, e = fetch_date_range(DBS["Accounts Analysis"], "transactions")
        st.markdown(f"""
        <div class="date-card">
            <div class="module-title">Accounts Analysis</div>
            <div class="date-range">{s or 'No data'} ➡️ {e or 'No data'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with date_cols[1]:
        s, e = fetch_date_range(DBS["Limit Monitoring"], "violations", "created_at")
        st.markdown(f"""
        <div class="date-card">
            <div class="module-title">Limit Monitoring</div>
            <div class="date-range">{s or 'No data'} ➡️ {e or 'No data'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with date_cols[2]:
        s, e = fetch_date_range(DBS["Fraud Detection"], "fraud_detection_results", "timestamp")
        st.markdown(f"""
        <div class="date-card">
            <div class="module-title">Fraud Detection</div>
            <div class="date-range">{s or 'No data'} ➡️ {e or 'No data'}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Feature highlights section
    st.markdown('<h2 class="section-header">✨ Platform Capabilities</h2>', unsafe_allow_html=True)
    feature_cols = st.columns(3)
    
    with feature_cols[0]:
        st.markdown("""
        <div class="module-card">
            <div class="feature-icon">🔎</div>
            <div class="module-title">Multiple Account Detection</div>
            <ul class="feature-list">
                <li>Identify individuals with accounts across multiple banks</li>
                <li>Flag high-risk patterns and unusual activity</li>
                <li>Monitor transaction flows between accounts</li>
                <li>Generate comprehensive relationship maps</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with feature_cols[1]:
        st.markdown("""
        <div class="module-card">
            <div class="feature-icon">🚨</div>
            <div class="module-title">Transaction Limit Monitoring</div>
            <ul class="feature-list">
                <li>Track daily, weekly, and monthly transaction limits</li>
                <li>Receive instant alerts on violations</li>
                <li>Customize thresholds by account type</li>
                <li>Export compliance reports for regulatory review</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with feature_cols[2]:
        st.markdown("""
        <div class="module-card">
            <div class="feature-icon">🤖</div>
            <div class="module-title">AI-Powered Fraud Detection</div>
            <ul class="feature-list">
                <li>Machine learning fraud prediction</li>
                <li>Risk scoring for transactions</li>
                <li>Detailed analysis and reporting</li>
                <li>Continuous model improvement with feedback</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Platform overview message
    st.markdown("""
    <div class="highlight-card">
        <h3>Platform Overview</h3>
        <p>The Unified Financial Intelligence Platform provides robust monitoring and analytics tools for financial institutions. 
        This dashboard offers a high-level overview of system activity and key metrics. Select any module from the sidebar for detailed analysis and management.</p>
    </div>
    """, unsafe_allow_html=True)