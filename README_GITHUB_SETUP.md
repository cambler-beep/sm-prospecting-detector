# SM AI Prospecting Detector — GitHub Setup

Buyer-intent signal detector for Engrain prospecting. Runs Monday 4am, processes 300 companies (50 per AE × 6 AEs), posts results to Google Sheet.

**Status:** Ready to test today, deploy Monday 4am

---

## Quick Start

### 1. Upload Files to GitHub

Clone your repo:
```bash
git clone https://github.com/cambler-beep/sm-prospecting-detector.git
cd sm-prospecting-detector
```

Copy these files from your local outputs folder:
```
sm-prospecting-detector/
├── config.json
├── signal_detector.py
├── run_detector.py
├── requirements.txt
├── README.md
└── .github/
    └── workflows/
        └── schedule.yml
```

**GitHub has a simple web uploader:**
1. Go to your repo: https://github.com/cambler-beep/sm-prospecting-detector
2. Click "Add file" → "Upload files"
3. Drag the files above into the upload box
4. Click "Commit changes"

---

## Test Today (Before Monday Deployment)

### Install dependencies
```bash
pip install -r requirements.txt
```

### Test with one AE (5 companies to start)
```bash
python3 run_detector.py --ae Izzy --count 5
```

This will:
1. Fetch 5 pending companies for Izzy
2. Search for 2026 signals
3. Fall back to 2025 if needed
4. Analyze company portfolio
5. Extract contacts
6. POST results to your Google Sheet

**Output:**
- `output/batches/batch_*.json` — Raw detection results
- `output/logs/detector_*.log` — Detailed execution log
- Rows added to sheet's "Company News" and "News Contacts" tabs

### Test full batch (50 companies)
```bash
python3 run_detector.py --ae Mitch --count 50
```

Monitor the log:
```bash
tail -f output/logs/detector_*.log
```

---

## How It Works

### Detection Pipeline

**For each company:**

1. **Search 2026 news** — Look for recent acquisitions, developments, executive hires
   - Keywords: "acquires", "development", "appoints", "cdo", "construction", etc.
   - If found → `qualification: "qualified"`

2. **Fallback to 2025** — If no 2026 signals, search 2025 news
   - Same signal types
   - If found → `qualification: "qualified"`

3. **Analyze portfolio** — If no recent news, check company vertical fit
   - Is the company in a SightMap vertical? (multifamily, senior living, student housing, etc.)
   - If yes → `qualification: "no_qualifying_news"` (still research, but no hot signals)
   - If no → `qualification: "not_qualified"`

**Every company gets output** — No skips. Either signals found or portfolio context provided.

### Signal Types

- **ACQUISITION** — Buys, portfolio growth, consolidation
- **DEVELOPMENT** — New properties, lease-ups, construction
- **EXECUTIVE_HIRE** — C-suite, CDO, CMO, VP Marketing, VP Leasing hires
- **PARTNERSHIP** — Strategic partnerships, joint ventures
- **MARKET_ACTIVITY** — Awards, conferences, strategic moves

### Sequential Processing

Monday 4am workflow runs all 6 AEs sequentially:
1. Izzy (50 companies) — ~5-10 min
2. Mitch (50 companies) — ~5-10 min
3. Kodie (50 companies) — ~5-10 min
4. Ben (50 companies) — ~5-10 min
5. Brian (50 companies) — ~5-10 min
6. Jacob (50 companies) — ~5-10 min

**Total:** ~300 companies, ~30-60 minutes

Sequential processing avoids rate limiting and keeps logs clean.

---

## Configuration

Edit `config.json` to:
- Add/remove AEs from `ae_list`
- Adjust detection keywords in `buyer_intent_keywords_2026`
- Update sheet ID or web app URL if needed

---

## Troubleshooting

### "No pending companies found"
- Check that column E (Batch Status) in the sheet is empty for those rows
- Verify AE name matches exactly (case-sensitive)
- Run `getPending` endpoint directly in your browser to debug

### "POST failed"
- Verify internet connection
- Check `config.json` has correct `web_app.url` and `api_key`
- Check Google Sheet web app is deployed

### "News search returned nothing"
- This is normal — not all companies have recent news
- Script still includes company with `qualification: "no_qualifying_news"`
- Portfolio analysis will determine if they're a SightMap prospect

### "Detection failed for a company"
- Check logs in `output/logs/`
- Script will still include the company with minimal data
- No companies are skipped

---

## Schedule

**Current:** Monday 4am UTC (adjustable via cron expression in `.github/workflows/schedule.yml`)

To change schedule:
1. Edit `.github/workflows/schedule.yml`
2. Change the `cron` value
   - `0 4 * * 1` = Monday 4am UTC
   - `0 2 * * 1` = Monday 2am UTC
   - `0 4 * * 0` = Sunday 4am UTC
3. Commit and push

**Manual trigger:** Go to GitHub Actions tab → Click "Run workflow"

---

## Output Format

### Company News Tab
| Column | Contents |
|--------|----------|
| A | company name |
| B | company domain |
| C | signal type (ACQUISITION, DEVELOPMENT, EXECUTIVE_HIRE, etc.) |
| D | news summary |
| E | why it matters for Engrain |
| F | source link |
| G | source date |
| H | likely project |

### News Contacts Tab
| Column | Contents |
|--------|----------|
| A | Clay Push Status (empty) |
| B | company name |
| C | SightMap AE |
| D | first name |
| E | last name |
| F | full name |
| G | title |
| H | company domain |
| I | public email (if available) |
| J | LinkedIn URL (if available) |
| K | related news links |
| L | why relevant |
| M | email draft (empty) |
| N | Clay note (empty) |
| O | Clay pushed at (empty) |

### Batch Status Updates
Column E in "No Outbound Email Batch" tab updated to "done" after processing.

---

## Cost

**Completely free.** No APIs, no credentials, no subscriptions needed.

- Uses urllib + BeautifulSoup for web scraping
- Google Search via public web interface
- No authentication required

---

## Next Steps

1. **Test today:** `python3 run_detector.py --ae Izzy --count 5`
2. **Review output** in Google Sheet
3. **Verify detection quality** — Are signals accurate? Are contacts relevant?
4. **Deploy Monday:** GitHub Actions will run automatically at 4am

---

## Files

- `config.json` — Configuration (sheet ID, AE list, keywords)
- `signal_detector.py` — Core detection engine
- `run_detector.py` — Orchestrator (fetches pending, runs detection, posts to sheet)
- `requirements.txt` — Python dependencies
- `.github/workflows/schedule.yml` — GitHub Actions workflow (Monday 4am)
- `output/batches/` — Detection results (JSON)
- `output/logs/` — Execution logs

---

## Support

Check logs for detailed error messages:
```bash
tail -50 output/logs/detector_*.log
```

Review payload sent to sheet:
```bash
cat output/batches/batch_*.json
```

---

**Ready to test!**
```bash
python3 run_detector.py --ae Izzy --count 5
```
