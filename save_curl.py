#!/usr/bin/env python3
"""
Parse curl.txt -> save ALL headers -> test -> extract.

The problem: Zoho requires more headers than just cookie/csrf/org.
Solution: Save every header from the working cURL and replay them all.

Usage:
  1. Copy as cURL from DevTools, paste into curl.txt
  2. python save_curl.py blades
"""
import re
import sys
import subprocess
import json
from pathlib import Path


def parse_curl(text):
    """Parse cURL command, extract URL, all headers, and cookie."""
    # Normalize line continuations
    text = text.replace('\\\r\n', ' ').replace('\\\n', ' ')
    text = ' '.join(text.split())
    
    result = {'headers': {}, 'cookie': None, 'url': None}
    
    # Extract URL
    m = re.search(r"curl\s+'([^']+)'", text)
    if not m:
        m = re.search(r'curl\s+"([^"]+)"', text)
    if m:
        result['url'] = m.group(1)
    
    # Extract -b cookie
    m = re.search(r"-b\s+'([^']+)'", text)
    if not m:
        m = re.search(r'-b\s+"([^"]+)"', text)
    if m:
        result['cookie'] = m.group(1)
    
    # Extract all -H headers
    for m in re.finditer(r"-H\s+'([^']+)'", text):
        hdr = m.group(1)
        if ':' in hdr:
            name, value = hdr.split(':', 1)
            result['headers'][name.strip()] = value.strip()
    
    # Also check for Cookie in -H headers
    if not result['cookie']:
        for name, value in result['headers'].items():
            if name.lower() == 'cookie':
                result['cookie'] = value
                break
    
    return result


def build_ps1_cmd(url, cookie, headers):
    """Build a PowerShell curl.exe command string."""
    parts = ['curl.exe -s']
    
    # URL
    safe_url = url.replace('`', '``')
    parts.append(f'"{safe_url}"')
    
    # Cookie via -b
    safe_cookie = cookie.replace('`', '``').replace('"', '`"')
    parts.append(f'-b "{safe_cookie}"')
    
    # All headers
    for name, value in headers.items():
        # Skip cookie header if we're using -b
        if name.lower() == 'cookie':
            continue
        safe_val = value.replace('`', '``').replace('"', '`"')
        parts.append(f'-H "{name}: {safe_val}"')
    
    return ' '.join(parts)


def run_ps1(cmd):
    """Write PS1 and execute it."""
    ps1_path = Path('_tmp_test.ps1')
    ps1_path.write_text(cmd, encoding='utf-8')
    
    try:
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-File', str(ps1_path)],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip()
    finally:
        ps1_path.unlink(missing_ok=True)


