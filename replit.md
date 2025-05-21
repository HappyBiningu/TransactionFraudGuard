# Unified Financial Intelligence Dashboard

## Overview

This is a comprehensive financial intelligence dashboard built with Streamlit, focusing on transaction monitoring across multiple accounts, limit monitoring, and fraud detection. The application uses SQLite databases for storage and provides intuitive visualizations and analysis tools for financial transactions.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a modular architecture with three main components:

1. **Multiple Accounts Analysis** - Monitors and analyzes transactions across different bank accounts
2. **Limit Monitoring** - Tracks transaction thresholds and generates alerts for violations
3. **Fraud Detection** - Uses machine learning (XGBoost) to identify potentially fraudulent transactions

Each component is implemented as a separate Streamlit page with its own database, but they all share a common UI framework and helper functions. The application is designed to be deployed with Streamlit's built-in server.

### Key Design Decisions

- **Database Choice**: SQLite was chosen for its simplicity and zero-configuration approach. Each module has its own database to maintain separation of concerns.
- **Frontend Framework**: Streamlit provides rapid development, interactive visualization capabilities, and seamless Python integration.
- **Modular Structure**: Using Streamlit's multi-page app feature separates concerns and makes the codebase easier to maintain.

## Key Components

### 1. Main Application (app.py)

The entry point for the application, providing a dashboard overview with summary metrics from all three modules. It includes helper functions for database access and metric calculations that are used across the application.

### 2. Multiple Accounts Analysis (pages/1_multiple_accounts.py)

Tracks and analyzes transactions across multiple bank accounts and financial institutions. Features include:
- Transaction data visualization
- Metrics on individual activities across multiple accounts
- Database connection pooling for performance

### 3. Limit Monitoring System (pages/2_limit_monitoring.py)

Monitors transactions against predefined thresholds and generates alerts when limits are exceeded. Features include:
- Configurable transaction limits
- Violation tracking and reporting
- Time-based monitoring (daily, weekly, monthly)

### 4. Fraud Detection System (pages/3_fraud_detection.py)

Uses machine learning to identify potentially fraudulent transactions. Features include:
- Pre-trained XGBoost model integration
- Batch processing via CSV uploads
- Individual transaction analysis
- Anomaly visualization

## Data Flow

1. **Data Ingestion**: 
   - Transaction data is uploaded via CSV files or manually entered
   - Data is validated for required fields and formats

2. **Data Processing**:
   - Transactions are enriched with metadata (timestamp parsing, aggregations)
   - Multiple account activity is identified
   - Transactions are evaluated against defined limits
   - ML model processes transactions for fraud probability

3. **Data Storage**:
   - Processed transactions are stored in their respective SQLite databases
   - Analysis results and violations are persisted for reporting

4. **Data Presentation**:
   - Interactive dashboards show key metrics
   - Visualizations highlight patterns and anomalies
   - Detailed transaction data is available for further investigation

## External Dependencies

### Core Dependencies
- Streamlit: Web application framework
- Pandas: Data manipulation and analysis
- SQLite: Database storage
- Plotly: Interactive visualizations

### Machine Learning Dependencies
- Joblib: Model serialization
- Scikit-learn: Data preprocessing
- XGBoost: Gradient boosting implementation for fraud detection

## Deployment Strategy

The application is configured for deployment using Streamlit's built-in server. The `.replit` file contains deployment configuration for running on Replit with auto-scaling enabled.

```python
# From .replit
deploymentTarget = "autoscale"
run = ["streamlit", "run", "app.py", "--server.port", "5000"]
```

The Streamlit configuration (in `.streamlit/config.toml`) specifies server settings:
- Headless mode enabled
- Listening on all interfaces (0.0.0.0)
- Port 5000
- Custom theme settings

For local development, the application can be run using `streamlit run app.py`, which will start the development server with hot-reloading enabled.