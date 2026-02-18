#!/usr/bin/env python3
"""
go3.py - Fix the quote problem.

The cookie contains literal " chars (ZohoMarkRef="https://...").
These break:
  - Windows subprocess (escapes " to \")
  - requests library (sometimes)
  - YAML (always)

Fix: write cookie to a temp file, use curl -b @file
Also test: does stripping quotes from cookie work?
"""
import re
import sys
import subprocess
import tempfile
from pathlib import Path


def parse_curl(text):
    creds = {}
    
    m = re.search(r"-b\s+'([^']+)'", text)
    if not m:
        m = re.search(r'-b\s+"([^"]+)"', text)
    if m:
        creds['cookie'] = m.group(1)
    
    if 'cookie' not in creds:
        m = re.search(r"-H\s+'[Cc]ookie:\s*([^']+)'", text)
        if m:
            creds['cookie'] = m.group(1)
    
    for match in re.finditer(r"""-H\s+'([^']+)'""", text):
        hdr = match.group(1)
        if ':' not in hdr:
            continue
        name, value = hdr.split(':', 1)
        name = name.strip().lower()
        value = value.strip()
        if name == 'x-zcsrf-token':
            creds['csrf'] = value
        elif name == 'x-crm-org':
            creds['org'] = value
        elif name == 'x-static-version' and value:
            creds['static'] = value
    
    return creds


def test_curl_via_file(cookie, csrf, org, label=""):
    """Write cookie to temp file, pass to curl -b @file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(cookie)
        tmppath = f.name
    
    try:
        cmd = [
            'curl.exe', '-s',
            'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=2',
            '-H', 'x-requested-with: XMLHttpRequest',
            '-H', f'x-zcsrf-token: {csrf}',
            '-H', f'x-crm-org: {org}',
            '-H', f'Cookie: @{tmppath}',
        ]
        # Actually, curl's -b with a filename expects Netscape cookie format.
        # For raw cookie header, use -H 'Cookie: ...' via a header file.
        
        # Better approach: use --cookie with the raw string but via a config file
        # Write a curl config file instead
        with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False, encoding='utf-8') as cfg:
            cfg.write(f'header = "Cookie: {cookie}"\n')
            cfg.write(f'header = "x-zcsrf-token: {csrf}"\n')
            cfg.write(f'header = "x-crm-org: {org}"\n')
            cfg.write(f'header = "x-requested-with: XMLHttpRequest"\n')
            cfgpath = cfg.name
        
        cmd2 = [
            'curl.exe', '-s',
            '-K', cfgpath,
            'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=2',
        ]
        
        result = subprocess.run(cmd2, capture_output=True, text=True, timeout=15)
        return result.stdout
    finally:
        Path(tmppath).unlink(missing_ok=True)
        Path(cfgpath).unlink(missing_ok=True)


def main():
    client = sys.argv[1] if len(sys.argv) > 1 else 'blades'
    curl_file = sys.argv[2] if len(sys.argv) > 2 else 'curl.txt'
    
    text = Path(curl_file).read_text(encoding='utf-8')
    creds = parse_curl(text)
    
    cookie = creds.get('cookie', '')
    csrf = creds.get('csrf', '')
    org = creds.get('org', '')
    static = creds.get('static')
    
    if not all([cookie, csrf, org]):
        print("❌ Missing credentials in curl.txt")
        sys.exit(1)
    
    quote_count = cookie.count('"')
    print(f"Cookie: {len(cookie)} chars, {quote_count} embedded quotes")
    print(f"CSRF: {csrf[:30]}...")
    print(f"Org: {org}")
    print()
    
    # TEST 1: Cookie via config file (avoids all quoting)
    print("TEST 1: curl.exe via config file (no quoting issues)...", end=' ')
    resp1 = test_curl_via_file(cookie, csrf, org)
    ok1 = '"functions"' in resp1
    print(f"{'✅ PASS' if ok1 else '❌ FAIL'}")
    if not ok1:
        print(f"  Response: {resp1[:200]}")
    print()
    
    # TEST 2: Same but with quotes stripped from cookie
    clean_cookie = cookie.replace('"', '')
    print(f"TEST 2: curl.exe via config file, quotes stripped...", end=' ')
    resp2 = test_curl_via_file(clean_cookie, csrf, org)
    ok2 = '"functions"' in resp2
    print(f"{'✅ PASS' if ok2 else '❌ FAIL'}")
    if not ok2:
        print(f"  Response: {resp2[:200]}")
    print()
    
    # TEST 3: Strip the problem cookies entirely
    # Remove ZohoMarkRef and ZohoMarkSrc cookies (they have quotes, not needed for auth)
    filtered_parts = []
    for part in cookie.split('; '):
        if 'ZohoMarkRef' in part or 'ZohoMarkSrc' in part:
            continue
        filtered_parts.append(part)
    filtered_cookie = '; '.join(filtered_parts)
    
    print(f"TEST 3: curl.exe, ZohoMark cookies removed...", end=' ')
    resp3 = test_curl_via_file(filtered_cookie, csrf, org)
    ok3 = '"functions"' in resp3
    print(f"{'✅ PASS' if ok3 else '❌ FAIL'}")
    if not ok3:
        print(f"  Response: {resp3[:200]}")
    print()
    
    # Results
    print("=" * 60)
    if ok1 or ok2 or ok3:
        # Pick the working cookie
        if ok3:
            final_cookie = filtered_cookie
            method = "ZohoMark cookies removed"
        elif ok2:
            final_cookie = clean_cookie
            method = "quotes stripped"
        else:
            final_cookie = cookie
            method = "original"
        
        print(f"✅ SUCCESS ({method})")
        d = Path('config') / client
        d.mkdir(parents=True, exist_ok=True)
        (d / 'cookie.txt').write_text(final_cookie, encoding='utf-8')
        (d / 'csrf_token.txt').write_text(csrf, encoding='utf-8')
        (d / 'org_id.txt').write_text(org, encoding='utf-8')
        if static:
            (d / 'static_token.txt').write_text(static, encoding='utf-8')
        print(f"Saved to config/{client}/")
        print(f"Now run: python -m src.extractors.main --client {client} --extract functions")
    else:
        print("❌ All tests failed")
        print()
        print("This means either:")
        print("  1. Credentials expired (most likely — try being faster)")
        print("  2. Something else is wrong with the cookie format")
        print()
        print("Debug: check if your manual curl.exe STILL works.")
        print("If manual curl.exe also fails now, creds are expired.")


if __name__ == '__main__':
    main()
