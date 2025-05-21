import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

# Constants
DB_FILE = "financial_alerts.db"
ALERTS_TABLE = "alerts"
ALERT_TYPES_TABLE = "alert_types"
ALERT_RULES_TABLE = "alert_rules"
ALERT_ACTIONS_TABLE = "alert_actions"
PAGE_SIZE = 20

# Page configuration
st.set_page_config(
    page_title="Financial Alerts",
    page_icon="🚨",
    layout="wide"
)

# Database helper functions
def get_db_connection():
    """Create a database connection to the SQLite database"""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # Enable row factory for named columns
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {e}")
        st.error(f"Error connecting to database: {e}")
        return None

def check_database_exists():
    """Check if the alerts database exists"""
    return os.path.exists(DB_FILE)

def get_alert_counts_by_type():
    """Get alert counts grouped by type"""
    conn = get_db_connection()
    if conn:
        try:
            query = """
                SELECT alert_type, COUNT(*) as count
                FROM alerts
                GROUP BY alert_type
                ORDER BY count DESC
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting alert counts by type: {e}")
            st.error(f"Error getting alert counts by type: {e}")
            conn.close()
    return pd.DataFrame(columns=['alert_type', 'count'])

def get_alert_counts_by_severity():
    """Get alert counts grouped by severity"""
    conn = get_db_connection()
    if conn:
        try:
            query = """
                SELECT severity, COUNT(*) as count
                FROM alerts
                GROUP BY severity
                ORDER BY CASE 
                    WHEN severity = 'critical' THEN 1 
                    WHEN severity = 'high' THEN 2 
                    WHEN severity = 'medium' THEN 3 
                    WHEN severity = 'low' THEN 4 
                END
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting alert counts by severity: {e}")
            st.error(f"Error getting alert counts by severity: {e}")
            conn.close()
    return pd.DataFrame(columns=['severity', 'count'])

def get_alert_counts_by_status():
    """Get alert counts grouped by status"""
    conn = get_db_connection()
    if conn:
        try:
            query = """
                SELECT status, COUNT(*) as count
                FROM alerts
                GROUP BY status
                ORDER BY CASE 
                    WHEN status = 'new' THEN 1 
                    WHEN status = 'in_progress' THEN 2 
                    WHEN status = 'resolved' THEN 3 
                    WHEN status = 'false_positive' THEN 4 
                END
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting alert counts by status: {e}")
            st.error(f"Error getting alert counts by status: {e}")
            conn.close()
    return pd.DataFrame(columns=['status', 'count'])

def get_alerts_over_time():
    """Get alert counts over time"""
    conn = get_db_connection()
    if conn:
        try:
            query = """
                SELECT date(created_at) as alert_date, COUNT(*) as count
                FROM alerts
                GROUP BY date(created_at)
                ORDER BY date(created_at)
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting alerts over time: {e}")
            st.error(f"Error getting alerts over time: {e}")
            conn.close()
    return pd.DataFrame(columns=['alert_date', 'count'])

def get_alert_rules():
    """Get all alert rules"""
    conn = get_db_connection()
    if conn:
        try:
            query = """
                SELECT r.id, r.rule_name, r.alert_type, r.description, r.rule_criteria, 
                       r.enabled, r.created_at, t.default_severity
                FROM alert_rules r
                JOIN alert_types t ON r.alert_type = t.type_name
                ORDER BY r.id
            """
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            logger.error(f"Error getting alert rules: {e}")
            st.error(f"Error getting alert rules: {e}")
            conn.close()
    return pd.DataFrame()

