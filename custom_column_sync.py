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
- Dynamic order status and ship date updates for existing orders
- Serial numbers starting from 193 with auto-increment functionality

Column Layout (Updated with Sr. No. and Ship Date):
1. Sr. No., 2. Print Status, 3. SKU Status, 4. Order Status, 5. Product Name, 
6. Quantitiy Ordered, 7. Order summary, 8. Order ID, 9. Purchase Date,
10. Ship Date, 11. Buyer Name, 12. Ship City, 13. Ship State, 14. ASIN

Version: 2025-07-31 - All features verified and working
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
            
            # Update headers to match new format if they're outdated
            self.update_headers_if_needed()
            
        except gspread.WorksheetNotFound:
            self.worksheet = self.spreadsheet.add_worksheet(title='Orders', rows=1000, cols=14)
            
            # Add headers in exact sequence requested (with Sr. No. and Ship Date)
            headers = [
                'Sr. No.',          # Auto-incrementing serial number
                'Print Status',      # Dropdown: Not Printed/Printed
                'SKU Status',       # Dropdown: Not Packed/Box Packed
                'Order Status',     # Dynamic status from Amazon
                'Product Name',
                'Quantitiy Ordered',  # Note: keeping your exact spelling "Quantitiy"
                'Order summary',    # Shows "Item 1 of 3" etc. (lowercase 's')
                'Order ID',
                'Purchase Date',    # Formatted date
                'Ship Date',        # Dynamic ship date from Amazon
                'Buyer Name',
                'Ship City',
                'Ship State',
                'ASIN'
            ]
            self.worksheet.append_row(headers)
            
            # Setup dropdown validations
            self.setup_dropdown_validations()
            
        print(f"✅ Connected to Google Sheet: {self.spreadsheet.title}")
        
        # Debug: Print column layout for verification
        self.print_column_layout()
    
    def print_column_layout(self):
        """Print the column layout for debugging purposes"""
        try:
            headers = self.worksheet.row_values(1)
            print("📋 Current column layout:")
            for i, header in enumerate(headers):
                print(f"   Column {chr(65+i)} (index {i}): {header}")
                if header == 'Order ID':
                    print(f"   ✅ Order ID found at index {i} (Column {chr(65+i)})")
        except Exception as e:
            print(f"⚠️ Could not print column layout: {e}")
    
    def update_headers_if_needed(self):
        """Update existing worksheet headers to match new format"""
        try:
            # Get current headers (first row)
            current_headers = self.worksheet.row_values(1)
            
            # Define the correct headers
            correct_headers = [
                'Sr. No.',          # Auto-incrementing serial number
                'Print Status',      # Dropdown: Not Printed/Printed
                'SKU Status',       # Dropdown: Not Packed/Box Packed
                'Order Status',     # Dynamic status from Amazon
                'Product Name',
                'Quantitiy Ordered',  # Note: keeping your exact spelling "Quantitiy"
                'Order summary',    # Shows "Item 1 of 3" etc. (lowercase 's')
                'Order ID',
                'Purchase Date',    # Formatted date
                'Ship Date',        # Dynamic ship date from Amazon
                'Buyer Name',
                'Ship City',
                'Ship State',
                'ASIN'
            ]
            
            # Check if headers need updating
            headers_need_update = False
            
            # If we don't have the right number of columns or different headers
            if len(current_headers) != len(correct_headers):
                headers_need_update = True
            else:
                for i, (current, correct) in enumerate(zip(current_headers, correct_headers)):
                    if current != correct:
                        headers_need_update = True
                        break
            
            if headers_need_update:
                print("🔄 Updating worksheet headers to new format...")
                
                # Update the header row
                self.worksheet.update('A1:N1', [correct_headers])
                
                # Update serial numbers for existing data
                self.update_serial_numbers_for_existing_data()
                
                print("✅ Headers updated successfully!")
            else:
                print("ℹ️ Headers are already in correct format")
                
        except Exception as e:
            print(f"⚠️ Could not update headers: {e}")
    
    def update_serial_numbers_for_existing_data(self):
        """Add serial numbers to existing data starting from 193"""
        try:
            existing_data = self.worksheet.get_all_values()
            if len(existing_data) <= 1:
                return  # No data to update
            
            print("🔢 Adding serial numbers to existing orders...")
            
            # Get all rows except header
            data_rows = existing_data[1:]
            
            # Group by Order ID to assign same serial number to items from same order
            order_groups = {}
            for i, row in enumerate(data_rows):
                if len(row) > 7:  # Make sure we have Order ID column
                    order_id = row[7]  # Order ID is at index 7 (column H)
                    if order_id not in order_groups:
                        order_groups[order_id] = []
                    order_groups[order_id].append(i + 2)  # +2 because row index starts from 2 (after header)
            
            # Assign serial numbers starting from 193
            serial_number = 193
            updates = []
            
            for order_id, row_indices in order_groups.items():
                # All rows with same order ID get same serial number
                for row_index in row_indices:
                    updates.append({
                        'range': f'A{row_index}',
                        'values': [[str(serial_number)]]
                    })
                serial_number += 1
            
            # Batch update all serial numbers
            if updates:
                self.worksheet.batch_update(updates)
                print(f"✅ Added serial numbers to {len(updates)} rows, starting from 193")
            
        except Exception as e:
            print(f"⚠️ Could not update serial numbers: {e}")
    
    def setup_dropdown_validations(self):
        """Setup dropdown menus for Print Status and SKU Status columns"""
        try:
            # Print Status dropdown (Column B - shifted due to Sr. No.)
            print_status_rule = {
                "requests": [
                    {
                        "setDataValidation": {
                            "range": {
                                "sheetId": self.worksheet.id,
                                "startRowIndex": 1,  # Start from row 2 (after header)
                                "endRowIndex": 1000,  # Apply to 1000 rows
                                "startColumnIndex": 1,  # Column B (was A)
                                "endColumnIndex": 2
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
            
            # SKU Status dropdown (Column C - shifted due to Sr. No.)
            sku_status_rule = {
                "requests": [
                    {
                        "setDataValidation": {
                            "range": {
                                "sheetId": self.worksheet.id,
                                "startRowIndex": 1,  # Start from row 2 (after header)
                                "endRowIndex": 1000,  # Apply to 1000 rows
                                "startColumnIndex": 2,  # Column C (was B)
                                "endColumnIndex": 3
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
    
    def get_next_serial_number(self):
        """Get the next serial number starting from 193"""
        try:
            existing_data = self.worksheet.get_all_values()
            if len(existing_data) <= 1:
                return 193  # Start from 193 if no data
            
            # Get serial numbers from column A (index 0)
            serial_numbers = []
            for row in existing_data[1:]:  # Skip header
                if len(row) > 0 and row[0]:
                    try:
                        serial_numbers.append(int(row[0]))
                    except ValueError:
                        continue  # Skip non-numeric values
            
            if not serial_numbers:
                return 193  # Start from 193 if no valid serial numbers
            
            # Return the highest serial number + 1, but ensure minimum is 193
            next_serial = max(serial_numbers) + 1
            return max(next_serial, 193)
            
        except Exception as e:
            print(f"⚠️ Could not get serial number: {e}")
            return 193  # Default to 193 on error
    
    def get_existing_unique_ids(self):
        """Get existing order IDs to prevent duplicates"""
        try:
            existing_data = self.worksheet.get_all_values()
            if len(existing_data) <= 1:
                return set()
            
            # Get Order IDs from column H (index 7) - Order ID column position
            order_ids = set()
            for row in existing_data[1:]:  # Skip header row
                if len(row) > 7 and row[7]:  # Ensure row has Order ID column and it's not empty
                    order_id = row[7].strip()  # Remove any whitespace
                    if order_id and order_id != 'N/A':  # Only add valid Order IDs
                        order_ids.add(order_id)
            
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
    
    def get_ship_date(self, order, order_items):
        """Get ship date from order or order items"""
        try:
            # Check multiple possible ship date fields from Amazon SP-API
            
            # 1. Check order-level ship date fields
            ship_date_fields = ['ShipDate', 'LatestShipDate', 'EarliestShipDate']
            for field in ship_date_fields:
                ship_date = order.get(field, None)
                if ship_date:
                    return self.format_purchase_date(ship_date)
            
            # 2. Check order items for shipping info
            for item in order_items:
                # Check item-level ship date fields
                item_ship_fields = ['ShipDate', 'LatestShipDate', 'EarliestShipDate']
                for field in item_ship_fields:
                    ship_date = item.get(field, None)
                    if ship_date:
                        return self.format_purchase_date(ship_date)
            
            # 3. Check for fulfillment data in order items
            for item in order_items:
                fulfillment_data = item.get('FulfillmentData', {})
                if fulfillment_data:
                    ship_date = fulfillment_data.get('ShipDate', None)
                    if ship_date:
                        return self.format_purchase_date(ship_date)
            
            # 4. If no ship date found, return based on order status
            order_status = order.get('OrderStatus', '').lower()
            if order_status in ['pending', 'unshipped', 'partiallyshipped']:
                return 'Pending'
            elif order_status == 'shipped':
                return 'Shipped (Date TBD)'
            elif order_status in ['delivered', 'invoiceunconfirmed']:
                return 'Delivered (Date TBD)'
            elif order_status == 'canceled':
                return 'Canceled'
            else:
                return 'N/A'
                
        except Exception as e:
            print(f"⚠️ Error getting ship date: {e}")
            return 'N/A'
    
    def update_existing_orders(self):
        """Update order status and ship date for existing orders in the sheet"""
        try:
            print("🔄 Checking for updates to existing orders...")
            
            existing_data = self.worksheet.get_all_values()
            if len(existing_data) <= 1:
                print("ℹ️ No existing orders to update")
                return
            
            updated_count = 0
            
            # Process each row (skip header)
            for row_index, row in enumerate(existing_data[1:], start=2):
                if len(row) < 8:  # Need at least Order ID column (index 7, so need 8 elements)
                    continue
                
                order_id = row[7].strip() if row[7] else ''  # Order ID is in column H (index 7)
                if not order_id or order_id == 'N/A':
                    continue
                
                current_order_status = row[3]  # Order Status is in column D (index 3)
                current_ship_date = row[9] if len(row) > 9 else 'N/A'  # Ship Date is in column J (index 9)
                
                # Get latest order data from Amazon
                try:
                    amazon_credentials = get_amazon_credentials()
                    orders_api = Orders(marketplace=Marketplaces.IN, credentials=amazon_credentials)
                    
                    # Get order details
                    order_response = orders_api.get_order(order_id)
                    order_data = order_response.payload
                    
                    # Get order items for ship date info
                    order_items = self.get_order_details(order_id)
                    
                    # Get latest status and ship date
                    latest_order_status = order_data.get('OrderStatus', 'N/A')
                    latest_ship_date = self.get_ship_date(order_data, order_items)
                    
                    # Check if updates are needed
                    status_changed = current_order_status != latest_order_status
                    ship_date_changed = current_ship_date != latest_ship_date
                    
                    if status_changed or ship_date_changed:
                        print(f"🔄 Updating order {order_id}:")
                        
                        if status_changed:
                            print(f"   📊 Status: {current_order_status} → {latest_order_status}")
                            # Update Order Status (column D)
                            self.worksheet.update_cell(row_index, 4, latest_order_status)
                        
                        if ship_date_changed:
                            print(f"   📅 Ship Date: {current_ship_date} → {latest_ship_date}")
                            # Update Ship Date (column J)
                            self.worksheet.update_cell(row_index, 10, latest_ship_date)
                        
                        updated_count += 1
                        
                        # Small delay to avoid API rate limits
                        time.sleep(0.5)
                    
                except Exception as order_error:
                    print(f"⚠️ Could not update order {order_id}: {order_error}")
                    continue
            
            if updated_count > 0:
                print(f"✅ Updated {updated_count} existing orders")
            else:
                print("ℹ️ No existing orders needed updates")
                
        except Exception as e:
            print(f"❌ Error updating existing orders: {e}")
    
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
            
            # Get ship date
            ship_date = self.get_ship_date(order, order_items)
            
            # Get next serial number for this order (same for all items in the order)
            serial_number = self.get_next_serial_number()
            
            if order_items:
                total_items_in_order = len(order_items)
                
                for idx, item in enumerate(order_items, 1):
                    # Create order summary info
                    order_summary = f"Item {idx} of {total_items_in_order}"
                    if total_items_in_order > 1:
                        order_summary += f" 📦 SAME ORDER"
                    
                    # Get order status (no more conversion from "Shipped" to "Ordered")
                    order_status = order.get('OrderStatus', 'N/A')
                    
                    # Create row data in new column order (with Sr. No. and Ship Date)
                    row_data = [
                        str(serial_number), # Sr. No. (same for all items in order)
                        'Not Printed',  # Print Status (default)
                        'Not Packed',   # SKU Status (default)
                        order_status,   # Order Status (no conversion)
                        item.get('Title', 'N/A'),
                        str(item.get('QuantityOrdered', 0)),
                        order_summary,  # Order Summary
                        order_id,       # Order ID
                        formatted_date,
                        ship_date,      # Ship Date
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
                # Get order status (no more conversion from "Shipped" to "Ordered")
                order_status = order.get('OrderStatus', 'N/A')
                
                # Get ship date for this order
                ship_date = self.get_ship_date(order, [])
                
                # Get serial number for this order
                serial_number = self.get_next_serial_number()
                
                row_data = [
                    str(serial_number), # Sr. No.
                    'Not Printed',  # Print Status (default)
                    'Not Packed',   # SKU Status (default)
                    order_status,   # Order Status (no conversion)
                    'No items found',
                    '0',
                    'Single Item',  # Order summary
                    order_id,       # Order ID
                    formatted_date,
                    ship_date,      # Ship Date
                    buyer_name,
                    ship_city,
                    ship_state,
                    'N/A'
                ]
                
                self.worksheet.insert_row(row_data, index=2)
                new_orders_added += 1
                existing_order_ids.add(order_id)
        
        print(f"🎉 New orders sync complete!")
        print(f"✅ Added {new_orders_added} new orders")
        print(f"⏭️ Skipped {skipped_duplicates} duplicates")
        
        # Update existing orders for dynamic status and ship date changes
        self.update_existing_orders()
        
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
    print("   • Auto-incrementing serial numbers starting from 193")
    print("   • Dynamic ship date tracking with real-time updates")
    print("   • Dynamic order status updates for existing orders")
    print("   • Original order status (no Shipped->Ordered conversion)")
    
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
