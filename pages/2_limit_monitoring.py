import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
from sqlite3 import Error
import io
import plotly.express as px
import plotly.graph_objects as go
import logging
import os
import sys

# Add the root directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sidebar import render_sidebar

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

# Constants
DB_FILE = "transaction_monitoring.db"

# Page configuration
st.set_page_config(
    page_title="Transaction Limit Monitoring",
    page_icon="🚦",
    layout="wide",
    menu_items=None
)

# Render sidebar navigation
render_sidebar()

# Database functions
def create_connection():
    """Create a database connection to a SQLite database"""
    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        return conn
    except Error as e:
        logger.error(f"Error connecting to database: {e}")
        st.error(f"Error connecting to database: {e}")
    return conn

def initialize_database():
    """Initialize the database with required tables"""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Create settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    setting_name TEXT UNIQUE,
                    setting_value REAL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create violations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    individual_id TEXT,
                    period_type TEXT,
                    period_date TEXT,
                    amount REAL,
                    num_accounts INTEGER,
                    num_banks INTEGER,
                    bank_names TEXT,
                    account_ids TEXT,
                    transaction_count INTEGER,
                    limit_value REAL,
                    violation_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create uploaded_files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS uploaded_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    record_count INTEGER
                )
            ''')
            
            # Insert default limits if they don't exist
            cursor.execute('''
                INSERT OR IGNORE INTO settings (setting_name, setting_value)
                VALUES 
                    ('daily_limit', 1000.0),
                    ('weekly_limit', 5000.0),
                    ('monthly_limit', 10000.0)
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
        except Error as e:
            logger.error(f"Error initializing database: {e}")
            st.error(f"Error initializing database: {e}")
        finally:
            conn.close()

def save_settings_to_db(limits):
    """Save current limits to database"""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE settings
                SET setting_value = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE setting_name = 'daily_limit'
            ''', (limits['daily'],))
            
            cursor.execute('''
                UPDATE settings
                SET setting_value = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE setting_name = 'weekly_limit'
            ''', (limits['weekly'],))
            
            cursor.execute('''
                UPDATE settings
                SET setting_value = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE setting_name = 'monthly_limit'
            ''', (limits['monthly'],))
            
            conn.commit()
            logger.info(f"Updated settings: daily={limits['daily']}, weekly={limits['weekly']}, monthly={limits['monthly']}")
        except Error as e:
            logger.error(f"Error saving settings to database: {e}")
            st.error(f"Error saving settings to database: {e}")
        finally:
            conn.close()

def get_settings_from_db():
    """Retrieve limits from database"""
    limits = {
        'daily': 1000.0,
        'weekly': 5000.0,
        'monthly': 10000.0
    }
    
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT setting_name, setting_value FROM settings")
            rows = cursor.fetchall()
            
            for row in rows:
                if row[0] == 'daily_limit':
                    limits['daily'] = row[1]
                elif row[0] == 'weekly_limit':
                    limits['weekly'] = row[1]
                elif row[0] == 'monthly_limit':
                    limits['monthly'] = row[1]
        except Error as e:
            logger.error(f"Error retrieving settings from database: {e}")
            st.error(f"Error retrieving settings from database: {e}")
        finally:
            conn.close()
    
    return limits

def save_violations_to_db(violations_data, limits):
    """Save violations data to database"""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            
            # Count total violations to be inserted
            total_violations = (
                len(violations_data['daily_violations']) + 
                len(violations_data['weekly_violations']) + 
                len(violations_data['monthly_violations'])
            )
            
            inserted_count = 0
            
            # Save daily violations
            for _, row in violations_data['daily_violations'].iterrows():
                violation_type = 'Direct Violation' if row['amount'] > limits['daily'] else 'Potential Circumvention'
                cursor.execute('''
                    INSERT INTO violations (
                        individual_id, period_type, period_date, amount, 
                        num_accounts, num_banks, bank_names, account_ids, 
                        transaction_count, limit_value, violation_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['individual_id'], 'daily', str(row['date']), row['amount'],
                    row['num_accounts'], row['num_banks'], row['bank_name'], row['account_id'],
                    row['transaction_id'], limits['daily'], violation_type
                ))
                inserted_count += 1
            
            # Save weekly violations
            for _, row in violations_data['weekly_violations'].iterrows():
                violation_type = 'Direct Violation' if row['amount'] > limits['weekly'] else 'Potential Circumvention'
                period_date = f"Week {row['week']}, {row['year']}"
                cursor.execute('''
                    INSERT INTO violations (
                        individual_id, period_type, period_date, amount, 
                        num_accounts, num_banks, bank_names, account_ids, 
                        transaction_count, limit_value, violation_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['individual_id'], 'weekly', period_date, row['amount'],
                    row['num_accounts'], row['num_banks'], row['bank_name'], row['account_id'],
                    row['transaction_id'], limits['weekly'], violation_type
                ))
                inserted_count += 1
            
            # Save monthly violations
            for _, row in violations_data['monthly_violations'].iterrows():
                violation_type = 'Direct Violation' if row['amount'] > limits['monthly'] else 'Potential Circumvention'
                period_date = f"{row['month']}/{row['year']}"
                cursor.execute('''
                    INSERT INTO violations (
                        individual_id, period_type, period_date, amount, 
                        num_accounts, num_banks, bank_names, account_ids, 
                        transaction_count, limit_value, violation_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row['individual_id'], 'monthly', period_date, row['amount'],
                    row['num_accounts'], row['num_banks'], row['bank_name'], row['account_id'],
                    row['transaction_id'], limits['monthly'], violation_type
                ))
                inserted_count += 1
            
            conn.commit()
            logger.info(f"Saved {inserted_count} violations to database")
            return inserted_count
        except Error as e:
            logger.error(f"Error saving violations to database: {e}")
            st.error(f"Error saving violations to database: {e}")
            return 0
        finally:
            conn.close()

