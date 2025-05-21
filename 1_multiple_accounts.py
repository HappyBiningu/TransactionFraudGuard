import streamlit as st
import pandas as pd
import sqlite3
import logging
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DB_FILE = "transactions.db"
TABLE_NAME = "transactions"
PAGE_SIZE = 1000
CACHE_TTL = 60

# Custom CSS
st.markdown("""
    <style>
    .metric-card { background: #f0f2f6; padding: 1rem; border-radius: 8px; }
    .warning-text { color: #dc3545; font-weight: bold; }
    .success-text { color: #28a745; font-weight: bold; }
    .info-zone { background: #f8f9fa; border: 1px solid #dee2e6; padding: 1rem; border-radius: 8px; }
    .section-header { font-size: 1.3rem; font-weight: 600; margin-top: 1.5rem; margin-bottom: 0.5rem; color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)


# Database connection pool
@st.cache_resource
def get_db_pool():
    try:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        logger.info(f"Successfully connected to database: {DB_FILE}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database {DB_FILE}: {e}")
        st.error(f"Database connection error: {e}")
        return None

@contextmanager
def get_db_connection():
    conn = get_db_pool()
    try:
        yield conn
    finally:
        pass  # Connection is managed by pool

def init_database():
    with get_db_connection() as conn:
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=NORMAL;
            PRAGMA cache_size=-2000;
            PRAGMA temp_store=MEMORY;
              -- Create accounts table
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                individual_id TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            );

            -- Create transactions table
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT UNIQUE NOT NULL,
                individual_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                bank_name TEXT NOT NULL,
                amount REAL NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(account_id)
            );

            -- Create indices
            CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_accounts_individual ON accounts(individual_id);
        """)
        conn.commit()

@st.cache_data(ttl=CACHE_TTL)
def get_db_stats():
    """Get statistics about multiple accounts from the database."""
    try:
        conn = get_db_pool()
        if not conn:
            logger.error("Could not get database connection")
            raise Exception("Database connection failed")

        # Check if table exists
        table_check = conn.execute("""
            SELECT name FROM sqlite_master            WHERE type='table' AND name='transactions'
        """).fetchone()
        
        if not table_check:
            logger.info("Table 'transactions' does not exist. Initializing database...")
            init_database()
            return {
                "total_records": 0,
                "unique_individuals": 0,
                "total_amount": 0,
                "date_range": (None, None),
                "avg_accounts": 0,
                "multi_account_holders_count": 0,
                "percent_with_multiple_accounts": 0,
                "top_individuals": {}
            }

        # Get basic stats
        logger.info("Fetching basic statistics...")
        result = conn.execute("""            SELECT 
                COUNT(*) as total_records,
                COUNT(DISTINCT individual_id) as unique_individuals,
                SUM(amount) as total_amount,
                MIN(timestamp) as min_date,
                MAX(timestamp) as max_date
            FROM transactions t
        """).fetchone()
        
        logger.info(f"Basic stats - Records: {result[0]}, Individuals: {result[1]}, Amount: {result[2]}")
        
        # Get multiple accounts stats
        logger.info("Analyzing multiple accounts...")
        multi_accounts_data = pd.read_sql_query("""            SELECT 
                individual_id,
                COUNT(DISTINCT account_id) as account_count
            FROM transactions t
            GROUP BY individual_id
        """, conn)
        
        # Calculate metrics
        avg_accounts = multi_accounts_data['account_count'].mean() if not multi_accounts_data.empty else 0
        multi_account_holders = multi_accounts_data[multi_accounts_data['account_count'] > 1]
        multi_account_holders_count = len(multi_account_holders)
        percent_with_multiple = (multi_account_holders_count / len(multi_accounts_data) * 100) if not multi_accounts_data.empty else 0
        
        # Get top 5 individuals with most accounts
        top_individuals = dict(multi_accounts_data.nlargest(5, 'account_count').set_index('individual_id')['account_count']) if not multi_accounts_data.empty else {}
        
        logger.info(f"Found {multi_account_holders_count} individuals with multiple accounts")
        
        stats = {
            "total_records": result[0] or 0,
            "unique_individuals": result[1] or 0,
            "total_amount": float(result[2] or 0),
            "date_range": (result[3], result[4]),
            "avg_accounts": float(avg_accounts),
            "multi_account_holders_count": multi_account_holders_count,
            "percent_with_multiple_accounts": float(percent_with_multiple),
            "top_individuals": top_individuals
        }
        logger.info("Successfully generated database statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Error in get_db_stats: {str(e)}")
        st.error(f"Error getting database statistics: {str(e)}")
        return {
            "total_records": 0,
            "unique_individuals": 0,
            "total_amount": 0,
            "date_range": (None, None),
            "avg_accounts": 0,
            "multi_account_holders_count": 0,
            "percent_with_multiple_accounts": 0,
            "top_individuals": {}
        }

