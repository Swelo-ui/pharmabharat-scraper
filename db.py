"""
db.py -- SQLite storage layer for scraped PharmaBharat jobs.

Ek hi jagah par saara DB logic. Koi external DB server nahi chahiye,
sab kuch ek file (jobs.db) mein store hota hai.
"""

import sqlite3
import time
import re
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "jobs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    slug            TEXT PRIMARY KEY,   -- URL path, unique id for a job
    url             TEXT NOT NULL,
    title           TEXT,
    company         TEXT,
    category        TEXT,
    experience_raw  TEXT,
    is_fresher      INTEGER DEFAULT 0,  -- strict: card literally says "Fresher"
    is_fresher_friendly INTEGER DEFAULT 0,  -- fresher OR 0-X years experience
    salary          TEXT,
    location        TEXT,
    application_type TEXT,
    verified        INTEGER DEFAULT 0,
    posted_date_raw TEXT,
    posted_timestamp INTEGER,            -- parsed unix timestamp for chronological sorting
    description_md  TEXT,               -- full job detail page, deep-scraped
    detail_scraped  INTEGER DEFAULT 0,
    first_seen_at   INTEGER,             -- unix timestamp, jab hamne pehli baar dekha
    scraped_at      INTEGER,             -- unix timestamp, last detail scrape
    notified        INTEGER DEFAULT 0,   -- notification bhej di kya
    email           TEXT,                -- extracted contact email
    phone           TEXT,                -- extracted phone / whatsapp number
    banner_url      TEXT,                -- extracted HD recruitment banner
    source          TEXT DEFAULT 'pharmabharat'  -- which site: pharmabharat / pharmarecruiter
);

CREATE TABLE IF NOT EXISTS meta (
    key             TEXT PRIMARY KEY,
    value           TEXT
);

CREATE INDEX IF NOT EXISTS idx_category ON jobs(category);
CREATE INDEX IF NOT EXISTS idx_fresher ON jobs(is_fresher_friendly);
CREATE INDEX IF NOT EXISTS idx_notified ON jobs(notified);
CREATE INDEX IF NOT EXISTS idx_posted_ts ON jobs(posted_timestamp);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


import re

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+?91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b|(?:\+?91[\-\s]?)?[6-9]\d{9}\b|0\d{2,4}[\-\s]?\d{6,8}\b")


def backfill_contacts():
    """Extract email & phone from description_md for jobs missing contact columns."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT slug, description_md FROM jobs WHERE (email IS NULL OR phone IS NULL) AND description_md IS NOT NULL"
            ).fetchall()
            for r in rows:
                md_text = r["description_md"]
                if not md_text:
                    continue
                email_m = EMAIL_RE.search(md_text)
                phone_m = PHONE_RE.search(md_text)
                if email_m or phone_m:
                    e_val = email_m.group().strip() if email_m else None
                    p_val = phone_m.group().strip() if phone_m else None
                    conn.execute(
                        "UPDATE jobs SET email = COALESCE(?, email), phone = COALESCE(?, phone) WHERE slug = ?",
                        (e_val, p_val, r["slug"])
                    )
    except Exception:
        pass


def backfill_banners():
    """Fetch og:image for any job in database where banner_url is NULL or invalid web page URL."""
    try:
        import requests
        from bs4 import BeautifulSoup
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT slug, url, banner_url FROM jobs WHERE banner_url IS NULL OR (banner_url NOT LIKE '%.jpg%' AND banner_url NOT LIKE '%.png%' AND banner_url NOT LIKE '%.jpeg%' AND banner_url NOT LIKE '%.webp%' AND banner_url NOT LIKE '%/wp-content/uploads/%')"
            ).fetchall()
            if not rows:
                return
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            }
            for r in rows:
                url = r["url"]
                if not url or not url.startswith("http"):
                    continue
                try:
                    resp = requests.get(url, headers=headers, timeout=6)
                    if resp.status_code == 200:
                        soup = BeautifulSoup(resp.text, "lxml")
                        og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
                        img_url = og_img.get("content").strip() if og_img and og_img.get("content") else None
                        if not img_url:
                            for img in soup.find_all("img"):
                                src_val = img.get("data-full-url") or img.get("data-orig-file") or img.get("data-lazy-src") or img.get("data-src") or img.get("src")
                                if src_val and "/wp-content/uploads/" in src_val:
                                    img_url = src_val.strip()
                                    break
                        if img_url:
                            conn.execute("UPDATE jobs SET banner_url = ? WHERE slug = ?", (img_url, r["slug"]))
                except Exception:
                    pass
    except Exception:
        pass


KNOWN_BRANDS = [
    "Eli Lilly", "Lilly", "IQVIA", "Sandoz", "Colgate", "Accenture", "Emcure", "Emnar Pharma",
    "Medreich Pharma", "Medreich", "GNE Lifesciences", "Strides", "Zydus", "Lupin", "Sun Pharma",
    "Sun Pharmaceutical", "Novartis", "Pfizer", "Merck", "Baxter", "Medtronic", "CorroHealth",
    "ChiroKHealth", "Thermo Fisher", "Thermo Fisher Scientific", "Labcorp", "Icon", "Parexel",
    "Fortrea", "Syneos Health", "ProPharma", "Wipro", "Clario", "RevClinical", "Veeda Clinical Research",
    "Aet Laboratories", "Micro Labs", "Bharat Biotech", "RPG Life Sciences", "Sigachi Industries",
    "Macleods Pharma", "MSN Biotech", "MSN Laboratories", "IPCA Laboratories", "Farbe Firma",
    "Jubilant Biosys", "Altrakem", "Salus Pharmaceuticals", "Immacule Lifesciences", "Baroque Pharmaceuticals",
    "Zenotech Laboratories", "Clarivate", "Ciron Drugs", "Stellar Formulations", "Piramal Pharma", "Marisym Biologicals",
    "Harris", "Bristol Myers Squibb", "Script Assist", "UPSC", "IIT Hyderabad", "West Coast Pharmaceutical",
    "Milan Laboratories", "Gufic Biosciences", "Reckitt", "Heranba Group", "Dr. Reddy", "Klinera", "Mitocon Biopharma"
]

def extract_company_from_text(title: str, text: str = "") -> str:
    combined = f"{title or ''} {text or ''}"
    for brand in KNOWN_BRANDS:
        pattern = r'\b' + re.escape(brand) + r'\b'
        if re.search(pattern, combined, re.IGNORECASE):
            return brand

    match = re.split(r'\b(?:hiring|is hiring|walk[\-\s]?in|announces|careers|openings|recruitment|vacancy)\b', title or "", flags=re.IGNORECASE)
    if match and len(match[0].strip()) > 2:
        candidate = match[0].strip().rstrip(" -:|")
        if len(candidate.split()) <= 4 and candidate.lower() not in ["new pharma job", "pharma jobs", "20 vacancies"]:
            return candidate

    return "Pharma Company"


def backfill_companies():
    """Ensure all jobs in DB have crisp, accurate company names extracted from title/description."""
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT slug, title, company, description_md FROM jobs WHERE company IS NULL OR company = '' OR company = 'None' OR company = 'PHARMA COMPANY'").fetchall()
            for r in rows:
                extracted = extract_company_from_text(r["title"], r["description_md"])
                if extracted and extracted != "Pharma Company":
                    conn.execute("UPDATE jobs SET company = ? WHERE slug = ?", (extracted, r["slug"]))
    except Exception:
        pass


def parse_posted_timestamp(date_raw: str | None) -> int | None:
    """Parse raw string like 'July 25, 2026', '2 hours ago', 'July 24, 2026' to epoch timestamp."""
    if not date_raw:
        return None
    s = str(date_raw).strip()
    now = int(time.time())

    # "2 hours ago", "5 mins ago", "1 day ago"
    m_ago = re.search(r"(\d+)\s*(hour|min|minute|day|week|month)s?\s*ago", s, flags=re.I)
    if m_ago:
        val = int(m_ago.group(1))
        unit = m_ago.group(2).lower()
        if "min" in unit:
            return now - (val * 60)
        elif "hour" in unit:
            return now - (val * 3600)
        elif "day" in unit:
            return now - (val * 86400)
        elif "week" in unit:
            return now - (val * 7 * 86400)
        elif "month" in unit:
            return now - (val * 30 * 86400)

    # Clean ordinal suffixes like "25th July 2026" -> "25 July 2026"
    cleaned_s = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", s)
    formats = [
        "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y",
        "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y/%m/%d"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned_s[:19], fmt)
            return int(dt.timestamp())
        except Exception:
            pass

    return None


def backfill_posted_timestamps():
    """Populate posted_timestamp column for all existing jobs in SQLite DB."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT slug, posted_date_raw, first_seen_at FROM jobs WHERE posted_timestamp IS NULL"
            ).fetchall()
            for r in rows:
                ts = parse_posted_timestamp(r["posted_date_raw"])
                if not ts:
                    ts = r["first_seen_at"] or int(time.time())
                conn.execute("UPDATE jobs SET posted_timestamp = ? WHERE slug = ?", (ts, r["slug"]))
    except Exception:
        pass


