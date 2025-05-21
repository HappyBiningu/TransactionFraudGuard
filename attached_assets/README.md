# Fraud Detection System

A web-based interface for detecting suspicious transactions using a trained XGBoost model.

## Features

- Upload CSV files with transaction data for batch processing
- Manual input for single transaction analysis
- Real-time transaction scoring
- Interactive data visualization
- Detailed transaction analysis with multiple metrics
- User-friendly interface with clear results presentation

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation

1. Clone this repository or download the files to your local machine.

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Ensure your model file (`fraud_detection_pipeline.pkl`) is in the correct location:
   ```
   C:\Users\PRISCILLA\Desktop\model23\fraud_detection_pipeline.pkl
   ```

2. Start the Streamlit application:
```bash
streamlit run app.py
```

3. The application will open in your default web browser at `http://localhost:8501`

## Using the Application

### CSV Upload
1. Prepare a CSV file with the following columns:
   - transaction_id
   - individual_id
   - account_id
   - bank_name
   - amount
   - timestamp

2. Use the "Upload CSV" option to process multiple transactions at once.

### Manual Input
1. Fill in the transaction details in the form:
   - Transaction ID (auto-generated)
   - Individual ID
   - Account ID
   - Bank Name
   - Amount
   - Timestamp (auto-filled with current time)

2. Click "Analyze Transaction" to get the prediction.

## Results Interpretation

- Red highlighted rows indicate suspicious transactions
- The Fraud Probability column shows the model's confidence level
- Summary statistics show the total number of transactions and suspicious ones
- Additional metrics include daily, weekly, and monthly totals

## Troubleshooting

If you encounter any issues:

1. Ensure all required packages are installed correctly
2. Verify the model file path is correct
3. Check that input data matches the expected format
4. Look for error messages in the application interface

## Support

For any questions or issues, please open an issue in the repository. 