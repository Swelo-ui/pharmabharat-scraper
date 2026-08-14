import csv
import io
import time
import threading
from collections import deque
from flask import Flask, jsonify, request, render_template, Response

import db
import scraper

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
db.init_db()

# ─── Scrape State ─────────────────────────────────────────────────────────────
is_scraping = False
last_scrape_status = {
    "running": False,
    "new_jobs": 0,
    "scraped_so_far": 0,
    "current_category": None,
    "categories_done": 0,
    "total_targets": 0,
    "error": None,
    "completed_at": None,
}
# Last 5 sync results — newest first
scrape_history: deque = deque(maxlen=5)
# Smart page count: adapts based on last sync result
_adaptive_pages = 1  # default: 1 page per category (~21 targets × 1 page ≈ 50s)

# ─── Stats Cache ──────────────────────────────────────────────────────────────
_stats_cache = {"data": None, "expires_at": 0}
_STATS_TTL = 5  # seconds


def _get_cached_stats():
    now = time.time()
    if _stats_cache["data"] is None or now > _stats_cache["expires_at"]:
        _stats_cache["data"] = db.get_stats()
        _stats_cache["expires_at"] = now + _STATS_TTL
    return _stats_cache["data"]


def _invalidate_stats_cache():
    _stats_cache["expires_at"] = 0


BROADCAST_NOTIFICATION = None

def trigger_internal_push_broadcast(title: str, message: str, url: str = "/"):
    global BROADCAST_NOTIFICATION
    BROADCAST_NOTIFICATION = {
        "id": f"notif_job_{int(time.time())}",
        "title": title,
        "message": message,
        "url": url,
        "timestamp": int(time.time())
    }


@app.route("/api/push-broadcast", methods=["GET", "POST"])
def api_push_broadcast():
    global BROADCAST_NOTIFICATION
    if request.method == "POST":
        data = request.get_json() or {}
        BROADCAST_NOTIFICATION = {
            "id": f"notif_{int(time.time())}",
            "title": data.get("title", "Pharmly Notification"),
            "message": data.get("message", ""),
            "url": data.get("url", "/"),
            "timestamp": int(time.time())
        }
        return jsonify({"status": "success", "notification": BROADCAST_NOTIFICATION})

    # Return broadcast only if set and less than 1 hour old
    if BROADCAST_NOTIFICATION and (int(time.time()) - BROADCAST_NOTIFICATION.get("timestamp", 0)) < 3600:
        return jsonify({"status": "success", "notification": BROADCAST_NOTIFICATION})

    return jsonify({"status": "idle", "notification": None})


@app.route("/api/telegram/scrape", methods=["POST", "GET"])
def api_telegram_scrape():
    import threading
    import telegram_scraper
    def _async_task():
        try:
            telegram_scraper.scrape_telegram_channels()
        except Exception:
            pass
    thread = threading.Thread(target=_async_task)
    thread.daemon = True
    thread.start()
    return jsonify({"status": "success", "message": "Telegram channel scrape triggered in background"})


@app.route("/api/app-version")
def api_app_version():
    return jsonify({
        "version_code": 10,
        "version_name": "3.6.0",
        "download_url": "https://github.com/Swelo-ui/pharmabharat-scraper/raw/main/Pharmly.apk",
        "changelog": [
            "⚡ Official Version 3.6.0 Update!",
            "Native Doze-Bypass Engine — 2-Min Background Closed App Notification",
            "Instant Startup & Resume Push Check in MainActivity",
            "4-Field Verified Smart Deduplication (Brand, Role, Loc, Exp)"
        ]
    })


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/download/apk")
@app.route("/PharmlyPro.apk")
@app.route("/PharmaBharatPro.apk")
def download_apk():
    from flask import send_from_directory
    apk_dir = os.path.dirname(os.path.abspath(__file__))
    file_to_send = "PharmlyPro.apk" if os.path.exists(os.path.join(apk_dir, "PharmlyPro.apk")) else "PharmaBharatPro.apk"
    return send_from_directory(apk_dir, file_to_send, as_attachment=True)


@app.route("/api/jobs")
def api_jobs():
    category = request.args.get("category") or None
    degree = request.args.get("degree") or None
    fresher_only = request.args.get("fresher_only", "false").lower() == "true"
    verified_only = request.args.get("verified_only", "false").lower() == "true"
    location = request.args.get("location") or None
    source = request.args.get("source") or None
    q = request.args.get("q") or None
    sort_by = request.args.get("sort_by", "newest")
    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)

    result = db.query_jobs(
        category=category,
        degree=degree,
        fresher_only=fresher_only,
        verified_only=verified_only,
        location=location,
        source=source,
        q=q,
        sort_by=sort_by,
        page=page,
        per_page=per_page,
    )
    return jsonify(result)


