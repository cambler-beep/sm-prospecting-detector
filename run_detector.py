#!/usr/bin/env python3
"""
SM AI Prospecting — Detector Orchestrator

Fetches pending companies, runs signal detection, posts to Google Sheet
Usage: python3 run_detector.py --ae Izzy --count 50
"""

import json
import argparse
import sys
import logging
import time
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.error
from signal_detector import SignalDetector

# ──────────────────────────────────────────────────────────────────────────────
# SETUP
# ──────────────────────────────────────────────────────────────────────────────

CONFIG_PATH = Path('config.json')
with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

# Setup logging
LOG_DIR = Path(CONFIG['output_dir']) / 'logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"detector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(CONFIG['output_dir']) / 'batches'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# MAIN WORKFLOW
# ──────────────────────────────────────────────────────────────────────────────

def fetch_pending_companies(ae_name: str) -> list:
    """Fetch pending companies from sheet via getPending endpoint"""

    endpoint = CONFIG['getPending_endpoint'].replace('{AE_NAME}', ae_name)
    logger.info(f"Fetching pending companies for AE: {ae_name}")

    try:
        req = urllib.request.Request(endpoint)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            pending = data.get('pending', [])

            logger.info(f"Found {len(pending)} pending companies")
            for company in pending[:3]:
                logger.info(f"  Row {company['row']}: {company['company']}")
            if len(pending) > 3:
                logger.info(f"  ... and {len(pending) - 3} more")

            return pending

    except urllib.error.URLError as e:
        logger.error(f"Failed to fetch pending companies: {e}")
        raise


def run_detection(companies: list, ae_name: str) -> list:
    """Run signal detection on all companies"""

    logger.info(f"\nRunning signal detection on {len(companies)} companies...")

    detector = SignalDetector()
    results = []

    for i, company in enumerate(companies, 1):
        logger.info(f"[{i}/{len(companies)}] {company['company']}")

        try:
            result = detector.detect(company['company'], company['domain'])
            results.append(result)
            time.sleep(0.5)  # Be respectful to servers

        except Exception as e:
            logger.error(f"  Detection failed: {e}")
            # Still include company with fallback data
            results.append({
                "company_name": company['company'],
                "company_domain": company['domain'],
                "signals": [],
                "contacts": [{
                    "name": company['company'],
                    "title": "Company",
                    "reason_relevant": "Detection failed",
                    "linkedin": "",
                    "email": ""
                }],
                "qualification": "no_qualifying_news",
                "notes": f"Detection failed: {str(e)}"
            })

    logger.info(f"\nDetection complete: {len(results)} companies processed")
    return results


