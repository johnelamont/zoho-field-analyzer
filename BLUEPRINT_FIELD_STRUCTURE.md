# Blueprint Transition Field Structure - Explained

## Your Questions Answered

### Q1: Why does "Shipping State" appear 4 times?

**Answer:** It appears in `FieldsMeta`, which contains **ALL available fields** in the module, not just the ones being updated.

The 4 occurrences are:
1. `FieldsMeta.Potentials[90]` - Main module field definition
2. `rlMeta.{module_id}.relModFieldsMeta` (3 times) - Related module field definitions

**Key insight:** `FieldsMeta` = field catalog (all 186 Potentials fields)
**Not the same as:** Fields being updated in this transition (9 fields)

---

## The Actual Structure

### Where the 9 Field Updates Are Defined

**1. Fields Array** (10 items - 9 fields + 1 info message)
```json
{
  "Fields": [
    {
      "Type": "Field",
      "Id": "3193870000110629420",
      "Module": "Potentials",
      "uiType": "3"
      // This is a field being updated
    },
    {
      "Type": "Info",
      "Info": "You can only skip default follow ups..."
      // This is just an informational message
    }
  ]
}
```

**2. FieldVsLable** (Field ID → Display Label)
```json
{
  "FieldVsLable": {
    "3193870000027436132": "Accounts Payable Email",
    "3193870000112392062": "Skip Auto Follow Up Calls",
    "3193870000110629420": "Special Delivery Instructions",
    "3193870000007557139": "Co-Op Used",
    "3193870000118852262": "Tax Exempt",
    "3193870000110629347": "Liftgate Required?",
    "3193870000110629378": "Shipping Updates Email",
    "3193870000110629390": "Delivery Site Phone",
    "3193870000052648001": "One Time Shipping Instructions"
  }
}
```

**3. FieldVsName** (Field ID → API Column Name)
```json
{
  "FieldVsName": {
    "3193870000027436132": "POTENTIALCF40",
    "3193870000112392062": "POTENTIALCF205",
    "3193870000110629420": "POTENTIALCF201",
    "3193870000007557139": "POTENTIALCF8",
    "3193870000118852262": "POTENTIALCF209",
    "3193870000110629347": "POTENTIALCF192",
    "3193870000110629378": "POTENTIALCF194",
    "3193870000110629390": "POTENTIALCF196",
    "3193870000052648001": "POTENTIALCF45"
  }
}
```

**4. Actions.Deluge** (Functions to execute)
```json
{
  "Actions": {
    "Deluge": [
      {
        "Id": "3193870000104375817",
        "Name": "Deals_SendLatestSalesorder"
      }
    ]
  }
}
```

---

## What Each Section Means

### FieldsMeta (Metadata Catalog)
- **Purpose:** Shows ALL available fields in the module
- **Count:** 186 fields for Potentials
- **Usage:** Reference for what fields exist, not what's being updated
- **Why "Shipping State" appears 4 times:** It's defined in:
  1. Main Potentials module
  2. Related module 1 (Products?)
  3. Related module 2 (Sales Orders?)
  4. Related module 3 (Quotes?)

### Fields Array (Actual Fields in Transition)
- **Purpose:** Fields being collected/updated in THIS transition
- **Count:** 10 items (9 fields + 1 info message)
- **Structure:** Each has `Id`, `Type`, `Module`, `uiType`
- **Usage:** These are the fields the user fills out during transition

### FieldVsLable (Display Names)
- **Purpose:** Map field IDs to human-readable labels
- **Count:** 9 mappings
- **Example:** `3193870000110629420` → `"Special Delivery Instructions"`
- **Usage:** What the user sees in the Zoho UI

### FieldVsName (API Column Names)
- **Purpose:** Map field IDs to database column names
- **Count:** 9 mappings
- **Example:** `3193870000110629420` → `"POTENTIALCF201"`
- **Problem:** These are column names, NOT the nice API names
- **Solution:** Use modules data to get real API names

---

## Where Are the Real API Names?

**Problem:** `FieldVsName` gives you `POTENTIALCF201`, not `Special_Delivery_Instructions`

**Solution:** Use the modules extractor data!

### Modules Data Structure:
```json
{
  "module": "Deals",
  "fields": [
    {
      "id": "3193870000110629420",
      "field_label": "Special Delivery Instructions",
      "api_name": "Special_Delivery_Instructions",  ← REAL API NAME
      "column_name": "POTENTIALCF201"               ← MATCHES FieldVsName
    }
  ]
}
```

### The Mapping Chain:
```
Blueprint Transition
  ↓
FieldVsLable: "3193870000110629420" → "Special Delivery Instructions"
  ↓
FieldVsName: "3193870000110629420" → "POTENTIALCF201"
  ↓
Modules Data: column_name "POTENTIALCF201" → api_name "Special_Delivery_Instructions"
```

---

## Why Multiple Representations?

Zoho uses different field references in different contexts:

| Context | Uses | Example |
|---------|------|---------|
| **User Interface** | Field Label | "Special Delivery Instructions" |
| **API Calls** | API Name | "Special_Delivery_Instructions" |
| **Database** | Column Name | "POTENTIALCF201" |
| **Internal ID** | Field ID | "3193870000110629420" |

Blueprints use **Field Labels** for display and **Column Names** internally.

---

## Summary for Your Transition

**Your "Verify Details-Send Salesorder" transition has:**

✅ **9 fields being updated:**
1. Accounts Payable Email
2. Skip Auto Follow Up Calls
3. Special Delivery Instructions
4. Co-Op Used
5. Tax Exempt
6. Liftgate Required?
7. Shipping Updates Email
8. Delivery Site Phone
9. One Time Shipping Instructions

✅ **1 function to execute:**
- Deals_SendLatestSalesorder (runs AFTER transition)

✅ **Field definitions are in 3 places:**
- `Fields` array - What fields are in the transition
- `FieldVsLable` - Field ID → Display label mapping
- `FieldVsName` - Field ID → Column name mapping

❌ **"Shipping State" is NOT being updated in this transition**
- It appears 4 times in `FieldsMeta` (available fields catalog)
- It does NOT appear in `Fields`, `FieldVsLable`, or `FieldVsName`
- It's just metadata showing what fields exist, not what's being used

---

## Building the Rosetta Stone

To get complete field mapping:

1. **From Blueprint Transition:**
   - Field ID: `3193870000110629420`
   - Field Label: `"Special Delivery Instructions"` (from FieldVsLable)
   - Column Name: `"POTENTIALCF201"` (from FieldVsName)

2. **From Modules Data:**
   - Match column_name `"POTENTIALCF201"` → Get api_name `"Special_Delivery_Instructions"`

3. **Result:**
   - Blueprint updates: `"Special Delivery Instructions"` (label)
   - Functions use: `"Special_Delivery_Instructions"` (API name)
   - Database stores: `"POTENTIALCF201"` (column name)
   - Internal reference: `"3193870000110629420"` (field ID)

All four representations point to the SAME field! 🎯

---

## Code Impact

Our blueprint extractor already captures:
- ✅ `field_label` from FieldVsLable
- ✅ `field_id` from Fields array
- ❌ Need to add: `column_name` from FieldVsName

Then the Rosetta Stone analyzer can:
1. Take blueprint `column_name`
2. Look it up in modules data
3. Get the `api_name`
4. Map blueprint field updates to API names
5. Compare with function field references
6. Show complete cross-system field usage

**Next update:** Add column_name extraction to blueprint transition processing! 📝