def save_to_database(df):
    """Save validated DataFrame to the database."""
    try:
        # Check for existing transaction IDs
        with get_db_connection() as conn:
            existing_ids = pd.read_sql(
                f"SELECT transaction_id FROM {TABLE_NAME} WHERE transaction_id IN ({','.join(['?']*len(df))})",
                conn,
                params=df['transaction_id'].tolist()
            )
        
        if not existing_ids.empty:
            st.warning(f"Found {len(existing_ids)} existing transactions in the database.")
            handle_duplicates = st.radio(
                "How would you like to handle existing transactions?",
                ["Skip existing", "Update existing", "Cancel"],
                index=0
            )
            
            if handle_duplicates == "Cancel":
                return False, "Operation cancelled by user"
            
            if handle_duplicates == "Skip existing":
                # Filter out existing transactions
                df = df[~df['transaction_id'].isin(existing_ids['transaction_id'])]
                if df.empty:
                    return False, "No new transactions to save after skipping existing ones"
            
            elif handle_duplicates == "Update existing":
                # Delete existing records first
                with get_db_connection() as conn:
                    placeholders = ','.join(['?' for _ in existing_ids['transaction_id']])
                    conn.execute(
                        f"DELETE FROM {TABLE_NAME} WHERE transaction_id IN ({placeholders})",
                        existing_ids['transaction_id'].tolist()
                    )
                    conn.commit()
        
        # Save to database
        if not df.empty:
            with get_db_connection() as conn:
                try:
                    # Enable foreign keys
                    conn.execute("PRAGMA foreign_keys = ON")
                    
                    # First, insert accounts
                    accounts_df = df[['individual_id', 'account_id', 'bank_name']].drop_duplicates()
                    try:
                        accounts_df.to_sql('accounts', conn, if_exists='append', index=False)
                    except sqlite3.IntegrityError:
                        # Accounts already exist, that's okay
                        pass

                    # Then insert transactions
                    try:
                        df.to_sql(TABLE_NAME, conn, if_exists='append', index=False, chunksize=1000)
                    except sqlite3.IntegrityError as e:
                        if "FOREIGN KEY constraint failed" in str(e):
                            return False, "Error: Some account IDs don't exist in the accounts table."
                        else:
                            return False, f"Error: {str(e)}"
                    
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    return False, f"Database error: {str(e)}"
                    
            st.cache_data.clear()
            return True, f"Successfully saved {len(df)} transactions to database"
        return False, "No transactions to save"
    
    except Exception as e:
        return False, f"Error saving data: {str(e)}"

