# Blueprints Extraction Guide

The BlueprintsExtractor now supports two workflows based on your requirements.

## Workflow 1: Extract ALL Blueprints (Full Extraction)

Use this for initial extraction or periodic full updates:

```bash
python -m src.extractors.main --client blades --extract blueprints
```

**What it does:**
1. Gets list of all blueprints from Zoho
2. Loops through each blueprint
3. Downloads full details (transitions, field updates, conditions)
4. Saves to `data/blades/raw/blueprints/`

**Output:**
```
data/blades/raw/
└── blueprints/
    ├── Account_Management_3193870000116366582.json
    ├── Contact_Management_3193870000114396072.json
    ├── Field_Sales_Process_3193870000102787278.json
    ├── Inside_Sales_Process_3193870000032608388.json
    ├── Leads_Blueprint_3193870000091284157.json
    └── blueprints_index.json
```

**Example output:**
```
[1/9] Extracting: Account Management (Accounts) - Active
  ✓ Saved
[2/9] Extracting: Contact Management (Contacts) - Active
  ✓ Saved
...
```

## Workflow 2: Extract Single Blueprint (Quick Update)

Use this when a specific blueprint was modified:

```bash
python -m src.extractors.main --client blades --extract blueprints \
  --blueprint-id 3193870000102787278 \
  --blueprint-module Potentials
```

**What it does:**
1. Skips the "list all" step
2. Directly downloads that specific blueprint
3. Overwrites the old file (if exists)
4. Fast - takes only seconds

**Required arguments:**
- `--blueprint-id`: The blueprint ID (from Zoho URL or previous extraction)
- `--blueprint-module`: Module name (Potentials, Accounts, Leads, etc.)

## Finding Blueprint IDs

### Method 1: From Zoho UI
Open a blueprint in Zoho and check the URL:
```
https://crm.zoho.com/.../ProcessFlow.do?...&processId=3193870000102787278...
                                                      ^^^^^^^^^^^^^^^^^^
                                                      This is the ID
```

### Method 2: From Previous Extraction
Check `blueprints_index.json`:
```json
[
  {
    "id": "3193870000102787278",
    "name": "Field Sales Process",
    "module": "Potentials",
    "status": "Active",
    "filename": "Field_Sales_Process_3193870000102787278.json"
  }
]
```

## Module Names

Common module names (from your system):
- `Potentials` (Deals/Opportunities)
- `Accounts`
- `Contacts`
- `Leads`
- `Events` (Meetings)
- `CustomModule8`, `CustomModule9`, etc.

**Tip:** Run the full extraction once to get the `blueprints_index.json` which lists all module names.

## Typical Usage Pattern

```bash
# Week 1: Full extraction (initial setup)
python -m src.extractors.main --client blades --extract blueprints

# Week 2: Someone modifies "Field Sales Process"
python -m src.extractors.main --client blades --extract blueprints \
  --blueprint-id 3193870000102787278 \
  --blueprint-module Potentials

# Week 3: Business as usual, no changes
# (no extraction needed)

# Week 4: Someone modifies "Leads Blueprint"
python -m src.extractors.main --client blades --extract blueprints \
  --blueprint-id 3193870000091284157 \
  --blueprint-module Leads

# Month 2: Full extraction (catch anything we missed)
python -m src.extractors.main --client blades --extract blueprints
```

## What's in the Blueprint Files?

Each blueprint JSON contains:
- **metadata**: Name, module, status, created/modified dates
- **details**: Full blueprint configuration
  - **transitions**: State changes (e.g., Draft → Approved)
  - **field updates**: What fields change in each transition
  - **conditions**: Rules for when transitions can happen
  - **scripts**: Before/after transition scripts

Example structure:
```json
{
  "metadata": {
    "Id": "3193870000102787278",
    "Name": "Field Sales Process",
    "Tab": {"Name": "Potentials"},
    "ProcessStatus": "Active"
  },
  "details": {
    "transitions": [...],
    "states": [...],
    "field_updates": [...]
  }
}
```

## Error Handling

**"Module name required when extracting specific blueprint"**
- You forgot `--blueprint-module`
- Add it: `--blueprint-module Potentials`

**"--blueprint-id can only be used with --extract blueprints"**
- You're trying to use `--blueprint-id` with other extractors
- Use it only with blueprints

**"No blueprints found"**
- Check your credentials
- Verify you have blueprints configured in Zoho
- Check the org_id in your config file

## Combining with Other Extractors

```bash
# Extract blueprints AND functions
python -m src.extractors.main --client blades --extract blueprints functions

# Extract everything including blueprints
python -m src.extractors.main --client blades --extract-all
```

## Next Steps

After extraction:
1. **Review the files** in `data/blades/raw/blueprints/`
2. **Check transitions** to see field updates
3. **Run the analyzer** to build the Rosetta Stone
4. **Search for fields** to see which blueprints modify them

```bash
# Build field mapping
python -m src.analyzers.rosetta_builder --client blades
```

The Rosetta Stone will include blueprint field updates along with functions and workflows!
