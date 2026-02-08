# Zoho Field Analyzer

A comprehensive tool for extracting and analyzing Zoho CRM metadata to understand how and where field values are transformed across your CRM configuration.

## Project Goals

### Phase 1: Data Extraction
Extract all Zoho CRM metadata that affects field values:
- Deluge Functions (standalone scripts)
- Workflows (field updates, tasks, notifications)
- Blueprints (transition logic)
- Modules (field definitions, layouts)
- Custom buttons and links
- Field update actions
- Web forms

### Phase 2: Field Mapping Analysis
Create a comprehensive "Rosetta Stone" that maps:
- Every field in your CRM
- All locations where each field is read or modified
- The transformation logic applied
- Dependencies between fields
- Workflow chains that affect fields

## Project Structure

```
zoho-field-analyzer/
├── src/                          # Source code
│   ├── extractors/               # Data extraction from Zoho
│   │   ├── __init__.py
│   │   ├── base.py              # Base extractor class
│   │   ├── functions.py         # Extract Deluge functions
│   │   ├── workflows.py         # Extract workflows
│   │   ├── blueprints.py        # Extract blueprints
│   │   ├── modules.py           # Extract module metadata
│   │   └── custom_actions.py    # Extract buttons, links, etc.
│   ├── analyzers/               # Data analysis
│   │   ├── __init__.py
│   │   ├── field_tracker.py    # Track field changes
│   │   ├── dependency_graph.py  # Build dependency graphs
│   │   └── rosetta_builder.py   # Build the Rosetta Stone
│   ├── api/                     # API clients
│   │   ├── __init__.py
│   │   └── zoho_client.py      # Zoho API wrapper
│   └── utils/                   # Utilities
│       ├── __init__.py
│       ├── file_helpers.py     # File operations
│       └── logging_config.py   # Logging setup
├── data/                        # Client-specific data
│   └── {client_name}/
│       ├── raw/                # Raw extracted data
│       │   ├── functions/
│       │   ├── workflows/
│       │   ├── blueprints/
│       │   └── modules/
│       └── analyzed/           # Processed data
│           └── field_mapping.json
├── config/                      # Configuration files
│   ├── client_template.yaml    # Template for new clients
│   └── {client_name}.yaml      # Client-specific config
├── output/                      # Final reports
│   ├── {client}_rosetta_stone.json
│   └── {client}_field_report.html
├── tests/                       # Unit tests
├── requirements.txt             # Python dependencies
└── setup.py                     # Package setup
```

## Quick Start

### 1. Installation

```bash
pip install -r requirements.txt
```

### 2. Configuration

Create a client configuration file:

```bash
cp config/client_template.yaml config/your_client.yaml
```

Edit `config/your_client.yaml` with your Zoho credentials:
- Cookie header
- CSRF token
- Organization ID

### 3. Extract Data

```bash
# Extract all data for a client
python -m src.extractors.main --client your_client --extract-all

# Or extract specific types
python -m src.extractors.main --client your_client --extract functions
python -m src.extractors.main --client your_client --extract workflows
```

### 4. Analyze Data

```bash
# Build the field mapping
python -m src.analyzers.rosetta_builder --client your_client

# Generate report
python -m src.analyzers.rosetta_builder --client your_client --report html
```

## Getting Zoho API Credentials

Zoho CRM uses browser-based authentication. To extract credentials:

1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Navigate to Zoho CRM and perform any action
4. Find a successful request (200 status)
5. Copy the following headers:
   - `Cookie` - The full cookie header value
   - `x-zcsrf-token` - Include the `crmcsrfparam=` prefix
   - `x-crm-org` - Your organization ID

These credentials are temporary and will need to be refreshed periodically.

## Multi-Client Support

Each client gets isolated data storage:

```
data/
├── acme_corp/
│   ├── raw/...
│   └── analyzed/...
└── tech_startup/
    ├── raw/...
    └── analyzed/...
```

Configuration files in `config/` manage credentials per client.

## Output Formats

The Rosetta Stone can be generated in multiple formats:
- **JSON**: Machine-readable complete mapping
- **HTML**: Interactive visual report
- **CSV**: Spreadsheet-compatible field list
- **GraphML**: Network graph for visualization tools

## Development

### Adding New Extractors

1. Create a new file in `src/extractors/`
2. Inherit from `BaseExtractor`
3. Implement `extract()` method
4. Register in `main.py`

### Adding New Analyzers

1. Create a new file in `src/analyzers/`
2. Implement analysis logic
3. Output to `data/{client}/analyzed/`

## License

[Your License Here]
