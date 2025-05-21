import streamlit as st
import pandas as pd
import sqlite3
import logging
import io
import plotly.express as px
from contextlib import contextmanager
from datetime import datetime
import os

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='app.log')
logger = logging.getLogger(__name__)

# Constants
DB_FILE = "transactions.db"
TABLE_NAME = "transactions"
PAGE_SIZE = 100
CACHE_TTL = 60

# Page config
st.set_page_config(
    page_title="Multiple Accounts Analysis",
    page_icon="👥",
    layout="wide"
)

# Database connection pool
@st.cache_resource
def get_db_pool():
    """Create and return a database connection pool."""
    try:
        if not os.path.exists(DB_FILE):
            # Create the database file if it doesn't exist
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            logger.info(f"Created new database: {DB_FILE}")
            init_database(conn)
        else:
            conn = sqlite3.connect(DB_FILE, check_same_thread=False)
            logger.info(f"Successfully connected to database: {DB_FILE}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database {DB_FILE}: {e}")
        st.error(f"Database connection error: {e}")
        return None

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = get_db_pool()
    try:
        yield conn
    finally:
        pass  # Connection is managed by pool

def init_database(conn=None):
    """Initialize the database with necessary tables and indices."""
    if conn is None:
        conn = get_db_pool()
    
    try:
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
                timestamp TIMESTAMP NOT NULL
            );

            -- Create indices
            CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
            CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id);
            CREATE INDEX IF NOT EXISTS idx_accounts_individual ON accounts(individual_id);
        """)
        conn.commit()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        st.error(f"Database initialization error: {e}")

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
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='transactions'
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
        result = conn.execute("""
            SELECT 
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
        multi_accounts_data = pd.read_sql_query("""
            SELECT 
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

        logger.info("Starting dataframe validation")
        logger.info(f"Validating {len(df)} rows of data")
        logger.info(f"Columns present: {list(df.columns)}")
        logger.info("Data validation successful")
        
        return True, df
    except Exception as e:
        logger.error(f"Error in validate_dataframe: {str(e)}")
        return False, f"Data validation error: {str(e)}"

def save_to_database(df):
    """Save validated DataFrame to the database."""
    try:
        if df.empty:
            return False, "No data to save"
            
        logger.info(f"Starting database save with {len(df)} rows")
        
        # Check for existing transaction IDs
        with get_db_connection() as conn:
            # Use parameterized query with proper placeholder handling
            placeholders = ','.join(['?'] * len(df))
            query = f"SELECT transaction_id FROM {TABLE_NAME} WHERE transaction_id IN ({placeholders})"
            
            existing_ids_df = pd.read_sql_query(
                query,
                conn,
                params=df['transaction_id'].tolist()
            )
            
            if not existing_ids_df.empty:
                existing_ids = existing_ids_df['transaction_id'].tolist()
                logger.info(f"Found {len(existing_ids)} existing transactions")
                
                handle_duplicates = st.radio(
                    "How would you like to handle existing transactions?",
                    ["Skip existing", "Update existing", "Cancel"],
                    index=0
                )
                
                if handle_duplicates == "Cancel":
                    return False, "Operation cancelled by user"
                
                if handle_duplicates == "Skip existing":
                    # Filter out existing transactions
                    df = df[~df['transaction_id'].isin(existing_ids)]
                    if df.empty:
                        logger.info("No new transactions to save after filtering")
                        return False, "No new transactions to save after filtering existing ones"
                
                elif handle_duplicates == "Update existing":
                    # Delete existing records first
                    with get_db_connection() as conn:
                        cursor = conn.cursor()
                        placeholders = ','.join(['?'] for _ in existing_ids)
                        cursor.execute(
                            f"DELETE FROM {TABLE_NAME} WHERE transaction_id IN ({placeholders})",
                            existing_ids
                        )
                        conn.commit()
            
            logger.info(f"Saving {len(df)} transactions to database")
            
            # Save to database
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
                    logger.info("Save successful")
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Error saving to database: {str(e)}")
                    return False, f"Database error: {str(e)}"
                    
            st.cache_data.clear()
            return True, f"Successfully saved {len(df)} transactions to database"
        
        return False, "No transactions to save"
    
    except Exception as e:
        logger.error(f"Error in save_to_database: {str(e)}")
        return False, f"Error saving data: {str(e)}"

@st.cache_data(ttl=CACHE_TTL)
def get_paginated_data(page, page_size=PAGE_SIZE, date_range=None, bank_filter=None, min_accounts=1):
    """Get paginated transaction data with filters."""
    try:
        with get_db_connection() as conn:
            query_parts = [f"SELECT transaction_id, individual_id, account_id, bank_name, amount, timestamp FROM {TABLE_NAME}"]
            query_params = []
            
            where_conditions = []
            
            # Add date range filter if provided
            if date_range and date_range[0] and date_range[1]:
                where_conditions.append("date(timestamp) BETWEEN ? AND ?")
                query_params.extend([date_range[0], date_range[1]])
            
            # Add bank filter if provided
            if bank_filter:
                where_conditions.append("bank_name = ?")
                query_params.append(bank_filter)
            
            # Apply multi-account filter if min_accounts > 1
            if min_accounts > 1:
                multi_account_query = f"""
                    individual_id IN (
                        SELECT individual_id 
                        FROM (
                            SELECT individual_id, COUNT(DISTINCT account_id) as acc_count 
                            FROM {TABLE_NAME} 
                            GROUP BY individual_id
                        )
                        WHERE acc_count >= ?
                    )
                """
                where_conditions.append(multi_account_query)
                query_params.append(min_accounts)
            
            # Combine all conditions
            if where_conditions:
                query_parts.append("WHERE " + " AND ".join(where_conditions))
            
            # Add order by and pagination
            query_parts.append("ORDER BY timestamp DESC LIMIT ? OFFSET ?")
            query_params.extend([page_size, page * page_size])
            
            # Build full query
            query = " ".join(query_parts)
            
            # Get total count for pagination
            count_query_parts = [f"SELECT COUNT(*) FROM {TABLE_NAME}"]
            if where_conditions:
                count_query_parts.append("WHERE " + " AND ".join(where_conditions))
            count_query = " ".join(count_query_parts)
            
            # Execute count query
            cursor = conn.cursor()
            cursor.execute(count_query, query_params[:-2] if query_params else [])
            total_records = cursor.fetchone()[0]
            total_pages = (total_records + page_size - 1) // page_size
            
            # Execute data query
            df = pd.read_sql_query(query, conn, params=query_params, parse_dates=['timestamp'])
            return df, total_pages, total_records
    except Exception as e:
        logger.error(f"Error fetching paginated data: {e}")
        return pd.DataFrame(), 0, 0

def get_multiple_accounts_data():
    """Get data about individuals with multiple accounts."""
    try:
        with get_db_connection() as conn:
            query = """
            SELECT 
                t.individual_id,
                COUNT(DISTINCT t.account_id) as num_accounts,
                COUNT(DISTINCT t.bank_name) as num_banks,
                GROUP_CONCAT(DISTINCT t.bank_name) as banks,
                GROUP_CONCAT(DISTINCT t.account_id) as accounts,
                COUNT(t.transaction_id) as num_transactions,
                SUM(t.amount) as total_amount,
                MIN(t.timestamp) as first_transaction,
                MAX(t.timestamp) as last_transaction
            FROM transactions t
            GROUP BY t.individual_id
            HAVING num_accounts > 1
            ORDER BY num_accounts DESC, total_amount DESC
            """
            df = pd.read_sql_query(query, conn, parse_dates=['first_transaction', 'last_transaction'])
            return df
    except Exception as e:
        logger.error(f"Error fetching multiple accounts data: {e}")
        return pd.DataFrame()

def export_to_csv(df):
    """Export DataFrame to CSV."""
    if df.empty:
        st.error("No data to export")
        return
    
    csv = df.to_csv(index=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name=f"multiple_accounts_data_{timestamp}.csv",
        mime="text/csv"
    )

def main():
    """Main function for the multiple accounts analysis app."""
    st.title("👥 Multiple Accounts Analysis")
    
    # Initialize database if needed
    init_database()
    
    # Get database stats
    stats = get_db_stats()
    
    # Top metrics row
    st.markdown("### 📊 Account Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Individuals", f"{stats['unique_individuals']:,}")
    
    with col2:
        st.metric("Multi-Account Holders", f"{stats['multi_account_holders_count']:,}")
    
    with col3:
        st.metric("% with Multiple Accounts", f"{stats['percent_with_multiple_accounts']:.1f}%")
    
    with col4:
        st.metric("Avg. Accounts per Individual", f"{stats['avg_accounts']:.2f}")
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Data Upload", "🔍 Account Analysis", "📊 Visualizations", "📥 Data Export"])
    
    with tab1:
        st.header("Upload Transaction Data")
        
        # File upload widget
        uploaded_file = st.file_uploader("Upload CSV file with transaction data", type=["csv"])
        
        # Sample format
        st.markdown("""
        **Required CSV Format:**
        
        | transaction_id | individual_id | account_id | bank_name | amount | timestamp |
        | -------------- | ------------- | ---------- | --------- | ------ | --------- |
        | TX123456 | IND001 | ACC001 | Bank A | 1000.00 | 2023-01-01 12:00:00 |
        """)
        
        if uploaded_file is not None:
            try:
                # Read the CSV
                df = pd.read_csv(uploaded_file)
                st.write(f"Uploaded file: {uploaded_file.name}, {df.shape[0]} rows, {df.shape[1]} columns")
                
                # Store in session state for reuse
                if "df" not in st.session_state:
                    st.session_state.df = df
                    logger.info(f"Successfully loaded new CSV with {len(df)} rows")
                else:
                    logger.info(f"Found existing dataset in session state")
                    logger.info(f"Using previous dataset with {len(st.session_state.df)} rows")
                
                # Display the data preview
                st.subheader("Data Preview")
                st.dataframe(df.head(10))
                
                # Validate data
                valid, result = validate_dataframe(df)
                if valid:
                    st.session_state.validated_df = result
                    st.success("Data validation successful!")
                    
                    # Save data button
                    if st.button("Save Data to Database"):
                        success, message = save_to_database(st.session_state.validated_df)
                        if success:
                            st.success(message)
                            # Clear the cache to refresh metrics
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(message)
                else:
                    st.error(f"Data validation failed: {result}")
            except Exception as e:
                logger.error(f"Error processing uploaded file: {str(e)}")
                st.error(f"Error processing uploaded file: {str(e)}")
    
    with tab2:
        st.header("Multiple Accounts Analysis")
        
        # Filter settings
        st.subheader("Filter Settings")
        col1, col2 = st.columns(2)
        
        with col1:
            # Date range filter
            try:
                start_date, end_date = stats['date_range']
                if start_date and end_date:
                    start_date = datetime.strptime(start_date.split()[0], "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date.split()[0], "%Y-%m-%d").date()
                    date_range = st.date_input(
                        "Date Range",
                        value=(start_date, end_date),
                        format="YYYY-MM-DD"
                    )
                else:
                    date_range = None
            except:
                date_range = None
        
        with col2:
            # Bank filter
            try:
                with get_db_connection() as conn:
                    banks = pd.read_sql_query("SELECT DISTINCT bank_name FROM transactions", conn)['bank_name'].tolist()
                bank_filter = st.selectbox("Bank", ["All Banks"] + banks)
                if bank_filter == "All Banks":
                    bank_filter = None
            except:
                bank_filter = None
        
        # Get multiple accounts data
        multi_accounts_df = get_multiple_accounts_data()
        
        if not multi_accounts_df.empty:
            st.subheader("Individuals with Multiple Accounts")
            multi_accounts_df['duration_days'] = (multi_accounts_df['last_transaction'] - multi_accounts_df['first_transaction']).dt.days
            
            # Format display columns
            display_df = multi_accounts_df.copy()
            display_df['first_transaction'] = display_df['first_transaction'].dt.strftime('%Y-%m-%d')
            display_df['last_transaction'] = display_df['last_transaction'].dt.strftime('%Y-%m-%d')
            display_df['total_amount'] = display_df['total_amount'].apply(lambda x: f"${x:,.2f}")
            
            st.dataframe(
                display_df.rename(columns={
                    'individual_id': 'Individual ID',
                    'num_accounts': 'Accounts',
                    'num_banks': 'Banks',
                    'banks': 'Bank Names',
                    'accounts': 'Account IDs',
                    'num_transactions': 'Transactions',
                    'total_amount': 'Total Amount',
                    'first_transaction': 'First Transaction',
                    'last_transaction': 'Last Transaction',
                    'duration_days': 'Duration (days)'
                }),
                hide_index=True
            )
            
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
                            params=(selected_individual,),
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
                            
                            # Format dates and amounts
                            account_summary['First Transaction'] = account_summary['First Transaction'].dt.strftime('%Y-%m-%d')
                            account_summary['Last Transaction'] = account_summary['Last Transaction'].dt.strftime('%Y-%m-%d')
                            account_summary['Total Amount'] = account_summary['Total Amount'].apply(lambda x: f"${x:,.2f}")
                            account_summary['Avg Amount'] = account_summary['Avg Amount'].apply(lambda x: f"${x:,.2f}")
                            
                            st.dataframe(account_summary, hide_index=True)
                            
                            # Show transaction timeline
                            individual_txns['date'] = individual_txns['timestamp'].dt.date
                            daily_amounts = individual_txns.groupby(['date', 'account_id']).agg({
                                'amount': 'sum'
                            }).reset_index()
                            
                            fig = px.bar(
                                daily_amounts, 
                                x='date', 
                                y='amount', 
                                color='account_id',
                                title=f"Transaction Timeline for {selected_individual}",
                                labels={'date': 'Date', 'amount': 'Amount', 'account_id': 'Account ID'}
                            )
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Show all transactions
                            st.write("**All Transactions:**")
                            display_txns = individual_txns.copy()
                            display_txns['timestamp'] = display_txns['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                            display_txns['amount'] = display_txns['amount'].apply(lambda x: f"${x:,.2f}")
                            st.dataframe(display_txns, hide_index=True)
                            
                except Exception as e:
                    logger.error(f"Error fetching individual transactions: {str(e)}")
                    st.error(f"Error fetching data: {str(e)}")
        else:
            st.info("No individuals with multiple accounts found in the database.")
    
    with tab3:
        st.header("📊 Data Visualizations")
        
        # Only show visualizations if we have data
        if stats['total_records'] > 0:
            # Get data for visualizations
            try:
                with get_db_connection() as conn:
                    # Account distribution chart
                    account_dist = pd.read_sql_query("""
                        SELECT 
                            num_accounts,
                            COUNT(*) as count
                        FROM (
                            SELECT 
                                individual_id,
                                COUNT(DISTINCT account_id) as num_accounts
                            FROM transactions
                            GROUP BY individual_id
                        )
                        GROUP BY num_accounts
                        ORDER BY num_accounts
                    """, conn)
                    
                    # Bank distribution chart
                    bank_dist = pd.read_sql_query("""
                        SELECT 
                            bank_name,
                            COUNT(DISTINCT account_id) as num_accounts,
                            COUNT(DISTINCT individual_id) as num_individuals,
                            SUM(amount) as total_amount
                        FROM transactions
                        GROUP BY bank_name
                        ORDER BY num_accounts DESC
                    """, conn)
                    
                    # Transactions over time
                    time_dist = pd.read_sql_query("""
                        SELECT 
                            DATE(timestamp) as date,
                            COUNT(*) as num_transactions,
                            SUM(amount) as total_amount
                        FROM transactions
                        GROUP BY date
                        ORDER BY date
                    """, conn)
                    
                    time_dist['date'] = pd.to_datetime(time_dist['date'])
                    
                    # Multi-accounts over banks data
                    multi_bank_data = pd.read_sql_query("""
                        SELECT 
                            num_banks,
                            COUNT(*) as count
                        FROM (
                            SELECT 
                                individual_id,
                                COUNT(DISTINCT bank_name) as num_banks
                            FROM transactions
                            GROUP BY individual_id
                        )
                        GROUP BY num_banks
                        ORDER BY num_banks
                    """, conn)
                    
                # Create visualizations
                col1, col2 = st.columns(2)
                
                with col1:
                    # Accounts per individual distribution
                    fig = px.bar(
                        account_dist,
                        x='num_accounts',
                        y='count',
                        title="Accounts per Individual Distribution",
                        labels={'num_accounts': 'Number of Accounts', 'count': 'Number of Individuals'}
                    )
                    fig.update_layout(xaxis=dict(tickmode='linear'))
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Bank distribution
                    fig = px.bar(
                        bank_dist,
                        x='bank_name',
                        y='num_accounts',
                        title="Accounts by Bank",
                        labels={'bank_name': 'Bank', 'num_accounts': 'Number of Accounts'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Banks per individual distribution
                    fig = px.bar(
                        multi_bank_data,
                        x='num_banks',
                        y='count',
                        title="Banks per Individual Distribution",
                        labels={'num_banks': 'Number of Banks', 'count': 'Number of Individuals'}
                    )
                    fig.update_layout(xaxis=dict(tickmode='linear'))
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Transaction amount over time
                    fig = px.line(
                        time_dist,
                        x='date',
                        y='total_amount',
                        title="Transaction Amount Over Time",
                        labels={'date': 'Date', 'total_amount': 'Total Amount'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
            except Exception as e:
                logger.error(f"Error generating visualizations: {str(e)}")
                st.error(f"Error generating visualizations: {str(e)}")
        else:
            st.info("No data available for visualizations. Please upload transaction data first.")
    
    with tab4:
        st.header("Data Export")
        
        export_type = st.selectbox(
            "Select Export Type",
            ["All Transactions", "Multiple Account Holders Only", "Summary Statistics"]
        )
        
        if export_type == "All Transactions":
            try:
                page = 0
                df, _, total = get_paginated_data(page, page_size=10000)
                if not df.empty:
                    st.write(f"Exporting {len(df)} transactions (max 10,000 records)")
                    export_to_csv(df)
                else:
                    st.info("No transaction data to export.")
            except Exception as e:
                logger.error(f"Error exporting transactions: {str(e)}")
                st.error(f"Error exporting data: {str(e)}")
                
        elif export_type == "Multiple Account Holders Only":
            multi_accounts_df = get_multiple_accounts_data()
            if not multi_accounts_df.empty:
                st.write(f"Exporting data for {len(multi_accounts_df)} individuals with multiple accounts")
                export_to_csv(multi_accounts_df)
            else:
                st.info("No multiple account holders to export.")
                
        elif export_type == "Summary Statistics":
            try:
                with get_db_connection() as conn:
                    # Create summary dataframe
                    summary_data = {
                        "Metric": [
                            "Total Individuals",
                            "Total Accounts",
                            "Total Transactions",
                            "Total Amount",
                            "Multi-Account Individuals",
                            "Percentage with Multiple Accounts",
                            "Average Accounts per Individual",
                            "Date Range"
                        ],
                        "Value": [
                            stats['unique_individuals'],
                            pd.read_sql_query("SELECT COUNT(DISTINCT account_id) FROM transactions", conn).iloc[0, 0],
                            stats['total_records'],
                            f"${stats['total_amount']:,.2f}",
                            stats['multi_account_holders_count'],
                            f"{stats['percent_with_multiple_accounts']:.2f}%",
                            f"{stats['avg_accounts']:.2f}",
                            f"{stats['date_range'][0]} to {stats['date_range'][1]}" if stats['date_range'][0] else "N/A"
                        ]
                    }
                    
                    summary_df = pd.DataFrame(summary_data)
                    st.dataframe(summary_df, hide_index=True)
                    export_to_csv(summary_df)
                    
            except Exception as e:
                logger.error(f"Error exporting summary statistics: {str(e)}")
                st.error(f"Error exporting data: {str(e)}")

if __name__ == "__main__":
    main()
