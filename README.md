# Amazon to Google Sheets Sync - Azure Functions

Secure, automated Amazon order synchronization with Google Sheets using Azure Functions.

## 🚀 Features

- **Automated Sync**: Timer trigger every minute
- **Smart Sleep Mode**: No checking from 12:30 AM - 5:30 AM IST
- **Secure Credentials**: Environment variables only (no hardcoded secrets)
- **Duplicate Prevention**: Automatic order ID tracking
- **Custom Formatting**: Dropdown menus for Print Status and SKU Status
- **Azure Functions Ready**: Complete deployment configuration included

## 📋 Column Structure

1. **Print Status** (Dropdown: Not Printed/Printed)
2. **SKU Status** (Dropdown: Not Packed/Box Packed)
3. **Order Status**
4. **Product Name**
5. **Quantity Ordered**
6. **Order Summary** (Shows "Item 1 of 3" for multi-item orders)
7. **Order ID**
8. **Purchase Date** (Formatted: Jul 30, 2025 06:13 PM)
9. **Buyer Name**
10. **Total Amount**
11. **Ship City**
12. **Ship State**
13. **ASIN**

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
- **Lookback**: Checks last 2 hours for orders to prevent missing any

## 🔒 Security

- All credentials stored as environment variables
- No secrets in code or repository
- Google credentials managed separately
- `.gitignore` protects sensitive files

## 🧪 Local Testing

```bash
# Set environment variables
export AMAZON_REFRESH_TOKEN="your_token"
export AMAZON_LWA_APP_ID="your_app_id"
export AMAZON_LWA_CLIENT_SECRET="your_secret"

# Run locally
python custom_column_sync.py
```

## 📊 Monitoring

- Azure Function App logs show sync status
- Google Sheets populated with new orders
- Duplicate prevention keeps data clean

## 🆘 Troubleshooting

- **No orders syncing**: Check environment variables in Azure
- **Google Sheets error**: Verify `google_credentials.json` uploaded
- **Deployment failed**: Check GitHub Actions logs
- **Schedule not working**: Verify timer trigger in function.json
