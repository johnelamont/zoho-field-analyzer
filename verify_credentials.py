#!/usr/bin/env python3
"""
Verify that config file has been updated with fresh credentials
"""

import yaml
import sys
from pathlib import Path

def check_file_updated(config_path):
    """Check if config file has fresh credentials"""
    
    print("="*70)
    print(f"VERIFYING: {config_path}")
    print("="*70)
    print()
    
    if not Path(config_path).exists():
        print(f"❌ File not found: {config_path}")
        print()
        print("Make sure you're running from the project root directory")
        print("and that the file exists in config/")
        return False
    
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return False
    
    creds = config.get('zoho_credentials', {})
    
    # Show first 100 chars of cookie
    cookie = creds.get('cookie', '')
    print("Cookie (first 100 chars):")
    print(f"  {cookie[:100]}...")
    print()
    
    # Parse cookies
    cookies = {}
    for c in cookie.split('; '):
        if '=' in c:
            name, value = c.split('=', 1)
            cookies[name] = value
    
    # Check for old timestamp indicators
    print("Checking cookie age...")
    
    # Look for timestamp cookies
    old_timestamps = ['1768382243812', '1769693652817']
    found_old = False
    
    for ts in old_timestamps:
        if ts in cookie:
            print(f"  ❌ Found old timestamp: {ts}")
            print(f"     This is from January 2026!")
            found_old = True
    
    if found_old:
        print()
        print("="*70)
        print("❌ FILE WAS NOT UPDATED!")
        print("="*70)
        print()
        print("Your lamont.yaml still contains OLD credentials from January.")
        print()
        print("You need to:")
        print("1. Actually REPLACE the cookie value in the file")
        print("2. Not just copy - DELETE the old value first")
        print("3. Paste the NEW cookie you just captured")
        print("4. SAVE the file (Ctrl+S)")
        print()
        print("The file should be at: config/lamont.yaml")
        print()
        return False
    
    # Check for very fresh indicators
    import time
    current_time = int(time.time() * 1000)
    found_recent = False
    
    for name in cookies.keys():
        try:
            if len(name) == 13 and name.isdigit():
                timestamp = int(name)
                age_minutes = (current_time - timestamp) / 1000 / 60
                
                if age_minutes < 60:
                    print(f"  ✓ Found recent timestamp: {name}")
                    print(f"    Age: {age_minutes:.1f} minutes")
                    found_recent = True
        except:
            pass
    
    if not found_recent:
        print("  ⚠ No recent timestamp cookies found")
        print("    Cannot definitively verify age")
    
    print()
    
    # Check for critical cookies
    print("Critical cookies check:")
    critical = ['JSESSIONID', 'CSRF_TOKEN', 'ZW_CSRF_TOKEN', 'drecn']
    all_present = True
    
    for cookie_name in critical:
        if cookie_name in cookies:
            # Show last 10 chars to verify it's different
            value_preview = cookies[cookie_name][-10:] if len(cookies[cookie_name]) > 10 else cookies[cookie_name]
            print(f"  ✓ {cookie_name} (...{value_preview})")
        else:
            print(f"  ✗ {cookie_name} - MISSING")
            all_present = False
    
    print()
    
    # Check other fields
    print("Other credentials:")
    
    csrf = creds.get('csrf_token', '')
    if csrf:
        print(f"  ✓ csrf_token: {csrf[:30]}...")
    else:
        print(f"  ✗ csrf_token: MISSING")
    
    org = creds.get('org_id', '')
    if org:
        print(f"  ✓ org_id: {org}")
    else:
        print(f"  ✗ org_id: MISSING")
    
    # Check for typo
    if 'statis_token' in creds:
        print(f"  ❌ statis_token: {creds['statis_token']} (TYPO!)")
        print(f"     Should be 'static_token' not 'statis_token'")
    elif 'static_token' in creds:
        print(f"  ✓ static_token: {creds['static_token']}")
    else:
        print(f"  ✗ static_token: MISSING")
    
    print()
    print("="*70)
    
    if found_old:
        print("RESULT: ❌ OLD CREDENTIALS - File not updated")
        print()
        print("Next steps:")
        print("1. Open config/lamont.yaml in your text editor")
        print("2. DELETE the entire cookie line")
        print("3. Type: cookie: 'PASTE_HERE'")
        print("4. Paste the NEW cookie you captured from DevTools")
        print("5. Save the file")
        print("6. Run this script again to verify")
        return False
    elif all_present and found_recent:
        print("RESULT: ✅ LOOKS GOOD!")
        print()
        print("Your credentials appear to be fresh.")
        print()
        print("Next step: Test immediately")
        print("  python quick_test_mrtarget.py")
        return True
    else:
        print("RESULT: ⚠️ UNCERTAIN")
        print()
        print("Credentials may be updated but cannot verify.")
        print("Try testing anyway:")
        print("  python quick_test_mrtarget.py")
        return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python verify_credentials.py <config_file>")
        print()
        print("Example:")
        print("  python verify_credentials.py config/lamont.yaml")
        sys.exit(1)
    
    config_file = sys.argv[1]
    result = check_file_updated(config_file)
    
    sys.exit(0 if result else 1)
