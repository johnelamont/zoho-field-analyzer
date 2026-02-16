#!/usr/bin/env python3
"""
Blueprint Authentication Diagnostic Tool

This script helps diagnose why blueprint extraction works for one client (blades) 
but not another (mrtarget). It tests the authentication and helps identify missing headers.
"""

import yaml
import requests
import json
from pathlib import Path

def load_config(client_name):
    """Load client configuration"""
    config_path = Path(f'config/{client_name}.yaml')
    if not config_path.exists():
        # Try uploaded path
        config_path = Path(f'/mnt/user-data/uploads/{client_name}.yaml')
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def parse_cookies(cookie_string):
    """Parse cookie string into individual cookies"""
    cookies = {}
    for cookie in cookie_string.split('; '):
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            cookies[name] = value
    return cookies

def create_session(config):
    """Create a requests session with proper authentication"""
    creds = config['zoho_credentials']
    session = requests.Session()
    
    # Parse and set cookies
    cookie_dict = parse_cookies(creds['cookie'])
    for name, value in cookie_dict.items():
        session.cookies.set(name, value, domain='.zoho.com')
    
    # Build headers
    headers = {
        'x-zcsrf-token': creds['csrf_token'],
        'x-crm-org': creds['org_id'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'X-Requested-With': 'XMLHttpRequest, XMLHttpRequest'
    }
    
    # Add static token if present (this is the key difference!)
    if 'static_token' in creds:
        headers['X-Static-Token'] = creds['static_token']
        print(f"✓ Added X-Static-Token: {creds['static_token']}")
    else:
        print("⚠ No static_token found in config")
    
    session.headers.update(headers)
    
    return session

def test_blueprint_endpoint(client_name):
    """Test blueprint endpoint for a client"""
    print(f"\n{'='*60}")
    print(f"Testing {client_name.upper()}")
    print('='*60)
    
    config = load_config(client_name)
    org_id = config['zoho_credentials']['org_id']
    
    session = create_session(config)
    
    # Show what cookies we're sending
    print(f"Cookies set: {len(session.cookies)}")
    print(f"Headers: {list(session.headers.keys())}")
    
    # Test the blueprint endpoint
    url = f"https://crm.zoho.com/crm/org{org_id}/ProcessFlow.do"
    params = {
        'pageTitle': 'crm.label.process.automation',
        'allowMultiClick': 'true',
        'action': 'showAllProcesses',
        'isFromBack': 'true',
        'module': 'All'
    }
    
    print(f"\nRequesting: {url}")
    print(f"Params: {params}")
    
    try:
        response = session.get(url, params=params, timeout=10)
        
        print(f"\n{'='*60}")
        print("RESPONSE")
        print('='*60)
        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"Response Size: {len(response.text)} bytes")
        
        # Check if we got JSON or HTML
        content_type = response.headers.get('Content-Type', '')
        
        if 'json' in content_type.lower():
            print("\n✓ SUCCESS! Got JSON response")
            try:
                data = response.json()
                blueprints = data.get('Processes', [])
                print(f"✓ Found {len(blueprints)} blueprints")
                
                if blueprints:
                    print("\nFirst 3 blueprints:")
                    for i, bp in enumerate(blueprints[:3], 1):
                        print(f"  {i}. {bp.get('Name', 'Unknown')} (ID: {bp.get('Id')})")
                
                return True
            except json.JSONDecodeError as e:
                print(f"✗ JSON parsing failed: {e}")
                return False
        
        elif 'html' in content_type.lower():
            print("\n✗ FAILED! Got HTML instead of JSON")
            print("\nThis usually means:")
            print("  1. Credentials expired/invalid")
            print("  2. Missing required authentication header")
            print("  3. Session not properly authenticated")
            
            # Show response preview
            print(f"\nResponse preview (first 500 chars):")
            print("-" * 60)
            print(response.text[:500])
            print("-" * 60)
            
            # Check for common HTML indicators
            lower_text = response.text.lower()
            if 'login' in lower_text or 'signin' in lower_text:
                print("\n⚠ Response contains 'login' - credentials likely expired")
            if 'error' in lower_text:
                print("\n⚠ Response contains 'error' text")
            
            return False
        
        else:
            print(f"\n⚠ Unexpected content type: {content_type}")
            print(f"Response preview: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"\n✗ Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

def compare_configs(client1, client2):
    """Compare two client configurations to identify differences"""
    print(f"\n{'='*60}")
    print(f"COMPARING {client1.upper()} vs {client2.upper()}")
    print('='*60)
    
    config1 = load_config(client1)
    config2 = load_config(client2)
    
    creds1 = config1['zoho_credentials']
    creds2 = config2['zoho_credentials']
    
    # Check for key differences
    print("\nCredential fields comparison:")
    all_keys = set(creds1.keys()) | set(creds2.keys())
    
    for key in sorted(all_keys):
        in_1 = key in creds1
        in_2 = key in creds2
        
        if in_1 and in_2:
            print(f"  ✓ {key}: Both have this field")
        elif in_1 and not in_2:
            print(f"  ⚠ {key}: Only {client1} has this field")
        elif in_2 and not in_1:
            print(f"  ⚠ {key}: Only {client2} has this field ← THIS IS THE ISSUE!")
    
    # Check rate limiting settings
    if 'rate_limiting' in config1 and 'rate_limiting' in config2:
        print("\nRate limiting settings:")
        print(f"  {client1}: {config1['rate_limiting']}")
        print(f"  {client2}: {config2['rate_limiting']}")

def main():
    """Run all diagnostics"""
    print("ZOHO BLUEPRINT AUTHENTICATION DIAGNOSTICS")
    print("=" * 60)
    
    # Test both clients
    blades_works = test_blueprint_endpoint('blades')
    mrtarget_works = test_blueprint_endpoint('lamont')
    
    # Compare configurations
    compare_configs('blades', 'mrtarget')
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"blades: {'✓ WORKING' if blades_works else '✗ FAILED'}")
    print(f"mrtarget: {'✓ WORKING' if mrtarget_works else '✗ FAILED'}")
    
    if not mrtarget_works and blades_works:
        print("\n" + "="*60)
        print("DIAGNOSIS & FIX")
        print("="*60)
        print("\nThe issue is likely:")
        print("1. Missing X-Static-Token header in mrtarget requests")
        print("2. Or expired/invalid credentials in mrtarget.yaml")
        print("\nTo fix:")
        print("1. If blades.yaml is missing static_token, get it from browser")
        print("2. Update your zoho_client.py to include X-Static-Token header:")
        print("   session.headers['X-Static-Token'] = creds.get('static_token', '')")
        print("3. Or refresh your mrtarget.yaml credentials from browser")

if __name__ == '__main__':
    main()
