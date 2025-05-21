import streamlit as st
import pandas as pd
import sqlite3
import io
from datetime import datetime, timedelta
import sys
import os

# Add the root directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from auth import require_auth, get_current_user
from sidebar import render_sidebar
from theme_utils import apply_custom_theme

# Constants
DB_FILE = "transactions.db"
PAGE_SIZE = 50

# Set page config
st.set_page_config(page_title="Multiple Accounts Analysis", page_icon="🔍", layout="wide", menu_items=None)

# Apply custom theme
apply_custom_theme()

# Use the default Streamlit navigation
from streamlit_config import use_default_navigation
use_default_navigation()

# Display user info in sidebar
user_info = get_current_user() or {}

# Add user info to sidebar
with st.sidebar:
    st.markdown(f"""
    <div style="padding: 10px; margin-bottom: 20px; border-bottom: 1px solid #e6e6e6;">
        <p style="margin-bottom: 5px;"><strong>Logged in as:</strong></p>
        <p style="margin-bottom: 2px;"><b>{user_info.get('full_name', 'User')}</b></p>
        <p style="font-size: 0.9em; color: #666;">Role: {user_info.get('role', 'Analyst').capitalize()}</p>
    </div>
    """, unsafe_allow_html=True)

# Apply authentication
@require_auth
def main():
    st.title("🔍 Multiple Accounts Analysis")
    
    # Initialize database
    init_database()
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📊 Analysis", "📁 Database Management", "❓ Help"])
    
    with tab1:
        st.header("Multiple Accounts Analysis")
        st.write("This module identifies individuals with accounts across multiple financial institutions")
        
        # Get data for analysis
        df = get_or_upload_dataframe()
        
        if df is not None and not df.empty:
            # Preprocess data if needed
            df = preprocess_dataframe(df)
            
            # Get multiple accounts analysis
            multi_accounts_df = get_multiple_accounts_data()
            
            if multi_accounts_df is not None and not multi_accounts_df.empty:
                st.subheader("🔍 Multiple Account Holders")
                st.write(f"Found {len(multi_accounts_df)} individuals with accounts at multiple banks")
                
                # Display multiple accounts data
                st.dataframe(
                    multi_accounts_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "total_amount": st.column_config.NumberColumn(format="$%.2f"),
                    }
                )
                
                # Export option
                if st.button("Export to CSV"):
                    export_to_csv(multi_accounts_df)
                
                # Individual detail expander
                st.subheader("Individual Detail View")
                selected_individual = st.selectbox(
                    "Select Individual ID", 
                    multi_accounts_df['individual_id'].tolist()
                )
                
                if selected_individual:
                    try:
                        with get_db_connection() as conn:
                            individual_txns = pd.read_sql_query(
                                "SELECT * FROM transactions WHERE individual_id = ? ORDER BY timestamp",
                                conn,
                                params=[selected_individual],
                                parse_dates=['timestamp']
                            )
                            
                            if not individual_txns.empty:
                                st.write(f"**Transactions for {selected_individual}:**")
                                
                                # Show transaction summary by account
                                account_summary = individual_txns.groupby(['account_id', 'bank_name']).agg({
                                    'amount': ['sum', 'mean', 'count'],
                                    'timestamp': ['min', 'max']
                                }).reset_index()
                                
                                account_summary.columns = ['Account ID', 'Bank Name', 'Total Amount', 'Avg Amount', 
                                                        'Transactions', 'First Transaction', 'Last Transaction']
                                
                                st.write("**Account Summary:**")
                                st.dataframe(
                                    account_summary,
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "Total Amount": st.column_config.NumberColumn(format="$%.2f"),
                                        "Avg Amount": st.column_config.NumberColumn(format="$%.2f"),
                                        "First Transaction": st.column_config.DatetimeColumn(format="D MMM YYYY"),
                                        "Last Transaction": st.column_config.DatetimeColumn(format="D MMM YYYY"),
                                    }
                                )
                                
                                # Show transaction details
                                st.write("**Transaction Details:**")
                                st.dataframe(
                                    individual_txns[['transaction_id', 'account_id', 'bank_name', 'amount', 'timestamp']],
                                    use_container_width=True,
                                    hide_index=True,
                                    column_config={
                                        "amount": st.column_config.NumberColumn(format="$%.2f"),
                                        "timestamp": st.column_config.DatetimeColumn(format="D MMM YYYY, h:mm a"),
                                    }
                                )
                    except Exception as e:
                        st.error(f"Error loading individual details: {str(e)}")
            else:
                st.info("No individuals with multiple accounts found in the current dataset.")
    
    with tab2:
        render_database_management()
    
    with tab3:
        st.header("📋 Help & Documentation")
        st.markdown("""
        ## About Multiple Accounts Analysis
        
        This module is designed to identify individuals who hold accounts across multiple financial institutions, which may indicate potential risk or fraud patterns.
        
        ### Key Features
        - **Data Upload**: Upload transaction data in CSV format
        - **Multiple Account Analysis**: Identify individuals with accounts at multiple banks
        - **Individual Details**: View detailed transaction history for specific individuals
        - **Database Management**: View, filter, and export transaction data stored in the system
        
        ### Data Requirements
        For proper analysis, your CSV files should include these fields:
        - `transaction_id`: Unique transaction identifier
        - `individual_id`: Identifier for the individual (customer)
        - `account_id`: Account identifier 
        - `bank_name`: Name of the financial institution
        - `amount`: Transaction amount (numeric)
        - `timestamp`: Transaction date/time (in YYYY-MM-DD format)
        
        ### Analysis Methodology
        The system identifies individuals who have transaction activity across multiple distinct financial institutions, 
        which may require additional scrutiny according to AML/CFT regulations.
        """)

