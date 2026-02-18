"""
Main Extraction Script
Orchestrates all data extraction from Zoho CRM

Updated to use plain-text credential loading (no more YAML cookie issues).
"""
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
import logging

from ..api.zoho_client import ZohoAPIClient, load_credentials
from ..utils.logging_config import setup_logging
from ..utils.file_helpers import (
    load_yaml, 
    get_client_raw_dir,
    list_clients
)

from .functions import FunctionsExtractor
from .workflows import WorkflowsExtractor
from .blueprints import BlueprintsExtractor
from .modules import ModulesExtractor
from .recruit.functions import RecruitFunctionsExtractor
from .flow.functions import FlowFunctionsExtractor

logger = logging.getLogger(__name__)


# Registry of available extractors
EXTRACTORS = {
    'functions': FunctionsExtractor,
    'workflows': WorkflowsExtractor,
    'blueprints': BlueprintsExtractor,
    'modules': ModulesExtractor,
    'recruit_functions': RecruitFunctionsExtractor,
    'flow_functions': FlowFunctionsExtractor,
}

# Which Zoho product each extractor targets (for connection testing)
EXTRACTOR_PRODUCT = {
    'functions': 'crm',
    'workflows': 'crm',
    'blueprints': 'crm',
    'modules': 'crm',
    'recruit_functions': 'recruit',
    'flow_functions': 'flow',
}

# Connection test URLs per product
PRODUCT_TEST_URLS = {
    'crm': 'https://crm.zoho.com/crm/v2/settings/functions?type=org&start=1&limit=1',
    'recruit': 'https://recruit.zoho.com/recruit/v2/settings/functions?type=org&start=1&limit=1',
    'flow': 'https://flow.zoho.com/rest/flow-deluge-functions/',
}


def load_client_config(client_name: str, config_dir: Path = None) -> Dict[str, Any]:
    """
    Load client configuration.
    
    Credentials come from plain text files: config/{client_name}/*.txt
    Other settings come from YAML: config/{client_name}.yaml (if exists)
    """
    if config_dir is None:
        config_dir = Path('config')
    
    # Load credentials from text files (preferred) or YAML (fallback)
    creds = load_credentials(client_name, config_dir)
    
    # Load additional config from YAML if it exists (rate limits, output settings, etc.)
    yaml_file = config_dir / f'{client_name}.yaml'
    if yaml_file.exists():
        config = load_yaml(yaml_file)
    else:
        config = {}
    
    # Inject credentials into config (overrides YAML values)
    config['zoho_credentials'] = creds
    
    return config


def create_api_client(config: Dict[str, Any]) -> ZohoAPIClient:
    """
    Create Zoho API client from configuration.
    
    Now properly passes static_token and uses cleaned credentials.
    """
    creds = config['zoho_credentials']
    extraction_settings = config.get('extraction', {})
    
    client = ZohoAPIClient(
        cookie=creds['cookie'],
        csrf_token=creds['csrf_token'],
        org_id=creds['org_id'],
        static_token=creds.get('static_token'),
        all_headers=creds.get('all_headers'),
        max_retries=extraction_settings.get('max_retries', 3),
        retry_delay=extraction_settings.get('retry_delay', 1.0),
    )
    
    return client


