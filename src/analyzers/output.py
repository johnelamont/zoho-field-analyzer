"""
Output generators for field analysis results.

Generates:
  1. Module synopsis (Goal 2a) - table of fields per module
  2. Detailed field analysis (Goal 2b) - full usage profile per field  
  3. AI-readable JSON export
"""
import json
import logging
from pathlib import Path
from typing import List, Dict

from .usage import UsageTracker, FieldProfile, UsageType, SourceType

logger = logging.getLogger(__name__)


def generate_module_synopsis(tracker: UsageTracker, module: str, 
                              output_dir: Path) -> Path:
    """
    Goal 2a: Module synopsis with field table.
    
    Generates a markdown file with:
    - Module summary stats
    - Alphabetical table of fields with label, api_name, type, usage summary, link
    """
    profiles = tracker.get_module_profiles(module)
    used = [p for p in profiles if p.is_used]
    unused = [p for p in profiles if not p.is_used]
    
    lines = []
    lines.append(f"# {module} - Field Synopsis")
    lines.append("")
    lines.append(f"**Total fields:** {len(profiles)} | "
                 f"**Used in automation:** {len(used)} | "
                 f"**Not used:** {len(unused)}")
    lines.append("")
    
    # Field table
    lines.append("## Fields")
    lines.append("")
    lines.append("| Field Label | API Name | Type | Usage | Detail |")
    lines.append("|---|---|---|---|---|")
    
    for p in profiles:
        usage = p.usage_summary
        detail_link = f"[detail](fields/{module}_{p.api_name}.md)"
        lines.append(f"| {p.field_label} | `{p.api_name}` | {p.data_type} | {usage} | {detail_link} |")
    
    lines.append("")
    
    # Summary by usage type
    lines.append("## Usage Summary")
    lines.append("")
    lines.append(f"- **Read in conditions:** {sum(len(p.reads) for p in profiles)} times across {sum(1 for p in profiles if p.reads)} fields")
    lines.append(f"- **Written by automation:** {sum(len(p.writes) for p in profiles)} times across {sum(1 for p in profiles if p.writes)} fields")
    lines.append(f"- **Manual entry (blueprints):** {sum(len(p.entries) for p in profiles)} times across {sum(1 for p in profiles if p.entries)} fields")
    lines.append("")
    
    filepath = output_dir / f"{module}_synopsis.md"
    filepath.write_text('\n'.join(lines), encoding='utf-8')
    return filepath