def get_paginated_alerts(page, status_filter=None, severity_filter=None, days_back=None):
    """Get a page of alerts with optional filters"""
    conn = get_db_connection()
    if conn:
        try:
            query = f"SELECT * FROM {ALERTS_TABLE}"
            params = []
            where_clauses = []
            
            # Apply filters
            if status_filter:
                where_clauses.append("status = ?")
                params.append(status_filter)
            
            if severity_filter:
                where_clauses.append("severity = ?")
                params.append(severity_filter)
            
            if days_back:
                cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                where_clauses.append("date(created_at) >= ?")
                params.append(cutoff_date)
            
            # Combine all WHERE clauses
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            # Get total count for pagination
            count_query = f"SELECT COUNT(*) as count FROM ({query})"
            count_result = conn.execute(count_query, params).fetchone()
            total_records = count_result['count'] if count_result else 0
            total_pages = (total_records + PAGE_SIZE - 1) // PAGE_SIZE if total_records > 0 else 1
            
            # Add pagination and ordering
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([PAGE_SIZE, page * PAGE_SIZE])
            
            # Execute query
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            return df, total_pages, total_records
        except Exception as e:
            logger.error(f"Error getting paginated alerts: {e}")
            st.error(f"Error getting paginated alerts: {e}")
            if conn:
                conn.close()
    return pd.DataFrame(), 0, 0

def get_alert_details(alert_id):
    """Get detailed information about a specific alert"""
    conn = get_db_connection()
    if conn:
        try:
            # Get alert details
            alert_query = f"SELECT * FROM {ALERTS_TABLE} WHERE id = ?"
            alert = conn.execute(alert_query, (alert_id,)).fetchone()
            
            if not alert:
                conn.close()
                return None, None
            
            # Get actions for this alert
            actions_query = f"""
                SELECT * FROM {ALERT_ACTIONS_TABLE} 
                WHERE alert_id = ? 
                ORDER BY performed_at DESC
            """
            actions_df = pd.read_sql_query(actions_query, conn, params=(alert_id,))
            
            conn.close()
            return dict(alert), actions_df
        except Exception as e:
            logger.error(f"Error getting alert details: {e}")
            st.error(f"Error getting alert details: {e}")
            if conn:
                conn.close()
    return None, None

def update_alert_status(alert_id, new_status, performed_by, action_details):
    """Update the status of an alert and add an action record"""
    conn = get_db_connection()
    if conn:
        try:
            # Update alert status
            update_query = f"""
                UPDATE {ALERTS_TABLE} 
                SET status = ?, updated_at = CURRENT_TIMESTAMP, assigned_to = ?
                WHERE id = ?
            """
            conn.execute(update_query, (new_status, performed_by, alert_id))
            
            # Add action record
            action_type = 'status_change'
            action_query = f"""
                INSERT INTO {ALERT_ACTIONS_TABLE} (
                    alert_id, action_type, action_details, performed_by
                ) VALUES (?, ?, ?, ?)
            """
            conn.execute(action_query, (alert_id, action_type, action_details, performed_by))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error updating alert status: {e}")
            st.error(f"Error updating alert status: {e}")
            if conn:
                conn.rollback()
                conn.close()
    return False

def add_alert_action(alert_id, action_type, action_details, performed_by):
    """Add a new action record for an alert"""
    conn = get_db_connection()
    if conn:
        try:
            query = f"""
                INSERT INTO {ALERT_ACTIONS_TABLE} (
                    alert_id, action_type, action_details, performed_by
                ) VALUES (?, ?, ?, ?)
            """
            conn.execute(query, (alert_id, action_type, action_details, performed_by))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error adding alert action: {e}")
            st.error(f"Error adding alert action: {e}")
            if conn:
                conn.rollback()
                conn.close()
    return False

