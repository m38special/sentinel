# Liquid Sound - Launch Checklist

## Pre-Launch (Day -1)

### Infrastructure
- [ ] Redis instance running
- [ ] TimescaleDB connected
- [ ] Celery workers running (3+)
- [ ] Health dashboard accessible
- [ ] Slack bot authenticated

### Services
- [ ] CIPHER deployed (cipherprotect.netlify.app)
- [ ] AXIOM deployed (axiomquantum.netlify.app)
- [ ] SENTINEL WebSocket listener running
- [ ] NOVA social scanner active
- [ ] DREAM content generator ready

### Security
- [ ] API keys in environment (not code)
- [ ] Redis auth enabled
- [ ] Rate limiting configured
- [ ] CIPHER audit complete
- [ ] Dependencies updated

### GitHub
- [ ] All PRs merged to main
- [ ] CI/CD passing
- [ ] Version tagged (v2.1.0)

---

## Launch Day

### Morning (9am CT)
- [ ] Deploy latest to Railway
- [ ] Verify health dashboard green
- [ ] Check Slack bot responding
- [ ] Run test token through pipeline

### Mid-Day
- [ ] Monitor SENTINEL for token signals
- [ ] Verify NOVA scanning social
- [ ] Check AXIOM scoring tokens
- [ ] Review alerts in #plays channel

### Evening
- [ ] Daily briefing at 7pm CT
- [ ] Review day's signals
- [ ] Document any issues

---

## Post-Launch (Week 1)

### Monitoring
- [ ] Check health dashboard daily
- [ ] Review error logs
- [ ] Monitor API usage

### Iterations
- [ ] Collect feedback
- [ ] Fix issues
- [ ] Plan Phase 5

---

## Emergency Contacts

| Role | Name | Channel |
|------|------|---------|
| CTO | Urahara | @urahara |
| CFO | Yoruichi | @yoruichi |
| Security | CIPHER | @cipher |

---

## Rollback Plan

If issues detected:
1. Pause Celery workers
2. Revert to previous Railway deployment
3. Investigate logs
4. Fix and redeploy
