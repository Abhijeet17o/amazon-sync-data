"""
RUN BACKUP SCRIPT - AMAZON TO GOOGLE SHEETS
===========================================
Simple runner script for backup operations.

HOW TO RUN LOCALLY:
1. Update Amazon credentials in backup_column_file_fixed.py
2. Ensure google_credentials.json is in the same folder
3. Run this script: python run_backup.py

Features:
- Fetches last 2 days (48 hours) of Amazon orders
- Populates Google Sheet with latest 14-column layout
- API rate limiting: 3-second delay after every 10 orders
- No duplicate handling (simple backup function)
"""

import sys
import os
from datetime import datetime

def main():
    print("🎯 AMAZON BACKUP SYNC RUNNER")
    print("=" * 50)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    # Check if google_credentials.json exists
    if not os.path.exists('google_credentials.json'):
        print("❌ Error: google_credentials.json not found!")
        print("💡 Make sure you have the Google service account credentials file")
        return
    
    print("✅ google_credentials.json found")
    
    try:
        # Import and run the backup
        from backup_column_file_fixed import main as backup_main
        
        print("🚀 Starting backup process...")
        backup_main()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure backup_column_file_fixed.py is in the same folder")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("💡 Check your credentials and internet connection")
    
    print(f"\n📅 Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
