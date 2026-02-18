#!/usr/bin/env python3
"""
Find what Python requests is doing differently from curl.exe

Tests:
1. Show exactly what requests sends (prepared request inspection)
2. Try http.client (bypasses requests entirely)
3. Try subprocess calling curl.exe (should match manual curl)
"""
import sys
import subprocess
import http.client
import ssl
from pathlib import Path
from urllib.parse import urlparse

BASE_URL = 'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=2'


def load_creds(client_name):
    d = Path('config') / client_name
    return {
        'cookie': (d / 'cookie.txt').read_text(encoding='utf-8').strip(),
        'csrf': (d / 'csrf_token.txt').read_text(encoding='utf-8').strip(),
        'org': (d / 'org_id.txt').read_text(encoding='utf-8').strip(),
    }


def test_inspect_requests(c):
    """Show exactly what requests would send"""
    import requests
    
    print("=" * 60)
    print("TEST 1: Inspect what requests actually sends")
    print("=" * 60)
    
    req = requests.Request('GET', BASE_URL, headers={
        'Cookie': c['cookie'],
        'x-zcsrf-token': c['csrf'],
        'x-crm-org': c['org'],
        'x-requested-with': 'XMLHttpRequest',
    })
    
    prepared = req.prepare()
    
    print(f"URL: {prepared.url}")
    print(f"Method: {prepared.method}")
    print("Headers sent by requests:")
    for k, v in prepared.headers.items():
        if k.lower() == 'cookie':
            print(f"  {k}: ({len(v)} chars) {v[:80]}...{v[-40:]}")
        else:
            print(f"  {k}: {v}")
    
    # Check for differences in cookie
    original = c['cookie']
    sent = prepared.headers.get('Cookie', '')
    if original != sent:
        print()
        print("⚠️  Cookie was MODIFIED by requests!")
        print(f"  Original length: {len(original)}")
        print(f"  Sent length:     {len(sent)}")
        # Find first difference
        for i, (a, b) in enumerate(zip(original, sent)):
            if a != b:
                print(f"  First diff at position {i}:")
                print(f"    Original: ...{original[max(0,i-20):i+20]}...")
                print(f"    Sent:     ...{sent[max(0,i-20):i+20]}...")
                break
    else:
        print()
        print("✅ Cookie sent unchanged")
    
    # Now actually send it
    print()
    resp = requests.get(BASE_URL, headers={
        'Cookie': c['cookie'],
        'x-zcsrf-token': c['csrf'],
        'x-crm-org': c['org'],
        'x-requested-with': 'XMLHttpRequest',
    })
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:200]}")
    print()


def test_http_client(c):
    """Bypass requests entirely — use stdlib http.client"""
    print("=" * 60)
    print("TEST 2: http.client (bypasses requests library)")
    print("=" * 60)
    
    parsed = urlparse(BASE_URL)
    
    context = ssl.create_default_context()
    conn = http.client.HTTPSConnection(parsed.hostname, context=context)
    
    headers = {
        'Cookie': c['cookie'],
        'x-zcsrf-token': c['csrf'],
        'x-crm-org': c['org'],
        'x-requested-with': 'XMLHttpRequest',
    }
    
    path = parsed.path + '?' + parsed.query
    print(f"Host: {parsed.hostname}")
    print(f"Path: {path}")
    print(f"Headers: {list(headers.keys())}")
    
    try:
        conn.request('GET', path, headers=headers)
        resp = conn.getresponse()
        body = resp.read().decode('utf-8')
        
        print(f"Status: {resp.status}")
        print(f"Response: {body[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
    
    print()


def test_curl_subprocess(c):
    """Call curl.exe from Python — should match manual curl"""
    print("=" * 60)
    print("TEST 3: subprocess curl.exe (should match manual)")
    print("=" * 60)
    
    cmd = [
        'curl.exe', '-s',
        BASE_URL,
        '-H', f'x-requested-with: XMLHttpRequest',
        '-H', f'x-zcsrf-token: {c["csrf"]}',
        '-H', f'x-crm-org: {c["org"]}',
        '-b', c['cookie'],
    ]
    
    print(f"Running curl.exe...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        print(f"Exit code: {result.returncode}")
        print(f"Response: {result.stdout[:300]}")
        if result.stderr:
            print(f"Stderr: {result.stderr[:200]}")
    except Exception as e:
        print(f"Error: {e}")
    
    print()


def main():
    client = sys.argv[1] if len(sys.argv) > 1 else 'blades'
    c = load_creds(client)
    
    print(f"Cookie: {len(c['cookie'])} chars")
    print(f"Cookie has quotes: {'Yes' if '\"' in c['cookie'] else 'No'}")
    print()
    
    test_inspect_requests(c)
    test_http_client(c)
    test_curl_subprocess(c)
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("If Test 2 or 3 pass but Test 1 fails:")
    print("  → requests library is corrupting something")
    print("If all fail: credentials expired between capture and test")
    print("If all pass: the issue is in zoho_client.py session setup")


if __name__ == '__main__':
    main()
