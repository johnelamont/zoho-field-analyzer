# Blueprint Transitions Extraction Guide

Complete guide for extracting blueprint transition details and field updates.

## Overview

Blueprints have a 3-level structure:
1. **Blueprint list** - All blueprints in the system
2. **Blueprint details** - Structure, states, transitions
3. **Transition details** - Field updates, conditions, values

This guide covers extracting **all three levels**.

## Two Workflows

### Workflow 1: Basic Blueprint Extraction (Faster)

Gets blueprint structure without detailed transition information:

```bash
python -m src.extractors.main --client blades --extract blueprints
```

**What you get:**
- Blueprint metadata
- Transition list (names and IDs)
- States and structure
- **Does NOT include:** Field update details per transition

**Use when:**
- Initial quick scan
- You only need blueprint structure
- Speed is important

### Workflow 2: Full Extraction with Transitions (Slower, Complete)

Gets everything including detailed field updates:

```bash
python -m src.extractors.main --client blades --extract blueprints --with-transitions
```

**What you get:**
- Everything from Workflow 1 PLUS:
- Field labels that are updated in each transition
- Values those fields are set to
- Raw transition detail files
- Complete field update mapping

**Use when:**
- Building the Rosetta Stone
- Need to know which fields blueprints modify
- Analyzing field transformations

## Performance Considerations

### Rate Limiting
The `--with-transitions` flag makes **many additional API calls**:
- 1 call per transition (not per blueprint)
- Example: 9 blueprints × 10 transitions avg = 90 calls
- Built-in 750ms delay between transition requests

### Time Estimates
**Without transitions:**
- 9 blueprints ≈ 1-2 minutes

**With transitions:**
- 9 blueprints × 10 transitions = 90 transition calls
- 90 × 0.75 seconds = ~68 seconds of delays alone
- Total: 5-10 minutes for full extraction

**Recommendation:** Run without transitions first, then add `--with-transitions` when needed.

## Output Structure

### Basic Extraction (No Transitions)
```
data/blades/raw/blueprints/
├── Field_Sales_Process_3193870000102787278.json
├── Account_Management_3193870000116366582.json
├── Leads_Blueprint_3193870000091284157.json
└── blueprints_index.json
```

### With Transitions
```
data/blades/raw/blueprints/
├── Field_Sales_Process_3193870000102787278.json  ← Enriched with field updates
├── Account_Management_3193870000116366582.json
├── Leads_Blueprint_3193870000091284157.json
├── transitions/  ← Raw transition detail files
│   ├── 3193870000102787278_Qualify_3193870000091284045.json
│   ├── 3193870000102787278_Propose_3193870000091284046.json
│   ├── 3193870000102787278_Negotiate_3193870000091284047.json
│   └── ...
└── blueprints_index.json
```

## What's in the Files?

### Blueprint File (Without Transitions)
```json
{
  "metadata": {
    "Id": "3193870000102787278",
    "Name": "Field Sales Process",
    "Tab": {"Name": "Potentials"}
  },
  "details": {
    "TransitionsMeta": [
      {
        "TransitionId": "3193870000091284045",
        "Name": "Qualify",
        "FromState": "Draft",
        "ToState": "Qualified"
      }
    ]
  }
}
```

### Blueprint File (With Transitions - Enriched)
```json
{
  "metadata": {...},
  "details": {
    "TransitionsMeta": [
      {
        "TransitionId": "3193870000091284045",
        "Name": "Qualify",
        "FromState": "Draft",
        "ToState": "Qualified",
        "transition_details_file": "3193870000102787278_Qualify_3193870000091284045.json",
        "field_updates": [
          {
            "field_label": "Stage",
            "field_value": "Qualified",
            "field_id": "3193870000000002565"
          },
          {
            "field_label": "Qualified Date",
            "field_value": "${System.CurrentDateTime}",
            "field_id": "3193870000116366554"
          }
        ],
        "field_update_count": 2
      }
    ],
    "transition_summary": {
      "total_transitions": 10,
      "total_field_updates": 25
    }
  }
}
```

### Raw Transition File
```json
{
  "FieldVsLabel": {
    "3193870000000002565": "Stage",
    "3193870000116366554": "Qualified Date"
  },
  "Actions": {
    "Fieldupdate": [
      {
        "fieldLabel": "Stage",
        "fieldValue": "Qualified",
        "fieldId": "3193870000000002565"
      },
      {
        "fieldLabel": "Qualified Date",
        "fieldValue": "${System.CurrentDateTime}",
        "fieldId": "3193870000116366554"
      }
    ]
  }
}
```