def determine_fresher_eligibility(experience_raw: str | None, title: str | None = "", description_md: str | None = "") -> bool:
    """
    Centralized, accurate classifier for Fresher eligibility.
    Returns True if job accepts 0 years / freshers / trainees / interns.
    Returns False if job explicitly requires 1+ years experience.
    """
    exp_raw = (experience_raw or "").strip()
    exp_clean = re.sub(r'[\ufffd\u2013\u2014\u2012–—~]', '-', exp_raw).lower()
    exp_clean = re.sub(r'\s+', ' ', exp_clean)
    
    title_str = (title or "").strip().lower()
    desc_str = (description_md or "").strip().lower()

    # 1. Explicit fresher / trainee / intern / entry level keywords in experience_raw
    if any(k in exp_clean for k in ["fresher", "trainee", "intern", "entry level", "entry-level"]):
        if "not" not in exp_clean:
            return True

    # 2. Check for 0 min experience in experience_raw (e.g. 0-1 years, 0 to 2 years, 0 - 3 years, 0 years, 0-5 years)
    if re.search(r'\b0\d?\s*(?:-|to|\+|\s)\s*\d*\s*(?:year|yr|month)', exp_clean):
        m_zero = re.search(r'\b0(\d+)', exp_clean)
        if not (m_zero and int(m_zero.group(1)) > 0):
            return True

    if exp_clean in ["0 years", "0 year", "0-1 years", "0-1 year", "0"]:
        return True

    # 3. If experience_raw explicitly specifies >= 1 year min experience:
    # e.g., '1-5 years', '3-5 years', '1 year', 'minimum 2 years', '1 to 10 years', '2-6 years', '1-4 years'
    if exp_clean:
        m = re.search(r'(?:min(?:imum)?\s*)?(\d+)\s*(?:-|to|\+|\s)?\s*(\d*)\s*(?:years?|yrs?|months?)', exp_clean)
        if m:
            num = int(m.group(1))
            if num >= 1 and 'fresher' not in exp_clean and 'trainee' not in exp_clean and 'intern' not in exp_clean:
                return False

        if "experience preferred" in exp_clean or "experience required" in exp_clean:
            if 'fresher' not in exp_clean and '0' not in exp_clean:
                return False

    # 4. Check title for explicit fresher / trainee / intern keywords ONLY IF experience_raw is missing or 0
    if any(k in title_str for k in ["fresher", "freshers", "trainee", "intern"]):
        return True

    # 5. Check description if title and experience_raw are empty/ambiguous
    if not exp_clean:
        if any(k in desc_str[:500] for k in ["fresher", "freshers", "0-1 year", "0 to 1", "0-2 year", "0 to 2", "trainee", "intern"]):
            if "not eligible for fresher" not in desc_str and "freshers cannot apply" not in desc_str:
                return True

    return False


