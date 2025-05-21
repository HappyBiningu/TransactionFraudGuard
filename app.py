import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
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
        
# Helper function to fetch time series data for visualizations
def fetch_time_series_data(db_file, query):
    """Fetch time series data for charts"""
    try:
        conn = sqlite3.connect(db_file)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error fetching time series data: {str(e)}")
        return pd.DataFrame()

# Helper function to calculate KPI trends
def calculate_kpi_trend(db_file, query_current, query_previous):
    """Calculate KPI trend (current vs previous period)"""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Current period value
        cursor.execute(query_current)
        current = cursor.fetchone()[0] or 0
        
        # Previous period value
        cursor.execute(query_previous)
        previous = cursor.fetchone()[0] or 0
        
        conn.close()
        
        if previous == 0:
            # Avoid division by zero
            percent_change = 100 if current > 0 else 0
        else:
            percent_change = ((current - previous) / previous) * 100
            
        return current, percent_change
    except Exception as e:
        return 0, 0

# Page layout
st.set_page_config(page_title="📊 Unified Financial Dashboard", layout="wide", menu_items=None)

# Check if user is logged in
is_authenticated = login_page()

# Only render sidebar if user is authenticated
if is_authenticated:
    # Render sidebar navigation
    render_sidebar()
    
    # Custom CSS for modern styling with a more sophisticated design
    st.markdown("""
    <style>
        :root {
            --primary-color: #2563EB;
            --primary-light: #60A5FA;
            --primary-dark: #1E40AF; 
            --secondary-color: #10B981;
            --secondary-light: #6EE7B7;
            --tertiary-color: #F59E0B;
            --tertiary-light: #FCD34D;
            --background-light: #F9FAFB;
            --background-card: #FFFFFF;
            --text-dark: #1F2937;
            --text-muted: #6B7280;
            --card-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            --card-shadow-hover: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            --border-radius: 12px;
            --gradient-blue: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
            --gradient-green: linear-gradient(135deg, var(--secondary-color), var(--secondary-light));
            --gradient-amber: linear-gradient(135deg, var(--tertiary-color), var(--tertiary-light));
        }
        
        .main-container {
            background-color: var(--background-light);
            border-radius: var(--border-radius);
            padding: 2rem;
            margin-bottom: 2rem;
        }
        
        .main-header {
            font-size: 2.5rem;
            font-weight: 800;
            background-image: linear-gradient(135deg, #1E3A8A, #3B82F6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-align: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #E5E7EB;
            letter-spacing: -0.025em;
        }
        
        .section-header {
            font-size: 1.8rem;
            font-weight: 700;
            color: var(--primary-dark);
            margin: 2rem 0 1.5rem 0;
            padding-bottom: 0.5rem;
            position: relative;
        }
        
        .section-header::after {
            content: "";
            position: absolute;
            bottom: 0;
            left: 0;
            width: 60px;
            height: 4px;
            background: var(--gradient-blue);
            border-radius: 2px;
        }
        
        .metric-card {
            background-color: var(--background-card);
            border-radius: var(--border-radius);
            padding: 1.75rem;
            box-shadow: var(--card-shadow);
            text-align: center;
            margin-bottom: 1.5rem;
            transition: all 0.3s ease;
            border-top: 5px solid;
            overflow: hidden;
            position: relative;
        }
        
        .metric-card:hover {
            transform: translateY(-7px);
            box-shadow: var(--card-shadow-hover);
        }
        
        .metric-card-accounts {
            border-top-color: var(--primary-color);
        }
        
        .metric-card-accounts::before {
            background: var(--gradient-blue);
        }
        
        .metric-card-limits {
            border-top-color: var(--secondary-color);
        }
        
        .metric-card-limits::before {
            background: var(--gradient-green);
        }
        
        .metric-card-fraud {
            border-top-color: var(--tertiary-color);
        }
        
        .metric-card-fraud::before {
            background: var(--gradient-amber);
        }
        
        .metric-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 5px;
            opacity: 0.7;
            transition: height 0.3s ease-in-out;
        }
        
        .metric-card:hover::before {
            height: 10px;
        }
        
        .metric-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        
        .metric-value {
            font-size: 2.2rem;
            font-weight: 800;
            margin: 0.5rem 0;
            transition: transform 0.3s ease;
        }
        
        .metric-value-accounts {
            color: var(--primary-color);
        }
        
        .metric-value-limits {
            color: var(--secondary-color);
        }
        
        .metric-value-fraud {
            color: var(--tertiary-color);
        }
        
        .metric-card:hover .metric-value {
            transform: scale(1.05);
        }
        
        .metric-label {
            font-size: 0.95rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.075em;
            font-weight: 600;
            margin-bottom: 0.75rem;
        }
        
        .module-card {
            background-color: var(--background-card);
            border-radius: var(--border-radius);
            padding: 2rem;
            box-shadow: var(--card-shadow);
            height: 100%;
            transition: all 0.3s ease;
            border-left: 5px solid transparent;
            position: relative;
            overflow: hidden;
        }
        
        .module-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--card-shadow-hover);
        }
        
        .module-card-accounts {
            border-left-color: var(--primary-color);
        }
        
        .module-card-limits {
            border-left-color: var(--secondary-color);
        }
        
        .module-card-fraud {
            border-left-color: var(--tertiary-color);
        }
        
        .module-title {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 1.25rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid #E5E7EB;
            position: relative;
        }
        
        .module-title-accounts {
            color: var(--primary-dark);
        }
        
        .module-title-limits {
            color: var(--secondary-color);
        }
        
        .module-title-fraud {
            color: var(--tertiary-color);
        }
        
        .timeline-card {
            background-color: var(--background-card);
            border-radius: var(--border-radius);
            padding: 1.25rem;
            box-shadow: var(--card-shadow);
            margin-bottom: 1.5rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .timeline-card:hover {
            transform: translateY(-3px);
            box-shadow: var(--card-shadow-hover);
        }
        
        .timeline-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 5px;
            height: 100%;
            opacity: 0.7;
        }
        
        .timeline-card-accounts::before {
            background: var(--gradient-blue);
        }
        
        .timeline-card-limits::before {
            background: var(--gradient-green);
        }
        
        .timeline-card-fraud::before {
            background: var(--gradient-amber);
        }
        
        .timeline-title {
            font-size: 1.2rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .timeline-title-accounts {
            color: var(--primary-dark);
        }
        
        .timeline-title-limits {
            color: var(--secondary-color);
        }
        
        .timeline-title-fraud {
            color: var(--tertiary-color);
        }
        
        .date-range {
            font-weight: 500;
            font-size: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .date-range-arrow {
            margin: 0 0.5rem;
            color: var(--text-muted);
        }
        
        .feature-card {
            background-color: var(--background-card);
            border-radius: var(--border-radius);
            padding: 2rem;
            box-shadow: var(--card-shadow);
            height: 100%;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            z-index: 1;
        }
        
        .feature-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-size: 200% 200%;
            background-position: 0 0;
            opacity: 0;
            z-index: -1;
            transition: opacity 0.5s ease;
        }
        
        .feature-card:hover::before {
            opacity: 0.05;
        }
        
        .feature-card-accounts::before {
            background-image: var(--gradient-blue);
        }
        
        .feature-card-limits::before {
            background-image: var(--gradient-green);
        }
        
        .feature-card-fraud::before {
            background-image: var(--gradient-amber);
        }
        
        .feature-card:hover {
            transform: translateY(-7px);
            box-shadow: var(--card-shadow-hover);
        }
        
        .feature-icon {
            background-color: rgba(37, 99, 235, 0.1);
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 1.5rem;
            font-size: 1.75rem;
        }
        
        .feature-icon-accounts {
            background-color: rgba(37, 99, 235, 0.1);
            color: var(--primary-color);
        }
        
        .feature-icon-limits {
            background-color: rgba(16, 185, 129, 0.1);
            color: var(--secondary-color);
        }
        
        .feature-icon-fraud {
            background-color: rgba(245, 158, 11, 0.1);
            color: var(--tertiary-color);
        }
        
        .feature-title {
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 1rem;
        }
        
        .feature-title-accounts {
            color: var(--primary-dark);
        }
        
        .feature-title-limits {
            color: var(--secondary-color);
        }
        
        .feature-title-fraud {
            color: var(--tertiary-color);
        }
        
        .feature-list {
            margin-left: 0;
            padding-left: 1.25rem;
            color: var(--text-dark);
        }
        
        .feature-list li {
            margin-bottom: 0.5rem;
            position: relative;
            padding-left: 0.5rem;
        }
        
        .feature-list li::before {
            content: "";
            position: absolute;
            left: -1.25rem;
            top: 0.5rem;
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }
        
        .feature-list-accounts li::before {
            background-color: var(--primary-color);
        }
        
        .feature-list-limits li::before {
            background-color: var(--secondary-color);
        }
        
        .feature-list-fraud li::before {
            background-color: var(--tertiary-color);
        }
        
        .overview-card {
            background-color: var(--background-card);
            border-radius: var(--border-radius);
            padding: 2rem;
            box-shadow: var(--card-shadow);
            margin: 2.5rem 0 1rem;
            border-left: 5px solid var(--primary-color);
            transition: all 0.3s ease;
        }
        
        .overview-card:hover {
            box-shadow: var(--card-shadow-hover);
        }
        
        .overview-title {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--primary-dark);
            margin-bottom: 1rem;
        }
        
        .overview-content {
            color: var(--text-dark);
            line-height: 1.6;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Main header with custom container
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    st.markdown('<h1 class="main-header">Unified Financial Intelligence Platform</h1>', unsafe_allow_html=True)
    
    # Summary cards section
    st.markdown('<h2 class="section-header">Intelligence Dashboard</h2>', unsafe_allow_html=True)
    
    # Create a container for metrics
    metrics_cols = st.columns([1,1,1])
    
    # --- Transactions.db ---
    with metrics_cols[0]:
        total_tx = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(*) FROM transactions")
        unique_individuals = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(DISTINCT individual_id) FROM transactions")
        total_amt = fetch_metric(DBS["Accounts Analysis"], "SELECT SUM(amount) FROM transactions")
        
        # Format the total amount correctly
        formatted_amount = f"${total_amt:,.2f}" if isinstance(total_amt, (int, float)) else "$0.00"
        
        st.markdown(f"""
        <div class="metric-card metric-card-accounts">
            <div class="metric-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="#2563EB" viewBox="0 0 16 16">
                    <path d="M11 6a3 3 0 1 1-6 0 3 3 0 0 1 6 0z"/>
                    <path fill-rule="evenodd" d="M0 8a8 8 0 1 1 16 0A8 8 0 0 1 0 8zm8-7a7 7 0 0 0-5.468 11.37C3.242 11.226 4.805 10 8 10s4.757 1.225 5.468 2.37A7 7 0 0 0 8 1z"/>
                </svg>
            </div>
            <div class="module-title module-title-accounts">Account Analysis</div>
            <div class="metric-label">Transactions</div>
            <div class="metric-value metric-value-accounts">{total_tx:,}</div>
            <div class="metric-label">Unique Individuals</div>
            <div class="metric-value metric-value-accounts">{unique_individuals:,}</div>
            <div class="metric-label">Total Amount</div>
            <div class="metric-value metric-value-accounts">{formatted_amount}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- transaction_monitoring.db ---
    with metrics_cols[1]:
        violations = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM violations")
        files = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM uploaded_files")
        settings = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM settings")
        
        st.markdown(f"""
        <div class="metric-card metric-card-limits">
            <div class="metric-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="#10B981" viewBox="0 0 16 16">
                    <path d="M5 3a5 5 0 0 0 0 10h6a5 5 0 0 0 0-10H5zm6 9a4 4 0 1 1 0-8 4 4 0 0 1 0 8z"/>
                </svg>
            </div>
            <div class="module-title module-title-limits">Limit Monitoring</div>
            <div class="metric-label">Violations Detected</div>
            <div class="metric-value metric-value-limits">{violations:,}</div>
            <div class="metric-label">Files Analyzed</div>
            <div class="metric-value metric-value-limits">{files:,}</div>
            <div class="metric-label">Rule Settings</div>
            <div class="metric-value metric-value-limits">{settings:,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- fraud_detection.db ---
    with metrics_cols[2]:
        frauds = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results")
        suspicious = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1")
        users = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM users")
        
        st.markdown(f"""
        <div class="metric-card metric-card-fraud">
            <div class="metric-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" fill="#F59E0B" viewBox="0 0 16 16">
                    <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2z"/>
                </svg>
            </div>
            <div class="module-title module-title-fraud">Fraud Detection</div>
            <div class="metric-label">Total Analyses</div>
            <div class="metric-value metric-value-fraud">{frauds:,}</div>
            <div class="metric-label">Suspicious Detected</div>
            <div class="metric-value metric-value-fraud">{suspicious:,}</div>
            <div class="metric-label">System Users</div>
            <div class="metric-value metric-value-fraud">{users:,}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Data range overview
    st.markdown('<h2 class="section-header">Activity Timeline</h2>', unsafe_allow_html=True)
    date_cols = st.columns(3)
    
    with date_cols[0]:
        s, e = fetch_date_range(DBS["Accounts Analysis"], "transactions")
        st.markdown(f"""
        <div class="timeline-card timeline-card-accounts">
            <div class="timeline-title timeline-title-accounts">Account Analysis Period</div>
            <div class="date-range">
                <span>{s or 'No data'}</span>
                <span class="date-range-arrow">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M1 8a.5.5 0 0 1 .5-.5h11.793l-3.147-3.146a.5.5 0 0 1 .708-.708l4 4a.5.5 0 0 1 0 .708l-4 4a.5.5 0 0 1-.708-.708L13.293 8.5H1.5A.5.5 0 0 1 1 8z"/>
                    </svg>
                </span>
                <span>{e or 'No data'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with date_cols[1]:
        s, e = fetch_date_range(DBS["Limit Monitoring"], "violations", "created_at")
        st.markdown(f"""
        <div class="timeline-card timeline-card-limits">
            <div class="timeline-title timeline-title-limits">Limit Monitoring Period</div>
            <div class="date-range">
                <span>{s or 'No data'}</span>
                <span class="date-range-arrow">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M1 8a.5.5 0 0 1 .5-.5h11.793l-3.147-3.146a.5.5 0 0 1 .708-.708l4 4a.5.5 0 0 1 0 .708l-4 4a.5.5 0 0 1-.708-.708L13.293 8.5H1.5A.5.5 0 0 1 1 8z"/>
                    </svg>
                </span>
                <span>{e or 'No data'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with date_cols[2]:
        s, e = fetch_date_range(DBS["Fraud Detection"], "fraud_detection_results", "timestamp")
        st.markdown(f"""
        <div class="timeline-card timeline-card-fraud">
            <div class="timeline-title timeline-title-fraud">Fraud Detection Period</div>
            <div class="date-range">
                <span>{s or 'No data'}</span>
                <span class="date-range-arrow">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                        <path fill-rule="evenodd" d="M1 8a.5.5 0 0 1 .5-.5h11.793l-3.147-3.146a.5.5 0 0 1 .708-.708l4 4a.5.5 0 0 1 0 .708l-4 4a.5.5 0 0 1-.708-.708L13.293 8.5H1.5A.5.5 0 0 1 1 8z"/>
                    </svg>
                </span>
                <span>{e or 'No data'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Feature highlights section
    st.markdown('<h2 class="section-header">Platform Capabilities</h2>', unsafe_allow_html=True)
    feature_cols = st.columns(3)
    
    with feature_cols[0]:
        st.markdown("""
        <div class="feature-card feature-card-accounts">
            <div class="feature-icon feature-icon-accounts">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M6 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm-5 6s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1H1zM11 3.5a.5.5 0 0 1 .5-.5h4a.5.5 0 0 1 .5.5v4a.5.5 0 0 1-1 0V4H12v3.5a.5.5 0 0 1-1 0v-4z"/>
                </svg>
            </div>
            <div class="feature-title feature-title-accounts">Multiple Account Detection</div>
            <ul class="feature-list feature-list-accounts">
                <li>Identify individuals with accounts across multiple banks</li>
                <li>Flag high-risk patterns and unusual activity</li>
                <li>Monitor transaction flows between related accounts</li>
                <li>Generate comprehensive relationship networks</li>
                <li>Visual mapping of complex account structures</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with feature_cols[1]:
        st.markdown("""
        <div class="feature-card feature-card-limits">
            <div class="feature-icon feature-icon-limits">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M9.5 2a.5.5 0 0 1 0 1h-3a.5.5 0 0 1 0-1h3zm-3 2a.5.5 0 0 0 .5.5h3a.5.5 0 0 0 0-1h-3a.5.5 0 0 0-.5.5zm1.5 3a.5.5 0 0 1 0 1H3a.5.5 0 0 1 0-1h5zm-5 2a.5.5 0 0 0 .5.5h5a.5.5 0 0 0 0-1H3a.5.5 0 0 0-.5.5zm9.5-4a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"/>
                    <path fill-rule="evenodd" d="M13.5 3a1 1 0 0 0-1 1v8a1 1 0 0 0 1 1h1a1 1 0 0 0 1-1V4a1 1 0 0 0-1-1h-1zm-1 10a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2h-1a2 2 0 0 0-2 2v9z"/>
                </svg>
            </div>
            <div class="feature-title feature-title-limits">Transaction Limit Monitoring</div>
            <ul class="feature-list feature-list-limits">
                <li>Track daily, weekly, and monthly transaction limits</li>
                <li>Receive instant alerts on threshold violations</li>
                <li>Customize monitoring rules by account type</li>
                <li>Export compliance reports for regulatory review</li>
                <li>Historical trend analysis of limit breaches</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with feature_cols[2]:
        st.markdown("""
        <div class="feature-card feature-card-fraud">
            <div class="feature-icon feature-icon-fraud">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" fill="currentColor" viewBox="0 0 16 16">
                    <path d="M6 12.5a.5.5 0 0 1 .5-.5h3a.5.5 0 0 1 0 1h-3a.5.5 0 0 1-.5-.5ZM3 8.062C3 6.76 4.235 5.765 5.53 5.886a26.58 26.58 0 0 0 4.94 0C11.765 5.765 13 6.76 13 8.062v1.157a.933.933 0 0 1-.765.935c-.845.147-2.34.346-4.235.346-1.895 0-3.39-.2-4.235-.346A.933.933 0 0 1 3 9.219V8.062Zm4.542-.827a.25.25 0 0 0-.217.068l-.92.9a24.767 24.767 0 0 1-1.871-.183.25.25 0 0 0-.068.495c.55.076 1.232.149 2.02.193a.25.25 0 0 0 .189-.071l.754-.736.847 1.71a.25.25 0 0 0 .404.062l.932-.97a25.286 25.286 0 0 0 1.922-.188.25.25 0 0 0-.068-.495c-.538.074-1.207.145-1.98.189a.25.25 0 0 0-.166.076l-.754.785-.842-1.7a.25.25 0 0 0-.182-.135Z"/>
                    <path d="M8.5 1.866a1 1 0 1 0-1 0V3h-2A4.5 4.5 0 0 0 1 7.5V8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1v1a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1a1 1 0 0 0 1-1V9a1 1 0 0 0-1-1v-.5A4.5 4.5 0 0 0 10.5 3h-2V1.866ZM14 7.5V13a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V7.5A3.5 3.5 0 0 1 5.5 4h5A3.5 3.5 0 0 1 14 7.5Z"/>
                </svg>
            </div>
            <div class="feature-title feature-title-fraud">AI-Powered Fraud Detection</div>
            <ul class="feature-list feature-list-fraud">
                <li>Machine learning fraud prediction models</li>
                <li>Probabilistic risk scoring for transactions</li>
                <li>Detailed analysis and visual reporting</li>
                <li>Continuous model improvement with feedback</li>
                <li>Pattern recognition across transaction networks</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Platform overview message
    st.markdown("""
    <div class="overview-card">
        <div class="overview-title">Platform Overview</div>
        <div class="overview-content">
            The Unified Financial Intelligence Platform provides robust monitoring and analytics tools designed for financial institutions and regulatory bodies. 
            This dashboard presents a comprehensive overview of system activity, key metrics, and platform capabilities.
            <br><br>
            Select any module from the sidebar to access detailed analysis tools, management interfaces, and specialized reporting functions.
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Add additional CSS for new components
    st.markdown("""
    <style>
        .kpi-container {
            background-color: var(--background-light);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin: 2rem 0;
        }
        
        .kpi-card {
            background-color: var(--background-card);
            border-radius: var(--border-radius);
            padding: 1.25rem;
            box-shadow: var(--card-shadow);
            height: 100%;
            position: relative;
            overflow: hidden;
        }
        
        .kpi-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 0.5rem;
        }
        
        .kpi-value {
            font-size: 1.75rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        
        .kpi-trend {
            font-size: 0.875rem;
            display: flex;
            align-items: center;
        }
        
        .kpi-trend-up {
            color: #10B981;
        }
        
        .kpi-trend-down {
            color: #EF4444;
        }
        
        .kpi-trend-neutral {
            color: #6B7280;
        }
        
        .kpi-period {
            font-size: 0.75rem;
            color: var(--text-muted);
        }
        
        .chart-container {
            background-color: var(--background-card);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            box-shadow: var(--card-shadow);
            margin-bottom: 2rem;
            height: 100%;
        }
        
        .chart-title {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--primary-dark);
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #E5E7EB;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # KPI Summary Section
    st.markdown('<h2 class="section-header">Key Performance Indicators</h2>', unsafe_allow_html=True)
    st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
    
    # Create KPI summary
    kpi_cols = st.columns(4)
    
    # -- KPI 1: Transaction Volume Trend --
    with kpi_cols[0]:
        # Calculate current month vs previous month transaction volume
        current_query = f"""
        SELECT COUNT(*) FROM transactions 
        WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
        """
        previous_query = f"""
        SELECT COUNT(*) FROM transactions 
        WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', datetime('now', '-1 month'))
        """
        
        tx_count, tx_change = calculate_kpi_trend(
            DBS["Accounts Analysis"], 
            current_query, 
            previous_query
        )
        
        # Determine trend direction and icon
        if tx_change > 0:
            trend_class = "kpi-trend-up"
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="m7.247 4.86-4.796 5.481c-.566.647-.106 1.659.753 1.659h9.592a1 1 0 0 0 .753-1.659l-4.796-5.48a1 1 0 0 0-1.506 0z"/>
            </svg>"""
        elif tx_change < 0:
            trend_class = "kpi-trend-down"
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
            </svg>"""
        else:
            trend_class = "kpi-trend-neutral"
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 6.5a.5.5 0 0 1 .5.5v1.5H10a.5.5 0 0 1 0 1H8.5V11a.5.5 0 0 1-1 0V9.5H6a.5.5 0 0 1 0-1h1.5V7a.5.5 0 0 1 .5-.5z"/>
                <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3z"/>
            </svg>"""
        
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Transaction Volume</div>
            <div class="kpi-value">{tx_count:,}</div>
            <div class="kpi-trend {trend_class}">
                {trend_icon} {abs(tx_change):.1f}%
            </div>
            <div class="kpi-period">vs previous month</div>
        </div>
        """, unsafe_allow_html=True)
    
    # -- KPI 2: Fraud Detection Rate --
    with kpi_cols[1]:
        # Calculate current week vs previous week fraud detection rate
        current_query = f"""
        SELECT COUNT(*) FROM fraud_detection_results 
        WHERE predicted_suspicious = 1
        AND strftime('%Y-%W', timestamp) = strftime('%Y-%W', 'now')
        """
        previous_query = f"""
        SELECT COUNT(*) FROM fraud_detection_results 
        WHERE predicted_suspicious = 1
        AND strftime('%Y-%W', timestamp) = strftime('%Y-%W', datetime('now', '-7 days'))
        """
        
        fraud_count, fraud_change = calculate_kpi_trend(
            DBS["Fraud Detection"], 
            current_query, 
            previous_query
        )
        
        # Determine trend direction and icon (for fraud, down is good)
        if fraud_change < 0:
            trend_class = "kpi-trend-up"  # Fewer frauds is good
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="m7.247 4.86-4.796 5.481c-.566.647-.106 1.659.753 1.659h9.592a1 1 0 0 0 .753-1.659l-4.796-5.48a1 1 0 0 0-1.506 0z"/>
            </svg>"""
        elif fraud_change > 0:
            trend_class = "kpi-trend-down"  # More frauds is bad
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
            </svg>"""
        else:
            trend_class = "kpi-trend-neutral"
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 6.5a.5.5 0 0 1 .5.5v1.5H10a.5.5 0 0 1 0 1H8.5V11a.5.5 0 0 1-1 0V9.5H6a.5.5 0 0 1 0-1h1.5V7a.5.5 0 0 1 .5-.5z"/>
                <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3z"/>
            </svg>"""
        
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Fraud Detections</div>
            <div class="kpi-value">{fraud_count:,}</div>
            <div class="kpi-trend {trend_class}">
                {trend_icon} {abs(fraud_change):.1f}%
            </div>
            <div class="kpi-period">vs previous week</div>
        </div>
        """, unsafe_allow_html=True)
    
    # -- KPI 3: Limit Violation Rate --
    with kpi_cols[2]:
        # Calculate current week vs previous week violation rate
        current_query = f"""
        SELECT COUNT(*) FROM violations 
        WHERE strftime('%Y-%W', created_at) = strftime('%Y-%W', 'now')
        """
        previous_query = f"""
        SELECT COUNT(*) FROM violations 
        WHERE strftime('%Y-%W', created_at) = strftime('%Y-%W', datetime('now', '-7 days'))
        """
        
        violation_count, violation_change = calculate_kpi_trend(
            DBS["Limit Monitoring"], 
            current_query, 
            previous_query
        )
        
        # Determine trend direction and icon (for violations, down is good)
        if violation_change < 0:
            trend_class = "kpi-trend-up"  # Fewer violations is good
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="m7.247 4.86-4.796 5.481c-.566.647-.106 1.659.753 1.659h9.592a1 1 0 0 0 .753-1.659l-4.796-5.48a1 1 0 0 0-1.506 0z"/>
            </svg>"""
        elif violation_change > 0:
            trend_class = "kpi-trend-down"  # More violations is bad 
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
            </svg>"""
        else:
            trend_class = "kpi-trend-neutral"
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 6.5a.5.5 0 0 1 .5.5v1.5H10a.5.5 0 0 1 0 1H8.5V11a.5.5 0 0 1-1 0V9.5H6a.5.5 0 0 1 0-1h1.5V7a.5.5 0 0 1 .5-.5z"/>
                <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3z"/>
            </svg>"""
        
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Limit Violations</div>
            <div class="kpi-value">{violation_count:,}</div>
            <div class="kpi-trend {trend_class}">
                {trend_icon} {abs(violation_change):.1f}%
            </div>
            <div class="kpi-period">vs previous week</div>
        </div>
        """, unsafe_allow_html=True)
    
    # -- KPI 4: Multiple Accounts Detected --
    with kpi_cols[3]:
        # Calculate current month vs previous month multiple accounts
        current_query = f"""
        SELECT COUNT(DISTINCT individual_id) FROM transactions 
        WHERE individual_id IN (
            SELECT individual_id FROM transactions 
            GROUP BY individual_id 
            HAVING COUNT(DISTINCT bank_id) > 1
        )
        AND strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
        """
        previous_query = f"""
        SELECT COUNT(DISTINCT individual_id) FROM transactions 
        WHERE individual_id IN (
            SELECT individual_id FROM transactions 
            GROUP BY individual_id 
            HAVING COUNT(DISTINCT bank_id) > 1
        )
        AND strftime('%Y-%m', timestamp) = strftime('%Y-%m', datetime('now', '-1 month'))
        """
        
        multi_acct_count, multi_acct_change = calculate_kpi_trend(
            DBS["Accounts Analysis"], 
            current_query, 
            previous_query
        )
        
        # Determine trend direction and icon
        if multi_acct_change > 0:
            trend_class = "kpi-trend-up"
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="m7.247 4.86-4.796 5.481c-.566.647-.106 1.659.753 1.659h9.592a1 1 0 0 0 .753-1.659l-4.796-5.48a1 1 0 0 0-1.506 0z"/>
            </svg>"""
        elif multi_acct_change < 0:
            trend_class = "kpi-trend-down"
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/>
            </svg>"""
        else:
            trend_class = "kpi-trend-neutral"
            trend_icon = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16">
                <path d="M8 6.5a.5.5 0 0 1 .5.5v1.5H10a.5.5 0 0 1 0 1H8.5V11a.5.5 0 0 1-1 0V9.5H6a.5.5 0 0 1 0-1h1.5V7a.5.5 0 0 1 .5-.5z"/>
                <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2zm0 1a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3z"/>
            </svg>"""
        
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Multiple Accounts</div>
            <div class="kpi-value">{multi_acct_count:,}</div>
            <div class="kpi-trend {trend_class}">
                {trend_icon} {abs(multi_acct_change):.1f}%
            </div>
            <div class="kpi-period">vs previous month</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Close KPI container
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Interactive Data Visualizations Section
    st.markdown('<h2 class="section-header">Data Insights</h2>', unsafe_allow_html=True)
    
    # Create a layout for visualizations
    chart_cols = st.columns(2)
    
    # Chart 1: Transaction Volume by Bank
    with chart_cols[0]:
        try:
            # Get transaction volume by bank
            query = """
            SELECT b.bank_name, COUNT(*) as transaction_count
            FROM transactions t
            JOIN (
                SELECT DISTINCT bank_id, 'Bank ' || bank_id as bank_name
                FROM transactions
            ) b ON t.bank_id = b.bank_id
            GROUP BY b.bank_name
            ORDER BY transaction_count DESC
            LIMIT 10
            """
            
            # Fetch data
            tx_by_bank_df = fetch_time_series_data(DBS["Accounts Analysis"], query)
            
            if not tx_by_bank_df.empty:
                # Create bar chart
                fig = px.bar(
                    tx_by_bank_df,
                    x='bank_name',
                    y='transaction_count',
                    color_discrete_sequence=['#3B82F6'],
                    title="Transaction Volume by Bank",
                )
                
                # Customize layout
                fig.update_layout(
                    height=350,
                    xaxis_title="Bank",
                    yaxis_title="Transaction Count",
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False),
                    yaxis=dict(gridcolor='rgba(230,230,230,0.4)'),
                    margin=dict(l=10, r=10, t=50, b=30),
                )
                
                # Display chart in a container
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.info("No transaction data available for visualization.")
                st.markdown('</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Error generating transaction volume chart: {str(e)}")
    
    # Chart 2: Fraud Detection Trend
    with chart_cols[1]:
        try:
            # Get fraud detection trend data
            query = """
            SELECT 
                strftime('%Y-%m-%d', timestamp) as date,
                COUNT(*) as total_analyzed,
                SUM(CASE WHEN predicted_suspicious = 1 THEN 1 ELSE 0 END) as suspicious
            FROM fraud_detection_results
            GROUP BY date
            ORDER BY date DESC
            LIMIT 14
            """
            
            # Fetch data
            fraud_trend_df = fetch_time_series_data(DBS["Fraud Detection"], query)
            
            if not fraud_trend_df.empty:
                # Reverse for chronological order
                fraud_trend_df = fraud_trend_df.iloc[::-1].reset_index(drop=True)
                
                # Calculate suspicious percentage
                fraud_trend_df['suspicious_pct'] = (fraud_trend_df['suspicious'] / fraud_trend_df['total_analyzed'] * 100).round(1)
                
                # Create line chart
                fig = px.line(
                    fraud_trend_df,
                    x='date',
                    y='suspicious_pct',
                    markers=True,
                    title="Suspicious Transaction Rate Trend",
                    color_discrete_sequence=['#F59E0B'],
                )
                
                # Add shaded area
                fig.add_trace(
                    go.Scatter(
                        x=fraud_trend_df['date'],
                        y=fraud_trend_df['suspicious_pct'],
                        mode='none',
                        fill='tozeroy',
                        fillcolor='rgba(245, 158, 11, 0.2)',
                        name='Suspicious Rate',
                        showlegend=False,
                    )
                )
                
                # Customize layout
                fig.update_layout(
                    height=350,
                    xaxis_title="Date",
                    yaxis_title="Suspicious Rate (%)",
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False),
                    yaxis=dict(gridcolor='rgba(230,230,230,0.4)'),
                    margin=dict(l=10, r=10, t=50, b=30),
                )
                
                # Display chart in a container
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.info("No fraud detection data available for visualization.")
                st.markdown('</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Error generating fraud detection trend chart: {str(e)}")
    
    # Second row of charts
    chart_cols2 = st.columns(2)
    
    # Chart 3: Transaction Limit Violations by Type
    with chart_cols2[0]:
        try:
            # Get violation data by type
            query = """
            SELECT 
                CASE
                    WHEN type = 'daily' THEN 'Daily Limit'
                    WHEN type = 'weekly' THEN 'Weekly Limit'
                    WHEN type = 'monthly' THEN 'Monthly Limit'
                    ELSE type
                END as violation_type,
                COUNT(*) as violation_count
            FROM violations
            GROUP BY type
            ORDER BY violation_count DESC
            """
            
            # Fetch data
            violations_df = fetch_time_series_data(DBS["Limit Monitoring"], query)
            
            if not violations_df.empty:
                # Create pie chart
                fig = px.pie(
                    violations_df,
                    values='violation_count',
                    names='violation_type',
                    title="Limit Violations by Type",
                    color_discrete_sequence=['#2563EB', '#10B981', '#F59E0B', '#EF4444'],
                    hole=0.4,
                )
                
                # Customize layout
                fig.update_layout(
                    height=350,
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=10, r=10, t=50, b=10),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.2,
                        xanchor="center",
                        x=0.5
                    ),
                )
                
                # Display chart in a container
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.info("No violation data available for visualization.")
                st.markdown('</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Error generating violations chart: {str(e)}")
    
    # Chart 4: Multiple Accounts Distribution
    with chart_cols2[1]:
        try:
            # Get accounts distribution data
            query = """
            SELECT 
                COUNT(DISTINCT bank_id) as bank_count,
                COUNT(DISTINCT individual_id) as individual_count
            FROM transactions
            GROUP BY individual_id
            """
            
            # Fetch data
            accounts_df = fetch_time_series_data(DBS["Accounts Analysis"], query)
            
            if not accounts_df.empty:
                # Group by bank count
                accounts_grouped = accounts_df.groupby('bank_count')['individual_count'].sum().reset_index()
                accounts_grouped.columns = ['Number of Banks', 'Count of Individuals']
                
                # Create bar chart
                fig = px.bar(
                    accounts_grouped,
                    x='Number of Banks',
                    y='Count of Individuals',
                    color_discrete_sequence=['#1E40AF'],
                    title="Individuals by Number of Banks",
                )
                
                # Customize layout
                fig.update_layout(
                    height=350,
                    xaxis_title="Number of Banks",
                    yaxis_title="Count of Individuals",
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(showgrid=False, type='category'),
                    yaxis=dict(gridcolor='rgba(230,230,230,0.4)'),
                    margin=dict(l=10, r=10, t=50, b=30),
                )
                
                # Display chart in a container
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                st.info("No multiple accounts data available for visualization.")
                st.markdown('</div>', unsafe_allow_html=True)
                
        except Exception as e:
            st.error(f"Error generating multiple accounts chart: {str(e)}")
    
    # Close the main container
    st.markdown('</div>', unsafe_allow_html=True)