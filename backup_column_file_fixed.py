"""
BACKUP AMAZON TO GOOGLE SHEETS SYNC - Local Use Only
====================================================
BACKUP FILE PURPOSE:
- Fetch last 2 DAYS (48 hours) of orders from Amazon Seller API
- Populate data into Google Sheet with latest 14-column layout
- NO duplicate handling (simple backup function)
- NO dynamic checks or updates
- API rate limiting: 3-second delay after every 10 orders

Column Layout (Latest 14-Column Format):
1. Sr. No. (Auto-incrementing from 193)
2. Print Status (Dropdown: Not Printed/Printed)  
3. SKU Status (Dropdown: Not Packed/Box Packed)
4. Order Status (Direct from Amazon)
5. Product Name
6. Quantitiy Ordered (exact spelling preserved)
7. Order summary (Shows "Item 1 of 3" for multi-item orders)
8. Order ID  
9. Purchase Date (Formatted: Jul 30, 2025 06:13 PM)
10. Ship Date (Dynamic from Amazon)
11. Buyer Name
12. Ship City
13. Ship State
14. ASIN

⚠️ CREDENTIALS EXPOSED FOR LOCAL USE ONLY - NOT FOR DEPLOYMENT
Version: 2025-08-02 - Backup Function Aligned with Latest Updates
"""

import os
import json
import time
from datetime import datetime, timedelta

# Amazon SP-API imports
from sp_api.api import Orders
from sp_api.base import SellingApiException, Marketplaces

# Google Sheets imports
import gspread
from google.oauth2.service_account import Credentials

# Your Amazon credentials (EXPOSED FOR LOCAL USE - REPLACE WITH YOUR ACTUAL CREDENTIALS)
AMAZON_CREDENTIALS = {
    'refresh_token': 'YOUR_ACTUAL_REFRESH_TOKEN_HERE',
    'lwa_app_id': 'YOUR_ACTUAL_LWA_APP_ID_HERE',
    'lwa_client_secret': 'YOUR_ACTUAL_LWA_CLIENT_SECRET_HERE',
}

class BackupAmazonSync:
    def __init__(self, sheet_url):
        self.sheet_url = sheet_url
        # Initialize Amazon orders API with exposed credentials
        self.orders_api = Orders(marketplace=Marketplaces.IN, credentials=AMAZON_CREDENTIALS)
        self.setup_google_sheets()
        
    def setup_google_sheets(self):
        """Setup Google Sheets connection with latest 14-column layout"""
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
            print(f"✅ Connected to existing worksheet: {self.worksheet.title}")
            
        except gspread.WorksheetNotFound:
            self.worksheet = self.spreadsheet.add_worksheet(title='Orders', rows=1000, cols=14)
            
            # Add headers in latest 14-column format
            headers = [
                'Sr. No.',           # Auto-incrementing serial number
                'Print Status',      # Dropdown: Not Printed/Printed
                'SKU Status',        # Dropdown: Not Packed/Box Packed
                'Order Status',      # Direct status from Amazon
                'Product Name',
                'Quantitiy Ordered', # Note: keeping exact spelling "Quantitiy"
                'Order summary',     # Shows "Item 1 of 3" etc. (lowercase 's')
                'Order ID',
                'Purchase Date',     # Formatted date
                'Ship Date',         # Dynamic ship date from Amazon
                'Buyer Name',
                'Ship City',
                'Ship State',
                'ASIN'
            ]
            self.worksheet.append_row(headers)
            print(f"✅ Created new worksheet with 14-column layout")
            
        print(f"✅ Connected to Google Sheet: {self.spreadsheet.title}")

    
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
        """🆕 Get the next serial number starting from 193"""
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
    
    def get_ship_date(self, order, order_items):
        """🆕 Get ship date from order or order items"""
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
    

    
    def get_last_2_days_orders(self):
        """Get orders from last 2 days (48 hours) for backup purposes"""
        try:
            print("📥 Fetching orders from last 2 days (48 hours)...")
            
            created_after = (datetime.now() - timedelta(hours=48)).isoformat()
            response = self.orders_api.get_orders(CreatedAfter=created_after, MaxResultsPerPage=50)
            
            orders = response.payload.get('Orders', [])
            print(f"📦 Found {len(orders)} orders from last 2 days")
            
            return orders
            
        except Exception as e:
            print(f"❌ Error fetching orders: {e}")
            return []
    
    def get_order_details(self, order_id):
        """Get detailed order information including items"""
        try:
            items_response = self.orders_api.get_order_items(order_id)
            order_items = items_response.payload.get('OrderItems', [])
            
            return order_items
            
        except Exception as e:
            print(f"❌ Error getting order details for {order_id}: {e}")
            return []
    
    def backup_sync_to_sheet(self, orders):
        """Simple backup sync - populate all orders without duplicate checking"""
        if not orders:
            print("ℹ️ No orders to backup")
            return
            
        orders_added = 0
        order_count = 0
        
        print(f"🔄 Starting backup sync of {len(orders)} orders...")
        
        for order in orders:
            order_count += 1
            order_id = order.get('AmazonOrderId')
            
            print(f"📋 Processing order {order_count}/{len(orders)}: {order_id}")
            
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
            
            # Get next serial number for this order
            serial_number = self.get_next_serial_number()
            
            if order_items:
                total_items_in_order = len(order_items)
                
                for idx, item in enumerate(order_items, 1):
                    # Create order summary info
                    order_summary = f"Item {idx} of {total_items_in_order}"
                    if total_items_in_order > 1:
                        order_summary += f" 📦 SAME ORDER"
                    
                    # Get order status (no conversion - direct from Amazon)
                    order_status = order.get('OrderStatus', 'N/A')
                    
                    # Create row data in latest 14-column layout
                    row_data = [
                        str(serial_number),                    # 1. Sr. No.
                        'Not Printed',                         # 2. Print Status (default)
                        'Not Packed',                          # 3. SKU Status (default)
                        order_status,                          # 4. Order Status (direct from Amazon)
                        item.get('Title', 'N/A'),            # 5. Product Name
                        str(item.get('QuantityOrdered', 0)),  # 6. Quantitiy Ordered
                        order_summary,                         # 7. Order Summary
                        order_id,                             # 8. Order ID
                        formatted_date,                       # 9. Purchase Date
                        ship_date,                            # 10. Ship Date
                        buyer_name,                           # 11. Buyer Name
                        ship_city,                            # 12. Ship City
                        ship_state,                           # 13. Ship State
                        item.get('ASIN', 'N/A')              # 14. ASIN
                    ]
                    
                    # Insert at row 2 (after headers) to keep newest at top
                    try:
                        self.worksheet.insert_row(row_data, index=2)
                        orders_added += 1
                        
                        print(f"✅ Added: {item.get('Title', 'N/A')[:50]}...")
                        
                        # Small delay to avoid overwhelming the API
                        time.sleep(0.3)
                        
                    except Exception as e:
                        print(f"❌ Error adding row: {e}")
                        
            else:
                # Handle orders without items
                order_status = order.get('OrderStatus', 'N/A')
                
                row_data = [
                    str(serial_number),     # 1. Sr. No.
                    'Not Printed',          # 2. Print Status (default)
                    'Not Packed',           # 3. SKU Status (default)
                    order_status,           # 4. Order Status (direct from Amazon)
                    'No items found',       # 5. Product Name
                    '0',                    # 6. Quantitiy Ordered
                    'Single Item',          # 7. Order Summary
                    order_id,               # 8. Order ID
                    formatted_date,         # 9. Purchase Date
                    ship_date,              # 10. Ship Date
                    buyer_name,             # 11. Buyer Name
                    ship_city,              # 12. Ship City
                    ship_state,             # 13. Ship State
                    'N/A'                   # 14. ASIN
                ]
                
                try:
                    self.worksheet.insert_row(row_data, index=2)
                    orders_added += 1
                    print(f"✅ Added order without items: {order_id}")
                    time.sleep(0.3)
                except Exception as e:
                    print(f"❌ Error adding order: {e}")
            
            # API RATE LIMITING: Add delay after every 10 orders
            if order_count % 10 == 0:
                print(f"⏳ API Rate Limiting: Processed {order_count} orders, waiting 3 seconds...")
                time.sleep(3)
        
        print(f"🎉 Backup sync complete!")
        print(f"✅ Added {orders_added} order items from {len(orders)} orders")
        print(f"📊 Last 2 days of data successfully backed up to sheet")


