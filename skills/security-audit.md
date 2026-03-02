# Security Audit Skill

## Purpose
Run comprehensive security audit on LiQUiD SOUND codebase.

## Workflow

### 1. Scan for Secrets
```bash
grep -rn "api_key\|password\|secret\|token" --include="*.py" . | grep -v ".secrets\|REDACTED"
```

### 2. Check Dependencies
```bash
# Check for vulnerabilities
pip-audit || npm audit
```

### 3. Run Cipher Review
```bash
# Analyze code for vulnerabilities
python -c "from sentinel.tasks.security_scanner import scan_codebase; print(scan_codebase())"
```

### 4. Test Auth
```bash
# Verify no hardcoded credentials
git grep -E "(sk-|pk_live_|xoxb-)" -- "*.py" "*.js"
```

## Focus Areas
- SQL injection
- Command injection
- XSS vulnerabilities
- Hardcoded secrets
- Insecure random

## Output
- Post findings to #idea-ocean
- Update security_audit.md with results
- Create fix PR if critical issues found
