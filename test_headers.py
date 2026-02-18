#!/usr/bin/env python3
"""
Test what's different between working curl.exe and failing Python requests.
Tries multiple header combinations to find the culprit.

Usage: python test_headers.py blades
"""
import sys
import requests
from pathlib import Path

BASE_URL = 'https://crm.zoho.com/crm/v2/settings/functions'
PARAMS = '?type=org&start=1&limit=2'


def load_creds(client_name):
    d = Path('config') / client_name
    return {
        'cookie': (d / 'cookie.txt').read_text(encoding='utf-8').strip(),
        'csrf': (d / 'csrf_token.txt').read_text(encoding='utf-8').strip(),
        'org': (d / 'org_id.txt').read_text(encoding='utf-8').strip(),
        'static': (d / 'static_token.txt').read_text(encoding='utf-8').strip() if (d / 'static_token.txt').exists() else None,
    }


def test(label, headers):
    """Run a single test"""
    print(f"  {label}...", end=' ')
    try:
        resp = requests.get(BASE_URL + PARAMS, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            n = len(data.get('functions', []))
            print(f"✅ OK ({n} functions)")
            return True
        else:
            print(f"❌ {resp.status_code}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False


def main():
    client = sys.argv[1] if len(sys.argv) > 1 else 'blades'
    c = load_creds(client)
    
    print(f"Cookie: {len(c['cookie'])} chars")
    print(f"CSRF: {c['csrf'][:30]}...")
    print(f"Org: {c['org']}")
    print(f"Static: {c['static']}")
    print()
    
    # Test 1: Exact match to working cURL (minimal headers)
    test("Minimal (just auth)", {
        'Cookie': c['cookie'],
        'x-zcsrf-token': c['csrf'],
        'x-crm-org': c['org'],
        'x-requested-with': 'XMLHttpRequest',
    })
    
    # Test 2: Add isfrom header (present in the working cURL)
    test("+ isfrom: function", {
        'Cookie': c['cookie'],
        'x-zcsrf-token': c['csrf'],
        'x-crm-org': c['org'],
        'x-requested-with': 'XMLHttpRequest',
        'isfrom': 'function',
    })
    
    # Test 3: Add static version
    test("+ x-static-version", {
        'Cookie': c['cookie'],
        'x-zcsrf-token': c['csrf'],
        'x-crm-org': c['org'],
        'x-requested-with': 'XMLHttpRequest',
        'isfrom': 'function',
        'x-static-version': c['static'] or '',
    })

    # Test 4: What refresh_creds.py currently sends (the failing one)
    test("Current refresh_creds.py headers", {
        'Cookie': c['cookie'],
        'x-zcsrf-token': c['csrf'],
        'x-crm-org': c['org'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'x-requested-with': 'XMLHttpRequest, XMLHttpRequest',
    })
    
    # Test 5: Check if content-type is the problem
    test("Minimal + content-type", {
        'Cookie': c['cookie'],
        'x-zcsrf-token': c['csrf'],
        'x-crm-org': c['org'],
        'x-requested-with': 'XMLHttpRequest',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
    })
    
    # Test 6: Check if doubled x-requested-with is the problem
    test("Minimal + doubled x-requested-with", {
        'Cookie': c['cookie'],
        'x-zcsrf-token': c['csrf'],
        'x-crm-org': c['org'],
        'x-requested-with': 'XMLHttpRequest, XMLHttpRequest',
    })


if __name__ == '__main__':
    main()
