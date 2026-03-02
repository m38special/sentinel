# LEARNINGS.md - Lessons from Mistakes

_Every correction → fix it → write the lesson → write a rule → review at session start_

---

## 2026-02-27

### SENTINEL Deployment Issues

**Problem:** Railway couldn't reach api.pumpportal.fun (DNS failure from Railway network)

**Lesson:** Always test connectivity from the deployment environment, not just local

**Rule:** Before deploying, verify the target API/endpoint is reachable from the deployment environment

---

### CIPHER Audit - Old Code Version

**Problem:** CIPHER audited old HTTP polling code instead of new WebSocket version

**Lesson:** When requesting audits, specify exact commit/file versions

**Rule:** Always provide specific file paths or commit hashes when sending for review

---

### Slack @Mentions

**Problem:** Used wrong mention format for agents

**Lesson:** Slack needs proper user IDs (`<@U0AHG31TTSN>`) not just @names

**Rule:** Test Slack mentions in a channel first before relying on them

---

### Git Push - Host Key Verification

**Problem:** SSH key not configured, fell back to HTTPS but had conflicts

**Lesson:** Ensure GitHub auth is configured before pushing

**Rule:** Run `gh auth status` before important git operations

---

### Redis URL - Duplicate Lines

**Problem:** .env had duplicate REDIS_URL lines (old + new)

**Lesson:** Always verify .env after edits

**Rule:** Use `cat` to verify config files after changes

---

### Memory Reset

**Problem:** Workspace reset wiped all code

**Lesson:** Git repo is safety net - push early, push often

**Rule:** Push to git immediately after significant changes

---

### Duplicate Alert Race Condition

**Problem:** Multiple async alert tasks could send duplicates

**Lesson:** Atomic operations - mark sent BEFORE sending, not after

**Rule:** For any async multi-step process, use atomic DB operations

---

### WebSocket Schema Mismatch

**Problem:** Code expected method/data wrapper, PumpPortal sends flat JSON with txType

**Lesson:** Always verify actual API response format before writing parsers

**Rule:** Test with real data, not assumptions

---

### Redis Auth Missing

**Problem:** URL without password failed on Railway

**Lesson:** Full connection string with credentials needed

**Rule:** Test connections end-to-end before deployment

---

### Wrong Units (USD vs SOL)

**Problem:** MIN_MARKET_CAP set to $10k, but PumpPortal returns SOL

**Lesson:** Verify data types/units in source

**Rule:** Check field units before setting thresholds

---

### Missing redis Package

**Problem:** ImportError on Railway

**Lesson:** All imports must be in requirements.txt

**Rule:** Audit requirements after adding new dependencies

---

---

### Railway Root Directory Missing

**Problem:** Deployed code but got 404 - Railway didn't find Dockerfile

**Lesson:** When project is in subdirectory, Railway needs "Root Directory" set

**Rule:** For monorepos or subfolder projects, explicitly set Root Directory in Railway service settings

---

### Railway webCommand Placement

**Problem:** 404 on deployed service - web config wasn't applied

**Lesson:** Railway `webCommand` needs to be at deploy level, not nested

**Rule:** Test Railway JSON schema before deploying

---

*Making the same mistake twice is unforgivable.*
