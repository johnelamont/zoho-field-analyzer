"""
Rosetta Stone - Field name mapping across all Zoho naming conventions.

Maps between:
  - field_label (display name): "Flag Reason"
  - api_name: "Flag_Reason"  
  - column_name: "POTENTIALCF156"
  - field_id: "3193870000616809033"

Each module gets its own mapping table since field names are module-scoped.
"""
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class FieldEntry:
    """Single field with all its name variants and metadata."""
    
    __slots__ = ['module', 'field_label', 'api_name', 'column_name',
                 'field_id', 'data_type', 'raw']
    
    def __init__(self, module: str, field_label: str, api_name: str,
                 column_name: str, field_id: str, data_type: str,
                 raw: dict):
        self.module = module
        self.field_label = field_label
        self.api_name = api_name
        self.column_name = column_name
        self.field_id = field_id
        self.data_type = data_type
        self.raw = raw  # Full field definition from modules JSON
    
    def __repr__(self):
        return f"Field({self.module}.{self.api_name})"


class RosettaStone:
    """
    Bidirectional field name resolver.
    
    Usage:
        rosetta = RosettaStone.from_raw_modules(Path("data/blades/raw/modules"))
        field = rosetta.resolve("Deals", api_name="Stage")
        field = rosetta.resolve("Deals", column_name="POTENTIALCF156")
        field = rosetta.resolve("Deals", field_label="Flag Reason")
        field = rosetta.resolve("Deals", field_id="3193870000616809033")
    """
    
    def __init__(self):
        # module -> {lookup_key -> FieldEntry}
        self._by_api_name: Dict[str, Dict[str, FieldEntry]] = {}
        self._by_column_name: Dict[str, Dict[str, FieldEntry]] = {}
        self._by_label: Dict[str, Dict[str, FieldEntry]] = {}
        self._by_id: Dict[str, Dict[str, FieldEntry]] = {}
        # Also a flat id lookup (IDs are globally unique)
        self._global_by_id: Dict[str, FieldEntry] = {}
        # Module name normalization (Potentials -> Deals, etc.)
        self._module_aliases: Dict[str, str] = {}
        # All modules
        self.modules: Dict[str, List[FieldEntry]] = {}
    
    @classmethod
    def from_raw_modules(cls, modules_dir: Path) -> 'RosettaStone':
        """Build from raw modules extraction directory."""
        rosetta = cls()
        
        for module_file in sorted(modules_dir.glob("*.json")):
            if module_file.name in ('all_modules.json',):
                continue
            
            with open(module_file) as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            fields_data = data.get('fields', {})
            fields = fields_data.get('fields', [])
            
            module_name = metadata.get('api_name', module_file.stem)
            
            if not fields:
                logger.debug(f"No fields in {module_file.name}, skipping")
                continue
            
            rosetta._register_module(module_name, fields, metadata)
        
        # Build common aliases
        rosetta._build_aliases()
        
        logger.info(f"Rosetta Stone built: {len(rosetta.modules)} modules, "
                     f"{sum(len(v) for v in rosetta.modules.values())} fields")
        return rosetta
    
    def _register_module(self, module_name: str, fields: list, metadata: dict):
        """Register all fields for a module."""
        self._by_api_name[module_name] = {}
        self._by_column_name[module_name] = {}
        self._by_label[module_name] = {}
        self._by_id[module_name] = {}
        self.modules[module_name] = []
        
        for field_raw in fields:
            entry = FieldEntry(
                module=module_name,
                field_label=field_raw.get('field_label', ''),
                api_name=field_raw.get('api_name', ''),
                column_name=field_raw.get('column_name', ''),
                field_id=str(field_raw.get('id', '')),
                data_type=field_raw.get('data_type', ''),
                raw=field_raw
            )
            
            self.modules[module_name].append(entry)
            
            if entry.api_name:
                self._by_api_name[module_name][entry.api_name] = entry
            if entry.column_name:
                self._by_column_name[module_name][entry.column_name] = entry
            if entry.field_label:
                self._by_label[module_name][entry.field_label] = entry
            if entry.field_id:
                self._by_id[module_name][entry.field_id] = entry
                self._global_by_id[entry.field_id] = entry
    
    def _build_aliases(self):
        """Build module name aliases (Zoho internal names → API names)."""
        # Common Zoho internal-to-API mappings
        alias_map = {
            'Potentials': 'Deals',
            'Potential': 'Deals',
        }
        for alias, canonical in alias_map.items():
            if canonical in self.modules:
                self._module_aliases[alias] = canonical
    
    def _normalize_module(self, module: str) -> str:
        """Resolve module aliases."""
        return self._module_aliases.get(module, module)
    
    def resolve(self, module: str, *, api_name: str = None,
                column_name: str = None, field_label: str = None,
                field_id: str = None) -> Optional[FieldEntry]:
        """
        Resolve a field using any naming convention.
        
        Exactly one of api_name, column_name, field_label, or field_id must be provided.
        """
        module = self._normalize_module(module)
        
        if field_id:
            # Try module-specific first, then global
            entry = self._by_id.get(module, {}).get(field_id)
            if entry:
                return entry
            return self._global_by_id.get(field_id)
        
        if api_name:
            return self._by_api_name.get(module, {}).get(api_name)
        
        if column_name:
            return self._by_column_name.get(module, {}).get(column_name)
        
        if field_label:
            return self._by_label.get(module, {}).get(field_label)
        
        return None
    
    def resolve_by_id(self, field_id: str) -> Optional[FieldEntry]:
        """Resolve field by ID only (globally unique)."""
        return self._global_by_id.get(str(field_id))
    
    def get_module_fields(self, module: str) -> List[FieldEntry]:
        """Get all fields for a module."""
        module = self._normalize_module(module)
        return self.modules.get(module, [])
    
    def get_all_modules(self) -> List[str]:
        """Get list of all module names."""
        return sorted(self.modules.keys())
    
    def to_dict(self) -> dict:
        """Export as a serializable dictionary."""
        result = {}
        for module, fields in self.modules.items():
            result[module] = [
                {
                    'field_label': f.field_label,
                    'api_name': f.api_name,
                    'column_name': f.column_name,
                    'field_id': f.field_id,
                    'data_type': f.data_type,
                }
                for f in sorted(fields, key=lambda x: x.field_label.lower())
            ]
        return result
