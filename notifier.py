"""
notifier.py -- Naye jobs ke liye Telegram par notification bhejta hai.

Telegram kyun? Web-push (browser notification) ke liye HTTPS + service
worker + VAPID keys chahiye -- setup complex hai. Telegram bot 5 min
mein ban jata hai aur phone pe turant notification aati hai, bina
koi app open kiye.

SETUP (README.md mein bhi hai):
1. Telegram par @BotFather ko message karo -> /newbot -> naam do
   -> tumhe ek BOT_TOKEN milega.
2. Apne naye bot ko Telegram pe search karke usko /start bhejo.
3. Apna chat_id nikalne ke liye is URL ko browser mein khol:
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   (pehle bot ko ek message bhej chuke ho iske baad) -> JSON mein
   "chat":{"id": ...} dikhega, wahi CHAT_ID hai.
4. Dono values env vars mein daal do (ya seedha config.py file mein).
"""

import os
import requests
import logging

log = logging.getLogger("notifier")

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TG_CHAT_ID", "")

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_message(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        log.warning("TG_BOT_TOKEN / TG_CHAT_ID set nahi hain -- notification skip.")
        return False

    url = TELEGRAM_API.format(token=BOT_TOKEN)
    try:
        resp = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning("Telegram send failed: %s %s", resp.status_code, resp.text)
            return False
        return True
    except requests.RequestException as e:
        log.warning("Telegram send error: %s", e)
        return False


def format_job_message(job: dict) -> str:
    fresher_tag = "🟢 FRESHER" if job.get("is_fresher_friendly") else ""
    source = job.get("source", "pharmabharat")
    if source == "pharmarecruiter":
        source_tag = "🌐 PharmaRecruiter.in"
    else:
        source_tag = "💊 PharmaBharat.com"
    parts = [
        f"🆕 <b>{job.get('title') or 'New Job'}</b>",
        f"🏢 {job.get('company') or '-'}",
        f"📌 {job.get('experience_raw') or '-'} {fresher_tag}",
    ]
    if job.get("salary"):
        parts.append(f"💰 {job['salary']}")
    if job.get("location"):
        parts.append(f"📍 {job['location']}")
    if job.get("category"):
        parts.append(f"🏷 {job['category'].replace('-', ' ').title()}")
    parts.append(f"📡 {source_tag}")
    parts.append(f"🔗 <a href=\"{job['url']}\">Apply Now</a>")
    return "\n".join(parts)


def notify_new_jobs():
    """DB mein jitne bhi jobs notified=0 hain, sabke liye message bhejo."""
    import db

    unnotified = db.get_unnotified()
    if not unnotified:
        return 0

    sent_slugs = []
    for job in unnotified:
        ok = send_telegram_message(format_job_message(job))
        if ok:
            sent_slugs.append(job["slug"])

    db.mark_notified(sent_slugs)
    return len(sent_slugs)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = notify_new_jobs()
    print(f"Sent {count} notifications.")
