"""
telegram_scraper.py -- Real-time Telegram Channel Job Scraper & Listener.

Monitors official Telegram channels (t.me/s/Pharma_bharat & t.me/s/pharma_recruiter).
When a new job post link appears in either Telegram channel:
1. Extracts the job post URL.
2. Checks if slug already exists in jobs.db.
3. If new, deep-scrapes the detail page HTML for rich job details.
4. Passes the job to db.upsert_job() which executes our High-Precision 4-Field Verified Deduplication Engine.
5. Triggers instant push broadcast alert to all Android app users.
"""

import requests
import re
import time
import logging
from bs4 import BeautifulSoup
import db
import scraper

log = logging.getLogger("telegram_scraper")

TELEGRAM_CHANNELS = [
    {"username": "Pharma_bharat", "source": "pharmabharat", "domain": "pharmabharat.com"},
    {"username": "pharma_recruiter", "source": "pharmarecruiter", "domain": "pharmarecruiter.in"}
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def extract_slug_from_url(url: str) -> str:
    if not url:
        return ""
    # Strip query params & domain
    path = url.split("?")[0].rstrip("/").split("/")[-1]
    # Remove extension if any
    path = path.replace(".html", "").replace(".php", "")
    return path.strip()


def scrape_pharmarecruiter_feed():
    """
    Parses PharmaRecruiter's instant RSS Feed (https://pharmarecruiter.in/feed/)
    which publishes posts the exact second they are posted on WhatsApp/Website.
    """
    feed_url = "https://pharmarecruiter.in/feed/"
    new_slugs = []
    try:
        log.info("PharmaRecruiter Feed: Fetching instant RSS feed %s", feed_url)
        resp = requests.get(feed_url, headers=HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, "xml")
        items = soup.find_all("item")
        for item in reversed(items):
            link_tag = item.find("link")
            if not link_tag:
                continue
            job_url = link_tag.get_text().strip()
            slug = extract_slug_from_url(job_url)
            if not slug or len(slug) < 5 or db.job_exists_by_slug(slug):
                continue

            # Deep detail scrape
            detail_html = scraper.fetch(job_url)
            if not detail_html:
                continue

            parsed = scraper.parse_detail_page(detail_html)
            if not parsed:
                continue

            job_data = {
                "slug": f"pr-{slug}",
                "url": job_url,
                "title": parsed.get("title") or "New PharmaRecruiter Job",
                "company": parsed.get("company") or "PharmaRecruiter",
                "category": parsed.get("category") or "quality-assurance-jobs",
                "experience_raw": parsed.get("experience_raw"),
                "is_fresher": parsed.get("is_fresher", False),
                "is_fresher_friendly": parsed.get("is_fresher_friendly", False),
                "salary": parsed.get("salary"),
                "location": parsed.get("location"),
                "application_type": parsed.get("application_type"),
                "verified": parsed.get("verified", True),
                "posted_date_raw": parsed.get("posted_date_raw"),
                "description_md": parsed.get("description_md"),
                "detail_scraped": True,
                "email": parsed.get("email"),
                "phone": parsed.get("phone"),
                "banner_url": parsed.get("banner_url"),
                "source": "pharmarecruiter",
            }

            is_inserted = db.upsert_job(job_data)
            if is_inserted:
                new_slugs.append(job_data["slug"])
                log.info("PharmaRecruiter Feed SUCCESS: Added Job '%s' (%s)", job_data["title"], job_data["slug"])
                try:
                    import app
                    notif_title = f"📢 {job_data['company']} - {job_data['title']}"
                    notif_msg = f"{job_data.get('location', '')} | {job_data.get('experience_raw', '')}".strip(" |")
                    app.trigger_internal_push_broadcast(notif_title, notif_msg, job_url)
                except Exception:
                    pass

    except Exception as e:
        log.error("PharmaRecruiter Feed Error: %s", e)

    return new_slugs


def scrape_telegram_channels():
    """
    Scrapes official Telegram channel (@Pharma_bharat) and PharmaRecruiter Instant Feed.
    Returns: list of new job slugs added to jobs.db.
    """
    db.init_db()
    new_slugs = []

    # 1. PharmaRecruiter Instant Feed (feeds WhatsApp channel)
    pr_slugs = scrape_pharmarecruiter_feed()
    new_slugs.extend(pr_slugs)

    for channel_info in TELEGRAM_CHANNELS:
        ch_name = channel_info["username"]
        source = channel_info["source"]
        domain = channel_info["domain"]
        url = f"https://t.me/s/{ch_name}"

        try:
            log.info("Telegram: Fetching public web channel %s", url)
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code != 200:
                log.warning("Telegram: Failed to fetch %s (Status %s)", url, resp.status_code)
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            messages = soup.find_all("div", class_="tgme_widget_message")

            for msg in reversed(messages):  # Oldest to newest in page
                links = [
                    a["href"] for a in msg.find_all("a", href=True)
                    if domain in a["href"] and not "/category/" in a["href"] and not "/tag/" in a["href"]
                ]

                for job_url in links:
                    slug = extract_slug_from_url(job_url)
                    if not slug or len(slug) < 5:
                        continue

                    # Check DB first
                    if db.job_exists_by_slug(slug):
                        continue

                    # New job link found in Telegram channel!
                    log.info("Telegram: New job link found on @%s -> %s", ch_name, job_url)
                    
                    # Deep scrape detail page
                    detail_html = scraper.fetch(job_url)
                    if not detail_html:
                        continue

                    parsed = scraper.parse_detail_page(detail_html)
                    if not parsed:
                        continue

                    job_data = {
                        "slug": slug if source == "pharmabharat" else f"pr-{slug}",
                        "url": job_url,
                        "title": parsed.get("title") or "New Job Opening",
                        "company": parsed.get("company") or ("PharmaBharat" if source == "pharmabharat" else "PharmaRecruiter"),
                        "category": parsed.get("category") or "quality-assurance-jobs",
                        "experience_raw": parsed.get("experience_raw"),
                        "is_fresher": parsed.get("is_fresher", False),
                        "is_fresher_friendly": parsed.get("is_fresher_friendly", False),
                        "salary": parsed.get("salary"),
                        "location": parsed.get("location"),
                        "application_type": parsed.get("application_type"),
                        "verified": parsed.get("verified", True),
                        "posted_date_raw": parsed.get("posted_date_raw"),
                        "description_md": parsed.get("description_md"),
                        "detail_scraped": True,
                        "email": parsed.get("email"),
                        "phone": parsed.get("phone"),
                        "banner_url": parsed.get("banner_url"),
                        "source": source,
                    }

                    # Execute 4-Field Verified Deduplication & Insert
                    is_inserted = db.upsert_job(job_data)
                    if is_inserted:
                        new_slugs.append(job_data["slug"])
                        log.info("Telegram SUCCESS: Added & Deduplicated Job '%s' (%s)", job_data["title"], job_data["slug"])

                        # Trigger instant push notification broadcast to Android app users
                        try:
                            import app
                            notif_title = f"📢 {job_data['company']} - {job_data['title']}"
                            notif_msg = f"{job_data.get('location', '')} | {job_data.get('experience_raw', '')}".strip(" |")
                            app.trigger_internal_push_broadcast(notif_title, notif_msg, job_url)
                        except Exception:
                            pass

                    time.sleep(1.0)  # Gentle delay between page scrapes

        except Exception as e:
            log.error("Telegram: Error processing channel @%s: %s", ch_name, e)

    return new_slugs

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    added = scrape_telegram_channels()
    print(f"Telegram channel scrape finished. Added {len(added)} new jobs.")
