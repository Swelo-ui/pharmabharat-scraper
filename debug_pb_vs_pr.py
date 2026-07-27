import scraper
from bs4 import BeautifulSoup

pb_url = "https://pharmabharat.com/gufic-biosciences-ltd-hiring-qa-qc-professionals/"
pr_url = "https://pharmarecruiter.in/walk-in-interview-for-pharma-jobs-at-verve-human-care-laboratories-dehradun-qa-qc-production-roles/"

for name, u in [("PharmaBharat", pb_url), ("PharmaRecruiter", pr_url)]:
    html = scraper.fetch(u)
    if html:
        soup = BeautifulSoup(html, "lxml")
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
        print(f"=== {name} ===")
        print("og:image:", og["content"] if og else None)
        container = scraper._find_content_container(soup)
        if container:
            for img in container.find_all("img")[:3]:
                print("Container img:", img.get("src") or img.get("data-src"))
