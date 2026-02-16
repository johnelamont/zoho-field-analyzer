"""
HTML Report Builder

Takes analysis results and produces a single self-contained HTML file
that clients can open in any browser. No server, no zip, no dependencies.

The HTML template is stored as a string constant in this module so the
entire analyzer is a pure Python package with no external file dependencies.
"""
import json
import logging
from pathlib import Path
from typing import Optional

from .usage import UsageTracker

logger = logging.getLogger(__name__)


def build_html_report(tracker: UsageTracker, summary: dict,
                      output_path: Path, client_name: str = "Client") -> Path:
    """
    Build a self-contained HTML field analysis viewer.
    
    Args:
        tracker: Completed UsageTracker with all field data
        summary: Analysis summary dict (from main pipeline)
        output_path: Where to write the HTML file
        client_name: Display name shown in the top bar badge
    
    Returns:
        Path to the generated HTML file
    """
    # Build the data payload
    payload = _build_payload(tracker, summary)
    payload_json = json.dumps(payload, separators=(',', ':'))
    
    # Inject into template
    html = HTML_TEMPLATE.replace('// __DATA_INJECT__', f'DATA = {payload_json};')
    html = html.replace('__CLIENT_NAME__', _esc_html(client_name.upper()))
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding='utf-8')
    
    size_kb = output_path.stat().st_size / 1024
    logger.info(f"HTML report: {output_path} ({size_kb:.0f} KB)")
    return output_path


def _build_payload(tracker: UsageTracker, summary: dict) -> dict:
    """Convert tracker data into the JSON structure the viewer expects."""
    modules = {}
    
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
        
        modules[module] = {"fields": fields}
    
    return {"summary": summary, "modules": modules}


def _usage_to_dict(usage) -> dict:
    return {
        "type": usage.usage_type.value,
        "source_type": usage.source_type.value,
        "source_name": usage.source_name,
        "source_id": usage.source_id,
        "details": usage.details,
    }


def _esc_html(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


# ============================================================
# HTML TEMPLATE
# ============================================================
# Everything below is the complete, self-contained viewer.
# The marker // __DATA_INJECT__ gets replaced with the JSON payload.
# The marker __CLIENT_NAME__ gets replaced with the client badge text.

HTML_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Zoho CRM Field Analysis</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg-primary: #0f1117;
  --bg-secondary: #161822;
  --bg-tertiary: #1c1f2e;
  --bg-card: #1a1d2b;
  --bg-hover: #222538;
  --bg-active: #282c42;
  --border: #2a2e42;
  --border-light: #333754;
  --text-primary: #e8eaf0;
  --text-secondary: #9699ab;
  --text-muted: #6b6e82;
  --accent-blue: #5b8af5;
  --accent-green: #4ecb8d;
  --accent-orange: #f0a050;
  --accent-red: #e85c5c;
  --accent-purple: #a78bfa;
  --tag-read-bg: rgba(91,138,245,0.12);
  --tag-read-text: #7da4f7;
  --tag-write-bg: rgba(78,203,141,0.12);
  --tag-write-text: #6dd9a5;
  --tag-entry-bg: rgba(167,139,250,0.12);
  --tag-entry-text: #baa8fc;
  --tag-unused-bg: rgba(107,110,130,0.08);
  --tag-unused-text: #6b6e82;
  --font-body: 'DM Sans', -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
  --radius: 8px;
  --radius-sm: 5px;
  --shadow: 0 2px 8px rgba(0,0,0,0.3);
}

html, body { height: 100%; overflow: hidden; }

body {
  font-family: var(--font-body);
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 14px;
  line-height: 1.5;
}

.app {
  display: grid;
  grid-template-columns: 280px 1fr;
  grid-template-rows: 56px 1fr;
  height: 100vh;
}

.topbar {
  grid-column: 1 / -1;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 16px;
  z-index: 10;
}

.topbar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.topbar-brand svg { width: 22px; height: 22px; color: var(--accent-blue); }

.topbar-brand h1 {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: -0.01em;
}

