"""
Field usage tracking - records where and how each field is used.

Each usage is classified as:
  - READ: field value is evaluated in a condition or read in code
  - WRITE: field value is set/updated
  - ENTRY: field is presented to user for manual input (blueprint DURING tab)

Each usage has a source attribution:
  - source_type: "blueprint", "workflow", "function"
  - source_name: human-readable name
  - source_id: unique ID
  - details: context-specific info (value set, condition used, etc.)
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class UsageType(Enum):
    READ = "read"
    WRITE = "write"
    ENTRY = "entry"  # Blueprint DURING tab - user manually enters


class SourceType(Enum):
    BLUEPRINT = "blueprint"
    WORKFLOW = "workflow"
    FUNCTION = "function"


@dataclass
class FieldUsage:
    """Single instance of a field being used somewhere."""
    usage_type: UsageType
    source_type: SourceType
    source_name: str          # e.g. "Inside Sales Process > Discovery Call Completed"
    source_id: str            # Unique ID for linking
    module: str               # Module this field belongs to
    field_api_name: str       # API name of the field
    details: Dict[str, Any] = field(default_factory=dict)
    # details can include:
    #   For WRITE: {"value": "Discovery Completed", "update_type": "static"}
    #   For READ:  {"comparator": "equal", "value": ["Inbound Call", ...]}
    #   For READ in Deluge: {"line": 42, "context": "if(DealInfo.get(\"Stage\") == ..."}
    #   For WRITE in Deluge: {"line": 289, "target_module": "Deals", "value_expr": "FlagNotes"}


@dataclass  
class FieldProfile:
    """Complete usage profile for a single field."""
    module: str
    field_label: str
    api_name: str
    column_name: str
    field_id: str
    data_type: str
    
    reads: List[FieldUsage] = field(default_factory=list)
    writes: List[FieldUsage] = field(default_factory=list)
    entries: List[FieldUsage] = field(default_factory=list)
    
    @property
    def is_used(self) -> bool:
        return bool(self.reads or self.writes or self.entries)
    
    @property
    def total_usages(self) -> int:
        return len(self.reads) + len(self.writes) + len(self.entries)
    
    @property
    def usage_summary(self) -> str:
        """Quick summary like 'R:5 W:3 E:2' or 'unused'."""
        if not self.is_used:
            return "unused"
        parts = []
        if self.reads:
            parts.append(f"R:{len(self.reads)}")
        if self.writes:
            parts.append(f"W:{len(self.writes)}")
        if self.entries:
            parts.append(f"E:{len(self.entries)}")
        return " ".join(parts)
    
    def add_usage(self, usage: FieldUsage):
        if usage.usage_type == UsageType.READ:
            self.reads.append(usage)
        elif usage.usage_type == UsageType.WRITE:
            self.writes.append(usage)
        elif usage.usage_type == UsageType.ENTRY:
            self.entries.append(usage)


class UsageTracker:
    """
    Aggregates field usage across all sources.
    
    Key is (module, api_name) -> FieldProfile
    """
    
    def __init__(self):
        self._profiles: Dict[tuple, FieldProfile] = {}
    
    def register_field(self, module: str, field_label: str, api_name: str,
                       column_name: str, field_id: str, data_type: str):
        """Register a field from the Rosetta Stone."""
        key = (module, api_name)
        if key not in self._profiles:
            self._profiles[key] = FieldProfile(
                module=module,
                field_label=field_label,
                api_name=api_name,
                column_name=column_name,
                field_id=field_id,
                data_type=data_type,
            )
    
    def add_usage(self, usage: FieldUsage):
        """Add a usage record. Creates profile if needed."""
        key = (usage.module, usage.field_api_name)
        if key not in self._profiles:
            # Field referenced in automation but not in modules (orphan?)
            self._profiles[key] = FieldProfile(
                module=usage.module,
                field_label=usage.field_api_name,  # Best guess
                api_name=usage.field_api_name,
                column_name="",
                field_id="",
                data_type="unknown",
            )
        self._profiles[key].add_usage(usage)
    
    def get_profile(self, module: str, api_name: str) -> Optional[FieldProfile]:
        return self._profiles.get((module, api_name))
    
    def get_module_profiles(self, module: str) -> List[FieldProfile]:
        """Get all field profiles for a module, sorted by label."""
        return sorted(
            [p for p in self._profiles.values() if p.module == module],
            key=lambda p: p.field_label.lower()
        )
    
    def get_all_modules(self) -> List[str]:
        return sorted(set(p.module for p in self._profiles.values()))
    
    def get_used_fields(self, module: str = None) -> List[FieldProfile]:
        """Get only fields that are used in automation."""
        profiles = self._profiles.values()
        if module:
            profiles = [p for p in profiles if p.module == module]
        return sorted(
            [p for p in profiles if p.is_used],
            key=lambda p: (p.module, p.field_label.lower())
        )
    
    def get_unused_fields(self, module: str = None) -> List[FieldProfile]:
        """Get fields NOT used in any automation."""
        profiles = self._profiles.values()
        if module:
            profiles = [p for p in profiles if p.module == module]
        return sorted(
            [p for p in profiles if not p.is_used],
            key=lambda p: (p.module, p.field_label.lower())
        )
    
    def stats(self) -> dict:
        total = len(self._profiles)
        used = sum(1 for p in self._profiles.values() if p.is_used)
        return {
            'total_fields': total,
            'used_fields': used,
            'unused_fields': total - used,
            'total_reads': sum(len(p.reads) for p in self._profiles.values()),
            'total_writes': sum(len(p.writes) for p in self._profiles.values()),
            'total_entries': sum(len(p.entries) for p in self._profiles.values()),
        }
