#!/usr/bin/env python3
"""
Quick diagnostic: test functions API with two approaches
1. Through ZohoAPIClient session (your current flow)
2. Direct requests matching pull_scripts.py exactly

Run from project root:
  python diag_functions.py config/blades.yaml
"""
import sys
import yaml
import requests
from pathlib import Path

BASE_URL = 'https://crm.zoho.com/crm/v2'


def test_via_session(config):
    """Test using the same session approach as your extractors"""
    creds = config['zoho_credentials']
    
    session = requests.Session()
    session.headers.update({
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': 'https://crm.zoho.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'x-crm-org': creds['org_id'],
        'x-requested-with': 'XMLHttpRequest',
        'x-zcsrf-token': creds['csrf_token'],
        'Cookie': creds['cookie'],
    })
    
    # NOTE: intentionally NOT sending x-static-version
    
    url = f"{BASE_URL}/settings/functions"
    params = {'type': 'org', 'start': 1, 'limit': 5}
    
    print("TEST 1: Session approach (no x-static-version)")
    print(f"  URL: {url}")
    print(f"  Params: {params}")
    
    resp = session.get(url, params=params)
    print(f"  Status: {resp.status_code}")
    print(f"  Content-Type: {resp.headers.get('Content-Type', '?')}")
    print(f"  Body (first 300): {resp.text[:300]}")
    print()
    
    return resp.status_code


def test_via_session_with_empty_static(config):
    """Test with the empty x-static-version header (current bug)"""
    creds = config['zoho_credentials']
    
    session = requests.Session()
    session.headers.update({
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': 'https://crm.zoho.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'x-crm-org': creds['org_id'],
        'x-requested-with': 'XMLHttpRequest',
        'x-static-version': '',   # <-- THIS is the suspected problem
        'x-zcsrf-token': creds['csrf_token'],
        'Cookie': creds['cookie'],
    })
    
    url = f"{BASE_URL}/settings/functions"
    params = {'type': 'org', 'start': 1, 'limit': 5}
    
    print("TEST 2: Session with EMPTY x-static-version header")
    print(f"  URL: {url}")
    
    resp = session.get(url, params=params)
    print(f"  Status: {resp.status_code}")
    print(f"  Content-Type: {resp.headers.get('Content-Type', '?')}")
    print(f"  Body (first 300): {resp.text[:300]}")
    print()
    
    return resp.status_code


def test_direct_requests(config):
    """Test with exact pull_scripts.py approach — minimal headers"""
    creds = config['zoho_credentials']
    
    headers = {
        'Cookie': creds['cookie'],
        'x-zcsrf-token': creds['csrf_token'],
        'x-crm-org': creds['org_id'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'x-requested-with': 'XMLHttpRequest, XMLHttpRequest'
    }
    
    url = f"{BASE_URL}/settings/functions?type=org&start=1&limit=5"
    
    print("TEST 3: Direct requests (pull_scripts.py style)")
    print(f"  URL: {url}")
    
    resp = requests.get(url, headers=headers)
    print(f"  Status: {resp.status_code}")
    print(f"  Content-Type: {resp.headers.get('Content-Type', '?')}")
    print(f"  Body (first 300): {resp.text[:300]}")
    print()
    
    return resp.status_code


def main():
    if len(sys.argv) < 2:
        print("Usage: python diag_functions.py config/blades.yaml")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    if not Path(config_path).exists():
        print(f"File not found: {config_path}")
        sys.exit(1)
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    creds = config.get('zoho_credentials', {})
    print("=" * 60)
    print("FUNCTIONS API DIAGNOSTIC")
    print("=" * 60)
    print(f"Org ID: {creds.get('org_id')}")
    print(f"CSRF prefix: {creds.get('csrf_token', '')[:20]}...")
    print(f"Cookie length: {len(creds.get('cookie', ''))} chars")
    print()
    
    # Check csrf_token has required prefix
    csrf = creds.get('csrf_token', '')
    if not csrf.startswith('crmcsrfparam='):
        print("⚠️  csrf_token does NOT start with 'crmcsrfparam='")
        print(f"   Got: {csrf[:30]}...")
        print("   Expected: crmcsrfparam=...")
        print()
    
    results = {}
    
    results['no_static'] = test_via_session(config)
    results['empty_static'] = test_via_session_with_empty_static(config)
    results['direct'] = test_direct_requests(config)
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for label, status in results.items():
        icon = "✅" if status == 200 else "❌"
        print(f"  {icon} {label}: {status}")
    
    print()
    
    if all(s != 200 for s in results.values()):
        print("ALL FAILED → Credentials are expired. Refresh from DevTools.")
    elif results['no_static'] == 200 and results['empty_static'] != 200:
        print("DIAGNOSIS: Empty x-static-version header causes the 400.")
        print("FIX: Remove line 61 in zoho_client.py or use conditional:")
        print("  if static_token:")
        print("      headers['x-static-version'] = static_token")
    elif results['direct'] == 200 and results['no_static'] != 200:
        print("DIAGNOSIS: Extra session headers causing issue.")
        print("FIX: Strip session headers down to match pull_scripts.py")
    elif all(s == 200 for s in results.values()):
        print("ALL PASSED → Credentials work. Issue may be elsewhere.")
    else:
        print("MIXED RESULTS — check individual test output above.")


if __name__ == '__main__':
    main()
