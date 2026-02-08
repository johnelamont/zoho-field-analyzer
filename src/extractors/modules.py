"""
Modules Extractor
Extracts module metadata, fields, and layouts from Zoho CRM
"""
from pathlib import Path
from typing import Dict, Any, List
import logging

from .base import BaseExtractor
from ..api.zoho_client import ZohoAPIClient

logger = logging.getLogger(__name__)


class ModulesExtractor(BaseExtractor):
    """Extract module metadata from Zoho CRM"""
    
    def __init__(self, client: ZohoAPIClient, output_dir: Path, client_name: str):
        super().__init__(client, output_dir, client_name)
        self.modules_dir = output_dir / 'modules'
        self.modules_dir.mkdir(exist_ok=True)
    
    def get_extractor_name(self) -> str:
        return "modules"
    
    def get_all_modules(self) -> List[Dict[str, Any]]:
        """
        Get list of all modules
        
        Returns:
            List of module metadata
        """
        logger.info("Fetching all modules...")
        
        # Use v6 endpoint with proper parameters
        url = "https://crm.zoho.com/crm/v6/settings/modules"
        params = {
            'include': 'team_spaces',
            'status': 'user_hidden,system_hidden,scheduled_for_deletion,visible'
        }
        
        try:
            response = self.client.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                modules = data.get('modules', [])
                logger.info(f"Found {len(modules)} modules")
                return modules
            else:
                logger.error(f"Error getting modules: {response.status_code}")
                logger.error(response.text[:500])
                return []
                
        except Exception as e:
            logger.error(f"Exception getting modules: {e}")
            return []
    
    def get_module_fields(self, module_api_name: str) -> Dict[str, Any]:
        """
        Get field definitions for a module
        
        Args:
            module_api_name: API name of the module
            
        Returns:
            Field definitions response
        """
        # Use v2.2 endpoint with full parameters
        url = "https://crm.zoho.com/crm/v2.2/settings/fields"
        params = {
            'module': module_api_name,
            'type': 'all',
            'skip_field_permission': 'true',
            'api_name_page': 'true'
        }
        
        try:
            response = self.client.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error getting fields for {module_api_name}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"Exception getting fields for {module_api_name}: {e}")
            return None
    
    def extract(self) -> Dict[str, Any]:
        """
        Extract all module metadata and fields
        
        Returns:
            Extraction results
        """
        # Get all modules
        all_modules = self.get_all_modules()
        
        if not all_modules:
            logger.warning("No modules found!")
            return {
                'status': 'no_data',
                'stats': self.stats
            }
        
        # Filter to only modules that support fields
        # Criteria:
        # 1. api_supported: True (has API access)
        # 2. status: visible (not hidden/system modules)
        # 3. api_name does NOT end with __s (excludes system modules like Functions__s, Insights__s)
        # 4. creatable: True (excludes read-only system modules like Approvals)
        # 5. show_as_tab: True (shown in navigation, excludes Consents and other utility modules)
        modules = [
            m for m in all_modules 
            if m.get('api_supported', False) 
            and m.get('status') == 'visible'
            and not m.get('api_name', '').endswith('__s')
            and m.get('creatable', False)
            and m.get('show_as_tab', False)
        ]
        
        logger.info(f"Filtered to {len(modules)} modules with field support (from {len(all_modules)} total)")
        
        self.stats['total'] = len(modules)
        
        failed_items = []
        all_modules_data = []
        
        # Save master modules list (all modules, not just filtered)
        self.save_json({'modules': all_modules}, 'all_modules.json')
        logger.info("Saved master modules list")
        
        for i, module in enumerate(modules, 1):
            module_name = module.get('module_name', f'module_{i}')
            module_api_name = module.get('api_name', module_name)
            module_status = module.get('status', 'unknown')
            
            logger.info(f"[{i}/{len(modules)}] Extracting: {module_name} ({module_api_name}) - {module_status}")
            
            try:
                # Get field definitions
                fields_data = self.get_module_fields(module_api_name)
                
                if fields_data:
                    # Combine module metadata with fields
                    full_data = {
                        'metadata': module,
                        'fields': fields_data
                    }
                    
                    # Save module data
                    filename = f"{self.sanitize_filename(module_api_name)}.json"
                    self.save_json(full_data, f"modules/{filename}")
                    
                    # Count fields for summary
                    field_count = len(fields_data.get('fields', []))
                    
                    all_modules_data.append({
                        'module_name': module_name,
                        'api_name': module_api_name,
                        'status': module_status,
                        'field_count': field_count,
                        'filename': filename
                    })
                    
                    self.stats['successful'] += 1
                    logger.info(f"  [OK] Saved ({field_count} fields)")
                    
                else:
                    reason = "No fields data returned"
                    logger.warning(f"  [FAIL] {reason}")
                    failed_items.append({
                        'name': module_name,
                        'id': module_api_name,
                        'reason': reason
                    })
                    self.stats['failed'] += 1
                
            except Exception as e:
                reason = str(e)
                logger.error(f"  [FAIL] {reason}")
                failed_items.append({
                    'name': module_name,
                    'id': module_api_name,
                    'reason': reason
                })
                self.stats['failed'] += 1
        
        # Save master index
        self.save_json(all_modules_data, 'modules_index.json')
        
        # Save failed log
        if failed_items:
            self.save_failed_log(failed_items)
        
        return {
            'status': 'success',
            'stats': self.stats,
            'modules': all_modules_data,
            'failed': failed_items
        }