def save_uploaded_file_info(filename, record_count):
    """Save information about uploaded file"""
    conn = create_connection()
    if conn is not None:
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO uploaded_files (filename, record_count)
                VALUES (?, ?)
            ''', (filename, record_count))
            conn.commit()
            logger.info(f"Recorded file upload: {filename} with {record_count} records")
        except Error as e:
            logger.error(f"Error saving file info to database: {e}")
            st.error(f"Error saving file info to database: {e}")
        finally:
            conn.close()

def analyze_limits(df, limits):
    """Analyze transactions against limits and identify violations"""
    try:
        # Process timestamps
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['date'] = df['timestamp'].dt.date
        df['week'] = df['timestamp'].dt.isocalendar().week
        df['month'] = df['timestamp'].dt.month
        df['year'] = df['timestamp'].dt.year

        # Calculate totals by individual and time period
        daily_totals = df.groupby(['individual_id', 'date']).agg({
            'amount': 'sum',
            'bank_name': lambda x: ', '.join(sorted(set(x))),
            'account_id': lambda x: ', '.join(sorted(set(x))),
            'transaction_id': 'count'
        }).reset_index()
        
        weekly_totals = df.groupby(['individual_id', 'year', 'week']).agg({
            'amount': 'sum',
            'bank_name': lambda x: ', '.join(sorted(set(x))),
            'account_id': lambda x: ', '.join(sorted(set(x))),
            'transaction_id': 'count'
        }).reset_index()
        
        monthly_totals = df.groupby(['individual_id', 'year', 'month']).agg({
            'amount': 'sum',
            'bank_name': lambda x: ', '.join(sorted(set(x))),
            'account_id': lambda x: ', '.join(sorted(set(x))),
            'transaction_id': 'count'
        }).reset_index()

        # Add bank and account counts
        for df_totals in [daily_totals, weekly_totals, monthly_totals]:
            df_totals['num_banks'] = df_totals['bank_name'].str.count(',') + 1
            df_totals['num_accounts'] = df_totals['account_id'].str.count(',') + 1

        # Identify violations and potential circumvention
        daily_violations = daily_totals[
            (daily_totals['amount'] > limits['daily']) |
            ((daily_totals['amount'] >= limits['daily'] * 0.8) & (daily_totals['num_accounts'] > 1))
        ]
        
        weekly_violations = weekly_totals[
            (weekly_totals['amount'] > limits['weekly']) |
            ((weekly_totals['amount'] >= limits['weekly'] * 0.8) & (weekly_totals['num_accounts'] > 1))
        ]
        
        monthly_violations = monthly_totals[
            (monthly_totals['amount'] > limits['monthly']) |
            ((monthly_totals['amount'] >= limits['monthly'] * 0.8) & (monthly_totals['num_accounts'] > 1))
        ]

        return daily_violations, weekly_violations, monthly_violations
    except Exception as e:
        logger.error(f"Error in limit analysis: {e}")
        st.error(f"Error analyzing limits: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def preprocess_dataframe(df):
    """Preprocess and validate DataFrame"""
    if df is None:
        return None
    try:
        df = df.copy()
        df['amount'] = pd.to_numeric(df['amount'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        logger.error(f"Error preprocessing data: {str(e)}")
        st.error(f"Error preprocessing data: {str(e)}")
        return None

def get_violations_from_db(period_type=None, limit=100):
    """Get violations from database"""
    conn = create_connection()
    if conn is not None:
        try:
            query = "SELECT * FROM violations"
            params = []
            
            if period_type:
                query += " WHERE period_type = ?"
                params.append(period_type)
                
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            violations = pd.read_sql_query(query, conn, params=params)
            return violations
        except Error as e:
            logger.error(f"Error getting violations from database: {e}")
            st.error(f"Error getting violations from database: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()

def export_to_csv(df, filename):
    """Export DataFrame to CSV"""
    if df.empty:
        st.error("No data to export.")
        return
    
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=filename,
        mime="text/csv"
    )

def get_violation_stats():
    """Get statistics about violations"""
    conn = create_connection()
    if conn is not None:
        try:
            # Total violations
            total = pd.read_sql_query("SELECT COUNT(*) as count FROM violations", conn)['count'].iloc[0]
            
            # Violations by type
            by_type = pd.read_sql_query(
                "SELECT period_type, COUNT(*) as count FROM violations GROUP BY period_type", 
                conn
            )
            
            # Violations by violation type
            by_violation = pd.read_sql_query(
                "SELECT violation_type, COUNT(*) as count FROM violations GROUP BY violation_type", 
                conn
            )
            
            # Top individuals with violations
            top_individuals = pd.read_sql_query(
                "SELECT individual_id, COUNT(*) as count FROM violations GROUP BY individual_id ORDER BY count DESC LIMIT 5", 
                conn
            )
            
            # Recent trend (last 10 days)
            recent_trend = pd.read_sql_query(
                "SELECT date(created_at) as date, COUNT(*) as count FROM violations GROUP BY date(created_at) ORDER BY date DESC LIMIT 10", 
                conn
            )
            recent_trend['date'] = pd.to_datetime(recent_trend['date'])
            recent_trend = recent_trend.sort_values('date')
            
            return {
                'total': total,
                'by_type': by_type,
                'by_violation': by_violation,
                'top_individuals': top_individuals,
                'recent_trend': recent_trend
            }
        except Error as e:
            logger.error(f"Error getting violation stats: {e}")
            st.error(f"Error getting violation stats: {e}")
            return {}
        finally:
            conn.close()
    return {}

# Initialize database
initialize_database()

# Streamlit UI
st.title("🚦 Transaction Limit Monitoring")
st.markdown("---")

# Initialize session state with database values
if 'transaction_limits' not in st.session_state:
    st.session_state.transaction_limits = get_settings_from_db()

# Sidebar - Limit Settings
# Transaction limit controls - moved from sidebar to main content
col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("Transaction Limits")
    st.session_state.transaction_limits['daily'] = st.number_input(
        "Daily Limit ($)",
        value=st.session_state.transaction_limits['daily'],
        min_value=0.0
    )
    st.session_state.transaction_limits['weekly'] = st.number_input(
        "Weekly Limit ($)",
        value=st.session_state.transaction_limits['weekly'],
        min_value=0.0
    )
    st.session_state.transaction_limits['monthly'] = st.number_input(
        "Monthly Limit ($)",
        value=st.session_state.transaction_limits['monthly'],
        min_value=0.0
    )
    
    # Save button for limits
    if st.button("Save Limits to Database"):
        save_settings_to_db(st.session_state.transaction_limits)
        st.success("Limits saved to database!")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["Upload & Process", "Violation History", "Statistics", "Export"])

with tab1:
    st.header("Upload Transactions")
    
    # File uploader
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            df = preprocess_dataframe(df)
            
            if df is not None:
                if not all(col in df.columns for col in ['individual_id', 'amount', 'timestamp']):
                    st.error("CSV must contain individual_id, amount, and timestamp columns!")
                else:
                    # Store in session state
                    st.session_state.transactions_df = df
                    
                    # Display preview
                    st.subheader("Data Preview")
                    st.dataframe(df.head(10))
                    
                    # Process data button
                    if st.button("Process Transactions"):
                        daily_violations, weekly_violations, monthly_violations = analyze_limits(
                            df, st.session_state.transaction_limits
                        )
                        
                        violations_data = {
                            'daily_violations': daily_violations,
                            'weekly_violations': weekly_violations,
                            'monthly_violations': monthly_violations
                        }
                        
                        # Store in session state
                        st.session_state.violations_data = violations_data
                        
                        # Display violations summary
                        st.subheader("Violations Summary")
                        
                        total_violations = len(daily_violations) + len(weekly_violations) + len(monthly_violations)
                        
                        # Violations metrics
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Daily Violations", len(daily_violations))
                        with col2:
                            st.metric("Weekly Violations", len(weekly_violations))
                        with col3:
                            st.metric("Monthly Violations", len(monthly_violations))
                        with col4:
                            st.metric("Total Violations", total_violations)
                        
                        # Display detailed violations
                        if total_violations > 0:
                            # Format daily violations
                            if not daily_violations.empty:
                                st.subheader("Daily Violations")
                                display_daily = daily_violations.copy()
                                display_daily['violation_type'] = display_daily.apply(
                                    lambda x: 'Direct Violation' if x['amount'] > st.session_state.transaction_limits['daily'] 
                                    else 'Potential Circumvention', axis=1
                                )
                                display_daily['limit'] = st.session_state.transaction_limits['daily']
                                display_daily['over_limit'] = display_daily['amount'] - display_daily['limit']
                                display_daily['over_limit_percent'] = (display_daily['over_limit'] / display_daily['limit']) * 100
                                
                                cols_to_display = ['individual_id', 'date', 'amount', 'num_accounts', 'num_banks', 
                                                'limit', 'over_limit', 'over_limit_percent', 'violation_type']
                                st.dataframe(display_daily[cols_to_display])
                            
                            # Format weekly violations
                            if not weekly_violations.empty:
                                st.subheader("Weekly Violations")
                                display_weekly = weekly_violations.copy()
                                display_weekly['period'] = display_weekly.apply(
                                    lambda x: f"Week {x['week']}, {x['year']}", axis=1
                                )
                                display_weekly['violation_type'] = display_weekly.apply(
                                    lambda x: 'Direct Violation' if x['amount'] > st.session_state.transaction_limits['weekly'] 
                                    else 'Potential Circumvention', axis=1
                                )
                                display_weekly['limit'] = st.session_state.transaction_limits['weekly']
                                display_weekly['over_limit'] = display_weekly['amount'] - display_weekly['limit']
                                display_weekly['over_limit_percent'] = (display_weekly['over_limit'] / display_weekly['limit']) * 100
                                
                                cols_to_display = ['individual_id', 'period', 'amount', 'num_accounts', 'num_banks', 
                                                'limit', 'over_limit', 'over_limit_percent', 'violation_type']
                                st.dataframe(display_weekly[cols_to_display])
                            
                            # Format monthly violations
                            if not monthly_violations.empty:
                                st.subheader("Monthly Violations")
                                display_monthly = monthly_violations.copy()
                                display_monthly['period'] = display_monthly.apply(
                                    lambda x: f"{x['month']}/{x['year']}", axis=1
                                )
                                display_monthly['violation_type'] = display_monthly.apply(
                                    lambda x: 'Direct Violation' if x['amount'] > st.session_state.transaction_limits['monthly'] 
                                    else 'Potential Circumvention', axis=1
                                )
                                display_monthly['limit'] = st.session_state.transaction_limits['monthly']
                                display_monthly['over_limit'] = display_monthly['amount'] - display_monthly['limit']
                                display_monthly['over_limit_percent'] = (display_monthly['over_limit'] / display_monthly['limit']) * 100
                                
                                cols_to_display = ['individual_id', 'period', 'amount', 'num_accounts', 'num_banks', 
                                                'limit', 'over_limit', 'over_limit_percent', 'violation_type']
                                st.dataframe(display_monthly[cols_to_display])
                            
                            # Save violations button
                            if st.button("Save Violations to Database"):
                                inserted_count = save_violations_to_db(violations_data, st.session_state.transaction_limits)
                                save_uploaded_file_info(uploaded_file.name, len(df))
                                st.success(f"Successfully saved {inserted_count} violations to database.")
                        else:
                            st.info("No violations found in the uploaded data.")
        except Exception as e:
            logger.error(f"Error processing upload: {str(e)}")
            st.error(f"Error processing upload: {str(e)}")

with tab2:
    st.header("Violation History")
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        period_filter = st.selectbox(
            "Period Type",
            ["All", "daily", "weekly", "monthly"]
        )
    
    # Get violations from database
    period_type = None if period_filter == "All" else period_filter
    violations = get_violations_from_db(period_type)
    
    if not violations.empty:
        # Format date columns
        violations['created_at'] = pd.to_datetime(violations['created_at'])
        violations['created_at'] = violations['created_at'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Format currency columns
        violations['amount'] = violations['amount'].apply(lambda x: f"${x:,.2f}")
        violations['limit_value'] = violations['limit_value'].apply(lambda x: f"${x:,.2f}")
        
        # Display violations
        st.dataframe(violations)
        
        # Individual details
        st.subheader("Individual Details")
        selected_individual = st.selectbox(
            "Select Individual ID",
            [""] + violations['individual_id'].unique().tolist()
        )
        
        if selected_individual:
            individual_violations = violations[violations['individual_id'] == selected_individual]
            st.write(f"Showing {len(individual_violations)} violations for {selected_individual}")
            st.dataframe(individual_violations)
    else:
        st.info("No violations found in the database.")

with tab3:
    st.header("Violation Statistics")
    
    # Get statistics
    stats = get_violation_stats()
    
    if stats and 'total' in stats:
        # Top metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Violations", stats['total'])
        
        with col2:
            if not stats['by_type'].empty:
                daily_count = stats['by_type'][stats['by_type']['period_type'] == 'daily']['count'].iloc[0] if 'daily' in stats['by_type']['period_type'].values else 0
                st.metric("Daily Violations", daily_count)
        
        with col3:
            if not stats['by_violation'].empty:
                direct_violations = stats['by_violation'][stats['by_violation']['violation_type'] == 'Direct Violation']['count'].iloc[0] if 'Direct Violation' in stats['by_violation']['violation_type'].values else 0
                st.metric("Direct Violations", direct_violations)
        
        # Create visualizations
        col1, col2 = st.columns(2)
        
        with col1:
            # Violations by period type
            if not stats['by_type'].empty:
                fig = px.pie(
                    stats['by_type'],
                    values='count',
                    names='period_type',
                    title="Violations by Period Type"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Top individuals with violations
            if not stats['top_individuals'].empty:
                fig = px.bar(
                    stats['top_individuals'],
                    x='individual_id',
                    y='count',
                    title="Top Individuals with Violations"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Violations by violation type
            if not stats['by_violation'].empty:
                fig = px.pie(
                    stats['by_violation'],
                    values='count',
                    names='violation_type',
                    title="Violations by Type"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Recent trend
            if not stats['recent_trend'].empty:
                fig = px.line(
                    stats['recent_trend'],
                    x='date',
                    y='count',
                    title="Recent Violation Trend"
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No violation statistics available.")

with tab4:
    st.header("Export Data")
    
    export_type = st.selectbox(
        "Select Export Type",
        ["Violations Summary", "Daily Violations", "Weekly Violations", "Monthly Violations", "All Violations"]
    )
    
    if export_type == "Violations Summary":
        # Create summary dataframe
        if 'stats' in locals() and stats and 'total' in stats:
            summary_data = {
                "Metric": ["Total Violations"],
                "Value": [stats['total']]
            }
            
            if not stats['by_type'].empty:
                for _, row in stats['by_type'].iterrows():
                    summary_data["Metric"].append(f"{row['period_type'].capitalize()} Violations")
                    summary_data["Value"].append(row['count'])
            
            if not stats['by_violation'].empty:
                for _, row in stats['by_violation'].iterrows():
                    summary_data["Metric"].append(f"{row['violation_type']}")
                    summary_data["Value"].append(row['count'])
            
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df)
            
            export_to_csv(summary_df, "violations_summary.csv")
        else:
            st.info("No violation statistics available for export.")
    
    elif export_type == "Daily Violations":
        violations = get_violations_from_db('daily')
        if not violations.empty:
            st.dataframe(violations)
            export_to_csv(violations, "daily_violations.csv")
        else:
            st.info("No daily violations available for export.")
    
    elif export_type == "Weekly Violations":
        violations = get_violations_from_db('weekly')
        if not violations.empty:
            st.dataframe(violations)
            export_to_csv(violations, "weekly_violations.csv")
        else:
            st.info("No weekly violations available for export.")
    
    elif export_type == "Monthly Violations":
        violations = get_violations_from_db('monthly')
        if not violations.empty:
            st.dataframe(violations)
            export_to_csv(violations, "monthly_violations.csv")
        else:
            st.info("No monthly violations available for export.")
    
    elif export_type == "All Violations":
        violations = get_violations_from_db()
        if not violations.empty:
            st.dataframe(violations)
            export_to_csv(violations, "all_violations.csv")
        else:
            st.info("No violations available for export.")

# System status info
# Database info moved to main content footer
st.markdown("---")
st.caption(f"Database: {DB_FILE} | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
