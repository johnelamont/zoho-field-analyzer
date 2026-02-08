"""
Rosetta Stone Builder
Creates comprehensive field transformation mapping
"""
from pathlib import Path
from typing import Dict, Any
import logging
import json

from ..utils.file_helpers import load_json, save_json
from .field_tracker import FieldTracker

logger = logging.getLogger(__name__)


class RosettaStoneBuilder:
    """
    Build the comprehensive 'Rosetta Stone' of field transformations
    """
    
    def __init__(self, client_name: str, raw_data_dir: Path, analyzed_dir: Path):
        """
        Initialize Rosetta Stone builder
        
        Args:
            client_name: Name of the client
            raw_data_dir: Directory with raw extracted data
            analyzed_dir: Directory to save analyzed data
        """
        self.client_name = client_name
        self.raw_data_dir = raw_data_dir
        self.analyzed_dir = analyzed_dir
        self.rosetta_stone = {}
        
    def load_field_map(self) -> Dict[str, Any]:
        """
        Load field map from field tracker
        
        Returns:
            Field map dictionary
        """
        field_map_file = self.analyzed_dir / 'field_map.json'
        
        if not field_map_file.exists():
            logger.info("Field map not found, generating...")
            tracker = FieldTracker(self.client_name, self.raw_data_dir)
            field_map = tracker.build_field_map()
            tracker.save_field_map(field_map_file)
        else:
            logger.info(f"Loading field map from: {field_map_file}")
            field_map = load_json(field_map_file)
        
        return field_map
    
    def load_modules(self) -> Dict[str, Any]:
        """
        Load module metadata and field definitions
        
        Returns:
            Modules dictionary
        """
        modules_index = self.raw_data_dir / 'modules_index.json'
        
        if not modules_index.exists():
            logger.warning("Modules index not found")
            return {}
        
        modules_data = load_json(modules_index)
        
        # Load detailed module data
        modules = {}
        for module_info in modules_data:
            module_file = self.raw_data_dir / 'modules' / module_info['filename']
            if module_file.exists():
                module_data = load_json(module_file)
                modules[module_info['api_name']] = module_data
        
        return modules
    
    def build_rosetta_stone(self) -> Dict[str, Any]:
        """
        Build the complete Rosetta Stone
        
        Returns:
            Rosetta Stone dictionary
        """
        logger.info("Building Rosetta Stone...")
        
        # Load all data sources
        field_map = self.load_field_map()
        modules = self.load_modules()
        
        # Build comprehensive mapping
        rosetta_stone = {
            'client': self.client_name,
            'generated_at': None,  # TODO: Add timestamp
            'summary': {
                'total_fields': 0,
                'total_modules': len(modules),
                'total_transformations': 0
            },
            'modules': {},
            'fields': {}
        }
        
        # Process each module
        for module_name, module_data in modules.items():
            fields_data = module_data.get('fields', {})
            
            if 'fields' in fields_data:
                module_fields = fields_data['fields']
                
                rosetta_stone['modules'][module_name] = {
                    'display_name': module_data.get('metadata', {}).get('module_name', module_name),
                    'fields': {}
                }
                
                # Process each field in the module
                for field in module_fields:
                    field_name = field.get('api_name', field.get('field_label', ''))
                    
                    if not field_name:
                        continue
                    
                    # Get transformation info from field map
                    transformations = field_map.get(field_name, {})
                    
                    field_info = {
                        'api_name': field_name,
                        'label': field.get('field_label', field_name),
                        'data_type': field.get('data_type', 'unknown'),
                        'module': module_name,
                        'transformations': {
                            'functions': transformations.get('referenced_in_functions', []),
                            'workflows': transformations.get('updated_in_workflows', []),
                            'total_count': transformations.get('total_references', 0)
                        }
                    }
                    
                    # Add to module
                    rosetta_stone['modules'][module_name]['fields'][field_name] = field_info
                    
                    # Add to global field index
                    rosetta_stone['fields'][field_name] = field_info
                    
                    rosetta_stone['summary']['total_fields'] += 1
                    rosetta_stone['summary']['total_transformations'] += field_info['transformations']['total_count']
        
        self.rosetta_stone = rosetta_stone
        
        logger.info(f"Rosetta Stone built:")
        logger.info(f"  Modules: {rosetta_stone['summary']['total_modules']}")
        logger.info(f"  Fields: {rosetta_stone['summary']['total_fields']}")
        logger.info(f"  Transformations: {rosetta_stone['summary']['total_transformations']}")
        
        return rosetta_stone
    
    def save_rosetta_stone(self, output_file: Path = None) -> Path:
        """
        Save Rosetta Stone to file
        
        Args:
            output_file: Optional output file path
            
        Returns:
            Path to saved file
        """
        if not self.rosetta_stone:
            logger.warning("Rosetta Stone is empty, run build_rosetta_stone() first")
            return None
        
        if output_file is None:
            output_file = self.analyzed_dir / 'rosetta_stone.json'
        
        save_json(self.rosetta_stone, output_file)
        logger.info(f"Saved Rosetta Stone to: {output_file}")
        
        return output_file
    
    def generate_html_report(self, output_file: Path = None) -> Path:
        """
        Generate HTML report of the Rosetta Stone
        
        Args:
            output_file: Optional output file path
            
        Returns:
            Path to saved file
        """
        # TODO: Implement HTML report generation
        logger.info("HTML report generation not yet implemented")
        return None


def main():
    """Standalone execution"""
    import argparse
    from ..utils.logging_config import setup_logging
    from ..utils.file_helpers import get_client_raw_dir, get_client_analyzed_dir
    
    parser = argparse.ArgumentParser(description='Build Rosetta Stone field mapping')
    parser.add_argument('--client', required=True, help='Client name')
    parser.add_argument('--report', choices=['json', 'html'], default='json',
                       help='Report format')
    args = parser.parse_args()
    
    setup_logging(log_level='INFO')
    
    # Get directories
    raw_dir = get_client_raw_dir(args.client)
    analyzed_dir = get_client_analyzed_dir(args.client)
    
    # Build Rosetta Stone
    builder = RosettaStoneBuilder(args.client, raw_dir, analyzed_dir)
    rosetta = builder.build_rosetta_stone()
    
    # Save results
    if args.report == 'json':
        output_file = builder.save_rosetta_stone()
        print(f"\nRosetta Stone saved: {output_file}")
    elif args.report == 'html':
        output_file = builder.generate_html_report()
        if output_file:
            print(f"\nHTML report saved: {output_file}")
        else:
            print("\nHTML report generation not yet available")
    
    # Print summary
    print(f"\nSummary:")
    print(f"  Total modules: {rosetta['summary']['total_modules']}")
    print(f"  Total fields: {rosetta['summary']['total_fields']}")
    print(f"  Total transformations: {rosetta['summary']['total_transformations']}")


if __name__ == '__main__':
    main()
