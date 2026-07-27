import sqlite3, scraper

conn = sqlite3.connect("jobs.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT slug, title, url, banner_url, description_md FROM jobs WHERE title LIKE '%Gufic%'")
rows = cursor.fetchall()

print("Gufic Jobs count:", len(rows))
for r in rows:
    print("Title:", r["title"])
    print("URL:", r["url"])
    print("Banner URL:", r["banner_url"])
    print("Desc snippet:", (r["description_md"] or "")[:500])
    
    # Try fetching HTML and parsing detail
    html = scraper.fetch(r["url"])
    if html:
        parsed = scraper.parse_detail_page(html)
        print("Fresh parsed banner_url:", parsed.get("banner_url"))

conn.close()
