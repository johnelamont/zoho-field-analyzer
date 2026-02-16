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
                 module: Optional[str] = None, with_transitions: bool = False,
                 rate_limit_config: Optional[Dict[str, Any]] = None):
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
            rate_limit_config: Rate limiting configuration from YAML
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
        
        # Rate limiting configuration
        self.rate_limit_config = rate_limit_config or {}
        self.base_delay = self.rate_limit_config.get('base_delay', 4.0)
        cooldown_config = self.rate_limit_config.get('cooldown', {})
        self.cooldown_enabled = cooldown_config.get('enabled', True)
        self.cooldown_after = cooldown_config.get('after_requests', 76)
        self.cooldown_duration = cooldown_config.get('duration', 180)  # 3 minutes default
    
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
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response content-type: {response.headers.get('Content-Type', 'unknown')}")
            
            if response.status_code == 200:
                # Check if we got HTML instead of JSON (credentials issue)
                content_type = response.headers.get('Content-Type', '')
                if 'html' in content_type.lower():
                    logger.error("Got HTML response instead of JSON - credentials likely expired")
                    logger.error(f"Response preview: {response.text[:500]}")
                    return []
                
                try:
                    data = response.json()
                    blueprints = data.get('Processes', [])
                    logger.info(f"Found {len(blueprints)} total blueprints")
                    return blueprints
                except ValueError as json_err:
                    logger.error(f"JSON parsing failed: {json_err}")
                    logger.error(f"Response body: {response.text[:500]}")
                    return []
            else:
                logger.error(f"Error getting blueprints: {response.status_code}")
                logger.error(f"Response body: {response.text[:500]}")
                return []
                
        except Exception as e:
            logger.error(f"Exception getting blueprints: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
                # Check if we got HTML instead of JSON (rate limiting)
                content_type = response.headers.get('Content-Type', '')
                if 'html' in content_type.lower():
                    logger.warning(f"      Rate limited! Got HTML instead of JSON")
                    logger.warning(f"      Sleeping 5 seconds and retrying...")
                    import time
                    time.sleep(5)
                    # Retry once
                    response = self.client.session.get(url, params=params)
                    if response.status_code != 200:
                        logger.warning(f"      Retry failed: {response.status_code}")
                        return None
                
                try:
                    data = response.json()
                    if not data:
                        logger.warning(f"      Empty response for transition {transition_id}")
                        return None
                    return data
                except Exception as e:
                    logger.warning(f"      Could not parse JSON response: {e}")
                    return None
            else:
                logger.warning(f"      Error getting transition {transition_id}: {response.status_code}")
                # Only log first 200 chars to avoid HTML spam
                body_preview = response.text[:200] if response.text else "No body"
                logger.warning(f"      Response body: {body_preview}")
                
                # If 400 with HTML, likely rate limited
                if response.status_code == 400 and '<html>' in response.text.lower():
                    logger.warning(f"      Detected rate limiting (HTML error page)")
                
                return None
                
        except Exception as e:
            logger.warning(f"      Exception getting transition {transition_id}: {e}")
            import traceback
            logger.warning(traceback.format_exc())
            return None
    
    def extract_field_updates_from_transition(self, transition_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract field updates from transition details
        
        Args:
            transition_details: Full transition details response
            
        Returns:
            List of field updates with labels, IDs, and column names
        """
        field_updates = []
        
        try:
            # Get field mappings (note: FieldVsLable has typo in Zoho API)
            field_vs_label = transition_details.get('FieldVsLable', {})  # ID → Display Label
            field_vs_name = transition_details.get('FieldVsName', {})    # ID → Column Name
            
            # Get fields being updated in this transition
            fields = transition_details.get('Fields', [])
            
            # Process each field in the transition
            for field in fields:
                # Skip info messages (not actual fields)
                if field.get('Type') != 'Field':
                    continue
                
                field_id = field.get('Id')
                if not field_id:
                    continue
                
                # Get label and column name from mappings
                field_label = field_vs_label.get(field_id)
                column_name = field_vs_name.get(field_id)
                
                if field_label:  # Only include if we have a label
                    field_updates.append({
                        'field_id': field_id,
                        'field_label': field_label,
                        'column_name': column_name,  # POTENTIALCF201, etc.
                        'module': field.get('Module'),
                        'ui_type': field.get('uiType')
                    })
            
            # Also check legacy Actions.Fieldupdate for backwards compatibility
            actions = transition_details.get('Actions', {})
            if actions:
                field_update_actions = actions.get('Fieldupdate', [])
                
                for update in field_update_actions:
                    field_label = update.get('fieldLabel')
                    field_value = update.get('fieldValue')
                    
                    if field_label:
                        field_updates.append({
                            'field_label': field_label,
                            'field_value': field_value,
                            'field_id': update.get('fieldId'),
                            'source': 'legacy_action'  # Mark as from old structure
                        })
        
        except Exception as e:
            logger.error(f"Error extracting field updates: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
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
        current_delay = self.base_delay  # Use configured base delay
        rate_limit_hits = 0
        successful_requests = 0  # Track for cooldown
        
        # Log rate limiting settings
        if self.cooldown_enabled:
            logger.info(f"  Rate limiting: {self.base_delay}s delay, cooldown every {self.cooldown_after} requests ({self.cooldown_duration}s)")
        else:
            logger.info(f"  Rate limiting: {self.base_delay}s delay (cooldown disabled)")
        
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
                
                # Extract function calls from Actions.Deluge
                function_calls = []
                try:
                    actions = transition_details.get('Actions', {})
                    if actions:
                        deluge_functions = actions.get('Deluge', [])
                        
                        for func in deluge_functions:
                            function_calls.append({
                                'function_id': func.get('Id'),
                                'function_name': func.get('Name'),
                                'relation_type': func.get('relationType'),  # 0=after, 1=before
                                'description': func.get('description', '')
                            })
                except Exception as e:
                    logger.error(f"      Error extracting functions: {e}")
                
                # Add to transition metadata
                enriched_transition = {
                    **transition,
                    'transition_details_file': str(transition_filepath.name),
                    'field_updates': field_updates,
                    'field_update_count': len(field_updates),
                    'function_calls': function_calls,
                    'function_call_count': len(function_calls)
                }
                
                enriched_transitions.append(enriched_transition)
                total_field_updates += len(field_updates)
                successful_requests += 1  # Track successful requests for cooldown
                
                # Log what was found
                if len(field_updates) > 0 or len(function_calls) > 0:
                    parts = []
                    if len(field_updates) > 0:
                        parts.append(f"{len(field_updates)} field updates")
                    if len(function_calls) > 0:
                        parts.append(f"{len(function_calls)} function calls")
                    logger.info(f"      [OK] {', '.join(parts)}")
                else:
                    logger.info(f"      [OK] No field updates or functions")
            else:
                logger.warning(f"      [FAIL] Could not get transition details")
                # Check if this was likely a rate limit (happens around transition 77)
                if i >= 70:  # After ~70 transitions, be more careful
                    rate_limit_hits += 1
                    current_delay = min(current_delay + 2.0, 10.0)  # Increase delay, max 10s
                    logger.warning(f"      Possible rate limiting - increasing delay to {current_delay}s")
                enriched_transitions.append(transition)
            
            # Check if we need to take a cooldown break
            # Trigger BEFORE we might hit rate limiting (after every N transitions)
            if (self.cooldown_enabled and 
                i > 0 and 
                i % self.cooldown_after == 0 and
                i < len(transitions_meta)):  # Don't cooldown on last request
                logger.info("")
                logger.info(f"  ========================================")
                logger.info(f"  COOLDOWN: Completed {i} transitions")
                logger.info(f"  Pausing for {self.cooldown_duration} seconds ({self.cooldown_duration/60:.1f} minutes)")
                logger.info(f"  This allows Zoho's rate limit window to reset...")
                logger.info(f"  ========================================")
                logger.info("")
                time.sleep(self.cooldown_duration)
                logger.info(f"  Cooldown complete - resuming extraction...")
                logger.info("")
            # Rate limiting - delay between transition requests
            # Using progressive delay: starts at base_delay, increases if rate limited
            elif i < len(transitions_meta):
                logger.info(f"      Waiting {current_delay:.1f}s before next request...")
                time.sleep(current_delay)
        
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