def get_db_pool():
    """Create and return a database connection pool."""
    return sqlite3.connect(DB_FILE)

def get_db_connection():
    """Context manager for database connections."""
    return sqlite3.connect(DB_FILE)

def init_database(conn=None):
    """Initialize the database with necessary tables and indices."""
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_FILE)
        close_conn = True
    
    try:
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA cache_size=-2000;
            PRAGMA temp_store=MEMORY;
            
            -- Create accounts table if not exists
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                individual_id TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            );
            
            -- Create transactions table if not exists
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                individual_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                amount REAL NOT NULL,
                timestamp TIMESTAMP NOT NULL
            );
            
            -- Create indices if not exists
            CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_accounts_individual ON accounts(individual_id);
        """)
        
        if close_conn:
            conn.commit()
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")

def get_db_stats():
    """Get statistics about multiple accounts from the database."""
    try:
        conn = get_db_connection()
        
        # Get basic stats
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transactions")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT individual_id) FROM transactions")
            unique_individuals = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(amount) FROM transactions")
            total_amount = cursor.fetchone()[0]
            
            # Get multiple accounts stats
            multiple_accounts_query = """
                SELECT COUNT(*) FROM (
                    SELECT individual_id
                    FROM transactions
                    GROUP BY individual_id
                    HAVING COUNT(DISTINCT bank_name) > 1
                )
            """
            cursor.execute(multiple_accounts_query)
            multiple_accounts_count = cursor.fetchone()[0]
            
            stats = {
                "total_records": total_records or 0,
                "unique_individuals": unique_individuals or 0,
                "total_amount": total_amount or 0,
                "multiple_accounts_count": multiple_accounts_count or 0
            }
            
            return stats
        finally:
            conn.close()
    except Exception as e:
        st.error(f"Error getting database statistics: {str(e)}")
        return None

def validate_dataframe(df):
    """Validate the input DataFrame."""
    required_columns = ['transaction_id', 'individual_id', 'account_id', 'bank_name', 'amount', 'timestamp']
    
    # Check for required columns
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        st.error(f"Missing required columns: {', '.join(missing_cols)}")
        return False
    
    # Check for data integrity
    if df.empty:
        st.error("The uploaded data is empty")
        return False
    
    # Convert timestamp to datetime if it's not already
    try:
        if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
    except Exception as e:
        st.error(f"Error converting timestamps: {str(e)}")
        return False
    
    # Verify amount is numeric
    if not pd.api.types.is_numeric_dtype(df['amount']):
        try:
            df['amount'] = pd.to_numeric(df['amount'])
        except:
            st.error("Amount column must contain numeric values")
            return False
    
    return True

def save_to_database(df):
    """Save validated DataFrame to the database."""
    try:
        conn = get_db_connection()
        
        try:
            # Process accounts first
            accounts_df = df[['individual_id', 'account_id', 'bank_name']].drop_duplicates()
            
            # Check if accounts already exist
            for _, row in accounts_df.iterrows():
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT account_id FROM accounts WHERE account_id = ?", 
                    (row['account_id'],)
                )
                
                if cursor.fetchone() is None:
                    cursor.execute(
                        "INSERT INTO accounts (account_id, individual_id, bank_name) VALUES (?, ?, ?)",
                        (row['account_id'], row['individual_id'], row['bank_name'])
                    )
            
            # Process transactions
            for _, row in df.iterrows():
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT transaction_id FROM transactions WHERE transaction_id = ?", 
                    (row['transaction_id'],)
                )
                
                if cursor.fetchone() is None:
                    cursor.execute(
                        """
                        INSERT INTO transactions (
                            transaction_id, individual_id, account_id, bank_name, amount, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            row['transaction_id'], 
                            row['individual_id'],
                            row['account_id'],
                            row['bank_name'],
                            float(row['amount']),
                            row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        )
                    )
            
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            st.error(f"Error saving data: {str(e)}")
            return False
        finally:
            conn.close()
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return False