def sanitize_fresher_tags():
    """
    Re-evaluate is_fresher, is_fresher_friendly, and category across all active jobs.
    Fixes cases where experienced jobs (>0 years) were mistakenly tagged as FRESHER.
    """
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT slug, title, experience_raw, description_md, is_fresher_friendly, category FROM jobs").fetchall()
            updated_count = 0
            for r in rows:
                slug = r["slug"]
                exp = r["experience_raw"]
                title = r["title"]
                desc = r["description_md"]
                old_ff = r["is_fresher_friendly"]
                old_cat = r["category"]

                new_ff = int(determine_fresher_eligibility(exp, title, desc))
                new_cat = old_cat
                if not new_ff and old_cat == "freshers-jobs":
                    full_text = f"{title or ''} {desc or ''}".lower()
                    if "production" in full_text or "manufacturing" in full_text:
                        new_cat = "production-jobs"
                    elif "quality control" in full_text or "qc " in full_text:
                        new_cat = "quality-control-jobs"
                    elif "research" in full_text or "r&d" in full_text or "formulation" in full_text or "dmpk" in full_text or "chemistry" in full_text:
                        new_cat = "research-and-development-jobs"
                    elif "pharmacovigilance" in full_text or "pv " in full_text or "safety" in full_text:
                        new_cat = "pharmacovigilance-jobs"
                    elif "regulatory" in full_text or "ra " in full_text:
                        new_cat = "regulatory-affairs-jobs"
                    elif "clinical" in full_text or "tmf" in full_text or "cra" in full_text:
                        new_cat = "clinical-research-jobs"
                    else:
                        new_cat = "quality-assurance-jobs"

                if old_ff != new_ff or old_cat != new_cat:
                    conn.execute(
                        "UPDATE jobs SET is_fresher = ?, is_fresher_friendly = ?, category = ? WHERE slug = ?",
                        (new_ff, new_ff, new_cat, slug)
                    )
                    updated_count += 1
            print(f"sanitize_fresher_tags complete: Updated {updated_count} jobs in DB.")
        # Note: export_seed_json() NOT called here — runs at scrape-end in app.py instead
    except Exception as e:
        print(f"Error in sanitize_fresher_tags: {e}")


