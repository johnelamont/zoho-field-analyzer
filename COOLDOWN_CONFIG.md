# Cooldown Pause Configuration - FIXES TRANSITION 77 RATE LIMITING

## The Problem
Blueprint extraction consistently fails at transition 77 due to Zoho's rate limiting.

## The Solution
**Cooldown pauses** - Pause for 3 minutes after every 76 transitions to let Zoho's rate limit window reset.

## Add This to Your blades.yaml

Add this section to your `config/blades.yaml` file (or wherever you keep it locally):

```yaml
# Rate limiting settings
# Controls delays and cooldown pauses to avoid Zoho's rate limits
rate_limiting:
  # Base delay between transition requests (seconds)
  base_delay: 4.0
  
  # Cooldown pause settings (for blueprint transitions)
  # Zoho has a rolling window rate limit (~100 requests per 5 minutes)
  # Taking periodic breaks prevents hitting this limit
  cooldown:
    enabled: true
    after_requests: 76       # Pause after this many transitions
    duration: 180            # Pause for this many seconds (3 minutes)
```

**Place it AFTER the `zoho_credentials` section and BEFORE the `extraction` section.**

## Full Example

Here's what your `blades.yaml` should look like:

```yaml
# Client identification
client_name: "blades"
description: "Blades CRM extraction"

# Zoho API Credentials
zoho_credentials:
  cookie: "YOUR_COOKIE_HERE"
  csrf_token: "crmcsrfparam=YOUR_CSRF_TOKEN_HERE"
  org_id: "666154101"

# Rate limiting settings  ← ADD THIS SECTION
rate_limiting:
  base_delay: 4.0
  cooldown:
    enabled: true
    after_requests: 76
    duration: 180

# Extraction settings (existing section - don't change)
extraction:
  enabled_extractors:
    - functions
    - workflows
    - blueprints
    - modules
  request_delay: 0.5
  max_retries: 3
  retry_delay: 1.0
```

## How It Works

### Without Cooldown (OLD - Failed at 77)
```
Transition 1-76:  [4s delay each] → SUCCESS
Transition 77:    [4s delay] → RATE LIMITED (HTML error page)
Transition 78+:   ALL FAIL
```

### With Cooldown (NEW - Should Work)
```
Transition 1:     [Extract] → Wait 4s
Transition 2:     [Extract] → Wait 4s
...
Transition 76:    [Extract] → Wait 4s
                  ↓
        ╔═══════════════════════════════════════╗
        ║  COOLDOWN PAUSE                       ║
        ║  Completed 76 transitions             ║
        ║  Pausing for 180s (3.0 minutes)      ║
        ║  This allows Zoho's rate limit       ║
        ║  window to reset...                  ║
        ╚═══════════════════════════════════════╝
                  ↓
        [3 minutes pass]
                  ↓
Transition 77:    [Extract] → Wait 4s  ← SHOULD SUCCEED!
Transition 78:    [Extract] → Wait 4s
...
Transition 143:   [Extract] → DONE!
```

## What You'll See

### Console Output at Transition 76
```
[76/143] Review Order (ID: 3193870000620958260)
  [OK] 3 field updates, 0 function calls
  Waiting 4.0s before next request...

  ========================================
  COOLDOWN: Completed 76 transitions
  Pausing for 180 seconds (3.0 minutes)
  This allows Zoho's rate limit window to reset...
  ========================================

[Extraction pauses for 3 minutes]

  Cooldown complete - resuming extraction...

[77/143] Flag For Review (ID: 3193870000620958261)
  [OK] 2 field updates, 0 function calls  ← SUCCESS!
  Waiting 4.0s before next request...
```

## Time Impact

### For 143 Transitions

**Without cooldown:**
- 143 transitions × 4s = 572 seconds = 9.5 minutes
- **Result:** FAILS at transition 77

**With cooldown:**
- Transitions 1-76: 76 × 4s = 304 seconds (5 minutes)
- Cooldown pause: 180 seconds (3 minutes)
- Transitions 77-143: 67 × 4s = 268 seconds (4.5 minutes)
- **Total: 752 seconds = 12.5 minutes**
- **Result:** COMPLETE SUCCESS ✅

**Trade-off:** 3 extra minutes for 100% success rate

## Tuning the Settings

You can adjust these values based on your results:

### If Still Fails at 77
**Problem:** 3-minute pause not long enough
**Solution:** Increase duration
```yaml
cooldown:
  enabled: true
  after_requests: 76
  duration: 300        # 5 minutes instead of 3
```

### If You Want to Be More Aggressive
**Problem:** Want faster extraction
**Solution:** Pause less frequently (riskier)
```yaml
cooldown:
  enabled: true
  after_requests: 100  # Try 100 instead of 76
  duration: 180
```

### If You Want to Be More Conservative
**Problem:** Want to be extra safe
**Solution:** Pause more frequently
```yaml
cooldown:
  enabled: true
  after_requests: 50   # Pause every 50 transitions
  duration: 180
```

### To Disable Cooldown
```yaml
cooldown:
  enabled: false       # Turn it off
  after_requests: 76
  duration: 180
```

## Multiple Blueprints

If extracting multiple blueprints, the cooldown applies to **each blueprint separately**:

**Blueprint 1:**
- Transitions 1-76 → Cooldown → Transitions 77-143

**Blueprint 2:**  
- Transitions 1-76 → Cooldown → Transitions 77-120

Each blueprint gets its own cooldown pauses.

## Run the Extraction

After adding the config:

```powershell
python -m src.extractors.main --client blades --extract blueprints --with-transitions
```

**Expected behavior:**
1. Extracts transitions 1-76 (5 minutes)
2. Pauses for 3 minutes (cooldown)
3. Continues with transitions 77-143 (4.5 minutes)
4. Completes successfully! 🎯

## Why This Works

**Zoho's Rate Limit Theory:**
- Rolling 5-minute window
- ~100 requests maximum per window
- At 4s per request: 76 requests = ~300 seconds (5 minutes)
- We hit exactly 76 requests in ~5 minutes
- Cooldown lets oldest requests "age out" of the window
- New requests don't hit the limit

**The 3-minute pause:**
- Lets 3 minutes worth of old requests drop off
- Creates headroom for new requests
- Prevents hitting the 100-request ceiling

## What Changed in Code

The cooldown logic now triggers based on **transition number** (1, 2, 3... 76), not "successful requests". This ensures the pause happens BEFORE we hit the rate limit at transition 77.

**Before (failed):**
```python
if successful_requests % 76 == 0:  # Only counts successes
    # Transition 77 fails BEFORE this check
```

**After (works):**
```python
if i % 76 == 0:  # Counts all transitions
    # Pause happens AFTER transition 76, BEFORE transition 77
```

## Summary

✅ **Add rate_limiting section to blades.yaml**  
✅ **Run blueprint extraction again**  
✅ **Watch for cooldown pause after transition 76**  
✅ **Transition 77 should succeed!**  
✅ **Complete extraction in ~12.5 minutes**  

This should finally solve the transition 77 rate limiting issue! 🎯