def get_paginated_data(page, page_size=PAGE_SIZE, date_range=None, bank_filter=None, min_accounts=1):
    """Get paginated transaction data with filters."""
    try:
        conn = get_db_connection()
        
        # Build query with filters
        query = "SELECT * FROM transactions"
        params = []
        where_clauses = []
        
        if date_range and len(date_range) == 2:
            where_clauses.append("timestamp BETWEEN ? AND ?")
            params.extend([date_range[0], date_range[1]])
        
        if bank_filter:
            where_clauses.append("bank_name = ?")
            params.append(bank_filter)
        
        if min_accounts > 1:
            # Only include individuals with multiple accounts
            subquery = """
                individual_id IN (
                    SELECT individual_id 
                    FROM transactions 
                    GROUP BY individual_id 
                    HAVING COUNT(DISTINCT bank_name) >= ?
                )
            """
            where_clauses.append(subquery)
            params.append(min_accounts)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        # Add ordering and pagination
        query += " ORDER BY timestamp DESC"
        
        # Get total count for pagination
        count_query = f"SELECT COUNT(*) FROM ({query})"
        cursor = conn.cursor()
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
        
        # Add limit and offset for pagination
        query += f" LIMIT {page_size} OFFSET {page * page_size}"
        
        # Execute query
        df = pd.read_sql_query(query, conn, params=params, parse_dates=['timestamp'])
        
        conn.close()
        
        # Calculate total pages
        total_pages = (total_count + page_size - 1) // page_size
        
        return df, total_pages, total_count
    except Exception as e:
        st.error(f"Error retrieving data: {str(e)}")
        return pd.DataFrame(), 0, 0

def get_multiple_accounts_data():
    """Get data about individuals with multiple accounts."""
    try:
        conn = get_db_connection()
        
        # Query to find individuals with multiple bank accounts
        query = """
            WITH individual_banks AS (
                SELECT 
                    individual_id,
                    COUNT(DISTINCT bank_name) as bank_count,
                    COUNT(DISTINCT account_id) as account_count,
                    SUM(amount) as total_amount,
                    GROUP_CONCAT(DISTINCT bank_name) as banks,
                    GROUP_CONCAT(DISTINCT account_id) as accounts,
                    MIN(timestamp) as first_transaction,
                    MAX(timestamp) as last_transaction,
                    COUNT(*) as transaction_count
                FROM 
                    transactions
                GROUP BY 
                    individual_id
                HAVING 
                    COUNT(DISTINCT bank_name) > 1
            )
            SELECT * FROM individual_banks
            ORDER BY bank_count DESC, total_amount DESC
        """
        
        df = pd.read_sql_query(query, conn, parse_dates=['first_transaction', 'last_transaction'])
        conn.close()
        
        return df
    except Exception as e:
        st.error(f"Error retrieving multiple accounts data: {str(e)}")
        return None