def init_db():
    with get_conn() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            slug            TEXT PRIMARY KEY,
            url             TEXT NOT NULL,
            title           TEXT,
            company         TEXT,
            category        TEXT,
            experience_raw  TEXT,
            is_fresher      INTEGER DEFAULT 0,
            is_fresher_friendly INTEGER DEFAULT 0,
            salary          TEXT,
            location        TEXT,
            application_type TEXT,
            verified        INTEGER DEFAULT 0,
            posted_date_raw TEXT,
            description_md  TEXT,
            detail_scraped  INTEGER DEFAULT 0,
            first_seen_at   INTEGER,
            scraped_at      INTEGER,
            notified        INTEGER DEFAULT 0
        );
        """)
        # Migration: add any missing columns to existing DBs
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        migrations = [
            ("email",            "ALTER TABLE jobs ADD COLUMN email TEXT"),
            ("phone",            "ALTER TABLE jobs ADD COLUMN phone TEXT"),
            ("scraped_at",       "ALTER TABLE jobs ADD COLUMN scraped_at INTEGER"),
            ("is_active",        "ALTER TABLE jobs ADD COLUMN is_active INTEGER DEFAULT 1"),
            ("banner_url",       "ALTER TABLE jobs ADD COLUMN banner_url TEXT"),
            ("source",           "ALTER TABLE jobs ADD COLUMN source TEXT DEFAULT 'pharmabharat'"),
            ("posted_timestamp", "ALTER TABLE jobs ADD COLUMN posted_timestamp INTEGER"),
        ]
        for col_name, sql in migrations:
            if col_name not in cols:
                try:
                    conn.execute(sql)
                except Exception:
                    pass
        # Set all existing rows to active if is_active is NULL
        conn.execute("UPDATE jobs SET is_active = 1 WHERE is_active IS NULL")
        # Composite indexes created AFTER migration so columns exist
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON jobs(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fresher ON jobs(is_fresher_friendly)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_notified ON jobs(notified)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_active_cat_fresher ON jobs(is_active, category, is_fresher_friendly)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON jobs(source)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posted_ts ON jobs(posted_timestamp)")
    # Auto-extract email/phone, banner images, posted timestamps & company names for existing jobs
    backfill_contacts()
    backfill_banners()
    backfill_posted_timestamps()
    backfill_companies()
    seed_from_json()
    sanitize_fresher_tags()


# ─── GitHub Seed Sync (Bandwidth-Safe) ────────────────────────────────────────
# Throttle: 1 upload per 6 hours max = 4 uploads/day
# Bandwidth: 14 MB × 4 × 30 days = 1.68 GB/month  ✅ (safe under 4 GB limit)
#
# WHY 6 HOURS (not 5 min like before):
#   Old: 5-min throttle → up to 150 uploads/day → 2.1 GB/DAY → suspended in 3 days
#   New: 6-hr throttle  → max 4 uploads/day     → 1.68 GB/MONTH → safe ✅
#
# CALL CHAIN (fixed):
#   scrape_end (app.py) → export_seed_json() → sync_github_seed()
#   upsert_job()        → ❌ NO longer calls export_seed_json() (removed)
#   update_detail()     → ❌ NO longer calls export_seed_json() (removed)
_last_github_sync_time = 0.0


def sync_github_seed():
    """
    Upload jobs_seed.json to GitHub repo once every 6 hours (max 4x/day).

    Purpose: Persist new scraped jobs across Render redeploys.
    Without this: any redeploy wipes jobs scraped since last git push.

    Bandwidth budget:
        14 MB per upload × 4 per day × 30 days = 1.68 GB/month
        Leaves ~2.3 GB/month for API traffic (total free = 5 GB)
    """
    global _last_github_sync_time
    import os, json, base64, requests, time

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return  # No token set → skip silently (local dev or token not configured)

    now = time.time()
    THROTTLE_SECONDS = 12 * 3600  # 12 hours = max 2 uploads/day (bandwidth-optimized)
    if now - _last_github_sync_time < THROTTLE_SECONDS:
        remaining = int((THROTTLE_SECONDS - (now - _last_github_sync_time)) / 60)
        log.info(f"sync_github_seed: throttled, next upload in ~{remaining} min")
        return

    repo = os.environ.get("GITHUB_REPOSITORY") or "Swelo-ui/pharmabharat-scraper"
    seed_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs_seed.json")
    if not os.path.exists(seed_file):
        return

    try:
        with open(seed_file, "r", encoding="utf-8") as f:
            content_str = f.read()

        api_url = f"https://api.github.com/repos/{repo}/contents/jobs_seed.json"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "pharmabharat-seed-sync"
        }

        # GET current SHA (needed for update, not insert)
        resp = requests.get(api_url, headers=headers, timeout=10)
        sha = resp.json().get("sha") if resp.status_code == 200 else None

        content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
        payload = {
            "message": "chore: auto-sync jobs_seed.json [skip ci] [skip render]",
            "content": content_b64,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        r = requests.put(api_url, headers=headers, json=payload, timeout=20)
        if r.status_code in (200, 201):
            _last_github_sync_time = now
            log.info("sync_github_seed: ✅ Uploaded jobs_seed.json to GitHub (%.1f MB)", len(content_str) / 1_000_000)
        else:
            log.warning("sync_github_seed: GitHub API returned %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        log.warning("sync_github_seed: failed — %s", e)


def export_seed_json():
    """
    Write all active jobs to jobs_seed.json on local disk.
    Then attempt GitHub sync (max 4x/day via 6-hr throttle inside sync_github_seed).

    Called ONLY from:
      - _run_scrape_bg() in app.py (end of each full scrape cycle)
    NOT called from upsert_job() or update_detail() — that caused the bandwidth disaster.
    """
    import os, json
    seed_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs_seed.json")
    try:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM jobs WHERE is_active = 1 ORDER BY posted_timestamp DESC").fetchall()
            jobs_data = [dict(r) for r in rows]
            if jobs_data:
                with open(seed_file, "w", encoding="utf-8") as f:
                    json.dump(jobs_data, f, ensure_ascii=False, indent=2)
        # Sync to GitHub — 6-hr throttle inside prevents bandwidth abuse
        sync_github_seed()
    except Exception as e:
        log.warning("export_seed_json failed: %s", e)


def seed_from_json():
    """Ensure database is auto-seeded from jobs_seed.json on container startup if fresh or missing jobs."""
    import os, json
    seed_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs_seed.json")
    if not os.path.exists(seed_file):
        return
    try:
        with open(seed_file, "r", encoding="utf-8") as f:
            seed_jobs = json.load(f)
        if not seed_jobs:
            return
        with get_conn() as conn:
            for j in seed_jobs:
                conn.execute("""
                    INSERT INTO jobs (
                        slug, url, title, company, category, experience_raw, is_fresher, is_fresher_friendly,
                        salary, location, application_type, verified, posted_date_raw, posted_timestamp,
                        description_md, detail_scraped, first_seen_at, scraped_at, notified, email, phone, banner_url, source, is_active
                    ) VALUES (
                        :slug, :url, :title, :company, :category, :experience_raw, :is_fresher, :is_fresher_friendly,
                        :salary, :location, :application_type, :verified, :posted_date_raw, :posted_timestamp,
                        :description_md, :detail_scraped, :first_seen_at, :scraped_at, :notified, :email, :phone, :banner_url, :source, 1
                    ) ON CONFLICT(slug) DO UPDATE SET
                        title = excluded.title,
                        company = excluded.company,
                        category = excluded.category,
                        experience_raw = excluded.experience_raw,
                        salary = excluded.salary,
                        location = excluded.location,
                        application_type = excluded.application_type,
                        posted_date_raw = excluded.posted_date_raw,
                        posted_timestamp = excluded.posted_timestamp,
                        description_md = excluded.description_md,
                        email = excluded.email,
                        phone = excluded.phone,
                        banner_url = excluded.banner_url,
                        is_active = 1
                """, {
                    "slug": j.get("slug"),
                    "url": j.get("url"),
                    "title": j.get("title"),
                    "company": j.get("company"),
                    "category": j.get("category"),
                    "experience_raw": j.get("experience_raw"),
                    "is_fresher": j.get("is_fresher", 0),
                    "is_fresher_friendly": j.get("is_fresher_friendly", 0),
                    "salary": j.get("salary"),
                    "location": j.get("location"),
                    "application_type": j.get("application_type"),
                    "verified": j.get("verified", 0),
                    "posted_date_raw": j.get("posted_date_raw"),
                    "posted_timestamp": j.get("posted_timestamp"),
                    "description_md": j.get("description_md"),
                    "detail_scraped": j.get("detail_scraped", 0),
                    "first_seen_at": j.get("first_seen_at"),
                    "scraped_at": j.get("scraped_at"),
                    "notified": j.get("notified", 0),
                    "email": j.get("email"),
                    "phone": j.get("phone"),
                    "banner_url": j.get("banner_url"),
                    "source": j.get("source", "pharmabharat")
                })
    except Exception:
        pass


def _clean_str(text: str) -> str:
    if not text:
        return ""
    t = text.lower().replace("&", " and ")
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    return ' '.join(t.split())


def job_exists_by_slug(slug: str) -> bool:
    """Returns True if a job with the given slug or pr-slug already exists in jobs.db."""
    if not slug:
        return False
    with get_conn() as conn:
        row = conn.execute("SELECT slug FROM jobs WHERE slug = ? OR slug = ?", (slug, f"pr-{slug}")).fetchone()
        return row is not None


def _extract_brand_tokens(title: str, company: str) -> set:
    combined = _clean_str(f"{company or ''} {title or ''}")
    stop_words = {'hiring', 'is', 'for', 'walk', 'in', 'interview', 'jobs', 'vacancies', 'openings', 'ltd', 'limited', 'inc', 'pharma', 'pharmaceuticals', 'laboratories', 'biotech', 'lifesciences', 'qa', 'qc', 'professionals', 'plant', 'role', 'roles', 'and'}
    return set(w for w in combined.split() if w not in stop_words and len(w) > 2)


def _is_duplicate_job(conn, job: dict) -> bool:
    """
    High-Precision Multi-Field Deduplication Engine:
    Requires positive match across multiple verified data fields:
    1. Direct URL Slug Match
    2. Poster Image / Banner URL Match (non-default uploads)
    3. Direct Email / Phone Match
    4. Strict Multi-Field Overlap (Brand Match + Role Match + Location Match)
    """
    slug = job.get("slug") or ""
    title = job.get("title") or ""
    company = job.get("company") or ""
    location = job.get("location") or ""
    banner_url = job.get("banner_url")
    email = job.get("email")
    phone = job.get("phone")

    # 1. Direct Slug Match
    if slug:
        existing = conn.execute("SELECT slug FROM jobs WHERE slug = ?", (slug,)).fetchone()
        if existing:
            return True

    # 2. Poster Image Match (unique recruitment banner upload)
    if banner_url and "wp-content/uploads" in banner_url and "default" not in banner_url:
        img_filename = banner_url.split("/")[-1]
        if len(img_filename) > 5 and "Pharma-jobs" not in img_filename and "FRESHERS-Hiring" not in img_filename:
            b_row = conn.execute("SELECT slug FROM jobs WHERE banner_url LIKE ? AND is_active = 1 LIMIT 1", (f"%{img_filename}%",)).fetchone()
            if b_row:
                return True

    # 3. Direct Contact Info Match (Email or Phone)
    if email and len(email) > 5:
        e_row = conn.execute("SELECT slug FROM jobs WHERE lower(email) = lower(?) AND is_active = 1 LIMIT 1", (email.strip(),)).fetchone()
        if e_row:
            return True

    if phone and len(phone) > 7:
        clean_p = re.sub(r'\D', '', phone)
        if len(clean_p) >= 10:
            p_row = conn.execute("SELECT slug FROM jobs WHERE phone LIKE ? AND is_active = 1 LIMIT 1", (f"%{clean_p[-10:]}%",)).fetchone()
            if p_row:
                return True

    # 4. Ultra-Smart Actual Role Words & Domain Footprint Verification Engine
    brands1 = _extract_brand_tokens(title, company)
    if not brands1:
        return False

    core_pharma_keywords = {
        'qc', 'qa', 'quality', 'control', 'assurance', 'production', 'manufacturing', 'injectable', 'injectables',
        'osd', 'formulation', 'r&d', 'research', 'development', 'safety', 'reporting', 'pharmacovigilance', 'pv',
        'coordinator', 'analyst', 'programmer', 'coder', 'coding', 'tmf', 'regulatory', 'affairs', 'microbiology',
        'micro', 'utilities', 'engineering', 'maintenance', 'sales', 'representative', 'intern', 'apprentice',
        'trainee', 'officer', 'executive', 'manager', 'director', 'associate', 'specialist', 'auditor', 'packaging',
        'packing', 'warehouse', 'store', 'purchase', 'procurement', 'hr', 'human', 'resources'
    }
    stop_words = {
        'hiring', 'is', 'for', 'walk', 'in', 'interview', 'jobs', 'vacancies', 'openings',
        'ltd', 'limited', 'inc', 'pharma', 'pharmaceuticals', 'laboratories', 'biotech',
        'lifesciences', 'professionals', 'plant', 'role', 'roles', 'and', 'at', 'with', 'apply', 'now', '2026', 'drive'
    }

    t1_clean = re.sub(r'[^a-z0-9\s]', ' ', title.lower())
    t1_words = set(t1_clean.split())
    kw1 = set(w for w in t1_words if (w in core_pharma_keywords or (len(w) > 3 and w not in stop_words)))
    if not kw1:
        return False

    l1 = set(re.sub(r'[^a-z0-9\s]', ' ', (location or "").lower()).split())
    exp1_raw = _clean_str(job.get("experience_raw", ""))
    is_fresher1 = int(job.get("is_fresher", 0))

    rows = conn.execute("SELECT slug, title, company, location, experience_raw, is_fresher FROM jobs WHERE is_active = 1 ORDER BY posted_timestamp DESC LIMIT 250").fetchall()
    for r in rows:
        brands2 = _extract_brand_tokens(r["title"], r["company"])
        if not brands1.intersection(brands2):
            continue  # Different companies -> Not duplicate

        t2_clean = re.sub(r'[^a-z0-9\s]', ' ', (r["title"] or "").lower())
        t2_words = set(t2_clean.split())
        kw2 = set(w for w in t2_words if (w in core_pharma_keywords or (len(w) > 3 and w not in stop_words)))
        if not kw2:
            continue

        shared_role_words = kw1.intersection(kw2)
        if not shared_role_words:
            continue  # Zero shared core role words -> Distinct jobs

        union_role_words = kw1.union(kw2)
        role_ratio = len(shared_role_words) / float(len(union_role_words)) if union_role_words else 0.0

        # Location verification
        l2 = set(re.sub(r'[^a-z0-9\s]', ' ', (r["location"] or "").lower()).split())
        loc_mismatch = False
        if l1 and l2 and not (l1 & l2):
            loc_mismatch = True

        # Experience Level Verification
        exp2_raw = _clean_str(r["experience_raw"] or "")
        is_fresher2 = int(r["is_fresher"] or 0)
        exp_mismatch = False
        if (is_fresher1 and not is_fresher2 and "year" in exp2_raw and "0" not in exp2_raw) or (is_fresher2 and not is_fresher1 and "year" in exp1_raw and "0" not in exp1_raw):
            exp_mismatch = True

        if loc_mismatch or exp_mismatch:
            continue

        # Declare duplicate ONLY IF actual role footprint matches >= 70%
        if role_ratio >= 0.70:
            return True

    return False


def upsert_job(job: dict) -> bool:
    """
    Insert a job if it's new. Returns True if it was a NEW job
    (so caller can decide to notify), False if it already existed.

    Deduplication:
    - slug-based: same URL slug = same job (always skip)
    - smart dedup: title, company, banner image URL, or email/phone overlap
      Prefer the first source that inserted it (pharmabharat priority).
    """
    with get_conn() as conn:
        # Check by slug first
        existing = conn.execute(
            "SELECT slug FROM jobs WHERE slug = ?", (job["slug"],)
        ).fetchone()
        if existing:
            return False

        # Smart deduplication: check title, company, banner image, email/phone
        if _is_duplicate_job(conn, job):
            return False

        posted_ts = parse_posted_timestamp(job.get("posted_date_raw")) or int(time.time())
        is_ff = int(determine_fresher_eligibility(job.get("experience_raw"), job.get("title"), job.get("description_md")))
        res = conn.execute(
            """
            INSERT OR IGNORE INTO jobs (
                slug, url, title, company, category, experience_raw,
                is_fresher, is_fresher_friendly, salary, location,
                application_type, verified, posted_date_raw, posted_timestamp,
                description_md, detail_scraped, first_seen_at, scraped_at,
                notified, is_active, email, phone, banner_url, source
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                job["slug"],
                job["url"],
                job.get("title"),
                job.get("company"),
                job.get("category"),
                job.get("experience_raw"),
                is_ff,
                is_ff,
                job.get("salary"),
                job.get("location"),
                job.get("application_type"),
                int(job.get("verified", False)),
                job.get("posted_date_raw"),
                posted_ts,
                job.get("description_md"),
                int(job.get("detail_scraped", False)),
                int(time.time()),
                int(time.time()),
                0,  # notified
                1,  # is_active
                job.get("email"),
                job.get("phone"),
                job.get("banner_url"),
                job.get("source", "pharmabharat"),
            ),
        )
        is_new_insert = (res.rowcount > 0)
    # ✅ BANDWIDTH FIX: Removed per-job export_seed_json() call.
    # Old: every upsert → export_seed_json() → sync_github_seed() → 14MB upload
    # New: seed export happens only at end of full scrape (in app.py _run_scrape_bg)
    return is_new_insert


