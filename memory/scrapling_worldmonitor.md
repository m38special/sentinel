# Scrapling + World Monitor Analysis

---

## 🕷️ Scrapling (17.3k stars)

**Adaptive web scraping framework**

### Key Features
- Cloudflare/Turnstile bypass
- Auto-relocates DOM elements when layouts change (5.2x faster than AutoScraper)
- Async spider with proxy rotation
- HTTP/3 support
- MCP server for Claude-native integration

### Our Adoption

| Agent | Use Case |
|-------|----------|
| **NOVA** | Replace brittle trend scrapers. TikTok/Reddit/X/Instagram without blocks |
| **SENTINEL** | Augment PumpPortal with DEX pages, on-chain data behind bot protection |
| **Financial Analysts** | SEC filings, earnings pages, crypto news — no IP bans |

### Implementation
```python
# MCP = NOVA can use it natively
# Adaptive parsing = zero maintenance when sites update
```

---

## 🌍 World Monitor (16.5k stars)

**Real-time global intelligence dashboard**

### Key Features
- 150+ feeds: GDELT, ACLED, Feodo, URLhaus, AlienVault
- 36 toggleable map layers
- AI 4-tier summarization: Ollama → Groq → OpenRouter → Browser T5
- Country Instability Index (0-100 real-time)
- 4 variants: World/Tech/Finance/Happy

### Our Adoption

| Agent | Use Case |
|-------|----------|
| **Captain Yoruichi** | Finance Monitor = CFO dashboard |
| **Risk Manager** | GDELT + ACLED for geopolitical risk |
| **AXIOM** | Polymarket predictions = sentiment signal |
| **SENTINEL** | 4-tier AI summarization for signal synthesis |

### Data Sources to Wire
- **Markets:** CoinGecko, Polymarket, FRED
- **Geopolitics:** GDELT, ACLED
- **Threat Intel:** Feodo, URLhaus, AlienVault

---

## 🚀 Implementation Priorities

### Now
- [ ] Scrapling for NOVA (trend monitoring)

### Soon  
- [ ] World Monitor as internal dashboard
- [ ] Polymarket → AXIOM signal

### Later
- [ ] 4-tier AI fallback for SENTINEL alerts
