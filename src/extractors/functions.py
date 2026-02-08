"""
Deluge Functions Extractor
Extracts all Deluge functions from Zoho CRM
"""
from pathlib import Path
from typing import Dict, Any, List
import logging

from .base import BaseExtractor
from ..api.zoho_client import ZohoAPIClient

logger = logging.getLogger(__name__)


class FunctionsExtractor(BaseExtractor):
    """Extract Deluge functions from Zoho CRM"""
    
    def __init__(self, client: ZohoAPIClient, output_dir: Path, client_name: str):
        super().__init__(client, output_dir, client_name)
        self.functions_dir = output_dir / 'functions'
        self.functions_dir.mkdir(exist_ok=True)
    
    def get_extractor_name(self) -> str:
        return "functions"
    
    def get_all_functions(self) -> List[Dict[str, Any]]:
        """
        Get list of all functions using pagination
        
        Returns:
            List of function metadata
        """
        logger.info("Fetching all functions...")
        
        functions = self.client.paginated_get(
            endpoint='settings/functions',
            start_param='start',
            limit=50
        )
        
        logger.info(f"Found {len(functions)} total functions")
        return functions
    
    def get_function_source(self, function_id: str) -> Dict[str, Any]:
        """
        Get source code for a specific function
        
        Args:
            function_id: Function ID
            
        Returns:
            Function source data
        """
        endpoint = f'settings/functions/{function_id}'
        params = {
            'category': 'standalone',
            'source': 'crm',
            'language': 'deluge'
        }
        
        return self.client.get(endpoint, params=params)
    
    def extract_script_from_response(self, response: Dict[str, Any]) -> str:
        """
        Extract script content from API response
        
        Args:
            response: API response
            
        Returns:
            Script content or empty string
        """
        # Handle nested structure: {'functions': [{'script': '...'}]}
        if response and 'functions' in response and len(response['functions']) > 0:
            func_detail = response['functions'][0]
            return func_detail.get('script', '')
        return ''
    
    def extract(self) -> Dict[str, Any]:
        """
        Extract all Deluge functions and save to files
        
        Returns:
            Extraction results
        """
        # Get all functions
        functions = self.get_all_functions()
        self.stats['total'] = len(functions)
        
        if not functions:
            logger.warning("No functions found!")
            return {
                'status': 'no_data',
                'stats': self.stats
            }
        
        # Extract each function's source
        failed_items = []
        all_functions_data = []
        
        for i, func in enumerate(functions, 1):
            func_id = func['id']
            func_name = func.get('display_name', f'function_{func_id}')
            
            logger.info(f"[{i}/{len(functions)}] Extracting: {func_name}")
            
            try:
                # Get source code
                source_data = self.get_function_source(func_id)
                script = self.extract_script_from_response(source_data)
                
                if script:
                    # Create metadata header
                    header = self.create_metadata_header(
                        func,
                        id_field='id',
                        name_field='display_name'
                    )
                    
                    # Combine header and script
                    full_content = header + script
                    
                    # Save to individual file
                    filename = f"{self.sanitize_filename(func_name)}_{func_id}.txt"
                    self.save_text(full_content, f"functions/{filename}")
                    
                    # Add to collection
                    all_functions_data.append({
                        'metadata': func,
                        'script': script,
                        'filename': filename
                    })
                    
                    self.stats['successful'] += 1
                    logger.info(f"  ✓ Saved")
                    
                else:
                    reason = "No script in response"
                    logger.warning(f"  ✗ {reason}")
                    failed_items.append({
                        'name': func_name,
                        'id': func_id,
                        'reason': reason
                    })
                    self.stats['failed'] += 1
                    
            except Exception as e:
                reason = str(e)
                logger.error(f"  ✗ {reason}")
                failed_items.append({
                    'name': func_name,
                    'id': func_id,
                    'reason': reason
                })
                self.stats['failed'] += 1
        
        # Save master index
        self.save_json(all_functions_data, 'functions_index.json')
        
        # Save failed log if any
        if failed_items:
            self.save_failed_log(failed_items)
        
        return {
            'status': 'success',
            'stats': self.stats,
            'functions': all_functions_data,
            'failed': failed_items
        }


def main():
    """Standalone execution for testing"""
    import sys
    from ..utils.logging_config import setup_logging
    
    setup_logging()
    
    # This would normally come from config
    print("This extractor should be run through the main extraction script")
    print("Usage: python -m src.extractors.main --client CLIENT_NAME --extract functions")
    sys.exit(1)


if __name__ == '__main__':
    main()
