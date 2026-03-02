# Onboard Agent Skill

## Purpose
Onboard new AI agent to LiQUiD SOUND team.

## Workflow

### 1. Create Agent Profile
- Name the agent
- Define role (CTO, CFO, Quant, Security, Social)
- Set Telegram bot username

### 2. Configure Access
- Add to agent_registry.py
- Set UAI channel permissions
- Configure Redis keys

### 3. Add to Memory
- Update MEMORY.md with agent details
- Add to TEAM_ROSTER.md

### 4. Set Schedule
- Define briefing times (7am CT default)
- Configure heartbeat interval
- Set notification channels

### 5. Test
- Send test message via UAI
- Verify response
- Add to #idea-ocean

## Agent Templates

### Quantitative Analyst (AXIOM)
- Focus: Data analysis, predictions
- Channels: axiom:score, axiom:signal

### Security (CIPHER)
- Focus: Threat detection, audits
- Channels: security_alert, uai:events

### Social (NOVA)
- Focus: Sentiment, content
- Channels: social_signal, nova:post