def update_detail(slug: str, description_md: str, extra: dict):
    """Deep-scrape ke baad detail page ka structured data update karo."""
    b_url = extra.get("banner_url")
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE jobs SET description_md = ?, detail_scraped = 1,
                            scraped_at = ?,
                            salary = COALESCE(?, salary),
                            location = COALESCE(?, location),
                            experience_raw = COALESCE(?, experience_raw),
                            email = COALESCE(?, email),
                            phone = COALESCE(?, phone)
            WHERE slug = ?
            """,
            (
                description_md,
                int(time.time()),
                extra.get("salary"),
                extra.get("location"),
                extra.get("experience_raw"),
                extra.get("email"),
                extra.get("phone"),
                slug,
            ),
        )
        if b_url and (any(ext in b_url.lower() for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]) or "/wp-content/uploads/" in b_url):
            conn.execute("UPDATE jobs SET banner_url = ? WHERE slug = ?", (b_url, slug))
            
        row = conn.execute("SELECT title, experience_raw FROM jobs WHERE slug = ?", (slug,)).fetchone()
        if row:
            is_ff = int(determine_fresher_eligibility(row["experience_raw"], row["title"], description_md))
            conn.execute("UPDATE jobs SET is_fresher = ?, is_fresher_friendly = ? WHERE slug = ?", (is_ff, is_ff, slug))
    # ✅ BANDWIDTH FIX: Removed export_seed_json() — was triggering 14MB upload per detail scrape


def purge_expired(days: int = 180):
    """
    Unlimited Jobs Storage: Never deactivate or purge jobs from database.
    """
    return 0


def get_unnotified():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE notified = 0 AND is_active = 1 ORDER BY first_seen_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]


def mark_notified(slugs: list):
    if not slugs:
        return
    with get_conn() as conn:
        conn.executemany(
            "UPDATE jobs SET notified = 1 WHERE slug = ?", [(s,) for s in slugs]
        )


def get_job_by_slug(slug: str):
    """Fetch single job detail by slug."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE slug = ?", (slug,)).fetchone()
        if row:
            d = dict(row)
            d["is_expired"] = detect_is_expired(d)
            return d
    return None