.topbar-brand .client-badge {
  font-size: 11px;
  font-weight: 500;
  background: var(--accent-blue);
  color: #fff;
  padding: 2px 8px;
  border-radius: 99px;
  letter-spacing: 0.02em;
}

.search-box {
  flex: 1;
  max-width: 480px;
  position: relative;
}

.search-box input {
  width: 100%;
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 7px 12px 7px 36px;
  color: var(--text-primary);
  font-family: var(--font-body);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s;
}

.search-box input::placeholder { color: var(--text-muted); }
.search-box input:focus { border-color: var(--accent-blue); }

.search-box svg {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  pointer-events: none;
}

.topbar-stats {
  display: flex;
  gap: 16px;
  margin-left: auto;
  flex-shrink: 0;
}

.stat-pill {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-secondary);
}

.stat-pill .num {
  font-weight: 600;
  font-family: var(--font-mono);
  font-size: 13px;
}

.stat-pill .num.blue { color: var(--accent-blue); }
.stat-pill .num.green { color: var(--accent-green); }
.stat-pill .num.orange { color: var(--accent-orange); }

.sidebar {
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  padding: 12px 0;
}

.sidebar::-webkit-scrollbar { width: 4px; }
.sidebar::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

.sidebar-section { padding: 0 12px; margin-bottom: 4px; }

.sidebar-section-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  padding: 8px 8px 6px;
}

.module-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.1s;
  user-select: none;
}

.module-item:hover { background: var(--bg-hover); }
.module-item.active { background: var(--bg-active); }

