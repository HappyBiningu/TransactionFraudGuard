import sqlite3
import pandas as pd
import logging
import os
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

# Database files
ALERTS_DB = "financial_alerts.db"
TRANSACTIONS_DB = "transactions.db"
FRAUD_DB = "fraud_detection.db"
MONITORING_DB = "transaction_monitoring.db"

def init_alerts_database():
    """Initialize the financial alerts database with necessary tables"""
    if os.path.exists(ALERTS_DB):
        logger.info(f"Financial alerts database already exists: {ALERTS_DB}")
    else:
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
    
    # Insert default settings if they don't exist
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
    """Generate alerts for large transactions based on real transaction data"""
    logger.info("Generating large transaction alerts from real transaction data")
    
    # Get alert settings
    alerts_conn = sqlite3.connect(ALERTS_DB)
    cursor = alerts_conn.cursor()
    
    # Check if alert_settings table exists and has data
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alert_settings'")
    if not cursor.fetchone():
        # Use default threshold if settings table doesn't exist yet
        threshold = 10000.0
    else:
        cursor.execute("SELECT threshold_value FROM alert_settings WHERE alert_type = 'large_transaction'")
        result = cursor.fetchone()
        threshold = result[0] if result else 10000.0
    
    # Connect to the transactions database
    tx_conn = sqlite3.connect(TRANSACTIONS_DB)
    
    # Find large transactions that exceed the threshold
    # First make sure the database structure is properly initialized
    init_alerts_database()
    
    # Now check if our alerts table exists - if not, don't include the NOT IN clause
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='large_transaction_alerts'")
    if not cursor.fetchone():
        query = f"""
        SELECT 
            transaction_id,
            account_id,
            amount,
            timestamp
        FROM 
            transactions
        WHERE 
            amount > {threshold}
            AND timestamp >= datetime('now', '-30 day')
        LIMIT 100
        """
    else:
        query = f"""
        SELECT 
            transaction_id,
            account_id,
            amount,
            timestamp
        FROM 
            transactions
        WHERE 
            amount > {threshold}
            AND timestamp >= datetime('now', '-30 day')
            AND transaction_id NOT IN (
                SELECT transaction_id FROM large_transaction_alerts
            )
        LIMIT 100
        """
    
    large_transactions = pd.read_sql_query(query, tx_conn)
    tx_conn.close()
    
    if large_transactions.empty:
        logger.info("No new large transactions found")
        return 0
    
    # Generate alerts for these transactions
    alerts = []
    for _, tx in large_transactions.iterrows():
        alert = (
            tx['timestamp'],
            tx['account_id'],
            tx['transaction_id'],
            tx['amount'],
            threshold,
            'NEW',
            f"Large transaction of ${tx['amount']:.2f} exceeds threshold of ${threshold:.2f}"
        )
        alerts.append(alert)
    
    # Insert new alerts
    cursor.executemany('''
    INSERT INTO large_transaction_alerts 
    (timestamp, account_id, transaction_id, amount, threshold, status, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', alerts)
    
    alerts_conn.commit()
    alerts_conn.close()
    logger.info(f"Generated {len(alerts)} large transaction alerts")
    return len(alerts)

def generate_pattern_deviation_alerts():
    """Generate alerts for unusual transaction patterns based on fraud detection results"""
    logger.info("Generating pattern deviation alerts from fraud detection data")
    
    # Connect to databases
    alerts_conn = sqlite3.connect(ALERTS_DB)
    cursor = alerts_conn.cursor()
    
    fraud_conn = sqlite3.connect(FRAUD_DB)
    
    # First check if our alerts table exists yet - if not, don't include the NOT IN clause
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pattern_deviation_alerts'")
    if not cursor.fetchone():
        query = """
        SELECT 
            transaction_id,
            account_id,
            fraud_probability,
            timestamp
        FROM 
            fraud_detection_results
        WHERE 
            predicted_suspicious = 1
            AND timestamp >= datetime('now', '-30 day')
        """
    else:
        query = """
        SELECT 
            transaction_id,
            account_id,
            fraud_probability,
            timestamp
        FROM 
            fraud_detection_results
        WHERE 
            predicted_suspicious = 1
            AND transaction_id NOT IN (
                SELECT transaction_id FROM pattern_deviation_alerts
            )
            AND timestamp >= datetime('now', '-30 day')
        """
    
    suspicious_tx = pd.read_sql_query(query, fraud_conn)
    fraud_conn.close()
    
    if suspicious_tx.empty:
        logger.info("No new suspicious transactions found")
        return 0
    
    # Generate alerts for these transactions
    alerts = []
    for _, tx in suspicious_tx.iterrows():
        # Determine severity based on probability
        prob = tx['fraud_probability']
        
        if prob >= 0.9:
            severity = "CRITICAL"
        elif prob >= 0.7:
            severity = "HIGH"
        elif prob >= 0.5:
            severity = "MEDIUM"
        else:
            severity = "LOW"
        
        # Determine deviation type (this would normally be more sophisticated)
        deviation_type = "SPENDING_PATTERN"
        description = "Unusual spending pattern detected by fraud detection system"
        
        alert = (
            tx['timestamp'],
            tx['account_id'],
            deviation_type,
            severity,
            'NEW',
            description
        )
        alerts.append(alert)
    
    # Insert new alerts
    cursor.executemany('''
    INSERT INTO pattern_deviation_alerts 
    (timestamp, account_id, deviation_type, severity, status, description)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', alerts)
    
    alerts_conn.commit()
    alerts_conn.close()
    logger.info(f"Generated {len(alerts)} pattern deviation alerts")
    return len(alerts)

def generate_daily_balance_alerts():
    """Generate alerts for accounts with low balances based on transaction data"""
    logger.info("Generating daily balance alerts from transaction data")
    
    # Connect to databases
    alerts_conn = sqlite3.connect(ALERTS_DB)
    cursor = alerts_conn.cursor()
    
    # Check if alert_settings table exists and has data
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alert_settings'")
    if not cursor.fetchone():
        # Use default threshold if settings table doesn't exist yet
        threshold = 1000.0
    else:
        cursor.execute("SELECT threshold_value FROM alert_settings WHERE alert_type = 'daily_balance'")
        result = cursor.fetchone()
        threshold = result[0] if result else 1000.0
    
    tx_conn = sqlite3.connect(TRANSACTIONS_DB)
    
    # Check if our alerts table exists yet - if not, don't include the NOT IN clause
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily_balance_alerts'")
    if not cursor.fetchone():
        query = """
        SELECT 
            account_id,
            SUM(amount) as current_balance
        FROM 
            transactions
        GROUP BY 
            account_id
        HAVING 
            current_balance < ?
        """
        params = [threshold]
    else:
        query = """
        SELECT 
            account_id,
            SUM(amount) as current_balance
        FROM 
            transactions
        GROUP BY 
            account_id
        HAVING 
            current_balance < ?
            AND account_id NOT IN (
                SELECT account_id FROM daily_balance_alerts 
                WHERE timestamp >= datetime('now', '-1 day')
            )
        """
        params = [threshold]
    
    low_balance_accounts = pd.read_sql_query(query, tx_conn, params=params)
    tx_conn.close()
    
    if low_balance_accounts.empty:
        logger.info("No new low balance accounts found")
        return 0
    
    # Generate alerts for these accounts
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    alerts = []
    for _, acct in low_balance_accounts.iterrows():
        alert = (
            now,
            acct['account_id'],
            'LOW_BALANCE',
            acct['current_balance'],
            threshold,
            'NEW',
            f"Account balance (${acct['current_balance']:.2f}) is below threshold (${threshold:.2f})"
        )
        alerts.append(alert)
    
    # Insert new alerts
    cursor.executemany('''
    INSERT INTO daily_balance_alerts 
    (timestamp, account_id, alert_type, current_balance, threshold, status, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', alerts)
    
    alerts_conn.commit()
    alerts_conn.close()
    logger.info(f"Generated {len(alerts)} daily balance alerts")
    return len(alerts)

def generate_account_status_alerts():
    """Generate alerts for account status changes based on transaction monitoring data"""
    logger.info("Generating account status alerts from monitoring data")
    
    # Connect to databases
    alerts_conn = sqlite3.connect(ALERTS_DB)
    cursor = alerts_conn.cursor()
    
    # This would be more sophisticated in a real system with actual account status data
    # For now, we'll derive status changes from transaction and violation data
    tx_conn = sqlite3.connect(TRANSACTIONS_DB)
    monitoring_conn = sqlite3.connect(MONITORING_DB)
    
    # Check if violations table exists in monitoring database
    try:
        # Find accounts with violations from transaction monitoring
        query = """
        SELECT 
            account_id,
            COUNT(*) as violation_count
        FROM 
            violations
        WHERE 
            timestamp >= datetime('now', '-7 day')
        GROUP BY 
            account_id
        HAVING 
            violation_count >= 3
        """
        
        violation_accounts = pd.read_sql_query(query, monitoring_conn)
    except Exception as e:
        logger.error(f"Error querying violations table: {e}")
        # If we can't access violations, use fraud detection results instead
        monitoring_conn.close()
        fraud_conn = sqlite3.connect(FRAUD_DB)
        
        query = """
        SELECT 
            account_id,
            COUNT(*) as violation_count
        FROM 
            fraud_detection_results
        WHERE 
            predicted_suspicious = 1
            AND timestamp >= datetime('now', '-7 day')
        GROUP BY 
            account_id
        HAVING 
            violation_count >= 2
        """
        
        violation_accounts = pd.read_sql_query(query, fraud_conn)
        fraud_conn.close()
    
    monitoring_conn.close()
    
    if violation_accounts.empty:
        logger.info("No accounts with multiple violations found")
        return 0
    
    # Check if our alerts table exists yet
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='account_status_alerts'")
    table_exists = cursor.fetchone() is not None
    
    # Generate alerts for accounts with repeated violations
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    alerts = []
    for _, acct in violation_accounts.iterrows():
        # Check if we already have an alert for this account (only if table exists)
        if table_exists:
            cursor.execute("""
            SELECT id FROM account_status_alerts 
            WHERE account_id = ? AND timestamp >= datetime('now', '-7 day')
            """, (acct['account_id'],))
            
            if cursor.fetchone():
                continue  # Skip if we already have a recent alert
        
        alert = (
            now,
            acct['account_id'],
            'ACTIVE',
            'RESTRICTED',
            f"Multiple limit violations ({acct['violation_count']} in past week)",
            'NEW',
            f"Account restricted due to {acct['violation_count']} limit violations in the past week"
        )
        alerts.append(alert)
    
    # Insert new alerts
    cursor.executemany('''
    INSERT INTO account_status_alerts 
    (timestamp, account_id, previous_status, new_status, reason, status, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', alerts)
    
    alerts_conn.commit()
    alerts_conn.close()
    logger.info(f"Generated {len(alerts)} account status alerts")
    return len(alerts)

def generate_all_alerts():
    """Generate all types of alerts from real data"""
    init_alerts_database()
    
    large_tx = generate_large_transaction_alerts()
    pattern_dev = generate_pattern_deviation_alerts()
    daily_bal = generate_daily_balance_alerts()
    acct_status = generate_account_status_alerts()
    
    return {
        "large_transaction": large_tx,
        "pattern_deviation": pattern_dev,
        "daily_balance": daily_bal,
        "account_status": acct_status,
        "total": large_tx + pattern_dev + daily_bal + acct_status
    }

if __name__ == "__main__":
    results = generate_all_alerts()
    print(f"Generated {results['total']} total alerts:")
    print(f"- {results['large_transaction']} large transaction alerts")
    print(f"- {results['pattern_deviation']} pattern deviation alerts")
    print(f"- {results['daily_balance']} daily balance alerts")
    print(f"- {results['account_status']} account status alerts")