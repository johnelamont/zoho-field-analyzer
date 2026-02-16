#!/usr/bin/env python3
"""
Universal Blueprint Test - Works for any client
Tests if blueprint extraction works for a given client config
"""

import yaml
import requests
import sys
from pathlib import Path

def test_client(client_name):
    """Test blueprint extraction for a client"""
    
    config_path = Path(f'config/{client_name}.yaml')
    
    print("="*70)
    print(f"TESTING BLUEPRINT EXTRACTION: {client_name.upper()}")
    print("="*70)
    print()
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False
    
    # Load config
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return False
    
    creds = config['zoho_credentials']
    
    # Create session
    session = requests.Session()
    
    # Parse cookies
    cookie_count = 0
    for cookie in creds['cookie'].split('; '):
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            session.cookies.set(name, value, domain='.zoho.com')
            cookie_count += 1
    
    print(f"✓ Loaded config")
    print(f"✓ Parsed {cookie_count} cookies")
    
    # Set headers
    headers = {
        'x-zcsrf-token': creds['csrf_token'],
        'x-crm-org': creds['org_id'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest, XMLHttpRequest',
    }
    
    # Add static token if present
    if 'static_token' in creds and creds['static_token']:
        headers['X-Static-Token'] = creds['static_token']
        print(f"✓ Added X-Static-Token: {creds['static_token']}")
    else:
        print(f"⚠ No static_token in config")
    
    session.headers.update(headers)
    
    print(f"✓ Set {len(headers)} headers")
    print()
    
    # Make request
    print("Making request to Zoho...")
    org_id = creds['org_id']
    url = f"https://crm.zoho.com/crm/org{org_id}/ProcessFlow.do"
    params = {
        'pageTitle': 'crm.label.process.automation',
        'allowMultiClick': 'true',
        'action': 'showAllProcesses',
        'isFromBack': 'true',
        'module': 'All'
    }
    
    try:
        response = session.get(url, params=params, timeout=15)
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
    print()
    
    # Check response
    content_type = response.headers.get('Content-Type', '').lower()
    
    if 'json' in content_type:
        print("✅ SUCCESS! Got JSON response")
        print()
        
        try:
            data = response.json()
            blueprints = data.get('Processes', [])
            print(f"Found {len(blueprints)} blueprints:")
            print()
            
            if blueprints:
                print("First 5 blueprints:")
                for i, bp in enumerate(blueprints[:5], 1):
                    name = bp.get('Name', 'Unknown')
                    bp_id = bp.get('Id', 'Unknown')
                    module = bp.get('Tab', {}).get('Name', 'Unknown')
                    status = bp.get('ProcessStatus', 'Unknown')
                    print(f"  {i}. {name}")
                    print(f"     Module: {module}, Status: {status}, ID: {bp_id}")
                
                if len(blueprints) > 5:
                    print(f"\n  ... and {len(blueprints) - 5} more")
            else:
                print("⚠ No blueprints found")
            
            print()
            print("="*70)
            print(f"✅ {client_name.upper()} IS WORKING!")
            print("="*70)
            return True
            
        except Exception as e:
            print(f"❌ Failed to parse JSON: {e}")
            return False
    
    elif 'html' in content_type:
        print("❌ FAILED! Got HTML instead of JSON")
        print()
        print("This means credentials are expired or invalid.")
        print()
        
        # Show preview
        text = response.text.lower()
        if 'login' in text or 'sign in' in text:
            print("🔍 Response contains login page")
            print("   → Credentials EXPIRED")
        
        print()
        print("Response preview:")
        print("-"*70)
        print(response.text[:500])
        print("-"*70)
        print()
        print("="*70)
        print(f"❌ {client_name.upper()} FAILED")
        print("="*70)
        print()
        print("To fix:")
        print("1. Get fresh credentials from DevTools")
        print("2. Update config/{}.yaml".format(client_name))
        print("3. Run this test again")
        return False
    
    else:
        print(f"❌ Unexpected content type: {content_type}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_blueprint.py <client_name>")
        print()
        print("Examples:")
        print("  python test_blueprint.py blades")
        print("  python test_blueprint.py mrtarget")
        print("  python test_blueprint.py lamont")
        sys.exit(1)
    
    client_name = sys.argv[1]
    success = test_client(client_name)
    
    sys.exit(0 if success else 1)
