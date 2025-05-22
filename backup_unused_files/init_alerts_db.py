import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

# Database file
DB_FILE = "financial_alerts.db"

def init_alerts_database():
    """Initialize the financial alerts database"""
    
    if os.path.exists(DB_FILE):
        logger.info(f"Financial alerts database already exists: {DB_FILE}")
        return
    
    logger.info(f"Creating financial alerts database: {DB_FILE}")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT NOT NULL,
            individual_id TEXT NOT NULL,
            account_id TEXT,
            description TEXT NOT NULL,
            severity TEXT CHECK(severity IN ('low', 'medium', 'high', 'critical')) NOT NULL,
            status TEXT CHECK(status IN ('new', 'in_progress', 'resolved', 'false_positive')) DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP,
            assigned_to TEXT,
            related_data TEXT
        )
    ''')
    
    # Create alert_types table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_name TEXT UNIQUE NOT NULL,
            description TEXT,
            default_severity TEXT CHECK(default_severity IN ('low', 'medium', 'high', 'critical')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create alert_rules table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT UNIQUE NOT NULL,
            alert_type TEXT NOT NULL,
            description TEXT,
            rule_criteria TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP
        )
    ''')
    
    # Create alert_actions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alert_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            action_details TEXT,
            performed_by TEXT,
            performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (alert_id) REFERENCES alerts(id)
        )
    ''')
    
    # Insert default alert types
    alert_types = [
        ('suspicious_pattern', 'Suspicious transaction pattern detected', 'medium'),
        ('large_transaction', 'Unusually large transaction amount', 'high'),
        ('multiple_accounts', 'Activity across multiple accounts', 'medium'),
        ('limit_violation', 'Transaction limit exceeded', 'high'),
        ('unusual_location', 'Transaction from unusual location', 'medium'),
        ('rapid_movements', 'Rapid movement of funds', 'high'),
        ('structuring', 'Potential structuring activity', 'critical'),
        ('dormant_activity', 'Activity on previously dormant account', 'medium'),
        ('unauthorized_access', 'Potential unauthorized access', 'critical')
    ]
    
    cursor.executemany('''
        INSERT INTO alert_types (type_name, description, default_severity)
        VALUES (?, ?, ?)
    ''', alert_types)
    
    # Insert default rules
    alert_rules = [
        ('high_value_transaction', 'large_transaction', 'Transactions exceeding $10,000', 'amount > 10000'),
        ('multiple_accounts_same_day', 'multiple_accounts', 'Activity on 3+ accounts in same day', 'account_count > 3 AND timeframe = "daily"'),
        ('structured_deposits', 'structuring', 'Multiple deposits just under limits', 'amount BETWEEN 9000 AND 9999 AND count > 2'),
        ('rapid_withdrawals', 'rapid_movements', 'Multiple withdrawals in short period', 'withdrawal_count > 3 AND timeframe < "1 day"'),
        ('dormant_account_activity', 'dormant_activity', 'Activity after 90+ days dormancy', 'days_since_last_activity > 90')
    ]
    
    cursor.executemany('''
        INSERT INTO alert_rules (rule_name, alert_type, description, rule_criteria)
        VALUES (?, ?, ?, ?)
    ''', alert_rules)
    
    # Generate sample alerts
    individual_ids = [f"IND{i:04d}" for i in range(1, 51)]
    account_ids = [f"ACC{i:06d}" for i in range(1, 121)]
    
    # Map individuals to accounts
    account_to_individual = {}
    for account_id in account_ids:
        individual_id = random.choice(individual_ids)
        account_to_individual[account_id] = individual_id
    
    # Generate sample alerts
    sample_alerts = []
    now = datetime.now()
    
    for i in range(100):
        # Select random account and its owner
        account_id = random.choice(account_ids)
        individual_id = account_to_individual[account_id]
        
        # Select random alert type
        alert_type = random.choice([t[0] for t in alert_types])
        
        # Determine severity based on alert type
        severity_mapping = {t[0]: t[2] for t in alert_types}
        severity = severity_mapping.get(alert_type, 'medium')
        
        # Generate random timestamp in last 30 days
        days_ago = random.randint(0, 30)
        timestamp = now - timedelta(days=days_ago)
        
        # Create description based on alert type
        if alert_type == 'suspicious_pattern':
            description = f"Unusual transaction pattern detected for account {account_id}"
        elif alert_type == 'large_transaction':
            amount = random.randint(10000, 50000)
            description = f"Large transaction of ${amount:,} detected"
        elif alert_type == 'multiple_accounts':
            num_accounts = random.randint(3, 8)
            description = f"Activity detected across {num_accounts} accounts for individual {individual_id}"
        elif alert_type == 'limit_violation':
            limit_type = random.choice(['daily', 'weekly', 'monthly'])
            description = f"{limit_type.capitalize()} transaction limit exceeded"
        else:
            description = f"Alert generated for {alert_type.replace('_', ' ')}"
        
        # Set status (mostly new, some in progress or resolved)
        status_weights = {'new': 0.7, 'in_progress': 0.2, 'resolved': 0.08, 'false_positive': 0.02}
        status = random.choices(
            list(status_weights.keys()),
            weights=list(status_weights.values())
        )[0]
        
        # For resolved alerts, set an updated_at timestamp
        updated_at = timestamp + timedelta(days=random.randint(1, 3)) if status in ['resolved', 'false_positive'] else None
        updated_at_str = updated_at.strftime("%Y-%m-%d %H:%M:%S") if updated_at else None
        
        # Assigned to (for in_progress and resolved)
        assigned_to = None
        if status in ['in_progress', 'resolved', 'false_positive']:
            assigned_to = random.choice(['analyst1', 'analyst2', 'supervisor1'])
        
        # Add to sample alerts
        sample_alerts.append((
            alert_type,
            individual_id,
            account_id,
            description,
            severity,
            status,
            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            updated_at_str,
            assigned_to,
            None  # related_data
        ))
    
    # Insert sample alerts
    cursor.executemany('''
        INSERT INTO alerts (
            alert_type, individual_id, account_id, description,
            severity, status, created_at, updated_at, assigned_to, related_data
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', sample_alerts)
    
    # Add some sample actions for alerts that are in progress or resolved
    sample_actions = []
    alert_ids = [i+1 for i in range(100)]  # Assuming 100 alerts with IDs 1-100
    
    for alert_id in alert_ids:
        # Get status of this alert
        cursor.execute("SELECT status FROM alerts WHERE id = ?", (alert_id,))
        status = cursor.fetchone()[0]
        
        if status in ['in_progress', 'resolved', 'false_positive']:
            # Add investigation action
            sample_actions.append((
                alert_id,
                'investigation',
                'Initial investigation performed',
                random.choice(['analyst1', 'analyst2', 'supervisor1']),
            ))
            
            if status in ['resolved', 'false_positive']:
                # Add resolution action
                resolution_notes = "Alert resolved after investigation" if status == 'resolved' else "Determined to be false positive"
                sample_actions.append((
                    alert_id,
                    'resolution',
                    resolution_notes,
                    random.choice(['analyst1', 'analyst2', 'supervisor1']),
                ))
    
    # Insert sample actions
    cursor.executemany('''
        INSERT INTO alert_actions (
            alert_id, action_type, action_details, performed_by
        )
        VALUES (?, ?, ?, ?)
    ''', sample_actions)
    
    # Commit changes and close
    conn.commit()
    conn.close()
    
    logger.info(f"Financial alerts database initialized with {len(sample_alerts)} sample alerts")

if __name__ == "__main__":
    init_alerts_database()
    print("Financial alerts database initialized successfully!")