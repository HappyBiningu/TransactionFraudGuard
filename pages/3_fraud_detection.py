import streamlit as st
import pandas as pd
import joblib
from datetime import datetime, timedelta
import sqlite3
import os
import sys
import hashlib
from typing import Optional, Tuple, Dict, Any
import logging
import tempfile
import zipfile
import io
import plotly.express as px
import plotly.graph_objects as go
import uuid

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
DB_FILE = "fraud_detection.db"
FRAUD_TABLE = "fraud_detection_results"
USER_TABLE = "users"
PAGE_SIZE = 50  # Records per page
MODEL_PATH = "fraud_detection_pipeline.pkl"

# Configure page
st.set_page_config(
    page_title="Fraud Detection System",
    page_icon="🛡️",
    layout="wide"
)

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
# Define a simple class for styling, as pd.io.formats.style.Styler is not available
class SimpleStyler:
    def __init__(self, df):
        self.df = df
        
    def apply(self, func, axis=1):
        return self
        
    def format(self, format_dict):
        return self

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
            logger.info("Database initialized successfully")
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
                total_records = conn.execute(count_query, params[:-2] if params else []).fetchone()[0]
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
                stats["date_range"] = (min_max[0], min_max[1]) if min_max else (None, None)
                
                # Status distribution
                status_counts = conn.execute(
                    f"SELECT status, COUNT(*) as count FROM {FRAUD_TABLE} GROUP BY status"
                ).fetchall()
                stats["status_distribution"] = {row[0]: row[1] for row in status_counts}
                
                # Recent activity
                recent_activity = conn.execute(
                    f"SELECT strftime('%Y-%m-%d', processed_at) as day, COUNT(*) as count "
                    f"FROM {FRAUD_TABLE} "
                    f"GROUP BY day ORDER BY day DESC LIMIT 7"
                ).fetchall()
                stats["recent_activity"] = {row[0]: row[1] for row in recent_activity}
                
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
                logger.warning(f"Model file not found at {self.model_path}")
                return None
            
            pipeline = joblib.load(self.model_path)
            if not all(key in pipeline for key in ["model", "scaler", "label_encoder"]):
                logger.error("Invalid pipeline structure")
                return None
                
            logger.info("Model loaded successfully")
            return pipeline
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return None
    
    def preprocess_data(self, df: DataFrame) -> DataFrame:
        """Preprocess transaction data for fraud detection."""
        required_columns = {"transaction_id", "individual_id", "account_id", "bank_name", "amount", "timestamp"}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            logger.error(f"Missing required columns: {missing}")
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
            
            logger.info(f"Preprocessed {len(df)} transactions")
            return df
        except Exception as e:
            logger.error(f"Error preprocessing data: {str(e)}")
            raise
    
    def predict(self, df: DataFrame) -> DataFrame:
        """Make fraud predictions on processed transaction data."""
        if self.pipeline is None:
            st.error("Fraud detection model not loaded. Please ensure model file exists.")
            return df
            
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
                if feature in df.columns:
                    X[feature] = df[feature]
                else:
                    logger.error(f"Missing required feature: {feature}")
                    st.error(f"Missing required feature: {feature}")
                    return df
            
            # Encode bank names after creating the feature matrix
            try:
                X["bank_name"] = self.pipeline["label_encoder"].transform(X["bank_name"])
            except ValueError as e:
                logger.warning(f"Error encoding bank names: {str(e)}")
                # Handle unknown bank names by mapping to the most common category
                # Or you could add a special "unknown" category in the encoder
                X["bank_name"] = 0  # Default to first category for unknown banks
            
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
            
            # Add predictions to original dataframe
            results = df.copy()
            results["fraud_probability"] = y_prob
            results["predicted_suspicious"] = y_pred
            
            logger.info(f"Made predictions for {len(df)} transactions. Found {y_pred.sum()} suspicious transactions.")
            return results
        except Exception as e:
            logger.error(f"Error making predictions: {str(e)}")
            st.error(f"Error making predictions: {str(e)}")
            # Return original dataframe with empty prediction columns
            results = df.copy()
            results["fraud_probability"] = None
            results["predicted_suspicious"] = None
            return results