def export_to_csv(df):
    """Export DataFrame to CSV."""
    try:
        csv = df.to_csv(index=False).encode('utf-8')
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="Download CSV File",
            data=csv,
            file_name=f"multiple_accounts_{timestamp}.csv",
            mime="text/csv",
        )
    except Exception as e:
        st.error(f"Error exporting data: {str(e)}")

def render_database_management():
    st.header("📁 Database Management")
    
    tab1, tab2 = st.tabs(["View Data", "Delete Data"])
    
    with tab1:
        stats = get_db_stats()
        if stats:
            cols = st.columns(4)
            cols[0].metric("Total Records", f"{stats['total_records']:,}")
            cols[1].metric("Unique Individuals", f"{stats['unique_individuals']:,}")
            cols[2].metric("Multiple Account Users", f"{stats['multiple_accounts_count']:,}")
            cols[3].metric("Total Amount", f"${stats['total_amount']:,.2f}" if stats['total_amount'] else "$0.00")
        
        st.subheader("Transaction Records")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date_range = st.date_input(
                "Date Range",
                value=None,
                format="YYYY-MM-DD"
            )
        
        with col2:
            # Get unique banks for filter
            try:
                conn = get_db_connection()
                banks_df = pd.read_sql_query("SELECT DISTINCT bank_name FROM transactions", conn)
                conn.close()
                
                bank_options = ["All Banks"] + banks_df['bank_name'].tolist()
                bank_filter = st.selectbox("Bank", bank_options)
                if bank_filter == "All Banks":
                    bank_filter = None
            except:
                bank_filter = None
        
        with col3:
            min_accounts = st.number_input("Min. Number of Banks", min_value=1, max_value=10, value=1)
        
        # Initialize session state for pagination
        if "current_page" not in st.session_state:
            st.session_state.current_page = 0
        
        # Get paginated data
        page = st.session_state.current_page
        df, total_pages, total_records = get_paginated_data(
            page, PAGE_SIZE, date_range, bank_filter, min_accounts
        )
        
        if not df.empty:
            st.write(f"Showing {len(df)} of {total_records:,} records")
            
            # Pagination controls
            col1, col2, col3 = st.columns([2, 3, 2])
            with col1:
                if page > 0 and st.button("⬅️ Previous Page"):
                    st.session_state.current_page = page - 1
                    st.rerun()
            with col2:
                st.write(f"Page {page + 1} of {total_pages}")
            with col3:
                if page < total_pages - 1 and st.button("Next Page ➡️"):
                    st.session_state.current_page = page + 1
                    st.rerun()
            
            # Display data
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "amount": st.column_config.NumberColumn(format="$%.2f"),
                    "timestamp": st.column_config.DatetimeColumn(format="D MMM YYYY, h:mm a"),
                }
            )
            
            # Export option
            if st.button("Export All Transactions"):
                try:
                    conn = get_db_connection()
                    
                    # Build query with the same filters
                    query = "SELECT * FROM transactions"
                    params = []
                    where_clauses = []
                    
                    if date_range and len(date_range) == 2:
                        where_clauses.append("timestamp BETWEEN ? AND ?")
                        params.extend([date_range[0], date_range[1]])
                    
                    if bank_filter:
                        where_clauses.append("bank_name = ?")
                        params.append(bank_filter)
                    
                    if min_accounts > 1:
                        subquery = """
                            individual_id IN (
                                SELECT individual_id 
                                FROM transactions 
                                GROUP BY individual_id 
                                HAVING COUNT(DISTINCT bank_name) >= ?
                            )
                        """
                        where_clauses.append(subquery)
                        params.append(min_accounts)
                    
                    if where_clauses:
                        query += " WHERE " + " AND ".join(where_clauses)
                    
                    query += " ORDER BY timestamp DESC"
                    
                    # Execute query without pagination
                    all_data = pd.read_sql_query(query, conn, params=params, parse_dates=['timestamp'])
                    conn.close()
                    
                    # Export all data
                    export_to_csv(all_data)
                except Exception as e:
                    st.error(f"Error exporting all transactions: {str(e)}")
        else:
            st.info("No transaction records found matching the criteria.")
    
    with tab2:
        st.subheader("Delete Data")
        st.warning("⚠️ Deleting data is irreversible. Use with caution.")
        
        delete_option = st.radio(
            "Delete Options",
            ["Delete All Data", "Delete by Date Range", "Delete by Bank"]
        )
        
        if delete_option == "Delete All Data":
            if st.button("Delete All Transaction Data", type="primary"):
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM transactions")
                    count = cursor.rowcount
                    conn.commit()
                    conn.close()
                    st.success(f"Successfully deleted {count} transaction records.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting data: {str(e)}")
        
        elif delete_option == "Delete by Date Range":
            date_range = st.date_input(
                "Select Date Range to Delete",
                value=[datetime.now() - timedelta(days=30), datetime.now()],
                format="YYYY-MM-DD"
            )
            
            if len(date_range) == 2 and st.button("Delete Transactions in Selected Date Range", type="primary"):
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM transactions WHERE timestamp BETWEEN ? AND ?",
                        [date_range[0].strftime('%Y-%m-%d'), date_range[1].strftime('%Y-%m-%d 23:59:59')]
                    )
                    count = cursor.rowcount
                    conn.commit()
                    conn.close()
                    st.success(f"Successfully deleted {count} transaction records.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting data: {str(e)}")
        
        elif delete_option == "Delete by Bank":
            try:
                conn = get_db_connection()
                banks_df = pd.read_sql_query("SELECT DISTINCT bank_name FROM transactions", conn)
                conn.close()
                
                if not banks_df.empty:
                    bank_to_delete = st.selectbox(
                        "Select Bank to Delete Transactions From",
                        banks_df['bank_name'].tolist()
                    )
                    
                    if st.button("Delete Transactions from Selected Bank", type="primary"):
                        try:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "DELETE FROM transactions WHERE bank_name = ?",
                                [bank_to_delete]
                            )
                            count = cursor.rowcount
                            conn.commit()
                            conn.close()
                            st.success(f"Successfully deleted {count} transaction records from {bank_to_delete}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting data: {str(e)}")
                else:
                    st.info("No bank data available.")
            except Exception as e:
                st.error(f"Error loading banks: {str(e)}")

