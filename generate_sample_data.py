import gspread
import pandas as pd
import random
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials

# Sample transaction data
merchants = [
    "Amazon", "Walmart", "Target", "Starbucks", "Uber", "Netflix", 
    "Spotify", "Whole Foods", "Home Depot", "Best Buy", "Gas Station",
    "Restaurant", "Grocery Store", "Pharmacy", "Electric Bill"
]

categories = {
    "Shopping": ["Amazon", "Walmart", "Target", "Best Buy", "Home Depot"],
    "Food": ["Starbucks", "Whole Foods", "Restaurant", "Grocery Store"],
    "Entertainment": ["Netflix", "Spotify"],
    "Transportation": ["Uber", "Gas Station"],
    "Bills": ["Electric Bill"],
    "Health": ["Pharmacy"]
}

# Generate sample data
def generate_sample_data(num_transactions=50):
    data = []
    end_date = datetime.now()
    
    for i in range(num_transactions):
        date = end_date - timedelta(days=random.randint(0, 90))
        merchant = random.choice(merchants)
        
        # Find category for merchant
        category = "Other"
        for cat, merch_list in categories.items():
            if merchant in merch_list:
                category = cat
                break
        
        # Create transaction
        transaction = {
            "Date": date.strftime("%Y-%m-%d"),
            "Description": f"Purchase at {merchant}",
            "Amount": round(random.uniform(5, 200), 2) * -1,  # Negative for expenses
            "Category": category,
            "Account": "Chase Checking",
            "Transaction ID": f"tx_{i}_{random.randint(10000, 99999)}",
            "Pending": "No",
            "Merchant Name": merchant
        }
        data.append(transaction)
    
    # Add some income
    for i in range(3):
        date = end_date - timedelta(days=i*30)
        transaction = {
            "Date": date.strftime("%Y-%m-%d"),
            "Description": "Direct Deposit - Payroll",
            "Amount": round(random.uniform(2000, 3000), 2),  # Positive for income
            "Category": "Income",
            "Account": "Chase Checking",
            "Transaction ID": f"tx_income_{i}_{random.randint(10000, 99999)}",
            "Pending": "No",
            "Merchant Name": "Employer"
        }
        data.append(transaction)
        
    return data

# Upload to Google Sheets using a specific sheet ID
def upload_to_sheet_by_id(data, creds_path, sheet_id):
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_path, scopes=scope)
    client = gspread.authorize(creds)
    
    # Open sheet by ID
    try:
        sheet = client.open_by_key(sheet_id)
        print(f"Successfully opened sheet with ID: {sheet_id}")
    except Exception as e:
        print(f"Error opening sheet: {str(e)}")
        return None
    
    # Get or create transactions worksheet
    try:
        worksheet = sheet.worksheet("Transactions")
        print("Using existing Transactions worksheet")
        
        # Clear existing data
        try:
            # Get the number of rows in the sheet
            existing_data = worksheet.get_all_values()
            if len(existing_data) > 1:  # If there's data beyond the header
                # Clear all rows except header
                worksheet.batch_clear(["A2:H1000"])
                print("Cleared existing data")
        except Exception as e:
            print(f"Error clearing data: {str(e)}")
            
    except gspread.exceptions.WorksheetNotFound:
        # Create new worksheet if it doesn't exist
        worksheet = sheet.add_worksheet(title="Transactions", rows=1000, cols=10)
        print("Created new Transactions worksheet")
        
        # Add headers to transactions sheet
        headers = [
            "Date", "Description", "Amount", "Category", 
            "Account", "Transaction ID", "Pending", "Merchant Name"
        ]
        worksheet.append_row(headers)
    
    # Format data for upload
    df = pd.DataFrame(data)
    df = df.sort_values("Date", ascending=False)
    
    # Convert to list of lists for upload
    rows = df.values.tolist()
    
    # DEBUG: Print first few rows to check the data format
    print("Sample of data to be uploaded:")
    for row in rows[:3]:
        print(row)
    
    try:
        # Update with CORRECT parameter order (values first, then range)
        # Upload all rows at once - simpler approach
        worksheet.update(values=rows, range_name=f'A2')
        print(f"Updated all rows at once")
    except Exception as e:
        print(f"Error updating all rows: {str(e)}")
        
        # Try updating in smaller batches if the bulk update fails
        try:
            print("Trying batch update approach...")
            batch_size = 10
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i+batch_size]
                # Use the correct parameter order
                worksheet.update(values=batch, range_name=f'A{i+2}')
                print(f"Updated rows {i+2} to {i+min(i+batch_size+1, len(rows)+1)}")
        except Exception as e:
            print(f"Error with batch update: {str(e)}")
            return None
    
    print(f"Successfully added {len(data)} transactions to the sheet")
    
    # Get and return the sheet URL
    return sheet.url

if __name__ == "__main__":
    # Replace with the path to your service account credentials file
    creds_path = 'google_credentials.json'
    
   
    sheet_id = '1tLudq2Y4etF6R4VAtAKTlZ7ylW92SL28PiNW_vMVCxo'
    
    # Generate sample data
    sample_data = generate_sample_data(75)
    
    # Upload to the specified Google Sheet
    sheet_url = upload_to_sheet_by_id(sample_data, creds_path, sheet_id)
    
    if sheet_url:
        print(f"Data uploaded successfully! You can view your sheet at: {sheet_url}")
    else:
        print("Failed to upload data to the sheet.")