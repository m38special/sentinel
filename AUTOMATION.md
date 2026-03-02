# LiQUiD SOUND Automation System

Based on OpenClaw/Claude Code best practices.

## Structure

```
├── commands/      # Slash commands (/deploy, /audit, /test, /review)
├── skills/        # Workflow definitions
├── rules/         # Always-follow guidelines
└── hooks.json     # Pre/Post tool automation
```

## Commands

| Command | Description |
|---------|-------------|
| `/deploy` | Deploy to Railway/Netlify |
| `/audit` | Run security scan |
| `/test` | Execute test suite |
| `/review` | Trigger 3-AI code review |

## Skills

| Skill | Purpose |
|-------|---------|
| `deploy.md` | Production deployment |
| `security-audit.md` | Security scanning |
| `onboard-agent.md` | Add new AI agents |

## Rules

- `security.md` — Security practices
- `coding-style.md` — Code standards
- `git-workflow.md` — Commit/PR process

## Hooks

PreToolUse: Block dangerous commands
PostToolUse: Validate syntax
Stop: Check for uncommitted changes

---

*Built by Captain Urahara | LiQUiD SOUND*
