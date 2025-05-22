import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier
import joblib
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger(__name__)

# Output file
MODEL_PATH = 'fraud_detection_pipeline.pkl'

def create_sample_data():
    """Create sample fraud transaction data for training"""
    np.random.seed(42)
    
    # Generate 1000 sample transactions
    n_samples = 1000
    
    # Create transaction data
    data = {
        'transaction_id': [f'TX{i:06d}' for i in range(n_samples)],
        'amount': np.random.exponential(scale=500, size=n_samples),
        'account_age_days': np.random.randint(1, 3000, size=n_samples),
        'transaction_count_7d': np.random.randint(0, 20, size=n_samples),
        'amount_7d': np.random.exponential(scale=1000, size=n_samples),
        'transaction_count_30d': np.random.randint(0, 50, size=n_samples),
        'amount_30d': np.random.exponential(scale=3000, size=n_samples),
        'merchant_category': np.random.choice(['retail', 'travel', 'online', 'restaurant', 'other'], size=n_samples),
        'time_of_day': np.random.choice(['morning', 'afternoon', 'evening', 'night'], size=n_samples),
        'day_of_week': np.random.choice(['weekday', 'weekend'], size=n_samples),
        'card_present': np.random.choice([0, 1], size=n_samples),
        'is_foreign': np.random.choice([0, 1], p=[0.9, 0.1], size=n_samples),
        'is_high_risk_merchant': np.random.choice([0, 1], p=[0.95, 0.05], size=n_samples)
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Generate fraud labels (approximately 5% fraud rate)
    # Higher probability of fraud for:
    # - Large transactions
    # - Foreign transactions
    # - High risk merchants
    # - Night time transactions
    
    fraud_score = (
        (df['amount'] > 1000).astype(int) * 2 +
        df['is_foreign'] * 3 +
        df['is_high_risk_merchant'] * 4 +
        (df['time_of_day'] == 'night').astype(int) * 2 +
        (df['transaction_count_7d'] > 15).astype(int) * 2
    )
    
    # Normalize fraud score to probability
    fraud_prob = (fraud_score - fraud_score.min()) / (fraud_score.max() - fraud_score.min()) * 0.3
    
    # Generate labels
    df['is_fraud'] = np.random.binomial(1, fraud_prob, size=n_samples)
    
    return df

def create_fraud_detection_model():
    """Create and train a fraud detection model"""
    logger.info("Creating fraud detection model...")
    
    # Create sample data
    df = create_sample_data()
    
    # Define feature columns
    numerical_features = [
        'amount', 'account_age_days', 'transaction_count_7d', 
        'amount_7d', 'transaction_count_30d', 'amount_30d'
    ]
    
    categorical_features = [
        'merchant_category', 'time_of_day', 'day_of_week'
    ]
    
    binary_features = [
        'card_present', 'is_foreign', 'is_high_risk_merchant'
    ]
    
    # Define preprocessing for numerical features
    numerical_transformer = Pipeline(steps=[
        ('scaler', StandardScaler())
    ])
    
    # Define preprocessing for categorical features
    categorical_transformer = Pipeline(steps=[
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])
    
    # Combine preprocessing steps
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features),
            ('bin', 'passthrough', binary_features)
        ]
    )
    
    # Create the pipeline with preprocessing and model
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', XGBClassifier(n_estimators=100, learning_rate=0.1, random_state=42))
    ])
    
    # Split data
    X = df.drop(['transaction_id', 'is_fraud'], axis=1)
    y = df['is_fraud']
    
    # Train the model
    pipeline.fit(X, y)
    
    # Save the pipeline
    joblib.dump(pipeline, MODEL_PATH)
    logger.info(f"Fraud detection model saved to {MODEL_PATH}")
    
    return pipeline

if __name__ == "__main__":
    # Check if model already exists
    if os.path.exists(MODEL_PATH):
        logger.info(f"Model already exists at {MODEL_PATH}, skipping creation")
    else:
        create_fraud_detection_model()
        print(f"Fraud detection model created and saved to {MODEL_PATH}")