"""
Blueprint API Explorer
Test script to explore Zoho Blueprint endpoints and see what they return
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.api.zoho_client import ZohoAPIClient
from src.utils.logging_config import setup_logging
from src.utils.file_helpers import load_yaml

# Setup
setup_logging(log_level='INFO')


def save_response(data, filename):
    """Save API response to file for inspection"""
    output_dir = Path('api_exploration')
    output_dir.mkdir(exist_ok=True)
    
    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"   ✓ Saved to: {filepath}")
    return filepath


def explore_blueprint_endpoints(client, org_id, process_id=None, module='Accounts'):
    """
    Test the three blueprint endpoints you found
    
    Args:
        client: ZohoAPIClient instance
        org_id: Your Zoho org ID
        process_id: Optional specific blueprint/process ID
        module: Module name (default: Accounts)
    """
    print("\n" + "="*80)
    print("BLUEPRINT API EXPLORATION")
    print("="*80)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Endpoint 1: List all processes/blueprints
    print("\n[1] Getting all processes/blueprints...")
    print("    Endpoint: ProcessFlow.do?action=showAllProcesses")
    
    # This uses the old-style Zoho URL format, not v2 REST API
    # We'll need to make a direct request
    url1 = f"https://crm.zoho.com/crm/org{org_id}/ProcessFlow.do"
    params1 = {
        'pageTitle': 'crm.label.process.automation',
        'allowMultiClick': 'true',
        'action': 'showAllProcesses',
        'isFromBack': 'true'
    }
    
    try:
        response1 = client.session.get(url1, params=params1)
        if response1.status_code == 200:
            try:
                data1 = response1.json()
                filepath1 = save_response(data1, f'blueprint_all_processes_{timestamp}.json')
                
                # Print summary
                print(f"\n   Response keys: {list(data1.keys())}")
                if isinstance(data1, dict) and 'processes' in data1:
                    print(f"   Found {len(data1.get('processes', []))} processes")
            except json.JSONDecodeError:
                # Might be HTML
                print(f"   ⚠ Response is not JSON (might be HTML)")
                with open(f'api_exploration/blueprint_all_processes_{timestamp}.html', 'w') as f:
                    f.write(response1.text)
                print(f"   Saved as HTML for inspection")
        else:
            print(f"   ✗ Error: {response1.status_code}")
            print(f"   {response1.text[:200]}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    
    # Endpoint 2: Get specific process details
    if process_id:
        print(f"\n[2] Getting process details for ID: {process_id}...")
        print(f"    Endpoint: ProcessFlow.do?action=getProcessDetails")
        
        url2 = f"https://crm.zoho.com/crm/org{org_id}/ProcessFlow.do"
        params2 = {
            'action': 'getProcessDetails',
            'module': module,
            'processId': process_id,
            'toolTip': module,
            'isFromBack': 'true'
        }
        
        try:
            response2 = client.session.get(url2, params=params2)
            if response2.status_code == 200:
                try:
                    data2 = response2.json()
                    filepath2 = save_response(data2, f'blueprint_process_details_{process_id}_{timestamp}.json')
                    
                    # Print summary
                    print(f"\n   Response keys: {list(data2.keys())}")
                    if 'transitions' in data2:
                        print(f"   Found {len(data2.get('transitions', []))} transitions")
                except json.JSONDecodeError:
                    print(f"   ⚠ Response is not JSON")
                    with open(f'api_exploration/blueprint_process_details_{timestamp}.html', 'w') as f:
                        f.write(response2.text)
            else:
                print(f"   ✗ Error: {response2.status_code}")
        except Exception as e:
            print(f"   ✗ Exception: {e}")
    else:
        print("\n[2] Skipping process details (no process_id provided)")
        print("    Re-run with --process-id to test this endpoint")
    
    
    # Endpoint 3: Get merge fields (field metadata for automation)
    print(f"\n[3] Getting merge fields for module: {module}...")
    print("    Endpoint: /v9/settings/mergefields")
    
    url3 = f"https://crm.zoho.com/crm/v9/settings/mergefields"
    params3 = {
        'module': module,
        'type': 'automation',
        'includelookups': 'true'
    }
    
    try:
        response3 = client.session.get(url3, params=params3)
        if response3.status_code == 200:
            try:
                data3 = response3.json()
                filepath3 = save_response(data3, f'blueprint_mergefields_{module}_{timestamp}.json')
                
                # Print summary
                print(f"\n   Response keys: {list(data3.keys())}")
                if 'merge_fields' in data3:
                    print(f"   Found {len(data3.get('merge_fields', []))} merge fields")
            except json.JSONDecodeError:
                print(f"   ⚠ Response is not JSON")
        else:
            print(f"   ✗ Error: {response3.status_code}")
            print(f"   {response3.text[:200]}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    
    # Also try the v2 settings/blueprints endpoint (REST API)
    print(f"\n[4] Trying v2 REST API endpoint...")
    print("    Endpoint: /v2/settings/blueprints")
    
    try:
        # Try to list all blueprints via REST API
        blueprints_data = client.get('settings/blueprints')
        
        if blueprints_data:
            filepath4 = save_response(blueprints_data, f'blueprint_v2_api_{timestamp}.json')
            print(f"\n   Response keys: {list(blueprints_data.keys())}")
            
            if 'blueprints' in blueprints_data:
                blueprints = blueprints_data['blueprints']
                print(f"   Found {len(blueprints)} blueprints")
                
                # Print summary of each
                print("\n   Blueprints found:")
                for bp in blueprints[:5]:  # First 5
                    bp_id = bp.get('id', 'no-id')
                    bp_name = bp.get('name', 'unnamed')
                    bp_module = bp.get('module', {}).get('api_name', 'unknown')
                    print(f"      - {bp_name} (ID: {bp_id}, Module: {bp_module})")
                
                if len(blueprints) > 5:
                    print(f"      ... and {len(blueprints) - 5} more")
        else:
            print("   ✗ No data returned from v2 API")
    except Exception as e:
        print(f"   ✗ Exception: {e}")
    
    
    print("\n" + "="*80)
    print("EXPLORATION COMPLETE")
    print("="*80)
    print(f"\nAll responses saved to: api_exploration/")
    print("\nNext steps:")
    print("1. Review the JSON files in api_exploration/")
    print("2. Look for blueprint/process structures")
    print("3. Identify transition data and field updates")
    print("4. Update BlueprintsExtractor with the correct endpoints")
    print("\nTip: Use 'jq' or 'python -m json.tool' to pretty-print JSON files")
    print("     Or open them in VS Code for syntax highlighting")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Explore Zoho Blueprint API endpoints',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic exploration (uses config file)
  python explore_blueprints_api.py --client blades
  
  # Test specific process
  python explore_blueprints_api.py --client blades --process-id 3193870000116366582
  
  # Different module
  python explore_blueprints_api.py --client blades --module Leads
        """
    )
    
    parser.add_argument(
        '--client',
        required=True,
        help='Client name (must have config file)'
    )
    
    parser.add_argument(
        '--process-id',
        help='Specific blueprint/process ID to fetch details'
    )
    
    parser.add_argument(
        '--module',
        default='Accounts',
        help='Module name (default: Accounts)'
    )
    
    parser.add_argument(
        '--config-dir',
        type=Path,
        default=Path('config'),
        help='Config directory (default: config/)'
    )
    
    args = parser.parse_args()
    
    # Load config
    config_file = args.config_dir / f'{args.client}.yaml'
    if not config_file.exists():
        print(f"Error: Config file not found: {config_file}")
        sys.exit(1)
    
    print(f"Loading config: {config_file}")
    config = load_yaml(config_file)
    
    # Validate credentials
    if 'zoho_credentials' not in config:
        print("Error: Missing zoho_credentials in config")
        sys.exit(1)
    
    creds = config['zoho_credentials']
    
    # Create API client
    client = ZohoAPIClient(
        cookie=creds['cookie'],
        csrf_token=creds['csrf_token'],
        org_id=creds['org_id']
    )
    
    # Run exploration
    explore_blueprint_endpoints(
        client=client,
        org_id=creds['org_id'],
        process_id=args.process_id,
        module=args.module
    )


if __name__ == '__main__':
    main()
