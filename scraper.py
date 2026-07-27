"""
scraper.py -- PharmaBharat.com se job listings nikalne ka core logic.

DESIGN NOTE (important, README bhi padhna):
Website ka raw HTML abhi maine seedha nahi dekha (mere tools HTML ko
markdown mein convert kar dete hain, exact CSS class names chala nahi
pata). Isliye yeh parser CSS classes par depend NAHI karta -- iski
jagah text-pattern / structural heuristics use karta hai:

  - Har job card mein ek "Apply Now" link hota hai -> hum usse card
    dhoondte hain, phir uske parent container ka text nikaal ke
    regex se company / experience / date / salary / application-type
    match karte hain.
  - Job detail page par headings ek consistent pattern follow karte
    hain (# Job Overview, # Educational Qualification, # Salary, etc)
    -> hum poora content markdown mein convert karke un headings se
    section-wise split karte hain.

Agar site ka design badal jaye ya extraction galat lage, sabse pehle
`debug_dump()` function chalao (niche diya hai) -- woh raw parsed
output print karega taaki tum patterns ko tweak kar sako.

ETHICAL / LEGAL NOTE: PharmaBharat.com ki Terms & Conditions automated
scraping ko explicitly prohibit karti hain. Yeh script sirf PERSONAL,
low-frequency use ke liye hai. Rate-limit (delay) kam mat karo, aur
isse public/commercial product mat banao.
"""

import re
import time
import random
import logging

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("scraper")

BASE_URL = "https://pharmabharat.com"
PR_BASE_URL = "https://pharmarecruiter.in/freshers-jobs/"

# List of realistic Browser User-Agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
]


def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

# Category slugs taken from the site's own nav menu. Add/remove as needed.
CATEGORY_SLUGS = [
    "internships",
    "clinical-data-management-jobs",
    "clinical-research-jobs",
    "medical-writer-jobs",
    "tmf",
    "medical-coding-jobs",
    "packaging-jobs",
    "pharmacovigilance-jobs",
    "production-jobs",
    "quality-assurance-jobs",
    "quality-control-jobs",
    "regulatory-affairs-jobs",
    "research-and-development-jobs",
    "warehouse-jobs",
    "Government-jobs",
    "sas",
    "data-analyst",
    "medical-science-liaison-jobs",
    "medical-reviewer",
    "heor-rwe",
    "scientific-writer-jobs",
    # "college-faculty-jobs",  # returns 404 - removed
]

from datetime import datetime, timedelta

APPLICATION_TYPES = [
    "Virtual Interview", "Virtual Walk-In", "Online Interview", "Video Interview", "Telephonic Interview",
    "Walk In Interview", "Walk-In Interview", "Walkin Interview",
    "Email Application", "Online Application",
]

VIRTUAL_KEYWORDS = [
    "virtual interview", "virtual walk", "online interview", "video interview",
    "telephonic interview", "teams interview", "zoom interview", "google meet interview"
]

DATE_RE = re.compile(r"\b[A-Z][a-z]+ \d{1,2},? \d{4}\b")
EXPERIENCE_RE = re.compile(
    r"(?i)\b(freshers?|\d+\s*[-–—]\s*\d+\+?\s*years?|\d+\+?\s*years?)\b"
)
# Tightened: must have digit + unit (LPA / per month / lakhs / /-) OR a number >= 4 digits
SALARY_RE = re.compile(
    r"(₹|Rs\.?|INR)\s*[\d,.\s\-–—]+(?:LPA|per\s*month|/-|lakhs?|pa|p\.a\.?)",
    re.I
)
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b|\b[6-9]\d{9}\b")

# Known Indian cities / pharma hub locations for listing-page extraction
LOCATION_KEYWORDS = {
    "mumbai", "pune", "hyderabad", "bangalore", "bengaluru", "chennai",
    "delhi", "new delhi", "noida", "gurgaon", "gurugram", "ahmedabad",
    "kolkata", "vadodara", "baroda", "surat", "nagpur", "thane", "navi mumbai",
    "ankleshwar", "vapi", "baddi", "haridwar", "rishikesh", "chandigarh",
    "lucknow", "jaipur", "indore", "bhopal", "vizag", "visakhapatnam",
    "remote", "work from home", "wfh", "pan india", "across india",
    "multiple locations", "india",
}