def generate_field_detail(profile: FieldProfile, output_dir: Path) -> Path:
    """
    Goal 2b: Detailed field analysis.
    
    Shows everything known about a field:
    - Basic metadata
    - All automation usages (read, write, entry)
    - Where it's updated and to what values
    - Where it's evaluated and for what conditions
    """
    lines = []
    lines.append(f"# {profile.module}.{profile.api_name}")
    lines.append("")
    
    # Basic info
    lines.append("## Field Info")
    lines.append("")
    lines.append(f"| Property | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| **Label** | {profile.field_label} |")
    lines.append(f"| **API Name** | `{profile.api_name}` |")
    lines.append(f"| **Column Name** | `{profile.column_name}` |")
    lines.append(f"| **Field ID** | `{profile.field_id}` |")
    lines.append(f"| **Data Type** | {profile.data_type} |")
    lines.append(f"| **Module** | {profile.module} |")
    lines.append("")
    
    # Usage summary
    lines.append("## Usage Summary")
    lines.append("")
    if not profile.is_used:
        lines.append("**This field is not used in any automation.**")
    else:
        lines.append(f"- **Read (evaluated):** {len(profile.reads)} times")
        lines.append(f"- **Written (updated):** {len(profile.writes)} times")
        lines.append(f"- **Manual entry:** {len(profile.entries)} times")
    lines.append("")
    
    # WRITES - where is this field updated?
    if profile.writes:
        lines.append("## Written By (Field Updates)")
        lines.append("")
        
        # Group by source type
        bp_writes = [w for w in profile.writes if w.source_type == SourceType.BLUEPRINT]
        wf_writes = [w for w in profile.writes if w.source_type == SourceType.WORKFLOW]
        fn_writes = [w for w in profile.writes if w.source_type == SourceType.FUNCTION]
        
        if bp_writes:
            lines.append("### Blueprint Updates")
            lines.append("")
            for w in bp_writes:
                value = w.details.get('value', '')
                update_name = w.details.get('update_name', '')
                lines.append(f"- **{w.source_name}**")
                if value:
                    lines.append(f"  - Set to: `{value}`")
                if update_name:
                    lines.append(f"  - Update action: {update_name}")
            lines.append("")
        
        if wf_writes:
            lines.append("### Workflow Updates")
            lines.append("")
            for w in wf_writes:
                value = w.details.get('value', '')
                action_name = w.details.get('action_name', '')
                update_type = w.details.get('update_type', '')
                lines.append(f"- **{w.source_name}**")
                if action_name:
                    lines.append(f"  - Action: {action_name}")
                if value:
                    lines.append(f"  - Set to: `{value}`")
                if update_type:
                    lines.append(f"  - Type: {update_type}")
            lines.append("")
        
        if fn_writes:
            lines.append("### Function Updates")
            lines.append("")
            for w in fn_writes:
                line_num = w.details.get('line', '')
                context = w.details.get('context', '')
                lines.append(f"- **{w.source_name}**")
                if line_num:
                    lines.append(f"  - Line: {line_num}")
                if context:
                    lines.append(f"  - Code: `{context}`")
            lines.append("")
    
    # READS - where is this field evaluated?
    if profile.reads:
        lines.append("## Read By (Evaluated In)")
        lines.append("")
        
        bp_reads = [r for r in profile.reads if r.source_type == SourceType.BLUEPRINT]
        wf_reads = [r for r in profile.reads if r.source_type == SourceType.WORKFLOW]
        fn_reads = [r for r in profile.reads if r.source_type == SourceType.FUNCTION]
        
        if bp_reads:
            lines.append("### Blueprint Conditions")
            lines.append("")
            for r in bp_reads:
                lines.append(f"- **{r.source_name}**")
                criteria = r.details.get('criteria_string', '')
                if criteria:
                    lines.append(f"  - Criteria: {criteria[:200]}")
            lines.append("")
        
        if wf_reads:
            lines.append("### Workflow Conditions")
            lines.append("")
            for r in wf_reads:
                comparator = r.details.get('comparator', '')
                value = r.details.get('value', '')
                lines.append(f"- **{r.source_name}**")
                if comparator:
                    cond = f"{comparator}"
                    if value:
                        if isinstance(value, list):
                            cond += f" [{', '.join(str(v) for v in value)}]"
                        else:
                            cond += f" `{value}`"
                    lines.append(f"  - Condition: {cond}")
            lines.append("")
        
        if fn_reads:
            lines.append("### Function Reads")
            lines.append("")
            for r in fn_reads:
                line_num = r.details.get('line', '')
                lines.append(f"- **{r.source_name}**" + (f" (line {line_num})" if line_num else ""))
            lines.append("")
    
    # ENTRIES - blueprint manual entry
    if profile.entries:
        lines.append("## Manual Entry (Blueprint DURING Tab)")
        lines.append("")
        for e in profile.entries:
            mandatory = "Required" if e.details.get('mandatory') else "Optional"
            lines.append(f"- **{e.source_name}** ({mandatory})")
        lines.append("")
    
    # Write file
    fields_dir = output_dir / 'fields'
    fields_dir.mkdir(exist_ok=True)
    filepath = fields_dir / f"{profile.module}_{profile.api_name}.md"
    filepath.write_text('\n'.join(lines), encoding='utf-8')
    return filepath


def generate_ai_export(tracker: UsageTracker, output_dir: Path) -> Path:
    """
    AI-readable JSON export of the complete field analysis.
    
    Structure:
    {
      "modules": {
        "Deals": {
          "fields": {
            "Stage": {
              "label": "Stage",
              "api_name": "Stage",
              "column_name": "STAGE",
              "data_type": "picklist",
              "reads": [...],
              "writes": [...],
              "entries": [...]
            }
          }
        }
      }
    }
    """
    export = {"modules": {}}
    
    for module in tracker.get_all_modules():
        profiles = tracker.get_module_profiles(module)
        module_data = {"fields": {}}
        
        for p in profiles:
            field_data = {
                "label": p.field_label,
                "api_name": p.api_name,
                "column_name": p.column_name,
                "field_id": p.field_id,
                "data_type": p.data_type,
                "is_used": p.is_used,
                "usage_summary": p.usage_summary,
                "reads": [_usage_to_dict(u) for u in p.reads],
                "writes": [_usage_to_dict(u) for u in p.writes],
                "entries": [_usage_to_dict(u) for u in p.entries],
            }
            module_data["fields"][p.api_name] = field_data
        
        export["modules"][module] = module_data
    
    filepath = output_dir / "field_analysis.json"
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(export, f, indent=2, ensure_ascii=False)
    
    return filepath


