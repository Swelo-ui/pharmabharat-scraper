import sqlite3, scraper

# Fetch listing from pharmabharat.com homepage
html = scraper.fetch("https://pharmabharat.com/", retries=2)
jobs = scraper.parse_listing_page(html)

print("Found PharmaBharat listing jobs:", len(jobs))
for j in jobs[:5]:
    print("Title:", j["title"])
    print("URL:", j["url"])
    # Deep scrape detail page
    d_html = scraper.fetch(j["url"])
    if d_html:
        detail = scraper.parse_detail_page(d_html)
        print("  - Banner URL:", detail.get("banner_url") if detail else None)
        print("  - Extra:", detail.get("extra") if detail else None)
    print("="*40)
