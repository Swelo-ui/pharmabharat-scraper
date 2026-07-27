import scraper

html = scraper.fetch("https://pharmabharat.com/")
jobs = scraper.parse_listing_page(html)

print(f"Scraped {len(jobs)} posts from PharmaBharat homepage.")

with_banners = 0
for j in jobs:
    d_html = scraper.fetch(j["url"])
    if d_html:
        parsed = scraper.parse_detail_page(d_html)
        b_url = parsed.get("banner_url") if parsed else None
        if b_url:
            with_banners += 1
            print(f"  ✓ {j['title'][:40]} -> {b_url}")

print(f"\nTotal with Banners: {with_banners}/{len(jobs)}")
