"""
scrape_and_push.py
------------------
GitHub Actions par chalega. Koi Flask server nahi — sirf:
  1. pharmabharat.com + pharmarecruiter.in se scrape karo
  2. jobs.db update karo
  3. jobs_seed.json export karo
  4. PythonAnywhere ke /api/sync endpoint ko call karo taaki wo
     updated jobs.db GitHub raw URL se apne aap pull kar le

Environment Variables (GitHub Secrets se inject hote hain):
  PA_SYNC_TOKEN  : /api/sync route ka secret token
  PA_APP_URL     : e.g. https://yourusername.pythonanywhere.com
"""

import os
import sys
import time
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("scrape_and_push")

# ── Imports ───────────────────────────────────────────────────────────────────
try:
    import db
    import scraper
except ImportError as e:
    log.error(f"Import failed: {e}. Make sure db.py and scraper.py exist.")
    sys.exit(1)

# ── Init DB ───────────────────────────────────────────────────────────────────
db.init_db()

# ── Run Scrape ────────────────────────────────────────────────────────────────
log.info("=== Starting scrape run ===")
start = time.time()

try:
    new_slugs = scraper.scrape_all_recent(pages=1, deep=True)
    log.info(f"Scrape done — {len(new_slugs)} new jobs found in {time.time()-start:.1f}s")
except Exception as e:
    log.error(f"Scrape failed: {e}")
    new_slugs = []

# ── Telegram / WhatsApp feed (best-effort) ────────────────────────────────────
try:
    import telegram_scraper
    tg_slugs = telegram_scraper.scrape_telegram_channels()
    if tg_slugs:
        new_slugs.extend(tg_slugs)
        log.info(f"Telegram: {len(tg_slugs)} additional jobs")
except Exception as e:
    log.warning(f"Telegram scrape skipped: {e}")

# ── Export seed JSON ──────────────────────────────────────────────────────────
try:
    db.export_seed_json()
    log.info("jobs_seed.json exported successfully")
except Exception as e:
    log.warning(f"Seed JSON export failed: {e}")

# ── Notify PythonAnywhere to pull updated DB ──────────────────────────────────
pa_url   = os.environ.get("PA_APP_URL", "").rstrip("/")
pa_token = os.environ.get("PA_SYNC_TOKEN", "")

if pa_url and pa_token:
    sync_endpoint = f"{pa_url}/api/sync?token={pa_token}"
    log.info(f"Calling PA sync endpoint: {pa_url}/api/sync ...")
    try:
        resp = requests.get(sync_endpoint, timeout=60)
        if resp.ok:
            log.info(f"PA sync success: {resp.json()}")
        else:
            log.warning(f"PA sync returned HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        log.error(f"PA sync call failed: {e}")
else:
    log.warning("PA_APP_URL or PA_SYNC_TOKEN not set — skipping PA sync notification")

log.info(f"=== Done. Total new jobs this run: {len(new_slugs)} ===")