.module-item .name {
  flex: 1;
  font-size: 13px;
  font-weight: 400;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.module-item .count {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.module-item .usage-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.usage-dot.high { background: var(--accent-green); }
.usage-dot.medium { background: var(--accent-orange); }
.usage-dot.low { background: var(--accent-red); }
.usage-dot.none { background: var(--border); }

.main {
  overflow-y: auto;
  padding: 24px 32px;
  background: var(--bg-primary);
}

.main::-webkit-scrollbar { width: 6px; }
.main::-webkit-scrollbar-thumb { background: var(--border); border-radius: 4px; }

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.breadcrumb a {
  color: var(--accent-blue);
  text-decoration: none;
  cursor: pointer;
}

.breadcrumb a:hover { text-decoration: underline; }
.breadcrumb .sep { color: var(--border-light); }

.module-header { margin-bottom: 24px; }

.module-header h2 {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 10px;
}

.module-stats {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.module-stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px 18px;
  min-width: 120px;
}

.module-stat-card .label {
  font-size: 11px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 4px;
}

.module-stat-card .value {
  font-size: 22px;
  font-weight: 700;
  font-family: var(--font-mono);
}

.module-stat-card .value.blue { color: var(--accent-blue); }
.module-stat-card .value.green { color: var(--accent-green); }
.module-stat-card .value.orange { color: var(--accent-orange); }
.module-stat-card .value.purple { color: var(--accent-purple); }
.module-stat-card .value.muted { color: var(--text-muted); }

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.filter-btn {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 5px 12px;
  font-family: var(--font-body);
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.1s;
}

.filter-btn:hover { background: var(--bg-hover); color: var(--text-primary); }
.filter-btn.active { background: var(--accent-blue); color: #fff; border-color: var(--accent-blue); }
.filter-btn.active-green { background: var(--accent-green); color: #000; border-color: var(--accent-green); }
.filter-btn.active-orange { background: var(--accent-orange); color: #000; border-color: var(--accent-orange); }
.filter-btn.active-purple { background: var(--accent-purple); color: #000; border-color: var(--accent-purple); }

.filter-count {
  font-family: var(--font-mono);
  font-size: 11px;
  margin-left: 4px;
  opacity: 0.7;
}

.field-table {
  width: 100%;
  border-collapse: collapse;
}

.field-table th {
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--bg-primary);
  z-index: 1;
}

.field-table th.sortable { cursor: pointer; user-select: none; }
.field-table th.sortable:hover { color: var(--text-secondary); }

.field-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
  vertical-align: middle;
}

.field-table tr { transition: background 0.05s; }
.field-table tr:hover { background: var(--bg-hover); }
.field-table tr.clickable { cursor: pointer; }

.field-name-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-name-cell .label { font-weight: 500; color: var(--text-primary); }

.field-name-cell .api {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}

.type-badge {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-tertiary);
  padding: 2px 7px;
  border-radius: 3px;
  display: inline-block;
}

.usage-tags { display: flex; gap: 5px; flex-wrap: wrap; }

.usage-tag {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 3px;
  font-family: var(--font-mono);
  white-space: nowrap;
}

.usage-tag.read { background: var(--tag-read-bg); color: var(--tag-read-text); }
.usage-tag.write { background: var(--tag-write-bg); color: var(--tag-write-text); }
.usage-tag.entry { background: var(--tag-entry-bg); color: var(--tag-entry-text); }
.usage-tag.unused { background: var(--tag-unused-bg); color: var(--tag-unused-text); }

.field-detail-header { margin-bottom: 24px; }

.field-detail-header h2 {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 4px;
}

.field-detail-header .api-name {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--accent-blue);
  margin-bottom: 12px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 28px;
}

.info-item {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
}

.info-item .label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  margin-bottom: 3px;
}

.info-item .value {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  word-break: break-all;
}

.info-item .value.mono {
  font-family: var(--font-mono);
  font-size: 12px;
}

.usage-section { margin-bottom: 28px; }

.usage-section h3 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.usage-section h3 .count-badge {
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 3px;
}

.usage-section h3 .count-badge.read { background: var(--tag-read-bg); color: var(--tag-read-text); }
.usage-section h3 .count-badge.write { background: var(--tag-write-bg); color: var(--tag-write-text); }
.usage-section h3 .count-badge.entry { background: var(--tag-entry-bg); color: var(--tag-entry-text); }

.usage-list { list-style: none; }

.usage-list li {
  padding: 10px 14px;
  border-left: 3px solid var(--border);
  margin-bottom: 6px;
  background: var(--bg-card);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  font-size: 13px;
}

.usage-list li.source-blueprint { border-left-color: var(--accent-orange); }
.usage-list li.source-workflow { border-left-color: var(--accent-blue); }
.usage-list li.source-function { border-left-color: var(--accent-green); }

.usage-list .source-name {
  font-weight: 500;
  color: var(--text-primary);
  margin-bottom: 3px;
}

.usage-list .source-type-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-right: 6px;
  opacity: 0.7;
}

.usage-list .detail-line {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 3px;
}

.usage-list .detail-line code {
  font-family: var(--font-mono);
  font-size: 11px;
  background: var(--bg-tertiary);
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--text-primary);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-top: 20px;
}

.overview-module-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  cursor: pointer;
  transition: all 0.1s;
}

.overview-module-card:hover {
  border-color: var(--accent-blue);
  background: var(--bg-hover);
  transform: translateY(-1px);
}

.overview-module-card .mod-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.overview-module-card .mod-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-secondary);
}

.overview-module-card .mod-bar {
  height: 4px;
  background: var(--bg-tertiary);
  border-radius: 2px;
  margin-top: 10px;
  overflow: hidden;
}

.overview-module-card .mod-bar-fill {
  height: 100%;
  border-radius: 2px;
  background: var(--accent-green);
  transition: width 0.3s;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
}

.empty-state .icon { font-size: 40px; margin-bottom: 12px; opacity: 0.3; }
.empty-state p { font-size: 14px; }

.search-results-header { margin-bottom: 16px; }
.search-results-header h2 { font-size: 18px; font-weight: 600; }

.search-results-header .result-count {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

.search-result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  margin-bottom: 6px;
  cursor: pointer;
  transition: all 0.1s;
}

.search-result-item:hover {
  border-color: var(--accent-blue);
  background: var(--bg-hover);
}

