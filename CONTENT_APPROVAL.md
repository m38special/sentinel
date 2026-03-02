# Content Approval Workflow

**Rule: Nothing goes live without human approval.**

## Flow

1. **Draft** → Agent creates content draft
2. **Queue** → Content goes to approval channel with approve/reject
3. **Review** → Human reviews
4. **Published** → Only after explicit approval

## Implementation

- Slack: Use message with reactions (✅ approve, ❌ reject)
- Telegram: Inline buttons (if supported)

## Approval Channels

| Content Type | Channel | Approver |
|--------------|---------|----------|
| Social posts | #idea-ocean | CEO |
| SENTINEL alerts | Slack/Telegram | Auto-approved (alerts are informational) |
| Agent commits | #idea-ocean | CEO |

## Notes

- Never auto-post to social media
- Always queue for approval first
- Rejected content gets discarded
