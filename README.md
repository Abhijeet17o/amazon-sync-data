# Amazon to Google Sheets Sync - Azure Functions

Secure, automated Amazon order synchronization with Google Sheets using Azure Functions with enhanced duplicate prevention and dynamic order status updates.

## 🚀 Features

- **Automated Sync**: Timer trigger every minute with intelligent sleep mode
- **Smart Sleep Mode**: No checking from 12:30 AM - 5:30 AM IST
- **Secure Credentials**: Environment variables only (no hardcoded secrets)
- **🆕 Enhanced Duplicate Prevention**: Multi-level duplicate detection (Order + Item level)
- **🆕 Dynamic Status Updates**: Real-time order status and ship date updates for orders from last 6 hours
- **🆕 Serial Number Management**: Auto-incrementing serial numbers starting from 193
- **Custom Formatting**: Dropdown menus for Print Status and SKU Status
- **🆕 Standardized 14-Column Layout**: Consistent column structure across all implementations
- **Azure Functions Ready**: Complete deployment configuration included

## 📋 Standardized Column Structure (14 Columns)

1. **Sr. No.** (Auto-incrementing, starts from 193)
2. **Print Status** (Dropdown: Not Printed/Printed)
3. **SKU Status** (Dropdown: Not Packed/Box Packed)
4. **Order Status** (Dynamic updates from Amazon)
5. **Product Name**
6. **Quantity Ordered**
7. **Order Summary** (Shows "Item 1 of 3" for multi-item orders)
8. **Order ID**
9. **Purchase Date** (Formatted: Jul 30, 2025 06:13 PM)
10. **Ship Date** (Dynamic updates from Amazon)
11. **Buyer Name**
12. **Ship City**
13. **Ship State**
14. **ASIN**

## 🆕 Enhanced Features

### Dynamic Order Updates
- **6-Hour Window**: Only processes orders from the last 6 hours for efficiency
- **Status Monitoring**: Tracks important status transitions:
  - Pending → Ordered
  - Pending → Cancelled
  - Ordered → Cancelled
- **Ship Date Updates**: Automatically updates ship dates when available from Amazon
- **Smart Filtering**: Uses purchase date to identify recent orders only

### Advanced Duplicate Prevention
- **Order-Level**: Prevents duplicate orders by Order ID
- **Item-Level**: Prevents duplicate items within orders using Order ID + ASIN combination
- **Batch Processing**: Atomic insertion to prevent partial order data

### Serial Number Management
- **Auto-Increment**: Serial numbers start from 193 and increment for each unique order
- **Same Order Items**: All items from the same order get the same serial number
- **Backward Compatibility**: Automatically adds serial numbers to existing data

## 🛠 Deployment Guide

### Prerequisites
- Azure Function App created (`simple-amazon-sync`)
- Google Sheets API credentials (`google_credentials.json`)
- Amazon SP-API credentials

### Step 1: Set Environment Variables in Azure

Go to your Azure Function App → Configuration → Application Settings:

```bash
AMAZON_REFRESH_TOKEN=your_actual_refresh_token
AMAZON_LWA_APP_ID=your_actual_app_id
AMAZON_LWA_CLIENT_SECRET=your_actual_client_secret
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/your_sheet_id
FUNCTIONS_WORKER_RUNTIME=python
```

### Step 2: GitHub Deployment Setup

1. Add GitHub Secret: `AZURE_PUBLISH_PROFILE`
2. Get publish profile from Azure Function App → Get publish profile
3. Copy entire XML content to the GitHub secret

### Step 3: Deploy

Push to the `main` branch and GitHub Actions will automatically deploy.

## ⏰ Schedule Details

- **Frequency**: Every minute (`0 * * * * *`)
- **Sleep Hours**: 12:30 AM - 5:30 AM IST (no sync during these hours)
- **Lookback**: Checks last 6 hours for orders (handles sleep time gaps)
- **Dynamic Updates**: Monitors order status changes for recent orders only
- **API Efficiency**: Rate-limited with intelligent delays to avoid overwhelming Amazon API

