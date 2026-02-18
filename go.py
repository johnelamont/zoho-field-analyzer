#!/usr/bin/env python3
"""
All-in-one credential refresh: parse cURL → test → save.

1. Copy as cURL (bash) from Chrome DevTools
2. Paste into curl.txt (notepad curl.txt, paste, Ctrl+S, close)
3. Immediately run: python go.py blades

Does everything in one shot — no intermediate steps.
"""
import re
import sys
import subprocess
from pathlib import Path


def parse_curl(text):
    """Extract credentials from cURL command"""
    creds = {}
    
    # Cookie via -b flag
    m = re.search(r"-b\s+'([^']+)'", text)
    if not m:
        m = re.search(r'-b\s+"([^"]+)"', text)
    if m:
        creds['cookie'] = m.group(1)
    
    # Cookie via -H 'Cookie: ...'
    if 'cookie' not in creds:
        m = re.search(r"-H\s+'[Cc]ookie:\s*([^']+)'", text)
        if not m:
            m = re.search(r'-H\s+"[Cc]ookie:\s*([^"]+)"', text)
        if m:
            creds['cookie'] = m.group(1)
    
    # Other headers
    for match in re.finditer(r"""-H\s+['"]([^'"]+)['"]""", text):
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


def test_with_curl(creds):
    """Test using curl.exe (proven to work)"""
    cmd = [
        'curl.exe', '-s',
        'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=2',
        '-H', f'x-requested-with: XMLHttpRequest',
        '-H', f'x-zcsrf-token: {creds["csrf"]}',
        '-H', f'x-crm-org: {creds["org"]}',
        '-b', creds['cookie'],
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return result.stdout


def save_creds(client, creds):
    """Save to text files"""
    d = Path('config') / client
    d.mkdir(parents=True, exist_ok=True)
    
    mapping = {
        'cookie': 'cookie.txt',
        'csrf': 'csrf_token.txt',
        'org': 'org_id.txt',
        'static': 'static_token.txt',
    }
    
    for key, filename in mapping.items():
        if key in creds:
            (d / filename).write_text(creds[key], encoding='utf-8')


def main():
    if len(sys.argv) < 2:
        print("Usage: python go.py <client_name> [curl_file]")
        print("  python go.py blades              # reads curl.txt")
        print("  python go.py blades mycurl.txt    # reads mycurl.txt")
        sys.exit(1)
    
    client = sys.argv[1]
    curl_file = sys.argv[2] if len(sys.argv) > 2 else 'curl.txt'
    
    # Parse
    if not Path(curl_file).exists():
        print(f"❌ {curl_file} not found")
        print(f"   Paste your cURL into {curl_file} first")
        sys.exit(1)
    
    text = Path(curl_file).read_text(encoding='utf-8')
    creds = parse_curl(text)
    
    if not creds.get('cookie'):
        print("❌ No cookie found in cURL")
        sys.exit(1)
    if not creds.get('csrf'):
        print("❌ No x-zcsrf-token found in cURL")
        sys.exit(1)
    if not creds.get('org'):
        print("❌ No x-crm-org found in cURL")
        sys.exit(1)
    
    print(f"Parsed: cookie={len(creds['cookie'])}ch, csrf={creds['csrf'][:20]}..., org={creds['org']}, static={creds.get('static', 'none')}")
    
    # Test immediately with curl.exe (proven to work)
    print("Testing...", end=' ')
    response = test_with_curl(creds)
    
    if '"functions"' in response:
        print("✅ WORKS!")
        save_creds(client, creds)
        print(f"Saved to config/{client}/")
        print(f"Now run: python -m src.extractors.main --client {client} --extract functions")
    elif 'INVALID_REQUEST' in response:
        print("❌ 400 — credentials expired. Be faster!")
        print("   Copy cURL → paste into curl.txt → run go.py within 30 seconds")
    else:
        print(f"❌ Unexpected: {response[:200]}")


if __name__ == '__main__':
    main()
