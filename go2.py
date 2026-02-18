#!/usr/bin/env python3
"""
Debug: show what's parsed, then try both parsed curl and raw curl.
Usage: python go2.py blades
"""
import re
import sys
import subprocess
from pathlib import Path


def main():
    client = sys.argv[1] if len(sys.argv) > 1 else 'blades'
    curl_file = sys.argv[2] if len(sys.argv) > 2 else 'curl.txt'
    
    text = Path(curl_file).read_text(encoding='utf-8')
    
    print(f"curl.txt: {len(text)} chars")
    print(f"First 50: {repr(text[:50])}")
    print()
    
    # --- Parse cookie ---
    cookie = None
    
    # Try -b 'value'
    m = re.search(r"-b\s+'([^']+)'", text)
    if m:
        cookie = m.group(1)
        print(f"Cookie source: -b flag (single quotes)")
    
    if not cookie:
        m = re.search(r'-b\s+"([^"]+)"', text)
        if m:
            cookie = m.group(1)
            print(f"Cookie source: -b flag (double quotes)")
    
    if not cookie:
        m = re.search(r"-H\s+'[Cc]ookie:\s*([^']+)'", text)
        if m:
            cookie = m.group(1)
            print(f"Cookie source: -H Cookie header")
    
    if cookie:
        print(f"Cookie length: {len(cookie)}")
        print(f"Cookie start:  {cookie[:60]}...")
        print(f"Cookie end:    ...{cookie[-60:]}")
    else:
        print("❌ NO COOKIE FOUND")
    
    # --- Parse other headers ---
    csrf = None
    org = None
    static = None
    
    for match in re.finditer(r"""-H\s+'([^']+)'""", text):
        hdr = match.group(1)
        if ':' not in hdr:
            continue
        name, value = hdr.split(':', 1)
        name = name.strip().lower()
        value = value.strip()
        
        if name == 'x-zcsrf-token':
            csrf = value
        elif name == 'x-crm-org':
            org = value
        elif name == 'x-static-version' and value:
            static = value
    
    print(f"CSRF:   {csrf[:40] if csrf else 'NOT FOUND'}...")
    print(f"Org:    {org or 'NOT FOUND'}")
    print(f"Static: {static or 'not found'}")
    print()
    
    if not all([cookie, csrf, org]):
        print("❌ Missing credentials. Check curl.txt format.")
        sys.exit(1)
    
    # --- TEST A: Parsed credentials via curl.exe ---
    print("TEST A: Parsed credentials → curl.exe")
    cmd_a = [
        'curl.exe', '-s',
        'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=2',
        '-H', 'x-requested-with: XMLHttpRequest',
        '-H', f'x-zcsrf-token: {csrf}',
        '-H', f'x-crm-org: {org}',
        '-b', cookie,
    ]
    result_a = subprocess.run(cmd_a, capture_output=True, text=True, timeout=15)
    print(f"  Response: {result_a.stdout[:200]}")
    a_ok = '"functions"' in result_a.stdout
    print(f"  {'✅ PASS' if a_ok else '❌ FAIL'}")
    print()
    
    # --- TEST B: Run the ENTIRE cURL command as-is (just swap curl→curl.exe) ---
    print("TEST B: Raw cURL (swap curl→curl.exe, no parsing)")
    # Replace 'curl ' at start with 'curl.exe '
    raw = text.strip()
    if raw.startswith("curl '") or raw.startswith("curl \\"):
        raw = 'curl.exe ' + raw[5:]
    elif raw.startswith("curl'"):
        raw = 'curl.exe' + raw[4:]
    else:
        raw = raw.replace('curl ', 'curl.exe ', 1)
    
    # Run via shell (preserves all quoting)
    result_b = subprocess.run(raw, capture_output=True, text=True, timeout=15, shell=True)
    print(f"  Response: {result_b.stdout[:200]}")
    if result_b.stderr:
        print(f"  Stderr: {result_b.stderr[:200]}")
    b_ok = '"functions"' in result_b.stdout
    print(f"  {'✅ PASS' if b_ok else '❌ FAIL'}")
    print()
    
    # --- Diagnosis ---
    print("=" * 60)
    if a_ok and b_ok:
        print("Both pass — saving credentials")
        d = Path('config') / client
        d.mkdir(parents=True, exist_ok=True)
        (d / 'cookie.txt').write_text(cookie, encoding='utf-8')
        (d / 'csrf_token.txt').write_text(csrf, encoding='utf-8')
        (d / 'org_id.txt').write_text(org, encoding='utf-8')
        if static:
            (d / 'static_token.txt').write_text(static, encoding='utf-8')
        print(f"✅ Saved to config/{client}/")
    elif b_ok and not a_ok:
        print("Raw cURL works but parsed fails → PARSING BUG")
        print("The regex is losing or corrupting something.")
    elif not a_ok and not b_ok:
        print("Both fail → credentials expired")
        print("Be faster: copy cURL, save, run go2.py within 15 seconds")
    elif a_ok and not b_ok:
        print("Parsed works but raw fails → shell quoting issue (harmless)")
        d = Path('config') / client
        d.mkdir(parents=True, exist_ok=True)
        (d / 'cookie.txt').write_text(cookie, encoding='utf-8')
        (d / 'csrf_token.txt').write_text(csrf, encoding='utf-8')
        (d / 'org_id.txt').write_text(org, encoding='utf-8')
        if static:
            (d / 'static_token.txt').write_text(static, encoding='utf-8')
        print(f"✅ Saved to config/{client}/")


if __name__ == '__main__':
    main()
