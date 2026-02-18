#!/usr/bin/env python3
"""
Diagnose and fix cookie quoting issues in YAML config.

The problem: Zoho cookies can contain literal double-quote characters.
YAML chokes on these regardless of quoting style:
  - Single quotes: 'cookie_with_"quotes"'  → YAML error or silent truncation
  - Double quotes: "cookie_with_\"quotes\"" → escaping issues
  - No quotes: cookie_with_"quotes"         → parse error

The fix: Use YAML block scalar (pipe |) which preserves content literally.

Run:
  python diag_cookie.py config/blades.yaml
"""
import sys
import yaml
import requests
from pathlib import Path

BASE_URL = 'https://crm.zoho.com/crm/v2'


def diagnose(config_path):
    print("=" * 60)
    print("COOKIE DIAGNOSTIC")
    print("=" * 60)
    print()
    
    # Step 1: Read raw file to see what's actually in there
    raw_text = Path(config_path).read_text(encoding='utf-8')
    
    # Find the cookie line(s)
    lines = raw_text.split('\n')
    cookie_lines = []
    in_cookie_block = False
    
    for i, line in enumerate(lines):
        if 'cookie:' in line.lower() and 'cookie_name' not in line.lower():
            cookie_lines.append((i + 1, line))
            # Check if it's a block scalar
            stripped = line.split('cookie:', 1)[1].strip() if 'cookie:' in line else ''
            if stripped in ('|', '|-', '>', '>-'):
                in_cookie_block = True
            continue
        if in_cookie_block:
            if line.startswith('    ') or line.startswith('\t'):
                cookie_lines.append((i + 1, line))
            else:
                in_cookie_block = False
    
    print("RAW cookie lines in file:")
    for lineno, line in cookie_lines:
        # Truncate for display but show quotes
        display = line[:120] + ('...' if len(line) > 120 else '')
        print(f"  L{lineno}: {display}")
    print()
    
    # Step 2: Check for embedded quotes in raw text
    for lineno, line in cookie_lines:
        quote_positions = [i for i, c in enumerate(line) if c == '"']
        if quote_positions:
            print(f"  ⚠️  Line {lineno} has {len(quote_positions)} double-quote characters")
            # Show context around each quote
            for pos in quote_positions[:5]:
                start = max(0, pos - 15)
                end = min(len(line), pos + 15)
                snippet = line[start:end]
                marker_pos = pos - start
                print(f"     ...{snippet}...")
                print(f"     {'   ' + ' ' * marker_pos}^")
    print()
    
    # Step 3: Parse YAML and check what we actually get
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        cookie = config.get('zoho_credentials', {}).get('cookie', '')
        print(f"YAML-PARSED cookie length: {len(cookie)} chars")
        print(f"First 80 chars: {cookie[:80]}")
        print(f"Last 80 chars:  {cookie[-80:]}")
        print()
        
        # Check for quote chars in parsed value
        parsed_quotes = cookie.count('"')
        print(f"Double quotes in parsed cookie: {parsed_quotes}")
        
        if parsed_quotes > 0:
            # Find them
            for i, c in enumerate(cookie):
                if c == '"':
                    start = max(0, i - 20)
                    end = min(len(cookie), i + 20)
                    print(f"  Quote at position {i}: ...{cookie[start:end]}...")
        print()
        
        # Step 4: Test with the parsed cookie
        print("Testing parsed cookie against Zoho API...")
        creds = config['zoho_credentials']
        headers = {
            'Cookie': creds['cookie'],
            'x-zcsrf-token': creds['csrf_token'],
            'x-crm-org': creds['org_id'],
            'User-Agent': 'Mozilla/5.0',
            'x-requested-with': 'XMLHttpRequest, XMLHttpRequest'
        }
        
        resp = requests.get(
            f"{BASE_URL}/settings/functions?type=org&start=1&limit=2",
            headers=headers
        )
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.text[:200]}")
        print()
        
        if resp.status_code == 400:
            print("FAILED — trying with quotes stripped from cookie...")
            cleaned = cookie.replace('"', '')
            headers['Cookie'] = cleaned
            
            resp2 = requests.get(
                f"{BASE_URL}/settings/functions?type=org&start=1&limit=2",
                headers=headers
            )
            print(f"  Status: {resp2.status_code}")
            print(f"  Response: {resp2.text[:200]}")
            print()
            
            if resp2.status_code == 200:
                print("✅ STRIPPING QUOTES FIXED IT!")
                print()
                print("The embedded double quotes in the cookie are the problem.")
                print("See fix options below.")
            else:
                print("Still failing — credentials may actually be expired.")
                print("Refresh from DevTools and try again.")
                return
        elif resp.status_code == 200:
            print("✅ Cookie works fine — YAML parsed it correctly!")
            return
        
    except yaml.YAMLError as e:
        print(f"❌ YAML PARSE ERROR: {e}")
        print()
        print("The YAML file itself is broken due to the quotes.")
    
    # Step 5: Show the fix
    print()
    print("=" * 60)
    print("FIX OPTIONS")
    print("=" * 60)
    print()
    print("Option 1 (RECOMMENDED): Use YAML block scalar")
    print("  In your YAML file, change the cookie line to:")
    print()
    print("  zoho_credentials:")
    print("    cookie: |")
    print("      ZW_CSRF_TOKEN=abc123; _iamadt=xyz789; ...")
    print()
    print("  The pipe (|) tells YAML to treat the next indented")
    print("  line as a literal string — no quote parsing at all.")
    print("  The cookie value must be indented (2+ spaces).")
    print()
    print("Option 2: Strip quotes programmatically")
    print("  Add to zoho_client.py __init__:")
    print("    cookie = cookie.replace('\"', '')")
    print()
    print("Option 3: Save cookie to a separate .txt file")
    print("  zoho_credentials:")
    print("    cookie_file: config/blades_cookie.txt")
    print("  Then load it as raw text (no YAML parsing).")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python diag_cookie.py config/blades.yaml")
        sys.exit(1)
    diagnose(sys.argv[1])
