# /test - Run Test Suite

Execute test suite for LiQUiD SOUND.

## Usage
/test [scope]

## Scopes
- unit — Unit tests only
- integration — Integration tests
- all — Full test suite (default)

## Commands
```bash
pytest tests/           # Unit tests
pytest tests/ -v       # Verbose
pytest tests/ --cov     # With coverage
```

## CI Integration
Tests run automatically on PR via GitHub Actions.

## Examples
/test
/test unit
/test all