def set_last_sync_time(ts: int | None = None):
    """Store the exact timestamp when a scrape completed into SQLite meta table."""
    if ts is None:
        ts = int(time.time())
    try:
        with get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_sync_at', ?)", (str(ts),))
    except Exception:
        pass


def get_last_sync_time() -> int:
    """Fetch exact timestamp of last completed scrape with new jobs from DB meta table or max job timestamp."""
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = 'last_sync_at'").fetchone()
            if row and row["value"]:
                val = int(row["value"])
                if val <= int(time.time()):
                    return val
            row_max = conn.execute("SELECT MAX(posted_timestamp) as m FROM jobs WHERE is_active = 1 AND posted_timestamp <= ?", (int(time.time()),)).fetchone()
            if row_max and row_max["m"]:
                return row_max["m"]
            return int(time.time())
    except Exception:
        return int(time.time())


def get_stats():
    """Return dashboard summary metrics."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE is_active = 1").fetchone()["c"]
        fresher = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE is_fresher_friendly = 1 AND is_active = 1").fetchone()["c"]
        verified = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE verified = 1 AND is_active = 1").fetchone()["c"]
        categories = conn.execute("SELECT COUNT(DISTINCT category) as c FROM jobs WHERE category IS NOT NULL AND is_active = 1").fetchone()["c"]
        last_sync = get_last_sync_time()
        # Source-wise counts
        pb_count = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE is_active = 1 AND (source = 'pharmabharat' OR source IS NULL)").fetchone()["c"]
        pr_count = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE is_active = 1 AND source = 'pharmarecruiter'").fetchone()["c"]
        return {
            "total": total,
            "fresher": fresher,
            "verified": verified,
            "categories": categories,
            "last_updated": last_sync,
            "pharmabharat_count": pb_count,
            "pharmarecruiter_count": pr_count,
        }


MONTHS_MAP = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'june': 6, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
    'nov': 11, 'november': 11, 'dec': 12, 'december': 12
}


def detect_is_expired(job: dict) -> bool:
    """
    Detect if walk-in event date or application deadline has passed relative to today.
    Returns True ONLY IF an explicit event/walk-in date or deadline is found AND all such dates are strictly in the past.
    Returns False if any event date is today/future or if no explicit event date is specified.
    """
    try:
        today = datetime.now().date()
        title = (job.get("title") or "").lower()
        desc = (job.get("description_md") or "").lower()

        # Remove URLs to avoid false positives in file/image paths
        desc = re.sub(r'https?://[^\s<>"]+', '', desc)
        desc = re.sub(r'\]\s*\(\s*https?://[^)]*\)', ']()', desc)

        full_text = f"{title}\n{desc}"
        filtered_lines = []
        for line in full_text.splitlines():
            if re.search(r'\b(?:posted|published|post|publish)\b', line, re.I):
                continue
            filtered_lines.append(line)
        text = "\n".join(filtered_lines)

        event_dates = []

        # Specific keywords that indicate actual walk-in/interview/deadline event dates
        kw = r'(?:walk[\-\s]?in|interview|drive|deadline|last date|event date|due date|closing date|valid till|valid up to|held on|scheduled on|timing|on\s+(?:august|aug|july|jul|june|jun|september|sep|october|oct|november|nov|december|dec|january|jan|february|feb|march|mar)|date[\s:\-\*]+)'

        # 1. Match numeric date ranges like '25-07-2026 to 27-07-2026'
        for m in re.finditer(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\s*(?:to|\-)\s*(\d{1,2})[\/\-\.](\d{4})', text):
            d, mth, y = int(m.group(4)), int(m.group(5)), int(m.group(6))
            if 2020 <= y <= 2035:
                try:
                    event_dates.append(datetime(y, mth, d).date())
                except Exception:
                    pass

        # 2. Match single numeric dates near walk-in / interview / drive / deadline keywords
        for m in re.finditer(kw + r'.*?(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', text):
            d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2020 <= y <= 2035:
                try:
                    event_dates.append(datetime(y, mth, d).date())
                except Exception:
                    pass

        # 3. Match word dates (DD Month YYYY) near keywords
        for m in re.finditer(kw + r'.*?(\d{1,2})(?:st|nd|rd|th)?\s+(?:&|and|\-)?\s*(?:(\d{1,2})(?:st|nd|rd|th)?\s+)?([a-z]+)\s+(\d{4})', text):
            d1 = int(m.group(1))
            d2 = int(m.group(2)) if m.group(2) else d1
            last_day = max(d1, d2)
            mth_str = m.group(3).lower()
            y = int(m.group(4))
            if mth_str in MONTHS_MAP and 2020 <= y <= 2035:
                try:
                    event_dates.append(datetime(y, MONTHS_MAP[mth_str], last_day).date())
                except Exception:
                    pass

        # 4. Match US-format word dates (Month DD, YYYY) near keywords
        for m in re.finditer(kw + r'.*?([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?[,\s]+(\d{4})', text):
            mth_str = m.group(1).lower()
            d = int(m.group(2))
            y = int(m.group(3))
            if mth_str in MONTHS_MAP and 2020 <= y <= 2035:
                try:
                    event_dates.append(datetime(y, MONTHS_MAP[mth_str], d).date())
                except Exception:
                    pass

        if not event_dates:
            return False

        latest_event = max(event_dates)
        return latest_event < today

    except Exception:
        return False


def detect_degrees(title: str | None, desc: str | None, category: str | None) -> list:
    """Detect eligible pharmaceutical degrees (B.Pharm, M.Pharm, Pharm.D, D.Pharm) from job text."""
    txt = f"{title or ''} {desc or ''} {category or ''}".lower()
    degs = []
    if re.search(r"\bb[\.\-\s]?pharm\b|\bbachelor\s+of\s+pharmacy\b", txt):
        degs.append("B.Pharm")
    if re.search(r"\bm[\.\-\s]?pharm\b|\bmaster\s+of\s+pharmacy\b", txt):
        degs.append("M.Pharm")
    if re.search(r"\bpharm[\.\-\s]?d\b|\bdoctor\s+of\s+pharmacy\b", txt):
        degs.append("Pharm.D")
    if re.search(r"\bd[\.\-\s]?pharm\b|\bdiploma\s+in\s+pharmacy\b", txt):
        degs.append("D.Pharm")
    return degs


def query_jobs(category=None, fresher_only=False, verified_only=False,
               location=None, q=None, sort_by="newest", page=1, per_page=20,
               source=None, degree=None):
    where = ["is_active = 1"]
    params = []

    if category:
        where.append("category = ?")
        params.append(category)
    if fresher_only:
        where.append("is_fresher_friendly = 1")
    if verified_only:
        where.append("verified = 1")
    if location:
        where.append("location LIKE ?")
        params.append(f"%{location}%")
    if source:
        where.append("source = ?")
        params.append(source)
    if degree:
        deg = degree.lower().strip()
        if deg == "bpharm":
            where.append("(title LIKE '%b.pharm%' OR title LIKE '%bpharm%' OR title LIKE '%b-pharm%' OR title LIKE '%b. pharmacy%' OR title LIKE '%bachelor of pharmacy%' OR description_md LIKE '%b.pharm%' OR description_md LIKE '%bpharm%' OR description_md LIKE '%b-pharm%' OR description_md LIKE '%b. pharmacy%' OR description_md LIKE '%bachelor of pharmacy%')")
        elif deg == "mpharm":
            where.append("(title LIKE '%m.pharm%' OR title LIKE '%mpharm%' OR title LIKE '%m-pharm%' OR title LIKE '%m. pharmacy%' OR title LIKE '%master of pharmacy%' OR description_md LIKE '%m.pharm%' OR description_md LIKE '%mpharm%' OR description_md LIKE '%m-pharm%' OR description_md LIKE '%m. pharmacy%' OR description_md LIKE '%master of pharmacy%')")
        elif deg == "pharmd":
            where.append("(title LIKE '%pharm.d%' OR title LIKE '%pharmd%' OR title LIKE '%pharm-d%' OR title LIKE '%doctor of pharmacy%' OR description_md LIKE '%pharm.d%' OR description_md LIKE '%pharmd%' OR description_md LIKE '%pharm-d%' OR description_md LIKE '%doctor of pharmacy%')")
        elif deg == "dpharm":
            where.append("(title LIKE '%d.pharm%' OR title LIKE '%dpharm%' OR title LIKE '%d-pharm%' OR title LIKE '%diploma in pharmacy%' OR description_md LIKE '%d.pharm%' OR description_md LIKE '%dpharm%' OR description_md LIKE '%d-pharm%' OR description_md LIKE '%diploma in pharmacy%')")

    if q:
        where.append("(title LIKE ? OR company LIKE ? OR email LIKE ? OR phone LIKE ? OR location LIKE ? OR description_md LIKE ?)")
        params.extend([f"%{q}%"] * 6)

    where_sql = "WHERE " + " AND ".join(where)
    offset = (page - 1) * per_page

    # Chronological Sorting by actual post date & time
    if sort_by == "oldest":
        order_clause = "ORDER BY COALESCE(posted_timestamp, first_seen_at) ASC, rowid ASC"
    elif sort_by == "title":
        order_clause = "ORDER BY title ASC, rowid DESC"
    else:  # newest (default)
        order_clause = "ORDER BY COALESCE(posted_timestamp, first_seen_at) DESC, rowid DESC"

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) as c FROM jobs {where_sql}", params
        ).fetchone()["c"]

        rows = conn.execute(
            f"""SELECT * FROM jobs {where_sql}
                {order_clause} LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()

        job_list = []
        now_ts = int(time.time())
        for r in rows:
            d = dict(r)
            d["degrees"] = detect_degrees(d.get("title"), d.get("description_md"), d.get("category"))
            d["is_expired"] = detect_is_expired(d)
            first_seen = d.get("first_seen_at") or 0
            # If discovered within last 24h and has a detailed posted_date_raw
            if (now_ts - first_seen) < 86400 and d.get("posted_date_raw") and d.get("detail_scraped"):
                d["date_updated_recently"] = True
            else:
                d["date_updated_recently"] = False
            job_list.append(d)

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "jobs": job_list,
        }


