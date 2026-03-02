# SENTINEL 🚨

Real-time SPL Token Early Detection System

## Quick Start

```bash
# 1. Copy env template
cp .env.example .env

# 2. Edit .env with your tokens
nano .env

# 3. Run with Docker
docker-compose up -d sentinel-mvp
```

## Architecture

- **scanner_mvp.py** — Main scanner (asyncio, 5-min poll, SQLite)
- **alerts.py** — Slack + Telegram hooks
- **Docker** — Containerized deployment

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook |
| `TELEGRAM_BOT_TOKEN` | Telegram bot API token |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |

## License

MIT
