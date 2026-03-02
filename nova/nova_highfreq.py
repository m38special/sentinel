#!/usr/bin/env python3
"""
NOVA Content Engine - High Frequency Posting
3-5 posts per day for algorithm growth
"""
import os
import random
from datetime import datetime, timedelta

# High-frequency content themes
MORNING_THEMES = [
    "morning abundance affirmation",
    "daily wealth intention",
    "888 morning frequency",
    "abundance activation",
]

MIDDAY_THEMES = [
    "market pulse update",
    "crypto education",
    "defi insight",
    "solana analysis",
]

EVENING_THEMES = [
    "evening gratitude",
    "abundance reflection",
    "wealth mindset reset",
    "tomorrow's vision",
]

TRENDING_CAPTIONS = [
    "Save this ✨",
    "Share the abundance 💫",
    "DM for details 👑",
    "Comment below 👇",
    "Turn this into your lockscreen 🖤",
]

def generate_post(time_of_day: str, account: str) -> dict:
    """Generate single post"""
    
    if account == "@888abundancefrequency":
        if time_of_day == "morning":
            theme = random.choice(MORNING_THEMES)
            content = generate_abundance_morning(theme)
        elif time_of_day == "midday":
            theme = random.choice(MIDDAY_THEMES)
            content = generate_abundance_midday(theme)
        else:  # evening
            theme = random.choice(EVENING_THEMES)
            content = generate_abundance_evening(theme)
        
        hashtags = "#888 #abundance #manifestation #wealth #frequency #spiritual #moneymindset #universe"
    else:
        # @liquidinsights
        if time_of_day == "morning":
            theme = random.choice(MORNING_THEMES)
            content = generate_market_morning(theme)
        elif time_of_day == "midday":
            theme = random.choice(MIDDAY_THEMES)
            content = generate_market_midday(theme)
        else:
            theme = random.choice(EVENING_THEMES)
            content = generate_market_evening(theme)
        
        hashtags = "#crypto #bitcoin #solana #defi #web3 #trading #investing #market"

    return {
        "time": time_of_day,
        "account": account,
        "theme": theme,
        "content": content,
        "hashtags": hashtags,
        "cta": random.choice(TRENDING_CAPTIONS),
    }

def generate_abundance_morning(theme: str) -> str:
    templates = [
        f"MORNING FREQUENCY | {theme}\n\nThe 888 energy is rising.\n\nToday is the day your abundance activates.\n\nSpeak this into existence:\n\n\"I am open to receiving unlimited wealth.\"\n\n{random.choice(TRENDING_CAPTIONS)}",
        f"WAKE UP TO ABUNDANCE | {theme}\n\nThe universe is already conspiring for you.\n\nYou don't need to chase.\n\nYou need to align.\n\n{random.choice(TRENDING_CAPTIONS)}",
    ]
    return random.choice(templates)

def generate_abundance_midday(theme: str) -> str:
    templates = [
        f"MIDDAY ABUNDANCE CHECK | {theme}\n\nHow is your frequency right now?\n\nAre you in flow or friction?\n\nAlign and receive.\n\n{random.choice(TRENDING_CAPTIONS)}",
        f"ABUNDANCE REALITY CHECK | {theme}\n\nThe money is coming.\n\nAre you ready to receive it?\n\n{random.choice(TRENDING_CAPTIONS)}",
    ]
    return random.choice(templates)

def generate_abundance_evening(theme: str) -> str:
    templates = [
        f"NIGHTLY REFLECTION | {theme}\n\nWhat abundance did you create today?\n\nWhat will you create tomorrow?\n\nThe 888 portal never closes.\n\n{random.choice(TRENDING_CAPTIONS)}",
        f"BEFORE YOU SLEEP | {theme}\n\nSpeak this:\n\n\"Tomorrow I receive.\"\n\nThe universe is listening.\n\n{random.choice(TRENDING_CAPTIONS)}",
    ]
    return random.choice(templates)

def generate_market_morning(theme: str) -> str:
    templates = [
        f"MARKET OPEN | {theme}\n\nHere's what to watch today:\n\n• BTC holding support\n• SOL looking strong\n• DeFi TVL increasing\n\nSave for later.\n\n{random.choice(TRENDING_CAPTIONS)}",
        f"MORNING PULSE | {theme}\n\nMarkets are shifting.\n\nHere's your quick brief:\n\nThe smart money is positioning.\n\n{random.choice(TRENDING_CAPTIONS)}",
    ]
    return random.choice(templates)

def generate_market_midday(theme: str) -> str:
    templates = [
        f"MIDDAY MARKET CHECK | {theme}\n\nQuick update:\n\nMarkets are consolidating.\n\nThis is where opportunities are built.\n\n{random.choice(TRENDING_CAPTIONS)}",
        f"MARKET MOMENTUM | {theme}\n\nThe trend is your friend.\n\nBut don't forget risk management.\n\n{random.choice(TRENDING_CAPTIONS)}",
    ]
    return random.choice(templates)

def generate_market_evening(theme: str) -> str:
    templates = [
        f"MARKET CLOSE | {theme}\n\nToday's lesson:\n\nThe dip is not the end.\n\nIt's the opportunity.\n\n{random.choice(TRENDING_CAPTIONS)}",
        f"NIGHTLY ANALYSIS | {theme}\n\nHere's what happened:\n\nMarkets move in cycles.\n\nWe're in the building phase.\n\n{random.choice(TRENDING_CAPTIONS)}",
    ]
    return random.choice(templates)

def generate_daily_posts(account: str, count: int = 4) -> list:
    """Generate multiple posts for the day"""
    times = ["morning", "midday", "evening"]
    if count == 3:
        times = ["morning", "midday", "evening"]
    elif count == 4:
        times = ["morning", "midday", "midday", "evening"]
    else:  # 5
        times = ["morning", "midday", "midday", "evening", "evening"]
    
    posts = []
    for t in times[:count]:
        posts.append(generate_post(t, account))
    
    return posts

if __name__ == "__main__":
    print("=" * 50)
    print("NOVA HIGH-FREQUENCY CONTENT")
    print("3-5 posts per day")
    print("=" * 50)
    
    # Generate for both accounts
    for account in ["@888abundancefrequency", "@liquidinsights"]:
        print(f"\n=== {account} ===")
        posts = generate_daily_posts(account, random.choice([3, 4, 5]))
        for i, p in enumerate(posts, 1):
            print(f"\nPost {i} ({p['time'].upper()}):")
            print(p['content'][:150] + "...")