def _decode_cf_hex(hex_str):
    try:
        key = int(hex_str[:2], 16)
        return "".join(chr(int(hex_str[i:i+2], 16) ^ key) for i in range(2, len(hex_str), 2))
    except Exception:
        return ""

def _clean_email_protection(job):
    if not job or not isinstance(job, dict):
        return job
    desc = job.get("description_md")
    if not desc:
        return job

    import re
    def cf_replace(m):
        decoded = _decode_cf_hex(m.group(1))
        return decoded if decoded else m.group(0)

    desc = re.sub(r'data-cfemail="([a-fA-F0-9]+)"', cf_replace, desc)

    contact_email = job.get("email")
    if contact_email:
        desc = re.sub(r'\[email\s*protected\]', f'<a href="mailto:{contact_email}">{contact_email}</a>', desc, flags=re.I)
    elif "data-cfemail" not in desc:
        # Fallback regex search for cf email hashes in text
        def inline_cf_replace(m):
            dec = _decode_cf_hex(m.group(0))
            return dec if dec else m.group(0)
    
    job["description_md"] = desc
    return job


@app.route("/api/job/<path:slug>")
def api_job_detail(slug):
    job = db.get_job_by_slug(slug)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # On-Demand Detail Scrape: If description_md is missing, fetch live, populate DB, and return full details
    desc = job.get("description_md")
    if (not desc or len(str(desc).strip()) < 30) and job.get("url"):
        try:
            detail_html = scraper.fetch(job["url"], retries=3, delay=0.3)
            if detail_html:
                parsed = scraper.parse_detail_page(detail_html)
                if parsed and parsed.get("description_md"):
                    db.update_detail(job["slug"], parsed["description_md"], parsed.get("extra") or {})
                    job = db.get_job_by_slug(slug) or job
        except Exception as e:
            app.logger.warning(f"On-demand detail scrape failed for {slug}: {e}")

    job = _clean_email_protection(job)
    return jsonify(job)


@app.route("/api/stats")
def api_stats():
    stats = dict(_get_cached_stats())
    db_sync = db.get_last_sync_time()
    if last_scrape_status["completed_at"]:
        stats["last_sync_at"] = last_scrape_status["completed_at"]
    elif db_sync and db_sync > 0:
        stats["last_sync_at"] = db_sync
    else:
        stats["last_sync_at"] = stats.get("last_updated")
    return jsonify(stats)


@app.route("/api/categories")
def api_categories():
    return jsonify(db.distinct_categories())


@app.route("/api/locations")
def api_locations():
    return jsonify(db.distinct_locations())


@app.route("/api/sources")
def api_sources():
    """Per-source job counts — for dashboard display."""
    stats = _get_cached_stats()
    return jsonify({
        "pharmabharat": stats.get("pharmabharat_count", 0),
        "pharmarecruiter": stats.get("pharmarecruiter_count", 0),
        "total": stats.get("total", 0),
    })


@app.route("/api/export")
def api_export():
    key = request.args.get("key") or request.args.get("password") or ""
    if key.strip().lower() != "swelo":
        return jsonify({"error": "Unauthorized. Admin password 'swelo' is required to export data."}), 403

    fmt = request.args.get("format", "csv").lower()
    category = request.args.get("category") or None
    degree = request.args.get("degree") or None
    fresher_only = request.args.get("fresher_only", "false").lower() == "true"
    verified_only = request.args.get("verified_only", "false").lower() == "true"
    q = request.args.get("q") or None
    source = request.args.get("source") or None

    result = db.query_jobs(
        category=category,
        degree=degree,
        fresher_only=fresher_only,
        verified_only=verified_only,
        location=None,
        q=q,
        source=source,
        page=1,
        per_page=100000,
    )
    jobs = result["jobs"]

    if fmt == "json":
        return jsonify(jobs)

    # Return CSV with UTF-8 BOM so Excel opens it cleanly with correct encoding & full details
    output = io.StringIO()
    output.write("\ufeff")  # UTF-8 BOM for Microsoft Excel
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "title", "company", "category", "location", "experience_raw", "salary",
            "application_type", "is_fresher_friendly", "verified", "email", "phone",
            "posted_date_raw", "url", "description_md", "source"
        ],
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(jobs)

    response = Response(output.getvalue(), mimetype="text/csv; charset=utf-8-sig")
    response.headers["Content-Disposition"] = "attachment; filename=pharmabharat_jobs_full_details_export.csv"
    return response


# ─── Scraper Background Thread ────────────────────────────────────────────────

