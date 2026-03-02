#!/usr/bin/env python3
"""
SENTINEL Multi-Exchange Scanner (v2.1)
Uses ccxt for unified access to 100+ exchanges
"""

import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional

import ccxt
from dotenv import load_dotenv

load_dotenv()


class MultiExchangeScanner:
    """Scan multiple DEXs and CEXs for new tokens"""
    
    SUPPORTED_EXCHANGES = {
        'pumpfun': {
            'class': ccxt.pumpfun,
            'type': 'DEX',
            'tokens': []  # New tokens found
        },
        'binance': {
            'class': ccxt.binance,
            'type': 'CEX',
            'tokens': []
        },
        'raydium': {
            'class': ccxt.raydium,
            'type': 'DEX',
            'tokens': []
        },
        'orca': {
            'class': ccxt.orca,
            'type': 'DEX',
            'tokens': []
        },
        'jupiter': {
            'class': ccxt.jupiter,
            'type': 'DEX',
            'tokens': []
        }
    }
    
    def __init__(self):
        self.exchanges: Dict[str, ccxt.Exchange] = {}
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize available exchanges"""
        for name, config in self.SUPPORTED_EXCHANGES.items():
            try:
                exchange_class = config['class']
                # Use demo/testnet where available
                exchange = exchange_class({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
                })
                self.exchanges[name] = exchange
                print(f"✓ Initialized {name} ({config['type']})")
            except Exception as e:
                print(f"✗ Failed to init {name}: {e}")
    
    async def scan_pumpfun(self) -> List[Dict]:
        """Scan Pump.fun for new tokens"""
        tokens = []
        try:
            exchange = self.exchanges.get('pumpfun')
            if not exchange:
                # Fallback: use PumpPortal WebSocket directly
                return await self._scan_pumpportal_fallback()
            
            # Fetch recent trades
            # Note: pumpfun-specific methods vary
            markets = await exchange.fetch_markets()
            
            for market in markets[-50:]:  # Last 50 markets
                tokens.append({
                    'symbol': market['symbol'],
                    'address': market.get('id'),
                    'dex': 'pumpfun',
                    'timestamp': datetime.utcnow().isoformat(),
                    'volume_24h': market.get('quoteVolume', 0),
                    'liquidity': market.get('liquidity', 0)
                })
                
        except Exception as e:
            print(f"Pump.fun scan error: {e}")
        
        return tokens
    
    async def _scan_pumpportal_fallback(self) -> List[Dict]:
        """Fallback to PumpPortal WebSocket for pump.fun"""
        # This uses the existing sentinel_ph2.py logic
        # Placeholder for integration
        return []
    
    async def scan_cex_listings(self, exchange_name: str = 'binance') -> List[Dict]:
        """Scan CEX for new listings"""
        tokens = []
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                return tokens
            
            # Fetch recent tickers
            tickers = await exchange.fetch_tickers()
            
            # Filter for recently added (by checking first seen)
            for symbol, ticker in tickers.items():
                created = ticker.get('created')
                if created:
                    hours_old = (datetime.utcnow() - created).total_seconds() / 3600
                    if hours_old < 24:  # Last 24 hours
                        tokens.append({
                            'symbol': symbol,
                            'exchange': exchange_name,
                            'price': ticker.get('last'),
                            'volume_24h': ticker.get('baseVolume'),
                            'created': created.isoformat()
                        })
                        
        except Exception as e:
            print(f"{exchange_name} scan error: {e}")
        
        return tokens
    
    async def scan_dex_new_pairs(self, dex_name: str) -> List[Dict]:
        """Scan DEXs for new pairs (Raydium, Orca, Jupiter)"""
        tokens = []
        try:
            exchange = self.exchanges.get(dex_name)
            if not exchange:
                return tokens
            
            # Fetch markets and find recent ones
            markets = await exchange.fetch_markets()
            
            # Sort by creation time if available
            recent = markets[-20:] if len(markets) > 20 else markets
            
            for market in recent:
                tokens.append({
                    'symbol': market['symbol'],
                    'base': market['base'],
                    'quote': market['quote'],
                    'dex': dex_name,
                    'timestamp': datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            print(f"{dex_name} scan error: {e}")
        
        return tokens
    
    async def full_scan(self) -> Dict[str, List]:
        """Run full multi-chain scan"""
        results = {
            'pumpfun': await self.scan_pumpfun(),
            'cex_listings': await self.scan_cex_listings('binance'),
            'raydium': await self.scan_dex_new_pairs('raydium')
        }
        return results


async def main():
    scanner = MultiExchangeScanner()
    print("\n=== SENTINEL Multi-Exchange Scanner v2.1 ===\n")
    
    results = await scanner.full_scan()
    
    for source, tokens in results.items():
        print(f"\n{source.upper()}: {len(tokens)} tokens")
        for token in tokens[:5]:  # Show first 5
            print(f"  - {token.get('symbol', token.get('address', 'N/A'))}")


if __name__ == '__main__':
    asyncio.run(main())
