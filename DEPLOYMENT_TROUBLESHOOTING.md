# Azure Functions Deployment Troubleshooting

## 🚨 Common Issues & Solutions

### 1. "Not Found (CODE: 404)" Error

**Cause:** Azure Function App doesn't exist or publish profile is incorrect.

**Solutions:**
1. **Check Azure Function App Name**
   - Verify the app name `simple-amazon-sync` exists in your Azure portal
   - If not, create a new Function App with this exact name

2. **Update Publish Profile**
   ```bash
   # In Azure portal:
   # 1. Go to your Function App
   # 2. Go to "Get publish profile" 
   # 3. Download the .publishsettings file
   # 4. Copy entire content to GitHub secret AZURE_PUBLISH_PROFILE
   ```

3. **Recreate Function App (if needed)**
   - Delete existing Function App in Azure portal
   - Create new one with name: `simple-amazon-sync`
   - Runtime: Python 3.11
   - Plan: Consumption (free tier)

### 2. Environment Variables Missing

**Required Azure Function App Settings:**
```
AMAZON_REFRESH_TOKEN=your_token_here
AMAZON_LWA_APP_ID=your_app_id_here  
AMAZON_LWA_CLIENT_SECRET=your_secret_here
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/1REsoseklT3qWeUVI7ngGrpLBe-6WPo-gjsTIgV5Cw4U
```

### 3. Required GitHub Secrets

```
AZURE_PUBLISH_PROFILE=<content_of_.publishsettings_file>
GOOGLE_CREDENTIALS_JSON=<content_of_google_credentials.json>
```

### 4. File Structure Check

Ensure your repo has:
```
├── host.json
├── requirements.txt  
├── TimerTrigger1/
│   ├── function.json
│   └── __init__.py
└── custom_column_sync.py
```

### 5. Manual Deployment Alternative

If GitHub Actions fail, deploy manually:

```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Login to Azure
az login

# Deploy function
func azure functionapp publish simple-amazon-sync
```

### 6. Check Deployment Status

After deployment, verify in Azure portal:
1. Go to Function App → Functions
2. Should see "TimerTrigger1" function
3. Check "Monitor" tab for execution logs
4. Verify "Configuration" has all environment variables

## 🔧 Quick Fix Commands

**Force redeploy:**
```bash
git commit --allow-empty -m "Force Azure redeploy"
git push origin main
```

**Check logs:**
- Azure Portal → Function App → Log Stream
- Azure Portal → Function App → Monitor → Application Insights

## 📞 Need Help?

1. Check Azure Function logs in the portal
2. Verify all secrets are set correctly in GitHub
3. Ensure Function App name matches exactly: `simple-amazon-sync`
4. Try manual deployment if GitHub Actions continue to fail
