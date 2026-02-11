# Workflows Extraction Guide

Extract workflow rules and field update actions from Zoho CRM automation.

## Overview

Workflows have a 2-level structure:
1. **Workflow rules** - Automated processes triggered by record events
2. **Field update actions** - Specific fields modified by workflows

This guide covers extracting **both levels**.

## Two Workflows

### Workflow 1: Basic Workflow Extraction (Faster)

Gets workflow structure without detailed field update information:

```powershell
python -m src.extractors.main --client blades --extract workflows
```

**What you get:**
- Workflow metadata (name, module, trigger conditions)
- List of actions with IDs and names
- **Does NOT include:** Field API names being updated

**Use when:**
- Initial quick scan
- You only need workflow structure
- Speed is important

### Workflow 2: Full Extraction with Field Updates (Slower, Complete)

Gets everything including detailed field update information:

```powershell
python -m src.extractors.main --client blades --extract workflows --with-field-updates
```

**What you get:**
- Everything from Workflow 1 PLUS:
- Field API names that are updated
- Values those fields are set to
- Raw field update detail files
- Complete field update mapping

**Use when:**
- Building the Rosetta Stone
- Need to know which fields workflows modify
- Analyzing field transformations

## Performance Considerations

### Rate Limiting
The `--with-field-updates` flag makes **additional API calls**:
- 1 call per field update action (not per workflow)
- Example: 50 workflows × 4 field updates avg = 200 calls
- Built-in 500ms delay between field update requests

### Time Estimates
**Without field updates:**
- 50 workflows ≈ 1-2 minutes

**With field updates:**
- 50 workflows × 4 field updates = 200 field update calls
- 200 × 0.5 seconds = ~100 seconds of delays alone
- Total: 3-5 minutes for full extraction

**Recommendation:** Run without field updates first, then add `--with-field-updates` when needed.

## Output Structure

### Basic Extraction (No Field Updates)
```
data/blades/raw/workflows/
├── Leads_-_Cr_-_Reset_System_Variables_2_3193870000100198540.json
├── Government_Contacts_Layout_Rule_3193870000012794033.json
├── all_workflows.json
└── workflows_index.json
```

### With Field Updates
```
data/blades/raw/workflows/
├── Leads_-_Cr_-_Reset_System_Variables_2_3193870000100198540.json  ← Enriched
├── Government_Contacts_Layout_Rule_3193870000012794033.json
├── field_updates/  ← Raw field update detail files
│   ├── 3193870000100198540_Leads_-_Trigger_Update_to_Blank_3193870000100198484.json
│   ├── 3193870000100198540_Leads_-_Days_In_This_Stage_to_0_3193870000698571642.json
│   └── ...
├── all_workflows.json
└── workflows_index.json
```

## What's in the Files?

### Workflow File (Without Field Updates)
```json
{
  "id": "3193870000100198540",
  "name": "Leads - Cr - Reset System Variables 2",
  "module": {"api_name": "Leads"},
  "status": {"active": true},
  "conditions": [
    {
      "instant_actions": {
        "actions": [
          {
            "id": "3193870000698571642",
            "name": "Leads - Days In This Stage to 0",
            "type": "field_updates"
          }
        ]
      }
    }
  ]
}
```

### Workflow File (With Field Updates - Enriched)
```json
{
  "id": "3193870000100198540",
  "name": "Leads - Cr - Reset System Variables 2",
  "conditions": [
    {
      "instant_actions": {
        "actions": [
          {
            "id": "3193870000698571642",
            "name": "Leads - Days In This Stage to 0",
            "type": "field_updates",
            "field_api_name": "Days_In_This_Stage",
            "field_id": "3193870000698351573",
            "field_value": 0,
            "update_type": "static",
            "module": "Leads",
            "field_update_details_file": "..."
          }
        ]
      }
    }
  ],
  "field_updates_summary": {
    "total_field_update_actions": 4,
    "enriched_actions": 4
  }
}
```

### Raw Field Update File
```json
{
  "field_updates": [
    {
      "id": "3193870000698571642",
      "name": "Leads - Days In This Stage to 0",
      "field": {
        "api_name": "Days_In_This_Stage",
        "id": "3193870000698351573"
      },
      "value": 0,
      "type": "static",
      "module": {
        "api_name": "Leads"
      }
    }
  ]
}
```

## API Endpoints Used

### 1. List All Workflows
```
GET https://crm.zoho.com/crm/v8/settings/automation/workflow_rules
?page=1
&per_page=200
```

### 2. Get Field Update Details
```
GET https://crm.zoho.com/crm/v8/settings/automation/field_updates/{action_id}
?include_inner_details=module.plural_label,related_module.module_name,...
```

## Usage Examples

### Example 1: Quick Structure Check
```powershell
# Just get workflow structure (fast)
python -m src.extractors.main --client blades --extract workflows
```

### Example 2: Full Field Mapping
```powershell
# Get everything including field updates (slow but complete)
python -m src.extractors.main --client blades --extract workflows --with-field-updates
```