## 🔄 Sync Process

### New Orders
1. Fetches orders from last 6 hours via Amazon SP-API
2. Checks for existing Order ID + ASIN combinations
3. Adds new orders with auto-incremented serial numbers
4. Applies default dropdown values (Not Printed, Not Packed)

### Existing Order Updates
1. Identifies orders from last 6 hours in the sheet
2. Compares current vs latest status from Amazon
3. Updates only Order Status (Column D) and Ship Date (Column J)
4. Logs important status transitions for monitoring

## 🛡️ Data Integrity

- **Atomic Operations**: Batch processing prevents partial data insertion
- **Column Consistency**: All references use standardized column mapping
- **Error Handling**: Graceful failure handling with detailed logging
- **Validation**: Input validation and data sanitization

## 🔒 Security

- All credentials stored as environment variables
- No secrets in code or repository
- Google credentials managed separately
- `.gitignore` protects sensitive files

## 🧪 Local Testing

### Option 1: Development Script
```bash
# Set environment variables
export AMAZON_REFRESH_TOKEN="your_token"
export AMAZON_LWA_APP_ID="your_app_id"
export AMAZON_LWA_CLIENT_SECRET="your_secret"
export GOOGLE_SHEET_URL="your_sheet_url"

# Run standalone script
python custom_column_sync.py
```

### Option 2: Azure Functions Local Runtime
```bash
# Install Azure Functions Core Tools
func start

# Test the timer trigger locally
func run TimerTrigger1
```

## 📊 Monitoring & Logging

### Azure Functions Logs
- Sync status and order counts
- Important status transitions
- Error details and API responses
- Performance metrics and timing

### Google Sheets Updates
- New orders appear at the top (row 2)
- Status changes logged in Azure logs
- Serial numbers for order tracking
- Dropdown menus ready for manual input

### Key Metrics
- **New Orders Added**: Count of fresh orders synced
- **Duplicates Skipped**: Efficiency indicator
- **Status Updates**: Dynamic changes detected
- **API Calls**: Rate limiting and optimization

## 🆘 Troubleshooting

### Common Issues
- **No orders syncing**: Check environment variables in Azure Function App
- **Google Sheets error**: Verify `google_credentials.json` is uploaded correctly
- **Deployment failed**: Check GitHub Actions logs for details
- **Schedule not working**: Verify timer trigger configuration in function.json
- **Column mismatch**: Headers auto-update to standardized 14-column format
- **Serial number issues**: System automatically assigns numbers starting from 193

### Debug Steps
1. **Check Azure Function Logs**: Monitor execution and error details
2. **Verify Environment Variables**: Ensure all required credentials are set
3. **Test Google Sheets Access**: Confirm permissions and sheet URL
4. **Amazon API Status**: Check for API rate limits or credential issues
5. **Column Layout**: Verify 14-column standardized structure

## 🔧 Configuration Files

### Required Files
- `TimerTrigger1/__init__.py` - Main Azure Function code
- `custom_column_sync.py` - Standalone development script  
- `function.json` - Timer trigger configuration
- `host.json` - Azure Functions host settings
- `requirements.txt` - Python dependencies
- `google_credentials.json` - Google Sheets API credentials (not in repo)

### Environment Variables
```bash
# Amazon SP-API Credentials
AMAZON_REFRESH_TOKEN=your_refresh_token
AMAZON_LWA_APP_ID=your_app_id  
AMAZON_LWA_CLIENT_SECRET=your_client_secret

# Google Sheets
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/your_sheet_id

# Azure Functions
FUNCTIONS_WORKER_RUNTIME=python
```

## 📈 Version History

- **v2025-08-02**: Enhanced duplicate prevention, dynamic 6-hour updates, standardized 14-column layout
- **v2025-07-31**: Serial number management, improved error handling, batch processing
- **v2025-07-30**: Basic Azure Functions implementation with timer triggers
- **v2025-07-29**: Initial release with manual sync capability
