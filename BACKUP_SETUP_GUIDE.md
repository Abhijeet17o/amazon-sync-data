# BACKUP SYNC - LOCAL SETUP GUIDE

## 📋 Purpose
This backup script fetches the **last 2 days (48 hours)** of Amazon orders and populates them into your Google Sheet with the latest 14-column layout.

## ⚠️ Important Notes
- **Local Use Only**: Credentials are exposed in the script
- **No Duplicate Handling**: Simple backup function
- **API Rate Limiting**: 3-second delay after every 10 orders
- **No Dynamic Updates**: Just raw data population

## 📊 Column Layout (14 Columns)
1. **Sr. No.** - Auto-incrementing from 193
2. **Print Status** - Default: "Not Printed"
3. **SKU Status** - Default: "Not Packed"
4. **Order Status** - Direct from Amazon
5. **Product Name**
6. **Quantitiy Ordered** (exact spelling preserved)
7. **Order summary** - "Item 1 of 3" for multi-item orders
8. **Order ID**
9. **Purchase Date** - Formatted: "Jul 30, 2025 06:13 PM"
10. **Ship Date** - Dynamic from Amazon
11. **Buyer Name**
12. **Ship City**
13. **Ship State**
14. **ASIN**

## 🚀 How to Run Locally

### Step 1: Update Amazon Credentials
Open `backup_column_file_fixed.py` and update the credentials section:

```python
# Your Amazon credentials (EXPOSED FOR LOCAL USE - REPLACE WITH YOUR ACTUAL CREDENTIALS)
AMAZON_CREDENTIALS = {
    'refresh_token': 'YOUR_ACTUAL_REFRESH_TOKEN_HERE',
    'lwa_app_id': 'YOUR_ACTUAL_LWA_APP_ID_HERE',
    'lwa_client_secret': 'YOUR_ACTUAL_LWA_CLIENT_SECRET_HERE',
}
```

### Step 2: Ensure Google Credentials
Make sure `google_credentials.json` is in the same folder as the backup script.

### Step 3: Install Dependencies
```bash
pip install python-amazon-sp-api gspread google-auth google-auth-oauthlib google-auth-httplib2
```

### Step 4: Run the Backup
Choose one of these methods:

**Method 1: Direct Script**
```bash
python backup_column_file_fixed.py
```

**Method 2: Using Runner**
```bash
python run_backup.py
```

**Method 3: PowerShell (Windows)**
```powershell
python backup_column_file_fixed.py
```

## 📤 Expected Output
```
🎯 BACKUP AMAZON TO GOOGLE SHEETS SYNC
============================================================
📋 BACKUP PURPOSE:
   • Fetch last 2 DAYS (48 hours) of orders from Amazon
   • Populate data into Google Sheet
   • No duplicate handling (simple backup function)
   • API rate limiting: 3-second delay after every 10 orders

✅ Connected to Google Sheet: Your Sheet Name
📥 Fetching orders from last 2 days (48 hours)...
📦 Found 15 orders from last 2 days
🔄 Starting backup sync of 15 orders...
📋 Processing order 1/15: 123-4567890-1234567
✅ Added: Product Name Here...
⏳ API Rate Limiting: Processed 10 orders, waiting 3 seconds...
🎉 Backup sync complete!
✅ Added 25 order items from 15 orders
📊 Last 2 days of data successfully backed up to sheet
```

## 🔧 Troubleshooting

### Common Issues:

**1. "❌ Error fetching orders"**
- Check your Amazon credentials
- Verify SP-API access permissions
- Ensure marketplace is set correctly (IN for India)

**2. "❌ Error: google_credentials.json not found"**
- Make sure the file is in the same folder
- Check file name spelling (case-sensitive)

**3. "❌ Error adding row"**
- Check Google Sheet permissions
- Verify service account has edit access
- Check if sheet exists and is accessible

**4. Rate Limiting Issues**
- The script includes 3-second delays after every 10 orders
- If you still hit limits, increase the delay in the code

### Verification Steps:
1. Check that orders appear in your Google Sheet
2. Verify 14-column layout is correct
3. Confirm serial numbers start from 193
4. Check that newest orders appear at the top

## ⚡ Quick Commands

**Check if everything is ready:**
```bash
# Check Python installation
python --version

# Check if required files exist
dir google_credentials.json
dir backup_column_file_fixed.py

# Test Google Sheets connection (optional)
python -c "import gspread; print('✅ gspread available')"
```

**Run with verbose output:**
```bash
python backup_column_file_fixed.py 2>&1 | findstr /V "INFO"
```

## 📝 Notes
- This script will add data to the **top** of your sheet (newest first)
- Serial numbers auto-increment based on existing data
- Multi-item orders will show "Item 1 of 3" format
- Ship dates are fetched dynamically from Amazon when available
- Order status is taken directly from Amazon (no conversions)

## 🔄 Regular Backup Schedule
For regular backups, you can create a Windows batch file:

```batch
@echo off
echo Running Amazon Backup Sync...
cd /d "f:\ALL CODE\Order Notifier\amazon-sync-clean"
python backup_column_file_fixed.py
pause
```

Save as `run_backup.bat` and double-click to run.