### Example 3: Combine with Other Extractors
```powershell
# Extract workflows, blueprints, and modules together
python -m src.extractors.main --client blades --extract workflows blueprints modules --with-field-updates --with-transitions
```

### Example 4: Extract Everything
```powershell
# Get complete data for Rosetta Stone
python -m src.extractors.main --client blades --extract-all --with-field-updates --with-transitions
```

## Console Output

### Without Field Updates
```
[1/50] Extracting: Leads - Cr - Reset System Variables 2 (Leads) - Active
  [OK] Saved (4 actions)

[2/50] Extracting: Government Contacts Layout Rule (Contacts) - Inactive
  [OK] Saved (1 actions)
```

### With Field Updates
```
[1/50] Extracting: Leads - Cr - Reset System Variables 2 (Leads) - Active
  Extracting field update details...
  Processing 4 field update actions...
    [1/4] Leads - Trigger Update to Blank (ID: 3193870000100198484)
      [OK] Field: Trigger_Update
    [2/4] Leads - Deduplication Checked to Blank (ID: 3193870000100198489)
      [OK] Field: Deduplication_Checked
    [3/4] Leads - Date Put Into This Stage to NOW (ID: 3193870000698564642)
      [OK] Field: Date_Put_Into_This_Stage
    [4/4] Leads - Days In This Stage to 0 (ID: 3193870000698571642)
      [OK] Field: Days_In_This_Stage
  [OK] Processed 4 actions, 4 field updates
  [OK] Saved (4 actions)
```

## What Gets Captured?

From each workflow with field updates:
- ✅ **field_api_name** - API name of the field (e.g., "Days_In_This_Stage")
- ✅ **field_value** - What it's set to (literal value or formula)
- ✅ **field_id** - Zoho's internal field ID
- ✅ **update_type** - "static", "formula", "user", etc.
- ✅ **module** - Which module the field belongs to
- ✅ Raw field update JSON file (complete data)

## Integration with Blueprints and Functions

**Problem:** Three different systems modify fields:
- Functions use field API names (e.g., `"Days_In_This_Stage"`)
- Workflows use field API names (e.g., `"Days_In_This_Stage"`)
- Blueprints use field labels (e.g., `"Days In This Stage"`)

**Solution:** Modules data provides the mapping:
```json
{
  "field_label": "Days In This Stage",
  "api_name": "Days_In_This_Stage"
}
```

**Result:** Complete Rosetta Stone showing all field modifications:
```json
{
  "Days_In_This_Stage": {
    "api_name": "Days_In_This_Stage",
    "field_label": "Days In This Stage",
    "modified_by": {
      "functions": ["Reset_Lead_Variables"],
      "workflows": ["Leads - Cr - Reset System Variables 2"],
      "blueprints": ["Lead Qualification Blueprint"]
    }
  }
}
```

## Troubleshooting

**"No workflows found"**
- Check credentials in config file
- Credentials may have expired
- Try refreshing from Chrome DevTools

**"Error getting field update {id}: 400"**
- Field update action ID might be invalid
- Credentials might have expired
- Action might have been deleted

**Takes too long**
- This is expected with `--with-field-updates`
- 50 workflows × 4 actions = 200+ API calls
- Consider running overnight or during off-hours
- Or run basic extraction first, add field updates later

## Next Steps

After extraction with field updates:

1. **Review the field update files** in `workflows/field_updates/`
2. **Check enriched workflow data** with field_api_name
3. **Run analysis** to build Rosetta Stone
4. **Combine with blueprints and functions** for complete mapping

```powershell
# Build complete field mapping
python -m src.analyzers.rosetta_builder --client blades
```

The Rosetta Stone will include:
- Functions that modify fields
- **Workflows that modify fields** ← NEW!
- Blueprints that modify fields

## Performance Tips

1. **Run basic extraction first** to see what you have
2. **Add field updates when needed** for deep analysis
3. **Extract overnight** for large CRMs with many workflows
4. **Monitor console output** to see progress
5. **Check logs** in `logs/` directory for details

## Advanced: Action Types

Workflows can have different action types:
- **field_updates** - Modify field values (we extract these)
- **email_notifications** - Send emails
- **tasks** - Create tasks
- **webhooks** - Call external APIs
- **functions** - Execute Deluge functions

Only `field_updates` actions are extracted with `--with-field-updates` since they're relevant for the Rosetta Stone.

## Summary

| Feature | Without --with-field-updates | With --with-field-updates |
|---------|------------------------------|---------------------------|
| **Speed** | Fast (1-2 min) | Slow (3-5 min) |
| **Workflow Structure** | ✅ Yes | ✅ Yes |
| **Action Names** | ✅ Yes | ✅ Yes |
| **Field API Names** | ❌ No | ✅ Yes |
| **Field Values** | ❌ No | ✅ Yes |
| **Update Types** | ❌ No | ✅ Yes |
| **Raw Details** | ❌ No | ✅ Yes |
| **Rosetta Stone Ready** | ❌ No | ✅ Yes |

**For Rosetta Stone: Always use `--with-field-updates`**

Ready to extract! 🚀