# UI Components
def render_alert_dashboard():
    """Render the dashboard view with alert statistics"""
    st.subheader("📊 Alert Statistics")
    
    # Get alert statistics
    alerts_by_type = get_alert_counts_by_type()
    alerts_by_severity = get_alert_counts_by_severity()
    alerts_by_status = get_alert_counts_by_status()
    alerts_over_time = get_alerts_over_time()
    
    # Convert alert_date to datetime for better plotting
    if not alerts_over_time.empty:
        alerts_over_time['alert_date'] = pd.to_datetime(alerts_over_time['alert_date'])
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Alert types pie chart
        if not alerts_by_type.empty:
            fig_type = px.pie(
                alerts_by_type, 
                values='count', 
                names='alert_type', 
                title='Alerts by Type',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_type.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_type, use_container_width=True)
        else:
            st.info("No alert type data available")
        
        # Alerts over time line chart
        if not alerts_over_time.empty:
            fig_time = px.line(
                alerts_over_time, 
                x='alert_date', 
                y='count',
                title='Alerts Over Time',
                markers=True
            )
            fig_time.update_layout(xaxis_title="Date", yaxis_title="Number of Alerts")
            st.plotly_chart(fig_time, use_container_width=True)
        else:
            st.info("No time series data available")
    
    with col2:
        # Alert severity bar chart
        if not alerts_by_severity.empty:
            # Define custom color mapping for severity
            severity_colors = {
                'low': 'green',
                'medium': 'orange',
                'high': 'red',
                'critical': 'darkred'
            }
            
            fig_severity = px.bar(
                alerts_by_severity,
                x='severity',
                y='count',
                title='Alerts by Severity',
                color='severity',
                color_discrete_map=severity_colors
            )
            fig_severity.update_layout(xaxis_title="Severity", yaxis_title="Number of Alerts")
            st.plotly_chart(fig_severity, use_container_width=True)
        else:
            st.info("No severity data available")
        
        # Alert status bar chart
        if not alerts_by_status.empty:
            # Define custom color mapping for status
            status_colors = {
                'new': 'blue',
                'in_progress': 'orange',
                'resolved': 'green',
                'false_positive': 'gray'
            }
            
            fig_status = px.bar(
                alerts_by_status,
                x='status',
                y='count',
                title='Alerts by Status',
                color='status',
                color_discrete_map=status_colors
            )
            fig_status.update_layout(xaxis_title="Status", yaxis_title="Number of Alerts")
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("No status data available")

