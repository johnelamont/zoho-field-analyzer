"""
Blueprint Analyzer

Extracts field usage from blueprint transitions:
  - Fields array (DURING tab) → ENTRY usage (user manually fills in)
  - Actions.Fieldupdate (AFTER tab) → WRITE usage (automatic updates)
  - Actions.Deluge → function references (analyzed separately by deluge analyzer)
  - CriteriaString → READ usage (transition conditions)

Uses FieldsMeta + Rosetta Stone to resolve column_name → api_name.
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple

from .rosetta import RosettaStone
from .usage import FieldUsage, UsageType, SourceType, UsageTracker

logger = logging.getLogger(__name__)


# Map Zoho internal module names to API module names
MODULE_MAP = {
    'Potentials': 'Deals',
    'Leads': 'Leads',
    'Accounts': 'Accounts',
    'Contacts': 'Contacts',
    'Events': 'Events',
    'Tasks': 'Tasks',
    'Cases': 'Cases',
}


class BlueprintAnalyzer:
    """Analyze blueprint transitions for field usage."""
    
    def __init__(self, rosetta: RosettaStone, tracker: UsageTracker):
        self.rosetta = rosetta
        self.tracker = tracker
        self.stats = {
            'blueprints_processed': 0,
            'transitions_processed': 0,
            'field_updates_found': 0,
            'entry_fields_found': 0,
            'criteria_fields_found': 0,
            'unresolved_fields': 0,
        }
        self._unresolved: List[dict] = []
    
    def analyze_all(self, blueprints_dir: Path):
        """Analyze all blueprints and their transitions."""
        transitions_dir = blueprints_dir / 'transitions'
        
        if not transitions_dir.exists():
            logger.warning(f"No transitions directory at {transitions_dir}")
            return
        
        # Load blueprint index to get names
        blueprint_names = {}
        for bp_file in blueprints_dir.glob("*.json"):
            if bp_file.name == 'blueprints_index.json':
                continue
            try:
                with open(bp_file) as f:
                    bp_data = json.load(f)
                
                # Structure: {metadata: {Name, Id}, details: {...}}
                metadata = bp_data.get('metadata', {})
                bp_id = str(metadata.get('Id', ''))
                bp_name = metadata.get('Name', '')
                
                if not bp_id or not bp_name:
                    # Fallback: try Processes array format
                    processes = bp_data.get('Processes', [])
                    for p in (processes if isinstance(processes, list) else [processes]):
                        pid = str(p.get('Id', ''))
                        pname = p.get('Name', '')
                        if pid:
                            blueprint_names[pid] = pname or bp_file.stem
                else:
                    blueprint_names[bp_id] = bp_name
                    
                # Also try extracting from filename: Name_ID.json
                if not bp_id:
                    parts = bp_file.stem.rsplit('_', 1)
                    if len(parts) == 2 and parts[1].isdigit():
                        blueprint_names[parts[1]] = parts[0]
                        
            except Exception as e:
                logger.debug(f"Couldn't parse blueprint file {bp_file.name}: {e}")
        
        # Process each transition file
        for trans_file in sorted(transitions_dir.glob("*.json")):
            try:
                with open(trans_file) as f:
                    trans_data = json.load(f)
                
                # Parse filename: {blueprint_id}_{transition_name}_{transition_id}.json
                parts = trans_file.stem.split('_', 1)
                bp_id = parts[0] if parts else ''
                bp_name = blueprint_names.get(bp_id, bp_id)
                trans_name = trans_data.get('Name', trans_file.stem)
                module_raw = trans_data.get('Module', '')
                module = MODULE_MAP.get(module_raw, module_raw)
                
                source_label = f"{bp_name} > {trans_name}"
                
                self._analyze_transition(trans_data, module, source_label, trans_file.stem)
                self.stats['transitions_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {trans_file.name}: {e}")
        
        self.stats['blueprints_processed'] = len(blueprint_names)
        
        logger.info(f"Blueprint analysis complete: "
                     f"{self.stats['transitions_processed']} transitions, "
                     f"{self.stats['field_updates_found']} field updates, "
                     f"{self.stats['entry_fields_found']} entry fields, "
                     f"{self.stats['unresolved_fields']} unresolved")
    
    def _analyze_transition(self, trans: dict, module: str, 
                            source_label: str, source_id: str):
        """Analyze a single transition for field usage."""
        
        # Build local column_name → field mapping from FieldsMeta
        local_field_map = self._build_fieldsmeta_map(trans, module)
        
        # 1. DURING tab - Fields array (user manual entry)
        self._process_during_fields(trans, module, source_label, source_id, local_field_map)
        
        # 2. AFTER tab - Actions.Fieldupdate (automatic field updates)
        self._process_field_updates(trans, module, source_label, source_id, local_field_map)
        
        # 3. Criteria - fields used in transition conditions
        self._process_criteria(trans, module, source_label, source_id, local_field_map)
    
    def _build_fieldsmeta_map(self, trans: dict, module: str) -> Dict[str, str]:
        """
        Build field_id → api_name mapping from FieldsMeta.
        
        FieldsMeta gives us column_name (Name) and field_id (Id).
        We cross-reference with Rosetta Stone to get api_name.
        """
        field_map = {}  # field_id -> api_name
        
        fields_meta = trans.get('FieldsMeta', {})
        for meta_key, meta_fields in fields_meta.items():
            if not isinstance(meta_fields, list):
                continue
            for fm in meta_fields:
                fid = str(fm.get('Id', ''))
                col_name = fm.get('Name', '')
                label = fm.get('Label', '')
                
                if not fid:
                    continue
                
                # Try to resolve via Rosetta Stone
                resolved = None
                if fid:
                    resolved = self.rosetta.resolve_by_id(fid)
                if not resolved and col_name:
                    resolved = self.rosetta.resolve(module, column_name=col_name)
                if not resolved and label:
                    resolved = self.rosetta.resolve(module, field_label=label)
                
                if resolved:
                    field_map[fid] = resolved.api_name
                else:
                    # Store column_name as fallback
                    field_map[fid] = col_name or label or fid
        
        return field_map
    
    def _process_during_fields(self, trans: dict, module: str,
                                source_label: str, source_id: str,
                                field_map: Dict[str, str]):
        """Process DURING tab fields (manual entry by user).
        
        DURING fields have structure:
          {"Type": "Field", "Id": "3193870000605817009", "Module": "Potentials",
           "IsNonMandatory": False, ...}
        No Label key - must resolve via field_map or Rosetta Stone by ID.
        """
        fields = trans.get('Fields', [])
        for f in fields:
            # Skip non-field entries (Type="Info" are just instruction text)
            if f.get('Type') != 'Field':
                continue
            
            fid = str(f.get('Id', ''))
            if not fid:
                continue
            
            # Resolve field name via local FieldsMeta map or Rosetta Stone
            api_name = field_map.get(fid)
            label = ''
            if not api_name:
                resolved = self.rosetta.resolve_by_id(fid)
                if resolved:
                    api_name = resolved.api_name
                    label = resolved.field_label
                else:
                    api_name = fid
                    self._log_unresolved(module, f"ID:{fid}", fid, source_label, "during_field")
            else:
                # Get the label from Rosetta for display
                resolved = self.rosetta.resolve(module, api_name=api_name)
                if resolved:
                    label = resolved.field_label
            
            is_mandatory = not f.get('IsNonMandatory', True)
            
            self.tracker.add_usage(FieldUsage(
                usage_type=UsageType.ENTRY,
                source_type=SourceType.BLUEPRINT,
                source_name=source_label,
                source_id=source_id,
                module=module,
                field_api_name=api_name,
                details={
                    'mandatory': is_mandatory,
                    'field_label': label,
                }
            ))
            self.stats['entry_fields_found'] += 1
    
    def _process_field_updates(self, trans: dict, module: str,
                                source_label: str, source_id: str,
                                field_map: Dict[str, str]):
        """Process AFTER tab field updates (automatic)."""
        actions = trans.get('Actions', {})
        field_updates = actions.get('Fieldupdate', [])
        
        for fu in field_updates:
            fid = str(fu.get('fieldId', ''))
            label = fu.get('fieldLabel', '')
            value = fu.get('fieldValue', '')
            actual_value = fu.get('actualValue', '')
            update_name = fu.get('Name', '')
            
            api_name = field_map.get(fid)
            if not api_name:
                resolved = self.rosetta.resolve(module, field_label=label)
                if resolved:
                    api_name = resolved.api_name
                else:
                    # Try by ID globally
                    resolved = self.rosetta.resolve_by_id(fid)
                    if resolved:
                        api_name = resolved.api_name
                    else:
                        api_name = label
                        self._log_unresolved(module, label, fid, source_label, "field_update")
            
            self.tracker.add_usage(FieldUsage(
                usage_type=UsageType.WRITE,
                source_type=SourceType.BLUEPRINT,
                source_name=source_label,
                source_id=source_id,
                module=module,
                field_api_name=api_name,
                details={
                    'value': value,
                    'actual_value': actual_value,
                    'update_name': update_name,
                    'field_label': label,
                }
            ))
            self.stats['field_updates_found'] += 1
    
    def _process_criteria(self, trans: dict, module: str,
                          source_label: str, source_id: str,
                          field_map: Dict[str, str]):
        """Process transition criteria (field evaluations)."""
        criteria_str = trans.get('CriteriaString', '')
        if not criteria_str or not criteria_str.strip():
            return
        
        # CriteriaString is a text-based condition, not structured.
        # We record it as a general read on the transition.
        # The actual field references would need parsing.
        # For now, log it as context.
        self.tracker.add_usage(FieldUsage(
            usage_type=UsageType.READ,
            source_type=SourceType.BLUEPRINT,
            source_name=source_label,
            source_id=source_id,
            module=module,
            field_api_name="_transition_criteria_",
            details={
                'criteria_string': criteria_str,
                'note': 'Unparsed transition criteria'
            }
        ))
    
    def _log_unresolved(self, module: str, label: str, field_id: str,
                        source: str, context: str):
        self.stats['unresolved_fields'] += 1
        self._unresolved.append({
            'module': module,
            'label': label,
            'field_id': field_id,
            'source': source,
            'context': context,
        })
    
    def get_function_references(self, blueprints_dir: Path) -> List[dict]:
        """
        Extract Deluge function references from blueprints.
        
        Returns list of {function_name, function_id, blueprint, transition}
        """
        refs = []
        transitions_dir = blueprints_dir / 'transitions'
        
        if not transitions_dir.exists():
            return refs
        
        for trans_file in sorted(transitions_dir.glob("*.json")):
            try:
                with open(trans_file) as f:
                    trans = json.load(f)
                
                actions = trans.get('Actions', {})
                deluge_refs = actions.get('Deluge', [])
                
                for d in deluge_refs:
                    refs.append({
                        'function_name': d.get('Name', ''),
                        'function_id': str(d.get('Id', '')),
                        'transition': trans.get('Name', ''),
                        'transition_file': trans_file.name,
                        'module': trans.get('Module', ''),
                    })
            except Exception:
                pass
        
        return refs
