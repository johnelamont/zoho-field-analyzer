"""
Main Extraction Script
Orchestrates all data extraction from Zoho CRM
"""
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any
import logging

from ..api.zoho_client import ZohoAPIClient
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

logger = logging.getLogger(__name__)


# Registry of available extractors
EXTRACTORS = {
    'functions': FunctionsExtractor,
    'workflows': WorkflowsExtractor,
    'blueprints': BlueprintsExtractor,
    'modules': ModulesExtractor,
}


def load_client_config(client_name: str, config_dir: Path = None) -> Dict[str, Any]:
    """
    Load client configuration from YAML file
    
    Args:
        client_name: Name of the client
        config_dir: Directory containing config files
        
    Returns:
        Configuration dictionary
    """
    if config_dir is None:
        config_dir = Path('config')
    
    config_file = config_dir / f'{client_name}.yaml'
    
    if not config_file.exists():
        logger.error(f"Configuration file not found: {config_file}")
        logger.info(f"Create a config file by copying config/client_template.yaml")
        sys.exit(1)
    
    logger.info(f"Loading configuration: {config_file}")
    config = load_yaml(config_file)
    
    # Validate required fields
    if 'zoho_credentials' not in config:
        logger.error("Missing 'zoho_credentials' in config file")
        sys.exit(1)
    
    creds = config['zoho_credentials']
    required = ['cookie', 'csrf_token', 'org_id']
    
    for field in required:
        if field not in creds or not creds[field] or 'YOUR_' in creds[field]:
            logger.error(f"Missing or invalid '{field}' in zoho_credentials")
            logger.info("Please update your configuration file with valid credentials")
            sys.exit(1)
    
    return config


def create_api_client(config: Dict[str, Any]) -> ZohoAPIClient:
    """
    Create Zoho API client from configuration
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Initialized API client
    """
    creds = config['zoho_credentials']
    
    return ZohoAPIClient(
        cookie=creds['cookie'],
        csrf_token=creds['csrf_token'],
        org_id=creds['org_id']
    )


