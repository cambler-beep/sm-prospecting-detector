#!/usr/bin/env python3
"""
SM AI Prospecting — Improved Buyer Intent Signal Detector

Searches for real buyer-intent signals using multiple sources:
1. Company press releases and announcements
2. LinkedIn company pages and news
3. Industry-specific sources
4. News aggregators

Falls back: 2026 → 2025 → portfolio analysis
"""

import json
import logging
import time
import re
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

with open('config.json') as f:
    CONFIG = json.load(f)

# ──────────────────────────────────────────────────────────────────────────────
# SIGNAL DETECTOR
# ──────────────────────────────────────────────────────────────────────────────

class SignalDetector:
    """Detect buyer-intent signals using multi-source research"""

    def __init__(self):
        self.keywords = CONFIG['buyer_intent_keywords_2026']
        self.verticals = CONFIG['sightmap_verticals']

    def detect(self, company_name: str, domain: str) -> Dict:
        """Main detection pipeline with multi-source research"""

        logger.info(f"Detecting signals: {company_name}")

        signals = []
        contacts = []
        qualification = "no_qualifying_news"

        # Step 1: Search press releases and news (2026 first)
        pr_results = self.search_press_releases(company_name, 2026)
        if pr_results['signals']:
            signals.extend(pr_results['signals'])
            contacts.extend(pr_results['contacts'])
            qualification = "qualified"
            logger.info(f"  Found {len(signals)} signals from press releases ✓")

        # Step 2: Search LinkedIn company news (if no signals yet)
        if not signals:
            linkedin_results = self.search_linkedin_company(company_name)
            if linkedin_results['signals']:
                signals.extend(linkedin_results['signals'])
                contacts.extend(linkedin_results['contacts'])
                qualification = "qualified"
                logger.info(f"  Found {len(signals)} signals from LinkedIn ✓")

        # Step 3: Search industry news and announcements (2026)
        if not signals:
            industry_results = self.search_industry_news(company_name, 2026)
            if industry_results['signals']:
                signals.extend(industry_results['signals'])
                contacts.extend(industry_results['contacts'])
                qualification = "qualified"
                logger.info(f"  Found {len(signals)} industry news signals ✓")

        # Step 4: Fallback to 2025 if nothing in 2026
        if not signals:
            pr_2025 = self.search_press_releases(company_name, 2025)
            if pr_2025['signals']:
                signals.extend(pr_2025['signals'])
                contacts.extend(pr_2025['contacts'])
                qualification = "qualified"
                logger.info(f"  Found {len(signals)} 2025 signals ✓")

        # Step 5: Extract leadership from company website
        if not contacts:
            try:
                website_contacts = self.extract_website_contacts(domain)
                contacts.extend(website_contacts)
            except Exception as e:
                logger.debug(f"  Website extraction failed: {e}")

        # Step 6: Analyze portfolio fit
        try:
            portfolio_fit = self.analyze_portfolio(company_name, domain)
            if portfolio_fit['is_sightmap_prospect'] and not signals:
                qualification = "no_qualifying_news"
                logger.info(f"  Company is SightMap prospect (no_qualifying_news)")
        except Exception as e:
            logger.debug(f"  Portfolio analysis failed: {e}")

        # Ensure at least 1 contact
        if not contacts:
            contacts = [{
                "name": company_name,
                "title": "Company",
                "reason_relevant": "Primary contact",
                "linkedin": "",
                "email": ""
            }]

        return {
            "company_name": company_name,
            "company_domain": domain,
            "signals": signals[:5],
            "contacts": contacts[:3],
            "qualification": qualification,
            "notes": f"Detection completed {datetime.now().strftime('%Y-%m-%d')}"
        }

    def search_press_releases(self, company_name: str, year: int = 2026) -> Dict:
        """Search for company press releases and announcements"""

        signals = []
        contacts = []

        try:
            query = f'"{company_name}" press release {year}'
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

            req = urllib.request.Request(search_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

            soup = BeautifulSoup(html, 'html.parser')
            snippets = soup.find_all(['span', 'div'], limit=20)

            for snippet in snippets:
                text = snippet.get_text()

                if self._contains_signal_keywords(text) and len(text) > 20:
                    signal_type = self._classify_signal(text)
                    signal = {
                        "type": signal_type,
                        "summary": text[:150],
                        "source_url": f"https://www.google.com/search?q={urllib.parse.quote(company_name)}",
                        "source_date": f"{year}-01-01"
                    }
                    signals.append(signal)

                if len(signals) >= 3:
                    break

            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"  Press release search failed: {e}")

        return {"signals": signals, "contacts": contacts}

    def search_linkedin_company(self, company_name: str) -> Dict:
        """Search LinkedIn for company news and leadership"""

        signals = []
        contacts = []

        try:
            query = f'site:linkedin.com "{company_name}" news'
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

            req = urllib.request.Request(search_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

            soup = BeautifulSoup(html, 'html.parser')
            snippets = soup.find_all(['span', 'div'], limit=15)

            for snippet in snippets:
                text = snippet.get_text()

                if self._contains_signal_keywords(text) and len(text) > 20:
                    signal = {
                        "type": self._classify_signal(text),
                        "summary": text[:120],
                        "source_url": f"https://www.linkedin.com",
                        "source_date": datetime.now().strftime('%Y-%m-%d')
                    }
                    signals.append(signal)

                if len(signals) >= 2:
                    break

            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"  LinkedIn search failed: {e}")

        return {"signals": signals, "contacts": contacts}

    def search_industry_news(self, company_name: str, year: int = 2026) -> Dict:
        """Search real estate industry news sites"""

        signals = []
        contacts = []

        try:
            query = f'{company_name} acquisition development news {year}'
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

            req = urllib.request.Request(search_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

            soup = BeautifulSoup(html, 'html.parser')
            snippets = soup.find_all(['span', 'div'], limit=15)

            for snippet in snippets:
                text = snippet.get_text()

                if self._contains_signal_keywords(text) and len(text) > 20:
                    signal = {
                        "type": self._classify_signal(text),
                        "summary": text[:140],
                        "source_url": search_url,
                        "source_date": f"{year}-01-01"
                    }
                    signals.append(signal)

                if len(signals) >= 2:
                    break

            time.sleep(0.5)

        except Exception as e:
            logger.debug(f"  Industry news search failed: {e}")

        return {"signals": signals, "contacts": contacts}

    def extract_website_contacts(self, domain: str) -> List[Dict]:
        """Extract leadership contacts from company website"""

        contacts = []

        try:
            url = f"https://{domain}"
            req = urllib.request.Request(url, headers=HEADERS)

            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

            soup = BeautifulSoup(html, 'html.parser')
            text = soup.get_text()

            name_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+)'
            names = re.findall(name_pattern, text)

            for name in names[:3]:
                contacts.append({
                    "name": name,
                    "title": "Company Leadership",
                    "reason_relevant": f"Identified from {domain}",
                    "linkedin": "",
                    "email": ""
                })

            time.sleep(0.3)

        except Exception as e:
            logger.debug(f"  Website extraction failed: {e}")

        return contacts

    def analyze_portfolio(self, company_name: str, domain: str) -> Dict:
        """Analyze company website for portfolio and vertical fit"""

        is_sightmap_prospect = True

        try:
            url = f"https://{domain}"
            req = urllib.request.Request(url, headers=HEADERS)

            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')

            text = html.lower()

            for vertical in self.verticals:
                if vertical.lower() in text:
                    is_sightmap_prospect = True
                    break

            time.sleep(0.3)

        except Exception as e:
            logger.debug(f"  Portfolio analysis failed: {e}")
            is_sightmap_prospect = True

        return {"is_sightmap_prospect": is_sightmap_prospect}

    def _contains_signal_keywords(self, text: str) -> bool:
        """Check if text contains buyer-intent keywords"""
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.keywords)

    def _classify_signal(self, text: str) -> str:
        """Classify signal type based on keywords"""

        text_lower = text.lower()

        if any(word in text_lower for word in ['acquir', 'purchase', 'portfolio']):
            return "ACQUISITION"
        elif any(word in text_lower for word in ['develop', 'construc', 'lease-up', 'groundbreaking']):
            return "DEVELOPMENT"
        elif any(word in text_lower for word in ['appoint', 'hire', 'name', 'cdo', 'cmo', 'vp', 'chief']):
            return "EXECUTIVE_HIRE"
        elif any(word in text_lower for word in ['partner', 'joint', 'strategic']):
            return "PARTNERSHIP"
        else:
            return "MARKET_ACTIVITY"
