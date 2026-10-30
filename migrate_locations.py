import sqlite3
import os
import sys

sys.path.append(r"H:\Pharmly\pharmabharat-scraper")
from location_utils import resolve_smart_location, clean_raw_string

db_paths = [
    r"H:\Pharmly\pharmabharat-scraper\jobs.db",
    r"H:\Pharmly\jobs.db"
]

for db_path in db_paths:
    if not os.path.exists(db_path):
        print(f"Skipping non-existent db: {db_path}")
        continue
    
    print(f"\nMigrating locations in {db_path}...")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # 1. Add column if not exists
    cols = [r[1] for r in c.execute("PRAGMA table_info(jobs)").fetchall()]
    if "canonical_location" not in cols:
        print("Adding column canonical_location...")
        c.execute("ALTER TABLE jobs ADD COLUMN canonical_location TEXT")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_canonical_location ON jobs(canonical_location)")

    # 2. Fetch all jobs
    rows = c.execute("SELECT slug, title, location, description_md FROM jobs").fetchall()
    print(f"Total jobs to process: {len(rows)}")

    updated = 0
    for r in rows:
        slug = r["slug"]
        title = r["title"]
        loc = r["location"]
        desc = r["description_md"]

        res = resolve_smart_location(loc, title, desc)
        canonical = res["canonical"]
        clean_disp = res["display"]

        # If current location has markdown junk or table noise, update to clean_disp
        new_loc = loc
        if loc:
            cleaned = clean_raw_string(loc)
            if cleaned != loc or len(loc) > 40 or "*" in loc or "|" in loc:
                new_loc = clean_disp

        c.execute(
            "UPDATE jobs SET canonical_location = ?, location = COALESCE(?, location) WHERE slug = ?",
            (canonical, new_loc, slug)
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"Successfully migrated {updated} jobs in {db_path}!")

print("\nAll database location migrations complete!")
