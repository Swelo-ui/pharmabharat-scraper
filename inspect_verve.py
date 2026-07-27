import scraper, sqlite3
from bs4 import BeautifulSoup

url = "https://pharmarecruiter.in/walk-in-interview-for-pharma-jobs-at-verve-human-care-laboratories-dehradun-qa-qc-production-roles/"
html = scraper.fetch(url)

if html:
    soup = BeautifulSoup(html, "lxml")
    
    print("--- OG Image ---")
    og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    print("og:image content:", og["content"] if og else None)
    
    print("\n--- Featured / Thumbnail Images ---")
    for sel in [".post-thumbnail img", ".featured-media img", "article img", ".single-featured-image-header img"]:
        for img in soup.select(sel):
            print(sel, "->", img.get("src"), "| data-src:", img.get("data-src"), "| data-orig-file:", img.get("data-orig-file"))

    print("\n--- Current parse_detail_page result ---")
    parsed = scraper.parse_detail_page(html)
    print("Current banner_url:", parsed.get("extra", {}).get("banner_url"))
