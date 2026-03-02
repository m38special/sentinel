# EPISODIC MEMORY — Action History & Patterns

_Every action, result, mistake, and success. Structured for quick retrieval._

---

## 2026-02-27 — SENTINEL Launch Day

### Episode 1: SENTINEL WebSocket Schema Mismatch
**Action:** Built SENTINEL MVP with WebSocket listener  
**Result:** Zero tokens detected for hours  
**Root Cause:** Code expected `{"method": "newToken", "data": {...}}` but PumpPortal sends flat JSON with `txType: "create"`  
**Fix:** Validate token by checking `txType == 'create'` directly on raw JSON  
**Pattern:** Always verify actual API response format before writing parsing logic

### Episode 2: CIPHER Audited Wrong Code Version
**Action:** Sent SENTINEL for security audit  
**Result:** CIPHER audited old HTTP polling code instead of new WebSocket version  
**Root Cause:** Didn't specify exact commit/file when requesting audit  
**Fix:** Always provide specific file paths or commit hashes for reviews  
**Pattern:** Context must include exact source references

### Episode 3: Redis URL Without Auth
**Action:** Configured Redis for UAI  
**Result:** Services couldn't connect  
**Root Cause:** Railway Redis requires password in URL format: `redis://default:PASSWORD@host:port`  
**Fix:** Always include full connection string with credentials  
**Pattern:** Test connections end-to-end before deployment

### Episode 4: MIN_MARKET_CAP Wrong Unit
**Action:** Set MIN_MARKET_CAP = 10,000 (USD)  
**Result:** All tokens filtered — new launches are ~$4,500  
**Root Cause:** Field is in SOL, not USD  
**Fix:** Use SOL-denominated thresholds, convert via SOL_USD_ESTIMATE  
**Pattern:** Verify units/types before setting thresholds

### Episode 5: Duplicate Alert Race Condition
**Action:** Multiple tokens trigger alerts concurrently  
**Result:** Duplicate alerts sent  
**Fix:** Atomic DB update — mark sent BEFORE sending alerts  
**Pattern:** For concurrent operations, use atomic transactions

### Episode 6: Missing redis Package
**Action:** Added UAI integration with Redis  
**Result:** ImportError on Railway  
**Fix:** redis>=5.0.0 in requirements.txt  
**Pattern:** All imports must be in requirements

### Episode 7: Git Embed Issue
**Action:** Committed workspace with nested repos  
**Result:** Git saw axiom/cipher/nova as embedded repos  
**Fix:** Use submodules or keep repos separate at same parent level  
**Pattern:** Don't nest git repos

---

## Recurring Patterns

| Pattern | Prevention |
|---------|------------|
| Wrong API schema | Test with real data first |
| Missing credentials | Test connections before deploy |
| Wrong units | Verify data types/units in source |
| Race conditions | Use atomic operations |
| Import errors | Audit requirements after code changes |

---

*This file trains future-you. Making the same mistake twice is unforgivable.*
