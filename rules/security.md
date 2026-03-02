# Security Rules

Always follow these security practices:

## Secrets
- Never commit API keys, tokens, or secrets
- Use .secrets or environment variables
- Run `grep -r "sk-\|api_key\|password"` before commit

## Validation
- Validate all inputs
- Sanitize user data
- Use parameterized queries

## Dependencies
- Keep packages updated
- Run `pip-audit` regularly
- Review PR dependencies

## Access
- Principle of least privilege
- No hardcoded credentials
- Rotate keys regularly
