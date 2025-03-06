import os
import datetime
import plaid
import json
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.configuration import Configuration, ApiClient
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64

class FinancialTracker:
    def __init__(self, google_creds_path='google_credentials.json'):
        # Initialize Plaid client
        self.plaid_client_id = os.environ.get('PLAID_CLIENT_ID')
        self.plaid_secret = os.environ.get('PLAID_SECRET')
        self.plaid_env = os.environ.get('PLAID_ENV', 'sandbox')
        
        # Configure Plaid client
        host = 'https://sandbox.plaid.com' if self.plaid_env == 'sandbox' else 'https://development.plaid.com'
        if self.plaid_env == 'production':
            host = 'https://production.plaid.com'
            
        configuration = Configuration(
            host=host,
            api_key={
                'clientId': self.plaid_client_id,
                'secret': self.plaid_secret,
            }
        )
        api_client = ApiClient(configuration)
        self.plaid_client = plaid_api.PlaidApi(api_client)
        
        # Initialize Google Sheets
        self.initialize_google_sheets(google_creds_path)
        
        # Transaction categories mapping
        self.categories = {
            'Food': ['Restaurants', 'Fast Food', 'Groceries'],
            'Transportation': ['Uber', 'Lyft', 'Gas', 'Public Transportation'],
            'Shopping': ['Amazon', 'Target', 'Walmart', 'Clothing'],
            'Entertainment': ['Movies', 'Streaming', 'Music'],
            'Bills': ['Utilities', 'Rent', 'Insurance', 'Internet'],
            'Health': ['Pharmacy', 'Doctor', 'Gym'],
            'Travel': ['Flights', 'Hotels', 'Vacation'],
            'Other': []
        }
        
        # Access token storage
        self.access_token = None
        
    def initialize_google_sheets(self, creds_path):
        """Initialize Google Sheets API connection"""
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(creds_path, scopes=scope)
        self.gc = gspread.authorize(creds)
        
    def create_financial_spreadsheet(self, sheet_name='My Financial Tracker'):
        """Create a new Google Sheet for financial tracking"""
        try:
            # Try to open existing sheet
            self.sheet = self.gc.open(sheet_name)
            print(f"Using existing sheet: {sheet_name}")
        except gspread.exceptions.SpreadsheetNotFound:
            # Create new sheet if not found
            self.sheet = self.gc.create(sheet_name)
            print(f"Created new sheet: {sheet_name}")
            
        # Check for and create necessary worksheets
        try:
            self.transactions_worksheet = self.sheet.worksheet("Transactions")
            print("Using existing Transactions worksheet")
        except gspread.exceptions.WorksheetNotFound:
            self.transactions_worksheet = self.sheet.add_worksheet(
                title="Transactions", 
                rows=1000, 
                cols=10
            )
            # Add headers to transactions sheet
            headers = [
                "Date", "Description", "Amount", "Category", 
                "Account", "Transaction ID", "Pending", "Merchant Name"
            ]
            self.transactions_worksheet.append_row(headers)
            print("Created Transactions worksheet")
            
        # Create categories worksheet
        try:
            self.categories_worksheet = self.sheet.worksheet("Categories")
            print("Using existing Categories worksheet")
        except gspread.exceptions.WorksheetNotFound:
            self.categories_worksheet = self.sheet.add_worksheet(
                title="Categories", 
                rows=100, 
                cols=2
            )
            # Add default categories
            self.categories_worksheet.append_row(["Category", "Keywords"])
            for category, keywords in self.categories.items():
                self.categories_worksheet.append_row([category, ", ".join(keywords)])
            print("Created Categories worksheet")
            
        # Create dashboard worksheet
        try:
            self.dashboard_worksheet = self.sheet.worksheet("Dashboard")
            print("Using existing Dashboard worksheet")
        except gspread.exceptions.WorksheetNotFound:
            self.dashboard_worksheet = self.sheet.add_worksheet(
                title="Dashboard", 
                rows=50, 
                cols=10
            )
            print("Created Dashboard worksheet")
            
    def get_link_token(self):
        """Create a link token for Plaid Link"""
        user = LinkTokenCreateRequestUser(
            client_user_id='user_good'
        )
        
        request = LinkTokenCreateRequest(
            user=user,
            client_name="Financial Tracker App",
            products=["transactions"],
            country_codes=["US"],
            language="en"
        )
        
        response = self.plaid_client.link_token_create(request)
        return response.link_token
    
    def exchange_public_token(self, public_token):
        """Exchange a public token for an access token"""
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        response = self.plaid_client.item_public_token_exchange(request)
        self.access_token = response.access_token
        
        # Save the access token
        try:
            os.makedirs('config', exist_ok=True)
            with open('config/access_token.json', 'w') as f:
                json.dump({'access_token': self.access_token}, f)
            print("Access token saved successfully")
        except Exception as e:
            print(f"Error saving access token: {str(e)}")
            
        return self.access_token
    
    def get_accounts(self):
        """Get accounts for an Item"""
        request = AccountsGetRequest(access_token=self.access_token)
        response = self.plaid_client.accounts_get(request)
        return response.accounts
    
    def get_transactions(self, start_date, end_date=None):
        """Get transactions for a date range"""
        if end_date is None:
            end_date = datetime.now().date()
            
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
        request = TransactionsGetRequest(
            access_token=self.access_token,
            start_date=start_date,
            end_date=end_date,
            options=TransactionsGetRequestOptions(
                count=500,
                offset=0
            )
        )
        
        response = self.plaid_client.transactions_get(request)
        transactions = response.transactions
        
        while len(transactions) < response.total_transactions:
            request = TransactionsGetRequest(
                access_token=self.access_token,
                start_date=start_date,
                end_date=end_date,
                options=TransactionsGetRequestOptions(
                    count=500,
                    offset=len(transactions)
                )
            )
            response = self.plaid_client.transactions_get(request)
            transactions.extend(response.transactions)
            
        return transactions
    
    def categorize_transaction(self, transaction):
        """Categorize a transaction based on its description"""
        description = transaction.name.lower()
        merchant_name = transaction.merchant_name.lower() if transaction.merchant_name else ""
        
        # Get categories and keywords from Google Sheet
        category_data = self.categories_worksheet.get_all_values()[1:]  # Skip header
        for row in category_data:
            if len(row) < 2:
                continue
                
            category = row[0]
            keywords = [k.strip().lower() for k in row[1].split(',')]
            
            # Check if any keyword is in the description or merchant name
            for keyword in keywords:
                if keyword and (keyword in description or keyword in merchant_name):
                    return category
                    
        # Default category
        return "Other"
    
    def add_transactions_to_sheet(self, transactions):
        """Add new transactions to Google Sheets"""
        # Get existing transaction IDs to avoid duplicates
        try:
            existing_transaction_ids = self.transactions_worksheet.col_values(6)[1:]  # Skip header
        except:
            existing_transaction_ids = []
            
        # Format and add each transaction
        new_rows = 0
        for transaction in transactions:
            if transaction.transaction_id in existing_transaction_ids:
                continue
                
            category = self.categorize_transaction(transaction)
            
            # Format transaction row
            row = [
                transaction.date,
                transaction.name,
                transaction.amount,
                category,
                transaction.account_id,
                transaction.transaction_id,
                "Yes" if transaction.pending else "No",
                transaction.merchant_name if transaction.merchant_name else "Unknown"
            ]
            
            self.transactions_worksheet.append_row(row)
            new_rows += 1
            
        print(f"Added {new_rows} new transactions to the sheet")
        return new_rows
    
    def update_dashboard(self):
        """Update the dashboard with spending charts and summaries"""
        # Get all transactions
        transactions_data = self.transactions_worksheet.get_all_values()[1:]  # Skip header
        
        if not transactions_data:
            print("No transactions to analyze")
            return
            
        # Convert to pandas DataFrame for analysis
        df = pd.DataFrame(transactions_data, columns=[
            "Date", "Description", "Amount", "Category", 
            "Account", "Transaction ID", "Pending", "Merchant Name"
        ])
        
        # Convert amount to float
        df['Amount'] = df['Amount'].astype(float)
        
        # Convert date to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Calculate spending by category
        category_spending = df.groupby('Category')['Amount'].sum().sort_values(ascending=False)
        
        # Calculate monthly spending
        df['Month'] = df['Date'].dt.strftime('%Y-%m')
        monthly_spending = df.groupby('Month')['Amount'].sum()
        
        # Clear existing dashboard
        self.dashboard_worksheet.clear()
        
        # Add title
        self.dashboard_worksheet.update('A1', 'Financial Dashboard')
        self.dashboard_worksheet.format('A1', {'textFormat': {'bold': True, 'fontSize': 14}})
        
        # Total spending
        total_spending = df['Amount'].sum()
        self.dashboard_worksheet.update('A3', 'Total Spending:')
        self.dashboard_worksheet.update('B3', f"${abs(total_spending):.2f}")
        
        # Spending by category
        self.dashboard_worksheet.update('A5', 'Spending by Category')
        self.dashboard_worksheet.format('A5', {'textFormat': {'bold': True}})
        
        for i, (category, amount) in enumerate(category_spending.items(), start=6):
            self.dashboard_worksheet.update(f'A{i}', category)
            self.dashboard_worksheet.update(f'B{i}', f"${abs(amount):.2f}")
            
        # Monthly spending
        row_offset = len(category_spending) + 8
        self.dashboard_worksheet.update(f'A{row_offset}', 'Monthly Spending')
        self.dashboard_worksheet.format(f'A{row_offset}', {'textFormat': {'bold': True}})
        
        for i, (month, amount) in enumerate(monthly_spending.items(), start=row_offset+1):
            self.dashboard_worksheet.update(f'A{i}', month)
            self.dashboard_worksheet.update(f'B{i}', f"${abs(amount):.2f}")
            
        # Add charts
        self.add_charts_to_dashboard()
            
        print("Dashboard updated successfully")
    
    def add_charts_to_dashboard(self):
        """Add charts to the dashboard worksheet"""
        # Get transaction data
        transactions_data = self.transactions_worksheet.get_all_values()[1:]  # Skip header
        
        if not transactions_data:
            print("No transactions to visualize")
            return
        
        # Convert to pandas DataFrame for analysis
        df = pd.DataFrame(transactions_data, columns=[
            "Date", "Description", "Amount", "Category", 
            "Account", "Transaction ID", "Pending", "Merchant Name"
        ])
        
        # Convert amount to float
        df['Amount'] = df['Amount'].astype(float).abs()  # Use absolute values for spending
        
        # Prepare data for charts
        categories = df.groupby('Category')['Amount'].sum().reset_index()
        categories = categories.sort_values('Amount', ascending=False)
        
        # Convert date to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        df['Month'] = df['Date'].dt.strftime('%Y-%m')
        monthly = df.groupby('Month')['Amount'].sum().reset_index()
        
    # Create pie chart for category spending
        try:
            # Clear existing charts
            try:
                charts = self.dashboard_worksheet.get_charts()
                for chart in charts:
                    self.dashboard_worksheet.delete_chart(chart.id)
            except Exception as e:
                print(f"No existing charts to delete or error: {str(e)}")
            # Add new chart creation code here
        except Exception as e:
            print(f"Error creating charts: {str(e)}")