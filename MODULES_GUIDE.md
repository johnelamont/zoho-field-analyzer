# Modules Extraction Guide

Extract module metadata and field definitions from Zoho CRM.

## Why Extract Modules?

Modules extraction is **critical** for the field label→API name conversion needed for blueprint analysis:

```
Blueprint says: "Stage" (label)
We need: "STAGE" (API name)

Modules data provides the mapping:
  field_label: "Stage"
  api_name: "Stage"
  column_name: "STAGE"
```

## What Gets Extracted

### 1. Module Metadata
For each module (Accounts, Leads, Potentials, etc.):
- Module name and API name
- Status (visible, hidden, etc.)
- Permissions and profiles
- Configuration details

### 2. Field Definitions
For each field in each module:
- **field_label**: "Account Owner" (display name)
- **api_name**: "Owner" (API reference)
- **column_name**: "SMOWNERID" (database column)
- **data_type**: "ownerlookup", "text", "picklist", etc.
- **id**: Field ID
- Permissions, validations, picklist values, etc.

## Usage

### Basic Extraction

```powershell
python -m src.extractors.main --client blades --extract modules
```

### Extract Everything

```powershell
python -m src.extractors.main --client blades --extract-all
```

## Output Structure

```
data/blades/raw/modules/
├── all_modules.json              # Master list of all modules
├── modules_index.json            # Summary index
├── Accounts.json                 # Full module + fields data
├── Leads.json
├── Potentials.json
├── Contacts.json
├── CustomModule8.json
└── ...
```

## File Contents

### all_modules.json
Complete list of modules:
```json
{
  "modules": [
    {
      "api_name": "Accounts",
      "module_name": "Accounts",
      "id": "3193870000000002177",
      "status": "visible",
      "plural_label": "Accounts",
      "singular_label": "Account"
    }
  ]
}
```

### Individual Module Files (e.g., Accounts.json)
```json
{
  "metadata": {
    "api_name": "Accounts",
    "module_name": "Accounts",
    "status": "visible"
  },
  "fields": {
    "fields": [
      {
        "field_label": "Account Owner",
        "api_name": "Owner",
        "column_name": "SMOWNERID",
        "data_type": "ownerlookup",
        "id": "3193870000000002421"
      },
      {
        "field_label": "Stage",
        "api_name": "Stage",
        "column_name": "STAGE",
        "data_type": "picklist",
        "pick_list_values": [...]
      }
    ]
  }
}
```

## Key Field Mappings

The most important data for blueprint analysis:

| field_label (what blueprints use) | api_name (what we need) | column_name (database) |
|-----------------------------------|-------------------------|------------------------|
| Account Owner | Owner | SMOWNERID |
| Stage | Stage | STAGE |
| Qualified Date | Qualified_Date | DEALSCF123 |
| Blueprint Status | Blueprint_Status | ACCOUNTCF177 |

## How This Enables Blueprint Analysis

**Problem:** Blueprints use field labels
```json
{
  "field_updates": [
    {"field_label": "Stage", "field_value": "Qualified"}
  ]
}
```

**Solution:** Modules data provides the mapping
```json
{
  "field_label": "Stage",
  "api_name": "Stage"
}
```

**Result:** We can build the Rosetta Stone
```json
{
  "Stage": {
    "api_name": "Stage",
    "modified_by": {
      "blueprints": ["Field Sales Process"],
      "functions": ["UpdateStage"],
      "workflows": ["Lead Conversion"]
    }
  }
}
```

## Performance

- **Speed**: 1-2 seconds per module
- **API Calls**: 1 call for module list + 1 call per module for fields
- **Example**: 50 modules = 51 API calls ≈ 1-2 minutes total

## What You'll See

```
[1/50] Extracting: Accounts (Accounts) - visible
  [OK] Saved (245 fields)

[2/50] Extracting: Leads (Leads) - visible
  [OK] Saved (178 fields)

[3/50] Extracting: Potentials (Potentials) - visible
  [OK] Saved (198 fields)

...
```

## Tips

### Extract Modules BEFORE Blueprints
For best results, run in this order:
```powershell
# 1. Modules first (provides field mappings)
python -m src.extractors.main --client blades --extract modules

# 2. Then blueprints with transitions
python -m src.extractors.main --client blades --extract blueprints --with-transitions

# 3. Finally, build Rosetta Stone
python -m src.analyzers.rosetta_builder --client blades
```

### Field Count as Health Check
Each module should have many fields:
- **Standard modules**: 50-200+ fields
- **Custom modules**: 10-50+ fields
- **If < 5 fields**: Something went wrong

### Hidden Modules
The extraction includes ALL modules:
- `visible`: Active modules
- `user_hidden`: Hidden from users
- `system_hidden`: System modules
- `scheduled_for_deletion`: Being deleted

All are useful for complete field mapping!

## Common Issues

**"No modules found"**
- Check credentials in config file
- Credentials may have expired
- Try refreshing from Chrome DevTools

**"Error getting fields for {module}: 400"**
- Module API name might be wrong
- Some system modules don't support field queries
- Check the error details in logs

**Missing fields in output**
- Check the module file directly
- Some modules have restricted field access
- User permissions might limit what's returned

## Next Steps

After extracting modules:

1. **Review the data**
   ```powershell
   # Look at what you got
   dir data\blades\raw\modules\
   
   # Open a module file
   code data\blades\raw\modules\Accounts.json
   ```

2. **Check field mappings**
   Search for specific fields to see their API names

3. **Run blueprint analysis**
   Now that you have field mappings, the analyzer can convert labels to API names

4. **Build Rosetta Stone**
   Combine all data sources for complete field transformation mapping

## Example: Finding a Field's API Name

Looking for "Qualified Date" field in Potentials:

```powershell
# Search in the Potentials module file
findstr /C:"Qualified Date" data\blades\raw\modules\Potentials.json
```

Or open the file and search for the field to see:
```json
{
  "field_label": "Qualified Date",
  "api_name": "Qualified_Date",
  "column_name": "QUALIFIEDDATE"
}
```

## Integration with Blueprint Data

**Blueprint transition says:**
```json
{
  "field_updates": [
    {"field_label": "Stage", "field_value": "Qualified"}
  ]
}
```

**Module data says:**
```json
{
  "field_label": "Stage",
  "api_name": "Stage"
}
```

**Analyzer combines them:**
```json
{
  "api_name": "Stage",
  "updated_in_blueprints": [
    {
      "blueprint": "Field Sales Process",
      "transition": "Qualify",
      "new_value": "Qualified"
    }
  ]
}
```

Perfect! Now we have the complete picture! 🎯
