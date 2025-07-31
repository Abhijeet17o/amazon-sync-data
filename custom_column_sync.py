"""
CUSTOM AMAZON TO GOOGLE SHEETS SYNC - Azure Functions Integration
================================================================
Secure Amazon order synchronization with Google Sheets using environment variables.

Features:
- Timer trigger every minute with sleep hours (12:30 AM - 5:30 AM IST)
- Environment variable based credentials for security
- Duplicate prevention and custom column formatting
- Azure Functions ready deployment
- Fetches orders from last 6 hours (handles sleep time gaps)
- Total Amount column removed as requested

Column Layout (Total Amount removed):
1. Print Status, 2. SKU Status, 3. Order Status, 4. Product Name, 
5. Quantity Ordered, 6. Order Summary, 7. Order ID, 8. Purchase Date,
9. Buyer Name, 10. Ship City, 11. Ship State, 12. ASIN
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta

# Amazon SP-API imports
from sp_api.api import Orders
from sp_api.base import SellingApiException, Marketplaces

# Google Sheets imports
import gspread
from google.oauth2.service_account import Credentials

# Azure Functions imports
try:
    import azure.functions as func
    AZURE_AVAILABLE = True
except ImportError:
    # azure.functions not available in local environment
    func = None
    AZURE_AVAILABLE = False

def get_amazon_credentials():
    """Get Amazon credentials from environment variables"""
    return {
        'refresh_token': os.environ.get('AMAZON_REFRESH_TOKEN'),
        'lwa_app_id': os.environ.get('AMAZON_LWA_APP_ID'),
        'lwa_client_secret': os.environ.get('AMAZON_LWA_CLIENT_SECRET'),
    }

class CustomAmazonSync:
    def __init__(self, sheet_url):
        self.sheet_url = sheet_url
        self.setup_google_sheets()
        
    def setup_google_sheets(self):
        """Setup Google Sheets connection with custom columns"""
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_file('google_credentials.json', scopes=scope)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_url(self.sheet_url)
        
        # Get or create Orders worksheet
        try:
            self.worksheet = self.spreadsheet.worksheet('Orders')
        except gspread.WorksheetNotFound:
            self.worksheet = self.spreadsheet.add_worksheet(title='Orders', rows=1000, cols=12)
            
            # Add headers in exact sequence requested (Total Amount removed)
            headers = [
                'Print Status',      # Dropdown: Not Printed/Printed
                'SKU Status',       # Dropdown: Not Packed/Box Packed
                'Order Status',
                'Product Name',
                'Quantity Ordered',
                'Order Summary',    # Shows "Item 1 of 3" etc.
                'Order ID',
                'Purchase Date',    # Formatted date
                'Buyer Name',
                'Ship City',
                'Ship State',
                'ASIN'
            ]
            self.worksheet.append_row(headers)
            
            # Setup dropdown validations
            self.setup_dropdown_validations()
            
        print(f"✅ Connected to Google Sheet: {self.spreadsheet.title}")
        
    def setup_dropdown_validations(self):
        """Setup dropdown menus for Print Status and SKU Status columns"""
        try:
            # Print Status dropdown (Column A)
            print_status_rule = {
                "requests": [
                    {
                        "setDataValidation": {
                            "range": {
                                "sheetId": self.worksheet.id,
                                "startRowIndex": 1,  # Start from row 2 (after header)
                                "endRowIndex": 1000,  # Apply to 1000 rows
                                "startColumnIndex": 0,  # Column A
                                "endColumnIndex": 1
                            },
                            "rule": {
                                "condition": {
                                    "type": "ONE_OF_LIST",
                                    "values": [
                                        {"userEnteredValue": "Not Printed"},
                                        {"userEnteredValue": "Printed"}
                                    ]
                                },
                                "showCustomUi": True,
                                "strict": True
                            }
                        }
                    }
                ]
            }
            
            # SKU Status dropdown (Column B)
            sku_status_rule = {
                "requests": [
                    {
                        "setDataValidation": {
                            "range": {
                                "sheetId": self.worksheet.id,
                                "startRowIndex": 1,  # Start from row 2 (after header)
                                "endRowIndex": 1000,  # Apply to 1000 rows
                                "startColumnIndex": 1,  # Column B
                                "endColumnIndex": 2
                            },
                            "rule": {
                                "condition": {
                                    "type": "ONE_OF_LIST",
                                    "values": [
                                        {"userEnteredValue": "Not Packed"},
                                        {"userEnteredValue": "Box Packed"}
                                    ]
                                },
                                "showCustomUi": True,
                                "strict": True
                            }
                        }
                    }
                ]
            }
            
            # Apply validation rules
            self.spreadsheet.batch_update(print_status_rule)
            self.spreadsheet.batch_update(sku_status_rule)
            
            print("✅ Dropdown validations setup complete")
            
        except Exception as e:
            print(f"⚠️ Could not setup dropdowns: {e}")
            print("💡 You can manually add dropdowns in Google Sheets")
    
    def format_purchase_date(self, date_string):
        """Convert Amazon date format to readable format"""
        try:
            # Parse Amazon date: 2025-07-30T18:13:35Z
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            
            # Convert to local time (assuming IST)
            # Add 5:30 hours for IST
            local_dt = dt.replace(tzinfo=None) + timedelta(hours=5, minutes=30)
            
            # Format as: Jul 30, 2025 11:43 PM
            formatted = local_dt.strftime('%b %d, %Y %I:%M %p')
            return formatted
            
        except Exception as e:
            print(f"⚠️ Date formatting error: {e}")
            return date_string
    
    def get_existing_unique_ids(self):
        """Get existing order IDs to prevent duplicates"""
        try:
            existing_data = self.worksheet.get_all_values()
            if len(existing_data) <= 1:
                return set()
            
            # Get Order IDs from column G (index 6) - Order ID column position
            order_ids = {row[6] for row in existing_data[1:] if len(row) > 6 and row[6]}
            
            print(f"📊 Found {len(order_ids)} existing Order IDs in sheet")
            return order_ids
            
        except Exception as e:
            print(f"⚠️ Could not read existing data: {e}")
            return set()
    
    def get_recent_orders(self, hours_back=6):
        """Get orders from last X hours (default 6 hours to handle sleep gaps)"""
        try:
            amazon_credentials = get_amazon_credentials()
            orders_api = Orders(marketplace=Marketplaces.IN, credentials=amazon_credentials)
            
            created_after = (datetime.now() - timedelta(hours=hours_back)).isoformat()
            response = orders_api.get_orders(CreatedAfter=created_after, MaxResultsPerPage=50)
            
            orders = response.payload.get('Orders', [])
            print(f"📦 Found {len(orders)} orders from last {hours_back} hours")
            
            return orders
            
        except Exception as e:
            print(f"❌ Error fetching orders: {e}")
            return []
    
    def get_order_details(self, order_id):
        """Get detailed order information including items"""
        try:
            amazon_credentials = get_amazon_credentials()
            orders_api = Orders(marketplace=Marketplaces.IN, credentials=amazon_credentials)
            
            items_response = orders_api.get_order_items(order_id)
            order_items = items_response.payload.get('OrderItems', [])
            
            return order_items
            
        except Exception as e:
            print(f"❌ Error getting order details for {order_id}: {e}")
            return []
    
    def sync_orders_to_sheet(self, orders):
        """Add new orders to Google Sheet with custom formatting"""
        if not orders:
            print("ℹ️ No orders to sync")
            return
            
        # Get existing order IDs to prevent duplicates
        existing_order_ids = self.get_existing_unique_ids()
        
        new_orders_added = 0
        skipped_duplicates = 0
        
        for order in orders:
            order_id = order.get('AmazonOrderId')
            
            # Skip if order already exists
            if order_id in existing_order_ids:
                print(f"⏭️ Skipping duplicate order: {order_id}")
                skipped_duplicates += 1
                continue
                
            # Add to existing set immediately to prevent duplicates in this batch
            existing_order_ids.add(order_id)
                
            print(f"📋 Processing new order: {order_id}")
            
            # Get order items
            order_items = self.get_order_details(order_id)
            
            # Get shipping address
            shipping_address = order.get('ShippingAddress', {})
            ship_city = shipping_address.get('City', 'N/A')
            ship_state = shipping_address.get('StateOrRegion', 'N/A')
            
            # Get buyer info
            buyer_info = order.get('BuyerInfo', {})
            buyer_name = buyer_info.get('BuyerName', 'N/A')
            
            # Format purchase date
            formatted_date = self.format_purchase_date(order.get('PurchaseDate', ''))
            
            if order_items:
                total_items_in_order = len(order_items)
                
                for idx, item in enumerate(order_items, 1):
                    # Create order summary info
                    order_summary = f"Item {idx} of {total_items_in_order}"
                    if total_items_in_order > 1:
                        order_summary += f" 📦 SAME ORDER"
                    
                    # Get order status and convert "Shipped" to "Ordered"
                    order_status = order.get('OrderStatus', 'N/A')
                    if order_status.lower() == 'shipped':
                        order_status = 'Ordered'
                    
                    # Create row data in new column order (Total Amount removed)
                    row_data = [
                        'Not Printed',  # Print Status (default)
                        'Not Packed',   # SKU Status (default)
                        order_status,   # Order Status (converted from "Shipped" to "Ordered")
                        item.get('Title', 'N/A'),
                        str(item.get('QuantityOrdered', 0)),
                        order_summary,  # Order Summary
                        order_id,       # Order ID
                        formatted_date,
                        buyer_name,
                        ship_city,
                        ship_state,
                        item.get('ASIN', 'N/A')
                    ]
                    
                    # Insert at row 2 (after headers) to keep newest at top
                    try:
                        self.worksheet.insert_row(row_data, index=2)
                        new_orders_added += 1
                        
                        print(f"✅ Added: {item.get('Title', 'N/A')[:50]}...")
                        
                        # Small delay to avoid overwhelming the API
                        time.sleep(0.3)
                        
                    except Exception as e:
                        print(f"❌ Error adding row: {e}")
                        
            else:
                # Handle orders without items
                # Get order status and convert "Shipped" to "Ordered"
                order_status = order.get('OrderStatus', 'N/A')
                if order_status.lower() == 'shipped':
                    order_status = 'Ordered'
                
                row_data = [
                    'Not Printed',  # Print Status (default)
                    'Not Packed',   # SKU Status (default)
                    order_status,   # Order Status (converted from "Shipped" to "Ordered")
                    'No items found',
                    '0',
                    'Single Item',  # Order summary
                    order_id,       # Order ID
                    formatted_date,
                    buyer_name,
                    ship_city,
                    ship_state,
                    'N/A'
                ]
                
                self.worksheet.insert_row(row_data, index=2)
                new_orders_added += 1
                existing_order_ids.add(order_id)
        
        print(f"🎉 Sync complete!")
        print(f"✅ Added {new_orders_added} new orders")
        print(f"⏭️ Skipped {skipped_duplicates} duplicates")
        print(f"🎯 Dropdowns ready for Print Status and SKU Status columns")

def is_sleep_time():
    """Check if current time is within sleep hours (12:30 AM to 5:30 AM IST)"""
    now = datetime.now()
    sleep_start = now.replace(hour=0, minute=30, second=0, microsecond=0)
    sleep_end = now.replace(hour=5, minute=30, second=0, microsecond=0)
    
    return sleep_start <= now <= sleep_end

def azure_timer_handler(mytimer):
    """Azure Functions timer trigger handler"""
    try:
        # Log timer information
        logging.info(f'Timer trigger executed at: {datetime.now()}')
        
        # Check if we're in sleep time (12:30 AM to 5:30 AM IST)
        if is_sleep_time():
            logging.info('😴 Sleeping time - No order checking until 5:30 AM')
            return "Sleeping - no sync during night hours"
        
        logging.info('🚀 Starting Amazon order sync...')
        
        # Validate environment variables
        required_vars = ['AMAZON_REFRESH_TOKEN', 'AMAZON_LWA_APP_ID', 'AMAZON_LWA_CLIENT_SECRET']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            error_msg = f"Missing environment variables: {', '.join(missing_vars)}"
            logging.error(error_msg)
            raise ValueError(error_msg)
        
        # Initialize sync
        sheet_url = os.environ.get('GOOGLE_SHEET_URL', "https://docs.google.com/spreadsheets/d/1REsoseklT3qWeUVI7ngGrpLBe-6WPo-gjsTIgV5Cw4U")
        sync = CustomAmazonSync(sheet_url)
        
        # Get recent orders (last 6 hours to handle sleep gaps - orders during 12:30-5:30 AM sleep time)
        orders = sync.get_recent_orders(hours_back=6)
        
        # Sync to sheet
        sync.sync_orders_to_sheet(orders)
        
        logging.info('✅ Amazon sync completed successfully')
        return "Sync completed successfully"
        
    except Exception as e:
        logging.error(f'❌ Error in Azure timer function: {str(e)}')
        raise

def main():
    """Main function for local testing"""
    print("🎯 AMAZON TO GOOGLE SHEETS SYNC - AZURE FUNCTIONS")
    print("=" * 60)
    print("📋 Features:")
    print("   • Secure environment variable credentials")
    print("   • Timer trigger every minute (with sleep hours)")
    print("   • Custom column formatting with dropdowns")
    print("   • Duplicate prevention")
    print("   • Sleep time: 12:30 AM - 5:30 AM IST")
    print("   • Fetches orders from last 6 hours (handles sleep gaps)")
    print("   • Total Amount column removed")
    
    try:
        # For local testing, you'll need to set environment variables
        if not os.environ.get('AMAZON_REFRESH_TOKEN'):
            print("\n⚠️  Environment variables not set for local testing")
            print("💡 For production, these will be set in Azure Function App settings")
            return
            
        # Initialize sync
        sheet_url = os.environ.get('GOOGLE_SHEET_URL', "https://docs.google.com/spreadsheets/d/1REsoseklT3qWeUVI7ngGrpLBe-6WPo-gjsTIgV5Cw4U")
        sync = CustomAmazonSync(sheet_url)
        
        print("\n📥 Running one-time sync...")
        orders = sync.get_recent_orders(hours_back=6)
        sync.sync_orders_to_sheet(orders)
        print("✅ Local sync complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure environment variables are set correctly")

if __name__ == "__main__":
    main()