.search-result-item .module-label {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-tertiary);
  padding: 2px 7px;
  border-radius: 3px;
  flex-shrink: 0;
  min-width: 80px;
  text-align: center;
}

.search-result-item .field-info { flex: 1; }
.search-result-item .field-info .label { font-weight: 500; font-size: 13px; }

.search-result-item .field-info .api {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}

mark {
  background: rgba(91,138,245,0.25);
  color: var(--text-primary);
  border-radius: 2px;
  padding: 0 1px;
}

@media (max-width: 768px) {
  .app { grid-template-columns: 1fr; grid-template-rows: 56px auto 1fr; }
  .sidebar { max-height: 200px; border-right: none; border-bottom: 1px solid var(--border); }
  .main { padding: 16px; }
  .topbar-stats { display: none; }
}
</style>
</head>
<body>
<div class="app">
  <div class="topbar">
    <div class="topbar-brand">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
      <h1>Field Analysis</h1>
      <span class="client-badge" id="clientBadge">__CLIENT_NAME__</span>
    </div>
    <div class="search-box">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
      <input type="text" id="searchInput" placeholder="Search fields by name, API name, or column name..." autocomplete="off">
    </div>
    <div class="topbar-stats">
      <div class="stat-pill"><span class="num blue" id="statTotal">0</span> fields</div>
      <div class="stat-pill"><span class="num green" id="statUsed">0</span> used</div>
      <div class="stat-pill"><span class="num orange" id="statUnused">0</span> unused</div>
    </div>
  </div>
  <div class="sidebar" id="sidebar"></div>
  <div class="main" id="mainContent"></div>
</div>
<script>
let DATA = null;
const state = { currentModule: null, currentField: null, searchQuery: '', filter: 'all', sortCol: 'label', sortDir: 'asc' };

function init() {
  if (!DATA) { document.getElementById('mainContent').innerHTML = '<div class="empty-state"><div class="icon">&#9888;</div><p>No data loaded</p></div>'; return; }
  const s = DATA.summary.field_stats;
  document.getElementById('statTotal').textContent = s.total_fields.toLocaleString();
  document.getElementById('statUsed').textContent = s.used_fields.toLocaleString();
  document.getElementById('statUnused').textContent = s.unused_fields.toLocaleString();
  renderSidebar();
  renderOverview();
  document.getElementById('searchInput').addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim();
    if (state.searchQuery.length >= 2) renderSearchResults();
    else if (state.searchQuery.length === 0) {
      if (state.currentField) renderFieldDetail(state.currentModule, state.currentField);
      else if (state.currentModule) renderModuleView(state.currentModule);
      else renderOverview();
    }
  });
  document.getElementById('searchInput').addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { e.target.value = ''; state.searchQuery = '';
      if (state.currentField) renderFieldDetail(state.currentModule, state.currentField);
      else if (state.currentModule) renderModuleView(state.currentModule);
      else renderOverview();
    }
  });
}

function renderSidebar() {
  const sb = document.getElementById('sidebar');
  const mods = Object.keys(DATA.modules).sort((a, b) => {
    const au = Object.values(DATA.modules[a].fields).filter(f => f.is_used).length;
    const bu = Object.values(DATA.modules[b].fields).filter(f => f.is_used).length;
    return bu - au;
  });
  const coreModules = mods.filter(m => Object.values(DATA.modules[m].fields).some(f => f.is_used));
  const otherModules = mods.filter(m => !Object.values(DATA.modules[m].fields).some(f => f.is_used));
  let html = '<div class="sidebar-section"><div class="sidebar-section-label">Active Modules</div>';
  coreModules.forEach(m => { html += moduleItemHtml(m); });
  html += '</div>';
  if (otherModules.length) {
    html += '<div class="sidebar-section"><div class="sidebar-section-label">No Automation</div>';
    otherModules.forEach(m => { html += moduleItemHtml(m); });
    html += '</div>';
  }
  sb.innerHTML = html;
  sb.querySelectorAll('.module-item').forEach(el => {
    el.addEventListener('click', () => {
      state.currentModule = el.dataset.module; state.currentField = null;
      state.searchQuery = ''; document.getElementById('searchInput').value = '';
      renderModuleView(el.dataset.module); updateSidebarActive();
    });
  });
}

