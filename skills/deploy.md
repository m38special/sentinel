# Deploy Skill

## Purpose
Deploy LiQUiD SOUND services to production.

## Workflow

### 1. Check Status
```bash
# Check Railway status
openclaw status

# Check recent commits
git log --oneline -5
```

### 2. Deploy Service
```bash
# Push to GitHub (auto-deploys)
git push origin phase5
```

### 3. Verify
```bash
# Test endpoints
curl https://sentinel-production-f9d8.up.railway.app/health
curl https://radiant-alpaca-fdf79f.netlify.app/
```

### 4. Notify
- Post to #idea-ocean in Slack
- Update MEMORY.md with deployment timestamp

## Services
- SENTINEL: https://sentinel-production-f9d8.up.railway.app
- Liquid.Swap: https://radiant-alpaca-fdf79f.netlify.app
- LiQUiD SOUND: liquidsound.us (DNS pending)
