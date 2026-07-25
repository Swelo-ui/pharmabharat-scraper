"""
monitor.py -- Yeh script hamesha chalti rehti hai background mein,
har N minute mein DONO sites (PharmaBharat + PharmaRecruiter) ke
naye jobs check karti hai aur mil jaye to Telegram par bhej deti hai.

App band ho ya offline ho — yeh script independently chalti rehti hai
aur notifications aate rehte hain.

Chalane ka tarika:
    python monitor.py

Rokne ke liye Ctrl+C.
Server/laptop pe 24x7 chalana hai:
  - Windows: pythonw monitor.py  (background, no console window)
  - Linux/Mac: nohup python monitor.py &
  - Startup pe chalane ke liye: run_monitor.bat double-click karo
  - Ya Windows Task Scheduler mein add karo (README dekho)
"""

import logging
import time

import scraper
import notifier
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("monitor.log", encoding="utf-8"),
    ]
)
log = logging.getLogger("monitor")

# Smart backoff config
MIN_INTERVAL = 30    # minutes when jobs are being found
MAX_INTERVAL = 60    # minutes when nothing new found for 2+ consecutive syncs
LISTING_PAGES_TO_CHECK = 2

_consecutive_empty = 0  # how many syncs in a row returned 0 new jobs


def job_cycle():
    global _consecutive_empty

    log.info("═══ Checking PharmaBharat + PharmaRecruiter for new jobs... ═══")
    try:
        # Scrape DONO sites ek sath — deduplication automatic hogi
        new_slugs = scraper.scrape_all_recent(pages=LISTING_PAGES_TO_CHECK, deep=True)
        count = len(new_slugs)
        log.info("✓ Found %s new job(s) across both sites.", count)
        db.set_last_sync_time()

        sent = notifier.notify_new_jobs()
        log.info("✓ Sent %s notification(s).", sent)

        # Purge jobs older than 30 days (mark inactive)
        purged = db.purge_expired(days=30)
        if purged:
            log.info("✓ Marked %s old jobs as inactive.", purged)

        if count == 0:
            _consecutive_empty += 1
        else:
            _consecutive_empty = 0

    except Exception:
        log.exception("Error during scrape/notify cycle")


def _next_interval():
    """Return next check interval in minutes based on recent activity."""
    if _consecutive_empty >= 2:
        interval = MAX_INTERVAL
        log.info("No new jobs for %s consecutive syncs — next check in %s min.",
                 _consecutive_empty, interval)
    else:
        interval = MIN_INTERVAL
    return interval


if __name__ == "__main__":
    log.info("="*60)
    log.info(" PharmaBharat + PharmaRecruiter Monitor Started")
    log.info(" Sources: pharmabharat.com + pharmarecruiter.in/freshers-jobs")
    log.info(" Interval: %s-%s min | Pages: %s | Notifications: Telegram",
             MIN_INTERVAL, MAX_INTERVAL, LISTING_PAGES_TO_CHECK)
    log.info("="*60)
    db.init_db()

    while True:
        job_cycle()
        interval = _next_interval()
        log.info("Sleeping %s minutes until next check...", interval)
        time.sleep(interval * 60)
