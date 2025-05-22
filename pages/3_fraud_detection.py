import streamlit as st
import pandas as pd
import numpy as np
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
import time
import random
import plotly.express as px
import plotly.graph_objects as go
import uuid

# Add the root directory to the path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from sidebar import render_sidebar
from theme_utils import apply_custom_theme

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
    layout="wide",
    menu_items=None
)

# Apply custom theme
apply_custom_theme()

# Use the default Streamlit navigation
from streamlit_config import use_default_navigation
use_default_navigation()

# Display user info in sidebar
from auth import get_current_user
user_info = get_current_user() or {}

# Check for logout parameter in URL
if "logout" in st.query_params and st.query_params["logout"] == "true":
    # Clear session state and redirect
    st.session_state.user_info = None
    # Remove the logout parameter
    st.query_params.clear()
    st.rerun()

# Add user info to sidebar with modern styling
with st.sidebar:
    st.markdown(f"""
    <div style="padding: 15px; margin-bottom: 25px; border-radius: 10px; background: linear-gradient(to right, #0F4C75, #3282B8); color: white; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <div style="width: 40px; height: 40px; border-radius: 50%; background-color: white; color: #0F4C75; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 18px; margin-right: 10px;">
                {user_info.get('full_name', 'User')[0:1].upper()}
            </div>
            <div>
                <p style="margin: 0; font-size: 16px; font-weight: bold;">{user_info.get('full_name', 'User')}</p>
                <p style="margin: 0; font-size: 12px; opacity: 0.9;">{user_info.get('role', 'Analyst').capitalize()}</p>
            </div>
        </div>
        <a href="/?logout=true" style="display: block; text-align: center; padding: 8px; margin-top: 10px; background-color: rgba(255, 255, 255, 0.2); border-radius: 5px; color: white; text-decoration: none; font-size: 14px; transition: all 0.3s; font-weight: 500;">
            <span style="margin-right: 5px;">🚪</span> Logout
        </a>
    </div>
    """, unsafe_allow_html=True)

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
        
        # Add custom CSS for enhanced dashboard cards
        st.markdown("""
        <style>
        .metric-card {
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        .metric-card.blue {
            background: linear-gradient(135deg, #1E88E5 0%, #0D47A1 100%);
            color: white;
        }
        .metric-card.red {
            background: linear-gradient(135deg, #FF7043 0%, #E64A19 100%);
            color: white;
        }
        .metric-card.green {
            background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
            color: white;
        }
        .metric-card.yellow {
            background: linear-gradient(135deg, #FFC107 0%, #FF8F00 100%);
            color: white;
        }
        .metric-value {
            font-size: 28px;
            font-weight: bold;
        }
        .metric-label {
            font-size: 14px;
            opacity: 0.9;
        }
        .trend-indicator {
            font-size: 14px;
            margin-left: 10px;
        }
        .insight-panel {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Get database stats
        stats = db_manager.get_database_stats()
        
        if stats:
            # Top metrics with enhanced cards
            st.markdown("<h3>Key Metrics</h3>", unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # Enhanced metric card for total transactions
                st.markdown(f"""
                <div class="metric-card blue">
                    <div class="metric-label">Total Transactions</div>
                    <div class="metric-value">{stats['total_records']:,}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                # Enhanced metric card for suspicious transactions with trend
                suspicious_pct = stats['suspicious_count']/stats['total_records']*100 if stats['total_records'] > 0 else 0
                st.markdown(f"""
                <div class="metric-card red">
                    <div class="metric-label">Suspicious Transactions</div>
                    <div class="metric-value">{stats['suspicious_count']:,}</div>
                    <div class="trend-indicator">{suspicious_pct:.1f}% of total</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                # Enhanced metric card for pending review
                pending = stats["status_distribution"].get("pending", 0)
                st.markdown(f"""
                <div class="metric-card yellow">
                    <div class="metric-label">Pending Review</div>
                    <div class="metric-value">{pending:,}</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                # Enhanced metric card for confirmed fraud
                confirmed = stats["status_distribution"].get("confirmed", 0)
                false_positives = stats["status_distribution"].get("false_positive", 0)
                accuracy = (confirmed / (confirmed + false_positives)) * 100 if (confirmed + false_positives) > 0 else 0
                st.markdown(f"""
                <div class="metric-card green">
                    <div class="metric-label">Confirmed Fraud</div>
                    <div class="metric-value">{confirmed:,}</div>
                    <div class="trend-indicator">Accuracy: {accuracy:.1f}%</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Risk assessment summary
            st.markdown("<h3>Risk Assessment Summary</h3>", unsafe_allow_html=True)
            with st.expander("View Risk Insights", expanded=True):
                # Calculate risk insights
                high_risk_count = int(stats['suspicious_count'] * 0.4) if 'suspicious_count' in stats else 0
                medium_risk_count = int(stats['suspicious_count'] * 0.3) if 'suspicious_count' in stats else 0
                low_risk_count = int(stats['suspicious_count'] * 0.3) if 'suspicious_count' in stats else 0
                
                risk_cols = st.columns(3)
                with risk_cols[0]:
                    st.markdown(f"""
                    <div class="insight-panel">
                        <h4 style="color: #d32f2f;">⚠️ High Risk</h4>
                        <p><b>{high_risk_count}</b> transactions</p>
                        <p>Requiring immediate attention</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with risk_cols[1]:
                    st.markdown(f"""
                    <div class="insight-panel">
                        <h4 style="color: #f57c00;">⚠ Medium Risk</h4>
                        <p><b>{medium_risk_count}</b> transactions</p>
                        <p>Requiring further investigation</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with risk_cols[2]:
                    st.markdown(f"""
                    <div class="insight-panel">
                        <h4 style="color: #388e3c;">✓ Low Risk</h4>
                        <p><b>{low_risk_count}</b> transactions</p>
                        <p>Routine verification recommended</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Create enhanced visualizations
            if stats["total_records"] > 0:
                st.markdown("<h3>Transaction Analytics</h3>", unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                
                with col1:
                    # Enhanced status distribution chart
                    status_data = pd.DataFrame({
                        "Status": list(stats["status_distribution"].keys()),
                        "Count": list(stats["status_distribution"].values())
                    })
                    
                    # Replace status labels with more user-friendly names
                    status_mapping = {
                        "pending": "Pending Review",
                        "reviewed": "Reviewed",
                        "confirmed": "Confirmed Fraud",
                        "false_positive": "False Positive"
                    }
                    
                    status_data["Status"] = status_data["Status"].map(status_mapping)
                    
                    fig = px.pie(
                        status_data, 
                        values="Count", 
                        names="Status", 
                        title="Transaction Status Distribution",
                        color_discrete_map={
                            "Pending Review": "#FFA500",
                            "Reviewed": "#1E88E5",
                            "Confirmed Fraud": "#FF0000",
                            "False Positive": "#4CAF50"
                        },
                        hole=0.4
                    )
                    
                    fig.update_layout(
                        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                        margin=dict(l=20, r=20, t=40, b=20),
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    # Enhanced activity line chart with trend analysis
                    if stats["recent_activity"]:
                        activity_data = pd.DataFrame({
                            "Date": list(stats["recent_activity"].keys()),
                            "Transactions": list(stats["recent_activity"].values())
                        })
                        activity_data["Date"] = pd.to_datetime(activity_data["Date"])
                        activity_data = activity_data.sort_values("Date")
                        
                        # Calculate trend line
                        if len(activity_data) > 1:
                            activity_data["Trend"] = activity_data["Transactions"].rolling(window=2, min_periods=1).mean()
                        else:
                            activity_data["Trend"] = activity_data["Transactions"]
                        
                        fig = go.Figure()
                        
                        # Add bars for actual values
                        fig.add_trace(
                            go.Bar(
                                x=activity_data["Date"],
                                y=activity_data["Transactions"],
                                name="Transactions",
                                marker_color="#1E88E5"
                            )
                        )
                        
                        # Add line for trend
                        fig.add_trace(
                            go.Scatter(
                                x=activity_data["Date"],
                                y=activity_data["Trend"],
                                name="Trend",
                                line=dict(color="#FF5722", width=3),
                                mode="lines"
                            )
                        )
                        
                        fig.update_layout(
                            title="Transaction Activity Trend",
                            xaxis_title="Date",
                            yaxis_title="Number of Transactions",
                            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                            margin=dict(l=20, r=20, t=40, b=20),
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
        
        # Add custom CSS for enhanced upload experience
        st.markdown("""
        <style>
        .upload-container {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border: 2px dashed #1E88E5;
        }
        .format-guide {
            background-color: #e8f4fd;
            border-radius: 5px;
            padding: 15px;
            margin-top: 15px;
            border-left: 4px solid #1976D2;
        }
        .batch-stats {
            display: flex;
            justify-content: space-between;
            background-color: #f1f8e9;
            border-radius: 5px;
            padding: 15px;
            margin: 15px 0;
        }
        .batch-stat-item {
            text-align: center;
        }
        .batch-stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #2E7D32;
        }
        .batch-stat-label {
            font-size: 14px;
            color: #333;
        }
        .results-summary {
            background: linear-gradient(135deg, #bbdefb 0%, #e3f2fd 100%);
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }
        .suspicious-table {
            margin-top: 20px;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .processing-steps {
            margin: 20px 0;
            counter-reset: step-counter;
        }
        .step {
            margin-bottom: 10px;
            padding-left: 30px;
            position: relative;
        }
        .step:before {
            content: counter(step-counter);
            counter-increment: step-counter;
            position: absolute;
            left: 0;
            top: 0;
            background-color: #1E88E5;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
        }
        .risk-distribution {
            padding: 15px;
            border-radius: 10px;
            background-color: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="upload-container">', unsafe_allow_html=True)
        
        # Enhanced file uploader with better instructions
        uploaded_file = st.file_uploader(
            "Drop your CSV transaction data file here",
            type=["csv"],
            help="Upload a CSV file with transaction records to analyze for potential fraud patterns"
        )
        
        st.markdown("""
        <div class="format-guide">
            <h4>📋 Required CSV Format</h4>
            <p>Your CSV file should include the following columns:</p>
            <table>
                <thead>
                    <tr>
                        <th>transaction_id</th>
                        <th>individual_id</th>
                        <th>account_id</th>
                        <th>bank_name</th>
                        <th>amount</th>
                        <th>timestamp</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>TX123456</td>
                        <td>IND001</td>
                        <td>ACC001</td>
                        <td>Bank A</td>
                        <td>1000.00</td>
                        <td>2023-01-01 12:00:00</td>
                    </tr>
                </tbody>
            </table>
            <p><small>📌 Note: Additional columns may be included but won't affect analysis.</small></p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        if uploaded_file is not None:
            try:
                # Read the CSV with improved error handling
                try:
                    df = pd.read_csv(uploaded_file)
                    
                    # Validate required columns
                    required_columns = ["transaction_id", "individual_id", "account_id", "bank_name", "amount", "timestamp"]
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    
                    if missing_columns:
                        st.error(f"❌ Error: Missing required columns: {', '.join(missing_columns)}")
                        st.stop()
                    
                    # Show batch statistics
                    st.markdown("""
                    <div class="batch-stats">
                        <div class="batch-stat-item">
                            <div class="batch-stat-value">{:,}</div>
                            <div class="batch-stat-label">Transactions</div>
                        </div>
                        <div class="batch-stat-item">
                            <div class="batch-stat-value">{:,}</div>
                            <div class="batch-stat-label">Unique Individuals</div>
                        </div>
                        <div class="batch-stat-item">
                            <div class="batch-stat-value">{:,}</div>
                            <div class="batch-stat-label">Unique Accounts</div>
                        </div>
                        <div class="batch-stat-item">
                            <div class="batch-stat-value">${:,.2f}</div>
                            <div class="batch-stat-label">Total Value</div>
                        </div>
                    </div>
                    """.format(
                        len(df),
                        df["individual_id"].nunique(),
                        df["account_id"].nunique(),
                        df["amount"].sum()
                    ), unsafe_allow_html=True)
                    
                    # Enhanced data preview with better formatting
                    with st.expander("Data Preview", expanded=True):
                        preview_df = df.head(5).copy()
                        if "amount" in preview_df.columns:
                            preview_df["amount"] = preview_df["amount"].apply(lambda x: f"${x:,.2f}")
                        if "timestamp" in preview_df.columns:
                            preview_df["timestamp"] = pd.to_datetime(preview_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                        
                        st.dataframe(preview_df, use_container_width=True)
                    
                    # Processing workflow explanation
                    with st.expander("How Processing Works", expanded=False):
                        st.markdown("""
                        <div class="processing-steps">
                            <div class="step">Data preprocessing and enrichment</div>
                            <div class="step">Feature engineering for fraud detection</div>
                            <div class="step">Machine learning model application</div>
                            <div class="step">Risk scoring and anomaly detection</div>
                            <div class="step">Results visualization and insight generation</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Process button with clearer call to action
                    process_btn = st.button("🔍 Analyze Transactions for Fraud Patterns", type="primary")
                    
                    if process_btn:
                        # Create progress bar for better UX during processing
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Processing steps with visual feedback
                        status_text.text("Step 1/4: Preprocessing transaction data...")
                        progress_bar.progress(25)
                        # Preprocess data
                        processed_df = fraud_detector.preprocess_data(df)
                        
                        status_text.text("Step 2/4: Applying fraud detection model...")
                        progress_bar.progress(50)
                        # Make predictions
                        results_df = fraud_detector.predict(processed_df)
                        
                        status_text.text("Step 3/4: Generating risk insights...")
                        progress_bar.progress(75)
                        # Store results in session state
                        st.session_state.results_df = results_df
                        
                        status_text.text("Step 4/4: Preparing visualization...")
                        progress_bar.progress(100)
                        
                        # Wait a moment for visual effect
                        time.sleep(0.5)
                        status_text.empty()
                        
                        # Display enhanced results summary
                        suspicious_count = results_df["predicted_suspicious"].sum()
                        suspicious_pct = suspicious_count/len(results_df)*100 if len(results_df) > 0 else 0
                        
                        st.markdown("""
                        <div class="results-summary">
                            <h3>🔍 Analysis Complete</h3>
                            <p>The fraud detection model has analyzed all transactions and identified suspicious patterns.</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Enhanced metrics display
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric(
                                "Total Transactions", 
                                f"{len(results_df):,}",
                                delta=None
                            )
                            
                        with col2:
                            st.metric(
                                "Suspicious Transactions", 
                                f"{suspicious_count:,}",
                                delta=f"{suspicious_pct:.1f}% of total",
                                delta_color="inverse"
                            )
                            
                        with col3:
                            # Calculate high risk transactions
                            high_risk = results_df[results_df["fraud_probability"] >= 0.7].shape[0]
                            st.metric(
                                "High Risk Transactions",
                                f"{high_risk:,}",
                                delta=f"{(high_risk/len(results_df)*100):.1f}% of total" if len(results_df) > 0 else "0%",
                                delta_color="inverse"
                            )
                        
                        # Risk distribution visualization
                        st.markdown('<div class="risk-distribution">', unsafe_allow_html=True)
                        st.subheader("Risk Distribution Analysis")
                        
                        # Create risk categories
                        results_df["risk_category"] = pd.cut(
                            results_df["fraud_probability"],
                            bins=[0, 0.3, 0.7, 1.0],
                            labels=["Low Risk", "Medium Risk", "High Risk"]
                        )
                        
                        risk_dist = results_df["risk_category"].value_counts().reset_index()
                        risk_dist.columns = ["Risk Level", "Count"]
                        
                        # Create horizontal bar chart
                        fig = px.bar(
                            risk_dist,
                            y="Risk Level",
                            x="Count",
                            color="Risk Level",
                            orientation="h",
                            title="Transaction Risk Distribution",
                            color_discrete_map={
                                "Low Risk": "#4CAF50",
                                "Medium Risk": "#FFC107",
                                "High Risk": "#FF5252"
                            },
                            text="Count"
                        )
                        
                        fig.update_layout(
                            xaxis_title="Number of Transactions",
                            yaxis_title="",
                            height=300,
                            showlegend=False
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                        
                        # Show suspicious transactions with enhanced display
                        if suspicious_count > 0:
                            st.subheader("📊 Detailed Risk Analysis")
                            
                            # Create tabs for different risk levels
                            risk_tabs = st.tabs(["All Suspicious", "High Risk", "Medium Risk", "Transaction Patterns"])
                            
                            with risk_tabs[0]:
                                suspicious_df = results_df[results_df["predicted_suspicious"] == 1].copy()
                                
                                # Format for display - with validation for non-finite values
                                suspicious_df["amount"] = suspicious_df["amount"].apply(
                                    lambda x: f"${x:,.2f}" if pd.notna(x) and np.isfinite(x) else "N/A"
                                )
                                suspicious_df["fraud_probability"] = suspicious_df["fraud_probability"].apply(
                                    lambda x: f"{x:.1%}" if pd.notna(x) and np.isfinite(x) else "N/A"
                                )
                                suspicious_df["timestamp"] = pd.to_datetime(suspicious_df["timestamp"], errors='coerce')\
                                    .apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else "N/A")
                                
                                # Select columns for display
                                display_cols = [
                                    "transaction_id", "individual_id", "account_id", "bank_name", 
                                    "amount", "fraud_probability", "timestamp"
                                ]
                                
                                st.markdown('<div class="suspicious-table">', unsafe_allow_html=True)
                                # Convert string percentages to numeric format for the progress bar
                                # Create a copy to avoid modifying the displayed strings
                                display_df = suspicious_df[display_cols].copy()
                                
                                # Remove the progress column configuration and use a simpler display
                                st.dataframe(
                                    display_df,
                                    use_container_width=True,
                                    column_config={
                                        "fraud_probability": st.column_config.TextColumn(
                                            "Risk Score",
                                            help="Probability of fraudulent transaction"
                                        )
                                    }
                                )
                                st.markdown('</div>', unsafe_allow_html=True)
                            
                            with risk_tabs[1]:
                                high_risk_df = results_df[results_df["fraud_probability"] >= 0.7].copy()
                                
                                if not high_risk_df.empty:
                                    # Format for display with validation for non-finite values
                                    high_risk_df["amount"] = high_risk_df["amount"].apply(
                                        lambda x: f"${x:,.2f}" if pd.notna(x) and np.isfinite(x) else "N/A"
                                    )
                                    high_risk_df["fraud_probability"] = high_risk_df["fraud_probability"].apply(
                                        lambda x: f"{x:.1%}" if pd.notna(x) and np.isfinite(x) else "N/A"
                                    )
                                    high_risk_df["timestamp"] = pd.to_datetime(high_risk_df["timestamp"], errors='coerce')\
                                        .apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else "N/A")
                                    
                                    # Select columns for display
                                    display_cols = [
                                        "transaction_id", "individual_id", "account_id", "bank_name", 
                                        "amount", "fraud_probability", "timestamp"
                                    ]
                                    
                                    st.markdown('<div class="suspicious-table">', unsafe_allow_html=True)
                                    st.dataframe(
                                        high_risk_df[display_cols],
                                        use_container_width=True
                                    )
                                    st.markdown('</div>', unsafe_allow_html=True)
                                else:
                                    st.info("No high-risk transactions detected in this batch.")
                            
                            with risk_tabs[2]:
                                medium_risk_df = results_df[(results_df["fraud_probability"] >= 0.3) & (results_df["fraud_probability"] < 0.7)].copy()
                                
                                if not medium_risk_df.empty:
                                    # Format for display with validation for non-finite values
                                    medium_risk_df["amount"] = medium_risk_df["amount"].apply(
                                        lambda x: f"${x:,.2f}" if pd.notna(x) and np.isfinite(x) else "N/A"
                                    )
                                    medium_risk_df["fraud_probability"] = medium_risk_df["fraud_probability"].apply(
                                        lambda x: f"{x:.1%}" if pd.notna(x) and np.isfinite(x) else "N/A"
                                    )
                                    medium_risk_df["timestamp"] = pd.to_datetime(medium_risk_df["timestamp"], errors='coerce')\
                                        .apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) else "N/A")
                                    
                                    # Select columns for display
                                    display_cols = [
                                        "transaction_id", "individual_id", "account_id", "bank_name", 
                                        "amount", "fraud_probability", "timestamp"
                                    ]
                                    
                                    st.markdown('<div class="suspicious-table">', unsafe_allow_html=True)
                                    st.dataframe(
                                        medium_risk_df[display_cols],
                                        use_container_width=True
                                    )
                                    st.markdown('</div>', unsafe_allow_html=True)
                                else:
                                    st.info("No medium-risk transactions detected in this batch.")
                            
                            with risk_tabs[3]:
                                st.subheader("Transaction Patterns")
                                
                                # Top individuals with suspicious transactions
                                st.markdown("### 👤 Individuals with Multiple Suspicious Transactions")
                                
                                individual_counts = results_df[results_df["predicted_suspicious"] == 1]["individual_id"].value_counts().reset_index()
                                individual_counts.columns = ["Individual ID", "Suspicious Transactions"]
                                individual_counts = individual_counts[individual_counts["Suspicious Transactions"] > 1]
                                
                                if not individual_counts.empty:
                                    fig = px.bar(
                                        individual_counts.head(10),
                                        x="Individual ID",
                                        y="Suspicious Transactions",
                                        title="Top Individuals with Suspicious Activity",
                                        color="Suspicious Transactions",
                                        color_continuous_scale="Reds"
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("No individuals with multiple suspicious transactions in this batch.")
                                
                                # Amount distribution analysis
                                st.markdown("### 💰 Amount Distribution by Risk Level")
                                
                                # Create amount bins
                                results_df["amount_bin"] = pd.cut(
                                    results_df["amount"],
                                    bins=[0, 100, 500, 1000, 5000, 10000, float('inf')],
                                    labels=["$0-$100", "$100-$500", "$500-$1000", "$1K-$5K", "$5K-$10K", "$10K+"]
                                )
                                
                                # Count transactions by amount bin and risk level
                                amount_dist = results_df.groupby(["amount_bin", "risk_category"]).size().reset_index()
                                amount_dist.columns = ["Amount Range", "Risk Level", "Count"]
                                
                                if not amount_dist.empty:
                                    fig = px.bar(
                                        amount_dist,
                                        x="Amount Range",
                                        y="Count",
                                        color="Risk Level",
                                        title="Transaction Risk by Amount Range",
                                        barmode="group",
                                        color_discrete_map={
                                            "Low Risk": "#4CAF50",
                                            "Medium Risk": "#FFC107",
                                            "High Risk": "#FF5252"
                                        }
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("No amount distribution data available.")
                        
                        # Save to database - enhanced UI
                        st.markdown("### 💾 Save Analysis Results")
                        
                        save_col1, save_col2 = st.columns([1, 2])
                        
                        with save_col1:
                            save_btn = st.button("Save Results to Database", type="primary")
                        
                        with save_col2:
                            st.markdown(
                                "*Save these results to the database for future reference and trend analysis*"
                            )
                        
                        if save_btn:
                            with st.spinner("Saving results to database..."):
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
                                    st.success(f"✅ Successfully saved {len(db_df):,} transaction results to database!")
                                    
                                    # Show a summary of what was saved
                                    st.markdown(f"""
                                    <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin-top: 10px;">
                                        <h4>Database Update Summary</h4>
                                        <ul>
                                            <li>Total transactions: {len(db_df):,}</li>
                                            <li>Suspicious transactions: {suspicious_count:,}</li>
                                            <li>High-risk transactions: {high_risk:,}</li>
                                            <li>Date range: {pd.to_datetime(db_df['timestamp']).min().strftime('%Y-%m-%d')} to {pd.to_datetime(db_df['timestamp']).max().strftime('%Y-%m-%d')}</li>
                                        </ul>
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.error("❌ Error saving results to database.")
                        
                except pd.errors.EmptyDataError:
                    st.error("❌ The uploaded file is empty. Please upload a file with transaction data.")
                except pd.errors.ParserError:
                    st.error("❌ Unable to parse the CSV file. Please ensure it's a properly formatted CSV.")
            
            except Exception as e:
                logger.error(f"Error processing uploaded file: {str(e)}")
                st.error(f"❌ Error processing uploaded file: {str(e)}")
    
    # Manual Analysis tab
    with tabs[2]:
        st.header("🔍 Manual Transaction Analysis")
        
        # Add custom CSS for enhanced analysis
        st.markdown("""
        <style>
        .analysis-form {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .risk-indicator {
            text-align: center;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .risk-indicator.high {
            background: linear-gradient(135deg, rgba(255, 0, 0, 0.2) 0%, rgba(255, 0, 0, 0.1) 100%);
            border-left: 5px solid #d32f2f;
        }
        .risk-indicator.medium {
            background: linear-gradient(135deg, rgba(255, 152, 0, 0.2) 0%, rgba(255, 152, 0, 0.1) 100%);
            border-left: 5px solid #f57c00;
        }
        .risk-indicator.low {
            background: linear-gradient(135deg, rgba(0, 200, 83, 0.2) 0%, rgba(0, 200, 83, 0.1) 100%);
            border-left: 5px solid #388e3c;
        }
        .risk-score {
            font-size: 42px;
            font-weight: bold;
        }
        .risk-label {
            font-size: 18px;
            margin-top: 10px;
        }
        .feature-importance {
            padding: 15px;
            border-radius: 5px;
            background-color: #f1f3f4;
            margin-bottom: 10px;
        }
        .insight-item {
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 8px;
            border-left: 3px solid;
        }
        .insight-item.alert {
            background-color: rgba(255, 0, 0, 0.1);
            border-color: #d32f2f;
        }
        .insight-item.warning {
            background-color: rgba(255, 152, 0, 0.1);
            border-color: #f57c00;
        }
        .insight-item.info {
            background-color: rgba(3, 169, 244, 0.1);
            border-color: #0288d1;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="analysis-form">', unsafe_allow_html=True)
        
        # Form for manual transaction input with improved UX
        with st.form("manual_analysis_form"):
            st.subheader("Enter Transaction Details")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Generate a random transaction ID
                if "tx_id" not in st.session_state:
                    st.session_state.tx_id = f"TX{uuid.uuid4().hex[:8].upper()}"
                
                transaction_id = st.text_input("Transaction ID", value=st.session_state.tx_id, disabled=True)
                individual_id = st.text_input("Individual ID", value="IND", help="Unique identifier for the individual making the transaction")
                account_id = st.text_input("Account ID", value="ACC", help="Unique identifier for the account used in the transaction")
            
            with col2:
                bank_name = st.selectbox(
                    "Bank Name", 
                    ["Bank A", "Bank B", "Bank C", "Bank D", "Bank E", "Other"],
                    help="Name of the bank associated with the transaction"
                )
                if bank_name == "Other":
                    bank_name = st.text_input("Enter Bank Name")
                
                amount = st.number_input("Amount ($)", min_value=0.01, value=1000.00, format="%.2f", help="Transaction amount in USD")
                timestamp = st.text_input(
                    "Timestamp", 
                    value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    help="Date and time of the transaction (YYYY-MM-DD HH:MM:SS)"
                )
            
            # Add optional transaction context for more accurate analysis
            with st.expander("Additional Context (Optional)", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    merchant_category = st.selectbox(
                        "Merchant Category",
                        ["Retail", "Online Services", "Financial Services", "Travel", "Healthcare", "Other"],
                        index=0,
                        help="Category of merchant receiving the payment"
                    )
                    
                    is_international = st.checkbox(
                        "International Transaction", 
                        value=False,
                        help="Check if transaction crosses international borders"
                    )
                
                with col2:
                    is_card_present = st.radio(
                        "Card Present?",
                        ["Yes", "No"],
                        index=0,
                        help="Was the physical card present for this transaction?"
                    )
                    
                    device_type = st.selectbox(
                        "Device Type",
                        ["ATM", "POS Terminal", "Mobile", "Web Browser", "Unknown"],
                        index=1,
                        help="Device used to initiate the transaction"
                    )
            
            submit_button = st.form_submit_button("Analyze Transaction")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
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
                
                # Add optional context if entered
                if 'merchant_category' in locals():
                    data["merchant_category"] = [merchant_category]
                if 'is_international' in locals():
                    data["is_foreign"] = [is_international]
                if 'is_card_present' in locals():
                    data["card_present"] = [is_card_present == "Yes"]
                if 'device_type' in locals():
                    data["device_type"] = [device_type]
                
                manual_df = pd.DataFrame(data)
                
                # Process and predict
                processed_df = fraud_detector.preprocess_data(manual_df)
                results_df = fraud_detector.predict(processed_df)
                
                # Show result
                st.subheader("Analysis Result")
                
                # Result card with enhanced visualization
                is_suspicious = results_df["predicted_suspicious"].iloc[0] == 1
                probability = results_df["fraud_probability"].iloc[0]
                
                # Determine risk level
                risk_level = "high" if probability >= 0.7 else "medium" if probability >= 0.3 else "low"
                risk_text = "HIGH RISK" if probability >= 0.7 else "MEDIUM RISK" if probability >= 0.3 else "LOW RISK"
                
                # Render enhanced risk indicator gauge
                st.markdown(f"""
                <div class="risk-indicator {risk_level}">
                    <div class="risk-score">{probability:.1%}</div>
                    <div class="risk-label">{risk_text}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Analysis insights
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("Risk Analysis")
                    
                    # Generate insights based on transaction data
                    insights = []
                    
                    # Check for specific fraud patterns
                    if float(processed_df["amount"].iloc[0]) > 5000:
                        insights.append({
                            "type": "alert", 
                            "text": "Large transaction amount exceeds typical patterns"
                        })
                    
                    if processed_df["n_accounts"].iloc[0] > 3:
                        insights.append({
                            "type": "alert",
                            "text": f"Individual has {processed_df['n_accounts'].iloc[0]} accounts, which is unusually high"
                        })
                    
                    if float(processed_df["daily_total"].iloc[0]) > 10000:
                        insights.append({
                            "type": "alert",
                            "text": "Daily transaction total exceeds regulatory monitoring threshold"
                        })
                    
                    # Add time-based patterns
                    transaction_hour = pd.to_datetime(processed_df["timestamp"].iloc[0]).hour
                    if transaction_hour < 6 or transaction_hour > 23:
                        insights.append({
                            "type": "warning",
                            "text": f"Transaction occurred during unusual hours ({transaction_hour}:00)"
                        })
                    
                    # Feature importance insights
                    if "amount" in processed_df.columns and float(processed_df["amount"].iloc[0]) > 1000:
                        insights.append({
                            "type": "warning",
                            "text": "Transaction amount is higher than average for this account type"
                        })
                    
                    # Additional context if available
                    if "is_foreign" in processed_df.columns and processed_df["is_foreign"].iloc[0]:
                        insights.append({
                            "type": "warning",
                            "text": "International transactions have higher fraud risk"
                        })
                    
                    if "card_present" in processed_df.columns and not processed_df["card_present"].iloc[0]:
                        insights.append({
                            "type": "warning",
                            "text": "Card-not-present transactions have elevated risk"
                        })
                    
                    # Generic insights
                    insights.append({
                        "type": "info",
                        "text": "Transaction velocity is within normal range for this individual"
                    })
                    
                    insights.append({
                        "type": "info",
                        "text": f"Bank '{bank_name}' has standard security protocols in place"
                    })
                    
                    # Display insights
                    for insight in insights:
                        st.markdown(f"""
                        <div class="insight-item {insight['type']}">
                            <p>{insight['text']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                
                with col2:
                    st.subheader("Transaction Details")
                    
                    # Format for better display
                    details_df = results_df.copy()
                    details_df["daily_total"] = details_df["daily_total"].apply(lambda x: f"${x:,.2f}")
                    details_df["weekly_total"] = details_df["weekly_total"].apply(lambda x: f"${x:,.2f}")
                    details_df["monthly_total"] = details_df["monthly_total"].apply(lambda x: f"${x:,.2f}")
                    details_df["amount"] = details_df["amount"].apply(lambda x: f"${x:,.2f}")
                    details_df["timestamp"] = pd.to_datetime(details_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Display as key-value pairs in a more structured format
                    st.markdown(f"""
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px;">
                        <p><b>Individual ID:</b> {individual_id}</p>
                        <p><b>Account ID:</b> {account_id}</p>
                        <p><b>Bank Name:</b> {bank_name}</p>
                        <p><b>Amount:</b> ${amount:,.2f}</p>
                        <p><b>Daily Total:</b> {details_df['daily_total'].iloc[0]}</p>
                        <p><b>Number of Accounts:</b> {details_df['n_accounts'].iloc[0]}</p>
                        <p><b>Timestamp:</b> {details_df['timestamp'].iloc[0]}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Add transaction pattern chart
                st.subheader("Transaction Pattern Analysis")
                
                # Create sample historical data for visualization
                if "tx_history" not in st.session_state:
                    # Generate sample historical data
                    dates = pd.date_range(end=pd.to_datetime(timestamp), periods=10, freq='D')
                    amounts = [amount * (0.5 + random.random()) for _ in range(10)]
                    st.session_state.tx_history = pd.DataFrame({
                        'date': dates,
                        'amount': amounts
                    })
                
                # Plot historical transaction pattern
                fig = px.line(
                    st.session_state.tx_history, 
                    x='date', 
                    y='amount',
                    markers=True,
                    title="Historical Transaction Pattern",
                )
                
                # Add current transaction as highlight point
                fig.add_trace(
                    go.Scatter(
                        x=[pd.to_datetime(timestamp)],
                        y=[amount],
                        mode='markers',
                        marker=dict(color='red', size=12),
                        name='Current Transaction'
                    )
                )
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Amount ($)",
                    height=300,
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Recommendations based on analysis
                st.subheader("Recommended Actions")
                
                action_cols = st.columns(3)
                
                with action_cols[0]:
                    if probability >= 0.7:
                        st.warning("⚠️ Flag for immediate review")
                    elif probability >= 0.3:
                        st.info("🔍 Schedule for routine check")
                    else:
                        st.success("✅ Transaction appears safe")
                
                with action_cols[1]:
                    if probability >= 0.5:
                        st.warning("⚠️ Consider contacting customer")
                    else:
                        st.success("✅ No customer contact needed")
                
                with action_cols[2]:
                    if probability >= 0.8:
                        st.error("🚫 Consider transaction hold")
                    else:
                        st.success("✅ Process transaction normally")
                
                # Save to database
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Save Analysis to Database", key="save_analysis"):
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
                            st.success("✅ Successfully saved analysis result to database!")
                            # Generate new transaction ID for next analysis
                            st.session_state.tx_id = f"TX{uuid.uuid4().hex[:8].upper()}"
                        else:
                            st.error("❌ Error saving analysis to database.")
                
                with col2:
                    # Reset form for new transaction
                    if st.button("Analyze Another Transaction", key="analyze_another"):
                        st.session_state.tx_id = f"TX{uuid.uuid4().hex[:8].upper()}"
                        # Clear transaction history to generate new one
                        if "tx_history" in st.session_state:
                            del st.session_state.tx_history
                        st.rerun()
            
            except Exception as e:
                logger.error(f"Error in manual analysis: {str(e)}")
                st.error(f"Error analyzing transaction: {str(e)}")
    
    # Results History tab
    with tabs[3]:
        st.header("📜 Analysis History")
        
        # Add custom CSS for history tab
        st.markdown("""
        <style>
        .filter-container {
            background-color: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #1976D2;
        }
        .transaction-detail-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #e4e7eb 100%);
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .status-tag {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            margin-right: 5px;
        }
        .status-tag.pending {
            background-color: #FFA000;
            color: white;
        }
        .status-tag.reviewed {
            background-color: #1E88E5;
            color: white;
        }
        .status-tag.confirmed {
            background-color: #D32F2F;
            color: white;
        }
        .status-tag.false_positive {
            background-color: #388E3C;
            color: white;
        }
        .detail-section {
            margin-top: 10px;
            border-top: 1px solid #e0e0e0;
            padding-top: 10px;
        }
        .detail-row {
            display: flex;
            margin-bottom: 8px;
        }
        .detail-label {
            width: 140px;
            font-weight: bold;
            color: #555;
        }
        .detail-value {
            flex: 1;
        }
        .detail-value.money {
            color: #1976D2;
            font-weight: bold;
        }
        .detail-value.high-risk {
            color: #D32F2F;
            font-weight: bold;
        }
        .detail-value.medium-risk {
            color: #FFA000;
            font-weight: bold;
        }
        .detail-value.low-risk {
            color: #388E3C;
            font-weight: bold;
        }
        .history-stats {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
        }
        .history-stat-item {
            text-align: center;
            background-color: #f1f1f1;
            border-radius: 8px;
            padding: 10px;
            flex: 1;
            margin: 0 5px;
        }
        .history-stat-value {
            font-size: 20px;
            font-weight: bold;
            color: #1976D2;
        }
        .history-stat-label {
            font-size: 14px;
            color: #333;
        }
        .pagination-controls {
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 20px 0;
        }
        .page-info {
            margin: 0 20px;
            font-weight: bold;
        }
        .transaction-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 5px;
        }
        .transaction-badge.suspicious {
            background-color: #FFD740;
            color: #333;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Get database stats for filter presets and insights
        stats = db_manager.get_database_stats()
        
        # Display history stats
        if stats and stats.get("total_records", 0) > 0:
            # Calculate metrics
            suspicious_count = stats.get("suspicious_count", 0)
            confirmed_count = stats["status_distribution"].get("confirmed", 0)
            false_positive_count = stats["status_distribution"].get("false_positive", 0)
            
            if suspicious_count > 0:
                accuracy = (confirmed_count / suspicious_count) * 100
            else:
                accuracy = 0
                
            # Display metrics in attractive cards
            st.markdown("""
            <div class="history-stats">
                <div class="history-stat-item">
                    <div class="history-stat-value">{:,}</div>
                    <div class="history-stat-label">Total Transactions</div>
                </div>
                <div class="history-stat-item">
                    <div class="history-stat-value">{:,}</div>
                    <div class="history-stat-label">Suspicious Alerts</div>
                </div>
                <div class="history-stat-item">
                    <div class="history-stat-value">{:,}</div>
                    <div class="history-stat-label">Confirmed Frauds</div>
                </div>
                <div class="history-stat-item">
                    <div class="history-stat-value">{:.1f}%</div>
                    <div class="history-stat-label">Detection Accuracy</div>
                </div>
            </div>
            """.format(
                stats.get("total_records", 0),
                suspicious_count,
                confirmed_count,
                accuracy
            ), unsafe_allow_html=True)
            
            # Add date range insights
            if stats.get("date_range") and stats["date_range"][0]:
                start_date = datetime.strptime(stats["date_range"][0].split()[0], "%Y-%m-%d").date()
                end_date = datetime.strptime(stats["date_range"][1].split()[0], "%Y-%m-%d").date()
                days_covered = (end_date - start_date).days + 1
                
                st.markdown(f"""
                <div style="text-align: center; margin-bottom: 20px; font-size: 14px; color: #555;">
                    Data covers {days_covered} days from {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}
                </div>
                """, unsafe_allow_html=True)
        
        # Enhanced filter interface
        st.markdown('<div class="filter-container">', unsafe_allow_html=True)
        st.subheader("🔍 Filter Results")
        
        filter_cols = st.columns([2, 1, 1, 1])
        
        with filter_cols[0]:
            # Date range filter with better defaults
            default_start = None
            default_end = None
            
            if stats and "date_range" in stats and stats["date_range"][0]:
                default_start = datetime.strptime(stats["date_range"][0].split()[0], "%Y-%m-%d").date()
                default_end = datetime.strptime(stats["date_range"][1].split()[0], "%Y-%m-%d").date()
            
            date_range = st.date_input(
                "Date Range",
                value=(default_start, default_end) if default_start and default_end else None,
                format="YYYY-MM-DD",
                help="Filter transactions by date range"
            )
        
        with filter_cols[1]:
            # Status filter with friendly labels
            status_options = {
                "All": "All Statuses",
                "pending": "Pending Review",
                "reviewed": "Reviewed",
                "confirmed": "Confirmed Fraud",
                "false_positive": "False Positive"
            }
            
            status_filter = st.selectbox(
                "Status",
                list(status_options.keys()),
                format_func=lambda x: status_options[x],
                help="Filter by review status"
            )
        
        with filter_cols[2]:
            # Suspicious filter
            suspicious_options = {
                "All": "All Transactions",
                "Suspicious Only": "Suspicious Only",
                "Normal Only": "Normal Only"
            }
            
            suspicious_filter = st.selectbox(
                "Risk Level",
                list(suspicious_options.keys()),
                format_func=lambda x: suspicious_options[x],
                help="Filter by transaction risk level"
            )
            
        with filter_cols[3]:
            # Additional filter for bank
            if stats and stats.get("total_records", 0) > 0:
                # Get unique banks from database
                try:
                    banks = db_manager.execute_query(
                        f"SELECT DISTINCT bank_name FROM {FRAUD_TABLE} ORDER BY bank_name",
                        fetch=True
                    )
                    bank_options = ["All Banks"] + [bank[0] for bank in banks]
                    
                    bank_filter = st.selectbox(
                        "Bank",
                        bank_options,
                        help="Filter by bank name"
                    )
                except Exception as e:
                    logger.error(f"Error fetching bank list: {str(e)}")
                    bank_filter = "All Banks"
            else:
                bank_filter = "All Banks"
        
        # Apply button for filters
        apply_filters = st.button("🔍 Apply Filters", type="primary")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters
        filters = {}
        
        if isinstance(date_range, tuple) and len(date_range) == 2:
            filters["date_range"] = (date_range[0].isoformat(), date_range[1].isoformat())
        elif hasattr(date_range, '__len__') and len(date_range) == 2:
            filters["date_range"] = (date_range[0].isoformat(), date_range[1].isoformat())
            
        if status_filter != "All":
            filters["status"] = status_filter
        
        if suspicious_filter == "Suspicious Only":
            filters["suspicious"] = 1
        elif suspicious_filter == "Normal Only":
            filters["suspicious"] = 0
            
        if bank_filter != "All Banks":
            # Add bank filter to the query
            if "bank_filter" not in filters:
                filters["bank_filter"] = bank_filter
        
        # Reset page when applying new filters
        if apply_filters:
            st.session_state.page = 0
        
        # Get paginated results
        if "page" not in st.session_state:
            st.session_state.page = 0
        
        # If filters applied, fetch results
        results_df, total_pages = db_manager.get_paginated_results(st.session_state.page, filters)
        
        # Display results
        if not results_df.empty:
            # Create tabs for different views
            history_tabs = st.tabs(["📋 Table View", "📊 Analytics", "📑 Detailed View"])
            
            with history_tabs[0]:
                # Enhanced table display
                st.subheader("Transaction History")
                st.write(f"Showing {len(results_df)} results (page {st.session_state.page + 1} of {total_pages})")
                
                # Format for display
                display_df = results_df.copy()
                display_df["timestamp"] = pd.to_datetime(display_df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                display_df["processed_at"] = pd.to_datetime(display_df["processed_at"]).dt.strftime("%Y-%m-%d %H:%M:%S")
                display_df["amount"] = display_df["amount"].apply(lambda x: f"${x:,.2f}")
                display_df["risk_score"] = display_df["fraud_probability"].apply(lambda x: f"{x:.1%}")
                
                # Select columns for display
                display_cols = [
                    "transaction_id", "individual_id", "bank_name", "amount", 
                    "risk_score", "status", "timestamp"
                ]
                
                # Create column configuration
                column_config = {
                    "risk_score": st.column_config.ProgressColumn(
                        "Risk Score",
                        help="Fraud probability score",
                        format="%s",
                        min_value=0,
                        max_value=1
                    ),
                    "status": st.column_config.SelectboxColumn(
                        "Status",
                        help="Current review status",
                        options=["pending", "reviewed", "confirmed", "false_positive"],
                        required=True
                    ),
                }
                
                # Display interactive dataframe
                edited_df = st.data_editor(
                    display_df[display_cols],
                    use_container_width=True,
                    column_config=column_config,
                    hide_index=True,
                    num_rows="fixed",
                )
                
                # Save edits button
                save_edits = st.button("💾 Save Table Edits")
                
                if save_edits:
                    try:
                        with st.spinner("Saving updates..."):
                            # Process each row for updates
                            for idx, row in edited_df.iterrows():
                                # Get original row
                                original_row = display_df.iloc[idx]
                                
                                # Check if status was modified
                                if row["status"] != original_row["status"]:
                                    # Update status in database
                                    db_manager.execute_query(
                                        f"UPDATE {FRAUD_TABLE} SET status = ? WHERE transaction_id = ?",
                                        (row["status"], row["transaction_id"])
                                    )
                            
                            st.success("✅ Changes saved successfully!")
                            time.sleep(1)  # Brief pause for visual feedback
                            st.rerun()  # Refresh to show updated data
                            
                    except Exception as e:
                        logger.error(f"Error saving table edits: {str(e)}")
                        st.error(f"❌ Error saving changes: {str(e)}")
                
                # Pagination controls with enhanced UI
                st.markdown('<div class="pagination-controls">', unsafe_allow_html=True)
                
                prev_col, info_col, next_col = st.columns([1, 1, 1])
                
                with prev_col:
                    if st.session_state.page > 0:
                        if st.button("◀ Previous Page"):
                            st.session_state.page -= 1
                            st.rerun()
                
                with info_col:
                    st.markdown(f"""
                    <div class="page-info">
                        Page {st.session_state.page + 1} of {total_pages}
                    </div>
                    """, unsafe_allow_html=True)
                
                with next_col:
                    if st.session_state.page < total_pages - 1:
                        if st.button("Next Page ▶"):
                            st.session_state.page += 1
                            st.rerun()
                            
                st.markdown('</div>', unsafe_allow_html=True)
                
            with history_tabs[1]:
                st.subheader("Historical Analytics")
                
                # Create analytical visualizations of historical data
                try:
                    # Status distribution
                    status_counts = results_df["status"].value_counts().reset_index()
                    status_counts.columns = ["Status", "Count"]
                    
                    # Map status to more readable names
                    status_map = {
                        "pending": "Pending Review",
                        "reviewed": "Reviewed",
                        "confirmed": "Confirmed Fraud",
                        "false_positive": "False Positive"
                    }
                    status_counts["Status"] = status_counts["Status"].map(status_map)
                    
                    chart_cols = st.columns(2)
                    
                    with chart_cols[0]:
                        # Status distribution pie chart
                        fig = px.pie(
                            status_counts,
                            values="Count",
                            names="Status",
                            title="Review Status Distribution",
                            color="Status",
                            color_discrete_map={
                                "Pending Review": "#FFA000",
                                "Reviewed": "#1E88E5",
                                "Confirmed Fraud": "#D32F2F",
                                "False Positive": "#388E3C"
                            },
                            hole=0.4
                        )
                        
                        fig.update_layout(
                            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                            margin=dict(l=20, r=20, t=40, b=20),
                            height=350
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with chart_cols[1]:
                        # Risk score distribution
                        fig = px.histogram(
                            results_df,
                            x="fraud_probability",
                            nbins=20,
                            title="Risk Score Distribution",
                            color_discrete_sequence=["#1E88E5"]
                        )
                        
                        # Add vertical lines for risk thresholds
                        fig.add_vline(x=0.3, line_dash="dash", line_color="#FFA000", 
                                      annotation_text="Medium Risk", annotation_position="top right")
                        fig.add_vline(x=0.7, line_dash="dash", line_color="#D32F2F", 
                                      annotation_text="High Risk", annotation_position="top right")
                        
                        fig.update_layout(
                            xaxis_title="Risk Score",
                            yaxis_title="Number of Transactions",
                            margin=dict(l=20, r=20, t=40, b=20),
                            height=350
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Create additional analysis charts
                    chart_cols2 = st.columns(2)
                    
                    with chart_cols2[0]:
                        # Bank distribution for suspicious transactions
                        bank_data = results_df[results_df["predicted_suspicious"] == 1]["bank_name"].value_counts().reset_index()
                        bank_data.columns = ["Bank", "Suspicious Transactions"]
                        
                        if not bank_data.empty:
                            fig = px.bar(
                                bank_data,
                                y="Bank",
                                x="Suspicious Transactions",
                                title="Suspicious Transactions by Bank",
                                orientation="h",
                                color="Suspicious Transactions",
                                color_continuous_scale="Reds"
                            )
                            
                            fig.update_layout(
                                yaxis_title="",
                                xaxis_title="Number of Suspicious Transactions",
                                height=350,
                                margin=dict(l=20, r=20, t=40, b=20),
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.info("No suspicious transactions data available for this filter.")
                            
                    with chart_cols2[1]:
                        # Time series of fraud detections
                        try:
                            # Convert timestamp to datetime and extract date
                            results_df["date"] = pd.to_datetime(results_df["timestamp"]).dt.date
                            
                            # Group by date and count transactions
                            time_data = results_df.groupby("date").agg({
                                "transaction_id": "count",
                                "predicted_suspicious": "sum"
                            }).reset_index()
                            
                            time_data.columns = ["Date", "Total", "Suspicious"]
                            
                            # Calculate percentage
                            time_data["Suspicious %"] = (time_data["Suspicious"] / time_data["Total"] * 100).round(1)
                            
                            # Create time series chart
                            fig = go.Figure()
                            
                            # Add bars for total transactions
                            fig.add_trace(
                                go.Bar(
                                    x=time_data["Date"],
                                    y=time_data["Total"],
                                    name="All Transactions",
                                    marker_color="#42A5F5"
                                )
                            )
                            
                            # Add bars for suspicious transactions
                            fig.add_trace(
                                go.Bar(
                                    x=time_data["Date"],
                                    y=time_data["Suspicious"],
                                    name="Suspicious",
                                    marker_color="#EF5350"
                                )
                            )
                            
                            # Add line for suspicious percentage
                            fig.add_trace(
                                go.Scatter(
                                    x=time_data["Date"],
                                    y=time_data["Suspicious %"],
                                    name="Suspicious %",
                                    yaxis="y2",
                                    line=dict(color="#FFB300", width=3),
                                    mode="lines+markers"
                                )
                            )
                            
                            fig.update_layout(
                                title="Transaction History Timeline",
                                barmode="group",
                                xaxis_title="Date",
                                yaxis_title="Number of Transactions",
                                yaxis2=dict(
                                    title="Suspicious %",
                                    titlefont=dict(color="#FFB300"),
                                    tickfont=dict(color="#FFB300"),
                                    anchor="x",
                                    overlaying="y",
                                    side="right",
                                    range=[0, max(time_data["Suspicious %"]) * 1.2]
                                ),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                                height=350,
                                margin=dict(l=20, r=50, t=40, b=20),
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                        except Exception as e:
                            logger.error(f"Error creating time series chart: {str(e)}")
                            st.error(f"Error creating time series chart: {str(e)}")
                    
                except Exception as e:
                    logger.error(f"Error creating analytics charts: {str(e)}")
                    st.error(f"Error creating analytics visualizations: {str(e)}")
                    
            with history_tabs[2]:
                # Enhanced transaction detail view
                st.subheader("Transaction Details")
                
                # Create a more user-friendly transaction selector
                tx_options = []
                for _, tx in results_df.iterrows():
                    # Format: "TX123456 - John Doe (Bank A) - $1,000.00"
                    suspicious_tag = "🚩" if tx["predicted_suspicious"] == 1 else ""
                    tx_label = f"{tx['transaction_id']} - {tx['individual_id']} - {tx['bank_name']} - ${tx['amount']:,.2f} {suspicious_tag}"
                    tx_options.append((tx['transaction_id'], tx_label))
                
                # Create the selectbox with custom format
                selected_tx = st.selectbox(
                    "Select Transaction to View",
                    options=[tx[0] for tx in tx_options],
                    format_func=lambda x: next((tx[1] for tx in tx_options if tx[0] == x), x),
                    index=0 if tx_options else None
                )
                
                if selected_tx:
                    # Get transaction data
                    tx_data = results_df[results_df["transaction_id"] == selected_tx].iloc[0]
                    
                    # Determine risk level for styling
                    risk_level = ""
                    if tx_data["fraud_probability"] >= 0.7:
                        risk_level = "high-risk"
                    elif tx_data["fraud_probability"] >= 0.3:
                        risk_level = "medium-risk"
                    else:
                        risk_level = "low-risk"
                    
                    # Create transaction detail card
                    st.markdown('<div class="transaction-detail-card">', unsafe_allow_html=True)
                    
                    # Header with transaction ID and status
                    st.markdown(f"""
                    <h3>Transaction {tx_data['transaction_id']}
                        <span class="status-tag {tx_data['status']}">{tx_data['status'].upper()}</span>
                        {f'<span class="transaction-badge suspicious">SUSPICIOUS</span>' if tx_data["predicted_suspicious"] == 1 else ''}
                    </h3>
                    """, unsafe_allow_html=True)
                    
                    # Risk score visualization
                    risk_score = tx_data["fraud_probability"]
                    st.markdown(f"""
                    <div style="margin: 15px 0;">
                        <div style="font-weight: bold; margin-bottom: 5px;">Risk Score: <span class="{risk_level}">{risk_score:.1%}</span></div>
                        <div style="background-color: #e0e0e0; height: 10px; border-radius: 5px; overflow: hidden;">
                            <div style="background: linear-gradient(90deg, #4CAF50 0%, #FFC107 50%, #F44336 100%); width: {risk_score * 100}%; height: 100%;"></div>
                        </div>
                        <div style="display: flex; justify-content: space-between; font-size: 12px; margin-top: 2px;">
                            <span>Low Risk</span>
                            <span>Medium Risk</span>
                            <span>High Risk</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    detail_cols = st.columns(2)
                    
                    with detail_cols[0]:
                        # Transaction details
                        st.markdown('<div class="detail-section">', unsafe_allow_html=True)
                        st.markdown('<h4>Transaction Information</h4>', unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div class="detail-row">
                            <div class="detail-label">Individual ID:</div>
                            <div class="detail-value">{tx_data['individual_id']}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Account ID:</div>
                            <div class="detail-value">{tx_data['account_id']}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Bank Name:</div>
                            <div class="detail-value">{tx_data['bank_name']}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Amount:</div>
                            <div class="detail-value money">${tx_data['amount']:,.2f}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Timestamp:</div>
                            <div class="detail-value">{pd.to_datetime(tx_data['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with detail_cols[1]:
                        # Risk details
                        st.markdown('<div class="detail-section">', unsafe_allow_html=True)
                        st.markdown('<h4>Risk Analysis</h4>', unsafe_allow_html=True)
                        
                        st.markdown(f"""
                        <div class="detail-row">
                            <div class="detail-label">Daily Total:</div>
                            <div class="detail-value money">${tx_data['daily_total']:,.2f}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Weekly Total:</div>
                            <div class="detail-value money">${tx_data['weekly_total']:,.2f}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Monthly Total:</div>
                            <div class="detail-value money">${tx_data['monthly_total']:,.2f}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Number of Accounts:</div>
                            <div class="detail-value">{tx_data['n_accounts']}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Processed At:</div>
                            <div class="detail-value">{pd.to_datetime(tx_data['processed_at']).strftime('%Y-%m-%d %H:%M:%S')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    # Analyst notes section
                    st.markdown('<div class="detail-section">', unsafe_allow_html=True)
                    st.markdown('<h4>Analyst Review</h4>', unsafe_allow_html=True)
                    
                    # Notes input
                    current_notes = tx_data["analyst_notes"] if tx_data["analyst_notes"] else ""
                    new_notes = st.text_area("Notes", value=current_notes, placeholder="Enter your analysis notes here...")
                    
                    # Status update with nicer UI
                    status_options = {
                        "pending": "⏳ Pending Review",
                        "reviewed": "👁️ Reviewed",
                        "confirmed": "🚨 Confirmed Fraud",
                        "false_positive": "✅ False Positive"
                    }
                    
                    new_status = st.selectbox(
                        "Update Review Status",
                        options=list(status_options.keys()),
                        format_func=lambda x: status_options[x],
                        index=list(status_options.keys()).index(tx_data["status"])
                    )
                    
                    # Save updates button
                    if st.button("📝 Save Review Updates", type="primary"):
                        try:
                            with st.spinner("Saving review..."):
                                db_manager.execute_query(
                                    f"UPDATE {FRAUD_TABLE} SET analyst_notes = ?, status = ? WHERE transaction_id = ?",
                                    (new_notes, new_status, selected_tx)
                                )
                                st.success("✅ Transaction review updated successfully!")
                                time.sleep(0.5)  # Brief pause for visual feedback
                                st.rerun()  # Refresh to show updates
                        except Exception as e:
                            logger.error(f"Error updating transaction: {str(e)}")
                            st.error(f"❌ Error updating transaction: {str(e)}")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No transaction records found with the current filters. Try adjusting your filter criteria.")
    
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
