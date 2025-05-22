import sqlite3
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

# Define database files
DB_FILES = {
    "transactions": "transactions.db",
    "monitoring": "transaction_monitoring.db",
    "fraud": "fraud_detection.db"
}

# Create demo data
def generate_demo_transactions(n=1000):
    """Generate demo transaction data"""
    
    # Define the possible values
    individual_ids = [f"IND{i:04d}" for i in range(1, 51)]
    account_ids = [f"ACC{i:06d}" for i in range(1, 121)]
    bank_names = ["Global Bank", "United Finance", "City Credit", "Metro Banking", "Coastal Trust"]
    
    # Create mappings of accounts to individuals (some individuals have multiple accounts)
    account_to_individual = {}
    for account_id in account_ids:
        # Assign an individual, with some individuals having multiple accounts
        individual_id = random.choice(individual_ids)
        account_to_individual[account_id] = individual_id
    
    # Generate transactions
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)
    
    transactions = []
    for i in range(n):
        account_id = random.choice(account_ids)
        individual_id = account_to_individual[account_id]
        
        # Generate a random timestamp in the past 90 days
        random_days = random.randint(0, 90)
        transaction_date = end_date - timedelta(days=random_days)
        
        transactions.append({
            "transaction_id": f"TXN{i:08d}",
            "individual_id": individual_id,
            "account_id": account_id,
            "bank_name": random.choice(bank_names),
            "amount": round(random.uniform(10, 5000), 2),
            "timestamp": transaction_date.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return pd.DataFrame(transactions)

def init_transactions_db():
    """Initialize the transactions database for multiple accounts analysis"""
    db_file = DB_FILES["transactions"]
    
    if os.path.exists(db_file):
        logger.info(f"Transactions database already exists: {db_file}")
        return
    
    logger.info(f"Creating transactions database: {db_file}")
    
    conn = sqlite3.connect(db_file)
    
    # Create tables
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
    
    # Generate demo data
    df = generate_demo_transactions(2000)
    logger.info(f"Generated {len(df)} demo transactions")
    
    # Insert accounts
    accounts_df = df[['individual_id', 'account_id', 'bank_name']].drop_duplicates()
    accounts_df.to_sql('accounts', conn, if_exists='append', index=False)
    logger.info(f"Inserted {len(accounts_df)} accounts")
    
    # Insert transactions
    df.to_sql('transactions', conn, if_exists='append', index=False)
    logger.info(f"Inserted {len(df)} transactions")
    
    conn.commit()
    conn.close()
    logger.info("Transactions database initialized successfully")

def init_monitoring_db():
    """Initialize the transaction monitoring database"""
    db_file = DB_FILES["monitoring"]
    
    if os.path.exists(db_file):
        logger.info(f"Monitoring database already exists: {db_file}")
        return
    
    logger.info(f"Creating monitoring database: {db_file}")
    
    conn = sqlite3.connect(db_file)
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
    
    # Insert default limits
    cursor.execute('''
        INSERT INTO settings (setting_name, setting_value)
        VALUES 
            ('daily_limit', 1000.0),
            ('weekly_limit', 5000.0),
            ('monthly_limit', 10000.0)
    ''')
    
    # Insert sample violations (generated from demo data)
    # Get the demo data
    df = generate_demo_transactions(500)
    
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
    
    # Add bank and account counts
    daily_totals['num_banks'] = daily_totals['bank_name'].str.count(',') + 1
    daily_totals['num_accounts'] = daily_totals['account_id'].str.count(',') + 1
    
    # Identify violations (amount > 1000)
    daily_violations = daily_totals[daily_totals['amount'] > 1000]
    
    # Insert sample violations
    for _, row in daily_violations.iterrows():
        violation_type = 'Direct Violation'
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
            row['transaction_id'], 1000.0, violation_type
        ))
    
    # Insert sample file upload info
    cursor.execute('''
        INSERT INTO uploaded_files (filename, record_count)
        VALUES (?, ?)
    ''', ('sample_data.csv', len(df)))
    
    conn.commit()
    conn.close()
    logger.info(f"Monitoring database initialized with {len(daily_violations)} sample violations")

def init_fraud_detection_db():
    """Initialize the fraud detection database"""
    db_file = DB_FILES["fraud"]
    
    if os.path.exists(db_file):
        logger.info(f"Fraud detection database already exists: {db_file}")
        return
    
    logger.info(f"Creating fraud detection database: {db_file}")
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Create fraud detection results table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fraud_detection_results (
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
    ''')
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            full_name TEXT,
            role TEXT CHECK(role IN ('analyst', 'supervisor', 'admin')),
            last_login TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Insert sample admin user
    import hashlib
    password_hash = hashlib.sha256("admin123".encode()).hexdigest()
    
    cursor.execute('''
        INSERT INTO users (username, password_hash, full_name, role, last_login, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', password_hash, 'System Administrator', 'admin', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 1))
    
    # Insert sample fraud detection results
    # Get the demo data
    df = generate_demo_transactions(300)
    
    # Add some fraud probabilities (randomly assign for demo purposes)
    for i, row in df.iterrows():
        # Assign higher fraud probability to larger transactions
        base_prob = 0.05
        if row['amount'] > 3000:
            base_prob = 0.8
        elif row['amount'] > 1000:
            base_prob = 0.3
            
        # Add some randomness
        prob = min(0.95, max(0.01, base_prob + random.uniform(-0.1, 0.1)))
        df.at[i, 'fraud_probability'] = prob
        df.at[i, 'predicted_suspicious'] = 1 if prob > 0.3 else 0
        
        # Add some totals
        df.at[i, 'daily_total'] = row['amount'] * 1.2
        df.at[i, 'weekly_total'] = row['amount'] * 3.5
        df.at[i, 'monthly_total'] = row['amount'] * 12
        df.at[i, 'n_accounts'] = random.randint(1, 3)
    
    # Insert the fraud detection results
    fraud_df = df[['transaction_id', 'individual_id', 'account_id', 'bank_name', 'amount', 
                  'daily_total', 'weekly_total', 'monthly_total', 'n_accounts', 
                  'fraud_probability', 'predicted_suspicious', 'timestamp']]
    
    # Insert records one by one (to handle SQLite type conversion better)
    for _, row in fraud_df.iterrows():
        cursor.execute('''
            INSERT INTO fraud_detection_results (
                transaction_id, individual_id, account_id, bank_name, amount,
                daily_total, weekly_total, monthly_total, n_accounts,
                fraud_probability, predicted_suspicious, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['transaction_id'], row['individual_id'], row['account_id'], row['bank_name'], row['amount'],
            row['daily_total'], row['weekly_total'], row['monthly_total'], row['n_accounts'],
            row['fraud_probability'], row['predicted_suspicious'], row['timestamp']
        ))
    
    conn.commit()
    conn.close()
    logger.info(f"Fraud detection database initialized with {len(fraud_df)} sample records")

if __name__ == "__main__":
    # Initialize all databases
    init_transactions_db()
    init_monitoring_db()
    init_fraud_detection_db()
    
    print("All databases initialized successfully!")