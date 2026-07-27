import scraper

url = "https://pharmabharat.com/harris-is-hiring-process-associate-freshers/"
html = scraper.fetch(url)
parsed = scraper.parse_detail_page(html)

print("Parsed Banner URL:", parsed.get("banner_url"))
print("Desc Markdown Snippet:")
print((parsed.get("description_md") or "")[:500].encode('ascii', 'ignore').decode('ascii'))
