"""
Blueprints Extractor
Extracts blueprint configurations and transition logic from Zoho CRM
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

from .base import BaseExtractor
from ..api.zoho_client import ZohoAPIClient

logger = logging.getLogger(__name__)


class BlueprintsExtractor(BaseExtractor):
    """Extract blueprints from Zoho CRM"""
    
    def __init__(self, client: ZohoAPIClient, output_dir: Path, client_name: str,
                 org_id: str, blueprint_id: Optional[str] = None, 
                 module: Optional[str] = None, with_transitions: bool = False):
        """
        Initialize blueprints extractor
        
        Args:
            client: Zoho API client
            output_dir: Output directory
            client_name: Client name
            org_id: Zoho organization ID
            blueprint_id: Optional specific blueprint ID to extract
            module: Optional module name (required if blueprint_id provided)
            with_transitions: Whether to extract detailed transition information
        """
        super().__init__(client, output_dir, client_name)
        self.blueprints_dir = output_dir / 'blueprints'
        self.blueprints_dir.mkdir(exist_ok=True)
        self.transitions_dir = self.blueprints_dir / 'transitions'
        self.transitions_dir.mkdir(exist_ok=True)
        self.org_id = org_id
        self.blueprint_id = blueprint_id
        self.module = module
        self.with_transitions = with_transitions
    
    def get_extractor_name(self) -> str:
        return "blueprints"
    
    def get_all_blueprints(self) -> List[Dict[str, Any]]:
        """
        Get list of all blueprints
        
        Returns:
            List of blueprint metadata
        """
        logger.info("Fetching all blueprints...")
        
        # Use the ProcessFlow.do endpoint with showAllProcesses action
        url = f"https://crm.zoho.com/crm/org{self.org_id}/ProcessFlow.do"
        params = {
            'pageTitle': 'crm.label.process.automation',
            'allowMultiClick': 'true',
            'action': 'showAllProcesses',
            'isFromBack': 'true',
            'module': 'All'
        }
        
        try:
            response = self.client.session.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                blueprints = data.get('Processes', [])
                logger.info(f"Found {len(blueprints)} total blueprints")
                return blueprints
            else:
                logger.error(f"Error getting blueprints: {response.status_code}")
                logger.error(response.text[:500])
                return []
                
        except Exception as e:
            logger.error(f"Exception getting blueprints: {e}")
            return []
    
    def get_blueprint_details(self, blueprint_id: str, module: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed blueprint configuration including transitions
        
        Args:
            blueprint_id: Blueprint/process ID
            module: Module name (e.g., 'Potentials', 'Accounts')
            
        Returns:
            Blueprint details or None
        """
        url = f"https://crm.zoho.com/crm/org{self.org_id}/ProcessFlow.do"
        params = {
            'action': 'getProcessDetails',
            'module': module,
            'processId': blueprint_id,
            'toolTip': module,
            'isFromBack': 'true'
        }
        
        try:
            response = self.client.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error getting blueprint {blueprint_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Exception getting blueprint {blueprint_id}: {e}")
            return None
    
    def get_transition_details(self, transition_id: str, module: str, 
                               layout_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific transition
        
        Args:
            transition_id: Transition ID
            module: Module name
            layout_id: Layout ID
            
        Returns:
            Transition details or None
        """
        url = f"https://crm.zoho.com/crm/org{self.org_id}/FlowTransition.do"
        params = {
            'Module': module,
            'action': 'getTransitionDetails',
            'TransitionId': transition_id,
            'LayoutId': layout_id
        }
        
        try:
            response = self.client.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error getting transition {transition_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"Exception getting transition {transition_id}: {e}")
            return None
    
    def extract_field_updates_from_transition(self, transition_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract field updates from transition details
        
        Args:
            transition_details: Full transition details response
            
        Returns:
            List of field updates with labels and values
        """
        field_updates = []
        
        # Get field label mappings
        field_vs_label = transition_details.get('FieldVsLabel', {})
        
        # Get field update actions
        actions = transition_details.get('Actions', {})
        field_update_actions = actions.get('Fieldupdate', [])
        
        for update in field_update_actions:
            field_label = update.get('fieldLabel')
            field_value = update.get('fieldValue')
            
            if field_label:
                field_updates.append({
                    'field_label': field_label,
                    'field_value': field_value,
                    'field_id': update.get('fieldId')  # If available
                })
        
        return field_updates
    
    def process_blueprint_transitions(self, blueprint_data: Dict[str, Any], 
                                     module: str, layout_id: str,
                                     blueprint_id: str) -> Dict[str, Any]:
        """
        Process all transitions for a blueprint and extract field updates
        
        Args:
            blueprint_data: Blueprint details from getProcessDetails
            module: Module name
            layout_id: Layout ID
            blueprint_id: Blueprint ID (for logging)
            
        Returns:
            Updated blueprint data with transition details
        """
        import time
        
        transitions_meta = blueprint_data.get('TransitionsMeta', [])
        
        if not transitions_meta:
            logger.info(f"  No transitions found in blueprint")
            return blueprint_data
        
        logger.info(f"  Processing {len(transitions_meta)} transitions...")
        
        enriched_transitions = []
        total_field_updates = 0
        
        for i, transition in enumerate(transitions_meta, 1):
            transition_id = transition.get('TransitionId')
            transition_name = transition.get('Name', 'Unnamed')
            
            if not transition_id:
                logger.warning(f"    [{i}/{len(transitions_meta)}] {transition_name} - No transition ID, skipping")
                enriched_transitions.append(transition)
                continue
            
            logger.info(f"    [{i}/{len(transitions_meta)}] {transition_name} (ID: {transition_id})")
            
            # Get transition details
            transition_details = self.get_transition_details(transition_id, module, layout_id)
            
            if transition_details:
                # Save raw transition details
                transition_filename = f"{self.sanitize_filename(transition_name)}_{transition_id}.json"
                transition_filepath = self.transitions_dir / f"{blueprint_id}_{transition_filename}"
                self.save_json(transition_details, f"blueprints/transitions/{blueprint_id}_{transition_filename}")
                
                # Extract field updates
                field_updates = self.extract_field_updates_from_transition(transition_details)
                
                # Add to transition metadata
                enriched_transition = {
                    **transition,
                    'transition_details_file': str(transition_filepath.name),
                    'field_updates': field_updates,
                    'field_update_count': len(field_updates)
                }
                
                enriched_transitions.append(enriched_transition)
                total_field_updates += len(field_updates)
                
                logger.info(f"      [OK] {len(field_updates)} field updates found")
            else:
                logger.warning(f"      [FAIL] Could not get transition details")
                enriched_transitions.append(transition)
            
            # Rate limiting - delay between transition requests
            if i < len(transitions_meta):
                time.sleep(0.75)  # 750ms delay between requests
        
        # Update blueprint data with enriched transitions
        blueprint_data['TransitionsMeta'] = enriched_transitions
        blueprint_data['transition_summary'] = {
            'total_transitions': len(transitions_meta),
            'total_field_updates': total_field_updates
        }
        
        logger.info(f"  [OK] Processed {len(transitions_meta)} transitions, {total_field_updates} total field updates")
        
        return blueprint_data
    
    def extract_single_blueprint(self, blueprint_id: str, module: str) -> Dict[str, Any]:
        """
        Extract a single specific blueprint
        
        Args:
            blueprint_id: Blueprint ID to extract
            module: Module name
            
        Returns:
            Extraction results
        """
        logger.info(f"Extracting single blueprint: {blueprint_id} ({module})")
        
        self.stats['total'] = 1
        
        details = self.get_blueprint_details(blueprint_id, module)
        
        if details:
            # If with_transitions, process transition details
            if self.with_transitions:
                logger.info("  Extracting transition details...")
                layout_id = details.get('Layout', {}).get('Id', '')
                if layout_id:
                    details = self.process_blueprint_transitions(details, module, layout_id, blueprint_id)
                else:
                    logger.warning("  No layout ID found, skipping transitions")
            
            # Save blueprint details
            filename = f"{self.sanitize_filename(module)}_{blueprint_id}.json"
            self.save_json(details, f"blueprints/{filename}")
            
            self.stats['successful'] = 1
            logger.info(f"[OK] Saved blueprint {blueprint_id}")
            
            return {
                'status': 'success',
                'stats': self.stats,
                'blueprint': {
                    'id': blueprint_id,
                    'module': module,
                    'filename': filename,
                    'details': details
                }
            }
        else:
            self.stats['failed'] = 1
            logger.error(f"[FAIL] Failed to get blueprint {blueprint_id}")
            
            return {
                'status': 'failed',
                'stats': self.stats,
                'error': 'Could not retrieve blueprint details'
            }
    
    def extract(self) -> Dict[str, Any]:
        """
        Extract all blueprints or a single blueprint
        
        Returns:
            Extraction results
        """
        # If specific blueprint ID provided, extract just that one
        if self.blueprint_id:
            if not self.module:
                logger.error("Module name required when extracting specific blueprint")
                return {
                    'status': 'error',
                    'error': 'Module name required with blueprint_id',
                    'stats': self.stats
                }
            
            return self.extract_single_blueprint(self.blueprint_id, self.module)
        
        # Otherwise, extract all blueprints
        blueprints = self.get_all_blueprints()
        self.stats['total'] = len(blueprints)
        
        if not blueprints:
            logger.warning("No blueprints found!")
            return {
                'status': 'no_data',
                'stats': self.stats
            }
        
        failed_items = []
        all_blueprints_data = []
        
        for i, blueprint in enumerate(blueprints, 1):
            blueprint_id = blueprint.get('Id')
            blueprint_name = blueprint.get('Name', f'blueprint_{blueprint_id}')
            module_name = blueprint.get('Tab', {}).get('Name', 'Unknown')
            status = blueprint.get('ProcessStatus', 'Unknown')
            
            logger.info(f"[{i}/{len(blueprints)}] Extracting: {blueprint_name} ({module_name}) - {status}")
            
            try:
                # Get detailed blueprint data
                details = self.get_blueprint_details(blueprint_id, module_name)
                
                if details:
                    # If with_transitions, process transition details
                    if self.with_transitions:
                        logger.info("  Extracting transition details...")
                        layout_id = blueprint.get('Layout', {}).get('Id', '')
                        if layout_id:
                            details = self.process_blueprint_transitions(
                                details, module_name, layout_id, blueprint_id
                            )
                        else:
                            logger.warning("  No layout ID found, skipping transitions")
                    
                    # Combine metadata with details
                    full_data = {
                        'metadata': blueprint,
                        'details': details
                    }
                    
                    # Save blueprint data
                    filename = f"{self.sanitize_filename(blueprint_name)}_{blueprint_id}.json"
                    self.save_json(full_data, f"blueprints/{filename}")
                    
                    all_blueprints_data.append({
                        'id': blueprint_id,
                        'name': blueprint_name,
                        'module': module_name,
                        'status': status,
                        'filename': filename
                    })
                    
                    self.stats['successful'] += 1
                    logger.info(f"  [OK] Saved")
                else:
                    reason = "No details in response"
                    logger.warning(f"  [FAIL] {reason}")
                    failed_items.append({
                        'name': blueprint_name,
                        'id': blueprint_id,
                        'module': module_name,
                        'reason': reason
                    })
                    self.stats['failed'] += 1
                    
            except Exception as e:
                reason = str(e)
                logger.error(f"  [FAIL] {reason}")
                failed_items.append({
                    'name': blueprint_name,
                    'id': blueprint_id,
                    'module': module_name,
                    'reason': reason
                })
                self.stats['failed'] += 1
        
        # Save master index
        self.save_json(all_blueprints_data, 'blueprints_index.json')
        
        # Save failed log
        if failed_items:
            self.save_failed_log(failed_items)
        
        return {
            'status': 'success',
            'stats': self.stats,
            'blueprints': all_blueprints_data,
            'failed': failed_items
        }
