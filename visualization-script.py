import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

def create_dashboard(creds_path, sheet_id):
    """Create a dashboard with data for charts based on transaction data"""
    # Set up credentials
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(creds_path, scopes=scope)
    client = gspread.authorize(creds)
    
    # Open sheet
    try:
        sheet = client.open_by_key(sheet_id)
        print(f"Successfully opened sheet with ID: {sheet_id}")
    except Exception as e:
        print(f"Error opening sheet: {str(e)}")
        return None
    
    # Get transaction data
    try:
        transactions_ws = sheet.worksheet("Transactions")
        transactions_data = transactions_ws.get_all_values()
        
        # Convert to DataFrame
        df = pd.DataFrame(transactions_data[1:], columns=transactions_data[0])
        
        # Convert Amount to numeric
        df['Amount'] = pd.to_numeric(df['Amount'])
        
        # Calculate metrics
        total_spending = df[df['Amount'] < 0]['Amount'].sum() * -1
        total_income = df[df['Amount'] > 0]['Amount'].sum()
        net_cash_flow = total_income - total_spending
        
        # Prepare data for category summary
        category_spending = df[df['Amount'] < 0].groupby('Category')['Amount'].sum() * -1
        category_spending = category_spending.reset_index()
        category_spending = category_spending.sort_values('Amount', ascending=False)
        
        # Create Dashboard worksheet or clear existing one
        try:
            try:
                dashboard_ws = sheet.worksheet("Dashboard")
                dashboard_ws.clear()
                print("Cleared existing Dashboard worksheet")
            except gspread.exceptions.WorksheetNotFound:
                dashboard_ws = sheet.add_worksheet(title="Dashboard", rows=50, cols=15)
                print("Created new Dashboard worksheet")
        
            # Add title - use list of lists for ALL updates
            dashboard_ws.update('A1', [['Financial Dashboard']])
            
            # Add summary metrics
            dashboard_ws.update('A3', [['Summary Metrics']])
            
            dashboard_ws.update('A4:B4', [['Total Spending:', f"${total_spending:.2f}"]])
            dashboard_ws.update('A5:B5', [['Total Income:', f"${total_income:.2f}"]])
            dashboard_ws.update('A6:B6', [['Net Cash Flow:', f"${net_cash_flow:.2f}"]])
            
            # Add category spending table
            dashboard_ws.update('A8', [['Spending by Category']])
            
            dashboard_ws.update('A9:B9', [['Category', 'Amount']])
            
            # Add category data
            category_data = []
            for _, row in category_spending.iterrows():
                category_data.append([row['Category'], f"${row['Amount']:.2f}"])
            
            if category_data:
                dashboard_ws.update(f'A10', category_data)
            
            # Add data for charts
            dashboard_ws.update('D3', [['Data for Charts']])
            
            # Add data for category pie chart
            dashboard_ws.update('D4', [['Category Spending Data (For Pie Chart)']])
            dashboard_ws.update('D5:E5', [['Category', 'Amount']])
            
            pie_data = []
            for _, row in category_spending.iterrows():
                # Use only numeric values for chart data
                pie_data.append([row['Category'], float(row['Amount'])])
            
            if pie_data:
                dashboard_ws.update(f'D6', pie_data)
            
            # Calculate monthly spending for time trend chart
            df['Date'] = pd.to_datetime(df['Date'])
            df['Month'] = df['Date'].dt.strftime('%Y-%m')
            monthly_spending = df[df['Amount'] < 0].groupby('Month')['Amount'].sum() * -1
            monthly_spending = monthly_spending.reset_index()
            
            # Add monthly data for bar/line chart
            row_offset = len(pie_data) + 8
            dashboard_ws.update(f'D{row_offset}', [['Monthly Spending Data (For Bar/Line Chart)']])
            dashboard_ws.update(f'D{row_offset+1}:E{row_offset+1}', [['Month', 'Amount']])
            
            monthly_data = []
            for _, row in monthly_spending.iterrows():
                monthly_data.append([row['Month'], float(row['Amount'])])
            
            if monthly_data:
                dashboard_ws.update(f'D{row_offset+2}', monthly_data)
                
            # Chart creation instructions
            instruction_row = row_offset + len(monthly_data) + 4
            dashboard_ws.update(f'A{instruction_row}', [['Chart Creation Instructions']])
            
            instructions = [
                ['Pie Chart for Category Spending:'],
                ['1. Select data range D5:E' + str(5 + len(pie_data) - 1)],
                ['2. Click Insert > Chart'],
                ['3. Choose "Pie chart"'],
                [''],
                ['Bar/Line Chart for Monthly Spending:'],
                [f'1. Select data range D{row_offset+1}:E{row_offset+1+len(monthly_data) - 1}'],
                ['2. Click Insert > Chart'],
                ['3. Choose "Column chart" or "Line chart"']
            ]
            
            dashboard_ws.update(f'A{instruction_row+1}', instructions)
            
            print("Dashboard created successfully!")
            return sheet.url
            
        except Exception as e:
            print(f"Error creating dashboard: {str(e)}")
            return None
            
    except Exception as e:
        print(f"Error processing transaction data: {str(e)}")
        return None

if __name__ == "__main__":
    
    creds_path = 'google_credentials.json'
    sheet_id = '1tLudq2Y4etF6R4VAtAKTlZ7ylW92SL28PiNW_vMVCxo'  
    
    # Create the dashboard
    dashboard_url = create_dashboard(creds_path, sheet_id)
    
    if dashboard_url:
        print(f"Dashboard created successfully! View your sheet at: {dashboard_url}")
    else:
        print("Failed to create dashboard.")
