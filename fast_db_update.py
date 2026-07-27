import sqlite3, scraper, db

conn = sqlite3.connect("jobs.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT slug, url, title, banner_url FROM jobs")
rows = cursor.fetchall()

print(f"Fast re-parsing and updating all {len(rows)} jobs in DB...")
updated_banners = 0

for idx, r in enumerate(rows):
    slug, url, title, old_banner = r["slug"], r["url"], r["title"], r["banner_url"]
    try:
        html = scraper.fetch(url, retries=1)
        if html:
            parsed = scraper.parse_detail_page(html)
            if parsed:
                desc = parsed.get("description_md")
                extra = parsed.get("extra") or {}
                new_banner = extra.get("banner_url")
                
                db.update_detail(slug, desc, extra)
                if new_banner != old_banner:
                    updated_banners += 1
                    b_str = str(new_banner)[:60] if new_banner else "None"
                    print(f"[{idx+1}/{len(rows)}] Updated Banner for: {title[:35]} -> {b_str}")
    except Exception as e:
        print(f"[{idx+1}/{len(rows)}] Error updating {slug}: {e}")

conn.close()
print(f"Completed full database banner update! Updated {updated_banners} job banner images!")
