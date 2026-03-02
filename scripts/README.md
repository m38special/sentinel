# LiQUiD SOUND Auto Code Review System

Based on @elvissun's proven 3-AI reviewer system.

## Overview

Every PR gets reviewed by **three AI models**, each catching different things:

| Reviewer | Strength | Focus |
|----------|----------|-------|
| **Codex** | Edge cases, logic errors | Backend, complex bugs |
| **Gemini** | Security, scalability | Frontend, UI |
| **Claude** | Architecture, validation | Overall quality |

## Setup

### 1. Configure API Keys

Add to GitHub Secrets:
- `ANTHROPIC_API_KEY` - for Claude
- `OPENAI_API_KEY` - for Codex
- `GEMINI_API_KEY` - for Gemini (optional)

### 2. Enable Workflow

The workflow runs automatically on every PR.

### 3. Manual Run

```bash
./scripts/code-review.sh m38special/sentinel 42
```

## Definition of Done

For a PR to be merged:
- [ ] PR created
- [ ] CI passing
- [ ] All 3 AI reviewers approved
- [ ] No critical blockers

## How It Works

1. **PR opened** → GitHub Actions triggers
2. **Fetches diff** → Gets all changes
3. **Routes to reviewers** → Codex (logic), Gemini (security), Claude (architecture)
4. **Posts comment** → Summary on PR
5. **Human review** → Merge if approved

## Customization

Edit `scripts/code-review.sh` to:
- Add more reviewers
- Change review focus
- Add file type filters

---

*Built by Captain Urahara | LiQUiD SOUND*
