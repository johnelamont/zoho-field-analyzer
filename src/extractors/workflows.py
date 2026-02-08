"""
Workflows Extractor
Extracts workflow rules, field updates, and actions from Zoho CRM
"""
from pathlib import Path
from typing import Dict, Any, List
import logging

from .base import BaseExtractor
from ..api.zoho_client import ZohoAPIClient

logger = logging.getLogger(__name__)


class WorkflowsExtractor(BaseExtractor):
    """Extract workflows from Zoho CRM"""
    
    def __init__(self, client: ZohoAPIClient, output_dir: Path, client_name: str):
        super().__init__(client, output_dir, client_name)
        self.workflows_dir = output_dir / 'workflows'
        self.workflows_dir.mkdir(exist_ok=True)
    
    def get_extractor_name(self) -> str:
        return "workflows"
    
    def get_all_workflows(self) -> List[Dict[str, Any]]:
        """
        Get list of all workflows
        
        Returns:
            List of workflow metadata
        """
        logger.info("Fetching all workflows...")
        
        workflows = self.client.paginated_get(
            endpoint='settings/workflow_rules',
            start_param='page',
            limit=50
        )
        
        logger.info(f"Found {len(workflows)} total workflows")
        return workflows
    
    def get_workflow_details(self, workflow_id: str) -> Dict[str, Any]:
        """
        Get detailed workflow configuration
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Workflow details
        """
        endpoint = f'settings/workflow_rules/{workflow_id}'
        return self.client.get(endpoint)
    
    def extract(self) -> Dict[str, Any]:
        """
        Extract all workflows and save to files
        
        Returns:
            Extraction results
        """
        # Get all workflows
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
        
        for i, workflow in enumerate(workflows, 1):
            workflow_id = workflow.get('id', f'workflow_{i}')
            workflow_name = workflow.get('name', f'workflow_{workflow_id}')
            
            logger.info(f"[{i}/{len(workflows)}] Extracting: {workflow_name}")
            
            try:
                # Get detailed workflow data
                details = self.get_workflow_details(workflow_id)
                
                if details:
                    # Save workflow as JSON
                    filename = f"{self.sanitize_filename(workflow_name)}_{workflow_id}.json"
                    self.save_json(details, f"workflows/{filename}")
                    
                    all_workflows_data.append({
                        'metadata': workflow,
                        'details': details,
                        'filename': filename
                    })
                    
                    self.stats['successful'] += 1
                    logger.info(f"  ✓ Saved")
                else:
                    reason = "No details in response"
                    logger.warning(f"  ✗ {reason}")
                    failed_items.append({
                        'name': workflow_name,
                        'id': workflow_id,
                        'reason': reason
                    })
                    self.stats['failed'] += 1
                    
            except Exception as e:
                reason = str(e)
                logger.error(f"  ✗ {reason}")
                failed_items.append({
                    'name': workflow_name,
                    'id': workflow_id,
                    'reason': reason
                })
                self.stats['failed'] += 1
        
        # Save master index
        self.save_json(all_workflows_data, 'workflows_index.json')
        
        # Save failed log
        if failed_items:
            self.save_failed_log(failed_items)
        
        return {
            'status': 'success',
            'stats': self.stats,
            'workflows': all_workflows_data,
            'failed': failed_items
        }