def main():
    client = sys.argv[1] if len(sys.argv) > 1 else 'blades'
    curl_file = sys.argv[2] if len(sys.argv) > 2 else 'curl.txt'
    
    if not Path(curl_file).exists():
        print(f"Missing: {curl_file}")
        sys.exit(1)
    
    text = Path(curl_file).read_text(encoding='utf-8')
    parsed = parse_curl(text)
    
    cookie = parsed['cookie']
    headers = parsed['headers']
    url = parsed['url']
    
    if not cookie:
        print("No cookie found in cURL")
        sys.exit(1)
    
    print(f"URL: {url}")
    print(f"Cookie: {len(cookie)} chars")
    print(f"Headers: {len(headers)}")
    for name in headers:
        print(f"  {name}")
    print()
    
    # Test 1: Full headers, original URL
    print("TEST 1: Full headers, original URL...", end=' ')
    cmd1 = build_ps1_cmd(url, cookie, headers)
    resp1 = run_ps1(cmd1)
    ok1 = resp1 and ('error' not in resp1.lower() or 'functions' in resp1.lower())
    # Better check: not an error response
    is_json1 = False
    try:
        j = json.loads(resp1)
        is_json1 = True
        ok1 = j.get('code') != 'INVALID_REQUEST' and j.get('code') != 'AUTHENTICATION_FAILURE'
    except:
        ok1 = bool(resp1) and 'error' not in resp1[:50].lower()
    print(f"{'PASS' if ok1 else 'FAIL'}: {resp1[:100]}")
    
    # Test 2: Full headers, functions endpoint (auto-detect product)
    if url and 'recruit.zoho.com' in url:
        test_url = 'https://recruit.zoho.com/recruit/v2/settings/functions?type=org&start=1&limit=2'
        product = 'recruit'
    elif url and 'flow.zoho.com' in url:
        test_url = 'https://flow.zoho.com/rest/flow-deluge-functions/'
        product = 'flow'
    else:
        test_url = 'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=2'
        product = 'crm'
    print(f"TEST 2: Full headers, {product} functions endpoint...", end=' ')
    cmd2 = build_ps1_cmd(test_url, cookie, headers)
    resp2 = run_ps1(cmd2)
    try:
        j2 = json.loads(resp2)
        # Flow uses 'user_functions', CRM/Recruit use 'functions'
        if product == 'flow':
            ok2 = 'user_functions' in j2
            count = len(j2.get('user_functions', []))
        else:
            ok2 = 'functions' in j2
            count = len(j2.get('functions', []))
        print(f"{'PASS' if ok2 else 'FAIL'}: {resp2[:100]}")
        if ok2:
            print(f"  Got {count} functions")
    except:
        ok2 = False
        print(f"FAIL: {resp2[:100]}")
    
    # Test 3: Minimal headers (just auth), functions endpoint
    minimal_headers = {}
    if product == 'flow':
        # Flow uses scope header instead of x-crm-org/x-zcsrf-token
        minimal_keys = ('scope', 'x-requested-with')
    else:
        minimal_keys = ('x-zcsrf-token', 'x-crm-org', 'x-requested-with')
    for name, value in headers.items():
        if name.lower() in minimal_keys:
            minimal_headers[name] = value
    
    print("TEST 3: Minimal headers, functions endpoint...", end=' ')
    cmd3 = build_ps1_cmd(test_url, cookie, minimal_headers)
    resp3 = run_ps1(cmd3)
    try:
        j3 = json.loads(resp3)
        if product == 'flow':
            ok3 = 'user_functions' in j3
        else:
            ok3 = 'functions' in j3
        print(f"{'PASS' if ok3 else 'FAIL'}: {resp3[:100]}")
    except:
        ok3 = False
        print(f"FAIL: {resp3[:100]}")
    
    print()
    
    if not ok1 and not ok2:
        print("FAIL: All tests failed. Credentials expired. Try again faster.")
        sys.exit(1)
    
    # Find which headers matter
    if ok2 and not ok3:
        print("Full headers work, minimal don't. Finding required headers...")
        print()
        
        # Try adding headers one at a time to minimal
        extra_headers = {k: v for k, v in headers.items() 
                        if k.lower() not in ('x-zcsrf-token', 'x-crm-org', 'x-requested-with', 'cookie')}
        
        for name, value in extra_headers.items():
            test_headers = {**minimal_headers, name: value}
            cmd_test = build_ps1_cmd(test_url, cookie, test_headers)
            resp_test = run_ps1(cmd_test)
            try:
                j = json.loads(resp_test)
                works = 'functions' in j
            except:
                works = False
            
            print(f"  + {name}: {'PASS' if works else 'fail'}")
            
            if works:
                print(f"\n  >>> '{name}' is the missing required header!")
                print(f"  >>> Value: {value}")
                # Save this header to config
                break
    
    # Save credentials
    if ok1 or ok2:
        d = Path('config') / client
        d.mkdir(parents=True, exist_ok=True)
        
        # Save cookie
        (d / 'cookie.txt').write_text(cookie, encoding='utf-8')
        
        # Save individual auth values
        csrf = headers.get('x-zcsrf-token', '')
        org = headers.get('x-crm-org', '')
        static = headers.get('x-static-version', '')
        
        (d / 'csrf_token.txt').write_text(csrf, encoding='utf-8')
        (d / 'org_id.txt').write_text(org, encoding='utf-8')
        if static:
            (d / 'static_token.txt').write_text(static, encoding='utf-8')
        
        # Save ALL headers as JSON (so zoho_client can replay them)
        (d / 'headers.json').write_text(
            json.dumps(headers, indent=2), encoding='utf-8'
        )
        
        print(f"\nSaved to config/{client}/")
        print(f"  cookie.txt: {len(cookie)} chars")
        print(f"  csrf_token.txt: {len(csrf)} chars")
        print(f"  org_id.txt: {len(org)} chars")
        print(f"  headers.json: {len(headers)} headers")
        if static:
            print(f"  static_token.txt: {static}")
        
        extract_type = {'recruit': 'recruit_functions', 'flow': 'flow_functions'}.get(product, 'functions')
        print(f"\nNow run: python -m src.extractors.main --client {client} --extract {extract_type}")


if __name__ == '__main__':
    main()