function moduleItemHtml(mod) {
  const fields = Object.values(DATA.modules[mod].fields);
  const total = fields.length;
  const used = fields.filter(f => f.is_used).length;
  const pct = total > 0 ? used / total : 0;
  let dotClass = 'none';
  if (pct > 0.5) dotClass = 'high'; else if (pct > 0.2) dotClass = 'medium'; else if (pct > 0) dotClass = 'low';
  const displayName = mod.replace(/_/g, ' ').replace(/zrouteiqzcrm /g, '');
  return '<div class="module-item" data-module="' + mod + '"><span class="usage-dot ' + dotClass + '"></span><span class="name" title="' + mod + '">' + displayName + '</span><span class="count">' + used + '/' + total + '</span></div>';
}

function updateSidebarActive() {
  document.querySelectorAll('.module-item').forEach(el => { el.classList.toggle('active', el.dataset.module === state.currentModule); });
}

function renderOverview() {
  state.currentModule = null; state.currentField = null; updateSidebarActive();
  const s = DATA.summary.field_stats;
  const mods = Object.keys(DATA.modules).sort((a, b) => {
    const au = Object.values(DATA.modules[a].fields).filter(f => f.is_used).length;
    const bu = Object.values(DATA.modules[b].fields).filter(f => f.is_used).length;
    return bu - au;
  });
  let html = '<div class="module-header"><h2>All Modules</h2><div class="module-stats">' +
    '<div class="module-stat-card"><div class="label">Total Fields</div><div class="value blue">' + s.total_fields.toLocaleString() + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Used</div><div class="value green">' + s.used_fields.toLocaleString() + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Unused</div><div class="value muted">' + s.unused_fields.toLocaleString() + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Read Refs</div><div class="value blue">' + s.total_reads.toLocaleString() + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Write Refs</div><div class="value green">' + s.total_writes.toLocaleString() + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Entry Refs</div><div class="value purple">' + s.total_entries.toLocaleString() + '</div></div>' +
    '</div></div><div class="overview-grid">';
  mods.forEach(mod => {
    const fields = Object.values(DATA.modules[mod].fields);
    const total = fields.length; const used = fields.filter(f => f.is_used).length;
    const pct = total > 0 ? ((used / total) * 100).toFixed(0) : 0;
    html += '<div class="overview-module-card" data-module="' + mod + '"><div class="mod-name">' + mod.replace(/_/g, ' ') + '</div><div class="mod-stats"><span>' + used + ' used</span><span>' + (total - used) + ' unused</span></div><div class="mod-bar"><div class="mod-bar-fill" style="width:' + pct + '%"></div></div></div>';
  });
  html += '</div>';
  const main = document.getElementById('mainContent'); main.innerHTML = html; main.scrollTop = 0;
  main.querySelectorAll('.overview-module-card').forEach(el => {
    el.addEventListener('click', () => { state.currentModule = el.dataset.module; state.currentField = null; renderModuleView(el.dataset.module); updateSidebarActive(); });
  });
}

