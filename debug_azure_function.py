"""
AZURE FUNCTION DEBUGGING SCRIPT
==============================
This script helps debug why your Azure Function isn't working.
Use this to test your setup step by step.
"""

import os
import logging
from datetime import datetime

def test_environment_variables():
    """Test if all required environment variables are set"""
    print("🔍 Testing Environment Variables...")
    
    required_vars = {
        'AMAZON_REFRESH_TOKEN': 'Amazon API refresh token',
        'AMAZON_LWA_APP_ID': 'Amazon LWA application ID',
        'AMAZON_LWA_CLIENT_SECRET': 'Amazon LWA client secret',
        'GOOGLE_SHEET_URL': 'Google Sheets URL (optional, has default)'
    }
    
    missing_vars = []
    present_vars = []
    
    for var_name, description in required_vars.items():
        value = os.environ.get(var_name)
        if value:
            present_vars.append(var_name)
            print(f"✅ {var_name}: {'*' * min(len(value), 20)}... (length: {len(value)})")
        else:
            missing_vars.append(var_name)
            print(f"❌ {var_name}: NOT SET - {description}")
    
    return len(missing_vars) == 0

def test_sleep_time():
    """Test if the function is currently in sleep time"""
    print("\n🕒 Testing Sleep Time Logic...")
    
    now = datetime.now()
    sleep_start = now.replace(hour=0, minute=30, second=0, microsecond=0)
    sleep_end = now.replace(hour=5, minute=30, second=0, microsecond=0)
    
    is_sleeping = sleep_start <= now <= sleep_end
    
    print(f"Current time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sleep window: {sleep_start.strftime('%H:%M')} - {sleep_end.strftime('%H:%M')}")
    
    if is_sleeping:
        print("😴 Currently in SLEEP TIME - Function will not execute")
        return False
    else:
        print("✅ Currently ACTIVE TIME - Function should execute")
        return True

def test_google_credentials():
    """Test if Google credentials file exists"""
    print("\n📄 Testing Google Credentials...")
    
    cred_file = 'google_credentials.json'
    if os.path.exists(cred_file):
        print(f"✅ {cred_file} exists")
        try:
            import json
            with open(cred_file, 'r') as f:
                creds = json.load(f)
            
            required_keys = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_keys = [key for key in required_keys if key not in creds]
            
            if missing_keys:
                print(f"❌ Missing keys in credentials: {missing_keys}")
                return False
            else:
                print("✅ Google credentials file has all required keys")
                return True
                
        except json.JSONDecodeError:
            print("❌ Google credentials file is not valid JSON")
            return False
    else:
        print(f"❌ {cred_file} NOT FOUND")
        return False

def test_azure_function_entry():
    """Test the Azure Function entry point"""
    print("\n🔧 Testing Azure Function Entry Point...")
    
    try:
        # Import our main function
        from custom_column_sync import azure_timer_handler
        print("✅ azure_timer_handler function imported successfully")
        
        # Test function signature
        import inspect
        sig = inspect.signature(azure_timer_handler)
        params = list(sig.parameters.keys())
        
        if len(params) == 1:
            print(f"✅ Function has correct parameter: {params[0]}")
            return True
        else:
            print(f"❌ Function has wrong number of parameters: {params}")
            print("Should have exactly 1 parameter (mytimer)")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import azure_timer_handler: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing function: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print("🚀 AZURE FUNCTION DIAGNOSTIC TEST")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Sleep Time Logic", test_sleep_time),
        ("Google Credentials", test_google_credentials),
        ("Azure Function Entry", test_azure_function_entry)
    ]
    
    all_passed = True
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
            all_passed = False
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
    
    if all_passed:
        print("\n🎉 All tests passed! Your function should work.")
        print("💡 If it's still not running, check:")
        print("   - Azure Function App is deployed")
        print("   - Environment variables are set in Azure Portal")
        print("   - Check Azure Function logs for errors")
    else:
        print("\n⚠️ Some tests failed. Fix these issues:")
        failed_tests = [name for name, passed in results if not passed]
        for test_name in failed_tests:
            print(f"   - {test_name}")

if __name__ == "__main__":
    main()
