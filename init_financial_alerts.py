"""
Script to initialize the financial alerts database and generate alerts from real data
This script should be run to set up the initial alerts data
"""
import os
import logging
import enhanced_financial_alerts as efa

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Check if alert database already exists
    if os.path.exists(efa.ALERTS_DB):
        logger.info(f"Financial alerts database already exists at {efa.ALERTS_DB}")
        backup_file = f"{efa.ALERTS_DB}.backup"
        os.rename(efa.ALERTS_DB, backup_file)
        logger.info(f"Created backup at {backup_file}")
    
    # Initialize the database structure
    logger.info("Initializing financial alerts database...")
    efa.init_alerts_database()
    
    # Generate alerts from real data
    logger.info("Generating alerts from real transaction data...")
    results = efa.generate_all_alerts()
    
    # Print summary
    print("-" * 50)
    print("FINANCIAL ALERTS INITIALIZATION COMPLETE")
    print("-" * 50)
    print(f"Generated {results['total']} total alerts from real data:")
    print(f"- {results['large_transaction']} large transaction alerts")
    print(f"- {results['pattern_deviation']} pattern deviation alerts")
    print(f"- {results['daily_balance']} daily balance alerts")
    print(f"- {results['account_status']} account status alerts")
    print("-" * 50)
    print("The financial alerts system is now using real transaction data instead of mock data.")
    print("You can access the alerts through the Financial Alerts page in the application.")