import os
from financial_tracker import FinancialTracker

def main():
    # Set environment variables for Plaid
    os.environ['PLAID_CLIENT_ID'] = 'your_plaid_client_id'
    os.environ['PLAID_SECRET'] = 'your_plaid_secret'
    os.environ['PLAID_ENV'] = 'development'  # Use 'development' or 'production' for real data
    
    # Initialize the tracker with saved access token
    tracker = FinancialTracker(google_creds_path='google_credentials.json')
    
    # Load the access token from secure storage
    # Retrieve from database or storage in production environment
    with open('access_token.txt', 'r') as f:
        tracker.access_token = f.read().strip()
    
    # Run the update cycle
    tracker.run_update_cycle(days_back=7)  # Get last 7 days of transactions

if __name__ == "__main__":
    main()
