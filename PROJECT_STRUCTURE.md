# Project Structure

This document explains the organization of the Zoho Field Analyzer codebase.

## Directory Layout

```
zoho-field-analyzer/
│
├── src/                          # Source code
│   ├── __init__.py
│   │
│   ├── api/                      # API client layer
│   │   ├── __init__.py
│   │   └── zoho_client.py       # Zoho CRM API wrapper with retry logic
│   │
│   ├── extractors/              # Data extraction modules
│   │   ├── __init__.py
│   │   ├── base.py              # BaseExtractor class (all extractors inherit)
│   │   ├── functions.py         # Extract Deluge functions
│   │   ├── workflows.py         # Extract workflow rules
│   │   ├── blueprints.py        # Extract blueprints
│   │   ├── modules.py           # Extract module metadata & fields
│   │   └── main.py              # CLI entry point for extraction
│   │
│   ├── analyzers/               # Data analysis modules
│   │   ├── __init__.py
│   │   ├── field_tracker.py    # Track field usage across sources
│   │   └── rosetta_builder.py  # Build comprehensive field mapping
│   │
│   └── utils/                   # Shared utilities
│       ├── __init__.py
│       ├── file_helpers.py     # File operations, path management
│       └── logging_config.py   # Logging configuration
│
├── data/                        # Client data (gitignored)
│   └── {client_name}/
│       ├── raw/                # Raw extracted data
│       │   ├── functions/
│       │   ├── workflows/
│       │   ├── blueprints/
│       │   └── modules/
│       └── analyzed/           # Analyzed/processed data
│           ├── field_map.json
│           └── rosetta_stone.json
│
├── config/                      # Configuration files
│   ├── client_template.yaml    # Template for new clients
│   └── {client_name}.yaml     # Client-specific configs (gitignored)
│
├── output/                      # Final reports (gitignored)
│   ├── {client}_rosetta_stone.json
│   └── {client}_field_report.html
│
├── logs/                        # Log files (gitignored)
│   └── extraction_YYYYMMDD_HHMMSS.log
│
├── tests/                       # Unit tests
│
├── legacy_pull_scripts.py      # Original script (reference)
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
├── .gitignore                   # Git ignore rules
├── README.md                    # Main documentation
├── QUICKSTART.md               # Quick start guide
└── PROJECT_STRUCTURE.md        # This file
```

## Core Components

### 1. API Layer (`src/api/`)

**zoho_client.py**
- Handles all HTTP communication with Zoho CRM API
- Manages authentication headers (Cookie, CSRF token, Org ID)
- Implements retry logic and rate limiting
- Provides `get()`, `post()`, and `paginated_get()` methods

### 2. Extractors (`src/extractors/`)

**base.py** - BaseExtractor class
- Abstract base class for all extractors
- Provides common functionality:
  - Statistics tracking
  - File saving (JSON, text)
  - Filename sanitization
  - Metadata header creation
  - Error logging

**functions.py** - FunctionsExtractor
- Extracts all Deluge functions
- Saves individual function scripts with metadata headers
- Creates `functions_index.json` master list
- Based on the original `pull_scripts.py`

**workflows.py** - WorkflowsExtractor
- Extracts workflow rules
- Captures field updates, conditions, actions
- Saves as JSON files

**modules.py** - ModulesExtractor
- Extracts module definitions
- Gets field metadata for each module
- Captures field types, labels, validations

**blueprints.py** - BlueprintsExtractor
- Extracts blueprint configurations
- Captures state transitions and logic
- *(Currently a stub - needs implementation)*

**main.py** - CLI Entry Point
- Command-line interface for running extractors
- Loads client configuration
- Orchestrates extraction process
- Handles logging and error reporting

### 3. Analyzers (`src/analyzers/`)

**field_tracker.py** - FieldTracker
- Analyzes extracted data to find field references
- Uses regex patterns to find field usage in functions
- Parses workflows for field updates
- Creates `field_map.json`

**rosetta_builder.py** - RosettaStoneBuilder
- Combines all data sources
- Creates comprehensive field → transformation mapping
- Generates `rosetta_stone.json`
- Can export to multiple formats (JSON, HTML)

### 4. Utilities (`src/utils/`)

