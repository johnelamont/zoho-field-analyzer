"""
Zoho CRM Field Analyzer - Main Pipeline

Orchestrates the full analysis:
  1. Build Rosetta Stone from modules data
  2. Register all fields in usage tracker
  3. Run blueprint analyzer
  4. Run workflow analyzer  
  5. Run Deluge function analyzer
  6. Generate outputs (human + AI readable)
"""
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

from .rosetta import RosettaStone
from .usage import UsageTracker
from .blueprint_analyzer import BlueprintAnalyzer
from .workflow_analyzer import WorkflowAnalyzer
from .deluge_analyzer import DelugeAnalyzer
from . import output
from .html_builder import build_html_report

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_analysis(raw_dir: Path, output_dir: Path, client_name: str = "Client"):
    """
    Run the complete field analysis pipeline.
    
    Args:
        raw_dir: Path to raw extraction data (e.g., data/blades/raw)
        output_dir: Path to write analysis results
        client_name: Display name for the client (shown in HTML report badge)
    """
    start_time = datetime.now()
    logger.info(f"Starting field analysis on {raw_dir}")
    
    modules_dir = raw_dir / 'modules'
    blueprints_dir = raw_dir / 'blueprints'
    workflows_dir = raw_dir / 'workflows'
    functions_dir = raw_dir / 'functions'
    
    # Validate directories exist
    for d, name in [(modules_dir, 'modules'), (blueprints_dir, 'blueprints'),
                     (workflows_dir, 'workflows'), (functions_dir, 'functions')]:
        if not d.exists():
            logger.error(f"Missing directory: {d}")
            logger.error(f"Expected raw extraction data in {raw_dir}")
            return
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # =====================================================
    # Phase 1: Build the Rosetta Stone
    # =====================================================
    logger.info("Phase 1: Building Rosetta Stone...")
    rosetta = RosettaStone.from_raw_modules(modules_dir)
    
    # Save Rosetta Stone for reference
    rosetta_path = output_dir / 'rosetta_stone.json'
    with open(rosetta_path, 'w', encoding='utf-8') as f:
        json.dump(rosetta.to_dict(), f, indent=2, ensure_ascii=False)
    logger.info(f"Rosetta Stone saved to {rosetta_path}")
    
    # =====================================================
    # Phase 2: Register all fields in tracker
    # =====================================================
    logger.info("Phase 2: Registering fields in usage tracker...")
    tracker = UsageTracker()
    
    for module_name in rosetta.get_all_modules():
        for field in rosetta.get_module_fields(module_name):
            tracker.register_field(
                module=field.module,
                field_label=field.field_label,
                api_name=field.api_name,
                column_name=field.column_name,
                field_id=field.field_id,
                data_type=field.data_type,
            )
    
    initial_stats = tracker.stats()
    logger.info(f"Registered {initial_stats['total_fields']} fields "
                f"across {len(rosetta.get_all_modules())} modules")
    
    # =====================================================
    # Phase 3: Analyze blueprints
    # =====================================================
    logger.info("Phase 3: Analyzing blueprints...")
    bp_analyzer = BlueprintAnalyzer(rosetta, tracker)
    bp_analyzer.analyze_all(blueprints_dir)
    
    # Save blueprint function references for cross-referencing
    bp_func_refs = bp_analyzer.get_function_references(blueprints_dir)
    
    # Save unresolved fields log
    if bp_analyzer._unresolved:
        unresolved_path = output_dir / 'unresolved_blueprint_fields.json'
        with open(unresolved_path, 'w') as f:
            json.dump(bp_analyzer._unresolved, f, indent=2)
        logger.info(f"Saved {len(bp_analyzer._unresolved)} unresolved blueprint fields")
    
    # =====================================================
    # Phase 4: Analyze workflows
    # =====================================================
    logger.info("Phase 4: Analyzing workflows...")
    wf_analyzer = WorkflowAnalyzer(rosetta, tracker)
    wf_analyzer.analyze_all(workflows_dir)
    
    # =====================================================
    # Phase 5: Analyze Deluge functions
    # =====================================================
    logger.info("Phase 5: Analyzing Deluge functions...")
    deluge_analyzer = DelugeAnalyzer(rosetta, tracker)
    deluge_analyzer.analyze_all(functions_dir)
    
    # =====================================================
    # Phase 6: Generate outputs
    # =====================================================
    logger.info("Phase 6: Generating outputs...")
    
    # Master index
    output.generate_master_index(tracker, output_dir)
    logger.info("Generated master index")
    
    # Module synopses
    for module in tracker.get_all_modules():
        profiles = tracker.get_module_profiles(module)
        if profiles:  # Only generate for modules with fields
            output.generate_module_synopsis(tracker, module, output_dir)
    logger.info(f"Generated {len(tracker.get_all_modules())} module synopses")
    
    # Detailed field pages (only for used fields to keep output manageable)
    used_fields = tracker.get_used_fields()
    for profile in used_fields:
        output.generate_field_detail(profile, output_dir)
    logger.info(f"Generated {len(used_fields)} field detail pages")
    
    # AI-readable JSON
    ai_path = output.generate_ai_export(tracker, output_dir)
    logger.info(f"Generated AI export: {ai_path}")
    
    # =====================================================
    # Phase 7: Build self-contained HTML report
    # =====================================================
    logger.info("Phase 7: Building HTML report...")
    
    final_stats = tracker.stats()
    
    summary = {
        'analysis_date': datetime.now().isoformat(),
        'raw_data_dir': str(raw_dir),
        'output_dir': str(output_dir),
        'client_name': client_name,
        'elapsed_seconds': round((datetime.now() - start_time).total_seconds(), 1),
        'field_stats': final_stats,
        'blueprint_stats': bp_analyzer.stats,
        'workflow_stats': wf_analyzer.stats,
        'deluge_stats': deluge_analyzer.stats,
    }
    
    html_filename = f"{client_name.lower().replace(' ', '_')}_field_analysis.html"
    html_path = output_dir / html_filename
    build_html_report(tracker, summary, html_path, client_name=client_name)
    
    # =====================================================
    # Save summary and finish
    # =====================================================
    summary_path = output_dir / 'analysis_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    elapsed = summary['elapsed_seconds']
    
    logger.info("=" * 60)
    logger.info("ANALYSIS COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Client: {client_name}")
    logger.info(f"Total fields: {final_stats['total_fields']}")
    logger.info(f"Used in automation: {final_stats['used_fields']}")
    logger.info(f"Not used: {final_stats['unused_fields']}")
    logger.info(f"Read references: {final_stats['total_reads']}")
    logger.info(f"Write references: {final_stats['total_writes']}")
    logger.info(f"Entry references: {final_stats['total_entries']}")
    logger.info(f"Time: {elapsed:.1f}s")
    logger.info(f"Output: {output_dir}")
    logger.info(f"HTML report: {html_path}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python -m src.main <raw_data_dir> <output_dir> [client_name]")
        print()
        print("Example:")
        print("  python -m src.main data/blades/raw output/blades Blades")
        print("  python -m src.main data/lamont/raw output/lamont Lamont")
        sys.exit(1)
    
    raw_dir = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    name = sys.argv[3] if len(sys.argv) > 3 else raw_dir.parent.name
    
    run_analysis(raw_dir, out_dir, client_name=name)