def generate_master_index(tracker: UsageTracker, output_dir: Path) -> Path:
    """Generate a master index linking to all module synopses."""
    lines = []
    lines.append("# Zoho CRM Field Analysis")
    lines.append("")
    
    stats = tracker.stats()
    lines.append(f"**Total fields analyzed:** {stats['total_fields']}")
    lines.append(f"**Fields used in automation:** {stats['used_fields']}")
    lines.append(f"**Fields not in automation:** {stats['unused_fields']}")
    lines.append(f"**Total read references:** {stats['total_reads']}")
    lines.append(f"**Total write references:** {stats['total_writes']}")
    lines.append(f"**Total manual entry references:** {stats['total_entries']}")
    lines.append("")
    
    lines.append("## Modules")
    lines.append("")
    lines.append("| Module | Total Fields | Used | Unused | Synopsis |")
    lines.append("|---|---|---|---|---|")
    
    for module in sorted(tracker.get_all_modules()):
        profiles = tracker.get_module_profiles(module)
        used = sum(1 for p in profiles if p.is_used)
        unused = len(profiles) - used
        link = f"[{module}]({module}_synopsis.md)"
        lines.append(f"| {link} | {len(profiles)} | {used} | {unused} | [view]({module}_synopsis.md) |")
    
    lines.append("")
    
    filepath = output_dir / "INDEX.md"
    filepath.write_text('\n'.join(lines), encoding='utf-8')
    return filepath


def generate_html_viewer(tracker: UsageTracker, output_dir: Path,
                         client_name: str = "CLIENT",
                         template_path: Path = None) -> Path:
    """
    Generate a self-contained interactive HTML viewer.
    
    Embeds all analysis data as JSON inside a single HTML file.
    Client just double-clicks to open — no server, no unzipping.
    
    Args:
        tracker: Completed usage tracker with all field data
        output_dir: Where to write the HTML file
        client_name: Display name shown in the viewer header badge
        template_path: Path to viewer_template.html. If None, looks
                       in the same directory as this module.
    
    Returns:
        Path to the generated HTML file
    """
    # Find the template
    if template_path is None:
        # Look next to this source file, then in parent dir
        here = Path(__file__).parent
        candidates = [
            here / 'viewer_template.html',
            here.parent / 'viewer_template.html',
        ]
        for c in candidates:
            if c.exists():
                template_path = c
                break
        if template_path is None:
            raise FileNotFoundError(
                f"viewer_template.html not found. Searched: {[str(c) for c in candidates]}"
            )
    
    template = template_path.read_text(encoding='utf-8')
    
    # Build the data payload
    stats = tracker.stats()
    summary = {"field_stats": stats}
    
    modules_export = {}
    for module in tracker.get_all_modules():
        profiles = tracker.get_module_profiles(module)
        fields = {}
        for p in profiles:
            fields[p.api_name] = {
                "label": p.field_label,
                "api_name": p.api_name,
                "column_name": p.column_name,
                "field_id": p.field_id,
                "data_type": p.data_type,
                "is_used": p.is_used,
                "usage_summary": p.usage_summary,
                "reads": [_usage_to_dict(u) for u in p.reads],
                "writes": [_usage_to_dict(u) for u in p.writes],
                "entries": [_usage_to_dict(u) for u in p.entries],
            }
        modules_export[module] = {"fields": fields}
    
    payload = {"summary": summary, "modules": modules_export}
    payload_json = json.dumps(payload, separators=(',', ':'))
    
    # Inject data and client name into template
    data_script = f'DATA = {payload_json};'
    html = template.replace('// __DATA_INJECT__', data_script)
    html = html.replace('>BLADES<', f'>{client_name.upper()}<')
    
    # Write output
    safe_name = client_name.lower().replace(' ', '_')
    filepath = output_dir / f"{safe_name}_field_analysis.html"
    filepath.write_text(html, encoding='utf-8')
    
    logger.info(f"HTML viewer: {filepath} ({filepath.stat().st_size / 1024:.0f} KB)")
    return filepath


def _usage_to_dict(usage) -> dict:
    """Convert a FieldUsage to a serializable dict."""
    return {
        "type": usage.usage_type.value,
        "source_type": usage.source_type.value,
        "source_name": usage.source_name,
        "source_id": usage.source_id,
        "details": usage.details,
    }
