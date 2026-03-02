# /audit - Security Audit

Run comprehensive security audit on codebase.

## Usage
/audit [scope]

## Scopes
- full — Complete audit (default)
- quick — Fast scan for secrets
- dependencies — Check vulnerable packages

## Checks
1. Hardcoded secrets
2. SQL injection
3. XSS vulnerabilities
4. Command injection
5. Dependency vulnerabilities

## Examples
/audit
/audit quick
/audit dependencies
