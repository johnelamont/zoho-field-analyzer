# Blueprint Transition Extraction Troubleshooting

## Issue
Blueprints extract successfully, but transitions fail to fetch.

## Updated Code
I've added comprehensive error handling and logging to help diagnose the issue:

### What Changed
1. ✅ Added try-catch around field extraction
2. ✅ Added try-catch around function extraction  
3. ✅ Added detailed logging in get_transition_details
4. ✅ Added response body logging on errors
5. ✅ Added full stack traces on exceptions

### Run Again and Check Logs

```powershell
python -m src.extractors.main --client blades --extract blueprints --with-transitions
```

### What to Look For

**In Console Output:**

1. **If you see HTTP errors:**
   ```
   Error getting transition {id}: 400
   Response body: {...}
   ```
   → Credentials expired or invalid parameters

2. **If you see empty response:**
   ```
   Empty response for transition {id}
   ```
   → API returned 200 but no data

3. **If you see Python exceptions:**
   ```
   Exception getting transition {id}: ...
   [traceback]
   ```
   → Code bug or unexpected data structure

4. **If you see field extraction errors:**
   ```
   Error extracting field updates: ...
   [traceback]
   ```
   → Issue with new Fields array processing

### Common Issues & Fixes

**Issue 1: Credentials Expired**
```
Error getting transition: 401 Unauthorized
```
**Fix:** Refresh credentials in config/blades.yaml from Chrome DevTools

**Issue 2: Invalid Transition ID**
```
Error getting transition: 400 Bad Request
```
**Fix:** May be a malformed transition or API change - check response body

**Issue 3: Empty Response**
```
Empty response for transition {id}
```
**Fix:** Transition might exist but have no data - this is OK, will skip

**Issue 4: Python Exception in Field Extraction**
```
Error extracting field updates: 'NoneType' object...
```
**Fix:** Transition structure different than expected - will log but continue

### Checking the Logs

Look in `logs/` directory for complete error details:
```
logs/
└── extraction_2024-02-12_*.log
```

The log will have full stack traces and all details.

### Test with Single Blueprint

If all transitions are failing, try extracting just one blueprint:

```powershell
python -m src.extractors.main --client blades --extract blueprints --blueprint-id 3193870000102787278 --blueprint-module Potentials --with-transitions
```

This will focus on just the Field Sales Process blueprint and show more detailed errors.

### Manual API Test

If you want to test the API directly, you can try the transition URL manually:

```
https://crm.zoho.com/crm/org{ORG_ID}/FlowTransition.do?action=getTransitionDetails&TransitionId={TRANSITION_ID}&Module={MODULE}&LayoutId={LAYOUT_ID}
```

Replace:
- `{ORG_ID}` with your org ID (from YAML)
- `{TRANSITION_ID}` with a transition ID (from blueprint JSON)
- `{MODULE}` with module name like "Potentials"
- `{LAYOUT_ID}` with layout ID (from blueprint JSON)

Open this URL in Chrome while logged into Zoho to see what the API returns.

### What I Need to Help Further

Please share:
1. The console output showing the error messages
2. Any stack traces from the log file
3. The specific error message for the first failing transition

With those details, I can pinpoint exactly what's failing and fix it! 🔧

## Possible Root Causes

Based on the symptoms (blueprints work, transitions fail):

1. **Credentials timeout mid-extraction** - Unlikely since blueprints worked
2. **Transition API changed** - Possible if Zoho updated the endpoint
3. **Rate limiting** - Unlikely, we have 750ms delays
4. **Blueprint has no transitions** - Would show "No transitions found"
5. **Transition details endpoint broken** - Need to see error code
6. **New field extraction code bug** - Caught by try-catch, would continue
7. **Function extraction bug** - Caught by try-catch, would continue

Most likely: **Transition API returning errors** or **Empty responses**

The new error logging will tell us exactly which! 🎯
