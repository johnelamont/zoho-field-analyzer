# Blueprint Rate Limiting - Progressive Backoff Solution

## Problem
Even with 2-second delays, rate limiting occurs at transition 77/143 consistently.

## New Solution: Progressive Backoff

### Changes Made

**1. Increased Base Delay: 2s → 4s**
```python
current_delay = 4.0  # Start with 4 seconds (was 2.0)
```

**2. Progressive Backoff on Failures**
```python
# When a transition fails after position 70:
rate_limit_hits += 1
current_delay = min(current_delay + 2.0, 10.0)  # Increase by 2s, max 10s
```

**3. Delay Visibility**
```python
logger.info(f"Waiting {current_delay:.1f}s before next request...")
# You'll see: "Waiting 4.0s..." then "Waiting 6.0s..." after failures
```

## How It Works

### Normal Flow (No Rate Limiting)
```
Transition 1:  [Extract] → Wait 4s
Transition 2:  [Extract] → Wait 4s
Transition 3:  [Extract] → Wait 4s
...
Transition 76: [Extract] → Wait 4s
Transition 77: [Extract] → Wait 4s
...
Transition 143: [Extract] → Done!
```

**Time:** 143 transitions × 4s = 572 seconds = **9.5 minutes**

### With Rate Limiting Detection
```
Transition 1:   [Extract] → Wait 4s
...
Transition 76:  [Extract] → Wait 4s
Transition 77:  [FAIL - Rate Limit] → Increase to 6s
Transition 78:  Wait 6s → [Extract] → Wait 6s
Transition 79:  Wait 6s → [Extract] → Wait 6s
...continues with 6s delay
```

**Time:** 
- First 76: 76 × 4s = 304s
- Last 67: 67 × 6s = 402s
- **Total: ~12 minutes**

### If Rate Limiting Continues
```
Transition 77:  [FAIL] → Delay: 4s → 6s
Transition 78:  [FAIL] → Delay: 6s → 8s
Transition 79:  [SUCCESS] → Delay stays at 8s
Transition 80:  [SUCCESS] → Delay stays at 8s
...continues with 8s delay
```

Maximum delay caps at **10 seconds**.

## Expected Behavior

### Console Output - Normal
```
[1/143] Verify Details-Send Salesorder (ID: 3193870000102787158)
  [OK] 9 field updates, 1 function calls
  Waiting 4.0s before next request...

[2/143] Contact Customer (ID: 3193870000102787159)
  [OK] 0 field updates, 0 function calls
  Waiting 4.0s before next request...
```

### Console Output - Rate Limiting Detected
```
[76/143] Review Order (ID: 3193870000620958260)
  [OK] 3 field updates, 0 function calls
  Waiting 4.0s before next request...

[77/143] Flag For Review (ID: 3193870000620958261)
  [FAIL] Could not get transition details
  Possible rate limiting - increasing delay to 6.0s
  Waiting 6.0s before next request...

[78/143] Next Transition (ID: 3193870000620958262)
  [OK] 2 field updates, 0 function calls
  Waiting 6.0s before next request...
```

## Why This Works

### The 77-Transition Pattern
Your system consistently hits rate limiting at transition 77:
- **Transitions 1-76:** Succeed with any delay
- **Transition 77+:** Trigger rate limit

**Hypothesis:** Zoho's rate limiter uses a **rolling time window**:
- Window: ~5 minutes
- Threshold: ~75-80 requests per window
- When exceeded: Block subsequent requests temporarily

### Progressive Backoff Solution
1. **Start conservative:** 4 seconds (15 requests/minute)
2. **Detect failures:** Watch for failures after transition 70
3. **Slow down more:** Increase to 6s, 8s, or 10s as needed
4. **Self-adjusting:** Automatically finds the right speed

## Time Comparison

| Delay Strategy | Time for 143 Transitions | Success Rate |
|----------------|-------------------------|--------------|
| **0.75s** (original) | 107s (1.8 min) | ❌ Fails at 77 |
| **2.0s** (first fix) | 286s (4.8 min) | ❌ Still fails at 77 |
| **4.0s** (new base) | 572s (9.5 min) | ⏳ Testing... |
| **4s→6s** (progressive) | ~720s (12 min) | ✅ Should work! |

**Trade-off:** Slower but reliable extraction

## Testing

Run the extraction:
```powershell
python -m src.extractors.main --client blades --extract blueprints --with-transitions
```

### What to Watch For

**Success indicators:**
- All 143 transitions complete
- Delays increase automatically if failures occur
- Final summary shows 143/143 successful

**Failure indicators:**
- Still fails at transition 77 even with 6s delay
- Multiple consecutive failures
- Delay increases to 10s max but still failing

## If It Still Fails

### Option 1: Increase Maximum Delay
Edit blueprints.py line ~342:
```python
current_delay = min(current_delay + 2.0, 15.0)  # Increase max to 15s
```

### Option 2: Increase Base Delay
Edit blueprints.py line ~275:
```python
current_delay = 6.0  # Start at 6 seconds instead of 4
```

### Option 3: Extract One Blueprint at a Time
```powershell
# Do each blueprint separately with breaks
python -m src.extractors.main --client blades --extract blueprints --blueprint-id {ID1} --blueprint-module {MODULE} --with-transitions

# Wait 10 minutes

python -m src.extractors.main --client blades --extract blueprints --blueprint-id {ID2} --blueprint-module {MODULE} --with-transitions
```

### Option 4: Run During Off-Peak Hours
Zoho's rate limiting might be less aggressive:
- Evenings (after 8 PM your time)
- Weekends
- Early mornings (before 6 AM)

## Key Improvements

✅ **4-second base delay** (2x longer than before)  
✅ **Progressive backoff** (auto-increases on failures)  
✅ **Delay visibility** (you see the wait time)  
✅ **Smart detection** (watches for failures after transition 70)  
✅ **Capped at 10s** (won't slow down indefinitely)  

## Expected Results

**Most likely outcome:**
- Transitions 1-76: Success with 4s delays (5 minutes)
- Transition 77: Fails, delay increases to 6s
- Transitions 78-143: Success with 6s delays (7 minutes)
- **Total: 12-13 minutes** for complete extraction

**If successful, you'll see:**
```
============================================================
EXTRACTION SUMMARY
============================================================
Blueprints processed: 1
Total transitions: 143
Total field updates: 427
Successfully saved: 1
Failed: 0
```

## Bottom Line

The **4-second base + progressive backoff** approach should handle Zoho's rate limiting automatically. If transition 77 fails, the system:
1. Detects the failure
2. Increases delay to 6 seconds
3. Continues successfully with longer delays

**Patience is key:** 12-13 minutes for 143 transitions is normal and expected! 🎯

Let's see if this works! 🚀
