"""
Field Tracker Analyzer
Tracks where and how fields are read, modified, and validated
"""
from pathlib import Path
from typing import Dict, Any, List, Set
import logging
import re

from ..utils.file_helpers import load_json, save_json

logger = logging.getLogger(__name__)


class FieldTracker:
    """
    Analyze extracted data to track field usage
    """
    
    def __init__(self, client_name: str, raw_data_dir: Path):
        """
        Initialize field tracker
        
        Args:
            client_name: Name of the client
            raw_data_dir: Directory containing raw extracted data
        """
        self.client_name = client_name
        self.raw_data_dir = raw_data_dir
        self.field_map = {}
        
    def analyze_functions(self) -> Dict[str, Any]:
        """
        Analyze Deluge functions for field references
        
        Returns:
            Dictionary mapping fields to functions that use them
        """
        logger.info("Analyzing functions for field references...")
        
        functions_dir = self.raw_data_dir / 'functions'
        
        if not functions_dir.exists():
            logger.warning("Functions directory not found")
            return {}
        
        field_references = {}
        
        # Load function files
        for func_file in functions_dir.glob('*.txt'):
            with open(func_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract field references (basic regex patterns)
            # Pattern 1: record.FieldName
            # Pattern 2: get("FieldName")
            # Pattern 3: set("FieldName", value)
            
            patterns = [
                r'\brecord\.(\w+)',
                r'get\(["\'](\w+)["\']\)',
                r'set\(["\'](\w+)["\']',
                r'\.(\w+)\s*=',  # Assignment
            ]
            
            fields_found = set()
            
            for pattern in patterns:
                matches = re.findall(pattern, content)
                fields_found.update(matches)
            
            # Store references
            for field in fields_found:
                if field not in field_references:
                    field_references[field] = []
                
                field_references[field].append({
                    'type': 'function',
                    'source': func_file.stem,
                    'file': str(func_file)
                })
        
        logger.info(f"Found {len(field_references)} fields referenced in functions")
        return field_references
    
    def analyze_workflows(self) -> Dict[str, Any]:
        """
        Analyze workflows for field updates
        
        Returns:
            Dictionary mapping fields to workflows that modify them
        """
        logger.info("Analyzing workflows for field updates...")
        
        workflows_dir = self.raw_data_dir / 'workflows'
        
        if not workflows_dir.exists():
            logger.warning("Workflows directory not found")
            return {}
        
        field_updates = {}
        
        # TODO: Implement workflow analysis
        # Need to parse workflow JSON and extract:
        # - Field updates
        # - Conditions that reference fields
        # - Email templates that reference fields
        
        return field_updates
    
    def build_field_map(self) -> Dict[str, Any]:
        """
        Build comprehensive field map from all sources
        
        Returns:
            Complete field map
        """
        logger.info("Building comprehensive field map...")
        
        # Analyze all sources
        function_refs = self.analyze_functions()
        workflow_refs = self.analyze_workflows()
        
        # Combine all references
        all_fields = set(function_refs.keys()) | set(workflow_refs.keys())
        
        field_map = {}
        
        for field in all_fields:
            field_map[field] = {
                'field_name': field,
                'referenced_in_functions': function_refs.get(field, []),
                'updated_in_workflows': workflow_refs.get(field, []),
                'total_references': (
                    len(function_refs.get(field, [])) + 
                    len(workflow_refs.get(field, []))
                )
            }
        
        self.field_map = field_map
        
        logger.info(f"Built field map with {len(field_map)} fields")
        return field_map
    
    def save_field_map(self, output_file: Path) -> None:
        """
        Save field map to JSON file
        
        Args:
            output_file: Path to output file
        """
        if not self.field_map:
            logger.warning("Field map is empty, run build_field_map() first")
            return
        
        save_json(self.field_map, output_file)
        logger.info(f"Saved field map to: {output_file}")


def main():
    """Standalone execution"""
    import argparse
    from ..utils.logging_config import setup_logging
    from ..utils.file_helpers import get_client_raw_dir, get_client_analyzed_dir
    
    parser = argparse.ArgumentParser(description='Track field usage across Zoho CRM')
    parser.add_argument('--client', required=True, help='Client name')
    args = parser.parse_args()
    
    setup_logging(log_level='INFO')
    
    # Get directories
    raw_dir = get_client_raw_dir(args.client)
    analyzed_dir = get_client_analyzed_dir(args.client)
    
    # Run analysis
    tracker = FieldTracker(args.client, raw_dir)
    field_map = tracker.build_field_map()
    
    # Save results
    output_file = analyzed_dir / 'field_map.json'
    tracker.save_field_map(output_file)
    
    print(f"\nField map generated: {output_file}")
    print(f"Total fields tracked: {len(field_map)}")


if __name__ == '__main__':
    main()
