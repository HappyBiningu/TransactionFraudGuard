import streamlit as st
import pandas as pd
import sqlite3
import sys
import os
import datetime
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# Add the root directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auth import require_auth
from sidebar import render_sidebar
import enhanced_financial_alerts as efa

# Constants
ALERTS_DB = "financial_alerts.db"
TABLES = [
    "daily_balance_alerts",
    "large_transaction_alerts",
    "pattern_deviation_alerts",
    "account_status_alerts"
]

# Page configuration
st.set_page_config(
    page_title="Financial Alerts",
    page_icon="🔔",
    layout="wide",
    menu_items=None
)

# Apply authentication decorator
@require_auth
def main():
    """Main function to render the Financial Alerts page"""
    # Render sidebar navigation
    render_sidebar()
    
    # Initialize database and generate alerts from real data
    efa.init_alerts_database()
    
    st.title("🔔 Financial Alerts")
    
    # Add custom CSS for enhanced appearance
    st.markdown("""
    <style>
        .enhanced-metrics {
            display: flex;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            min-width: 200px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            border-left: 4px solid #1E88E5;
            transition: transform 0.2s;
        }
        
        .metric-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .metric-card.critical {
            border-left-color: #E53935;
        }
        
        .metric-card.high {
            border-left-color: #FB8C00;
        }
        
        .metric-card.medium {
            border-left-color: #FDD835;
        }
        
        .metric-card.low {
            border-left-color: #43A047;
        }
        
        .metric-title {
            font-size: 0.9rem;
            color: #546E7A;
            margin-bottom: 5px;
        }
        
        .metric-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #263238;
            margin-bottom: 5px;
        }
        
        .metric-subtitle {
            font-size: 0.8rem;
            color: #78909C;
        }
        
        .alert-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        .refresh-btn {
            background-color: #E3F2FD;
            color: #1E88E5;
            border-radius: 20px;
            padding: 5px 15px;
            border: 1px solid #BBDEFB;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .refresh-btn:hover {
            background-color: #1E88E5;
            color: white;
        }
        
        .status-pill {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .status-new {
            background-color: #E3F2FD;
            color: #1565C0;
        }
        
        .status-investigating {
            background-color: #FFF8E1;
            color: #F57F17;
        }
        
        .status-confirmed {
            background-color: #FFEBEE;
            color: #C62828;
        }
        
        .status-resolved {
            background-color: #E8F5E9;
            color: #2E7D32;
        }
        
        .status-dismissed {
            background-color: #F5F5F5;
            color: #616161;
        }
        
        .chart-container {
            background-color: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        
        .alert-settings {
            background-color: #ECEFF1;
            border-radius: 8px;
            padding: 20px;
            margin-top: 30px;
        }
        
        .alert-settings h3 {
            margin-top: 0;
            color: #37474F;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Dashboard refresh functionality
    col1, col2 = st.columns([0.7, 0.3])
    with col1:
        st.subheader("Alert Overview")
    
    with col2:
        if st.button("🔄 Generate New Alerts", key="generate_alerts"):
            with st.spinner("Generating alerts from real transaction data..."):
                results = efa.generate_all_alerts()
                st.success(f"Generated {results['total']} new alerts from real data")
                st.rerun()
    
    # Get alert counts
    alert_counts = get_alert_counts()
    
    # Dashboard Overview Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        daily_balance_total = alert_counts['daily_balance_alerts']['total']
        new_daily_balance = alert_counts['daily_balance_alerts']['status'].get('NEW', 0)
        st.markdown(f"""
        <div class="metric-card low">
            <div class="metric-title">Balance Alerts</div>
            <div class="metric-value">{daily_balance_total}</div>
            <div class="metric-subtitle">{new_daily_balance} new alerts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        large_tx_total = alert_counts['large_transaction_alerts']['total']
        new_large_tx = alert_counts['large_transaction_alerts']['status'].get('NEW', 0)
        st.markdown(f"""
        <div class="metric-card medium">
            <div class="metric-title">Large Transaction Alerts</div>
            <div class="metric-value">{large_tx_total}</div>
            <div class="metric-subtitle">{new_large_tx} new alerts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        pattern_total = alert_counts['pattern_deviation_alerts']['total']
        new_pattern = alert_counts['pattern_deviation_alerts']['status'].get('NEW', 0)
        st.markdown(f"""
        <div class="metric-card high">
            <div class="metric-title">Pattern Deviation Alerts</div>
            <div class="metric-value">{pattern_total}</div>
            <div class="metric-subtitle">{new_pattern} new alerts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        status_total = alert_counts['account_status_alerts']['total']
        new_status = alert_counts['account_status_alerts']['status'].get('NEW', 0)
        st.markdown(f"""
        <div class="metric-card critical">
            <div class="metric-title">Status Change Alerts</div>
            <div class="metric-value">{status_total}</div>
            <div class="metric-subtitle">{new_status} new alerts</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Alert Trends Chart
    st.subheader("Alert Trends")
    
    # Create tabs for different visualizations
    viz_tabs = st.tabs(["Alert Timeline", "Alert Distribution", "Severity Analysis"])
    
    with viz_tabs[0]:
        alert_trends = get_alert_trends()
        if not alert_trends.empty:
            # Create the alert timeline chart
            fig = px.line(
                alert_trends, 
                x="date", 
                y="count",
                color="alert_type",
                color_discrete_map={
                    "daily_balance_alerts": "#43A047",
                    "large_transaction_alerts": "#FDD835",
                    "pattern_deviation_alerts": "#FB8C00",
                    "account_status_alerts": "#E53935"
                },
                title="Alert Volume Over Time",
                markers=True
            )
            
            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Number of Alerts",
                legend_title="Alert Type",
                plot_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5
                )
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No alert trend data available. Generate new alerts to see trends.")
    
    with viz_tabs[1]:
        # Get alert distribution data
        alert_distribution = get_alert_distribution()
        if not alert_distribution.empty:
            fig = px.pie(
                alert_distribution,
                values="count",
                names="alert_type",
                title="Distribution of Alerts by Type",
                color="alert_type",
                color_discrete_map={
                    "Daily Balance": "#43A047",
                    "Large Transaction": "#FDD835",
                    "Pattern Deviation": "#FB8C00",
                    "Account Status": "#E53935"
                },
                hole=0.4
            )
            
            fig.update_layout(
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.2,
                    xanchor="center",
                    x=0.5
                )
            )
            
            # Add total count in the center
            fig.add_annotation(
                text=f"Total<br>{alert_distribution['count'].sum()}",
                x=0.5, y=0.5,
                font_size=20,
                showarrow=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No alert distribution data available. Generate new alerts to see distribution.")
    
    with viz_tabs[2]:
        # Get severity distribution for pattern deviation alerts
        severity_data = get_severity_distribution()
        if not severity_data.empty:
            fig = px.bar(
                severity_data,
                x="severity",
                y="count",
                title="Pattern Deviation Alerts by Severity",
                color="severity",
                color_discrete_map={
                    "LOW": "#43A047",
                    "MEDIUM": "#FDD835",
                    "HIGH": "#FB8C00",
                    "CRITICAL": "#E53935"
                },
                text="count"
            )
            
            fig.update_layout(
                xaxis_title="Severity Level",
                yaxis_title="Number of Alerts",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No severity data available. Generate new pattern deviation alerts to see severity distribution.")
    
    # Alert Management Section
    st.subheader("Alert Management")
    
    # Create alert type selection
    alert_type_mapping = {
        "Balance Alerts": "daily_balance_alerts",
        "Large Transaction Alerts": "large_transaction_alerts",
        "Pattern Deviation Alerts": "pattern_deviation_alerts",
        "Status Change Alerts": "account_status_alerts"
    }
    
    selected_alert_type = st.selectbox(
        "Select Alert Type",
        options=list(alert_type_mapping.keys())
    )
    
    db_table = alert_type_mapping[selected_alert_type]
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_options = ["All", "NEW", "REVIEWING", "INVESTIGATING", "RESOLVED", 
                          "CLOSED", "CONFIRMED", "FALSE_ALARM", "UNDER_REVIEW", "DISMISSED", "NOTIFIED", "ACKNOWLEDGED"]
        status_filter = st.selectbox("Filter by Status", status_options)
    
    with col2:
        default_start_date = datetime.now() - timedelta(days=30)
        default_end_date = datetime.now()
        date_range = st.date_input(
            "Date Range",
            value=[default_start_date.date(), default_end_date.date()],
            max_value=datetime.now().date()
        )
    
    with col3:
        limit = st.number_input("Limit Results", min_value=10, max_value=1000, value=100, step=10)
        
        st.write("")  # Spacer
        if st.button("Export to CSV", key="export_button"):
            df = get_alerts_by_type(db_table, 
                                  status_filter if status_filter != "All" else None, 
                                  date_range, 
                                  limit)
            if not df.empty:
                csv_data = export_to_csv(df, f"{db_table}_export.csv")
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"{db_table}_export_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No data available to export.")
    
    # Display alerts
    df = get_alerts_by_type(db_table, status_filter if status_filter != "All" else None, date_range, limit)
    
    if not df.empty:
        # Prepare DataFrame for display
        df_display = df.copy()
        
        # Format amount and threshold columns if they exist
        if 'amount' in df_display.columns:
            df_display['amount'] = df_display['amount'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
        if 'threshold' in df_display.columns:
            df_display['threshold'] = df_display['threshold'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
        if 'current_balance' in df_display.columns:
            df_display['current_balance'] = df_display['current_balance'].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
        
        # Format timestamp
        if 'timestamp' in df_display.columns:
            df_display['timestamp'] = pd.to_datetime(df_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Rename columns for better display
        column_map = {col: col.replace('_', ' ').title() for col in df_display.columns}
        df_display = df_display.rename(columns=column_map)
        
        # Show the table
        st.dataframe(df_display, use_container_width=True)
        
        # Interactive Alert Management
        st.subheader("Update Alert Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Select an alert to update
            selected_alert_id = st.selectbox(
                "Select Alert by ID",
                options=df['id'].tolist(),
                format_func=lambda x: f"Alert #{x}"
            )
        
        with col2:
            # Choose new status
            new_status = st.selectbox(
                "New Status",
                options=["REVIEWING", "INVESTIGATING", "UNDER_REVIEW", "RESOLVED", "CLOSED", 
                         "CONFIRMED", "FALSE_ALARM", "DISMISSED", "NOTIFIED", "ACKNOWLEDGED"]
            )
        
        # Update button
        if st.button("Update Status", key="update_status_button"):
            success = update_alert_status(db_table, selected_alert_id, new_status)
            if success:
                st.success(f"Alert #{selected_alert_id} status updated to {new_status}")
                # Refresh display
                st.rerun()
            else:
                st.error("Failed to update alert status")
    else:
        st.info("No alerts found matching your criteria.")
    
    # Alert Settings Section
    with st.expander("Alert Settings", expanded=False):
        st.subheader("Alert Thresholds")
        
        # Get current settings
        settings = get_alert_settings()
        
        col1, col2 = st.columns(2)
        
        with col1:
            large_tx_threshold = st.number_input(
                "Large Transaction Threshold ($)",
                min_value=1000.0,
                max_value=100000.0,
                value=float(settings.get('large_transaction', 10000.0)),
                step=1000.0,
                format="%.2f"
            )
            
            daily_balance_threshold = st.number_input(
                "Low Balance Threshold ($)",
                min_value=100.0,
                max_value=10000.0,
                value=float(settings.get('daily_balance', 1000.0)),
                step=100.0,
                format="%.2f"
            )
        
        with col2:
            pattern_deviation_threshold = st.slider(
                "Pattern Deviation Sensitivity",
                min_value=0.1,
                max_value=1.0,
                value=float(settings.get('pattern_deviation', 0.8)),
                step=0.1,
                format="%.1f",
                help="Higher values mean higher sensitivity (more alerts)"
            )
            
            account_status_threshold = st.slider(
                "Account Status Change Sensitivity",
                min_value=0.1,
                max_value=1.0,
                value=float(settings.get('account_status', 1.0)),
                step=0.1,
                format="%.1f",
                help="Higher values mean higher sensitivity (more alerts)"
            )
        
        if st.button("Save Settings", key="save_settings"):
            new_settings = {
                'large_transaction': large_tx_threshold,
                'daily_balance': daily_balance_threshold,
                'pattern_deviation': pattern_deviation_threshold,
                'account_status': account_status_threshold
            }
            
            if update_alert_settings(new_settings):
                st.success("Alert settings updated successfully")
            else:
                st.error("Failed to update alert settings")

def get_alert_counts():
    """Get counts of alerts by type and status"""
    conn = sqlite3.connect(ALERTS_DB)
    
    result = {}
    for table in TABLES:
        # Get total count
        query = f"SELECT COUNT(*) FROM {table}"
        total = pd.read_sql_query(query, conn).iloc[0, 0]
        
        # Get count by status
        query = f"SELECT status, COUNT(*) as count FROM {table} GROUP BY status"
        status_counts = pd.read_sql_query(query, conn)
        
        status_dict = {}
        for _, row in status_counts.iterrows():
            status_dict[row['status']] = row['count']
        
        result[table] = {
            'total': total,
            'status': status_dict
        }
    
    conn.close()
    return result

def get_alert_trends():
    """Get trend data for alerts over time"""
    conn = sqlite3.connect(ALERTS_DB)
    
    # Create empty dataframe to store results
    result_df = pd.DataFrame()
    
    for table in TABLES:
        # Get counts by date
        query = f"""
        SELECT 
            date(timestamp) as date, 
            COUNT(*) as count,
            '{table}' as alert_type
        FROM {table}
        WHERE timestamp >= date('now', '-30 day')
        GROUP BY date(timestamp)
        ORDER BY date(timestamp)
        """
        
        df = pd.read_sql_query(query, conn)
        result_df = pd.concat([result_df, df], ignore_index=True)
    
    conn.close()
    
    # Convert date to datetime
    if not result_df.empty:
        result_df['date'] = pd.to_datetime(result_df['date'])
    
    return result_df

def get_alert_distribution():
    """Get distribution of alerts by type"""
    conn = sqlite3.connect(ALERTS_DB)
    
    result_data = []
    for table in TABLES:
        # Get count
        query = f"SELECT COUNT(*) as count FROM {table}"
        count = pd.read_sql_query(query, conn).iloc[0, 0]
        
        # Map table name to friendly name
        alert_type_map = {
            "daily_balance_alerts": "Daily Balance",
            "large_transaction_alerts": "Large Transaction",
            "pattern_deviation_alerts": "Pattern Deviation",
            "account_status_alerts": "Account Status"
        }
        
        result_data.append({
            "alert_type": alert_type_map.get(table, table),
            "count": count
        })
    
    conn.close()
    return pd.DataFrame(result_data)

def get_severity_distribution():
    """Get distribution of pattern deviation alerts by severity"""
    conn = sqlite3.connect(ALERTS_DB)
    
    query = """
    SELECT 
        severity, 
        COUNT(*) as count
    FROM pattern_deviation_alerts
    GROUP BY severity
    ORDER BY CASE 
        WHEN severity = 'CRITICAL' THEN 1
        WHEN severity = 'HIGH' THEN 2
        WHEN severity = 'MEDIUM' THEN 3
        WHEN severity = 'LOW' THEN 4
        ELSE 5
    END
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    return df

def get_alerts_by_type(table_name, status=None, date_range=None, limit=100):
    """Get alerts by type with optional filters"""
    conn = sqlite3.connect(ALERTS_DB)
    
    # Start building the query
    query = f"SELECT * FROM {table_name} WHERE 1=1"
    params = []
    
    # Add status filter if provided
    if status:
        query += " AND status = ?"
        params.append(status)
    
    # Add date range filter if provided
    if date_range and len(date_range) == 2:
        start_date = date_range[0].strftime('%Y-%m-%d')
        end_date = (date_range[1] + timedelta(days=1)).strftime('%Y-%m-%d')  # Add 1 day to include end date
        
        query += " AND date(timestamp) BETWEEN ? AND ?"
        params.append(start_date)
        params.append(end_date)
    
    # Add ordering and limit
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    # Execute query
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df

def update_alert_status(table_name, alert_id, new_status):
    """Update the status of an alert"""
    try:
        conn = sqlite3.connect(ALERTS_DB)
        cursor = conn.cursor()
        
        # Update the status
        cursor.execute(
            f"UPDATE {table_name} SET status = ? WHERE id = ?",
            (new_status, alert_id)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating alert status: {e}")
        return False

def get_alert_settings():
    """Get alert threshold settings"""
    conn = sqlite3.connect(ALERTS_DB)
    
    query = "SELECT alert_type, threshold_value FROM alert_settings"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert to dictionary
    settings = {}
    for _, row in df.iterrows():
        settings[row['alert_type']] = row['threshold_value']
    
    return settings

def update_alert_settings(settings):
    """Update alert threshold settings"""
    try:
        conn = sqlite3.connect(ALERTS_DB)
        cursor = conn.cursor()
        
        # Update each setting
        for alert_type, threshold in settings.items():
            cursor.execute(
                "UPDATE alert_settings SET threshold_value = ?, last_updated = ? WHERE alert_type = ?",
                (threshold, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), alert_type)
            )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error updating settings: {e}")
        return False

def export_to_csv(df, filename):
    """Export DataFrame to CSV"""
    csv = df.to_csv(index=False)
    return csv

if __name__ == "__main__":
    main()