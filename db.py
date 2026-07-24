"""
db.py -- SQLite storage layer for scraped PharmaBharat jobs.

Ek hi jagah par saara DB logic. Koi external DB server nahi chahiye,
sab kuch ek file (jobs.db) mein store hota hai.
"""

import sqlite3
import time
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
    description_md  TEXT,               -- full job detail page, deep-scraped
    detail_scraped  INTEGER DEFAULT 0,
    first_seen_at   INTEGER,             -- unix timestamp, jab hamne pehli baar dekha
    scraped_at      INTEGER,             -- unix timestamp, last detail scrape
    notified        INTEGER DEFAULT 0,   -- notification bhej di kya
    email           TEXT,                -- extracted contact email
    phone           TEXT                 -- extracted phone / whatsapp number
);

CREATE INDEX IF NOT EXISTS idx_category ON jobs(category);
CREATE INDEX IF NOT EXISTS idx_fresher ON jobs(is_fresher_friendly);
CREATE INDEX IF NOT EXISTS idx_notified ON jobs(notified);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Migration: add any missing columns to existing DBs
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(jobs)").fetchall()]
        migrations = [
            ("email",     "ALTER TABLE jobs ADD COLUMN email TEXT"),
            ("phone",     "ALTER TABLE jobs ADD COLUMN phone TEXT"),
            ("scraped_at","ALTER TABLE jobs ADD COLUMN scraped_at INTEGER"),
            ("is_active", "ALTER TABLE jobs ADD COLUMN is_active INTEGER DEFAULT 1"),
        ]
        for col_name, sql in migrations:
            if col_name not in cols:
                conn.execute(sql)
        # Set all existing rows to active if is_active is NULL
        conn.execute("UPDATE jobs SET is_active = 1 WHERE is_active IS NULL")
        # Composite index created AFTER migration so is_active column exists
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_active_cat_fresher ON jobs(is_active, category, is_fresher_friendly)"
        )


def upsert_job(job: dict) -> bool:
    """
    Insert a job if it's new. Returns True if it was a NEW job
    (so caller can decide to notify), False if it already existed.
    """
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT slug FROM jobs WHERE slug = ?", (job["slug"],)
        ).fetchone()
        if existing:
            return False

        conn.execute(
            """
            INSERT INTO jobs (
                slug, url, title, company, category, experience_raw,
                is_fresher, is_fresher_friendly, salary, location,
                application_type, verified, posted_date_raw,
                description_md, detail_scraped, first_seen_at, scraped_at,
                notified, is_active, email, phone
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                job["slug"],
                job["url"],
                job.get("title"),
                job.get("company"),
                job.get("category"),
                job.get("experience_raw"),
                int(job.get("is_fresher", False)),
                int(job.get("is_fresher_friendly", False)),
                job.get("salary"),
                job.get("location"),
                job.get("application_type"),
                int(job.get("verified", False)),
                job.get("posted_date_raw"),
                job.get("description_md"),
                int(job.get("detail_scraped", False)),
                int(time.time()),
                int(time.time()),
                0,
                1,  # is_active = True by default
                job.get("email"),
                job.get("phone"),
            ),
        )
        return True


def update_detail(slug: str, description_md: str, extra: dict):
    """Deep-scrape ke baad detail page ka structured data update karo."""
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


def purge_expired(days: int = 30):
    """
    Mark jobs older than `days` as inactive (is_active=0).
    Does NOT delete — preserves history. Returns count of marked jobs.
    """
    cutoff = int(time.time()) - (days * 86400)
    with get_conn() as conn:
        result = conn.execute(
            "UPDATE jobs SET is_active = 0 WHERE first_seen_at < ? AND is_active = 1",
            (cutoff,)
        )
        count = result.rowcount
    return count


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
        return dict(row) if row else None


def get_stats():
    """Return dashboard summary metrics."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE is_active = 1").fetchone()["c"]
        fresher = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE is_fresher_friendly = 1 AND is_active = 1").fetchone()["c"]
        verified = conn.execute("SELECT COUNT(*) as c FROM jobs WHERE verified = 1 AND is_active = 1").fetchone()["c"]
        categories = conn.execute("SELECT COUNT(DISTINCT category) as c FROM jobs WHERE category IS NOT NULL AND is_active = 1").fetchone()["c"]
        last_job = conn.execute("SELECT MAX(first_seen_at) as m FROM jobs WHERE is_active = 1").fetchone()["m"]
        return {
            "total": total,
            "fresher": fresher,
            "verified": verified,
            "categories": categories,
            "last_updated": last_job
        }


def query_jobs(category=None, fresher_only=False, verified_only=False,
               location=None, q=None, sort_by="newest", page=1, per_page=20):
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
    if q:
        where.append("(title LIKE ? OR company LIKE ? OR email LIKE ? OR phone LIKE ? OR location LIKE ?)")
        params.extend([f"%{q}%"] * 5)

    where_sql = "WHERE " + " AND ".join(where)
    offset = (page - 1) * per_page

    # Proper Sorting Logic with rowid tie-breaker
    if sort_by == "oldest":
        order_clause = "ORDER BY first_seen_at ASC, rowid ASC"
    elif sort_by == "title":
        order_clause = "ORDER BY title ASC, rowid DESC"
    else:  # newest (default)
        order_clause = "ORDER BY first_seen_at DESC, rowid DESC"

    with get_conn() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) as c FROM jobs {where_sql}", params
        ).fetchone()["c"]

        rows = conn.execute(
            f"""SELECT * FROM jobs {where_sql}
                {order_clause} LIMIT ? OFFSET ?""",
            params + [per_page, offset],
        ).fetchall()

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "jobs": [dict(r) for r in rows],
        }


def distinct_categories():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM jobs WHERE category IS NOT NULL AND is_active = 1 ORDER BY category"
        ).fetchall()
        return [r["category"] for r in rows]


def distinct_locations():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT location FROM jobs WHERE location IS NOT NULL AND location != '' AND is_active = 1 ORDER BY location LIMIT 50"
        ).fetchall()
        return [r["location"] for r in rows]
