"""
Workflow Analyzer

Extracts field usage from workflow rules:
  - criteria_details → READ usage (field evaluated in conditions)  
  - field_updates actions → WRITE usage (field value set)
  - functions actions → function references (analyzed by deluge analyzer)
  - execute_when → trigger context
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

from .rosetta import RosettaStone
from .usage import FieldUsage, UsageType, SourceType, UsageTracker

logger = logging.getLogger(__name__)


class WorkflowAnalyzer:
    """Analyze workflow rules for field usage."""
    
    def __init__(self, rosetta: RosettaStone, tracker: UsageTracker):
        self.rosetta = rosetta
        self.tracker = tracker
        self.stats = {
            'workflows_processed': 0,
            'criteria_reads': 0,
            'field_writes': 0,
            'function_refs': 0,
        }
    
    def analyze_all(self, workflows_dir: Path):
        """Analyze all workflows."""
        # Process each workflow file
        for wf_file in sorted(workflows_dir.glob("*.json")):
            if wf_file.name in ('workflows_index.json', 'FAILED_EXTRACTIONS.txt'):
                continue
            
            try:
                with open(wf_file) as f:
                    wf_data = json.load(f)
                
                self._analyze_workflow(wf_data, wf_file)
                self.stats['workflows_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {wf_file.name}: {e}")
        
        logger.info(f"Workflow analysis complete: "
                     f"{self.stats['workflows_processed']} workflows, "
                     f"{self.stats['criteria_reads']} criteria reads, "
                     f"{self.stats['field_writes']} field writes")
    
    def _analyze_workflow(self, wf: dict, wf_file: Path):
        """Analyze a single workflow."""
        wf_name = wf.get('name', wf_file.stem)
        wf_id = str(wf.get('id', ''))
        module_info = wf.get('module', {})
        module = module_info.get('api_name', '') if isinstance(module_info, dict) else ''
        
        if not module:
            logger.debug(f"No module for workflow {wf_name}, skipping")
            return
        
        source_label = f"Workflow: {wf_name}"
        
        # Process each condition block
        for condition in wf.get('conditions', []):
            seq = condition.get('sequence_number', 0)
            cond_source = f"{source_label} (cond {seq})"
            
            # 1. Criteria - field evaluations (READs)
            criteria_details = condition.get('criteria_details', {})
            if criteria_details:
                criteria = criteria_details.get('criteria')
                if criteria:
                    self._extract_criteria_reads(criteria, module, cond_source, wf_id)
            
            # 2. Instant actions
            instant = condition.get('instant_actions', {})
            if instant:
                for action in instant.get('actions', []):
                    self._process_action(action, module, cond_source, wf_id)
            
            # 3. Scheduled actions
            scheduled = condition.get('scheduled_actions', {})
            if isinstance(scheduled, dict):
                for action in scheduled.get('actions', []):
                    self._process_action(action, module, cond_source, wf_id)
    
    def _extract_criteria_reads(self, criteria: dict, module: str,
                                 source_label: str, source_id: str):
        """
        Recursively extract field reads from criteria structure.
        
        Criteria can be:
          - Simple: {"comparator": "equal", "field": {"api_name": "Phone"}, "value": ...}
          - Group: {"group_operator": "AND", "group": [...criteria...]}
        """
        if not criteria or not isinstance(criteria, dict):
            return
        
        # Check if this is a group
        if 'group' in criteria:
            for sub_criteria in criteria.get('group', []):
                self._extract_criteria_reads(sub_criteria, module, source_label, source_id)
            return
        
        # Simple criteria - extract field reference
        field_info = criteria.get('field', {})
        if not field_info or not isinstance(field_info, dict):
            return
        
        api_name = field_info.get('api_name', '')
        if not api_name:
            return
        
        comparator = criteria.get('comparator', '')
        value = criteria.get('value', '')
        
        self.tracker.add_usage(FieldUsage(
            usage_type=UsageType.READ,
            source_type=SourceType.WORKFLOW,
            source_name=source_label,
            source_id=source_id,
            module=module,
            field_api_name=api_name,
            details={
                'comparator': comparator,
                'value': value,
            }
        ))
        self.stats['criteria_reads'] += 1
    
    def _process_action(self, action: dict, module: str,
                        source_label: str, source_id: str):
        """Process a workflow action (field update, function call, etc.)."""
        action_type = action.get('type', '')
        
        if action_type == 'field_updates':
            self._process_field_update_action(action, module, source_label, source_id)
        elif action_type == 'functions':
            self.stats['function_refs'] += 1
            # Function analysis handled by deluge analyzer
    
    def _process_field_update_action(self, action: dict, module: str,
                                      source_label: str, source_id: str):
        """Process a field update action."""
        field_api_name = action.get('field_api_name', '')
        field_value = action.get('field_value', '')
        update_type = action.get('update_type', '')
        action_name = action.get('name', '')
        action_module = action.get('module', module)
        
        # Some field updates target related modules
        related = action.get('related_details')
        if related and isinstance(related, dict):
            target_module = related.get('module', {}).get('api_name', action_module)
        else:
            target_module = action_module if action_module else module
        
        if not field_api_name:
            logger.debug(f"No field_api_name in action {action_name}")
            return
        
        self.tracker.add_usage(FieldUsage(
            usage_type=UsageType.WRITE,
            source_type=SourceType.WORKFLOW,
            source_name=source_label,
            source_id=source_id,
            module=target_module,
            field_api_name=field_api_name,
            details={
                'value': field_value,
                'update_type': update_type,
                'action_name': action_name,
            }
        ))
        self.stats['field_writes'] += 1
    
    def get_function_references(self, workflows_dir: Path) -> List[dict]:
        """Extract function names referenced by workflows."""
        refs = []
        
        for wf_file in sorted(workflows_dir.glob("*.json")):
            if wf_file.name in ('workflows_index.json', 'FAILED_EXTRACTIONS.txt'):
                continue
            
            try:
                with open(wf_file) as f:
                    wf_data = json.load(f)
                
                wf_name = wf_data.get('name', '')
                module = wf_data.get('module', {}).get('api_name', '')
                
                for condition in wf_data.get('conditions', []):
                    for action_group in ('instant_actions', 'scheduled_actions'):
                        actions_data = condition.get(action_group, {})
                        if not isinstance(actions_data, dict):
                            continue
                        for action in actions_data.get('actions', []):
                            if action.get('type') == 'functions':
                                refs.append({
                                    'function_name': action.get('name', ''),
                                    'function_id': str(action.get('id', '')),
                                    'workflow': wf_name,
                                    'module': module,
                                })
            except Exception:
                pass
        
        return refs
