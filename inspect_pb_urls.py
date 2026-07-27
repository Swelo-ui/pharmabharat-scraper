import sqlite3, scraper
from bs4 import BeautifulSoup

conn = sqlite3.connect("jobs.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT title, url, source, banner_url FROM jobs WHERE source='pharmabharat' LIMIT 5")
rows = cursor.fetchall()

for r in rows:
    u = r["url"]
    html = scraper.fetch(u)
    if html:
        soup = BeautifulSoup(html, "lxml")
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        print("Title:", r["title"][:40])
        print("URL:", u)
        print("  og:image:", og["content"] if og else None)
        container = scraper._find_content_container(soup)
        if container:
            for img in container.find_all("img")[:3]:
                real = None
                for attr in ["data-full-url", "data-orig-file", "data-lazy-src", "data-src", "src"]:
                    val = img.get(attr)
                    if val and not val.startswith("data:"):
                        real = val
                        break
                print("  Container real img:", real)
        print("-" * 40)

conn.close()
