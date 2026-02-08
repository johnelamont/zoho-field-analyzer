"""
Example Usage of Zoho Field Analyzer
Demonstrates how to use the API programmatically
"""
from pathlib import Path
from src.api.zoho_client import ZohoAPIClient
from src.extractors.functions import FunctionsExtractor
from src.extractors.modules import ModulesExtractor
from src.analyzers.field_tracker import FieldTracker
from src.analyzers.rosetta_builder import RosettaStoneBuilder
from src.utils.logging_config import setup_logging
from src.utils.file_helpers import get_client_raw_dir, get_client_analyzed_dir


def example_basic_extraction():
    """Example: Basic extraction workflow"""
    
    # Setup logging
    setup_logging(log_level='INFO')
    
    # Create API client (replace with your credentials)
    client = ZohoAPIClient(
        cookie="YOUR_COOKIE_HERE",
        csrf_token="crmcsrfparam=YOUR_TOKEN_HERE",
        org_id="YOUR_ORG_ID_HERE"
    )
    
    # Get output directory
    client_name = "example_client"
    output_dir = get_client_raw_dir(client_name)
    
    # Extract functions
    print("Extracting functions...")
    functions_extractor = FunctionsExtractor(client, output_dir, client_name)
    results = functions_extractor.run()
    
    print(f"Extracted {results['stats']['successful']} functions")
    print(f"Failed: {results['stats']['failed']}")
    
    return results


def example_field_analysis():
    """Example: Analyze field usage"""
    
    setup_logging(log_level='INFO')
    
    client_name = "example_client"
    raw_dir = get_client_raw_dir(client_name)
    analyzed_dir = get_client_analyzed_dir(client_name)
    
    # Track field usage
    print("Analyzing field usage...")
    tracker = FieldTracker(client_name, raw_dir)
    field_map = tracker.build_field_map()
    
    # Save results
    output_file = analyzed_dir / 'field_map.json'
    tracker.save_field_map(output_file)
    
    print(f"Field map generated: {output_file}")
    print(f"Fields tracked: {len(field_map)}")
    
    return field_map


def example_rosetta_stone():
    """Example: Build comprehensive field mapping"""
    
    setup_logging(log_level='INFO')
    
    client_name = "example_client"
    raw_dir = get_client_raw_dir(client_name)
    analyzed_dir = get_client_analyzed_dir(client_name)
    
    # Build Rosetta Stone
    print("Building Rosetta Stone...")
    builder = RosettaStoneBuilder(client_name, raw_dir, analyzed_dir)
    rosetta = builder.build_rosetta_stone()
    
    # Save results
    output_file = builder.save_rosetta_stone()
    
    print(f"Rosetta Stone saved: {output_file}")
    print(f"Modules: {rosetta['summary']['total_modules']}")
    print(f"Fields: {rosetta['summary']['total_fields']}")
    print(f"Transformations: {rosetta['summary']['total_transformations']}")
    
    return rosetta


def example_search_field():
    """Example: Search for a specific field"""
    
    from src.utils.file_helpers import load_json
    
    client_name = "example_client"
    analyzed_dir = get_client_analyzed_dir(client_name)
    
    # Load Rosetta Stone
    rosetta_file = analyzed_dir / 'rosetta_stone.json'
    rosetta = load_json(rosetta_file)
    
    # Search for a field
    field_name = "Email"
    
    if field_name in rosetta['fields']:
        field_info = rosetta['fields'][field_name]
        
        print(f"\nField: {field_info['label']}")
        print(f"API Name: {field_info['api_name']}")
        print(f"Module: {field_info['module']}")
        print(f"Data Type: {field_info['data_type']}")
        print(f"\nTransformations:")
        print(f"  Functions: {len(field_info['transformations']['functions'])}")
        print(f"  Workflows: {len(field_info['transformations']['workflows'])}")
        print(f"  Total: {field_info['transformations']['total_count']}")
        
        # Show functions that use this field
        if field_info['transformations']['functions']:
            print(f"\nFunctions using {field_name}:")
            for func in field_info['transformations']['functions']:
                print(f"  - {func['source']}")
    else:
        print(f"Field '{field_name}' not found")


def example_list_all_fields():
    """Example: List all fields and their usage count"""
    
    from src.utils.file_helpers import load_json
    
    client_name = "example_client"
    analyzed_dir = get_client_analyzed_dir(client_name)
    
    # Load Rosetta Stone
    rosetta_file = analyzed_dir / 'rosetta_stone.json'
    rosetta = load_json(rosetta_file)
    
    # Get all fields sorted by transformation count
    fields = rosetta['fields']
    sorted_fields = sorted(
        fields.items(),
        key=lambda x: x[1]['transformations']['total_count'],
        reverse=True
    )
    
    print("\nTop 10 Most Modified Fields:")
    print("-" * 60)
    
    for i, (field_name, field_info) in enumerate(sorted_fields[:10], 1):
        count = field_info['transformations']['total_count']
        module = field_info['module']
        print(f"{i:2d}. {field_name:20s} ({module:15s}) - {count} modifications")


def example_find_unused_fields():
    """Example: Find fields that are never modified"""
    
    from src.utils.file_helpers import load_json
    
    client_name = "example_client"
    analyzed_dir = get_client_analyzed_dir(client_name)
    
    # Load Rosetta Stone
    rosetta_file = analyzed_dir / 'rosetta_stone.json'
    rosetta = load_json(rosetta_file)
    
    # Find unused fields
    unused = [
        (name, info) 
        for name, info in rosetta['fields'].items()
        if info['transformations']['total_count'] == 0
    ]
    
    print(f"\nUnused Fields: {len(unused)}")
    print("-" * 60)
    
    for field_name, field_info in unused[:20]:  # Show first 20
        print(f"  {field_name} ({field_info['module']})")
    
    if len(unused) > 20:
        print(f"  ... and {len(unused) - 20} more")


if __name__ == '__main__':
    print("Zoho Field Analyzer - Example Usage")
    print("=" * 60)
    print()
    print("This file demonstrates programmatic usage.")
    print("See QUICKSTART.md for CLI usage.")
    print()
    print("Uncomment the examples you want to run:")
    print()
    
    # Uncomment to run examples:
    
    # 1. Basic extraction
    # example_basic_extraction()
    
    # 2. Field analysis
    # example_field_analysis()
    
    # 3. Build Rosetta Stone
    # example_rosetta_stone()
    
    # 4. Search for a field
    # example_search_field()
    
    # 5. List all fields
    # example_list_all_fields()
    
    # 6. Find unused fields
    # example_find_unused_fields()
    
    print("Update this file with your credentials and uncomment examples to run.")
