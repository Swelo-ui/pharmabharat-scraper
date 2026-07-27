import scraper
from bs4 import BeautifulSoup

url = "https://pharmabharat.com/harris-is-hiring-process-associate-freshers/"
html = scraper.fetch(url)
soup = BeautifulSoup(html, "lxml")
container = scraper._find_content_container(soup)

print("Container tag:", container.name, container.get("class"))
imgs = container.find_all("img")
print("Found IMGs in container:", len(imgs))
for i in imgs:
    print("IMG attrs:", i.attrs)

parsed = scraper.parse_detail_page(html)
print("Parsed banner_url:", parsed.get("banner_url"))