**file_helpers.py**
- YAML/JSON loading and saving
- Client directory management
- Path utilities
- Client listing

**logging_config.py**
- Centralized logging setup
- Console and file logging
- Configurable log levels

## Data Flow

```
1. Configuration
   └─> config/{client}.yaml
       └─> Contains Zoho credentials

2. Extraction (Phase 1)
   └─> src/extractors/main.py
       ├─> ZohoAPIClient (authentication)
       ├─> FunctionsExtractor
       │   └─> data/{client}/raw/functions/
       ├─> WorkflowsExtractor
       │   └─> data/{client}/raw/workflows/
       └─> ModulesExtractor
           └─> data/{client}/raw/modules/

3. Analysis (Phase 2)
   └─> src/analyzers/field_tracker.py
       ├─> Reads: data/{client}/raw/
       └─> Writes: data/{client}/analyzed/field_map.json
   
   └─> src/analyzers/rosetta_builder.py
       ├─> Reads: data/{client}/raw/ + field_map.json
       └─> Writes: data/{client}/analyzed/rosetta_stone.json

4. Reporting
   └─> output/{client}_rosetta_stone.json
   └─> output/{client}_field_report.html
```

## Key Design Patterns

### 1. Extractor Pattern
All extractors inherit from `BaseExtractor`:
```python
class MyExtractor(BaseExtractor):
    def get_extractor_name(self) -> str:
        return "my_data"
    
    def extract(self) -> Dict[str, Any]:
        # Implementation
        return results
```

### 2. Client Isolation
Each client's data is completely isolated:
- Separate config file
- Separate data directory
- No cross-contamination

### 3. Raw → Analyzed Pipeline
- **Raw data**: Unprocessed extraction results
- **Analyzed data**: Processed, cross-referenced, enriched
- **Output**: Final reports and visualizations

### 4. Fail-Safe Extraction
- Individual items can fail without stopping the process
- Failed items are logged to `FAILED_EXTRACTIONS.txt`
- Statistics track success/failure counts

## Configuration Management

### Client Configuration Structure
```yaml
client_name: "acme_corp"
zoho_credentials:
  cookie: "..."
  csrf_token: "crmcsrfparam=..."
  org_id: "123456"
extraction:
  enabled_extractors: [functions, workflows, modules]
  request_delay: 0.5
output:
  data_dir: "data"
  log_level: "INFO"
```

## Adding New Extractors

1. Create new file in `src/extractors/`
2. Inherit from `BaseExtractor`
3. Implement required methods
4. Register in `src/extractors/main.py`:
   ```python
   EXTRACTORS = {
       'my_new_type': MyNewExtractor,
   }
   ```

## Adding New Analyzers

1. Create new file in `src/analyzers/`
2. Read from `data/{client}/raw/`
3. Write to `data/{client}/analyzed/`
4. Can be standalone or integrate with Rosetta Stone

## Usage Patterns

### Extract data for a client
```bash
python -m src.extractors.main --client acme_corp --extract-all
```

### Analyze specific field usage
```bash
python -m src.analyzers.field_tracker --client acme_corp
```

### Build comprehensive mapping
```bash
python -m src.analyzers.rosetta_builder --client acme_corp
```

## File Naming Conventions

- **Extractors**: `{type}.py` (e.g., `functions.py`)
- **Config files**: `{client_name}.yaml`
- **Raw data**: `{Name}_{ID}.{ext}`
- **Index files**: `{type}_index.json`
- **Analyzed data**: Descriptive names (`field_map.json`)

## Next Steps for Development

1. **Implement BlueprintsExtractor**
2. **Add CustomActionsExtractor** (buttons, links)
3. **Enhance field_tracker** with better parsing
4. **Create HTML report generator**
5. **Add dependency graph visualization**
6. **Implement change detection** (compare extractions over time)
7. **Add unit tests**

## Migration from Legacy Script

The original `pull_scripts.py` has been refactored into:
- API client → `src/api/zoho_client.py`
- Functions extraction → `src/extractors/functions.py`
- Configuration → YAML files in `config/`
- Utilities → `src/utils/`

Benefits of new structure:
- Reusable API client
- Multiple extractors sharing code
- Better error handling
- Multi-client support
- Extensible analysis pipeline