def render_alert_list():
    """Render the alert list with filters"""
    st.subheader("🔍 Alert List")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox(
            "Status",
            options=[None, "new", "in_progress", "resolved", "false_positive"],
            format_func=lambda x: "All" if x is None else x.replace('_', ' ').title()
        )
    
    with col2:
        severity_filter = st.selectbox(
            "Severity",
            options=[None, "low", "medium", "high", "critical"],
            format_func=lambda x: "All" if x is None else x.title()
        )
    
    with col3:
        days_back = st.selectbox(
            "Time Period",
            options=[None, 7, 14, 30, 90],
            format_func=lambda x: "All Time" if x is None else f"Last {x} days"
        )
    
    with col4:
        refresh = st.button("Refresh Data")
    
    # Get paginated data
    # Initialize page number in session state if not present
    if 'alert_page' not in st.session_state:
        st.session_state.alert_page = 0
    
    alerts_df, total_pages, total_records = get_paginated_alerts(
        st.session_state.alert_page,
        status_filter,
        severity_filter,
        days_back
    )
    
    # Display results
    if not alerts_df.empty:
        # Format the dataframe for display
        display_df = alerts_df.copy()
        
        # Convert timestamps to more readable format
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
        display_df['updated_at'] = pd.to_datetime(display_df['updated_at']).dt.strftime('%Y-%m-%d %H:%M')
        
        # Select columns to display
        display_df = display_df[['id', 'alert_type', 'severity', 'status', 'description', 'created_at']]
        
        # Rename columns for better display
        display_df.columns = ['ID', 'Alert Type', 'Severity', 'Status', 'Description', 'Created At']
        
        # Apply custom styling
        def highlight_severity(val):
            if val == 'critical':
                return 'background-color: #ffcccc; font-weight: bold'
            elif val == 'high':
                return 'background-color: #ffe6cc'
            elif val == 'medium':
                return 'background-color: #ffffcc'
            return ''
        
        def highlight_status(val):
            if val == 'new':
                return 'background-color: #cce5ff'
            elif val == 'in_progress':
                return 'background-color: #fff2cc'
            elif val == 'resolved':
                return 'background-color: #d9ead3'
            return ''
        
        # Display dataframe
        st.dataframe(display_df, use_container_width=True)
        
        # Pagination controls
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.session_state.alert_page > 0:
                if st.button("Previous Page"):
                    st.session_state.alert_page -= 1
                    st.rerun()
        
        with col2:
            st.write(f"Page {st.session_state.alert_page + 1} of {total_pages} (Total Records: {total_records})")
        
        with col3:
            if st.session_state.alert_page < total_pages - 1:
                if st.button("Next Page"):
                    st.session_state.alert_page += 1
                    st.rerun()
        
        # Alert details section
        st.subheader("📋 Alert Details")
        
        alert_id = st.number_input("Enter Alert ID for details", min_value=1, step=1)
        if st.button("View Details"):
            alert, actions = get_alert_details(alert_id)
            
            if alert:
                # Display alert information
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Alert Information**")
                    st.write(f"**ID:** {alert['id']}")
                    st.write(f"**Type:** {alert['alert_type']}")
                    st.write(f"**Description:** {alert['description']}")
                    st.write(f"**Status:** {alert['status']}")
                    st.write(f"**Severity:** {alert['severity']}")
                    st.write(f"**Individual ID:** {alert['individual_id']}")
                    st.write(f"**Account ID:** {alert['account_id']}")
                    
                with col2:
                    st.write("**Timeline**")
                    st.write(f"**Created:** {alert['created_at']}")
                    st.write(f"**Updated:** {alert['updated_at'] or 'Never'}")
                    st.write(f"**Assigned To:** {alert['assigned_to'] or 'Unassigned'}")
                    
                    # Add action options if alert is not resolved
                    if alert['status'] not in ['resolved', 'false_positive']:
                        st.write("**Actions**")
                        
                        new_status = st.selectbox(
                            "Change Status",
                            options=["in_progress", "resolved", "false_positive"],
                            format_func=lambda x: x.replace('_', ' ').title()
                        )
                        
                        performed_by = st.text_input("Your Name/ID")
                        action_details = st.text_area("Action Details/Notes")
                        
                        if st.button("Update Alert"):
                            if performed_by and action_details:
                                success = update_alert_status(
                                    alert_id, 
                                    new_status, 
                                    performed_by, 
                                    action_details
                                )
                                if success:
                                    st.success("Alert updated successfully!")
                                    st.rerun()
                            else:
                                st.error("Please fill in all fields")
                
                # Display action history
                if not actions.empty:
                    st.write("**Action History**")
                    
                    # Format action history for display
                    actions['performed_at'] = pd.to_datetime(actions['performed_at']).dt.strftime('%Y-%m-%d %H:%M')
                    actions = actions[['action_type', 'action_details', 'performed_by', 'performed_at']]
                    actions.columns = ['Action Type', 'Details', 'Performed By', 'Timestamp']
                    
                    st.dataframe(actions, use_container_width=True)
                else:
                    st.write("No actions recorded for this alert.")
            else:
                st.error(f"Alert with ID {alert_id} not found")
    else:
        st.info("No alerts found matching the selected criteria")

def render_alert_rules():
    """Render the alert rules page"""
    st.subheader("⚙️ Alert Rules")
    
    rules_df = get_alert_rules()
    
    if not rules_df.empty:
        # Format for display
        display_df = rules_df.copy()
        
        # Convert timestamp
        display_df['created_at'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d')
        
        # Format enabled column
        display_df['enabled'] = display_df['enabled'].map({1: '✅ Enabled', 0: '❌ Disabled'})
        
        # Select and rename columns
        display_df = display_df[['id', 'rule_name', 'alert_type', 'description', 'rule_criteria', 'default_severity', 'enabled']]
        display_df.columns = ['ID', 'Rule Name', 'Alert Type', 'Description', 'Criteria', 'Default Severity', 'Status']
        
        st.dataframe(display_df, use_container_width=True)
    else:
        st.info("No alert rules defined")
    
    # Rule management section - simplified for demo
    st.write("**Rule Management**")
    st.info("In a production environment, this section would provide functionality to create, edit, and delete alert rules.")

# Main application
def main():
    st.title("🚨 Financial Alerts System")
    
    # Check if database exists
    if not check_database_exists():
        st.error(f"Alert database not found. Please run the initialization script.")
        return
    
    # Navigation tabs
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Alert List", "Alert Rules"])
    
    with tab1:
        render_alert_dashboard()
    
    with tab2:
        render_alert_list()
    
    with tab3:
        render_alert_rules()

if __name__ == "__main__":
    main()