def run_extraction(client_name: str, extractor_names: List[str], 
                   config_dir: Path = None, base_data_dir: Path = None,
                   blueprint_id: str = None, blueprint_module: str = None,
                   with_transitions: bool = False, with_field_updates: bool = False) -> Dict[str, Any]:
    """
    Run data extraction for specified extractors
    
    Args:
        client_name: Name of the client
        extractor_names: List of extractor names to run
        config_dir: Configuration directory
        base_data_dir: Base data directory
        
    Returns:
        Extraction results
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
    
    logger.info("="*60)
    logger.info("ZOHO FIELD ANALYZER - DATA EXTRACTION")
    logger.info("="*60)
    logger.info(f"Client: {client_name}")
    logger.info(f"Extractors: {', '.join(extractor_names)}")
    if with_transitions:
        logger.info(f"With transitions: Yes (slower, more complete)")
    if with_field_updates:
        logger.info(f"With field updates: Yes (slower, more complete)")
    logger.info("")
    
    # Create API client
    client = create_api_client(config)
    
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
            # Create extractor instance
            extractor_class = EXTRACTORS[extractor_name]
            
            # BlueprintsExtractor needs special handling for org_id and optional blueprint_id
            if extractor_name == 'blueprints':
                org_id = config['zoho_credentials']['org_id']
                extractor = extractor_class(
                    client, 
                    output_dir, 
                    client_name,
                    org_id=org_id,
                    blueprint_id=blueprint_id,
                    module=blueprint_module,
                    with_transitions=with_transitions
                )
            # WorkflowsExtractor needs special handling for with_field_updates
            elif extractor_name == 'workflows':
                extractor = extractor_class(
                    client,
                    output_dir,
                    client_name,
                    with_field_updates=with_field_updates
                )
            else:
                extractor = extractor_class(client, output_dir, client_name)
            
            # Run extraction
            result = extractor.run()
            results[extractor_name] = result
            
            logger.info(f"Completed {extractor_name} extraction\n")
            
        except Exception as e:
            logger.error(f"Failed to run {extractor_name} extractor: {e}", exc_info=True)
            results[extractor_name] = {
                'status': 'error',
                'error': str(e)
            }
    
    logger.info("="*60)
    logger.info("EXTRACTION COMPLETE")
    logger.info("="*60)
    
    return results


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description='Extract data from Zoho CRM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all data types for a client
  python -m src.extractors.main --client acme_corp --extract-all
  
  # Extract specific data types
  python -m src.extractors.main --client acme_corp --extract functions workflows
  
  # List available clients
  python -m src.extractors.main --list-clients
        """
    )
    
    parser.add_argument(
        '--client',
        help='Client name (must have a config file in config/)'
    )
    
    parser.add_argument(
        '--extract',
        nargs='+',
        choices=list(EXTRACTORS.keys()),
        help='Data types to extract'
    )
    
    parser.add_argument(
        '--extract-all',
        action='store_true',
        help='Extract all available data types'
    )
    
    parser.add_argument(
        '--list-clients',
        action='store_true',
        help='List available client configurations'
    )
    
    parser.add_argument(
        '--config-dir',
        type=Path,
        default=Path('config'),
        help='Configuration directory (default: config/)'
    )
    
    parser.add_argument(
        '--data-dir',
        type=Path,
        default=Path('data'),
        help='Data directory (default: data/)'
    )
    
    parser.add_argument(
        '--blueprint-id',
        help='Specific blueprint ID to extract (blueprints only)'
    )
    
    parser.add_argument(
        '--blueprint-module',
        help='Module name for blueprint (required with --blueprint-id)'
    )
    
    parser.add_argument(
        '--with-transitions',
        action='store_true',
        help='Extract detailed transition information (blueprints only, slower)'
    )
    
    parser.add_argument(
        '--with-field-updates',
        action='store_true',
        help='Extract detailed field update information (workflows only, slower)'
    )
    
    args = parser.parse_args()
    
    # List clients
    if args.list_clients:
        config_dir = args.config_dir
        if config_dir.exists():
            configs = list(config_dir.glob('*.yaml'))
            if configs:
                print("Available client configurations:")
                for config_file in configs:
                    if config_file.stem != 'client_template':
                        print(f"  - {config_file.stem}")
            else:
                print("No client configurations found")
        else:
            print(f"Config directory not found: {config_dir}")
        
        # Also list data directories
        data_dir = args.data_dir
        if data_dir.exists():
            clients = list_clients(data_dir)
            if clients:
                print("\nClients with data:")
                for client in clients:
                    print(f"  - {client}")
        
        sys.exit(0)
    
    # Validate arguments
    if not args.client:
        parser.error("--client is required (or use --list-clients)")
    
    if not args.extract and not args.extract_all:
        parser.error("Must specify --extract or --extract-all")
    
    # Validate blueprint-specific arguments
    if args.blueprint_id and not args.blueprint_module:
        parser.error("--blueprint-module is required when using --blueprint-id")
    
    if args.blueprint_id and 'blueprints' not in (args.extract or []):
        parser.error("--blueprint-id can only be used with --extract blueprints")
    
    # Determine which extractors to run
    if args.extract_all:
        extractors = list(EXTRACTORS.keys())
    else:
        extractors = args.extract
    
    # Run extraction
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
        
        # Print summary
        print("\nExtraction Summary:")
        print("="*60)
        for name, result in results.items():
            status = result.get('status', 'unknown')
            stats = result.get('stats', {})
            
            print(f"\n{name.upper()}:")
            print(f"  Status: {status}")
            if 'total' in stats:
                print(f"  Total: {stats['total']}")
                print(f"  Successful: {stats['successful']}")
                print(f"  Failed: {stats['failed']}")
        
        print("\n" + "="*60)
        
    except KeyboardInterrupt:
        print("\n\nExtraction cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