def distinct_categories():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM jobs WHERE category IS NOT NULL AND is_active = 1 ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]


def _normalize_location(raw: str) -> str | None:
    """
    Normalize a raw location string to a clean, short city name.
    Returns None if the string is junk/too long/not a city.
    """
    if not raw:
        return None

    s = raw.strip()

    # Reject junk: markdown, company names, sentences, symbols
    JUNK_PATTERNS = [
        r'\*\*',            # markdown bold
        r'Job Location',    # literal label
        r'Company Name',    # literal label
        r'INDIAN AIR FORCE',
        r'Biophore India Pharmaceuticals',
        r'CDSCO',
        r'^India$',         # just "India" is too broad
    ]
    for pat in JUNK_PATTERNS:
        if re.search(pat, s, re.I):
            return None

    # Strip markdown formatting: **text**, *text*
    s = re.sub(r'\*+', '', s).strip()

    # Strip generic country prefixes like 'India (Remote) & ' or 'India &'
    s = re.sub(r'^India\s*(\([^)]*\))?\s*(&|/|and)\s*', '', s, flags=re.I).strip()

    # Handle compound locations with ' & ', ' / ', ' and ': pick the primary city
    if ' & ' in s:
        s = s.split(' & ')[0].strip()
    if ' / ' in s:
        s = s.split(' / ')[0].strip()
    if ' and ' in s:
        s = s.split(' and ')[0].strip()

    # Strip trailing state/country suffix variations to get canonical city
    # e.g., "Ahmedabad, Gujarat, India" -> "Ahmedabad"
    parts = [p.strip() for p in re.split(r',', s)]
    if len(parts) >= 2:
        city = parts[0]
    else:
        city = s

    # Normalize Bengaluru <-> Bangalore (keep Bengaluru as canonical)
    city = re.sub(r'\bBangalore\b', 'Bengaluru', city, flags=re.I)

    # Strip parenthetical area names or Remote tags
    city = re.sub(r'\s*\([^)]*\)', '', city).strip()

    # Reject if still too long (> 25 chars) or invalid generic words
    if not city or len(city) > 25 or city.lower() in ['india', 'remote', 'across india']:
        return None
    if any(kw in city.lower() for kw in ['pharmaceutical', 'looking', 'hiring', 'opportunity', 'company', 'ltd']):
        return None

    return city.strip() if city.strip() else None


def distinct_locations():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT location, COUNT(*) as cnt FROM jobs WHERE location IS NOT NULL AND location != '' AND is_active = 1 GROUP BY location ORDER BY cnt DESC"
        ).fetchall()

    # Normalize and deduplicate
    seen = set()
    clean = []
    for r in rows:
        norm = _normalize_location(r["location"])
        if norm and norm.lower() not in seen:
            seen.add(norm.lower())
            clean.append(norm)

    # Sort alphabetically and limit
    clean.sort()
    return clean[:60]
