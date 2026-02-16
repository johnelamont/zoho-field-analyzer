"""
Workflows Extractor
Extracts workflow rules and field update actions from Zoho CRM
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import time

from .base import BaseExtractor
from ..api.zoho_client import ZohoAPIClient

logger = logging.getLogger(__name__)


class WorkflowsExtractor(BaseExtractor):
    """Extract workflow rules from Zoho CRM"""
    
    def __init__(self, client: ZohoAPIClient, output_dir: Path, client_name: str,
                 with_field_updates: bool = False):
        """
        Initialize workflows extractor
        
        Args:
            client: Zoho API client
            output_dir: Output directory
            client_name: Client name
            with_field_updates: Whether to extract detailed field update information
        """
        super().__init__(client, output_dir, client_name)
        self.workflows_dir = output_dir / 'workflows'
        self.workflows_dir.mkdir(exist_ok=True)
        self.field_updates_dir = self.workflows_dir / 'field_updates'
        self.field_updates_dir.mkdir(exist_ok=True)
        self.with_field_updates = with_field_updates
    
    def get_extractor_name(self) -> str:
        return "workflows"
    
    def get_all_workflows(self) -> List[Dict[str, Any]]:
        """
        Get list of all workflows using pagination
        
        Returns:
            List of workflow rules
        """
        logger.info("Fetching all workflows...")
        
        # Use v8 endpoint with pagination
        url = "https://crm.zoho.com/crm/v8/settings/automation/workflow_rules"
        all_workflows = []
        page = 1
        per_page = 200
        
        while True:
            params = {'page': page, 'per_page': per_page}
            
            try:
                logger.info(f"Fetching page {page}...")
                logger.info(f"URL: {url}")
                logger.info(f"Params: {params}")
                
                response = self.client.session.get(url, params=params)
                
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    workflows = data.get('workflow_rules', [])
                    
                    if not workflows:
                        logger.info("No more workflows found")
                        break
                    
                    all_workflows.extend(workflows)
                    logger.info(f"  Found {len(workflows)} workflows (total: {len(all_workflows)})")
                    
                    # Check if we got fewer than per_page (last page)
                    if len(workflows) < per_page:
                        logger.info("Last page reached")
                        break
                    
                    page += 1
                    time.sleep(0.5)
                else:
                    logger.error(f"Error getting workflows page {page}: {response.status_code}")
                    logger.error(f"Response body: {response.text[:500]}")
                    break
                    
            except Exception as e:
                logger.error(f"Exception getting workflows page {page}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                break
        
        logger.info(f"Found {len(all_workflows)} total workflows")
        return all_workflows
    
    def get_workflow_details(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed workflow configuration including conditions and actions
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Workflow details with conditions or None
        """
        url = f"https://crm.zoho.com/crm/v8/settings/automation/workflow_rules/{workflow_id}"
        
        try:
            response = self.client.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                # Response is wrapped in workflow_rules array
                if data and 'workflow_rules' in data and len(data['workflow_rules']) > 0:
                    return data['workflow_rules'][0]
                return None
            else:
                logger.warning(f"Error getting workflow details {workflow_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"Exception getting workflow details {workflow_id}: {e}")
            return None
    
    def get_field_update_details(self, field_update_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a field update action
        
        Args:
            field_update_id: Field update action ID
            
        Returns:
            Field update details or None
        """
        url = f"https://crm.zoho.com/crm/v8/settings/automation/field_updates/{field_update_id}"
        params = {
            'include_inner_details': 'module.plural_label,related_module.module_name,related_module.plural_label,related_module.singular_label,display_value,field.ui_type'
        }
        
        try:
            response = self.client.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error getting field update {field_update_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.warning(f"Exception getting field update {field_update_id}: {e}")
            return None
    
    def extract_field_updates_from_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract field update details from workflow actions
        
        Args:
            workflow: Workflow data
            
        Returns:
            Updated workflow with field update details
        """
        workflow_id = workflow.get('id')
        workflow_name = workflow.get('name', 'Unnamed')
        
        # Get all field_update actions from all conditions
        field_update_actions = []
        conditions = workflow.get('conditions', [])
        
        for condition in conditions:
            instant_actions = condition.get('instant_actions', {})
            actions = instant_actions.get('actions', [])
            
            for action in actions:
                if action.get('type') == 'field_updates':
                    field_update_actions.append(action)
        
        if not field_update_actions:
            logger.info(f"  No field update actions found")
            return workflow
        
        logger.info(f"  Processing {len(field_update_actions)} field update actions...")
        
        # Enrich each field update action with detailed info
        enriched_actions = []
        total_field_updates = 0
        
        for i, action in enumerate(field_update_actions, 1):
            action_id = action.get('id')
            action_name = action.get('name', 'Unnamed')
            
            logger.info(f"    [{i}/{len(field_update_actions)}] {action_name} (ID: {action_id})")
            
            # Get field update details
            details = self.get_field_update_details(action_id)
            
            if details and 'field_updates' in details and len(details['field_updates']) > 0:
                field_update = details['field_updates'][0]
                
                # Save raw field update details
                field_update_filename = f"{self.sanitize_filename(action_name)}_{action_id}.json"
                field_update_filepath = self.field_updates_dir / f"{workflow_id}_{field_update_filename}"
                self.save_json(field_update, f"workflows/field_updates/{workflow_id}_{field_update_filename}")
                
                # Extract key field info
                enriched_action = {
                    **action,
                    'field_update_details_file': str(field_update_filepath.name),
                    'field_api_name': field_update.get('field', {}).get('api_name'),
                    'field_id': field_update.get('field', {}).get('id'),
                    'field_value': field_update.get('value'),
                    'update_type': field_update.get('type'),
                    'module': field_update.get('module', {}).get('api_name')
                }
                
                enriched_actions.append(enriched_action)
                total_field_updates += 1
                
                logger.info(f"      [OK] Field: {enriched_action['field_api_name']}")
            else:
                logger.warning(f"      [FAIL] Could not get field update details")
                enriched_actions.append(action)
            
            # Rate limiting
            if i < len(field_update_actions):
                time.sleep(0.5)
        
        # Update workflow with enriched actions
        for condition in workflow.get('conditions', []):
            instant_actions = condition.get('instant_actions', {})
            if instant_actions and 'actions' in instant_actions:
                # Replace actions with enriched versions
                original_actions = instant_actions['actions']
                updated_actions = []
                
                for orig_action in original_actions:
                    if orig_action.get('type') == 'field_updates':
                        # Find the enriched version
                        enriched = next(
                            (ea for ea in enriched_actions if ea['id'] == orig_action['id']),
                            orig_action
                        )
                        updated_actions.append(enriched)
                    else:
                        updated_actions.append(orig_action)
                
                instant_actions['actions'] = updated_actions
        
        # Add summary
        workflow['field_updates_summary'] = {
            'total_field_update_actions': len(field_update_actions),
            'enriched_actions': total_field_updates
        }
        
        logger.info(f"  [OK] Processed {len(field_update_actions)} actions, {total_field_updates} field updates")
        
        return workflow
    
    def extract(self) -> Dict[str, Any]:
        """
        Extract all workflows and optionally field update details
        
        Returns:
            Extraction results
        """
        # Get all workflows (basic list)
        workflows = self.get_all_workflows()
        self.stats['total'] = len(workflows)
        
        if not workflows:
            logger.warning("No workflows found!")
            return {
                'status': 'no_data',
                'stats': self.stats
            }
        
        failed_items = []
        all_workflows_data = []
        total_field_updates = 0
        total_workflows_with_field_updates = 0
        
        # Save master workflows list (basic)
        self.save_json({'workflow_rules': workflows}, 'all_workflows.json')
        logger.info("Saved master workflows list")
        logger.info("")
        
        for i, workflow_basic in enumerate(workflows, 1):
            workflow_id = workflow_basic.get('id')
            workflow_name = workflow_basic.get('name', f'workflow_{workflow_id}')
            workflow_module = workflow_basic.get('module', {}).get('api_name', 'Unknown')
            workflow_status = workflow_basic.get('status', {}).get('active', False)
            
            logger.info(f"[{i}/{len(workflows)}] Extracting: {workflow_name} ({workflow_module}) - {'Active' if workflow_status else 'Inactive'}")
            
            try:
                # Get detailed workflow data (includes conditions/actions)
                logger.info("  Getting workflow details...")
                workflow = self.get_workflow_details(workflow_id)
                
                if not workflow:
                    reason = "Could not get workflow details"
                    logger.warning(f"  [FAIL] {reason}")
                    failed_items.append({
                        'name': workflow_name,
                        'id': workflow_id,
                        'reason': reason
                    })
                    self.stats['failed'] += 1
                    continue
                
                # Count initial actions
                action_count = 0
                field_update_count = 0
                conditions = workflow.get('conditions', [])
                for condition in conditions:
                    instant_actions = condition.get('instant_actions', {})
                    actions = instant_actions.get('actions', [])
                    action_count += len(actions)
                    field_update_count += sum(1 for a in actions if a.get('type') == 'field_updates')
                
                logger.info(f"  Found {action_count} total actions, {field_update_count} field updates")
                
                # If with_field_updates, enrich workflow with field update details
                if self.with_field_updates and field_update_count > 0:
                    logger.info("  Extracting field update details...")
                    workflow = self.extract_field_updates_from_workflow(workflow)
                    
                    # Get enriched count from summary
                    summary = workflow.get('field_updates_summary', {})
                    enriched_count = summary.get('enriched_actions', 0)
                    total_field_updates += enriched_count
                    if enriched_count > 0:
                        total_workflows_with_field_updates += 1
                
                # Save workflow data
                filename = f"{self.sanitize_filename(workflow_name)}_{workflow_id}.json"
                self.save_json(workflow, f"workflows/{filename}")
                
                all_workflows_data.append({
                    'id': workflow_id,
                    'name': workflow_name,
                    'module': workflow_module,
                    'status': 'active' if workflow_status else 'inactive',
                    'action_count': action_count,
                    'field_update_count': field_update_count,
                    'filename': filename
                })
                
                self.stats['successful'] += 1
                logger.info(f"  [OK] Saved")
                logger.info("")
                
                # Rate limiting between workflows
                if i < len(workflows):
                    time.sleep(0.3)
                
            except Exception as e:
                reason = str(e)
                logger.error(f"  [FAIL] {reason}")
                failed_items.append({
                    'name': workflow_name,
                    'id': workflow_id,
                    'reason': reason
                })
                self.stats['failed'] += 1
                logger.info("")
        
        # Save master index with summary
        index_data = {
            'workflows': all_workflows_data,
            'summary': {
                'total_workflows': len(workflows),
                'successful': self.stats['successful'],
                'failed': self.stats['failed'],
                'total_field_updates_extracted': total_field_updates,
                'workflows_with_field_updates': total_workflows_with_field_updates
            }
        }
        self.save_json(index_data, 'workflows_index.json')
        
        # Save failed log
        if failed_items:
            self.save_failed_log(failed_items)
        
        # Print summary
        logger.info("="*60)
        logger.info("EXTRACTION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total workflows: {len(workflows)}")
        logger.info(f"Successfully extracted: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        if self.with_field_updates:
            logger.info(f"Total field updates extracted: {total_field_updates}")
            logger.info(f"Workflows with field updates: {total_workflows_with_field_updates}")
        logger.info("")
        
        return {
            'status': 'success',
            'stats': self.stats,
            'workflows': all_workflows_data,
            'failed': failed_items,
            'total_field_updates': total_field_updates
        }
