import scraper
from bs4 import BeautifulSoup

url = "https://pharmabharat.com/harris-is-hiring-process-associate-freshers/"
html = scraper.fetch(url)
soup = BeautifulSoup(html, "lxml")

print("--- OG Image ---")
og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
print(og)

print("\n--- Content Container IMGs ---")
container = scraper._find_content_container(soup)
if container:
    for img in container.find_all("img"):
        print(img.attrs)

print("\n--- All IMGs on Page ---")
for img in soup.find_all("img")[:10]:
    print(img.attrs)
