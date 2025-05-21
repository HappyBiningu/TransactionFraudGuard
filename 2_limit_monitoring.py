import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3
from sqlite3 import Error

# Database functions
def create_connection():
    """Create a database connection to a SQLite database"""
    conn = None
    try:
        conn = sqlite3.connect('transaction_monitoring.db')
        return conn
    except Error as e:
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
        except Error as e:
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
        except Error as e:
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
            
            conn.commit()
        except Error as e:
            st.error(f"Error saving violations to database: {e}")
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
        except Error as e:
            st.error(f"Error saving file info to database: {e}")
        finally:
            conn.close()

def analyze_limits(df, limits):
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

def preprocess_dataframe(df):
    if df is None:
        return None
    try:
        df = df.copy()
        df['amount'] = pd.to_numeric(df['amount'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        st.error(f"Error preprocessing data: {str(e)}")
        return None

# Initialize database
initialize_database()

# Streamlit App
st.title("💰 Transaction Limit Monitoring")
st.markdown("---")

# Initialize session state with database values
if 'transaction_limits' not in st.session_state:
    st.session_state.transaction_limits = get_settings_from_db()

# Sidebar - Limit Settings
with st.sidebar:
    st.header("Transaction Limits")
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
                # Save file info to database
                save_uploaded_file_info(uploaded_file.name, len(df))
                
                daily_violations, weekly_violations, monthly_violations = analyze_limits(
                    df, 
                    st.session_state.transaction_limits
                )
                
                # Prepare violations data for saving
                violations_data = {
                    'daily_violations': daily_violations,
                    'weekly_violations': weekly_violations,
                    'monthly_violations': monthly_violations
                }
                
                # Save violations to database
                save_violations_to_db(violations_data, st.session_state.transaction_limits)

                # Display controls
                st.markdown("### 📊 Violation Analysis Controls")
                col1, col2 = st.columns([1, 2])
                with col1:
                    display_mode = st.radio(
                        "Display Mode",
                        ["Combined View", "Separate Views"]
                    )
                with col2:
                    st.markdown("##### Display Options")
                    show_banks = st.toggle("Show Bank Details", value=True)
                    show_accounts = st.toggle("Show Account Details", value=True)
                    sort_by = st.selectbox(
                        "Sort Transactions By",
                        ["Amount (High to Low)", "Date", "Number of Accounts Used"]
                    )
                
                st.markdown("---")
                vtab1, vtab2, vtab3 = st.tabs(["Daily Violations", "Weekly Violations", "Monthly Violations"])
                
                def display_violations(violations, limit_type, limit_value):
                    if not violations.empty:
                        direct_violations = violations[violations['amount'] > limit_value]
                        circumvention_attempts = violations[
                            (violations['amount'] >= limit_value * 0.8) &
                            (violations['amount'] <= limit_value) &
                            (violations['num_accounts'] > 1)
                        ]
                        
                        def prepare_display_df(df):
                            display_df = df.copy()
                            display_df['amount'] = display_df['amount'].apply(lambda x: f"${x:,.2f}")
                            
                            if sort_by == "Amount (High to Low)":
                                display_df = display_df.sort_values('amount', ascending=False)
                            elif sort_by == "Date":
                                if 'date' in display_df.columns:
                                    display_df = display_df.sort_values('date')
                            elif sort_by == "Number of Accounts Used":
                                display_df = display_df.sort_values('num_accounts', ascending=False)
                            
                            if not show_banks:
                                display_df = display_df.drop(columns=['bank_name', 'num_banks'], errors='ignore')
                            if not show_accounts:
                                display_df = display_df.drop(columns=['account_id', 'num_accounts'], errors='ignore')
                            
                            return display_df
                        
                        if display_mode == "Combined View":
                            all_violations = pd.concat([
                                direct_violations.assign(type="Direct Violation"),
                                circumvention_attempts.assign(type="Potential Circumvention")
                            ])
                            if not all_violations.empty:
                                display_df = prepare_display_df(all_violations)
                                st.dataframe(display_df, use_container_width=True)
                        else:
                            if not direct_violations.empty:
                                with st.expander("🚨 Direct Limit Violations", expanded=True):
                                    display_df = prepare_display_df(direct_violations)
                                    st.dataframe(display_df, use_container_width=True)
                            
                            if not circumvention_attempts.empty:
                                with st.expander("⚠️ Potential Circumvention Attempts", expanded=True):
                                    display_df = prepare_display_df(circumvention_attempts)
                                    st.dataframe(display_df, use_container_width=True)
                    else:
                        st.info(f"No {limit_type.lower()} limit violations found")
                
                with vtab1:
                    st.subheader(f"Daily Limit Violations (>${st.session_state.transaction_limits['daily']:,.2f})")
                    display_violations(daily_violations, "Daily", st.session_state.transaction_limits['daily'])
                    
                with vtab2:
                    st.subheader(f"Weekly Limit Violations (>${st.session_state.transaction_limits['weekly']:,.2f})")
                    display_violations(weekly_violations, "Weekly", st.session_state.transaction_limits['weekly'])
                    
                with vtab3:
                    st.subheader(f"Monthly Limit Violations (>${st.session_state.transaction_limits['monthly']:,.2f})")
                    display_violations(monthly_violations, "Monthly", st.session_state.transaction_limits['monthly'])

                # Download reports
                if not all(x.empty for x in [daily_violations, weekly_violations, monthly_violations]):
                    st.markdown("### Download Reports")
                    report_cols = st.columns(3)
                    for idx, (name, data) in enumerate(violations_data.items()):
                        if not data.empty:
                            with report_cols[idx]:
                                csv = data.to_csv(index=False)
                                st.download_button(
                                    f"Download {name.replace('_', ' ').title()}",
                                    csv,
                                    f"{name}_{datetime.now().strftime('%Y%m%d')}.csv",
                                    "text/csv"
                                )
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")

# Add database viewer section
st.markdown("---")
st.header("Database Viewer")

db_tab1, db_tab2, db_tab3 = st.tabs(["Violations", "Settings", "Uploaded Files"])

with db_tab1:
    st.subheader("Stored Violations")
    conn = create_connection()
    if conn is not None:
        try:
            violations_df = pd.read_sql("SELECT * FROM violations ORDER BY created_at DESC", conn)
            st.dataframe(violations_df, use_container_width=True)
            
            if not violations_df.empty:
                csv = violations_df.to_csv(index=False)
                st.download_button(
                    "Download All Violations",
                    csv,
                    f"all_violations_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
        except Error as e:
            st.error(f"Error retrieving violations: {e}")
        finally:
            conn.close()

with db_tab2:
    st.subheader("Current Settings")
    conn = create_connection()
    if conn is not None:
        try:
            settings_df = pd.read_sql("SELECT * FROM settings", conn)
            st.dataframe(settings_df, use_container_width=True)
        except Error as e:
            st.error(f"Error retrieving settings: {e}")
        finally:
            conn.close()

with db_tab3:
    st.subheader("Uploaded Files History")
    conn = create_connection()
    if conn is not None:
        try:
            files_df = pd.read_sql("SELECT * FROM uploaded_files ORDER BY upload_time DESC", conn)
            st.dataframe(files_df, use_container_width=True)
            
            if not files_df.empty:
                csv = files_df.to_csv(index=False)
                st.download_button(
                    "Download Files History",
                    csv,
                    f"files_history_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
        except Error as e:
            st.error(f"Error retrieving file history: {e}")
        finally:
            conn.close()