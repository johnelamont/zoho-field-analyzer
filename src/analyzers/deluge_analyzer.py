"""
Deluge Function Analyzer

Smart analysis of Deluge scripts to identify field reads and writes.

Strategy:
  1. Track record variables: var = zoho.crm.getRecordById("Module", id) → var is a record
  2. Track update maps: zoho.crm.updateRecord("Module", id, mapVar) → mapVar holds writes
  3. .get("field") on record variables → READ
  4. .put("field", val) on update map variables → WRITE
  5. Heuristics to exclude non-field maps (error logging, API params, etc.)
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .rosetta import RosettaStone
from .usage import FieldUsage, UsageType, SourceType, UsageTracker

logger = logging.getLogger(__name__)

# Patterns to match Deluge code
RE_GET_RECORD = re.compile(
    r'(\w+)\s*=\s*zoho\.crm\.getRecordById\(\s*"(\w+)"', re.IGNORECASE
)
RE_SEARCH_RECORDS = re.compile(
    r'(\w+)\s*=\s*zoho\.crm\.searchRecords\(\s*"(\w+)"', re.IGNORECASE
)
RE_GET_RELATED = re.compile(
    r'(\w+)\s*=\s*zoho\.crm\.getRelatedRecords\(\s*"(\w+)"', re.IGNORECASE
)
RE_UPDATE_RECORD = re.compile(
    r'zoho\.crm\.updateRecord\(\s*"(\w+)"\s*,\s*(\w+)\s*,\s*(\w+)', re.IGNORECASE
)
RE_CREATE_RECORD = re.compile(
    r'zoho\.crm\.createRecord\(\s*"(\w+)"\s*,\s*(\w+)', re.IGNORECASE
)
RE_MAP_INIT = re.compile(
    r'(\w+)\s*=\s*(?:Map\(\)|map\(\)|{})', re.IGNORECASE
)
RE_DOT_GET = re.compile(
    r'(\w+)\.get\(\s*"(\w+)"\s*\)'
)
RE_DOT_PUT = re.compile(
    r'(\w+)\.put\(\s*"(\w+)"\s*,'
)
RE_FUNCTION_HEADER = re.compile(
    r'(?:void|string|int|bool|list|map)\s+[\w.]+\(([^)]*)\)', re.IGNORECASE
)

# Variable names that are clearly NOT field maps
NOISE_VAR_NAMES = {
    'errLogMap', 'errlogmap', 'inputParams', 'inputparams',
    'headers', 'params', 'queryParams', 'body', 'response',
    'resp', 'result', 'config', 'settings', 'options',
}

# Field names that are clearly NOT CRM fields
NOISE_FIELD_NAMES = {
    'Function', 'Email_Error', 'Params', 'See_Line', 'Module',
    'Error', 'status', 'code', 'message', 'data', 'details',
    'id', 'select_query', 'email', 'user_name', 'users',
    'name', 'content', 'result', 'response', 'info',
    '$se_module', 'trigger', 'workflow', 'blueprint', 'approval',
}

# Map variable name patterns to likely purposes
UPDATE_MAP_PATTERNS = re.compile(
    r'^(Up|Cr|Update|Create|update|create)\w*(Mp|Map|Params|Data|Record)$|'
    r'^(mp|map)\w*$',
    re.IGNORECASE
)


class DelugeAnalyzer:
    """Analyze Deluge function scripts for field reads/writes."""
    
    def __init__(self, rosetta: RosettaStone, tracker: UsageTracker):
        self.rosetta = rosetta
        self.tracker = tracker
        self.stats = {
            'functions_processed': 0,
            'field_reads': 0,
            'field_writes': 0,
            'unresolved_reads': 0,
            'unresolved_writes': 0,
        }
    
    def analyze_all(self, functions_dir: Path):
        """Analyze all Deluge function scripts."""
        for func_file in sorted(functions_dir.glob("*.txt")):
            try:
                with open(func_file, encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                func_name = self._extract_function_name(content, func_file)
                self._analyze_function(content, func_name, func_file.stem)
                self.stats['functions_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {func_file.name}: {e}")
        
        logger.info(f"Deluge analysis complete: "
                     f"{self.stats['functions_processed']} functions, "
                     f"{self.stats['field_reads']} reads, "
                     f"{self.stats['field_writes']} writes")
    
    def _extract_function_name(self, content: str, filepath: Path) -> str:
        """Extract display name from the file header."""
        for line in content.split('\n')[:5]:
            if line.startswith('// Display_Name:') or line.startswith('// Function:'):
                return line.split(':', 1)[1].strip()
        return filepath.stem
    
    def _analyze_function(self, content: str, func_name: str, source_id: str):
        """
        Analyze a single Deluge function for field reads and writes.
        
        Uses variable flow tracking:
        1. Identify record variables (from getRecordById, etc.)
        2. Identify update maps (from Map() that feed into updateRecord)
        3. Track .get() on records → READ
        4. Track .put() on update maps → WRITE
        """
        lines = content.split('\n')
        
        # Phase 1: Identify record variables and their modules
        record_vars = self._find_record_variables(content)
        
        # Phase 2: Identify update maps and their target modules
        update_maps = self._find_update_maps(content)
        
        # Phase 3: Scan all .get() calls on record variables → READs
        for match in RE_DOT_GET.finditer(content):
            var_name = match.group(1)
            field_name = match.group(2)
            
            if field_name in NOISE_FIELD_NAMES:
                continue
            
            if var_name in record_vars:
                module = record_vars[var_name]
                line_num = content[:match.start()].count('\n') + 1
                
                # Validate field exists in module
                resolved = self.rosetta.resolve(module, api_name=field_name)
                if resolved:
                    self.tracker.add_usage(FieldUsage(
                        usage_type=UsageType.READ,
                        source_type=SourceType.FUNCTION,
                        source_name=f"Function: {func_name}",
                        source_id=source_id,
                        module=module,
                        field_api_name=field_name,
                        details={'line': line_num}
                    ))
                    self.stats['field_reads'] += 1
                else:
                    # Field not in Rosetta Stone - could be valid but custom
                    # Still track it but mark as unresolved
                    self.tracker.add_usage(FieldUsage(
                        usage_type=UsageType.READ,
                        source_type=SourceType.FUNCTION,
                        source_name=f"Function: {func_name}",
                        source_id=source_id,
                        module=module,
                        field_api_name=field_name,
                        details={'line': line_num, 'unresolved': True}
                    ))
                    self.stats['unresolved_reads'] += 1
        
        # Phase 4: Scan all .put() calls on update maps → WRITEs
        for match in RE_DOT_PUT.finditer(content):
            var_name = match.group(1)
            field_name = match.group(2)
            
            if field_name in NOISE_FIELD_NAMES:
                continue
            if var_name.lower() in {v.lower() for v in NOISE_VAR_NAMES}:
                continue
            
            if var_name in update_maps:
                module = update_maps[var_name]
                line_num = content[:match.start()].count('\n') + 1
                
                # Try to extract the value being set
                line_text = lines[line_num - 1] if line_num <= len(lines) else ''
                
                resolved = self.rosetta.resolve(module, api_name=field_name)
                if resolved:
                    self.tracker.add_usage(FieldUsage(
                        usage_type=UsageType.WRITE,
                        source_type=SourceType.FUNCTION,
                        source_name=f"Function: {func_name}",
                        source_id=source_id,
                        module=module,
                        field_api_name=field_name,
                        details={
                            'line': line_num,
                            'context': line_text.strip()[:200],
                        }
                    ))
                    self.stats['field_writes'] += 1
                else:
                    self.tracker.add_usage(FieldUsage(
                        usage_type=UsageType.WRITE,
                        source_type=SourceType.FUNCTION,
                        source_name=f"Function: {func_name}",
                        source_id=source_id,
                        module=module,
                        field_api_name=field_name,
                        details={
                            'line': line_num,
                            'context': line_text.strip()[:200],
                            'unresolved': True,
                        }
                    ))
                    self.stats['unresolved_writes'] += 1
    
    def _find_record_variables(self, content: str) -> Dict[str, str]:
        """
        Find variables that hold CRM records.
        
        Returns: {variable_name: module_name}
        """
        records = {}
        
        # zoho.crm.getRecordById("Module", id)
        for match in RE_GET_RECORD.finditer(content):
            var_name = match.group(1)
            module = self._normalize_module(match.group(2))
            records[var_name] = module
        
        # zoho.crm.searchRecords("Module", criteria)
        # These return lists, but individual items are often accessed
        for match in RE_SEARCH_RECORDS.finditer(content):
            var_name = match.group(1)
            module = self._normalize_module(match.group(2))
            records[var_name] = module
            # Common pattern: each = listVar.get(i) or for each in listVar
            # We'll catch .get() on these too
        
        # Also catch common assignment patterns:
        # ContactInfo = zoho.crm.getRecordById(...)
        # Often followed by: ContactEmail = ContactInfo.get("Email")
        # The variable after = is tracked, not the intermediate
        
        # Handle list iteration: for each row in searchResults
        for_pattern = re.compile(r'for\s+each\s+(\w+)\s+in\s+(\w+)')
        for match in for_pattern.finditer(content):
            iter_var = match.group(1)
            list_var = match.group(2)
            if list_var in records:
                records[iter_var] = records[list_var]
        
        return records
    
    def _find_update_maps(self, content: str) -> Dict[str, str]:
        """
        Find Map variables used to update/create CRM records.
        
        Strategy:
        1. Find all zoho.crm.updateRecord("Module", id, mapVar) calls
        2. Find all zoho.crm.createRecord("Module", mapVar) calls
        3. Map the mapVar back to its module
        """
        update_maps = {}
        
        # updateRecord("Module", id, mapVar, ...)
        for match in RE_UPDATE_RECORD.finditer(content):
            module = self._normalize_module(match.group(1))
            map_var = match.group(3)
            update_maps[map_var] = module
        
        # createRecord("Module", mapVar)
        for match in RE_CREATE_RECORD.finditer(content):
            module = self._normalize_module(match.group(1))
            map_var = match.group(2)
            update_maps[map_var] = module
        
        # Also catch pattern where map is built then passed inline:
        # zoho.crm.updateRecord("Deals", id, {"Stage": "Closed Won"})
        # These are rare in practice - skip for now
        
        # If no explicit updateRecord found, use heuristics on Map() variables
        if not update_maps:
            for match in RE_MAP_INIT.finditer(content):
                var_name = match.group(1)
                if var_name.lower() not in {v.lower() for v in NOISE_VAR_NAMES}:
                    if UPDATE_MAP_PATTERNS.match(var_name):
                        # Can't determine module without updateRecord call
                        # Skip these - better to miss than to misattribute
                        pass
        
        return update_maps
    
    def _normalize_module(self, module: str) -> str:
        """Normalize Zoho module names."""
        aliases = {
            'Potentials': 'Deals',
            'Sales_Orders': 'Sales_Orders',
            'Salesorders': 'Sales_Orders',
            'Purchase_Orders': 'Purchase_Orders',
        }
        return aliases.get(module, module)
