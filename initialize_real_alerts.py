"""
Initialize the enhanced financial alerts system with real data
"""
import sqlite3
import os
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Database files
ALERTS_DB = "financial_alerts.db"
TRANSACTIONS_DB = "transactions.db"
FRAUD_DB = "fraud_detection.db"
MONITORING_DB = "transaction_monitoring.db"

def initialize_alerts_database():
    """Initialize the financial alerts database with necessary tables"""
    # Remove old database if it exists
    if os.path.exists(ALERTS_DB):
        os.remove(ALERTS_DB)
        logger.info(f"Removed existing alerts database: {ALERTS_DB}")
    
    logger.info(f"Creating financial alerts database: {ALERTS_DB}")
    
    conn = sqlite3.connect(ALERTS_DB)
    cursor = conn.cursor()
    
    # Create tables for different alert types
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_balance_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        account_id TEXT,
        alert_type TEXT,
        current_balance REAL,
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
    
    # Create alert settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alert_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_type TEXT UNIQUE,
        threshold_value REAL,
        is_active BOOLEAN,
        last_updated TEXT
    )
    ''')
    
    # Insert default settings
    default_settings = [
        ('large_transaction', 10000.0, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('daily_balance', 1000.0, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('pattern_deviation', 0.8, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        ('account_status', 1.0, 1, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    ]
    
    for setting in default_settings:
        cursor.execute('''
        INSERT OR IGNORE INTO alert_settings 
        (alert_type, threshold_value, is_active, last_updated)
        VALUES (?, ?, ?, ?)
        ''', setting)
    
    conn.commit()
    conn.close()
    logger.info("Financial alerts database tables created successfully")

def generate_large_transaction_alerts():
    """Generate large transaction alerts from real data"""
    logger.info("Generating large transaction alerts from real data")
    
    # Connect to databases
    alerts_conn = sqlite3.connect(ALERTS_DB)
    cursor = alerts_conn.cursor()
    
    # Get threshold from settings
    cursor.execute("SELECT threshold_value FROM alert_settings WHERE alert_type = 'large_transaction'")
    threshold = cursor.fetchone()[0]
    
    # Connect to transactions database
    tx_conn = sqlite3.connect(TRANSACTIONS_DB)
    tx_cursor = tx_conn.cursor()
    
    # Find large transactions
    tx_cursor.execute(f"""
    SELECT 
        transaction_id,
        account_id,
        amount,
        timestamp
    FROM 
        transactions
    WHERE 
        amount > {threshold}
    LIMIT 100
    """)
    
    transactions = tx_cursor.fetchall()
    tx_conn.close()
    
    if not transactions:
        logger.info("No large transactions found")
        return 0
    
    # Generate alerts
    count = 0
    for tx in transactions:
        transaction_id, account_id, amount, timestamp = tx
        
        # Insert alert
        cursor.execute("""
        INSERT INTO large_transaction_alerts 
        (timestamp, account_id, transaction_id, amount, threshold, status, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            account_id,
            transaction_id,
            amount,
            threshold,
            'NEW',
            f"Large transaction of ${amount:.2f} exceeds threshold of ${threshold:.2f}"
        ))
        count += 1
    
    alerts_conn.commit()
    alerts_conn.close()
    
    logger.info(f"Generated {count} large transaction alerts")
    return count

def generate_fraud_alerts():
    """Generate pattern deviation alerts from fraud detection data"""
    logger.info("Generating pattern deviation alerts from fraud data")
    
    # Connect to databases
    alerts_conn = sqlite3.connect(ALERTS_DB)
    cursor = alerts_conn.cursor()
    
    # Connect to fraud database
    fraud_conn = sqlite3.connect(FRAUD_DB)
    fraud_cursor = fraud_conn.cursor()
    
    # Find suspicious transactions
    try:
        fraud_cursor.execute("""
        SELECT 
            account_id,
            fraud_probability,
            timestamp
        FROM 
            fraud_detection_results
        WHERE 
            predicted_suspicious = 1
        LIMIT 100
        """)
        
        suspicious_tx = fraud_cursor.fetchall()
    except Exception as e:
        logger.error(f"Error querying fraud detection results: {e}")
        suspicious_tx = []
    
    fraud_conn.close()
    
    if not suspicious_tx:
        logger.info("No suspicious transactions found")
        return 0
    
    # Generate alerts
    count = 0
    for tx in suspicious_tx:
        account_id, probability, timestamp = tx
        
        # Determine severity
        if probability >= 0.9:
            severity = "CRITICAL"
        elif probability >= 0.7:
            severity = "HIGH"
        elif probability >= 0.5:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        # Insert alert
        cursor.execute("""
        INSERT INTO pattern_deviation_alerts 
        (timestamp, account_id, deviation_type, severity, status, description)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            timestamp,
            account_id,
            "SPENDING_PATTERN",
            severity,
            'NEW',
            "Unusual spending pattern detected by fraud detection system"
        ))
        count += 1
    
    alerts_conn.commit()
    alerts_conn.close()
    
    logger.info(f"Generated {count} pattern deviation alerts")
    return count

def generate_balance_alerts():
    """Generate daily balance alerts from transaction data"""
    logger.info("Generating daily balance alerts from transaction data")
    
    # Connect to databases
    alerts_conn = sqlite3.connect(ALERTS_DB)
    cursor = alerts_conn.cursor()
    
    # Get threshold from settings
    cursor.execute("SELECT threshold_value FROM alert_settings WHERE alert_type = 'daily_balance'")
    threshold = cursor.fetchone()[0]
    
    # Connect to transactions database
    tx_conn = sqlite3.connect(TRANSACTIONS_DB)
    tx_cursor = tx_conn.cursor()
    
    # Find accounts with low balances
    tx_cursor.execute(f"""
    SELECT 
        account_id,
        SUM(amount) as current_balance
    FROM 
        transactions
    GROUP BY 
        account_id
    HAVING 
        current_balance < {threshold}
    LIMIT 100
    """)
    
    low_balances = tx_cursor.fetchall()
    tx_conn.close()
    
    if not low_balances:
        logger.info("No low balance accounts found")
        return 0
    
    # Generate alerts
    count = 0
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for acct in low_balances:
        account_id, balance = acct
        
        # Insert alert
        cursor.execute("""
        INSERT INTO daily_balance_alerts 
        (timestamp, account_id, alert_type, current_balance, threshold, status, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            account_id,
            'LOW_BALANCE',
            balance,
            threshold,
            'NEW',
            f"Account balance (${balance:.2f}) is below threshold (${threshold:.2f})"
        ))
        count += 1
    
    alerts_conn.commit()
    alerts_conn.close()
    
    logger.info(f"Generated {count} daily balance alerts")
    return count

def generate_status_alerts():
    """Generate account status alerts"""
    logger.info("Generating account status alerts")
    
    # Connect to databases
    alerts_conn = sqlite3.connect(ALERTS_DB)
    cursor = alerts_conn.cursor()
    
    # Connect to fraud database to find accounts with potential issues
    fraud_conn = sqlite3.connect(FRAUD_DB)
    fraud_cursor = fraud_conn.cursor()
    
    # Find accounts with multiple suspicious transactions
    try:
        fraud_cursor.execute("""
        SELECT 
            account_id,
            COUNT(*) as suspicious_count
        FROM 
            fraud_detection_results
        WHERE 
            predicted_suspicious = 1
        GROUP BY 
            account_id
        HAVING 
            suspicious_count > 1
        LIMIT 25
        """)
        
        accounts = fraud_cursor.fetchall()
    except Exception as e:
        logger.error(f"Error querying fraud detection results: {e}")
        accounts = []
    
    fraud_conn.close()
    
    if not accounts:
        logger.info("No accounts with status changes found")
        return 0
    
    # Generate alerts
    count = 0
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for acct in accounts:
        account_id, suspicious_count = acct
        
        # Insert alert
        cursor.execute("""
        INSERT INTO account_status_alerts 
        (timestamp, account_id, previous_status, new_status, reason, status, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            now,
            account_id,
            'ACTIVE',
            'RESTRICTED',
            f"Multiple suspicious transactions ({suspicious_count})",
            'NEW',
            f"Account restricted due to {suspicious_count} suspicious transactions"
        ))
        count += 1
    
    alerts_conn.commit()
    alerts_conn.close()
    
    logger.info(f"Generated {count} account status alerts")
    return count

def main():
    """Main function to initialize the alerts database and generate alerts"""
    logger.info("Starting initialization of financial alerts with real data")
    
    # Initialize database
    initialize_alerts_database()
    
    # Generate alerts
    large_tx = generate_large_transaction_alerts()
    fraud = generate_fraud_alerts()
    balance = generate_balance_alerts()
    status = generate_status_alerts()
    
    total = large_tx + fraud + balance + status
    
    # Print summary
    print("-" * 50)
    print("FINANCIAL ALERTS INITIALIZATION COMPLETE")
    print("-" * 50)
    print(f"Generated {total} total alerts from real data:")
    print(f"- {large_tx} large transaction alerts")
    print(f"- {fraud} pattern deviation alerts")
    print(f"- {balance} daily balance alerts")
    print(f"- {status} account status alerts")
    print("-" * 50)
    print("The financial alerts system is now using real transaction data instead of mock data.")
    print("You can access the alerts through the Financial Alerts page in the application.")

if __name__ == "__main__":
    main()