def _progress_cb(scraped_so_far, new_so_far, category=None, categories_done=0):
    last_scrape_status["scraped_so_far"] = scraped_so_far
    last_scrape_status["new_jobs"] = new_so_far
    if category is not None:
        last_scrape_status["current_category"] = category
    last_scrape_status["categories_done"] = categories_done


def _run_scrape_bg(pages):
    global is_scraping, last_scrape_status, _adaptive_pages
    try:
        is_scraping = True
        total = 1 + len(scraper.CATEGORY_SLUGS) + 1  # pharmabharat homepage + categories + pharmarecruiter
        last_scrape_status["running"] = True
        last_scrape_status["error"] = None
        last_scrape_status["scraped_so_far"] = 0
        last_scrape_status["new_jobs"] = 0
        last_scrape_status["current_category"] = "homepage"
        last_scrape_status["categories_done"] = 0
        last_scrape_status["total_targets"] = total

        new_slugs = scraper.scrape_all_recent(pages=pages, deep=True, progress_cb=_progress_cb)

        # Also run Telegram channels (@Pharma_bharat & @pharma_recruiter) & WhatsApp RSS feed
        try:
            import telegram_scraper
            tg_slugs = telegram_scraper.scrape_telegram_channels()
            if tg_slugs:
                new_slugs.extend(tg_slugs)
        except Exception as e:
            app.logger.warning(f"Telegram/WhatsApp feed scrape error: {e}")

        last_scrape_status["new_jobs"] = len(new_slugs)

        # Invalidate stats cache after successful scrape
        _invalidate_stats_cache()

        # Smart adaptive page count for next sync
        if len(new_slugs) == 0:
            _adaptive_pages = 1   # found nothing → stay lean
        elif len(new_slugs) > 5:
            _adaptive_pages = min(2, pages + 1)  # lots found → scan more
        else:
            _adaptive_pages = 1   # normal

        # Trigger instant push notification for brand new daily jobs
        if len(new_slugs) > 0:
            try:
                first_job = db.get_job_by_slug(new_slugs[0])
                t_str = first_job.get("title") if first_job else "New Pharma Job Alert!"
                c_str = first_job.get("company") if first_job else ""
                n_msg = f"{c_str} - {len(new_slugs)} new job(s) posted!" if c_str else f"{len(new_slugs)} new pharma job(s) posted!"
                trigger_internal_push_broadcast(t_str, n_msg, f"/api/job/{new_slugs[0]}")
            except Exception:
                pass

    except Exception as e:
        last_scrape_status["error"] = str(e)
        last_scrape_status["new_jobs"] = 0
    finally:
        is_scraping = False
        last_scrape_status["running"] = False
        last_scrape_status["completed_at"] = int(time.time())
        if last_scrape_status.get("new_jobs", 0) > 0:
            db.set_last_sync_time(last_scrape_status["completed_at"])
        db.export_seed_json()

        # Record in history
        scrape_history.appendleft({
            "time": last_scrape_status["completed_at"],
            "new_jobs": last_scrape_status["new_jobs"],
            "scraped_so_far": last_scrape_status["scraped_so_far"],
            "error": last_scrape_status["error"],
        })


@app.route("/api/scrape/trigger", methods=["POST"])
def api_trigger_scrape():
    global is_scraping
    if is_scraping:
        return jsonify({"status": "already_running", "message": "Scraper is already running."})

    pages = request.args.get("pages", _adaptive_pages, type=int)
    t = threading.Thread(target=_run_scrape_bg, args=(pages,))
    t.daemon = True
    t.start()
    return jsonify({"status": "started", "message": f"Scraper started! Scanning {pages} page(s) per category."})


@app.route("/api/scrape/status")
def api_scrape_status():
    return jsonify(last_scrape_status)


@app.route("/api/scrape/history")
def api_scrape_history():
    return jsonify(list(scrape_history))


# ─── Periodic Background Scheduler Thread ─────────────────────────────────────
_scheduler_started = False
_scheduler_lock = threading.Lock()


def _background_scheduler_loop():
    """Runs in background: initial delay 10s, then scrapes every 30 mins."""
    time.sleep(10)
    while True:
        try:
            if not is_scraping:
                _run_scrape_bg(pages=_adaptive_pages)
        except Exception:
            pass
        time.sleep(1800)  # 30 minutes


def start_background_scheduler():
    global _scheduler_started
    with _scheduler_lock:
        if not _scheduler_started:
            _scheduler_started = True
            t = threading.Thread(target=_background_scheduler_loop, daemon=True)
            t.start()


# Auto-start scheduler when app module is loaded
start_background_scheduler()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
