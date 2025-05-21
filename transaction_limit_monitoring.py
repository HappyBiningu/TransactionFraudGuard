import streamlit as st
import yaml
import logging

# Set up logging
logging.basicConfig(filename="app.log", level=logging.INFO)

# Load configuration
try:
    with open("config.yaml", "r") as config_file:
        config = yaml.safe_load(config_file)
    model_path = config["model_path"]
    transaction_limit = config["transaction_limit"]
    logging.info("Configuration loaded successfully.")
except Exception as e:
    st.error("Error loading configuration.")
    logging.error(f"Error loading configuration: {e}")

# Set page configuration
st.set_page_config(page_title="Transaction Limit Monitoring - Dashboard", page_icon="⚠️")

# Load custom CSS
try:
    with open("static/styles.css") as css_file:
        st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    st.warning("Custom CSS file not found. Using default styles.")

# Streamlit UI
st.title("⚠️ Transaction Limit Monitoring - Dashboard")
st.sidebar.success("Select a page above")

st.markdown(f"""
### Transaction Limit Monitoring

The current transaction limit is **{transaction_limit}**.
""")