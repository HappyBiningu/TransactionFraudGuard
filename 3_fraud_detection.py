import streamlit as st
import pandas as pd
import joblib
from datetime import datetime, timedelta
import sqlite3
import os
import hashlib
from typing import Optional, Tuple, Dict, Any
import logging
import tempfile
import zipfile
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
DB_FILE = "fraud_detection.db"
FRAUD_TABLE = "fraud_detection_results"
USER_TABLE = "users"
PAGE_SIZE = 50  # Records per page
MODEL_PATH = "fraud_detection_pipeline.pkl"

# Security configuration
SESSION_TIMEOUT = timedelta(minutes=30)

# Configure pandas
pd.set_option("styler.render.max_elements", 2000000)
pd.set_option("display.float_format", "{:.2f}".format)

# Database schema
SCHEMA = {
    FRAUD_TABLE: f"""
    CREATE TABLE IF NOT EXISTS {FRAUD_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE,
        individual_id TEXT,
        account_id TEXT,
        bank_name TEXT,
        amount REAL,
        daily_total REAL,
        weekly_total REAL,
        monthly_total REAL,
        n_accounts INTEGER,
        fraud_probability REAL,
        predicted_suspicious INTEGER,
        timestamp TEXT,
        processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        analyst_notes TEXT,
        status TEXT CHECK(status IN ('pending', 'reviewed', 'confirmed', 'false_positive')) DEFAULT 'pending'
    )
    """,
    USER_TABLE: f"""
    CREATE TABLE IF NOT EXISTS {USER_TABLE} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        full_name TEXT,
        role TEXT CHECK(role IN ('analyst', 'supervisor', 'admin')),
        last_login TEXT,
        is_active INTEGER DEFAULT 1
    )
    """
}

# Type aliases
DataFrame = pd.DataFrame
Styler = pd.io.formats.style.Styler