def main():
    """Backup function - fetch last 2 days of orders"""
    print("🎯 BACKUP AMAZON TO GOOGLE SHEETS SYNC")
    print("=" * 60)
    print("📋 BACKUP PURPOSE:")
    print("   • Fetch last 2 DAYS (48 hours) of orders from Amazon")
    print("   • Populate data into Google Sheet")
    print("   • No duplicate handling (simple backup function)")
    print("   • API rate limiting: 3-second delay after every 10 orders")
    print("")
    print("📊 Latest 14-Column Layout:")
    print("   1. Sr. No. (Auto-incrementing from 193)")
    print("   2. Print Status (Default: Not Printed)")
    print("   3. SKU Status (Default: Not Packed)")
    print("   4. Order Status (Direct from Amazon)")
    print("   5. Product Name")
    print("   6. Quantitiy Ordered")
    print("   7. Order Summary (Item 1 of 3, etc.)")
    print("   8. Order ID")
    print("   9. Purchase Date (Formatted)")
    print("   10. Ship Date (Dynamic from Amazon)")
    print("   11. Buyer Name")
    print("   12. Ship City")
    print("   13. Ship State")
    print("   14. ASIN")
    print("")
    print("⚠️ CREDENTIALS EXPOSED - LOCAL USE ONLY")
    
    sheet_url = "https://docs.google.com/spreadsheets/d/1REsoseklT3qWeUVI7ngGrpLBe-6WPo-gjsTIgV5Cw4U"
    
    try:
        # Initialize backup sync
        sync = BackupAmazonSync(sheet_url)
        
        print(f"\n� Fetching orders from last 2 days (48 hours)...")
        orders = sync.get_last_2_days_orders()
        
        if orders:
            print(f"� Starting backup sync of {len(orders)} orders...")
            sync.backup_sync_to_sheet(orders)
            print("✅ Backup sync complete!")
            print("📊 Check your Google Sheet for the latest data")
        else:
            print("ℹ️ No orders found in the last 2 days")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure you:")
        print("   - Have google_credentials.json in this folder")
        print("   - Shared the sheet with the service account")
        print("   - Updated Amazon credentials in the script")
        print("   - Have valid Amazon SP-API access")

if __name__ == "__main__":
    main()
