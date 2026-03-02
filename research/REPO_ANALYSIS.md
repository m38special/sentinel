# REPO DEEP DIVE — Scrapling + World Monitor

_Source: Code-level analysis from Captain Yoruichi_

---

## 🕷️ SCRAPLING — Implementation

### 4 Fetcher Classes
```python
from scrapling.fetchers import Fetcher, AsyncFetcher, StealthyFetcher, DynamicFetcher

# Level 1: Fast HTTP
p = Fetcher.fetch('https://api.example.com')

# Level 2: JS rendering
p = DynamicFetcher.fetch('https://example.com', headless=True)

# Level 3: Anti-bot bypass (Cloudflare, Turnstile)
p = StealthyFetcher.fetch('https://example.com', headless=True)

# Level 4: Adaptive (learns + auto-relocates)
StealthyFetcher.adaptive = True
p = StealthyFetcher.fetch('https://example.com', adaptive=True)
```

### MCP Server — 6 Tools
- `fetch()` — Simple GET
- `stealthy_fetch()` — Anti-bot
- `dynamic_fetch()` — JS rendering
- `bulk_get()` — Parallel requests
- `spider()` — Full async crawler
- `get_similar()` — Find similar elements after changes

### What We Build

#### 1. NOVA Scraper
```python
# StealthyFetcher + bulk_get across X/Reddit/TikTok
# CSS pre-selector → ~80% token reduction
urls = [x_url, reddit_url, tiktok_url]
results = StealthyFetcher.bulk_get(urls)
```

#### 2. SENTINEL Enrichment Spider
```python
class SentinelSpider(Spider):
    name = "sentinel"
    start_urls = []  # Filled by PumpPortal trigger
    
    async def parse(self, response):
        # Pump.fun, DexScreener, Raydium in parallel
        # Returns enriched signal with name, supply, holders, socials
```

#### 3. MCP for Yoruichi
```python
# Natural language scraping
result = await mcp.stealthy_fetch(url, css_selector)
```

---

## 🌍 WORLD MONITOR — Implementation

### Finance Variant
```bash
VITE_VARIANT=finance
```

### Pre-built RSS Feeds (Free)
- Markets: Yahoo Finance, Bloomberg
- Crypto: CoinDesk, Cointelegraph
- Forex: XE
- Bonds: Treasury.gov
- Central Banks: Fed, ECB, BOJ
- Commodities: EIA
- Earnings: SEC EDGAR

### AI Summarization Pipeline
```
Ollama (local) → Groq (14.4k/day free) → OpenRouter → Browser T5
```

### Dedup Strategy
- Jaccard similarity > 0.6 = same story
- Redis 24h cache per story

### What We Steal

#### SENTINEL Signal Clustering
```python
# Cluster by narrative: AI/gov/meme/DeFi
# Convergence = multiple signal types on same token = HIGH alert
clusters = group_by_narrative(signals)
convergence_score = len(clusters[token])
```

#### LiQUiD SOUND Finance Monitor
1. [ ] Rename header + branding
2. [ ] SENTINEL live feed panel (uai:events:token_signal)
3. [ ] CoinGecko integration (already have)
4. [ ] Fear & Greed panel (no auth)
5. [ ] Polymarket → AXIOM sentiment

---

## Free API Keys Needed

| Service | Use | Tier |
|---------|-----|------|
| Groq | AI summarization | 14.4k/day free |
| FRED | Macro data | Free |
| Finnhub | Stock quotes | Free |
| Upstash Redis | Cache | Free tier |
| ACLED | Geopolitical | Researcher free |

**Already have:**
- ✅ CoinGecko
- ✅ Polymarket
- ✅ Yahoo Finance RSS

---

## Action Items

### Now
- [ ] Get Groq API key
- [ ] Get Upstash Redis
- [ ] Get FRED API key

### Soon
- [ ] NOVA scraper with Scrapling
- [ ] SENTINEL enrichment spider
- [ ] Finance Monitor fork

### Later
- [ ] MCP server for natural language scraping
- [ ] Signal clustering for AXIOM