## Field Label → API Name Conversion

**Important:** The transition details use **field labels** (display names), not API names.

**Examples:**
- Label: "Stage" → API Name: "STAGE"
- Label: "Qualified Date" → API Name: "QUALIFIEDDATE" or "DEALSCF123"

**Conversion Strategy:**
1. Extract transitions with labels (what we do now)
2. During analysis phase, map labels to API names using module field data
3. Build Rosetta Stone with API names

**Why not convert during extraction?**
- Modules might not be extracted yet
- Labels are the source of truth from Zoho
- Easier to debug with human-readable labels
- Conversion logic belongs in analysis phase

## Usage Examples

### Example 1: Quick Structure Check
```bash
# Just get blueprint structure (fast)
python -m src.extractors.main --client blades --extract blueprints
```

### Example 2: Full Field Mapping
```bash
# Get everything including field updates (slow but complete)
python -m src.extractors.main --client blades --extract blueprints --with-transitions
```

### Example 3: Update Single Blueprint with Transitions
```bash
# Someone modified the Field Sales Process blueprint
python -m src.extractors.main --client blades --extract blueprints \
  --blueprint-id 3193870000102787278 \
  --blueprint-module Potentials \
  --with-transitions
```

### Example 4: Re-extract Transitions Later
```bash
# Already have blueprints, just want to add transition details
# Run the same command with --with-transitions, it will overwrite

python -m src.extractors.main --client blades --extract blueprints --with-transitions
```

## Console Output

### Without Transitions
```
[1/9] Extracting: Field Sales Process (Potentials) - Active
  ✓ Saved

[2/9] Extracting: Account Management (Accounts) - Active
  ✓ Saved
```

### With Transitions
```
[1/9] Extracting: Field Sales Process (Potentials) - Active
  Extracting transition details...
  Processing 10 transitions...
    [1/10] Qualify (ID: 3193870000091284045)
      ✓ 2 field updates found
    [2/10] Propose (ID: 3193870000091284046)
      ✓ 3 field updates found
    [3/10] Negotiate (ID: 3193870000091284047)
      ✓ 1 field updates found
    ...
  ✓ Processed 10 transitions, 25 total field updates
  ✓ Saved

[2/9] Extracting: Account Management (Accounts) - Active
  Extracting transition details...
  Processing 8 transitions...
  ...
```

## What Gets Captured?

From each transition:
- ✅ **field_label** - Display name of the field
- ✅ **field_value** - What it's set to (literal value or formula)
- ✅ **field_id** - Zoho's internal field ID
- ✅ Raw transition JSON file (complete data)

## Troubleshooting

**"No layout ID found, skipping transitions"**
- Blueprint metadata is missing layout information
- This is rare but possible
- Blueprint structure still saved, just no transition details

**"Error getting transition {id}: 400"**
- Transition ID might be invalid
- Credentials might have expired
- Blueprint might be in draft state

**Rate limiting / 429 errors**
- Built-in 750ms delay should prevent this
- If it happens, increase delay in code (search for `time.sleep(0.75)`)
- Or run in smaller batches

**Takes too long**
- This is expected with `--with-transitions`
- 9 blueprints × 10 transitions = 90+ API calls
- Consider running overnight or during off-hours
- Or extract specific blueprints one at a time

## Next Steps

After extraction with transitions:

1. **Review the transition files** in `blueprints/transitions/`
2. **Check field updates** in enriched blueprint JSON
3. **Run analysis** to build Rosetta Stone
4. **Map field labels to API names** during analysis

```bash
# Build field mapping with blueprint data
python -m src.analyzers.rosetta_builder --client blades
```

The Rosetta Stone will include:
- Functions that modify fields
- Workflows that modify fields
- **Blueprints that modify fields** ← NEW!

## Performance Tips

1. **Run basic extraction first** to see what you have
2. **Add transitions when needed** for deep analysis
3. **Extract overnight** for large CRMs with many blueprints
4. **Use single-blueprint mode** for quick updates
5. **Monitor console output** to see progress

## Advanced: Configuring the Delay

If you hit rate limits, increase the delay in `blueprints.py`:

```python
# In process_blueprint_transitions method
time.sleep(0.75)  # Change this to 1.0 or 1.5 if needed
```

Higher values = slower but safer from rate limits.
