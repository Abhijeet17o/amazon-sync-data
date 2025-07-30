#!/bin/bash
# Azure Function Status Checker

echo "🔍 Checking Azure Function Status..."
echo "=================================="

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not installed. Please install it first."
    echo "💡 Download from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Function App details
FUNCTION_APP_NAME="simple-amazon-sync"
RESOURCE_GROUP="your-resource-group-name"  # Replace with your actual resource group

echo "📊 Function App: $FUNCTION_APP_NAME"
echo ""

# Check function app status
echo "🏃 Checking if Function App is running..."
APP_STATE=$(az functionapp show --name $FUNCTION_APP_NAME --resource-group $RESOURCE_GROUP --query "state" -o tsv 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ Function App State: $APP_STATE"
else
    echo "❌ Could not retrieve Function App status"
    echo "💡 Make sure you're logged in: az login"
    echo "💡 Update RESOURCE_GROUP name in this script"
fi

echo ""
echo "🔗 Quick Links:"
echo "   • Portal: https://portal.azure.com"
echo "   • Logs: Function App → Log stream"
echo "   • Monitor: Function App → Monitor"
echo "   • Metrics: Function App → Application Insights"
