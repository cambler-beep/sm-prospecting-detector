#!/usr/bin/env python3
"""
SM AI Prospecting — Buyer Intent Signal Detector

Searches for recent buyer-intent signals (acquisitions, developments, leadership)
Falls back: 2026 → 2025 → portfolio analysis
Completely free (no APIs, no credentials needed)
"""

import json
import logging
import time
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────────────────────────
# SETUP
# ──────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

# Load config
with open('config.json') as f:
    CONFIG = json.load(f)

# ──────────────────────────────────────────────────────────────────────────────
# SIGNAL DETECTOR
# ──────────────────────────────────────────────────────────────────────────────

class SignalDetector:
    """Detect buyer-intent signals for real estate companies"""

    def __init__(self):
        self.keywords = CONFIG['buyer_intent_keywords_2026']
        self.verticals = CONFIG['sightmap_verticals']

    def detect(self, company_name: str, domain: str) -> Dict:
        """Main detection pipeline: 2026 news → 2025 news → portfolio analysis"""

        logger.info(f"Detecting signals: {company_name}")

        signals = []
        contacts = []
        qualification = "no_qualifying_news"

        # Step 1: Search for 2026 signals
        news_2026 = self.search_news(company_name, year=2026)
        if news_2026['signals']:
            signals.extend(news_2026['signals'])
            contacts.extend(news_2026['contacts'])
            qualification = "qualified"
            logger.info(f"  Found {len(signals)} 2026 signals ✓")

        # Step 2: If no 2026 signals, search 2025
        if not signals:
            news_2025 = self.search_news(company_name, year=2025)
            if news_2025['signals']:
                signals.extend(news_2025['signals'])
                contacts.extend(news_2025['contacts'])
                qualification = "qualified"
                logger.info(f"  Found {len(signals)} 2025 signals ✓")

        # Step 3: Search for portfolio/company info (fallback if no recent news)
        try:
            portfolio_data = self.analyze_portfolio(company_name, domain)
            if portfolio_data['is_sightmap_prospect']:
                if not signals:
                    # No recent news, but company is in a SightMap vertical
                    qualification = "no_qualifying_news"
                    logger.info(f"  Company is SightMap prospect (no_qualifying_news)")

                # Extract contacts from company website if not already found
                if not contacts and portfolio_data.get('contacts'):
                    contacts.extend(portfolio_data['contacts'])
        except Exception as e:
            logger.debug(f"  Portfolio analysis failed: {e}")

        # Ensure at least 1 contact
        if not contacts:
            contacts = [{
                "name": company_name,
                "title": "Company",
                "reason_relevant": "Primary company contact",
                "linkedin": "",
                "email": ""
            }]

        return {
            "company_name": company_name,
            "company_domain": domain,
            "signals": signals[:5],  # Max 5 signals per company
            "contacts": contacts[:3],  # Max 3 contacts per company
            "qualification": qualification,
            "notes": f"Detection completed {datetime.now().strftime('%Y-%m-%d')}"
        }

    def search_news(self, company_name: str, year: int = 2026) -> Dict:
        """Search Google for news about the company in a specific year"""

        signals = []
        contacts = []

        try:
            # Build search query
            query = f"{company_name} news {year}"
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

            # Fetch search results
            req = urllib.request.Request(search_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')

            soup = BeautifulSoup(html, 'html.parser')

            # Extract search results
            results = soup.find_all('a', limit=10)

            for result in results:
                text = result.get_text()
                href = result.get('href', '')

                # Check for buyer-intent keywords
                if any(kw.lower() in text.lower() for kw in self.keywords):
                    signal = {
                        "type": self._classify_signal(text),
                        "summary": text[:150],
                        "source_url": href if href.startswith('http') else '',
                        "source_date": f"{year}-01-01"  # Approximate
                    }
                    signals.append(signal)

                if len(signals) >= 3:  # Stop after 3 signals
                    break

            time.sleep(0.5)  # Be respectful to servers

        except Exception as e:
            logger.debug(f"  News search failed for {year}: {e}")

        return {"signals": signals, "contacts": contacts}

    def analyze_portfolio(self, company_name: str, domain: str) -> Dict:
        """Analyze company website for portfolio composition and vertical fit"""

        is_sightmap_prospect = False
        contacts = []

        try:
            url = f"https://{domain}"
            req = urllib.request.Request(url, headers=HEADERS)

            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')

            text = html.lower()

            # Check if company operates in SightMap verticals
            for vertical in self.verticals:
                if vertical.lower() in text:
                    is_sightmap_prospect = True
                    break

            # Extract leadership names from website
            soup = BeautifulSoup(html, 'html.parser')
            names = re.findall(r'([A-Z][a-z]+\s+[A-Z][a-z]+)', text)

            for name in names[:2]:
                contacts.append({
                    "name": name,
                    "title": "Company Leadership",
                    "reason_relevant": "Identified from company website",
                    "linkedin": "",
                    "email": ""
                })

            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"  Portfolio analysis failed: {e}")
            is_sightmap_prospect = True  # Default to true if we can't verify

        return {
            "is_sightmap_prospect": is_sightmap_prospect,
            "contacts": contacts
        }

    def _classify_signal(self, text: str) -> str:
        """Classify signal type based on keywords"""

        text_lower = text.lower()

        if any(word in text_lower for word in ['acquir', 'purchase', 'portfolio']):
            return "ACQUISITION"
        elif any(word in text_lower for word in ['develop', 'construc', 'lease-up', 'new property']):
            return "DEVELOPMENT"
        elif any(word in text_lower for word in ['appoint', 'hire', 'name', 'cdo', 'cmo', 'vp', 'leadership']):
            return "EXECUTIVE_HIRE"
        elif any(word in text_lower for word in ['partner', 'joint', 'strategic']):
            return "PARTNERSHIP"
        else:
            return "MARKET_ACTIVITY"


# ──────────────────────────────────────────────────────────────────────────────
# USAGE
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    detector = SignalDetector()

    # Test with sample companies
    test_companies = [
        ("Lennar Corporation", "lennar.com"),
        ("Equity Residential", "equityapartments.com"),
        ("AvalonBay Communities", "avalonbay.com"),
    ]

    for name, domain in test_companies:
        result = detector.detect(name, domain)
        print(json.dumps(result, indent=2))
        print("---\n")
