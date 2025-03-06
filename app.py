from flask import Flask, render_template, jsonify, request
import os
from financial_tracker import FinancialTracker  # Import the main class we created

app = Flask(__name__)

# Initialize the tracker
tracker = FinancialTracker(google_creds_path='google_credentials.json')
tracker.create_financial_spreadsheet("My Financial Tracker")

@app.route('/')
def index():
    """Render the home page with Plaid Link"""
    # Get a link token from Plaid
    link_token = tracker.get_link_token()
    return render_template('index.html', link_token=link_token)

@app.route('/get_access_token', methods=['POST'])
def get_access_token():
    """Exchange public token for access token"""
    public_token = request.json['public_token']
    access_token = tracker.exchange_public_token(public_token)
    
    # Store the access token securely (in a real app, you'd use a database)
    # For this example, we're just storing it in memory
    
    # Run initial update to fetch transactions
    added = tracker.run_update_cycle(days_back=90)  # Get 90 days of transactions
    
    return jsonify({
        'success': True,
        'transactions_added': added
    })

@app.route('/update_transactions')
def update_transactions():
    """Endpoint to update transactions"""
    added = tracker.run_update_cycle(days_back=30)  # Get 30 days of transactions
    return jsonify({
        'success': True,
        'transactions_added': added
    })

if __name__ == '__main__':
    # Set environment variables for Plaid
    os.environ['PLAID_CLIENT_ID'] = 'your_plaid_client_id'
    os.environ['PLAID_SECRET'] = 'your_plaid_secret'
    os.environ['PLAID_ENV'] = 'sandbox'  # Use 'development' or 'production' for real data
    
    app.run(debug=True)
