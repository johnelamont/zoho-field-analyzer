#!/usr/bin/env python3
"""
Parse curl.txt → generate test.ps1 → run it.

Usage:
  python make_ps1.py blades          # generates and runs test_blades.ps1
  python make_ps1.py blades --no-run  # just generates, doesn't run
"""
import re
import sys
from pathlib import Path
import subprocess


def parse_curl_to_ps1(curl_text):
    """
    Convert a 'Copy as cURL (bash)' command into a single-line 
    PowerShell curl.exe command with double quotes.
    """
    # Remove line continuations and normalize
    text = curl_text.replace('\\\r\n', ' ').replace('\\\n', ' ')
    text = ' '.join(text.split())  # collapse whitespace
    
    # Extract URL (first quoted string after curl)
    url_match = re.search(r"curl\s+'([^']+)'", text)
    if not url_match:
        url_match = re.search(r'curl\s+"([^"]+)"', text)
    if not url_match:
        print("❌ Could not find URL in cURL command")
        return None, {}
    
    url = url_match.group(1)
    
    # Extract all -H headers
    headers = {}
    for m in re.finditer(r"-H\s+'([^']+)'", text):
        hdr = m.group(1)
        if ':' in hdr:
            name, value = hdr.split(':', 1)
            headers[name.strip()] = value.strip()
    
    # Extract -b cookie
    cookie = None
    bm = re.search(r"-b\s+'([^']+)'", text)
    if bm:
        cookie = bm.group(1)
    
    # Build the PowerShell command
    # In PS, we use double quotes. Inner double quotes need to be escaped as `"
    parts = [f'curl.exe -s "{url}"']
    
    for name, value in headers.items():
        # Escape any double quotes in header values
        safe_value = value.replace('"', '`"')
        parts.append(f'-H "{name}: {safe_value}"')
    
    if cookie:
        # For -b, escape inner double quotes
        safe_cookie = cookie.replace('"', '`"')
        parts.append(f'-b "{safe_cookie}"')
    
    ps_cmd = ' '.join(parts)
    
    creds = {
        'cookie': cookie,
        'headers': headers,
        'url': url,
    }
    
    return ps_cmd, creds


def main():
    client = sys.argv[1] if len(sys.argv) > 1 else 'blades'
    no_run = '--no-run' in sys.argv
    curl_file = 'curl.txt'
    
    if not Path(curl_file).exists():
        print(f"❌ {curl_file} not found")
        sys.exit(1)
    
    text = Path(curl_file).read_text(encoding='utf-8')
    print(f"Read {len(text)} chars from {curl_file}")
    
    # Generate two PS1 files:
    # 1. Full original cURL (all headers) hitting original URL
    # 2. Same headers but hitting functions test endpoint
    
    ps_cmd_original, creds = parse_curl_to_ps1(text)
    
    if not ps_cmd_original:
        sys.exit(1)
    
    # Modify URL to test endpoint
    ps_cmd_test = ps_cmd_original.replace(
        creds['url'], 
        'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=2'
    )
    
    # Write PS1 files
    ps1_path = Path(f'test_{client}.ps1')
    ps1_content = (
        f'Write-Host "TEST 1: Original URL"\n'
        f'{ps_cmd_original}\n'
        f'Write-Host ""\n'
        f'Write-Host ""\n'
        f'Write-Host "TEST 2: Functions endpoint"\n'
        f'{ps_cmd_test}\n'
        f'Write-Host ""\n'
    )
    
    ps1_path.write_text(ps1_content, encoding='utf-8')
    print(f"Generated: {ps1_path}")
    print()
    
    # Also write a minimal version with just auth-critical headers
    cookie = creds.get('cookie', '')
    csrf = creds['headers'].get('x-zcsrf-token', '')
    org = creds['headers'].get('x-crm-org', '')
    
    safe_cookie = cookie.replace('"', '`"')
    
    ps1_minimal = Path(f'test_{client}_minimal.ps1')
    ps1_minimal.write_text(
        f'Write-Host "TEST: Minimal headers"\n'
        f'curl.exe -s "https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=2" '
        f'-H "x-requested-with: XMLHttpRequest" '
        f'-H "x-zcsrf-token: {csrf}" '
        f'-H "x-crm-org: {org}" '
        f'-b "{safe_cookie}"\n'
        f'Write-Host ""\n',
        encoding='utf-8'
    )
    print(f"Generated: {ps1_minimal}")
    print()
    
    # Show what we parsed
    print(f"URL: {creds['url']}")
    print(f"Headers: {len(creds['headers'])}")
    for k, v in creds['headers'].items():
        if len(v) > 50:
            print(f"  {k}: {v[:40]}...({len(v)} chars)")
        else:
            print(f"  {k}: {v}")
    print(f"Cookie: {len(cookie)} chars")
    print()
    
    if no_run:
        print(f"Run with:")
        print(f"  powershell -ExecutionPolicy Bypass -File {ps1_path}")
        print(f"  powershell -ExecutionPolicy Bypass -File {ps1_minimal}")
    else:
        print("Running full test...")
        print("=" * 60)
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-File', str(ps1_path)],
            capture_output=True, text=True, timeout=30
        )
        print(result.stdout)
        if result.stderr:
            print(f"Stderr: {result.stderr[:300]}")
        
        print()
        print("Running minimal test...")
        print("=" * 60)
        result2 = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-File', str(ps1_minimal)],
            capture_output=True, text=True, timeout=30
        )
        print(result2.stdout)
        if result2.stderr:
            print(f"Stderr: {result2.stderr[:300]}")
        
        # Check results
        print("=" * 60)
        if '"functions"' in result.stdout or '"functions"' in result2.stdout:
            print("✅ SUCCESS — credentials work!")
            print()
            # Save
            d = Path('config') / client
            d.mkdir(parents=True, exist_ok=True)
            (d / 'cookie.txt').write_text(cookie, encoding='utf-8')
            (d / 'csrf_token.txt').write_text(csrf, encoding='utf-8')
            (d / 'org_id.txt').write_text(org, encoding='utf-8')
            static = creds['headers'].get('x-static-version', '')
            if static:
                (d / 'static_token.txt').write_text(static, encoding='utf-8')
            print(f"Saved to config/{client}/")
        else:
            print("❌ Both failed")
            print()
            print("Try running the .ps1 manually:")
            print(f"  powershell -ExecutionPolicy Bypass -File {ps1_minimal}")


if __name__ == '__main__':
    main()