# Patterns that clearly indicate NOT a company name
_NOT_COMPANY_RE = re.compile(
    r"(?i)^(freshers?|\d[\d\s\-–—+]*years?|apply|walk[\-\s]?in|online|email|"
    r"verified|immediate|urgent|[A-Z][a-z]+ \d{1,2},? \d{4}|₹|Rs|INR)",
    re.I
)

# Note: "verified" is NOT in this noise list on purpose -- we need to see that
# text in the line-matching loop below to detect the Verified badge.
NOISE_WORDS = {"apply now", "ad", "advertisement"}


def is_date_expired(date_str, text_content=None, is_walkin=False):
    """
    Smart Event Date Expiration Checker:
    1. Extracts exact walk-in event dates/ranges (e.g., '28-07-2026 to 31-07-2026' or '22/07/2026').
       If the last day of the walk-in event has passed (end_date < today), returns True (Expired).
    2. If no event date range found, checks posted date age. Posts > 30 days old are expired.
    """
    today = datetime.now().date()

    if text_content:
        # Match date ranges like '28-07-2026 to 31-07-2026' or '28/07/2026 - 31/07/2026'
        range_match = re.search(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\s*(?:to|\-)\s*(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', text_content)
        if range_match:
            try:
                d, m, y = int(range_match.group(4)), int(range_match.group(5)), int(range_match.group(6))
                end_date = datetime(y, m, d).date()
                if end_date < today:
                    return True
                else:
                    return False  # Event is still active or upcoming!
            except Exception:
                pass

        # Match single dates like '22-07-2026' or '22/07/2026' in text_content
        single_dates = re.findall(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', text_content)
        if single_dates:
            latest_date = None
            for d_str, m_str, y_str in single_dates:
                try:
                    dt = datetime(int(y_str), int(m_str), int(d_str)).date()
                    if latest_date is None or dt > latest_date:
                        latest_date = dt
                except Exception:
                    pass
            if latest_date and latest_date < today:
                return True

    # Check posted date age (general jobs older than 30 days are expired)
    if date_str:
        try:
            clean_str = date_str.replace(",", "").strip()
            p_dt = datetime.strptime(clean_str, "%B %d %Y").date()
            if (today - p_dt).days > 30:
                return True
        except Exception:
            pass

    return False


def _sleep(base_delay):
    # thoda randomness taaki request pattern robotic na lage
    time.sleep(base_delay + random.uniform(0.3, 1.2))


def fetch(url, retries=3, delay=1.5):
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=get_random_headers(), timeout=15)
            if resp.status_code == 200:
                return resp.text
            log.warning("Status %s for %s (attempt %s)", resp.status_code, url, attempt)
            if resp.status_code == 404:
                return None  # Don't retry 404s
        except requests.RequestException as e:
            log.warning("Error fetching %s: %s (attempt %s)", url, e, attempt)
        time.sleep(delay * attempt + random.uniform(0.2, 0.8))
    return None


def _clean_lines(container):
    lines = []
    for s in container.stripped_strings:
        s = s.strip()
        if not s or s.lower() in NOISE_WORDS:
            continue
        if s.lower().endswith("icon"):  # image alt-text jaise "Sun icon"
            continue
        lines.append(s)
    return lines


def _slug_from_url(url):
    return url.rstrip("/").split("/")[-1]


def _is_likely_company(text):
    """Heuristic: is this text a company name vs noise?"""
    if not text or len(text) < 2:
        return False
    if _NOT_COMPANY_RE.match(text):
        return False
    # Must have at least one letter
    if not re.search(r"[a-zA-Z]", text):
        return False
    return True


def _extract_location(lines):
    """Try to find a location from remaining lines using city keyword matching."""
    for line in lines:
        lower = line.lower()
        for kw in LOCATION_KEYWORDS:
            if kw in lower:
                return line.strip()
    return None


def parse_listing_page(html, category=None):
    """Ek listing page (homepage ya category page) se job cards nikalta hai."""
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    jobs = []
    seen_hrefs = set()

    apply_links = [a for a in soup.find_all("a") if a.get_text(strip=True) == "Apply Now"]

    for apply_a in apply_links:
        href = apply_a.get("href")
        if not href or href in seen_hrefs:
            continue
        
        clean_href = href.rstrip("/").lower()
        if clean_href in ["https://pharmabharat.com", "https://pharmarecruiter.in", "http://pharmabharat.com", "http://pharmarecruiter.in"]:
            continue
            
        seen_hrefs.add(href)

        # parent container dhoondo jisme title + meta dono hon
        container = apply_a
        for _ in range(6):
            if container.parent is None:
                break
            container = container.parent
            text_len = len(container.get_text(strip=True))
            if 40 <= text_len <= 700:
                break

        # title: same href wala doosra <a> jiska text "Apply Now" nahi hai
        title = None
        for a in container.find_all("a", href=href):
            t = a.get_text(strip=True)
            if t and t != "Apply Now":
                title = t
                break

        if title:
            t_upper = title.upper()
            if "JOB PORTAL" in t_upper or "PHARMABHARATPHARMACEUTICAL" in t_upper or t_upper in ["PHARMA BHARAT", "PHARMABHARAT"]:
                continue

        lines = _clean_lines(container)

        date_match = None
        experience = None
        salary = None
        app_type = None
        verified = False
        email_found = None
        phone_found = None
        location_found = None
        remaining = []

        container_text = " ".join(lines)
        email_m = EMAIL_RE.search(container_text)
        if email_m:
            email_found = email_m.group()
        phone_m = PHONE_RE.search(container_text)
        if phone_m:
            phone_found = phone_m.group()

        for line in lines:
            if line == title:
                continue
            if not date_match and DATE_RE.search(line):
                date_match = DATE_RE.search(line).group()
                continue
            lower_line = line.lower()
            if not app_type:
                for vk in VIRTUAL_KEYWORDS:
                    if vk in lower_line:
                        app_type = "Virtual Interview"
                        break
            if not app_type and line in APPLICATION_TYPES:
                app_type = line
                continue
            if "verified" in line.lower():
                verified = True
                continue
            if not experience and EXPERIENCE_RE.fullmatch(line.strip()):
                experience = line.strip()
                continue
            if not salary and SALARY_RE.search(line):
                salary = line.strip()
                continue
            remaining.append(line)

        # Skip expired jobs (walk-in interview event date passed or posted > 30 days ago)
        is_walkin = bool(app_type and "walk" in app_type.lower())
        if is_date_expired(date_match, text_content=container_text, is_walkin=is_walkin):
            log.info("Skipping expired job (%s): %s", date_match, title or href)
            continue

        # Company: first remaining line that passes company heuristic
        company = None
        for r in remaining:
            if _is_likely_company(r):
                company = r
                break

        # Sanitize text fields (remove &amp;, &#8211;, \ufffd replacement chars)
        def _sanitize(txt):
            if not txt:
                return txt
            import html
            txt = html.unescape(txt)
            txt = txt.replace('\ufffd', ' - ').replace('–', ' - ').replace('—', ' - ')
            txt = re.sub(r'\s*\-\s*', ' - ', txt)
            txt = re.sub(r'\s+', ' ', txt).strip()
            return txt

        title = _sanitize(title)
        company = _sanitize(company)
        location_found = _sanitize(location_found)
        experience = _sanitize(experience)

        is_fresher = bool(re.search(r"(?i)\bfreshers?\b", experience or ""))
        is_fresher_friendly = is_fresher or bool(re.match(r"^\s*0\s*[-–—]", experience or ""))

        slug = _slug_from_url(href)
        jobs.append({
            "slug": slug,
            "url": href if href.startswith("http") else BASE_URL + href,
            "title": title,
            "company": company,
            "category": category,
            "experience_raw": experience,
            "is_fresher": is_fresher,
            "is_fresher_friendly": is_fresher_friendly,
            "salary": salary,
            "location": location_found,
            "application_type": app_type,
            "verified": verified,
            "posted_date_raw": date_match,
            "email": email_found,
            "phone": phone_found,
        })

    return jobs


CONTENT_SELECTORS = [
    "article .entry-content",
    ".entry-content",
    ".post-content",
    ".single-content",
    "article",
    "main",
]


def _find_content_container(soup):
    for sel in CONTENT_SELECTORS:
        node = soup.select_one(sel)
        if node and len(node.get_text(strip=True)) > 200:
            return node
    return soup.body or soup


def parse_detail_page(html):
    """Job detail page se poora structured data nikalta hai (deep scrape)."""
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")
    container = _find_content_container(soup)

    # WordPress / Jetpack / LiteSpeed Lazy-Loading Image Pre-Processor
    if container:
        for img in container.find_all("img"):
            real_src = None
            for attr in ["data-full-url", "data-orig-file", "data-lazy-src", "data-src", "data-large-file", "src"]:
                val = img.get(attr)
                if val and isinstance(val, str) and not val.strip().startswith("data:"):
                    real_src = val.strip()
                    break

            if real_src:
                img["src"] = real_src

    # Extract Job Banner Image with Source-Aware Priority Logic
    banner_url = None
    og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"}) or soup.find("meta", attrs={"name": "twitter:image"})
    if og_img and og_img.get("content"):
        c_url = og_img["content"].strip()
        # Filter out site logos and generic PharmaBharat site template banners (e.g., Pharma-jobs-2026-...)
        is_generic_placeholder = any(x in c_url.lower() for x in ["logo", "favicon", "default-avatar", "placeholder", "header-logo", "brand-logo", "cropped-logo", "pharma-jobs-2026", "pharma-jobs-2"])
        if c_url and not c_url.startswith("data:") and not is_generic_placeholder:
            banner_url = c_url

    # Fallback to first real non-logo flyer image in container if no valid og:image
    if not banner_url and container:
        for img in container.find_all("img"):
            src_val = img.get("src")
            if src_val and not src_val.startswith("data:"):
                src_val = src_val.strip()
                is_logo_or_small = any(x in src_val.lower() for x in ["logo", "favicon", "placeholder", "default-avatar", "avatar", "header-logo", "brand-logo", "vector-", "200x200"])
                if not is_logo_or_small:
                    banner_url = src_val
                    break

    # REMOVE ALL AD ELEMENTS, IFRAMES, TABLE OF CONTENTS (TOC), AND SCRIPT BLOCKS BEFORE CONVERTING TO MARKDOWN
    ad_selectors = [
        "ins", "iframe", "script", "style", ".adsbygoogle", ".ad", ".ads",
        ".advertisement", ".sharedaddy", ".wp-block-embed", ".code-block",
        "div[class*='ad-']", "div[class*='ads']", ".jp-relatedposts",
        "#toc_container", ".toc_container", ".ez-toc-container", ".ez-toc-v2_0_69",
        "#ez-toc-container", "div[id*='toc']", "div[class*='toc']", ".table-of-contents",
        "nav[class*='toc']", ".ez-toc-title-container", ".ez-toc-widget-container"
    ]
    for sel in ad_selectors:
        for tag in container.select(sel):
            tag.decompose()

    # Decode Cloudflare Obfuscated Email Protection in container
    def decode_cf_email(hex_str):
        try:
            key = int(hex_str[:2], 16)
            return "".join(chr(int(hex_str[i:i+2], 16) ^ key) for i in range(2, len(hex_str), 2))
        except Exception:
            return ""

    if container:
        for tag in container.find_all(attrs={"data-cfemail": True}):
            cfemail = tag.get("data-cfemail")
            if cfemail:
                decoded = decode_cf_email(cfemail)
                if decoded:
                    tag.string = decoded
                    if tag.name == "a":
                        tag["href"] = f"mailto:{decoded}"

    markdown = md(str(container), heading_style="ATX")
    # Clean TOC table of contents markdown block if present
    markdown = re.sub(r"(?i)\n*#*\s*Contents\s*\n+(\s*[\*\-]\s*\[?\d+\.?\d*.*?\]?\(#.*?\)\s*\n?)+", "\n\n", markdown)
    markdown = re.sub(r"(?i)\n*#*\s*Contents\s*\n+(\s*\d+\.\s*\[?.*?\]?\(#.*?\)\s*\n?)+", "\n\n", markdown)

    # trailing share/ad/related-jobs section hata do agar mila
    cut_markers = ["Share This Job", "RECENT JOBS", "Advertisement", "Related Jobs"]
    for marker in cut_markers:
        idx = markdown.find(marker)
        if idx != -1:
            markdown = markdown[:idx]

    # "Job Overview" table se key-value pairs nikalo
    overview = {}
    table_match = re.search(
        r"#+\s*Job Overview(.*?)(?=\n#+\s|\Z)", markdown, re.S | re.I
    )
    if table_match:
        for row in re.findall(r"\|\s*([^|\n]+?)\s*\|\s*([^|\n]+?)\s*\|", table_match.group(1)):
            key, val = row[0].strip().lower(), row[1].strip()
            if key and "particular" not in key and "detail" not in key:
                overview[key] = val

    email_m = EMAIL_RE.search(markdown)
    phone_m = PHONE_RE.search(markdown)

    extra = {
        "location": overview.get("job location") or overview.get("location"),
        "salary": None,
        "experience_raw": overview.get("experience"),
        "email": email_m.group() if email_m else None,
        "phone": phone_m.group() if phone_m else None,
        "banner_url": banner_url,
    }

    salary_match = re.search(r"#+\s*Salary(.*?)(?=\n#+\s|\Z)", markdown, re.S | re.I)
    if salary_match:
        m = SALARY_RE.search(salary_match.group(1))
        if m:
            extra["salary"] = m.group().strip()

    return {"description_md": markdown.strip(), "extra": extra}


# Track categories that 404'd in the current run — skip retrying them
_dead_categories: set = set()


def scrape_recent(pages=1, delay=1.2, deep=True, progress_cb=None):
    """
    Homepage + har category ka pehla `pages` page scan karta hai --
    naye jobs pakadne ke liye. Yeh function baar-baar (e.g. har 30-60
    min) chalao monitoring ke liye.

    progress_cb: optional callable(scraped_so_far, new_so_far, category, categories_done)
    Returns: list of slugs jo NAYE the (is run mein pehli baar dikhe).
    """
    db.init_db()
    new_slugs = []
    scraped_count = 0
    categories_done = 0

    targets = [(None, BASE_URL)] + [
        (cat, f"{BASE_URL}/category/{cat}/") for cat in CATEGORY_SLUGS
        if cat not in _dead_categories
    ]

    for category, base in targets:
        cat_label = category or "homepage"
        # Notify frontend which category we're starting
        if progress_cb:
            progress_cb(scraped_count, len(new_slugs), cat_label, categories_done)

        for page in range(1, pages + 1):
            url = base if page == 1 else f"{base.rstrip('/')}/page/{page}/"
            html = fetch(url)
            if not html:
                if category:
                    log.warning("Skipping dead category: %s", category)
                    _dead_categories.add(category)
                continue
            for job in parse_listing_page(html, category=category):
                scraped_count += 1
                is_new = db.upsert_job(job)
                if is_new:
                    new_slugs.append(job["slug"])
                    log.info("NEW job: %s (%s)", job["title"], job["url"])
                    if deep:
                        _sleep(delay)
                        detail_html = fetch(job["url"])
                        parsed = parse_detail_page(detail_html)
                        if parsed:
                            db.update_detail(job["slug"], parsed["description_md"], parsed["extra"])
                if progress_cb:
                    progress_cb(scraped_count, len(new_slugs), cat_label, categories_done)
            _sleep(delay)

        categories_done += 1
        if progress_cb:
            progress_cb(scraped_count, len(new_slugs), cat_label, categories_done)

    return new_slugs


def scrape_full(max_pages=764, delay=2.5, deep=False, category=None):
    """
    Poori site ka historical crawl (default: sabhi 764 pages). Bahut
    zyada requests karega -- delay kam mat karo. `deep=True` har job
    ka detail page bhi fetch karega (bahut slow hoga, 11000+ jobs).
    """
    db.init_db()
    cats = [category] if category else [None] + CATEGORY_SLUGS
    total_new = 0

    for cat in cats:
        base = BASE_URL if cat is None else f"{BASE_URL}/category/{cat}/"
        for page in range(1, max_pages + 1):
            url = base if page == 1 else f"{base.rstrip('/')}/page/{page}/"
            html = fetch(url)
            if not html:
                log.info("Stopping category=%s at page=%s (fetch failed)", cat, page)
                break
            jobs = parse_listing_page(html, category=cat)
            if not jobs:
                log.info("Stopping category=%s at page=%s (no jobs found)", cat, page)
                break
            for job in jobs:
                is_new = db.upsert_job(job)
                if is_new:
                    total_new += 1
                    if deep:
                        _sleep(delay)
                        detail_html = fetch(job["url"])
                        parsed = parse_detail_page(detail_html)
                        if parsed:
                            db.update_detail(job["slug"], parsed["description_md"], parsed["extra"])
            log.info("category=%s page=%s -> %s jobs (total new so far: %s)",
                      cat, page, len(jobs), total_new)
            _sleep(delay)

    return total_new


# ─── PharmaRecruiter.in Scraper ────────────────────────────────────────────────

# WordPress category-to-slug mapping for pharmarecruiter.in CSS classes
_PR_CAT_MAP = {
    "category-walk-in-interviews": "walk-in-interviews",
    "category-pharmacovigilance-jobs": "pharmacovigilance-jobs",
    "category-qc-jobs": "quality-control-jobs",
    "category-qa-jobs": "quality-assurance-jobs",
    "category-clinical-research-jobs": "clinical-research-jobs",
    "category-rd-jobs": "research-and-development-jobs",
    "category-medical-coding-jobs": "medical-coding-jobs",
    "category-regulatory-affairs-jobs": "regulatory-affairs-jobs",
    "category-production-jobs": "production-jobs",
    "category-internship": "internships",
}


def _pr_extract_category(article_classes: list) -> str | None:
    """WordPress article CSS classes se category string nikalo."""
    for cls in article_classes:
        if cls in _PR_CAT_MAP:
            return _PR_CAT_MAP[cls]
    # fallback: koi bhi category- class
    for cls in article_classes:
        if cls.startswith("category-") and cls not in ("category-jobs", "category-freshers-jobs"):
            return cls.replace("category-", "").replace("-", " ").title()
    return "freshers-jobs"


def _pr_company_from_title(title: str) -> str | None:
    """Title se company name extract karne ki heuristic."""
    if not title:
        return None
    # Patterns like: "Jobs at XYZ Pharma", "XYZ Pharma Walk-In", etc.
    patterns = [
        r"(?:Jobs?\s+at|Hiring(?:\s+at)?|Walk-[Ii]n\s+(?:Interview\s+)?at|Opening(?:s)?\s+at)\s+([A-Z][\w\s&().,'\-]+?)(?:\s*[-|–—]|\s+for\s|\s+in\s|\s+Pharma|\s+Walk|$)",
        r"^([A-Z][\w\s&().,']+?)\s+(?:Walk-[Ii]n|Job|Hiring|Opening|Intern|Recruit|Drive)",
    ]
    for pat in patterns:
        m = re.search(pat, title)
        if m:
            cname = m.group(1).strip().rstrip(",;:")
            if len(cname) >= 3 and _is_likely_company(cname):
                return cname
    return None


def parse_pr_listing_page(html, source="pharmarecruiter"):
    """
    PharmaRecruiter.in ka WordPress listing page parse karta hai.
    Each <article> tag ek job hai:
      - Title:   h2.entry-title > a (text + href)
      - Date:    time.entry-date[datetime]
      - Banner:  div.post-image img
      - Category: article CSS classes
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    jobs = []
    seen_hrefs = set()

    articles = soup.find_all("article")
    for article in articles:
        # Title & URL
        title_tag = article.select_one("h2.entry-title a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        href = title_tag.get("href", "")
        if not href or href in seen_hrefs:
            continue
        # Skip if empty or not a real post URL
        if not href.startswith("http"):
            continue
        seen_hrefs.add(href)

        # Date
        time_tag = article.select_one("time.entry-date")
        date_raw = None
        if time_tag:
            dt_attr = time_tag.get("datetime", "")
            # datetime attr format: 2026-07-25T10:52:55+05:30 → parse to "Month DD, YYYY"
            try:
                from datetime import datetime as _dt
                d = _dt.fromisoformat(dt_attr[:19])
                date_raw = d.strftime("%B %d, %Y")
            except Exception:
                date_raw = time_tag.get_text(strip=True)

        # Banner image
        banner_url = None
        post_img_div = article.select_one("div.post-image img")
        if post_img_div:
            banner_url = (
                post_img_div.get("data-full-url") or
                post_img_div.get("data-orig-file") or
                post_img_div.get("data-lazy-src") or
                post_img_div.get("data-src") or
                post_img_div.get("src")
            )
            if banner_url:
                # Try to get largest image from srcset
                srcset = post_img_div.get("srcset", "")
                if srcset:
                    # Pick the last (largest) entry from srcset
                    parts = [p.strip().split(" ") for p in srcset.split(",") if p.strip()]
                    if parts:
                        # Find the largest width
                        best = None
                        best_w = 0
                        for p in parts:
                            if len(p) >= 2:
                                try:
                                    w = int(p[1].rstrip("w"))
                                    if w > best_w:
                                        best_w = w
                                        best = p[0]
                                except Exception:
                                    pass
                        if best:
                            banner_url = best

        # Category
        article_classes = article.get("class", [])
        category = _pr_extract_category(article_classes)

        # Walk-in detection from title/category
        title_lower = title.lower()
        app_type = None
        is_walkin = (
            "walk-in" in title_lower or "walk in" in title_lower or
            "walkin" in title_lower or
            category == "walk-in-interviews"
        )
        if is_walkin:
            app_type = "Walk In Interview"

        # Fresher detection from title
        is_fresher = bool(re.search(r"(?i)\bfreshers?\b", title))
        is_fresher_friendly = is_fresher

        # Company heuristic from title
        company = _pr_company_from_title(title)

        # Location from title
        location_found = None
        title_lower_str = title.lower()
        for kw in LOCATION_KEYWORDS:
            if kw in title_lower_str:
                location_found = kw.title()
                break

        # Skip expired jobs
        # Note: date_raw is the POST published date, not the walk-in event date.
        # Use 30-day rule for all PR jobs to avoid skipping recently-posted walk-in listings.
        if is_date_expired(date_raw.replace(",", "") if date_raw else None, is_walkin=False):
            log.info("PR: Skipping expired job (%s): %s", date_raw, title)
            continue

        slug = _slug_from_url(href)
        # Prefix slug with 'pr-' to avoid collisions with pharmabharat slugs
        if not slug.startswith("pr-"):
            slug = f"pr-{slug}"

        jobs.append({
            "slug": slug,
            "url": href,
            "title": title,
            "company": company,
            "category": category,
            "experience_raw": None,
            "is_fresher": is_fresher,
            "is_fresher_friendly": is_fresher_friendly,
            "salary": None,
            "location": location_found,
            "application_type": app_type,
            "verified": False,
            "posted_date_raw": date_raw,
            "email": None,
            "phone": None,
            "banner_url": banner_url,
            "source": source,
        })

    return jobs


# Track dead PR pages in current run
_pr_dead_pages: set = set()


PR_CATEGORIES = [
    "",  # Homepage (all recent posts)
    "category/walk-in-interviews/",
    "category/freshers-jobs/",
    "category/qc-jobs/",
    "category/qa-jobs/",
    "category/production-jobs/",
    "category/rd-jobs/",
    "category/pharmacovigilance-jobs/",
]


def scrape_pr_recent(pages=1, delay=1.5, deep=True, progress_cb=None):
    """
    PharmaRecruiter.in ka homepage aur saare main category sections scrape karta hai.
    Returns: list of new slugs.
    """
    db.init_db()
    new_slugs = []
    scraped_count = 0

    pr_base = "https://pharmarecruiter.in"

    for cat_path in PR_CATEGORIES:
        base_cat_url = f"{pr_base}/{cat_path}" if cat_path else pr_base
        for page in range(1, pages + 1):
            if page == 1:
                url = base_cat_url
            else:
                url = f"{base_cat_url.rstrip('/')}/page/{page}/"

            html = fetch(url)
            if not html:
                log.warning("PR: fetch failed for %s", url)
                break

            jobs = parse_pr_listing_page(html)
            if not jobs:
                log.info("PR: No jobs found on %s, skipping.", url)
                break

            for job in jobs:
                scraped_count += 1
                is_new = db.upsert_job(job)
                if is_new:
                    new_slugs.append(job["slug"])
                    log.info("PR NEW job: %s (%s)", job["title"], job["url"])
                    if deep:
                        _sleep(delay)
                        detail_html = fetch(job["url"])
                        parsed = parse_detail_page(detail_html)
                        if parsed:
                            db.update_detail(job["slug"], parsed["description_md"], parsed["extra"])
                if progress_cb:
                    progress_cb(scraped_count, len(new_slugs), "pharmarecruiter", 0)
            _sleep(delay)

    return new_slugs


def scrape_all_recent(pages=1, delay=1.2, deep=True, progress_cb=None):
    """
    Dono sites (PharmaBharat + PharmaRecruiter) scrape karta hai.
    Deduplication DB level par automatically hoti hai (title match).
    Returns: combined list of new slugs.
    """
    # PharmaBharat scrape
    pb_new = scrape_recent(pages=pages, delay=delay, deep=deep, progress_cb=progress_cb)
    # PharmaRecruiter scrape (freshers page)
    pr_new = scrape_pr_recent(pages=pages, delay=delay, deep=deep, progress_cb=progress_cb)
    return pb_new + pr_new


def debug_dump(url=BASE_URL):
    """Ek page fetch karke raw parsed jobs print karta hai -- selectors/
    regex tweak karne ke liye use karo agar extraction sahi na lage."""
    html = fetch(url)
    jobs = parse_listing_page(html)
    for j in jobs:
        print(j)
    print(f"\nTotal parsed: {len(jobs)}")


def debug_dump_pr(url=PR_BASE_URL):
    """PharmaRecruiter.in ka ek page fetch karke raw parsed jobs print karta hai."""
    html = fetch(url)
    jobs = parse_pr_listing_page(html)
    for j in jobs:
        print(j)
    print(f"\nTotal parsed: {len(jobs)}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        debug_dump()
    elif len(sys.argv) > 1 and sys.argv[1] == "debug_pr":
        debug_dump_pr()
    elif len(sys.argv) > 1 and sys.argv[1] == "full":
        n = scrape_full()
        print(f"Full scrape done. New jobs: {n}")
    else:
        n = scrape_all_recent(pages=2)
        print(f"Recent scrape done (both sites). New jobs: {len(n)}")