class DatabaseManager:
    """Handles all database operations with connection pooling and error handling."""
    
    def __init__(self, db_file: str = DB_FILE):
        self.db_file = db_file
        self._initialize_database()
        
    def _initialize_database(self) -> None:
        """Initialize database with required tables."""
        try:
            with self._get_connection() as conn:
                for table, schema in SCHEMA.items():
                    conn.execute(schema)
                conn.commit()
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper configuration."""
        conn = sqlite3.connect(self.db_file)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute_query(self, query: str, params: tuple = (), fetch: bool = False) -> Any:
        """Execute a SQL query with error handling."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor.fetchall() if fetch else None
        except sqlite3.Error as e:
            logger.error(f"Database error: {str(e)}")
            raise
    
    def save_results(self, df: DataFrame) -> bool:
        """Save fraud detection results to database."""
        try:
            with self._get_connection() as conn:
                df.to_sql(FRAUD_TABLE, conn, if_exists="append", index=False)
                return True
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            return False
    
    def get_paginated_results(self, page: int, filters: dict = None) -> Tuple[DataFrame, int]:
        """Get paginated results with optional filters."""
        base_query = f"SELECT * FROM {FRAUD_TABLE}"
        count_query = f"SELECT COUNT(*) FROM {FRAUD_TABLE}"
        
        where_clauses = []
        params = []
        
        if filters:
            if filters.get("date_range"):
                start_date, end_date = filters["date_range"]
                where_clauses.append("date(timestamp) BETWEEN ? AND ?")
                params.extend([start_date, end_date])
            if filters.get("status"):
                where_clauses.append("status = ?")
                params.append(filters["status"])
            if filters.get("suspicious") is not None:
                where_clauses.append("predicted_suspicious = ?")
                params.append(int(filters["suspicious"]))
        
        if where_clauses:
            where_statement = " WHERE " + " AND ".join(where_clauses)
            base_query += where_statement
            count_query += where_statement
        
        # Add sorting and pagination
        base_query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([PAGE_SIZE, page * PAGE_SIZE])
        
        try:
            with self._get_connection() as conn:
                total_records = conn.execute(count_query, params[:-2]).fetchone()[0]
                df = pd.read_sql_query(base_query, conn, params=params)
                total_pages = (total_records + PAGE_SIZE - 1) // PAGE_SIZE
                return df, total_pages
        except Exception as e:
            logger.error(f"Error fetching paginated results: {str(e)}")
            return pd.DataFrame(), 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and metrics."""
        stats = {}
        try:
            with self._get_connection() as conn:
                # Basic counts
                stats["total_records"] = conn.execute(f"SELECT COUNT(*) FROM {FRAUD_TABLE}").fetchone()[0]
                stats["suspicious_count"] = conn.execute(
                    f"SELECT COUNT(*) FROM {FRAUD_TABLE} WHERE predicted_suspicious = 1"
                ).fetchone()[0]
                
                # Date range
                min_max = conn.execute(
                    f"SELECT MIN(timestamp), MAX(timestamp) FROM {FRAUD_TABLE}"
                ).fetchone()
                stats["date_range"] = min_max
                
                # Status distribution
                status_counts = conn.execute(
                    f"SELECT status, COUNT(*) as count FROM {FRAUD_TABLE} GROUP BY status"
                ).fetchall()
                stats["status_distribution"] = dict(status_counts)
                
                # Recent activity
                recent_activity = conn.execute(
                    f"SELECT strftime('%Y-%m-%d', processed_at) as day, COUNT(*) as count "
                    f"FROM {FRAUD_TABLE} "
                    f"GROUP BY day ORDER BY day DESC LIMIT 7"
                ).fetchall()
                stats["recent_activity"] = recent_activity
                
                return stats
        except Exception as e:
            logger.error(f"Error getting database stats: {str(e)}")
            return {}

class FraudDetector:
    """Handles fraud detection model loading and predictions."""
    
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        self.pipeline = self._load_model()
        
    def _load_model(self) -> Optional[Dict[str, Any]]:
        """Load the fraud detection pipeline from disk."""
        try:
            if not os.path.exists(self.model_path):
                raise FileNotFoundError(f"Model file not found at {self.model_path}")
            
            pipeline = joblib.load(self.model_path)
            if not all(key in pipeline for key in ["model", "scaler", "label_encoder"]):
                raise ValueError("Invalid pipeline structure")
                
            return pipeline
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            st.error(f"Failed to load fraud detection model: {str(e)}")
            return None
    
    def preprocess_data(self, df: DataFrame) -> Optional[DataFrame]:
        """Preprocess transaction data for fraud detection."""
        required_columns = {"transaction_id", "individual_id", "account_id", "bank_name", "amount", "timestamp"}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise ValueError(f"Missing required columns: {missing}")
        
        try:
            # Convert timestamp and extract temporal features
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df["date"] = df["timestamp"].dt.date
            df["hour"] = df["timestamp"].dt.hour
            df["weekday"] = df["timestamp"].dt.weekday
            df["week"] = df["timestamp"].dt.isocalendar().week
            df["month"] = df["timestamp"].dt.month
            
            # Transaction aggregations
            df["daily_total"] = df.groupby(["individual_id", "date"])["amount"].transform("sum")
            df["weekly_total"] = df.groupby(["individual_id", "week"])["amount"].transform("sum")
            df["monthly_total"] = df.groupby(["individual_id", "month"])["amount"].transform("sum")
            df["daily_txn_count"] = df.groupby(["individual_id", "date"])["transaction_id"].transform("count")
            df["weekly_txn_count"] = df.groupby(["individual_id", "week"])["transaction_id"].transform("count")
            df["monthly_txn_count"] = df.groupby(["individual_id", "month"])["transaction_id"].transform("count")
            
            # Account features
            df["n_accounts"] = df.groupby("individual_id")["account_id"].transform("nunique")
            
            # Threshold flags
            df["exceeds_daily"] = (df["daily_total"] > 1000).astype(int)
            df["exceeds_weekly"] = (df["weekly_total"] > 5000).astype(int)
            df["exceeds_monthly"] = (df["monthly_total"] > 10000).astype(int)
            
            # Normalized amounts
            df["avg_amount_per_account_daily"] = df["daily_total"] / df["n_accounts"].replace(0, 1)
            df["avg_amount_per_account_weekly"] = df["weekly_total"] / df["n_accounts"].replace(0, 1)
            df["avg_amount_per_account_monthly"] = df["monthly_total"] / df["n_accounts"].replace(0, 1)
            
            return df
        except Exception as e:
            logger.error(f"Error preprocessing data: {str(e)}")
            raise
    
    def predict(self, df: DataFrame) -> Optional[DataFrame]:
        """Make fraud predictions on processed transaction data."""
        if self.pipeline is None:
            return None
            
        try:
            # Prepare feature matrix with exact column names
            features = [
                "amount", "bank_name", "hour", "weekday", 
                "daily_total", "weekly_total", "monthly_total",
                "daily_txn_count", "weekly_txn_count", "monthly_txn_count",
                "n_accounts", "exceeds_daily", "exceeds_weekly", "exceeds_monthly",
                "avg_amount_per_account_daily", "avg_amount_per_account_weekly", 
                "avg_amount_per_account_monthly"
            ]

            # Create feature matrix with correct column order
            X = pd.DataFrame()
            for feature in features:
                X[feature] = df[feature]
            
            # Encode bank names after creating the feature matrix
            X["bank_name"] = self.pipeline["label_encoder"].transform(X["bank_name"])
            
            # Scale numeric features
            numeric_cols = [
                "amount", "daily_total", "weekly_total", "monthly_total",
                "daily_txn_count", "weekly_txn_count", "monthly_txn_count",
                "n_accounts", "avg_amount_per_account_daily",
                "avg_amount_per_account_weekly", "avg_amount_per_account_monthly"
            ]
            X[numeric_cols] = self.pipeline["scaler"].transform(X[numeric_cols])
            
            # Make predictions
            y_prob = self.pipeline["model"].predict_proba(X)[:, 1]
            y_pred = (y_prob >= 0.3).astype(int)  # Using 0.3 threshold
            
            # Prepare results
            results = pd.DataFrame({
                "transaction_id": df["transaction_id"],
                "individual_id": df["individual_id"],
                "account_id": df["account_id"],
                "bank_name": df["bank_name"],
                "amount": df["amount"],
                "daily_total": df["daily_total"].round(2),
                "weekly_total": df["weekly_total"].round(2),
                "monthly_total": df["monthly_total"].round(2),
                "n_accounts": df["n_accounts"],
                "fraud_probability": y_prob.round(4),
                "predicted_suspicious": y_pred,
                "timestamp": df["timestamp"].astype(str)
            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            raise

class FraudDetectionUI:
    """Handles the Streamlit user interface for the fraud detection system."""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.detector = FraudDetector()
        self._initialize_session_state()
        self._setup_page_config()
        
    def _initialize_session_state(self) -> None:
        """Initialize Streamlit session state variables."""
        if "current_page" not in st.session_state:
            st.session_state.current_page = 0
        if "uploaded_file" not in st.session_state:
            st.session_state.uploaded_file = None
        if "show_delete_confirm" not in st.session_state:
            st.session_state.show_delete_confirm = False
        if "filters" not in st.session_state:
            st.session_state.filters = {}
    
    def _setup_page_config(self) -> None:
        """Configure Streamlit page settings."""
        st.set_page_config(
            page_title="Fraud Detection System",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Inject custom CSS
        self._inject_custom_css()
    
    def _inject_custom_css(self) -> None:
        """Inject custom CSS styles."""
        st.markdown("""
        <style>
            /* Main styles */
            .main {
                max-width: 1200px;
                padding: 2rem;
            }
            
            /* Headers */
            .section-header {
                font-size: 1.4rem;
                font-weight: 600;
                margin-top: 1.8rem;
                margin-bottom: 0.8rem;
                color: #2c3e50;
                border-bottom: 1px solid #eee;
                padding-bottom: 0.5rem;
            }
            
            /* Fraud alerts */
            .fraud-alert {
                background-color: #ffebee;
                color: #c62828;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
                border-left: 4px solid #c62828;
            }
            
            .safe-transaction {
                background-color: #e8f5e9;
                color: #2e7d32;
                padding: 1rem;
                border-radius: 8px;
                margin: 1rem 0;
                border-left: 4px solid #2e7d32;
            }
            
            /* Cards and boxes */
            .metric-card {
                background: white;
                border-radius: 10px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 1rem;
            }
            
            .info-box {
                background: #e3f2fd;
                border-radius: 8px;
                padding: 1rem;
                margin: 1rem 0;
                border-left: 4px solid #2196f3;
            }
            
            /* Buttons */
            .stButton>button {
                border-radius: 8px;
                padding: 0.5rem 1rem;
            }
            
            /* Dataframe styling */
            .dataframe {
                width: 100%;
            }
            
            /* Tabs */
            .stTabs [role="tablist"] {
                margin-bottom: 1rem;
            }
            
            /* Responsive adjustments */
            @media (max-width: 768px) {
                .main {
                    padding: 1rem;
                }
            }
        </style>
        """, unsafe_allow_html=True)
    
    def _show_file_uploader(self) -> Optional[DataFrame]:
        """Show file uploader and return uploaded DataFrame."""
        st.markdown("### Upload Transaction Data")
        st.info("""
        Upload a CSV file with the following columns:
        - `transaction_id`: Unique transaction identifier
        - `individual_id`: Customer/individual identifier
        - `account_id`: Account number/identifier
        - `bank_name`: Name of the bank/institution
        - `amount`: Transaction amount
        - `timestamp`: Transaction timestamp (YYYY-MM-DD HH:MM:SS)
        """)
        
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            key="file_uploader"
        )
        
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                
                # Validate required columns
                required_cols = {
                    "transaction_id", "individual_id", "account_id", 
                    "bank_name", "amount", "timestamp"
                }
                missing_cols = required_cols - set(df.columns)
                
                if missing_cols:
                    st.error(f"Missing required columns: {', '.join(missing_cols)}")
                    return None
                
                # Sample data preview
                with st.expander("Preview uploaded data"):
                    st.dataframe(df.head())
                    
                return df
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
                logger.error(f"File upload error: {str(e)}")
                return None
        return None
    
    def _show_manual_entry_form(self) -> Optional[DataFrame]:
        """Show manual transaction entry form and return DataFrame."""
        st.markdown("### Manual Transaction Entry")
        
        with st.form("manual_entry"):
            col1, col2 = st.columns(2)
            
            with col1:
                transaction_id = st.text_input(
                    "Transaction ID",
                    value=f"TXN_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    help="Unique transaction identifier"
                )
                individual_id = st.text_input(
                    "Individual ID",
                    value="IND_001",
                    help="Customer/individual identifier"
                )
                account_id = st.text_input(
                    "Account ID",
                    value="ACC_001",
                    help="Account number/identifier"
                )
            
            with col2:
                bank_name = st.text_input(
                    "Bank Name",
                    value="Bank_A",
                    help="Name of the bank/institution"
                )
                amount = st.number_input(
                    "Amount",
                    min_value=0.0,
                    value=100.0,
                    step=10.0,
                    format="%.2f",
                    help="Transaction amount"
                )
                timestamp = st.text_input(
                    "Timestamp",
                    value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    help="Transaction timestamp (YYYY-MM-DD HH:MM:SS)"
                )
            
            submitted = st.form_submit_button("Analyze Transaction")
            
            if submitted:
                try:
                    df = pd.DataFrame({
                        "transaction_id": [transaction_id],
                        "individual_id": [individual_id],
                        "account_id": [account_id],
                        "bank_name": [bank_name],
                        "amount": [amount],
                        "timestamp": [timestamp]
                    })
                    return df
                except Exception as e:
                    st.error(f"Error creating transaction: {str(e)}")
                    logger.error(f"Manual entry error: {str(e)}")
                    return None
        return None
    
    def _style_results(self, df: DataFrame) -> Styler:
        """Apply styling to fraud detection results."""
        def highlight_row(row):
            if row["predicted_suspicious"] == 1:
                return ["background-color: #ffebee"] * len(row)
            return [""] * len(row)
        
        def color_probability(val):
            color = "#c62828" if val >= 0.3 else "#2e7d32"
            return f"color: {color}; font-weight: bold"
        
        styled_df = df.style.apply(highlight_row, axis=1)
        styled_df = styled_df.applymap(color_probability, subset=["fraud_probability"])
        
        # Format numeric columns
        numeric_cols = ["amount", "daily_total", "weekly_total", "monthly_total"]
        styled_df = styled_df.format("{:.2f}", subset=numeric_cols)
        
        return styled_df
    
    def _show_analysis_results(self, results: DataFrame) -> None:
        """Display fraud detection results with visualizations."""
        if results.empty:
            st.warning("No results to display")
            return
        
        # Calculate summary statistics
        total_count = len(results)
        suspicious_count = results["predicted_suspicious"].sum()
        suspicious_percent = (suspicious_count / total_count * 100) if total_count > 0 else 0
        avg_prob = results["fraud_probability"].mean()
        
        # Display summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Transactions", total_count)
        with col2:
            st.metric("Suspicious Transactions", f"{suspicious_count} ({suspicious_percent:.1f}%)")
        with col3:
            st.metric("Average Fraud Probability", f"{avg_prob:.2%}")
        
        # Display styled results
        st.markdown("### Detailed Results")
        st.dataframe(
            self._style_results(results),
            use_container_width=True,
            height=600
        )
        
        # Add export options
        self._show_export_options(results)
    
    def _show_export_options(self, df: DataFrame) -> None:
        """Show options for exporting results."""
        st.markdown("### Export Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Export full results
            csv_full = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Download Full Results",
                data=csv_full,
                file_name="fraud_detection_results.csv",
                mime="text/csv",
                help="Download all analysis results as CSV"
            )
        
        with col2:
            # Export suspicious only
            suspicious = df[df["predicted_suspicious"] == 1]
            if not suspicious.empty:
                csv_suspicious = suspicious.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Download Suspicious Only",
                    data=csv_suspicious,
                    file_name="suspicious_transactions.csv",
                    mime="text/csv",
                    help="Download only suspicious transactions"
                )
            else:
                st.button(
                    "📥 Download Suspicious Only",
                    disabled=True,
                    help="No suspicious transactions to download"
                )
        
        with col3:
            # Export as Excel
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="All Results")
                if not suspicious.empty:
                    suspicious.to_excel(writer, index=False, sheet_name="Suspicious Only")
            excel_buffer.seek(0)
            
            st.download_button(
                label="📊 Download Excel Report",
                data=excel_buffer,
                file_name="fraud_detection_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                help="Download comprehensive Excel report"
            )
    
    def _show_historical_results(self) -> None:
        """Display paginated historical results with filtering options."""
        st.markdown("### Historical Analysis Results")
        
        # Filter controls
        with st.expander("🔍 Filter Options"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                date_range = st.date_input(
                    "Date Range",
                    value=[],
                    max_value=datetime.today(),
                    help="Filter by transaction date range"
                )
                
            with col2:
                status_filter = st.selectbox(
                    "Status",
                    options=["All", "pending", "reviewed", "confirmed", "false_positive"],
                    help="Filter by review status"
                )
                
            with col3:
                suspicious_filter = st.selectbox(
                    "Suspicious Flag",
                    options=["All", "Suspicious Only", "Normal Only"],
                    help="Filter by suspicious flag"
                )
            
            apply_filters = st.button("Apply Filters")
            
            if apply_filters:
                st.session_state.filters = {}
                
                if len(date_range) == 2:
                    st.session_state.filters["date_range"] = (
                        date_range[0].strftime("%Y-%m-%d"),
                        date_range[1].strftime("%Y-%m-%d")
                    )
                
                if status_filter != "All":
                    st.session_state.filters["status"] = status_filter
                
                if suspicious_filter == "Suspicious Only":
                    st.session_state.filters["suspicious"] = True
                elif suspicious_filter == "Normal Only":
                    st.session_state.filters["suspicious"] = False
        
        # Load and display data
        df, total_pages = self.db.get_paginated_results(
            st.session_state.current_page,
            st.session_state.filters
        )
        
        if not df.empty:
            # Pagination controls
            col1, col2, col3 = st.columns([2, 4, 2])
            
            with col1:
                if st.session_state.current_page > 0 and st.button("⬅️ Previous"):
                    st.session_state.current_page -= 1
                    st.experimental_rerun()
            
            with col2:
                st.write(f"Page {st.session_state.current_page + 1} of {total_pages}")
            
            with col3:
                if st.session_state.current_page < total_pages - 1 and st.button("Next ➡️"):
                    st.session_state.current_page += 1
                    st.experimental_rerun()
            
            # Display data with editing options
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                height=600,
                column_config={
                    "status": st.column_config.SelectboxColumn(
                        "Status",
                        help="Update review status",
                        options=["pending", "reviewed", "confirmed", "false_positive"],
                        required=True
                    ),
                    "analyst_notes": st.column_config.TextColumn(
                        "Notes",
                        help="Add analyst notes",
                        max_chars=200
                    )
                },
                disabled=["transaction_id", "individual_id", "account_id", "amount",
                         "fraud_probability", "predicted_suspicious", "timestamp"]
            )
            
            # Save edits
            if st.button("💾 Save Changes"):
                try:
                    with self.db._get_connection() as conn:
                        for _, row in edited_df.iterrows():
                            conn.execute(
                                f"UPDATE {FRAUD_TABLE} SET status = ?, analyst_notes = ? WHERE id = ?",
                                (row["status"], row["analyst_notes"], row["id"])
                            )  # Added missing closing parenthesis here
                        conn.commit()
                    st.success("Changes saved successfully!")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error saving changes: {str(e)}")
            
            # Show record count
            start_record = st.session_state.current_page * PAGE_SIZE + 1
            end_record = min((st.session_state.current_page + 1) * PAGE_SIZE, len(df))
            st.info(f"Showing records {start_record}-{end_record} of {len(df)} total")
        else:
            st.warning("No historical data found matching your criteria")
    
    def _show_database_management(self) -> None:
        """Show database management interface."""
        st.markdown("### Database Management")
        
        # Show database statistics
        stats = self.db.get_database_stats()
        if stats:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Records", f"{stats['total_records']:,}")
            
            with col2:
                st.metric("Suspicious Transactions", f"{stats['suspicious_count']:,}")
            
            with col3:
                if stats["date_range"][0] and stats["date_range"][1]:
                    date_range = f"{stats['date_range'][0][:10]} to {stats['date_range'][1][:10]}"
                    st.metric("Date Range", date_range)
            
            with col4:
                st.metric("Most Recent", stats["date_range"][1][:10] if stats["date_range"][1] else "N/A")
        
        st.markdown("---")
        
        # Backup and restore
        st.markdown("#### Backup & Restore")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Create Backup"):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
                        with open(DB_FILE, "rb") as f:
                            tmp.write(f.read())
                        tmp_path = tmp.name
                    
                    with open(tmp_path, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Backup",
                            data=f,
                            file_name=f"fraud_detection_backup_{datetime.now().strftime('%Y%m%d')}.db",
                            mime="application/x-sqlite3"
                        )
                    os.unlink(tmp_path)
                except Exception as e:
                    st.error(f"Error creating backup: {str(e)}")
        
        with col2:
            uploaded_backup = st.file_uploader(
                "Restore from backup",
                type=["db", "sqlite", "sqlite3"],
                accept_multiple_files=False,
                key="db_uploader"
            )
            
            if uploaded_backup and st.button("🔄 Restore Database", disabled=not uploaded_backup):
                try:
                    with open(DB_FILE, "wb") as f:
                        f.write(uploaded_backup.getvalue())
                    st.success("Database restored successfully! Please refresh the page.")
                except Exception as e:
                    st.error(f"Error restoring database: {str(e)}")
        
        st.markdown("---")
        
        # Data deletion
        st.markdown("#### Data Deletion")
        st.warning("⚠️ These actions are irreversible. Proceed with caution.")
        
        delete_option = st.radio(
            "Select deletion scope:",
            ["All Data", "By Date Range", "By Status", "Suspicious Only"],
            horizontal=True
        )
        
        if delete_option == "By Date Range":
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start Date")
            with col2:
                end_date = st.date_input("End Date")
            
            criteria = f"date(timestamp) BETWEEN '{start_date}' AND '{end_date}'"
            description = f"all transactions between {start_date} and {end_date}"
        
        elif delete_option == "By Status":
            status = st.selectbox("Select status to delete", ["pending", "reviewed", "confirmed", "false_positive"])
            criteria = f"status = '{status}'"
            description = f"all {status} transactions"
        
        elif delete_option == "Suspicious Only":
            criteria = "predicted_suspicious = 1"
            description = "all suspicious transactions"
        else:
            criteria = None
            description = "ALL transaction data"
        
        # Confirmation dialog
        if not st.session_state.show_delete_confirm:
            if st.button(f"🗑️ Delete {description}", key="delete_init"):
                st.session_state.show_delete_confirm = True
                st.session_state.delete_criteria = criteria
                st.session_state.delete_description = description
                st.experimental_rerun()
        
        if st.session_state.show_delete_confirm:
            st.error(f"⚠️ Are you sure you want to delete {st.session_state.delete_description}? This cannot be undone!")
            
            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("✔️ Confirm Deletion", type="primary"):
                    result = self.db.execute_query(
                        f"DELETE FROM {FRAUD_TABLE} WHERE {st.session_state.delete_criteria}" 
                        if st.session_state.delete_criteria 
                        else f"DELETE FROM {FRAUD_TABLE}"
                    )
                    st.success(f"Deleted {result.rowcount if result else 'unknown'} records")
                    st.session_state.show_delete_confirm = False
                    st.experimental_rerun()
            
            with col2:
                if st.button("❌ Cancel"):
                    st.session_state.show_delete_confirm = False
                    st.experimental_rerun()
    
    def _show_analysis_tab(self) -> None:
        """Show the transaction analysis tab."""
        st.markdown('<div class="section-header">1️⃣ Analyze Transactions</div>', unsafe_allow_html=True)
        
        input_method = st.radio(
            "Select input method:",
            ["Upload CSV", "Manual Entry"],
            horizontal=True
        )
        
        if input_method == "Upload CSV":
            df = self._show_file_uploader()
        else:
            df = self._show_manual_entry_form()
        
        if df is not None:
            with st.spinner("🔍 Analyzing transactions..."):
                try:
                    processed_df = self.detector.preprocess_data(df)
                    results = self.detector.predict(processed_df)
                    
                    if results is not None:
                        st.success("Analysis completed successfully!")
                        self._show_analysis_results(results)
                        
                        # Save to database option
                        if st.button("💾 Save Results to Database"):
                            if self.db.save_results(results):
                                st.success("Results saved to database!")
                            else:
                                st.error("Failed to save results to database")
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
                    logger.error(f"Analysis error: {str(e)}", exc_info=True)
    
    def _show_help_section(self) -> None:
        """Show help and documentation section."""
        with st.expander("📖 Documentation & Help"):
            st.markdown("""
            ## Fraud Detection System Documentation
            
            ### Overview
            This system helps identify potentially fraudulent financial transactions 
            using machine learning. It analyzes transaction patterns and flags 
            suspicious activity based on:
            - Transaction amounts and frequencies
            - Account behavior patterns
            - Temporal patterns
            
            ### How to Use
            
            **1. Analyze Transactions**
            - **Upload CSV**: Upload a CSV file with transaction data
            - **Manual Entry**: Enter transaction details manually
            - View analysis results and save to database
            
            **2. Historical Results**
            - View previously analyzed transactions
            - Filter and search through records
            - Update status and add analyst notes
            
            **3. Database Management**
            - View database statistics
            - Create backups and restore data
            - Delete records (with caution)
            
            ### Data Requirements
            CSV files must contain these columns:
            - `transaction_id`: Unique identifier
            - `individual_id`: Customer ID
            - `account_id`: Account number
            - `bank_name`: Bank/institution name
            - `amount`: Transaction amount
            - `timestamp`: Transaction date/time
            
            ### Model Information
            - **Algorithm**: Random Forest Classifier
            - **Threshold**: 30% probability for flagging
            - **Features**: Transaction amounts, frequencies, patterns
            """)
    
    def run(self) -> None:
        """Run the Streamlit application."""
        st.title("🔍 Advanced Fraud Detection System")
        st.markdown("""
        Detect suspicious financial transactions using machine learning. 
        Upload transaction data or analyze manually.
        """)
        
        # Main tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "Analyze Transactions", 
            "Historical Results", 
            "Database", 
            "Help"
        ])
        
        with tab1:
            self._show_analysis_tab()
        
        with tab2:
            self._show_historical_results()
        
        with tab3:
            self._show_database_management()
        
        with tab4:
            self._show_help_section()

if __name__ == "__main__":
    ui = FraudDetectionUI()
    ui.run()