def style_dataframe(df):
    """Add styling to the results dataframe."""
    if df is None or df.empty or "predicted_suspicious" not in df.columns:
        return df
    
    # For now, just return the dataframe without styling
    # This is a simplification to avoid pandas styling issues
    return df

def convert_df_to_csv(df: DataFrame) -> str:
    """Convert DataFrame to CSV string."""
    return df.to_csv(index=False).encode('utf-8')

def export_to_excel(df: DataFrame) -> bytes:
    """Export DataFrame to Excel bytes."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Fraud Detection Results', index=False)
    return output.getvalue()

def create_summary_report(df: DataFrame) -> DataFrame:
    """Create a summary report of fraud detection results."""
    if df.empty:
        return pd.DataFrame()
    
    # Basic counts
    total_transactions = len(df)
    suspicious_count = df["predicted_suspicious"].sum()
    suspicious_percent = (suspicious_count / total_transactions) * 100 if total_transactions > 0 else 0
    
    # Aggregate by individual
    individual_summary = df.groupby("individual_id").agg({
        "transaction_id": "count",
        "amount": "sum",
        "predicted_suspicious": "sum",
        "fraud_probability": "mean"
    }).reset_index()
    
    individual_summary.columns = [
        "Individual ID", 
        "Transaction Count", 
        "Total Amount", 
        "Suspicious Transactions",
        "Average Risk Score"
    ]
    
    # Format the summary DataFrame
    individual_summary["Suspicious Percent"] = (individual_summary["Suspicious Transactions"] / 
                                               individual_summary["Transaction Count"]) * 100
    
    individual_summary["Total Amount"] = individual_summary["Total Amount"].apply(lambda x: f"${x:,.2f}")
    individual_summary["Average Risk Score"] = individual_summary["Average Risk Score"].apply(lambda x: f"{x:.2%}")
    individual_summary["Suspicious Percent"] = individual_summary["Suspicious Percent"].apply(lambda x: f"{x:.1f}%")
    
    return individual_summary

def main():
    """Main application function."""
    st.title("🛡️ Fraud Detection System")
    
    # Initialize managers
    db_manager = DatabaseManager()
    fraud_detector = FraudDetector()
    
    # Check if model is loaded
    if fraud_detector.pipeline is None:
        st.warning(f"⚠️ Model not found at {MODEL_PATH}. Some functionality may be limited.")
    
    # Main navigation
    tabs = st.tabs(["Dashboard", "Upload Data", "Manual Analysis", "Results History", "Export"])
    
    # Dashboard tab
    with tabs[0]:
        st.header("📊 Fraud Detection Dashboard")
        
        # Get database stats
        stats = db_manager.get_database_stats()
        
        if stats:
            # Top metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Transactions", f"{stats['total_records']:,}")
            
            with col2:
                st.metric(
                    "Suspicious Transactions", 
                    f"{stats['suspicious_count']:,}",
                    f"{stats['suspicious_count']/stats['total_records']*100:.1f}%" if stats['total_records'] > 0 else "0%"
                )
            
            with col3:
                pending = stats["status_distribution"].get("pending", 0)
                st.metric("Pending Review", f"{pending:,}")
            
            with col4:
                confirmed = stats["status_distribution"].get("confirmed", 0)
                st.metric("Confirmed Fraud", f"{confirmed:,}")
            
            # Create visualizations
            if stats["total_records"] > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    # Status distribution pie chart
                    status_data = pd.DataFrame({
                        "Status": list(stats["status_distribution"].keys()),
                        "Count": list(stats["status_distribution"].values())
                    })
                    
                    fig = px.pie(
                        status_data, 
                        values="Count", 
                        names="Status", 
                        title="Transaction Status Distribution",
                        color_discrete_map={
                            "pending": "#FFA500",
                            "reviewed": "#1E88E5",
                            "confirmed": "#FF0000",
                            "false_positive": "#4CAF50"
                        }
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Recent activity line chart
                    if stats["recent_activity"]:
                        activity_data = pd.DataFrame({
                            "Date": list(stats["recent_activity"].keys()),
                            "Transactions": list(stats["recent_activity"].values())
                        })
                        activity_data["Date"] = pd.to_datetime(activity_data["Date"])
                        activity_data = activity_data.sort_values("Date")
                        
                        fig = px.line(
                            activity_data,
                            x="Date",
                            y="Transactions",
                            title="Recent Transaction Activity"
                        )
                        st.plotly_chart(fig, use_container_width=True)
            
            # Recent suspicious transactions
            st.subheader("Recent Suspicious Transactions")
            recent_suspicious, _ = db_manager.get_paginated_results(0, {"suspicious": 1})
            
            if not recent_suspicious.empty:
                # Format for display
                display_cols = [
                    "transaction_id", "individual_id", "account_id", "bank_name", 
                    "amount", "fraud_probability", "timestamp", "status"
                ]
                
                recent_display = recent_suspicious[display_cols].copy()
                recent_display["timestamp"] = pd.to_datetime(recent_display["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                
                st.dataframe(style_dataframe(recent_display))
            else:
                st.info("No suspicious transactions found in the database.")
        else:
            st.info("No transaction data available in the database. Upload data to start analysis.")
    
    # Upload Data tab
    with tabs[1]:
        st.header("📤 Upload Transaction Data")
        
        # File uploader
        uploaded_file = st.file_uploader("Upload CSV file with transaction data", type=["csv"])
        
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
                st.write(f"Uploaded file contains {len(df)} transactions")
                
                # Show data preview
                st.subheader("Data Preview")
                st.dataframe(df.head(5))
                
                # Process button
                if st.button("Process Transactions for Fraud Detection"):
                    with st.spinner("Processing transactions..."):
                        # Preprocess data
                        processed_df = fraud_detector.preprocess_data(df)
                        
                        # Make predictions
                        results_df = fraud_detector.predict(processed_df)
                        
                        # Store results in session state
                        st.session_state.results_df = results_df
                        
                        # Display results summary
                        suspicious_count = results_df["predicted_suspicious"].sum()
                        st.success(f"Processing complete! Found {suspicious_count} suspicious transactions out of {len(results_df)}.")
                        
                        # Show results
                        st.subheader("Detection Results")
                        
                        # Summary metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Transactions", len(results_df))
                        with col2:
                            st.metric("Suspicious Transactions", suspicious_count)
                        with col3:
                            st.metric(
                                "Suspicious Percentage", 
                                f"{suspicious_count/len(results_df)*100:.1f}%" if len(results_df) > 0 else "0%"
                            )
                        
                        # Show suspicious transactions
                        if suspicious_count > 0:
                            st.subheader("Suspicious Transactions")
                            suspicious_df = results_df[results_df["predicted_suspicious"] == 1]
                            
                            # Select columns for display
                            display_cols = [
                                "transaction_id", "individual_id", "account_id", "bank_name", 
                                "amount", "daily_total", "n_accounts", "fraud_probability"
                            ]
                            st.dataframe(style_dataframe(suspicious_df[display_cols]))
                        
                        # Save to database button
                        if st.button("Save Results to Database"):
                            # Prepare data for database
                            db_cols = [
                                "transaction_id", "individual_id", "account_id", "bank_name", 
                                "amount", "daily_total", "weekly_total", "monthly_total", 
                                "n_accounts", "fraud_probability", "predicted_suspicious", "timestamp"
                            ]
                            
                            db_df = results_df[db_cols].copy()
                            
                            # Convert timestamp to string for SQLite
                            db_df["timestamp"] = db_df["timestamp"].astype(str)
                            
                            # Save to database
                            if db_manager.save_results(db_df):
                                st.success(f"Successfully saved {len(db_df)} transaction results to database!")
                            else:
                                st.error("Error saving results to database.")
            
            except Exception as e:
                logger.error(f"Error processing uploaded file: {str(e)}")
                st.error(f"Error processing uploaded file: {str(e)}")
    
    # Manual Analysis tab
    with tabs[2]:
        st.header("🔍 Manual Transaction Analysis")
        
        # Form for manual transaction input
        with st.form("manual_analysis_form"):
            st.subheader("Enter Transaction Details")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Generate a random transaction ID
                if "tx_id" not in st.session_state:
                    st.session_state.tx_id = f"TX{uuid.uuid4().hex[:8].upper()}"
                
                transaction_id = st.text_input("Transaction ID", value=st.session_state.tx_id, disabled=True)
                individual_id = st.text_input("Individual ID", value="IND")
                account_id = st.text_input("Account ID", value="ACC")
            
            with col2:
                bank_name = st.selectbox(
                    "Bank Name", 
                    ["Bank A", "Bank B", "Bank C", "Bank D", "Bank E", "Other"]
                )
                if bank_name == "Other":
                    bank_name = st.text_input("Enter Bank Name")
                
                amount = st.number_input("Amount ($)", min_value=0.01, value=1000.00, format="%.2f")
                timestamp = st.text_input(
                    "Timestamp (YYYY-MM-DD HH:MM:SS)", 
                    value=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            
            submit_button = st.form_submit_button("Analyze Transaction")
        
        if submit_button:
            try:
                # Create DataFrame from input
                data = {
                    "transaction_id": [transaction_id],
                    "individual_id": [individual_id],
                    "account_id": [account_id],
                    "bank_name": [bank_name],
                    "amount": [amount],
                    "timestamp": [timestamp]
                }
                
                manual_df = pd.DataFrame(data)
                
                # Process and predict
                processed_df = fraud_detector.preprocess_data(manual_df)
                results_df = fraud_detector.predict(processed_df)
                
                # Show result
                st.subheader("Analysis Result")
                
                # Result card
                is_suspicious = results_df["predicted_suspicious"].iloc[0] == 1
                probability = results_df["fraud_probability"].iloc[0]
                
                result_color = "red" if is_suspicious else "green"
                result_text = "SUSPICIOUS" if is_suspicious else "NORMAL"
                
                st.markdown(f"""
                <div style="padding: 20px; border-radius: 5px; background-color: rgba({255 if is_suspicious else 0}, {0 if is_suspicious else 128}, 0, 0.2);">
                    <h3 style="color: {result_color};">{result_text}</h3>
                    <p>Transaction ID: {transaction_id}</p>
                    <p>Risk Score: {probability:.2%}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # Transaction details
                st.subheader("Transaction Details")
                
                # Format for better display
                details_df = results_df.copy()
                details_df["daily_total"] = details_df["daily_total"].apply(lambda x: f"${x:,.2f}")
                details_df["weekly_total"] = details_df["weekly_total"].apply(lambda x: f"${x:,.2f}")
                details_df["monthly_total"] = details_df["monthly_total"].apply(lambda x: f"${x:,.2f}")
                details_df["amount"] = details_df["amount"].apply(lambda x: f"${x:,.2f}")
                details_df["timestamp"] = pd.to_datetime(details_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                
                # Display as key-value pairs
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Individual ID:** {individual_id}")
                    st.markdown(f"**Account ID:** {account_id}")
                    st.markdown(f"**Bank Name:** {bank_name}")
                    st.markdown(f"**Amount:** ${amount:,.2f}")
                
                with col2:
                    st.markdown(f"**Daily Total:** {details_df['daily_total'].iloc[0]}")
                    st.markdown(f"**Number of Accounts:** {details_df['n_accounts'].iloc[0]}")
                    st.markdown(f"**Risk Score:** {probability:.2%}")
                    st.markdown(f"**Timestamp:** {details_df['timestamp'].iloc[0]}")
                
                # Save to database
                if st.button("Save Analysis to Database"):
                    # Prepare data for database
                    db_cols = [
                        "transaction_id", "individual_id", "account_id", "bank_name", 
                        "amount", "daily_total", "weekly_total", "monthly_total", 
                        "n_accounts", "fraud_probability", "predicted_suspicious", "timestamp"
                    ]
                    
                    db_df = results_df[db_cols].copy()
                    
                    # Convert timestamp to string for SQLite
                    db_df["timestamp"] = db_df["timestamp"].astype(str)
                    
                    # Save to database
                    if db_manager.save_results(db_df):
                        st.success("Successfully saved analysis result to database!")
                        # Generate new transaction ID for next analysis
                        st.session_state.tx_id = f"TX{uuid.uuid4().hex[:8].upper()}"
                    else:
                        st.error("Error saving analysis to database.")
                
                # Reset form for new transaction
                if st.button("Analyze Another Transaction"):
                    st.session_state.tx_id = f"TX{uuid.uuid4().hex[:8].upper()}"
                    st.rerun()
            
            except Exception as e:
                logger.error(f"Error in manual analysis: {str(e)}")
                st.error(f"Error analyzing transaction: {str(e)}")
    
    # Results History tab
    with tabs[3]:
        st.header("📜 Analysis History")
        
        # Filters
        st.subheader("Filter Results")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Date range filter
            stats = db_manager.get_database_stats()
            
            default_start = None
            default_end = None
            
            if stats and "date_range" in stats and stats["date_range"][0]:
                default_start = datetime.strptime(stats["date_range"][0].split()[0], "%Y-%m-%d").date()
                default_end = datetime.strptime(stats["date_range"][1].split()[0], "%Y-%m-%d").date()
            
            date_range = st.date_input(
                "Date Range",
                value=(default_start, default_end) if default_start and default_end else None,
                format="YYYY-MM-DD"
            )
        
        with col2:
            # Status filter
            status_filter = st.selectbox(
                "Status",
                ["All", "pending", "reviewed", "confirmed", "false_positive"]
            )
        
        with col3:
            # Suspicious filter
            suspicious_filter = st.selectbox(
                "Transaction Type",
                ["All", "Suspicious Only", "Normal Only"]
            )
        
        # Apply filters
        filters = {}
        
        if len(date_range) == 2:
            filters["date_range"] = (date_range[0].isoformat(), date_range[1].isoformat())
        
        if status_filter != "All":
            filters["status"] = status_filter
        
        if suspicious_filter == "Suspicious Only":
            filters["suspicious"] = 1
        elif suspicious_filter == "Normal Only":
            filters["suspicious"] = 0
        
        # Get paginated results
        if "page" not in st.session_state:
            st.session_state.page = 0
        
        results_df, total_pages = db_manager.get_paginated_results(st.session_state.page, filters)
        
        # Display results
        if not results_df.empty:
            st.write(f"Showing {len(results_df)} results (page {st.session_state.page + 1} of {total_pages})")
            
            # Format for display
            display_df = results_df.copy()
            display_df["timestamp"] = pd.to_datetime(display_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            display_df["processed_at"] = pd.to_datetime(display_df["processed_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Display as styled dataframe
            st.dataframe(style_dataframe(display_df))
            
            # Pagination controls
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if st.session_state.page > 0:
                    if st.button("Previous Page"):
                        st.session_state.page -= 1
                        st.rerun()
            
            with col2:
                st.write(f"Page {st.session_state.page + 1} of {total_pages}")
            
            with col3:
                if st.session_state.page < total_pages - 1:
                    if st.button("Next Page"):
                        st.session_state.page += 1
                        st.rerun()
            
            # Transaction detail view
            st.subheader("Transaction Details")
            
            selected_tx = st.selectbox(
                "Select Transaction",
                options=results_df["transaction_id"].tolist(),
                format_func=lambda x: f"{x} - {results_df[results_df['transaction_id'] == x]['individual_id'].iloc[0]}"
            )
            
            if selected_tx:
                tx_data = results_df[results_df["transaction_id"] == selected_tx].iloc[0]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Transaction ID:** {tx_data['transaction_id']}")
                    st.markdown(f"**Individual ID:** {tx_data['individual_id']}")
                    st.markdown(f"**Account ID:** {tx_data['account_id']}")
                    st.markdown(f"**Bank Name:** {tx_data['bank_name']}")
                    st.markdown(f"**Amount:** ${tx_data['amount']:,.2f}")
                
                with col2:
                    st.markdown(f"**Risk Score:** {tx_data['fraud_probability']:.2%}")
                    st.markdown(f"**Status:** {tx_data['status']}")
                    st.markdown(f"**Daily Total:** ${tx_data['daily_total']:,.2f}")
                    st.markdown(f"**Number of Accounts:** {tx_data['n_accounts']}")
                    st.markdown(f"**Timestamp:** {pd.to_datetime(tx_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Analyst notes
                current_notes = tx_data["analyst_notes"] if tx_data["analyst_notes"] else ""
                new_notes = st.text_area("Analyst Notes", value=current_notes)
                
                # Status update
                new_status = st.selectbox(
                    "Update Status",
                    ["pending", "reviewed", "confirmed", "false_positive"],
                    index=["pending", "reviewed", "confirmed", "false_positive"].index(tx_data["status"])
                )
                
                # Save updates button
                if st.button("Save Updates"):
                    try:
                        db_manager.execute_query(
                            f"UPDATE {FRAUD_TABLE} SET analyst_notes = ?, status = ? WHERE transaction_id = ?",
                            (new_notes, new_status, selected_tx)
                        )
                        st.success("Transaction updated successfully!")
                        # Refresh the page to show updates
                        st.rerun()
                    except Exception as e:
                        logger.error(f"Error updating transaction: {str(e)}")
                        st.error(f"Error updating transaction: {str(e)}")
        else:
            st.info("No results found with the current filters.")
    
    # Export tab
    with tabs[4]:
        st.header("📥 Export Options")
        
        export_type = st.selectbox(
            "Select Export Type",
            ["All Transactions", "Suspicious Transactions Only", "Custom Query", "Summary Report"]
        )
        
        if export_type == "All Transactions":
            # Get all transactions (with pagination for large datasets)
            try:
                all_results = []
                page = 0
                while True:
                    results_df, _ = db_manager.get_paginated_results(page)
                    if results_df.empty:
                        break
                    all_results.append(results_df)
                    page += 1
                    # Limit to 1000 pages (50,000 records) for performance
                    if page >= 1000:
                        break
                
                if all_results:
                    all_data = pd.concat(all_results)
                    st.write(f"Exporting {len(all_data)} transactions")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            label="Download as CSV",
                            data=convert_df_to_csv(all_data),
                            file_name=f"fraud_detection_all_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        st.download_button(
                            label="Download as Excel",
                            data=export_to_excel(all_data),
                            file_name=f"fraud_detection_all_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.info("No transactions found to export.")
            except Exception as e:
                logger.error(f"Error exporting all transactions: {str(e)}")
                st.error(f"Error exporting data: {str(e)}")
        
        elif export_type == "Suspicious Transactions Only":
            try:
                suspicious_results = []
                page = 0
                while True:
                    results_df, _ = db_manager.get_paginated_results(page, {"suspicious": 1})
                    if results_df.empty:
                        break
                    suspicious_results.append(results_df)
                    page += 1
                    # Limit to 1000 pages for performance
                    if page >= 1000:
                        break
                
                if suspicious_results:
                    suspicious_data = pd.concat(suspicious_results)
                    st.write(f"Exporting {len(suspicious_data)} suspicious transactions")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            label="Download as CSV",
                            data=convert_df_to_csv(suspicious_data),
                            file_name=f"fraud_detection_suspicious_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        st.download_button(
                            label="Download as Excel",
                            data=export_to_excel(suspicious_data),
                            file_name=f"fraud_detection_suspicious_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.info("No suspicious transactions found to export.")
            except Exception as e:
                logger.error(f"Error exporting suspicious transactions: {str(e)}")
                st.error(f"Error exporting data: {str(e)}")
        
        elif export_type == "Custom Query":
            st.subheader("Custom Query Filters")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Date range filter
                date_range = st.date_input(
                    "Date Range",
                    value=(datetime.now() - timedelta(days=30), datetime.now()),
                    format="YYYY-MM-DD"
                )
            
            with col2:
                # Status and type filters
                status_filter = st.multiselect(
                    "Status",
                    ["pending", "reviewed", "confirmed", "false_positive"],
                    default=["pending", "confirmed"]
                )
                
                suspicious_filter = st.radio(
                    "Transaction Type",
                    ["All", "Suspicious Only", "Normal Only"]
                )
            
            # Get results with filters
            try:
                filters = {}
                
                if len(date_range) == 2:
                    filters["date_range"] = (date_range[0].isoformat(), date_range[1].isoformat())
                
                if status_filter:
                    # Need to handle multiple status values as a custom SQL query
                    status_clause = "status IN (" + ",".join([f"'{s}'" for s in status_filter]) + ")"
                
                if suspicious_filter == "Suspicious Only":
                    filters["suspicious"] = 1
                elif suspicious_filter == "Normal Only":
                    filters["suspicious"] = 0
                
                # Execute query
                custom_query = f"SELECT * FROM {FRAUD_TABLE} WHERE "
                conditions = []
                params = []
                
                if "date_range" in filters:
                    conditions.append("date(timestamp) BETWEEN ? AND ?")
                    params.extend(filters["date_range"])
                
                if status_filter:
                    conditions.append(status_clause)
                
                if "suspicious" in filters:
                    conditions.append("predicted_suspicious = ?")
                    params.append(filters["suspicious"])
                
                if not conditions:
                    conditions.append("1=1")  # Default condition if none specified
                
                custom_query += " AND ".join(conditions)
                
                with db_manager._get_connection() as conn:
                    custom_data = pd.read_sql_query(custom_query, conn, params=params)
                
                if not custom_data.empty:
                    st.write(f"Found {len(custom_data)} transactions matching your criteria")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            label="Download as CSV",
                            data=convert_df_to_csv(custom_data),
                            file_name=f"fraud_detection_custom_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        st.download_button(
                            label="Download as Excel",
                            data=export_to_excel(custom_data),
                            file_name=f"fraud_detection_custom_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.info("No transactions found matching your criteria.")
            except Exception as e:
                logger.error(f"Error with custom query export: {str(e)}")
                st.error(f"Error exporting data: {str(e)}")
        
        elif export_type == "Summary Report":
            try:
                all_results = []
                page = 0
                while True:
                    results_df, _ = db_manager.get_paginated_results(page)
                    if results_df.empty:
                        break
                    all_results.append(results_df)
                    page += 1
                    # Limit to 1000 pages for performance
                    if page >= 1000:
                        break
                
                if all_results:
                    all_data = pd.concat(all_results)
                    summary_report = create_summary_report(all_data)
                    
                    st.subheader("Summary Report")
                    st.dataframe(summary_report)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.download_button(
                            label="Download as CSV",
                            data=convert_df_to_csv(summary_report),
                            file_name=f"fraud_detection_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        st.download_button(
                            label="Download as Excel",
                            data=export_to_excel(summary_report),
                            file_name=f"fraud_detection_summary_{datetime.now().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    # Create visualization for summary
                    st.subheader("Top 10 High-Risk Individuals")
                    
                    top_risk = summary_report.sort_values("Average Risk Score", ascending=False).head(10)
                    top_risk["Average Risk Score"] = top_risk["Average Risk Score"].apply(
                        lambda x: float(x.strip("%")) / 100
                    )
                    
                    fig = px.bar(
                        top_risk,
                        x="Individual ID",
                        y="Average Risk Score",
                        color="Suspicious Transactions",
                        title="Top 10 Individuals by Risk Score"
                    )
                    fig.update_yaxes(tickformat=".1%")
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No transaction data available for summary report.")
            except Exception as e:
                logger.error(f"Error creating summary report: {str(e)}")
                st.error(f"Error creating summary report: {str(e)}")

if __name__ == "__main__":
    main()
