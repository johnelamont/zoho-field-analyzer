#!/usr/bin/env python3
"""
Refresh and test Zoho CRM credentials.

Workflow:
  1. Captures cURL from Chrome DevTools
  2. Parses cookie, csrf_token, org_id automatically
  3. Saves to plain text files (no YAML quoting issues)
  4. Tests against Zoho API immediately
  5. Reports success/failure

Usage:
  # Interactive — paste cURL when prompted:
  python refresh_creds.py blades

  # Or save credentials manually:
  # 1. Create config/blades/ directory
  # 2. Save cookie.txt, csrf_token.txt, org_id.txt
  # 3. Run: python refresh_creds.py blades --test-only
"""
import argparse
import re
import sys
import requests
from pathlib import Path


def save_powershell_script(creds: dict, path: Path = Path("test-zoho.ps1")) -> Path:
    ps_script = creds_to_powershell(creds)
    path.write_text(ps_script, encoding="utf-8")
    print(f"Saved PowerShell script to {path}")
    return path

BASE_URL = 'https://crm.zoho.com/crm/v2'

def creds_to_powershell(creds: dict) -> str:
    """
    Return a PowerShell script that calls Invoke-WebRequest with headers
    and cookie derived from creds (cookie, csrf_token, org_id, static_token).
    """
    cookie = creds.get("cookie", "")
    csrf = creds.get("csrf_token", "")
    org = creds.get("org_id", "")
    static = creds.get("static_token", "")

    # PowerShell headers hashtable
    lines = []

    lines.append('$headers = @{')
    lines.append(f'  "x-crm-org"        = "{org}"')
    lines.append(f'  "x-zcsrf-token"    = "{csrf}"')
    if static:
        lines.append(f'  "x-static-version" = "{static}"')
    # Add a few essentials; you can extend as needed
    lines.append('  "x-requested-with" = "XMLHttpRequest"')
    lines.append('  "user-agent"       = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                 'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"')
    lines.append('}')
    lines.append('')

    # Cookie as a simple string
    # Escape embedded double quotes for PowerShell string literal
    ps_cookie = cookie.replace('"', '""')
    lines.append(f'$cookie = "{ps_cookie}"')
    lines.append('')

    # Build WebRequestSession and add cookie header manually
    # (PowerShell will send it as a normal Cookie header)
    lines.append('$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession')
    lines.append('$session.Headers["Cookie"] = $cookie')
    lines.append('')

    # Invoke-WebRequest
    url = f'{BASE_URL}/settings/functions?type=org&start=1&limit=2'
    lines.append('Invoke-WebRequest \\')
    lines.append(f'  -Uri "{url}" \\')
    lines.append('  -Headers $headers \\')
    lines.append('  -WebSession $session \\')
    lines.append('  -Method Get')

    return "\n".join(lines)


def normalize_curl(lines):
    # Join with spaces (you already do this)
    text = ' '.join(lines)

    # Remove backslash-newline sequences that Chrome inserts
    # If your pasted text literally contains " \\" at EOL, strip those too.
    text = text.replace('\\\n', ' ').replace('\\\r\n', ' ')

    # Collapse any excess whitespace
    text = ' '.join(text.split())
    return text


def parse_curl(curl_text: str) -> dict:
    """
    Parse a 'Copy as cURL (bash)' string and extract Zoho credentials.
    
    Returns dict with cookie, csrf_token, org_id, static_token (if present)
    """
    creds = {}
    
    # Extract headers: -H 'Header-Name: value' or -H "Header-Name: value"
    # Handle both single and double quoted headers
    header_pattern = r"""-H\s+['"]([^'"]+)['"]"""
    headers = re.findall(header_pattern, curl_text)
    
    for header in headers:
        if ':' not in header:
            continue
        name, value = header.split(':', 1)
        name = name.strip().lower()
        value = value.strip()
        
        if name == 'cookie':
            creds['cookie'] = value
        elif name == 'x-zcsrf-token':
            creds['csrf_token'] = value
        elif name == 'x-crm-org':
            creds['org_id'] = value
        elif name == 'x-static-version':
            if value:  # Only save if non-empty
                creds['static_token'] = value
    
    # NEW: capture cookie from -b / --cookie
    cookie_pattern = r"""(?:-b|--cookie)\s+(['"])(.*?)\1"""
    m = re.search(cookie_pattern, curl_text, flags=re.DOTALL)
    if m:
        creds['cookie'] = m.group(2)

    return creds


def save_credentials(client_name: str, creds: dict, config_dir: Path = None):
    """Save credentials to plain text files"""
    if config_dir is None:
        config_dir = Path('config')
    
    creds_dir = config_dir / client_name
    creds_dir.mkdir(parents=True, exist_ok=True)
    
    files_saved = []
    for key, filename in [
        ('cookie', 'cookie.txt'),
        ('csrf_token', 'csrf_token.txt'),
        ('org_id', 'org_id.txt'),
        ('static_token', 'static_token.txt'),
    ]:
        if key in creds and creds[key]:
            filepath = creds_dir / filename
            filepath.write_text(creds[key], encoding='utf-8')
            files_saved.append(f"  {filepath} ({len(creds[key])} chars)")
    
    return files_saved


def test_credentials(creds: dict) -> bool:
    """Test credentials against Zoho functions API"""
    headers = {
        'Cookie': creds['cookie'],
        'x-zcsrf-token': creds['csrf_token'],
        'x-crm-org': creds['org_id'],
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'x-requested-with': 'XMLHttpRequest, XMLHttpRequest',
    }
    
    if creds.get('static_token'):
        headers['x-static-version'] = creds['static_token']
    
    # Test 1: Functions API (v2)
    print("  Testing v2 API (functions)...", end=' ')
    url = f"{BASE_URL}/settings/functions?type=org&start=1&limit=2"
    resp = requests.get(url, headers=headers)
    
    if resp.status_code == 200:
        try:
            data = resp.json()
            count = len(data.get('functions', []))
            print(f"✅ OK ({count} functions)")
        except:
            print(f"✅ OK (status 200)")
    else:
        print(f"❌ FAILED ({resp.status_code})")
        print(f"    Response: {resp.text[:200]}")
        print(f"       Cookie value is: {creds['cookie']}")
        return False
    
    # Test 2: Blueprints endpoint (ProcessFlow.do)
    if creds.get('org_id'):
        print("  Testing blueprint API...", end=' ')
        bp_url = f"https://crm.zoho.com/crm/org{creds['org_id']}/ProcessFlow.do"
        bp_params = {
            'action': 'showAllProcesses',
            'module': 'All',
            'isFromBack': 'true',
        }
        bp_resp = requests.get(bp_url, headers=headers, params=bp_params)
        
        if bp_resp.status_code == 200:
            content_type = bp_resp.headers.get('Content-Type', '')
            if 'json' in content_type.lower():
                try:
                    data = bp_resp.json()
                    count = len(data.get('Processes', []))
                    print(f"✅ OK ({count} blueprints)")
                except:
                    print(f"✅ OK (status 200)")
            else:
                print(f"⚠️  Got HTML — may need static_token for blueprints")
        else:
            print(f"⚠️  Status {bp_resp.status_code} — blueprints may need static_token")
    
    return True


def interactive_capture():
    """Prompt user to paste cURL and parse it"""
    print()
    print("Paste the cURL command from Chrome DevTools, then press Enter twice:")
    print("(In Chrome: Network tab → right-click request → Copy → Copy as cURL (bash))")
    print()
    
    lines = []
    empty_count = 0
    
    while True:
        try:
            line = input()
        except EOFError:
            break

        # Two blank lines → end
        if line.strip() == '':
            empty_count += 1
            if empty_count >= 2:
                break
            continue
        else:
            empty_count = 0

        # Remove trailing backslash used for line continuation
        line = line.rstrip()
        if line.endswith('\\'):
            line = line[:-1].rstrip()

        lines.append(line)
    
    curl_text = ' '.join(lines)
    #curl_text = normalize_curl(lines)
    
    if not curl_text.strip():
        print("No input received.")
        return None
    
    creds = parse_curl(curl_text)
    
    error = False

    if not creds.get('cookie'):
        print("❌ Could not find Cookie header in cURL command")
        error = True
    if not creds.get('csrf_token'):
        print("❌ Could not find x-zcsrf-token header in cURL command")
        error = True
    if not creds.get('org_id'):
        print("❌ Could not find x-crm-org header in cURL command")
        error  = True
    
    if error:
        return None
    
    return creds, curl_text


def main():
    parser = argparse.ArgumentParser(
        description='Refresh and test Zoho CRM credentials',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python refresh_creds.py blades              # Interactive — paste cURL
  python refresh_creds.py blades --test-only  # Test existing credentials
  python refresh_creds.py lamont              # Different client
        """
    )
    
    parser.add_argument('client', help='Client name (e.g., blades, lamont)')
    parser.add_argument('--test-only', action='store_true',
                       help='Only test existing credentials, do not capture new ones')
    parser.add_argument('--config-dir', type=Path, default=Path('config'),
                       help='Config directory (default: config/)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print(f"ZOHO CREDENTIAL REFRESH — {args.client.upper()}")
    print("=" * 60)
    
    if args.test_only:
        # Load and test existing credentials
        creds_dir = args.config_dir / args.client
        
        creds = {}
        for key, filename in [
            ('cookie', 'cookie.txt'),
            ('csrf_token', 'csrf_token.txt'),
            ('org_id', 'org_id.txt'),
            ('static_token', 'static_token.txt'),
        ]:
            filepath = creds_dir / filename
            if filepath.exists():
                creds[key] = filepath.read_text(encoding='utf-8').strip()
                print(f"  Loaded {filename}: {len(creds[key])} chars")
            elif key != 'static_token':
                print(f"  ❌ Missing: {filepath}")
                sys.exit(1)
        
        print()
        print("Testing credentials...")
        if test_credentials(creds):
            print()
            print("✅ Credentials are valid. Ready to extract:")
            print(f"   python -m src.extractors.main --client {args.client} --extract-all")
        else:
            print()
            print("❌ Credentials failed. Refresh them:")
            print(f"   python refresh_creds.py {args.client}")
        
    else:
        # Interactive capture
        creds, curl_text = interactive_capture()
        
        if not creds:
            sys.exit(1)
        
        print()
        print("Parsed credentials:")
        print(f"  Cookie:       {len(creds['cookie'])} chars")
        print(f"  CSRF token:   {creds['csrf_token'][:40]}...")
        print(f"  Org ID:       {creds['org_id']}")
        if creds.get('static_token'):
            print(f"  Static token: {creds['static_token']}")
        print()
        
        # Test before saving
        print("Testing credentials...")
        if test_credentials(creds):
            print()
            
            # Save
            files = save_credentials(args.client, creds, args.config_dir)
            print("Saved credentials:")
            for f in files:
                print(f)
            
            print()
            print("✅ Ready to extract:")
            print(f"   python -m src.extractors.main --client {args.client} --extract-all")
        else:
            ps_path = save_powershell_script(creds)
            print()
            print("❌ Credentials failed verification.")
            print()
            print("Common causes:")
            print("  1. Zoho session expired between copy and paste (be fast!)")
            print("  2. Copied from wrong request — use a 200-status request")
            print("  3. Not logged into Zoho CRM in that browser tab")
            print(f"  4. Try this: {ps_path}")
            print()
            
            # Save anyway in case user wants to debug
            save = input("Save anyway for debugging? (y/n): ").strip().lower()
            if save == 'y':
                files = save_credentials(args.client, creds, args.config_dir)
                print("Saved:")
                for f in files:
                    print(f)
            
            sys.exit(1)


if __name__ == '__main__':
    main()
