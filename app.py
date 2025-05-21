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
            --danger-color: #DC2626;
            --warning-color: #F59E0B;
            --success-color: #10B981;
        }
        
        /* Dashboard Pills */
        .dashboard-pill {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            color: white;
            background: var(--gradient-blue);
            margin: 0 4px;
            box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
        }
        
        /* System Status Indicators */
        .system-status {
            display: flex;
            justify-content: center;
            margin: 10px 0 30px;
            gap: 20px;
            flex-wrap: wrap;
        }
        
        .system-status-item {
            display: flex;
            align-items: center;
            background-color: rgba(249, 250, 251, 0.7);
            padding: 6px 12px;
            border-radius: 30px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }
        
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-indicator.green {
            background-color: var(--success-color);
            box-shadow: 0 0 5px var(--success-color);
        }
        
        .status-indicator.yellow {
            background-color: var(--warning-color);
            box-shadow: 0 0 5px var(--warning-color);
        }
        
        .status-indicator.red {
            background-color: var(--danger-color);
            box-shadow: 0 0 5px var(--danger-color);
        }
        
        .status-text {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-dark);
        }
        
        /* Enhanced Metrics Overview */
        .metrics-overview {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        /* Enhanced Metric Cards */
        .enhanced-metric-card {
            background-color: var(--background-card);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            box-shadow: var(--card-shadow);
            transition: all 0.3s ease;
            height: 100%;
            display: flex;
            flex-direction: column;
            position: relative;
            overflow: hidden;
        }
        
        .enhanced-metric-card:hover {
            transform: translateY(-8px);
            box-shadow: var(--card-shadow-hover);
        }
        
        .enhanced-metric-card::before {
            content: "";
            position: absolute;
            width: 100%;
            height: 5px;
            top: 0;
            left: 0;
            transition: height 0.3s ease-in-out;
        }
        
        .enhanced-metric-card:hover::before {
            height: 8px;
        }
        
        .accounts-card::before {
            background: var(--gradient-blue);
        }
        
        .limits-card::before {
            background: var(--gradient-green);
        }
        
        .fraud-card::before {
            background: var(--gradient-amber);
        }
        
        .metric-card-header {
            display: flex;
            align-items: center;
            margin-bottom: 1.25rem;
        }
        
        .metric-card-icon {
            font-size: 1.75rem;
            margin-right: 0.75rem;
        }
        
        .metric-card-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-dark);
        }
        
        .metric-card-body {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        
        .primary-metric {
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--primary-color);
            margin-bottom: 0.25rem;
            line-height: 1.1;
        }
        
        .metric-label {
            font-size: 0.95rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            margin-bottom: 1.25rem;
        }
        
        .metric-details {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1.25rem;
        }
        
        .secondary-metric {
            display: flex;
            flex-direction: column;
        }
        
        .secondary-value {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-dark);
        }
        
        .secondary-label {
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-top: 0.25rem;
        }
        
        .metric-trend {
            display: flex;
            align-items: center;
            font-size: 0.9rem;
            font-weight: 600;
            padding: 0.5rem 0.75rem;
            border-radius: 8px;
            margin-top: auto;
        }
        
        .trend-up {
            background-color: rgba(16, 185, 129, 0.1);
            color: var(--success-color);
        }
        
        .trend-down {
            background-color: rgba(239, 68, 68, 0.1);
            color: var(--danger-color);
        }
        
        .trend-neutral {
            background-color: rgba(107, 114, 128, 0.1);
            color: var(--text-muted);
        }
        
        .trend-icon {
            margin-right: 0.5rem;
        }
        
        .trend-value {
            margin-right: 0.5rem;
        }
        
        .trend-period {
            font-size: 0.8rem;
            font-weight: 500;
            opacity: 0.8;
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
    
    # Completely simplified header - removed all subtext
    st.markdown('<div style="margin-bottom: 20px;"></div>', unsafe_allow_html=True)
    
    # Summary cards section
    st.markdown('<h2 class="section-header">Intelligence Dashboard</h2>', unsafe_allow_html=True)
    
    # Create a container for metrics with enhanced appearance
    st.markdown('<div class="metrics-overview">', unsafe_allow_html=True)
    metrics_cols = st.columns([1,1,1])
    
    # --- Transactions.db ---
    with metrics_cols[0]:
        total_tx = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(*) FROM transactions")
        unique_individuals = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(DISTINCT individual_id) FROM transactions")
        total_amt = fetch_metric(DBS["Accounts Analysis"], "SELECT SUM(amount) FROM transactions")
        
        # Format the total amount correctly
        formatted_amount = f"${total_amt:,.2f}" if isinstance(total_amt, (int, float)) else "$0.00"
        
        # Get current month stats
        current_month = datetime.now().strftime("%Y-%m")
        current_month_tx = fetch_metric(
            DBS["Accounts Analysis"], 
            f"SELECT COUNT(*) FROM transactions WHERE strftime('%Y-%m', timestamp) = '{current_month}'"
        )
        
        # Calculate month-over-month change
        previous_month = (datetime.now() - timedelta(days=30)).strftime("%Y-%m")
        previous_month_tx = fetch_metric(
            DBS["Accounts Analysis"], 
            f"SELECT COUNT(*) FROM transactions WHERE strftime('%Y-%m', timestamp) = '{previous_month}'"
        )
        
        # Calculate percent change
        if previous_month_tx > 0:
            percent_change = ((current_month_tx - previous_month_tx) / previous_month_tx) * 100
        else:
            percent_change = 0
            
        # Determine trend direction and icon
        if percent_change > 0:
            trend_icon = "📈"
            trend_class = "trend-up"
        elif percent_change < 0:
            trend_icon = "📉"
            trend_class = "trend-down"
        else:
            trend_icon = "⚖️"
            trend_class = "trend-neutral"
        
        st.markdown(f"""
        <div class="enhanced-metric-card accounts-card">
            <div class="metric-card-header">
                <div class="metric-card-icon">💳</div>
                <div class="metric-card-title">Account Activity</div>
            </div>
            <div class="metric-card-body">
                <div class="primary-metric">{total_tx:,}</div>
                <div class="metric-label">Total Transactions</div>
                <div class="metric-details">
                    <div class="secondary-metric">
                        <span class="secondary-value">{unique_individuals:,}</span>
                        <span class="secondary-label">Unique Customers</span>
                    </div>
                    <div class="secondary-metric">
                        <span class="secondary-value">{formatted_amount}</span>
                        <span class="secondary-label">Total Volume</span>
                    </div>
                </div>
                <div class="metric-trend {trend_class}">
                    <span class="trend-icon">{trend_icon}</span>
                    <span class="trend-value">{abs(percent_change):.1f}%</span>
                    <span class="trend-period">vs last month</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- transaction_monitoring.db ---
    with metrics_cols[1]:
        violations = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM violations")
        files = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM uploaded_files")
        settings = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM settings")
        
        # Calculate day-to-day change in violations
        violations_today = fetch_metric(
            DBS["Limit Monitoring"],
            "SELECT COUNT(*) FROM violations WHERE DATE(timestamp) = DATE('now')"
        )
        violations_yesterday = fetch_metric(
            DBS["Limit Monitoring"],
            "SELECT COUNT(*) FROM violations WHERE DATE(timestamp) = DATE('now', '-1 day')"
        )
        
        # Ensure we're working with numbers for calculation
        try:
            today_count = int(violations_today)
            yesterday_count = int(violations_yesterday)
            
            if yesterday_count > 0:
                daily_change = ((today_count - yesterday_count) / yesterday_count) * 100
            else:
                daily_change = 100 if today_count > 0 else 0
        except (ValueError, TypeError):
            daily_change = 0
            
        # Determine trend icon and class
        if daily_change > 0:
            trend_icon = "🔺"
            trend_class = "trend-down"  # Increasing violations is bad
        elif daily_change < 0:
            trend_icon = "🔽"
            trend_class = "trend-up"  # Decreasing violations is good
        else:
            trend_icon = "⚖️"
            trend_class = "trend-neutral"
            
        st.markdown(f"""
        <div class="enhanced-metric-card limits-card">
            <div class="metric-card-header">
                <div class="metric-card-icon">⚠️</div>
                <div class="metric-card-title">Limit Monitoring</div>
            </div>
            <div class="metric-card-body">
                <div class="primary-metric">{violations:,}</div>
                <div class="metric-label">Total Violations</div>
                <div class="metric-details">
                    <div class="secondary-metric">
                        <span class="secondary-value">{files:,}</span>
                        <span class="secondary-label">Files Analyzed</span>
                    </div>
                    <div class="secondary-metric">
                        <span class="secondary-value">{settings:,}</span>
                        <span class="secondary-label">Rule Settings</span>
                    </div>
                </div>
                <div class="metric-trend {trend_class}">
                    <span class="trend-icon">{trend_icon}</span>
                    <span class="trend-value">{abs(daily_change):.1f}%</span>
                    <span class="trend-period">day-to-day change</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # --- fraud_detection.db ---
    with metrics_cols[2]:
        frauds = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results")
        suspicious = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1")
        users = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM users")
        
        # Calculate fraud detection rate
        detection_rate = 0
        if frauds > 0:
            detection_rate = (suspicious / frauds) * 100
            
        # Get recent trend in fraud detection
        recent_suspicious = fetch_metric(
            DBS["Fraud Detection"], 
            "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1 AND date(timestamp) >= date('now', '-7 day')"
        )
        previous_suspicious = fetch_metric(
            DBS["Fraud Detection"], 
            "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1 AND date(timestamp) BETWEEN date('now', '-14 day') AND date('now', '-8 day')"
        )
        
        # Calculate week-over-week change
        if previous_suspicious > 0:
            fraud_change = ((recent_suspicious - previous_suspicious) / previous_suspicious) * 100
        else:
            fraud_change = 100 if recent_suspicious > 0 else 0
            
        # Determine trend icon and class (for fraud, an increase is bad)
        if fraud_change > 0:
            trend_icon = "🔍"
            trend_class = "trend-down"
        elif fraud_change < 0:
            trend_icon = "👍"
            trend_class = "trend-up"
        else:
            trend_icon = "⚖️"
            trend_class = "trend-neutral"
        
        st.markdown(f"""
        <div class="enhanced-metric-card fraud-card">
            <div class="metric-card-header">
                <div class="metric-card-icon">🔒</div>
                <div class="metric-card-title">Fraud Detection</div>
            </div>
            <div class="metric-card-body">
                <div class="primary-metric">{suspicious:,}</div>
                <div class="metric-label">Suspicious Transactions</div>
                <div class="metric-details">
                    <div class="secondary-metric">
                        <span class="secondary-value">{frauds:,}</span>
                        <span class="secondary-label">Total Analyses</span>
                    </div>
                    <div class="secondary-metric">
                        <span class="secondary-value">{detection_rate:.1f}%</span>
                        <span class="secondary-label">Detection Rate</span>
                    </div>
                </div>
                <div class="metric-trend {trend_class}">
                    <span class="trend-icon">{trend_icon}</span>
                    <span class="trend-value">{abs(fraud_change):.1f}%</span>
                    <span class="trend-period">week-over-week</span>
                </div>
            </div>
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
    
    # Empty space instead of features section
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
    # Empty space instead of overview
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    
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
            HAVING COUNT(DISTINCT bank_name) > 1
        )
        AND strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')
        """
        previous_query = f"""
        SELECT COUNT(DISTINCT individual_id) FROM transactions 
        WHERE individual_id IN (
            SELECT individual_id FROM transactions 
            GROUP BY individual_id 
            HAVING COUNT(DISTINCT bank_name) > 1
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
            SELECT bank_name, COUNT(*) as transaction_count
            FROM transactions
            GROUP BY bank_name
            ORDER BY transaction_count DESC
            LIMIT 10
            """
            
            # Fetch data
            tx_by_bank_df = fetch_time_series_data(DBS["Accounts Analysis"], query)
            
            if not tx_by_bank_df.empty:
                # Create an enhanced bar chart with gradient color
                fig = px.bar(
                    tx_by_bank_df,
                    x='bank_name',
                    y='transaction_count',
                    color='transaction_count',
                    color_continuous_scale=[(0, "#60A5FA"), (0.5, "#3B82F6"), (1, "#1D4ED8")],
                    title="Transaction Volume by Bank",
                    text='transaction_count',  # Show value labels on bars
                    template="plotly_white"    # Use a cleaner template
                )
                
                # Add a percentage calculation
                total_transactions = tx_by_bank_df['transaction_count'].sum()
                tx_by_bank_df['percentage'] = (tx_by_bank_df['transaction_count'] / total_transactions * 100).round(1)
                
                # Customize layout with enhanced styling
                fig.update_layout(
                    height=400,
                    title={
                        'text': "<b>Transaction Volume by Bank</b>",
                        'y':0.95,
                        'x':0.5,
                        'xanchor': 'center',
                        'yanchor': 'top',
                        'font': {'size': 22, 'color': '#1E40AF'}
                    },
                    xaxis_title=None,  # Remove axis titles for cleaner look
                    yaxis_title=None,
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        showgrid=False,
                        showline=True,
                        linecolor='rgba(230,230,230,0.8)'
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(230,230,230,0.4)',
                        showline=True,
                        linecolor='rgba(230,230,230,0.8)'
                    ),
                    margin=dict(l=10, r=10, t=70, b=30),
                    coloraxis_showscale=False,  # Hide color scale
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=14,
                        font_family="Roboto"
                    )
                )
                
                # Customize hover information to show percentage
                fig.update_traces(
                    hovertemplate='<b>%{x}</b><br>Transactions: %{y:,}<br>Percentage: %{customdata:.1f}%',
                    customdata=tx_by_bank_df['percentage'].values,
                    texttemplate='%{y:,}',
                    textposition='outside',
                    textfont=dict(color='#1E40AF', size=12),
                    marker_line_width=0,
                    opacity=0.9
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
                
                # Create an enhanced visualization with dual metrics
                fig = go.Figure()
                
                # Add suspicious rate line
                fig.add_trace(go.Scatter(
                    x=fraud_trend_df['date'],
                    y=fraud_trend_df['suspicious_pct'],
                    mode='lines+markers',
                    name='Suspicious Rate (%)',
                    line=dict(color='#F59E0B', width=3),
                    marker=dict(size=8, color='#F59E0B', line=dict(width=2, color='white')),
                    fill='tozeroy',
                    fillcolor='rgba(245, 158, 11, 0.1)',
                    hovertemplate='<b>%{x}</b><br>Rate: %{y:.1f}%<br>'
                ))
                
                # Add total transactions analyzed line on secondary y-axis
                fig.add_trace(go.Scatter(
                    x=fraud_trend_df['date'],
                    y=fraud_trend_df['total_analyzed'],
                    mode='lines',
                    name='Total Analyzed',
                    line=dict(color='#3B82F6', width=2, dash='dot'),
                    yaxis='y2',
                    hovertemplate='<b>%{x}</b><br>Analyzed: %{y:,}<br>'
                ))
                
                # Add annotations for peaks in suspicious rate
                max_idx = fraud_trend_df['suspicious_pct'].idxmax()
                max_date = fraud_trend_df.loc[max_idx, 'date']
                max_pct = fraud_trend_df.loc[max_idx, 'suspicious_pct']
                
                fig.add_annotation(
                    x=max_date,
                    y=max_pct,
                    text=f"Peak: {max_pct:.1f}%",
                    showarrow=True,
                    arrowhead=1,
                    arrowsize=1,
                    arrowwidth=2,
                    arrowcolor='#DC2626',
                    font=dict(color='#DC2626', size=12),
                    bgcolor='white',
                    bordercolor='#DC2626',
                    borderwidth=1,
                    borderpad=4,
                    ay=-40
                )
                
                # Calculate trend line to show direction
                if len(fraud_trend_df) > 1:
                    last_week = fraud_trend_df.iloc[-7:] if len(fraud_trend_df) >= 7 else fraud_trend_df
                    first_val = last_week['suspicious_pct'].iloc[0]
                    last_val = last_week['suspicious_pct'].iloc[-1]
                    trend_text = "Increasing ↑" if last_val > first_val else "Decreasing ↓"
                    trend_color = "#DC2626" if last_val > first_val else "#10B981"
                    
                    # Add a trend indicator
                    fig.add_annotation(
                        x=fraud_trend_df['date'].iloc[-1],
                        y=fraud_trend_df['suspicious_pct'].min(),
                        text=f"Recent Trend: {trend_text}",
                        showarrow=False,
                        font=dict(color=trend_color, size=13, family="Arial Black"),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor=trend_color,
                        borderwidth=1,
                        borderpad=4,
                        xanchor="right",
                        yanchor="bottom",
                        xshift=10
                    )
                
                # Customize layout with enhanced styling
                fig.update_layout(
                    height=400,
                    title={
                        'text': "<b>Suspicious Transaction Rate Analysis</b>",
                        'y':0.95,
                        'x':0.5,
                        'xanchor': 'center',
                        'yanchor': 'top',
                        'font': {'size': 22, 'color': '#F59E0B'}
                    },
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5,
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='rgba(230,230,230,0.9)',
                        borderwidth=1
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        title=None,
                        showgrid=False,
                        showline=True,
                        linecolor='rgba(230,230,230,0.8)'
                    ),
                    yaxis=dict(
                        title=dict(
                            text='Suspicious Rate (%)',
                            font=dict(color='#F59E0B')
                        ),
                        tickfont=dict(color='#F59E0B'),
                        showgrid=True,
                        gridcolor='rgba(230,230,230,0.4)',
                        showline=True,
                        linecolor='rgba(230,230,230,0.8)'
                    ),
                    yaxis2=dict(
                        title=dict(
                            text='Transactions Analyzed',
                            font=dict(color='#3B82F6')
                        ),
                        tickfont=dict(color='#3B82F6'),
                        overlaying='y',
                        side='right',
                        showgrid=False,
                        tickformat=',',
                        range=[0, fraud_trend_df['total_analyzed'].max() * 1.1]
                    ),
                    hovermode="x unified",
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=14,
                        font_family="Roboto"
                    ),
                    margin=dict(l=10, r=60, t=70, b=30)
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
                    WHEN period_type = 'daily' THEN 'Daily Limit'
                    WHEN period_type = 'weekly' THEN 'Weekly Limit'
                    WHEN period_type = 'monthly' THEN 'Monthly Limit'
                    ELSE period_type
                END as violation_type,
                COUNT(*) as violation_count
            FROM violations
            GROUP BY period_type
            ORDER BY violation_count DESC
            """
            
            # Fetch data
            violations_df = fetch_time_series_data(DBS["Limit Monitoring"], query)
            
            if not violations_df.empty:
                # Calculate percentages for better visualization
                total_violations = violations_df['violation_count'].sum()
                violations_df['percentage'] = (violations_df['violation_count'] / total_violations * 100).round(1)
                violations_df['label'] = violations_df.apply(
                    lambda x: f"{x['violation_type']}: {x['violation_count']} ({x['percentage']}%)", axis=1
                )
                
                # Create enhanced pie chart with custom styling
                fig = go.Figure(data=[go.Pie(
                    labels=violations_df['violation_type'],
                    values=violations_df['violation_count'],
                    text=violations_df['percentage'].apply(lambda x: f"{x}%"),
                    textinfo='text',
                    hoverinfo='label+value+percent',
                    textfont=dict(size=14, color='white'),
                    marker=dict(
                        colors=['#2563EB', '#10B981', '#F59E0B', '#EF4444'],
                        line=dict(color='white', width=2)
                    ),
                    hole=0.5,
                    rotation=90,
                    pull=[0.05 if x == violations_df['violation_count'].max() else 0 for x in violations_df['violation_count']]
                )])
                
                # Add a title in the center
                fig.add_annotation(
                    text="Violations<br>by Type",
                    x=0.5, y=0.5,
                    font=dict(size=20, color='#1E40AF', family='Arial Black'),
                    showarrow=False
                )
                
                # Add total count in the center below the title
                fig.add_annotation(
                    text=f"Total: {total_violations}",
                    x=0.5, y=0.42,
                    font=dict(size=16, color='#64748B'),
                    showarrow=False
                )
                
                # Customize layout with enhanced styling
                fig.update_layout(
                    height=400,
                    title={
                        'text': "<b>Transaction Limit Violations Analysis</b>",
                        'y':0.95,
                        'x':0.5,
                        'xanchor': 'center',
                        'yanchor': 'top',
                        'font': {'size': 22, 'color': '#2563EB'}
                    },
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=20, r=20, t=70, b=20),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.15,
                        xanchor="center",
                        x=0.5,
                        font=dict(size=14),
                        bgcolor='rgba(255,255,255,0.8)',
                        bordercolor='rgba(230,230,230,0.9)',
                        borderwidth=1
                    ),
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=14,
                        font_family="Roboto"
                    )
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
                COUNT(DISTINCT bank_name) as bank_count,
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
                
                # Calculate insights for annotations
                total_individuals = accounts_grouped['Count of Individuals'].sum()
                multi_bank_count = accounts_grouped[accounts_grouped['Number of Banks'] > 1]['Count of Individuals'].sum()
                multi_bank_pct = (multi_bank_count / total_individuals * 100).round(1)
                
                # Add percentage column
                accounts_grouped['Percentage'] = (accounts_grouped['Count of Individuals'] / total_individuals * 100).round(1)
                
                # Create enhanced bar chart with gradient color and annotations
                fig = go.Figure()
                
                # Add bar chart
                fig.add_trace(go.Bar(
                    x=accounts_grouped['Number of Banks'],
                    y=accounts_grouped['Count of Individuals'],
                    text=accounts_grouped['Count of Individuals'],
                    textposition='auto',
                    marker=dict(
                        color=accounts_grouped['Number of Banks'],
                        colorscale=[[0, '#DBEAFE'], [0.5, '#93C5FD'], [1, '#1E40AF']],
                        line=dict(width=1, color='white')
                    ),
                    hovertemplate='<b>%{x} Banks</b><br>Individuals: %{y:,}<br>Percentage: %{customdata:.1f}%',
                    customdata=accounts_grouped['Percentage'],
                    width=0.7
                ))
                
                # Add summary annotation
                fig.add_annotation(
                    xref="paper", yref="paper",
                    x=0.95, y=0.95,
                    text=f"<b>{multi_bank_pct}%</b> of individuals<br>have multiple bank<br>accounts",
                    showarrow=False,
                    font=dict(family="Arial", size=14, color="#1E40AF"),
                    align="right",
                    bordercolor="#93C5FD",
                    borderwidth=2,
                    borderpad=6,
                    bgcolor="rgba(219, 234, 254, 0.8)",
                    opacity=0.8
                )
                
                # Customize layout with enhanced styling
                fig.update_layout(
                    height=400,
                    title={
                        'text': "<b>Multiple Account Distribution Analysis</b>",
                        'y':0.95,
                        'x':0.5,
                        'xanchor': 'center',
                        'yanchor': 'top',
                        'font': {'size': 22, 'color': '#1E40AF'}
                    },
                    xaxis=dict(
                        title=dict(
                            text='Number of Banks per Individual',
                            font=dict(size=14)
                        ),
                        showgrid=False,
                        showline=True,
                        linecolor='rgba(230,230,230,0.8)',
                        type='category',
                        tickmode='array',
                        tickvals=accounts_grouped['Number of Banks'],
                        ticktext=[f"{x} Banks" for x in accounts_grouped['Number of Banks']]
                    ),
                    yaxis=dict(
                        title=dict(
                            text='Count of Individuals',
                            font=dict(size=14)
                        ),
                        showgrid=True,
                        gridcolor='rgba(230,230,230,0.4)',
                        showline=True,
                        linecolor='rgba(230,230,230,0.8)',
                        tickformat=','
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=10, r=10, t=70, b=50),
                    hoverlabel=dict(
                        bgcolor="white",
                        font_size=14,
                        font_family="Roboto"
                    ),
                    bargap=0.15
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