def validate_dataframe(df):
    """Validate the input DataFrame."""
    if df is None or df.empty:
        return False, "No data provided"

    required_columns = {'transaction_id', 'individual_id', 'account_id', 'bank_name', 'amount', 'timestamp'}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"

    try:
        # Validate data types
        df = df.copy()
        df['amount'] = pd.to_numeric(df['amount'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['transaction_id'] = df['transaction_id'].astype(str)
        df['individual_id'] = df['individual_id'].astype(str)
        df['account_id'] = df['account_id'].astype(str)
        df['bank_name'] = df['bank_name'].astype(str)

        # Check for nulls
        null_counts = df.isnull().sum()
        if null_counts.any():
            return False, f"Found null values in columns: {', '.join(null_counts[null_counts > 0].index)}"

        return True, df
    except Exception as e:
        return False, f"Data validation error: {str(e)}"

@st.cache_data(ttl=CACHE_TTL)
def get_paginated_data(page, page_size):
    try:
        with get_db_connection() as conn:
            total_records = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}").fetchone()[0]
            total_pages = (total_records + page_size - 1) // page_size
            
            offset = page * page_size
            query = f"""
                SELECT transaction_id, individual_id, account_id, bank_name, amount, timestamp
                FROM {TABLE_NAME}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            df = pd.read_sql_query(query, conn, params=(page_size, offset), parse_dates=['timestamp'])
            return df, total_pages, total_records
    except Exception as e:
        logger.error(f"Error fetching paginated data: {e}")
        return pd.DataFrame(), 0, 0

def get_multiple_accounts(df):
    if df.empty:
        return pd.DataFrame()
    
    account_counts = df.groupby('individual_id')['account_id'].nunique()
    multi_account_ids = account_counts[account_counts > 1].index
    
    if not multi_account_ids.any():
        return pd.DataFrame()
    
    multi_data = df[df['individual_id'].isin(multi_account_ids)]
    summary = multi_data.groupby('individual_id').agg({
        'account_id': lambda x: sorted(set(x)),
        'bank_name': lambda x: sorted(set(x)),
        'amount': ['count', 'sum'],
        'timestamp': ['min', 'max']
    }).reset_index()
    
    summary.columns = ['individual_id', 'accounts', 'banks', 'transaction_count', 
                      'total_amount', 'first_transaction', 'last_transaction']
    summary['num_accounts'] = summary['accounts'].apply(len)
    summary['num_banks'] = summary['banks'].apply(len)
    
    return summary.sort_values('num_accounts', ascending=False)

def render_database_management():
    st.markdown('<div class="info-zone"><h3>⚙️ Database Management</h3></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["View Data", "Delete Data"])
    
    with tab1:
        stats = get_db_stats()
        if stats:
            cols = st.columns(3)
            cols[0].metric("Total Records", f"{stats['total_records']:,}")
            cols[1].metric("Unique Individuals", f"{stats['unique_individuals']:,}")
            cols[2].metric("Total Amount", f"${stats['total_amount']:,.2f}")
        
        page = st.session_state.get('current_page', 0)
        df, total_pages, total_records = get_paginated_data(page, PAGE_SIZE)
        
        if not df.empty:
            col1, col2, col3 = st.columns([2, 3, 2])
            with col1:
                if page > 0 and st.button("⬅️ Previous"):
                    st.session_state.current_page = page - 1
                    st.experimental_rerun()
            with col2:
                st.write(f"Page {page + 1} of {total_pages}")
            with col3:
                if page < total_pages - 1 and st.button("Next ➡️"):
                    st.session_state.current_page = page + 1
                    st.experimental_rerun()
            
            st.dataframe(df, use_container_width=True, hide_index=True,
                        column_config={"amount": st.column_config.NumberColumn(format="$%.2f"),
                                     "timestamp": "Timestamp"})
            st.info(f"Showing {page * PAGE_SIZE + 1:,} to {min((page + 1) * PAGE_SIZE, total_records):,} of {total_records:,}")
        else:
            st.info("No data available.")

    with tab2:
        delete_option = st.radio("Delete Option:", ["By Date Range", "By Individual", "All Data"], horizontal=True)
        
        if delete_option == "By Date Range":
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Start Date")
            end_date = col2.date_input("End Date")
            
            if st.button("Confirm Delete"):
                with get_db_connection() as conn:
                    cursor = conn.execute(
                        f"DELETE FROM {TABLE_NAME} WHERE DATE(timestamp) BETWEEN ? AND ?",
                        (start_date, end_date)
                    )
                    count = cursor.rowcount
                    conn.commit()
                st.cache_data.clear()
                st.success(f"Deleted {count:,} records")
                st.experimental_rerun()
        
        elif delete_option == "By Individual":
            with get_db_connection() as conn:                individuals = pd.read_sql_query(
                    "SELECT individual_id, COUNT(*) as count FROM transactions GROUP BY individual_id",
                    conn
                )
            
            if not individuals.empty:
                selected = st.multiselect("Select Individuals",
                                       options=individuals['individual_id'],
                                       format_func=lambda x: f"{x} ({individuals[individuals['individual_id']==x]['count'].iloc[0]:,} transactions)")
                if selected and st.button("Confirm Delete"):
                    with get_db_connection() as conn:
                        placeholders = ','.join(['?' for _ in selected])
                        cursor = conn.execute(
                            f"DELETE FROM {TABLE_NAME} WHERE individual_id IN ({placeholders})",
                            selected
                        )
                        count = cursor.rowcount
                        conn.commit()
                    st.cache_data.clear()
                    st.success(f"Deleted {count:,} records")
                    st.experimental_rerun()
        
        else:
            if st.button("Delete All Data"):
                with get_db_connection() as conn:
                    cursor = conn.execute(f"DELETE FROM {TABLE_NAME}")
                    count = cursor.rowcount
                    conn.commit()
                st.cache_data.clear()
                st.success(f"Deleted {count:,} records")
                st.experimental_rerun()

def get_or_upload_dataframe():
    """Get existing DataFrame from session state or upload a new one."""
    if 'uploaded_df' not in st.session_state:
        st.session_state.uploaded_df = None
    
    uploaded_file = st.file_uploader("Upload CSV", type="csv")
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.session_state.uploaded_df = df
            return df
        except Exception as e:
            st.error(f"Error reading CSV: {str(e)}")
            return None
    
    return st.session_state.uploaded_df

def preprocess_dataframe(df):
    """Preprocess the DataFrame before multiple accounts analysis."""
    if df is None:
        return None
    
    try:
        # Convert timestamp to datetime if it's not already
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by timestamp
        df = df.sort_values('timestamp')
        
        # Remove duplicates based on transaction_id
        df = df.drop_duplicates(subset=['transaction_id'])
        
        return df
    except Exception as e:
        st.error(f"Error preprocessing data: {str(e)}")
        return None

def main():
    init_database()
    st.title("👥 Multiple Bank Accounts Analysis")
    tab1, tab2 = st.tabs(["Analysis", "Database Management"])
    with tab1:
        st.markdown('<div class="section-header">📤 Upload Data</div>', unsafe_allow_html=True)
        df = get_or_upload_dataframe()
        if df is not None:
            df = preprocess_dataframe(df)
            if df is not None:
                valid, result = validate_dataframe(df)
                if valid:
                    if st.button("💾 Save", help="Save uploaded transactions to the database"):
                        success, msg = save_to_database(result)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                else:
                    st.error(result)
        st.markdown('<div class="section-header">📊 Analysis</div>', unsafe_allow_html=True)
        df, _, _ = get_paginated_data(0, PAGE_SIZE)
        if not df.empty:
            stats = get_db_stats()
            cols = st.columns(3)
            cols[0].metric("Total Records", f"{stats['total_records']:,}")
            cols[1].metric("Unique Individuals", f"{stats['unique_individuals']:,}")
            cols[2].metric("Total Amount", f"${stats['total_amount']:,.2f}")
            multi_accounts = get_multiple_accounts(df)
            if not multi_accounts.empty:
                st.subheader(f"Found {len(multi_accounts)} individuals with multiple accounts")
                table_data = multi_accounts.copy()
                table_data['accounts'] = table_data['accounts'].apply(lambda x: ', '.join(x))
                table_data['banks'] = table_data['banks'].apply(lambda x: ', '.join(x))
                table_data['total_amount'] = table_data['total_amount'].apply(lambda x: f"${x:,.2f}")
                st.dataframe(table_data, use_container_width=True, hide_index=True,
                           column_config={
                               "total_amount": "Total Amount",
                               "transaction_count": st.column_config.NumberColumn(format="%d")
                           })
                csv = table_data.to_csv(index=False)
                st.download_button("Download Summary", csv, "summary.csv", "text/csv", help="Download summary of individuals with multiple accounts")
            else:
                st.info("No individuals with multiple accounts.")
        else:
            st.info("No data available.")
    with tab2:
        render_database_management()

if __name__ == "__main__":
    main()