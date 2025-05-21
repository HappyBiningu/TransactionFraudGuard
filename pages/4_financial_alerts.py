import streamlit as st
import pandas as pd
import sqlite3
import sys
import os
import datetime
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import io

# Add the root directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auth import require_auth
from sidebar import render_sidebar

# Constants
DB_FILE = "financial_alerts.db"
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
    layout="wide"
)

# Render sidebar navigation
render_sidebar()

# Initialize the database
def init_database():
    """Initialize the database with necessary tables if they don't exist"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_balance_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        account_id TEXT,
        alert_type TEXT,
        amount REAL,
        threshold REAL,
        status TEXT,
        description TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS large_transaction_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        account_id TEXT,
        transaction_id TEXT,
        amount REAL,
        threshold REAL,
        status TEXT,
        description TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS pattern_deviation_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        account_id TEXT,
        deviation_type TEXT,
        severity TEXT,
        status TEXT,
        description TEXT
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS account_status_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        account_id TEXT,
        previous_status TEXT,
        new_status TEXT,
        reason TEXT,
        status TEXT,
        description TEXT
    )
    ''')
    
    # Create test data if the tables are empty
    for table in TABLES:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        if count == 0:
            generate_test_data(conn, table)
    
    conn.commit()
    conn.close()

def generate_test_data(conn, table_name):
    """Generate test data for the specified table"""
    cursor = conn.cursor()
    
    # Generate 20-50 records per table
    num_records = random.randint(20, 50)
    
    if table_name == "daily_balance_alerts":
        for _ in range(num_records):
            # Generate a random date within the last 90 days
            days_ago = random.randint(0, 90)
            alert_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
            
            account_id = f"ACC-{random.randint(10000, 99999)}"
            alert_type = random.choice(["LOW_BALANCE", "BALANCE_DECLINE", "UNUSUAL_DEPOSIT"])
            amount = round(random.uniform(100, 10000), 2)
            threshold = round(random.uniform(100, 5000), 2)
            status = random.choice(["NEW", "REVIEWING", "RESOLVED", "CLOSED"])
            
            if alert_type == "LOW_BALANCE":
                description = f"Account balance ${amount:.2f} below threshold ${threshold:.2f}"
            elif alert_type == "BALANCE_DECLINE":
                description = f"Account balance declined by ${amount:.2f} in last 24 hours"
            else:
                description = f"Unusual deposit of ${amount:.2f} detected"
                
            cursor.execute('''
            INSERT INTO daily_balance_alerts (timestamp, account_id, alert_type, amount, threshold, status, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (alert_date, account_id, alert_type, amount, threshold, status, description))
            
    elif table_name == "large_transaction_alerts":
        for _ in range(num_records):
            days_ago = random.randint(0, 90)
            alert_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
            
            account_id = f"ACC-{random.randint(10000, 99999)}"
            transaction_id = f"TXN-{random.randint(100000, 999999)}"
            amount = round(random.uniform(5000, 50000), 2)
            threshold = round(random.uniform(5000, 20000), 2)
            status = random.choice(["NEW", "INVESTIGATING", "CONFIRMED", "FALSE_ALARM"])
            description = f"Large transaction of ${amount:.2f} exceeds threshold of ${threshold:.2f}"
                
            cursor.execute('''
            INSERT INTO large_transaction_alerts (timestamp, account_id, transaction_id, amount, threshold, status, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (alert_date, account_id, transaction_id, amount, threshold, status, description))
            
    elif table_name == "pattern_deviation_alerts":
        for _ in range(num_records):
            days_ago = random.randint(0, 90)
            alert_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
            
            account_id = f"ACC-{random.randint(10000, 99999)}"
            deviation_type = random.choice(["SPENDING_PATTERN", "LOCATION", "TIME_OF_DAY", "FREQUENCY"])
            severity = random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
            status = random.choice(["NEW", "UNDER_REVIEW", "CONFIRMED", "DISMISSED"])
            
            if deviation_type == "SPENDING_PATTERN":
                description = "Unusual spending pattern detected across multiple categories"
            elif deviation_type == "LOCATION":
                description = "Transactions from unusual geographic locations"
            elif deviation_type == "TIME_OF_DAY":
                description = "Transactions occurring at unusual times"
            else:
                description = "Unusual frequency of transactions"
                
            cursor.execute('''
            INSERT INTO pattern_deviation_alerts (timestamp, account_id, deviation_type, severity, status, description)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert_date, account_id, deviation_type, severity, status, description))
            
    elif table_name == "account_status_alerts":
        for _ in range(num_records):
            days_ago = random.randint(0, 90)
            alert_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d %H:%M:%S')
            
            account_id = f"ACC-{random.randint(10000, 99999)}"
            previous_status = random.choice(["ACTIVE", "DORMANT", "RESTRICTED", "ON_HOLD"])
            
            # Ensure new status is different
            statuses = ["ACTIVE", "DORMANT", "RESTRICTED", "ON_HOLD", "CLOSED"]
            statuses.remove(previous_status)
            new_status = random.choice(statuses)
            
            reasons = {
                "ACTIVE": ["Customer request", "Hold period expired", "Restrictions lifted"],
                "DORMANT": ["Inactivity", "Low balance", "Automatic system flag"],
                "RESTRICTED": ["Suspicious activity", "Legal order", "Bank policy violation"],
                "ON_HOLD": ["Pending investigation", "Temporary freeze", "Account verification"],
                "CLOSED": ["Customer request", "Bank decision", "Account merger"]
            }
            
            reason = random.choice(reasons.get(new_status, ["System update"]))
            status = random.choice(["NEW", "NOTIFIED", "ACKNOWLEDGED", "RESOLVED"])
            description = f"Account status changed from {previous_status} to {new_status} due to: {reason}"
                
            cursor.execute('''
            INSERT INTO account_status_alerts (timestamp, account_id, previous_status, new_status, reason, status, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (alert_date, account_id, previous_status, new_status, reason, status, description))

def get_alerts_by_type(alert_type, status_filter=None, date_range=None, limit=100):
    """Get alerts from database by type with optional filters"""
    conn = sqlite3.connect(DB_FILE)
    
    # Build the query with dynamic filtering
    query = f"SELECT * FROM {alert_type}"
    params = []
    
    # Apply filters
    conditions = []
    
    if status_filter and status_filter.lower() != "all":
        conditions.append("status = ?")
        params.append(status_filter)
    
    if date_range:
        if isinstance(date_range, list) and len(date_range) == 2:
            start_date, end_date = date_range
            if start_date and end_date:
                # Format dates for SQLite
                start_date_str = start_date.strftime('%Y-%m-%d')
                # Add one day to end_date to include the full day
                end_date_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
                
                conditions.append("timestamp BETWEEN ? AND ?")
                params.extend([start_date_str, end_date_str])
    
    # Add WHERE clause if we have any conditions
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    # Add limit and order
    query += f" ORDER BY timestamp DESC LIMIT {limit}"
    
    # Execute the query
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    return df

def update_alert_status(table, alert_id, new_status):
    """Update the status of an alert"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute(
        f"UPDATE {table} SET status = ? WHERE id = ?",
        (new_status, alert_id)
    )
    
    conn.commit()
    conn.close()
    return True

