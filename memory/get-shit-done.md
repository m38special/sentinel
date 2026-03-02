# get-shit-done (21.2k stars) — Analysis

**Context engineering + spec-driven development**

---

## Core Philosophy

> "The complexity is in the system, not in your workflow. Behind the scenes: context engineering, XML prompt formatting, subagent orchestration, state management."

**Problem:** Context rot — quality degradation as context fills

---

## Key Patterns

### 1. Thin Orchestrator
- Stays at 30-40% context
- Spawns specialized subagents with fresh 200k contexts
- Never does heavy lifting — coordinates only

### 2. Wave Execution
- **Parallel:** Independent tasks run simultaneously
- **Sequential:** Dependent tasks run in order

### 3. Atomic Git Commits
- One commit per task
- Clean history, easy rollback

### 4. Document Flow
```
PROJECT.md   → What we're building
STATE.md     → Current decisions, blockers, position
PLAN.md      → Task plan
SUMMARY.md   → What was done
VERIFICATION.md → Proof it works
```

---

## Our Adoption

### Captain Yoruichi (Orchestrator)
- [x] Thin coordinator — Yoruichi coordinates, agents execute
- [ ] STATE.md for persistent task state across handoffs
- [ ] Wave execution — parallel NOVA + Analysts, sequential dependencies

### All Agents
- [ ] PLAN.md → SUMMARY.md → VERIFICATION.md flow

### SENTINEL Phase 2
- [x] Docker + Redis + Celery + TimescaleDB = 4 parallel wave tasks
- [ ] Atomic commits per task

---

## GSD Workflow Implementation

```yaml
# STATE.md template
## Current Position
- Active task: X
- Completed: [A, B, C]
- Blockers: []

## Decisions
- Decision: X → Reason: Y

## Wave Status
- Wave 1: [parallel tasks]
- Wave 2: [depends on wave 1]
```

---

## Priority

1. Create STATE.md in workspace
2. Document wave execution for parallel agent tasks
3. Formalize PLAN → SUMMARY → VERIFICATION

---