function renderModuleView(mod) {
  const modData = DATA.modules[mod]; if (!modData) return;
  const fields = Object.values(modData.fields);
  const used = fields.filter(f => f.is_used); const unused = fields.filter(f => !f.is_used);
  const totalReads = fields.reduce((s, f) => s + f.reads.length, 0);
  const totalWrites = fields.reduce((s, f) => s + f.writes.length, 0);
  const totalEntries = fields.reduce((s, f) => s + f.entries.length, 0);
  const displayName = mod.replace(/_/g, ' ');
  let html = '<div class="breadcrumb"><a onclick="renderOverview()">All Modules</a><span class="sep">&#8250;</span><span>' + displayName + '</span></div>';
  html += '<div class="module-header"><h2>' + displayName + '</h2><div class="module-stats">' +
    '<div class="module-stat-card"><div class="label">Total Fields</div><div class="value blue">' + fields.length + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Used</div><div class="value green">' + used.length + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Unused</div><div class="value muted">' + unused.length + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Reads</div><div class="value blue">' + totalReads + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Writes</div><div class="value green">' + totalWrites + '</div></div>' +
    '<div class="module-stat-card"><div class="label">Entries</div><div class="value purple">' + totalEntries + '</div></div></div></div>';
  const fltrs = [['all','All',fields.length,''],['used','Used',used.length,'-green'],['unused','Unused',unused.length,''],['read','Has Reads',fields.filter(f=>f.reads.length>0).length,''],['write','Has Writes',fields.filter(f=>f.writes.length>0).length,'-green'],['entry','Has Entries',fields.filter(f=>f.entries.length>0).length,'-purple']];
  html += '<div class="filters">';
  fltrs.forEach(([k,lbl,cnt,suf]) => { html += '<button class="filter-btn ' + (state.filter===k ? 'active'+suf : '') + '" data-filter="' + k + '">' + lbl + ' <span class="filter-count">' + cnt + '</span></button>'; });
  html += '</div>';
  let filtered = fields;
  if (state.filter === 'used') filtered = fields.filter(f => f.is_used);
  else if (state.filter === 'unused') filtered = fields.filter(f => !f.is_used);
  else if (state.filter === 'read') filtered = fields.filter(f => f.reads.length > 0);
  else if (state.filter === 'write') filtered = fields.filter(f => f.writes.length > 0);
  else if (state.filter === 'entry') filtered = fields.filter(f => f.entries.length > 0);
  filtered.sort((a, b) => {
    let va, vb;
    if (state.sortCol === 'label') { va = a.label.toLowerCase(); vb = b.label.toLowerCase(); }
    else if (state.sortCol === 'type') { va = a.data_type; vb = b.data_type; }
    else if (state.sortCol === 'usage') { va = a.reads.length + a.writes.length + a.entries.length; vb = b.reads.length + b.writes.length + b.entries.length; }
    else { va = a.label.toLowerCase(); vb = b.label.toLowerCase(); }
    if (typeof va === 'string') { const c = va.localeCompare(vb); return state.sortDir === 'asc' ? c : -c; }
    return state.sortDir === 'asc' ? va - vb : vb - va;
  });
  const arrow = (col) => state.sortCol === col ? (state.sortDir === 'asc' ? ' &#8593;' : ' &#8595;') : '';
  html += '<table class="field-table"><thead><tr><th class="sortable" data-col="label">Field' + arrow('label') + '</th><th class="sortable" data-col="type">Type' + arrow('type') + '</th><th class="sortable" data-col="usage">Usage' + arrow('usage') + '</th></tr></thead><tbody>';
  filtered.forEach(f => {
    const tags = [];
    if (f.reads.length) tags.push('<span class="usage-tag read">R:' + f.reads.length + '</span>');
    if (f.writes.length) tags.push('<span class="usage-tag write">W:' + f.writes.length + '</span>');
    if (f.entries.length) tags.push('<span class="usage-tag entry">E:' + f.entries.length + '</span>');
    if (!f.is_used) tags.push('<span class="usage-tag unused">unused</span>');
    html += '<tr class="clickable" data-field="' + f.api_name + '"><td><div class="field-name-cell"><span class="label">' + esc(f.label) + '</span><span class="api">' + esc(f.api_name) + '</span></div></td><td><span class="type-badge">' + esc(f.data_type) + '</span></td><td><div class="usage-tags">' + tags.join('') + '</div></td></tr>';
  });
  html += '</tbody></table>';
  if (filtered.length === 0) html += '<div class="empty-state"><div class="icon">&#128269;</div><p>No fields match this filter</p></div>';
  const main = document.getElementById('mainContent'); main.innerHTML = html; main.scrollTop = 0;
  main.querySelectorAll('.filter-btn').forEach(btn => { btn.addEventListener('click', () => { state.filter = btn.dataset.filter; renderModuleView(mod); }); });
  main.querySelectorAll('th.sortable').forEach(th => { th.addEventListener('click', () => { const col = th.dataset.col; if (state.sortCol === col) state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc'; else { state.sortCol = col; state.sortDir = col === 'usage' ? 'desc' : 'asc'; } renderModuleView(mod); }); });
  main.querySelectorAll('tr.clickable').forEach(tr => { tr.addEventListener('click', () => { state.currentField = tr.dataset.field; renderFieldDetail(mod, tr.dataset.field); }); });
}

function renderFieldDetail(mod, apiName) {
  const modData = DATA.modules[mod]; if (!modData) return;
  const f = modData.fields[apiName]; if (!f) return;
  state.currentModule = mod; state.currentField = apiName; updateSidebarActive();
  const displayMod = mod.replace(/_/g, ' ');
  let html = '<div class="breadcrumb"><a onclick="renderOverview()">All Modules</a><span class="sep">&#8250;</span><a onclick="state.filter=\'all\'; renderModuleView(\'' + mod + '\')">' + displayMod + '</a><span class="sep">&#8250;</span><span>' + esc(f.label) + '</span></div>';
  html += '<div class="field-detail-header"><h2>' + esc(f.label) + '</h2><div class="api-name">' + esc(f.api_name) + '</div></div>';
  html += '<div class="info-grid">' +
    '<div class="info-item"><div class="label">Module</div><div class="value">' + displayMod + '</div></div>' +
    '<div class="info-item"><div class="label">API Name</div><div class="value mono">' + esc(f.api_name) + '</div></div>' +
    '<div class="info-item"><div class="label">Column Name</div><div class="value mono">' + esc(f.column_name || '\u2014') + '</div></div>' +
    '<div class="info-item"><div class="label">Field ID</div><div class="value mono">' + esc(f.field_id || '\u2014') + '</div></div>' +
    '<div class="info-item"><div class="label">Data Type</div><div class="value">' + esc(f.data_type) + '</div></div>' +
    '<div class="info-item"><div class="label">Usage</div><div class="value">' + (f.is_used ? f.usage_summary : 'Not used in automation') + '</div></div></div>';
  if (f.writes.length > 0) {
    html += '<div class="usage-section"><h3>Written By <span class="count-badge write">' + f.writes.length + '</span></h3><ul class="usage-list">';
    f.writes.forEach(u => { html += usageItemHtml(u, 'write'); }); html += '</ul></div>';
  }
  if (f.reads.length > 0) {
    html += '<div class="usage-section"><h3>Read By <span class="count-badge read">' + f.reads.length + '</span></h3><ul class="usage-list">';
    f.reads.forEach(u => { html += usageItemHtml(u, 'read'); }); html += '</ul></div>';
  }
  if (f.entries.length > 0) {
    html += '<div class="usage-section"><h3>Manual Entry <span class="count-badge entry">' + f.entries.length + '</span></h3><ul class="usage-list">';
    f.entries.forEach(u => { html += usageItemHtml(u, 'entry'); }); html += '</ul></div>';
  }
  if (!f.is_used) html += '<div class="empty-state" style="padding:40px"><div class="icon">&#128203;</div><p>This field is not referenced by any blueprint, workflow, or function.</p></div>';
  const main = document.getElementById('mainContent'); main.innerHTML = html; main.scrollTop = 0;
}

function usageItemHtml(u, type) {
  const sourceClass = 'source-' + u.source_type;
  const sourceLabel = u.source_type.charAt(0).toUpperCase() + u.source_type.slice(1);
  let details = '';
  if (type === 'write') {
    if (u.details.value) details += '<div class="detail-line">Set to: <code>' + esc(String(u.details.value)) + '</code></div>';
    if (u.details.action_name) details += '<div class="detail-line">Action: ' + esc(u.details.action_name) + '</div>';
    if (u.details.update_name) details += '<div class="detail-line">Update: ' + esc(u.details.update_name) + '</div>';
    if (u.details.context) details += '<div class="detail-line"><code>' + esc(u.details.context) + '</code></div>';
    if (u.details.line) details += '<div class="detail-line">Line ' + u.details.line + '</div>';
  } else if (type === 'read') {
    if (u.details.comparator) {
      let cond = u.details.comparator;
      if (u.details.value) {
        if (Array.isArray(u.details.value)) cond += ' [' + u.details.value.map(v => esc(String(v))).join(', ') + ']';
        else cond += ' "' + esc(String(u.details.value)) + '"';
      }
      details += '<div class="detail-line">Condition: <code>' + cond + '</code></div>';
    }
    if (u.details.line) details += '<div class="detail-line">Line ' + u.details.line + '</div>';
  } else if (type === 'entry') {
    details += '<div class="detail-line">' + (u.details.mandatory ? 'Required' : 'Optional') + '</div>';
  }
  return '<li class="' + sourceClass + '"><div class="source-name"><span class="source-type-label">' + sourceLabel + '</span>' + esc(u.source_name) + '</div>' + details + '</li>';
}

function renderSearchResults() {
  const q = state.searchQuery.toLowerCase(); const results = [];
  for (const [mod, modData] of Object.entries(DATA.modules)) {
    for (const [apiName, f] of Object.entries(modData.fields)) {
      const haystack = (f.label + ' ' + f.api_name + ' ' + f.column_name + ' ' + f.field_id).toLowerCase();
      if (haystack.includes(q)) results.push({ mod, apiName, field: f, score: f.is_used ? 1 : 0 });
    }
  }
  results.sort((a, b) => b.score - a.score || a.field.label.localeCompare(b.field.label));
  const capped = results.slice(0, 100);
  let html = '<div class="search-results-header"><h2>Search Results</h2><div class="result-count">' + results.length + ' field' + (results.length !== 1 ? 's' : '') + ' found' + (results.length > 100 ? ' (showing first 100)' : '') + '</div></div>';
  capped.forEach(r => {
    const tags = [];
    if (r.field.reads.length) tags.push('<span class="usage-tag read">R:' + r.field.reads.length + '</span>');
    if (r.field.writes.length) tags.push('<span class="usage-tag write">W:' + r.field.writes.length + '</span>');
    if (r.field.entries.length) tags.push('<span class="usage-tag entry">E:' + r.field.entries.length + '</span>');
    if (!r.field.is_used) tags.push('<span class="usage-tag unused">unused</span>');
    html += '<div class="search-result-item" data-module="' + r.mod + '" data-field="' + r.apiName + '"><span class="module-label">' + r.mod.replace(/_/g, ' ') + '</span><div class="field-info"><div class="label">' + highlight(r.field.label, state.searchQuery) + '</div><div class="api">' + highlight(r.field.api_name, state.searchQuery) + '</div></div><div class="usage-tags">' + tags.join('') + '</div></div>';
  });
  if (results.length === 0) html += '<div class="empty-state"><div class="icon">&#128269;</div><p>No fields match your search</p></div>';
  const main = document.getElementById('mainContent'); main.innerHTML = html; main.scrollTop = 0;
  main.querySelectorAll('.search-result-item').forEach(el => {
    el.addEventListener('click', () => { state.currentModule = el.dataset.module; state.currentField = el.dataset.field; renderFieldDetail(el.dataset.module, el.dataset.field); updateSidebarActive(); });
  });
}

function esc(str) { const d = document.createElement('div'); d.textContent = str; return d.innerHTML; }

function highlight(text, query) {
  if (!query) return esc(text);
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return esc(text);
  return esc(text.slice(0, idx)) + '<mark>' + esc(text.slice(idx, idx + query.length)) + '</mark>' + esc(text.slice(idx + query.length));
}

document.addEventListener('DOMContentLoaded', init);
</script>
<script id="dataScript">
// __DATA_INJECT__
</script>
</body>
</html>
'''