def get_or_upload_dataframe():
    """Get existing DataFrame from session state or upload a new one."""
    st.subheader("Data Source")
    
    option = st.radio(
        "Choose data source:",
        ["Use Existing Data", "Upload New Data"]
    )
    
    if option == "Upload New Data":
        uploaded_file = st.file_uploader("Upload transaction data (CSV)", type=["csv"])
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file, parse_dates=['timestamp'])
                
                if validate_dataframe(df):
                    st.success(f"Successfully loaded {len(df)} transactions")
                    
                    if st.button("Save to Database"):
                        if save_to_database(df):
                            st.success("Data saved to database successfully!")
                            return df
                        else:
                            st.error("Failed to save data to database.")
                    
                    return df
                else:
                    return None
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
                return None
    else:
        # Fetch existing data from database
        try:
            stats = get_db_stats()
            
            if stats and stats["total_records"] > 0:
                st.success(f"Using existing data ({stats['total_records']:,} records)")
                return pd.DataFrame()  # Return empty DataFrame to indicate using existing data
            else:
                st.warning("No existing data found in the database. Please upload data.")
                return None
        except Exception as e:
            st.error(f"Error checking existing data: {str(e)}")
            return None

def preprocess_dataframe(df):
    """Preprocess the DataFrame before multiple accounts analysis."""
    if df.empty:
        return df  # Using existing data from database
    
    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Ensure amount is float
    df['amount'] = df['amount'].astype(float)
    
    return df

if __name__ == "__main__":
    main()