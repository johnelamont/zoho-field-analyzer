#!/usr/bin/env python3
"""
Quick Visual Comparison: Blades vs MrTarget
Shows exactly what's different in the authentication
"""

import yaml
from pathlib import Path

def load_yaml(filename):
    """Load YAML from uploads directory"""
    path = Path(f'/mnt/user-data/uploads/{filename}')
    with open(path) as f:
        return yaml.safe_load(f)

def compare_credentials():
    """Show side-by-side comparison of credentials"""
    
    blades = load_yaml('blades.yaml')
    mrtarget = load_yaml('mrtarget.yaml')
    
    blades_creds = blades['zoho_credentials']
    mrtarget_creds = mrtarget['zoho_credentials']
    
    print("=" * 80)
    print("CREDENTIAL FIELD COMPARISON")
    print("=" * 80)
    print()
    print(f"{'Field':<20} {'Blades':<30} {'MrTarget':<30}")
    print("-" * 80)
    
    all_keys = set(blades_creds.keys()) | set(mrtarget_creds.keys())
    
    for key in sorted(all_keys):
        blades_has = "✓" if key in blades_creds else "✗ MISSING"
        mrtarget_has = "✓" if key in mrtarget_creds else "✗ MISSING"
        
        # Highlight the difference
        if key == 'static_token':
            if key not in blades_creds:
                blades_has += " ← PROBLEM!"
            print(f"{key:<20} {blades_has:<30} {mrtarget_has:<30}")
        else:
            print(f"{key:<20} {blades_has:<30} {mrtarget_has:<30}")
    
    print()
    print("=" * 80)
    print("WHAT HEADERS ARE BEING SENT")
    print("=" * 80)
    print()
    
    print("BLADES (currently working, but shouldn't be):")
    print("  ✓ x-zcsrf-token")
    print("  ✓ x-crm-org")
    print("  ✓ Cookie (with all session cookies)")
    print("  ✗ X-Static-Token  ← MISSING! (should fail but somehow works)")
    print()
    
    print("MRTARGET (should work, but doesn't):")
    print("  ✓ x-zcsrf-token")
    print("  ✓ x-crm-org")
    print("  ✓ Cookie (with all session cookies)")
    print("  ? X-Static-Token  ← In config, but is your CODE setting the header?")
    print()
    
    print("=" * 80)
    print("THE ISSUE")
    print("=" * 80)
    print()
    print("Even though mrtarget.yaml HAS the static_token field:")
    print(f"  static_token: \"{mrtarget_creds.get('static_token', 'NOT FOUND')}\"")
    print()
    print("Your zoho_client.py probably ISN'T using it to set the header!")
    print()
    print("You need to update zoho_client.py to:")
    print("  1. Accept static_token as a parameter")
    print("  2. Set session.headers['X-Static-Token'] = static_token")
    print()
    
    print("=" * 80)
    print("THE FIX")
    print("=" * 80)
    print()
    print("1. Update your src/api/zoho_client.py:")
    print()
    print("   In __init__ method:")
    print("   ```python")
    print("   def __init__(self, cookie, csrf_token, org_id, static_token=None, ...):")
    print("       # ... existing code ...")
    print("       ")
    print("       if static_token:")
    print("           self.session.headers['X-Static-Token'] = static_token")
    print("   ```")
    print()
    print("2. Update create_client_from_config:")
    print("   ```python")
    print("   return ZohoAPIClient(")
    print("       cookie=creds['cookie'],")
    print("       csrf_token=creds['csrf_token'],")
    print("       org_id=creds['org_id'],")
    print("       static_token=creds.get('static_token'),  # Add this!")
    print("       ...")
    print("   )")
    print("   ```")
    print()
    print("3. Add static_token to blades.yaml too:")
    print("   (Get it from browser DevTools → Network → X-Static-Token header)")
    print()
    
    print("=" * 80)
    print("WHY BLADES WORKS (theory)")
    print("=" * 80)
    print()
    print("Possible reasons:")
    print("1. The blades org might have different security settings")
    print("2. The blades cookies might include a static token equivalent")
    print("3. The blades session might still be 'warm' (recently authenticated)")
    print("4. Different Zoho data centers have different requirements")
    print()
    print("But to be safe and consistent, BOTH clients should:")
    print("- Have static_token in YAML")
    print("- Have X-Static-Token header in requests")
    print()

if __name__ == '__main__':
    compare_credentials()
