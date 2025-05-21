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
st.set_page_config(page_title="📊 Financial Intelligence", layout="wide", menu_items=None)

# Check if user is logged in
is_authenticated = login_page()

# Only render dashboard if user is authenticated
if is_authenticated:
    # Render sidebar navigation
    render_sidebar()
    
    # Modern CSS styling
    st.markdown("""
    <style>
        /* Modern color palette */
        :root {
            --primary: #4361ee;
            --primary-light: #4895ef;
            --secondary: #3a0ca3;
            --success: #4cc9f0;
            --warning: #f72585;
            --danger: #7209b7;
            --light: #f8f9fa;
            --dark: #212529;
            --bg-light: #f1f3f5;
            --white: #ffffff;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.06);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.05);
            --radius: 8px;
        }
        
        /* Streamlit styling overrides */
        .block-container {
            max-width: 100% !important;
            padding-top: 1rem !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        
        /* Hide Streamlit branding */
        #MainMenu, footer, header {
            visibility: hidden;
        }
        
        /* Dashboard layout */
        .dashboard {
            padding: 0.25rem;
        }
        
        .dashboard-header {
            font-size: 1.25rem;
            font-weight: 600;
            color: var(--dark);
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }
        
        /* KPI grid */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        /* KPI card */
        .kpi-card {
            background-color: var(--white);
            border-radius: var(--radius);
            padding: 1rem;
            box-shadow: var(--shadow-sm);
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            border-top: 3px solid transparent;
        }
        
        .kpi-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        
        .kpi-primary { border-top-color: var(--primary); }
        .kpi-success { border-top-color: var(--success); }
        .kpi-warning { border-top-color: var(--warning); }
        .kpi-danger { border-top-color: var(--danger); }
        
        .kpi-title {
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: rgba(0,0,0,0.5);
            margin-bottom: 0.5rem;
        }
        
        .kpi-value {
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--dark);
            line-height: 1.2;
            margin-bottom: 0.5rem;
        }
        
        .kpi-trend {
            display: flex;
            align-items: center;
            font-size: 0.7rem;
            font-weight: 500;
        }
        
        .trend-up { color: #10b981; }
        .trend-down { color: #ef4444; }
        .trend-neutral { color: #6b7280; }
        
        /* Chart grid */
        .chart-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
        }
        
        /* Chart container */
        .chart-card {
            background-color: var(--white);
            border-radius: var(--radius);
            padding: 1rem;
            box-shadow: var(--shadow-sm);
            height: 100%;
        }
        
        .chart-header {
            font-size: 0.85rem;
            font-weight: 600;
            color: var(--dark);
            margin-bottom: 0.75rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid rgba(0,0,0,0.05);
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Dashboard container
    st.markdown('<div class="dashboard">', unsafe_allow_html=True)
    
    # Dashboard header
    st.markdown('<div class="dashboard-header">Financial Intelligence Dashboard</div>', unsafe_allow_html=True)
    
    # Fetch metrics for KPIs
    # Account metrics
    total_tx = fetch_metric(DBS["Accounts Analysis"], "SELECT COUNT(*) FROM transactions")
    total_amt = fetch_metric(DBS["Accounts Analysis"], "SELECT SUM(amount) FROM transactions")
    formatted_amount = f"${total_amt:,.2f}" if isinstance(total_amt, (int, float)) else "$0.00"
    
    # Transaction trend
    tx_current, tx_change = calculate_kpi_trend(
        DBS["Accounts Analysis"], 
        "SELECT COUNT(*) FROM transactions WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')",
        "SELECT COUNT(*) FROM transactions WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', datetime('now', '-1 month'))"
    )
    
    # Violations metrics
    violations = fetch_metric(DBS["Limit Monitoring"], "SELECT COUNT(*) FROM violations")
    
    # Violations trend
    violations_current, violations_change = calculate_kpi_trend(
        DBS["Limit Monitoring"], 
        "SELECT COUNT(*) FROM violations WHERE strftime('%Y-%W', created_at) = strftime('%Y-%W', 'now')",
        "SELECT COUNT(*) FROM violations WHERE strftime('%Y-%W', created_at) = strftime('%Y-%W', datetime('now', '-7 days'))"
    )
    
    # Fraud metrics
    frauds = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results")
    suspicious = fetch_metric(DBS["Fraud Detection"], "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1")
    
    # Fraud trend
    fraud_current, fraud_change = calculate_kpi_trend(
        DBS["Fraud Detection"], 
        "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1 AND strftime('%Y-%W', timestamp) = strftime('%Y-%W', 'now')",
        "SELECT COUNT(*) FROM fraud_detection_results WHERE predicted_suspicious = 1 AND strftime('%Y-%W', timestamp) = strftime('%Y-%W', datetime('now', '-7 days'))"
    )
    
    # Calculate fraud rate percentage
    fraud_rate = f"{(suspicious / frauds * 100):.1f}%" if frauds > 0 else "0%"
    
    # Helper function for trend indicators
    def get_trend_html(change, inverted=False):
        """Generate HTML for trend indicators"""
        if change == 0:
            # No change
            return f"""
            <div class="kpi-trend trend-neutral">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right:4px">
                    <path d="M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
                No change
            </div>
            """
        
        # Determine if trend is positive (considering inverted meaning for some metrics)
        is_positive = (change > 0 and not inverted) or (change < 0 and inverted)
        
        if is_positive:
            return f"""
            <div class="kpi-trend trend-up">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right:4px">
                    <path d="M17 13L12 8L7 13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                {abs(change):.1f}% 
            </div>
            """
        else:
            return f"""
            <div class="kpi-trend trend-down">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right:4px">
                    <path d="M7 11L12 16L17 11" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                {abs(change):.1f}%
            </div>
            """
    
    # Render KPI Grid
    st.markdown('<div class="kpi-grid">', unsafe_allow_html=True)
    
    # Transaction Volume KPI
    st.markdown(f"""
    <div class="kpi-card kpi-primary">
        <div class="kpi-title">Transaction Volume</div>
        <div class="kpi-value">{total_tx:,}</div>
        {get_trend_html(tx_change)}
    </div>
    """, unsafe_allow_html=True)
    
    # Transaction Value KPI
    st.markdown(f"""
    <div class="kpi-card kpi-success">
        <div class="kpi-title">Transaction Value</div>
        <div class="kpi-value">{formatted_amount}</div>
        <div class="kpi-trend trend-neutral">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-right:4px">
                <path d="M5 12H19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            Current total
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Limit Violations KPI
    st.markdown(f"""
    <div class="kpi-card kpi-warning">
        <div class="kpi-title">Limit Violations</div>
        <div class="kpi-value">{violations:,}</div>
        {get_trend_html(violations_change, inverted=True)}
    </div>
    """, unsafe_allow_html=True)
    
    # Fraud Rate KPI
    st.markdown(f"""
    <div class="kpi-card kpi-danger">
        <div class="kpi-title">Fraud Rate</div>
        <div class="kpi-value">{fraud_rate}</div>
        {get_trend_html(fraud_change, inverted=True)}
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Chart grid for data visualizations
    st.markdown('<div class="chart-grid">', unsafe_allow_html=True)
    
    # Chart 1: Transaction Volume by Bank
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
            # Create chart container
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="chart-header">Transaction Volume by Bank</div>', unsafe_allow_html=True)
            
            # Create bar chart
            fig = px.bar(
                tx_by_bank_df,
                x='bank_name',
                y='transaction_count',
                color_discrete_sequence=['#4361ee'],
                title=None
            )
            
            # Customize layout
            fig.update_layout(
                height=275,
                xaxis_title=None,
                yaxis_title=None,
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            
            # Display chart
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="chart-header">Transaction Volume by Bank</div>', unsafe_allow_html=True)
            st.info("No transaction data available for visualization.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Error generating transaction volume chart: {str(e)}")
    
    # Chart 2: Fraud Detection Trend
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
            # Create chart container
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="chart-header">Suspicious Transaction Rate Trend</div>', unsafe_allow_html=True)
            
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
                title=None,
                color_discrete_sequence=['#7209b7']
            )
            
            # Add area fill
            fig.add_trace(
                go.Scatter(
                    x=fraud_trend_df['date'],
                    y=fraud_trend_df['suspicious_pct'],
                    mode='none',
                    fill='tozeroy',
                    fillcolor='rgba(114, 9, 183, 0.1)',
                    name='Suspicious Rate',
                    showlegend=False
                )
            )
            
            # Customize layout
            fig.update_layout(
                height=275,
                xaxis_title=None,
                yaxis_title=None,
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
                margin=dict(l=10, r=10, t=10, b=10),
            )
            
            # Display chart
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="chart-header">Suspicious Transaction Rate Trend</div>', unsafe_allow_html=True)
            st.info("No fraud detection data available for visualization.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Error generating fraud detection trend chart: {str(e)}")
    
    # Chart 3: Violations by Type
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
            # Create chart container
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="chart-header">Limit Violations by Type</div>', unsafe_allow_html=True)
            
            # Create pie chart
            fig = px.pie(
                violations_df,
                values='violation_count',
                names='violation_type',
                title=None,
                color_discrete_sequence=['#4361ee', '#f72585', '#4cc9f0', '#3a0ca3'],
                hole=0.4
            )
            
            # Customize layout
            fig.update_layout(
                height=275,
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.15,
                    xanchor="center",
                    x=0.5
                )
            )
            
            # Display chart
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="chart-header">Limit Violations by Type</div>', unsafe_allow_html=True)
            st.info("No violation data available for visualization.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Error generating violations chart: {str(e)}")
    
    # Chart 4: Multiple Accounts Distribution
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
            # Create chart container
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="chart-header">Individuals by Number of Banks</div>', unsafe_allow_html=True)
            
            # Group by bank count
            accounts_grouped = accounts_df.groupby('bank_count')['individual_count'].sum().reset_index()
            accounts_grouped.columns = ['Number of Banks', 'Count of Individuals']
            
            # Create bar chart
            fig = px.bar(
                accounts_grouped,
                x='Number of Banks',
                y='Count of Individuals',
                color_discrete_sequence=['#4cc9f0'],
                title=None
            )
            
            # Customize layout
            fig.update_layout(
                height=275,
                xaxis_title=None,
                yaxis_title=None,
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=False, type='category'),
                yaxis=dict(gridcolor='rgba(0,0,0,0.05)'),
                margin=dict(l=10, r=10, t=10, b=10)
            )
            
            # Display chart
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="chart-card">', unsafe_allow_html=True)
            st.markdown('<div class="chart-header">Individuals by Number of Banks</div>', unsafe_allow_html=True)
            st.info("No multiple accounts data available for visualization.")
            st.markdown('</div>', unsafe_allow_html=True)
            
    except Exception as e:
        st.error(f"Error generating multiple accounts chart: {str(e)}")
    
    # Close chart grid
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Close dashboard container
    st.markdown('</div>', unsafe_allow_html=True)