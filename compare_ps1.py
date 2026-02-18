#!/usr/bin/env python3
"""
Compare: what does zoho_client generate vs what make_ps1 generates?
Writes both to files so you can diff them.

Usage: python compare_ps1.py blades
"""
import sys
from pathlib import Path

# Import the zoho_client to see what it builds
sys.path.insert(0, '.')
from src.api.zoho_client import ZohoAPIClient, load_credentials


def main():
    client = sys.argv[1] if len(sys.argv) > 1 else 'blades'
    
    # Load creds
    creds = load_credentials(client)
    
    # Create client
    api = ZohoAPIClient(
        cookie=creds['cookie'],
        csrf_token=creds['csrf_token'],
        org_id=creds['org_id'],
        static_token=creds.get('static_token'),
    )
    
    # Build what zoho_client would send for the test URL
    url = 'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=1'
    cmd = api._build_curl_cmd(url)
    
    # Convert to ps1 the same way _exec_curl does
    ps_parts = []
    i = 0
    while i < len(cmd):
        token = cmd[i]
        if token == 'curl.exe':
            ps_parts.append('curl.exe')
        elif token in ('-s', '-X'):
            ps_parts.append(token)
        elif token in ('-w', '-b', '-H', '-d', '--data-urlencode'):
            i += 1
            if i < len(cmd):
                val = cmd[i].replace('`', '``').replace('"', '`"')
                ps_parts.append(f'{token} "{val}"')
        else:
            val = token.replace('`', '``').replace('"', '`"')
            ps_parts.append(f'"{val}"')
        i += 1
    
    generated = ' '.join(ps_parts)
    
    # Write to file
    Path('debug_generated.ps1').write_text(generated, encoding='utf-8')
    print(f"Wrote: debug_generated.ps1 ({len(generated)} chars)")
    
    # Also show the working test_blades_minimal.ps1 if it exists
    minimal = Path(f'test_{client}_minimal.ps1')
    if minimal.exists():
        working = minimal.read_text(encoding='utf-8')
        Path('debug_working.ps1').write_text(working, encoding='utf-8')
        print(f"Wrote: debug_working.ps1 ({len(working)} chars)")
    
    # Show the generated command (truncated)
    print()
    print("GENERATED PS1 (zoho_client):")
    # Show first part up to cookie, then after cookie
    parts = generated.split('-b ')
    if len(parts) == 2:
        before_cookie = parts[0]
        after_cookie = parts[1]
        cookie_end = after_cookie.find('" -H')
        if cookie_end > 0:
            cookie_val = after_cookie[:cookie_end+1]
            rest = after_cookie[cookie_end+1:]
            print(f"  {before_cookie}")
            print(f"  -b [COOKIE: {len(cookie_val)} chars]")
            print(f"  {rest}")
        else:
            print(f"  {before_cookie}")
            print(f"  -b [rest: {len(after_cookie)} chars]")
    else:
        print(f"  {generated[:200]}...")
    
    print()
    print("HEADERS in generated:")
    for part in generated.split(' -H '):
        if part.startswith('"') and ':' in part:
            header = part.split('"')[1] if '"' in part else part
            name = header.split(':')[0]
            print(f"  {name}")
    
    # Show working headers if available
    if minimal.exists():
        working = minimal.read_text(encoding='utf-8')
        print()
        print("HEADERS in working:")
        for part in working.split(' -H '):
            if part.startswith('"') and ':' in part:
                header = part.split('"')[1] if '"' in part else part
                name = header.split(':')[0]
                print(f"  {name}")
    
    # Quick test: run both
    import subprocess
    
    print()
    print("=" * 60)
    print("Running generated ps1...")
    r1 = subprocess.run(
        ['powershell', '-ExecutionPolicy', 'Bypass', '-File', 'debug_generated.ps1'],
        capture_output=True, text=True, timeout=15
    )
    out1 = r1.stdout.strip()
    # Status is last line
    lines1 = out1.rsplit('\n', 1)
    print(f"  Output: {lines1[0][:150] if lines1 else 'empty'}")
    
    if minimal.exists():
        print()
        print("Running working ps1...")
        r2 = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-File', str(minimal)],
            capture_output=True, text=True, timeout=15
        )
        print(f"  Output: {r2.stdout.strip()[:150]}")


if __name__ == '__main__':
    main()