def run_extraction(client_name: str, extractor_names: List[str], 
                   config_dir: Path = None, base_data_dir: Path = None,
                   blueprint_id: str = None, blueprint_module: str = None,
                   with_transitions: bool = False, with_field_updates: bool = False) -> Dict[str, Any]:
    """
    Run data extraction for specified extractors
    """
    # Load configuration
    config = load_client_config(client_name, config_dir)
    
    # Setup logging
    if 'output' in config and 'log_dir' in config['output']:
        log_dir = Path(config['output']['log_dir'])
    else:
        log_dir = Path('logs')
    
    log_level = config.get('output', {}).get('log_level', 'INFO')
    setup_logging(log_dir=log_dir, log_level=log_level)
    
    logger.info("=" * 60)
    logger.info("ZOHO FIELD ANALYZER -- DATA EXTRACTION")
    logger.info("=" * 60)
    logger.info(f"Client: {client_name}")
    logger.info(f"Extractors: {', '.join(extractor_names)}")
    if with_transitions:
        logger.info(f"With transitions: Yes")
    if with_field_updates:
        logger.info(f"With field updates: Yes")
    logger.info("")
    
    # Create API client
    client = create_api_client(config)
    
    # Quick connection test before starting extraction
    # Pick the right test URL based on which product we're extracting from
    products = set(EXTRACTOR_PRODUCT.get(e, 'crm') for e in extractor_names)
    test_product = list(products)[0]  # If mixed, test the first one
    test_url = PRODUCT_TEST_URLS.get(test_product)
    
    logger.info("Testing credentials against %s...", test_product)
    if not client.test_connection(test_url=test_url):
        logger.error("Credential test failed! Refresh with: python save_curl.py %s", client_name)
        return {'error': 'credentials_failed'}
    logger.info("")
    
    # Get output directory
    output_dir = get_client_raw_dir(client_name, base_data_dir)
    logger.info(f"Output directory: {output_dir}")
    logger.info("")
    
    # Run extractors
    results = {}
    
    for extractor_name in extractor_names:
        if extractor_name not in EXTRACTORS:
            logger.warning(f"Unknown extractor: {extractor_name}")
            continue
        
        logger.info(f"Running {extractor_name} extractor...")
        
        try:
            extractor_class = EXTRACTORS[extractor_name]
            
            if extractor_name == 'blueprints':
                org_id = config['zoho_credentials']['org_id']
                extractor = extractor_class(
                    client, output_dir, client_name,
                    org_id=org_id,
                    blueprint_id=blueprint_id,
                    module=blueprint_module,
                    with_transitions=with_transitions
                )
            elif extractor_name == 'workflows':
                extractor = extractor_class(
                    client, output_dir, client_name,
                    with_field_updates=with_field_updates
                )
            else:
                extractor = extractor_class(client, output_dir, client_name)
            
            result = extractor.run()
            results[extractor_name] = result
            
            logger.info(f"Completed {extractor_name} extraction\n")
            
        except Exception as e:
            logger.error(f"Failed to run {extractor_name} extractor: {e}", exc_info=True)
            results[extractor_name] = {
                'status': 'error',
                'error': str(e)
            }
    
    logger.info("=" * 60)
    logger.info("EXTRACTION COMPLETE")
    logger.info("=" * 60)
    
    return results


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description='Extract data from Zoho CRM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First: refresh credentials
  python save_curl.py blades               # CRM credentials
  python save_curl.py blades-recruit        # Recruit credentials (separate!)
  python save_curl.py blades-flow           # Flow credentials (separate!)

  # Extract CRM data
  python -m src.extractors.main --client blades --extract functions workflows
  python -m src.extractors.main --client blades --extract-all
  
  # Extract Recruit data (needs Recruit credentials)
  python -m src.extractors.main --client blades-recruit --extract recruit_functions
  
  # Extract Flow data (needs Flow credentials)
  python -m src.extractors.main --client blades-flow --extract flow_functions
  
  # List available clients
  python -m src.extractors.main --list-clients
        """
    )
    
    parser.add_argument('--client', help='Client name')
    parser.add_argument('--extract', nargs='+', choices=list(EXTRACTORS.keys()),
                       help='Data types to extract')
    parser.add_argument('--extract-all', action='store_true',
                       help='Extract all data types')
    parser.add_argument('--list-clients', action='store_true',
                       help='List available clients')
    parser.add_argument('--config-dir', type=Path, default=Path('config'))
    parser.add_argument('--data-dir', type=Path, default=Path('data'))
    parser.add_argument('--blueprint-id', help='Specific blueprint ID')
    parser.add_argument('--blueprint-module', help='Module for --blueprint-id')
    parser.add_argument('--with-transitions', action='store_true')
    parser.add_argument('--with-field-updates', action='store_true')
    
    args = parser.parse_args()
    
    if args.list_clients:
        config_dir = args.config_dir
        
        # Check for text-file credential directories
        if config_dir.exists():
            print("Clients with credentials:")
            for d in sorted(config_dir.iterdir()):
                if d.is_dir() and (d / 'cookie.txt').exists():
                    print(f"  OK: {d.name} (text files)")
            
            # Also show YAML-only clients
            for f in sorted(config_dir.glob('*.yaml')):
                if f.stem != 'client_template':
                    creds_dir = config_dir / f.stem
                    if not (creds_dir / 'cookie.txt').exists():
                        print(f"  WARN:  {f.stem} (YAML only -- run: python save_curl.py {f.stem})")
        
        data_dir = args.data_dir
        if data_dir.exists():
            clients = list_clients(data_dir)
            if clients:
                print("\nClients with extracted data:")
                for client in clients:
                    print(f"  > {client}")
        
        sys.exit(0)
    
    if not args.client:
        parser.error("--client is required (or use --list-clients)")
    
    if not args.extract and not args.extract_all:
        parser.error("Must specify --extract or --extract-all")
    
    if args.blueprint_id and not args.blueprint_module:
        parser.error("--blueprint-module required with --blueprint-id")
    
    extractors = list(EXTRACTORS.keys()) if args.extract_all else args.extract
    
    try:
        results = run_extraction(
            client_name=args.client,
            extractor_names=extractors,
            config_dir=args.config_dir,
            base_data_dir=args.data_dir,
            blueprint_id=args.blueprint_id,
            blueprint_module=args.blueprint_module,
            with_transitions=args.with_transitions,
            with_field_updates=args.with_field_updates
        )
        
        print("\nExtraction Summary:")
        print("=" * 60)
        
        if 'error' in results and isinstance(results.get('error'), str):
            print(f"\n  FAIL: {results['error']}")
        else:
            for name, result in results.items():
                if not isinstance(result, dict):
                    continue
                status = result.get('status', 'unknown')
                stats = result.get('stats', {})
                print(f"\n{name.upper()}:")
                print(f"  Status: {status}")
                if 'total' in stats:
                    print(f"  Total: {stats['total']}")
                    print(f"  Successful: {stats['successful']}")
                    print(f"  Failed: {stats['failed']}")
        print("\n" + "=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\nFAIL: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