def consolidate_results(detection_results: list, ae_name: str, batch_id: str) -> dict:
    """Convert detection results to Google Sheet payload format"""

    logger.info("\nConsolidating results into payload format...")

    company_news = []
    news_contacts = []
    batch_updates = []

    for result in detection_results:
        company_name = result['company_name']
        company_domain = result['company_domain']
        qualification = result['qualification']

        # Company News rows
        if result['signals']:
            for signal in result['signals']:
                company_news.append({
                    "company_name": company_name,
                    "company_domain": company_domain,
                    "signal_type": signal.get('type', 'OTHER'),
                    "news_summary": signal.get('summary', ''),
                    "why_it_matters": f"Buyer intent signal for SightMap expansion opportunities",
                    "source_link": signal.get('source_url', ''),
                    "source_date": signal.get('source_date', ''),
                    "likely_project": ""
                })
        else:
            # No signals found - add context row
            company_news.append({
                "company_name": company_name,
                "company_domain": company_domain,
                "signal_type": "NO_RECENT_SIGNALS",
                "news_summary": result.get('notes', 'No recent buyer-intent signals found'),
                "why_it_matters": "Company operates in SightMap vertical - monitor for future signals",
                "source_link": "",
                "source_date": datetime.now().strftime('%Y-%m-%d'),
                "likely_project": ""
            })

        # News Contacts rows
        for contact in result['contacts']:
            name_parts = contact.get('name', '').split()
            first_name = name_parts[0] if len(name_parts) > 0 else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

            news_contacts.append({
                "clay_push_status": "",
                "company_name": company_name,
                "sightmap_ae": ae_name,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": contact.get('name', ''),
                "title": contact.get('title', ''),
                "company_domain": company_domain,
                "public_email": contact.get('email', ''),
                "linkedin_url": contact.get('linkedin', ''),
                "related_news_links": "",
                "why_relevant": contact.get('reason_relevant', ''),
                "email_draft": "",
                "clay_note": "",
                "clay_pushed_at": ""
            })

        # Batch updates
        batch_updates.append({
            "domain": company_domain,
            "batch_status": "done",
            "processed_at": datetime.now().isoformat(),
            "batch_id": batch_id,
            "new_cycle_id": "",
            "news_qualification": qualification
        })

    payload = {
        "apiKey": CONFIG["web_app"]["api_key"],
        "sheetId": CONFIG["sheet_id"],
        "companyNews": company_news,
        "newsContacts": news_contacts,
        "batchUpdates": batch_updates
    }

    logger.info(f"  Company News: {len(company_news)} rows")
    logger.info(f"  News Contacts: {len(news_contacts)} rows")
    logger.info(f"  Batch Updates: {len(batch_updates)} rows")

    return payload


def post_payload(payload: dict) -> bool:
    """POST payload to Google Sheet web app"""

    logger.info("\nPOSTing to Google Sheet...")

    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode('utf-8')

    try:
        request = urllib.request.Request(
            CONFIG['web_app']['url'],
            data=payload_bytes,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            response_text = response.read().decode('utf-8')
            logger.info(f"✅ POST successful! (Status: {response.status})")

            if response_text and response_text.startswith('{'):
                try:
                    response_data = json.loads(response_text)
                    logger.info(f"   Response: {response_data}")
                except:
                    logger.info(f"   Response received (non-JSON)")

            return True

    except urllib.error.URLError as e:
        logger.error(f"❌ Failed to POST: {e}")
        raise


def save_payload(payload: dict, batch_id: str) -> None:
    """Save payload to disk for debugging"""

    output_file = OUTPUT_DIR / f"{batch_id}_payload.json"
    with open(output_file, 'w') as f:
        json.dump(payload, f, indent=2)

    logger.info(f"✅ Payload saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="SM AI Prospecting — Buyer Intent Signal Detector"
    )
    parser.add_argument("--ae", required=True, help="AE first name (Izzy, Mitch, etc.)")
    parser.add_argument("--count", type=int, default=50, help="Number of companies to process")
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("SM AI PROSPECTING — BUYER INTENT SIGNAL DETECTOR")
    logger.info("=" * 80)
    logger.info(f"AE: {args.ae}")
    logger.info(f"Target count: {args.count}")

    try:
        # Step 1: Fetch pending companies
        pending = fetch_pending_companies(args.ae)

        if not pending:
            logger.warning("No pending companies found. Exiting.")
            return

        companies = pending[:args.count]
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{args.ae}"

        # Step 2: Run detection
        detection_results = run_detection(companies, args.ae)

        # Step 3: Consolidate
        payload = consolidate_results(detection_results, args.ae, batch_id)

        # Step 4: Save payload
        save_payload(payload, batch_id)

        # Step 5: POST to sheet
        post_payload(payload)

        logger.info("\n" + "=" * 80)
        logger.info("✅ BATCH COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Batch ID: {batch_id}")
        logger.info(f"Companies processed: {len(companies)}")
        logger.info(f"Company News rows: {len(payload['companyNews'])}")
        logger.info(f"News Contacts rows: {len(payload['newsContacts'])}")
        logger.info("Data posted to Google Sheet ✅")

    except Exception as e:
        logger.error(f"\n❌ FATAL ERROR: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