def get_alert_counts():
    """Get counts of alerts by type and status"""
    conn = sqlite3.connect(DB_FILE)
    result = {}
    
    # Get counts for each table
    for table in TABLES:
        cursor = conn.cursor()
        # Total count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        total = cursor.fetchone()[0]
        
        # Count by status
        cursor.execute(f"SELECT status, COUNT(*) FROM {table} GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        result[table] = {
            'total': total,
            'status': status_counts
        }
    
    conn.close()
    return result

def export_to_csv(df, filename):
    """Export dataframe to CSV"""
    csv = df.to_csv(index=False)
    return csv.encode('utf-8')

@require_auth
def main():
    """Main function to render the Financial Alerts page"""
    # Render sidebar navigation
    render_sidebar()
    
    # Initialize database
    init_database()
    
    st.title("🔔 Financial Alerts")
    
    # Get alert counts
    alert_counts = get_alert_counts()
    
    # Dashboard Overview Cards
    st.subheader("Alert Overview")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        daily_balance_total = alert_counts['daily_balance_alerts']['total']
        new_daily_balance = alert_counts['daily_balance_alerts']['status'].get('NEW', 0)
        st.metric(
            label="Balance Alerts", 
            value=daily_balance_total,
            delta=f"{new_daily_balance} new"
        )
    
    with col2:
        large_tx_total = alert_counts['large_transaction_alerts']['total']
        new_large_tx = alert_counts['large_transaction_alerts']['status'].get('NEW', 0)
        st.metric(
            label="Large Transaction Alerts", 
            value=large_tx_total,
            delta=f"{new_large_tx} new"
        )
    
    with col3:
        pattern_total = alert_counts['pattern_deviation_alerts']['total']
        new_pattern = alert_counts['pattern_deviation_alerts']['status'].get('NEW', 0)
        st.metric(
            label="Pattern Deviation Alerts", 
            value=pattern_total,
            delta=f"{new_pattern} new"
        )
    
    with col4:
        status_total = alert_counts['account_status_alerts']['total']
        new_status = alert_counts['account_status_alerts']['status'].get('NEW', 0)
        st.metric(
            label="Status Change Alerts", 
            value=status_total,
            delta=f"{new_status} new"
        )
    
    # Alerts by Status Chart
    st.subheader("Alerts by Status")
    
    # Prepare data for the chart
    statuses = set()
    chart_data = []
    
    for table, data in alert_counts.items():
        # Convert table name to display name
        display_name = " ".join(table.split('_')[:-1]).title()
        
        for status, count in data['status'].items():
            statuses.add(status)
            chart_data.append({
                'Alert Type': display_name,
                'Status': status,
                'Count': count
            })
    
    if chart_data:
        chart_df = pd.DataFrame(chart_data)
        
        # Create a grouped bar chart
        fig = px.bar(
            chart_df, 
            x='Alert Type', 
            y='Count', 
            color='Status',
            title='Alert Distribution by Status',
            barmode='group'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No alert data available for visualization.")
    
    # Alert Management Section
    st.markdown("---")
    st.subheader("Alert Management")
    
    # Select alert type
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
                csv_data = export_to_csv(df, f"{db_table}.csv")
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name=f"{db_table}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.error("No data to export.")
    
    # Get filtered alerts
    df = get_alerts_by_type(db_table, 
                          status_filter if status_filter != "All" else None, 
                          date_range, 
                          limit)
    
    if not df.empty:
        # Process dataframe for display
        status_colors = {
            "NEW": "🔴 New",
            "REVIEWING": "🟠 Reviewing",
            "INVESTIGATING": "🟠 Investigating",
            "UNDER_REVIEW": "🟠 Under Review",
            "RESOLVED": "🟢 Resolved",
            "CLOSED": "⚪ Closed",
            "CONFIRMED": "🟡 Confirmed",
            "FALSE_ALARM": "⚪ False Alarm",
            "DISMISSED": "⚪ Dismissed",
            "NOTIFIED": "🟡 Notified",
            "ACKNOWLEDGED": "🟢 Acknowledged"
        }
        
        # Replace status codes with colored text
        df_display = df.copy()
        df_display['status'] = df_display['status'].map(lambda x: status_colors.get(x, x))
        
        # Format timestamp
        df_display['timestamp'] = pd.to_datetime(df_display['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
        
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
        st.info("No alerts found with the selected filters.")

if __name__ == "__main__":
    main()