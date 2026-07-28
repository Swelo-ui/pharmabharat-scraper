# 🛠️ Walkthrough — Real-Time Telegram Channel Job Scraper & Listener

Implemented a real-time Telegram Channel Job Scraper & Listener (`telegram_scraper.py`) that monitors the official Telegram public channels of **PharmaBharat** (`t.me/s/Pharma_bharat`) and **PharmaRecruiter** (`t.me/s/pharma_recruiter`).

When a new job link is posted on either Telegram channel:
1. Extracts the job URL.
2. Performs a deep detail scrape to parse full metadata (Title, Company, Category, Location, Experience, Salary, Banner Image, Email/Phone).
3. Executes our **High-Precision 4-Field Verified Deduplication Engine** (verifying Brand, Role, Location, Experience).
4. Injects missing/new jobs into `jobs.db` with PharmaBharat preference.
5. Triggers an instant push broadcast alert to all Android app users via `trigger_internal_push_broadcast()`.

---

## 📑 Changes Made

### 1. Backend Telegram Scraper (`telegram_scraper.py`)
- Created `telegram_scraper.py` to parse public Telegram web preview channels (`t.me/s/<channel_username>`).
- Requires **zero API keys / zero third-party dependencies** and runs 100% free and automated 24/7 on the server.

### 2. 4-Field Verified Deduplication & DB Layer (`db.py`)
- Added `db.job_exists_by_slug(slug)` helper to check for existing job URLs.
- Linked extracted Telegram jobs to `db.upsert_job()`, enforcing 4-field verification (Company Brand + Job Role + Location + Experience Level).

### 3. Background Monitor & REST API (`monitor.py` & `app.py`)
- Updated `monitor.py` to include `telegram_scraper.scrape_telegram_channels()` in the 24x7 background loop.
- Added `/api/telegram/scrape` REST endpoint to trigger Telegram channel scraping on demand asynchronously.

---

## 🧪 Validation & Results

### 1. Telegram Channel Extraction Test
- Executed `python telegram_scraper.py` locally and verified live extraction from both channels:
  - `@Pharma_bharat` -> `https://pharmabharat.com/sandoz-hiring-regulatory-affairs-associate-documentation/`
  - `@pharma_recruiter` -> `https://pharmarecruiter.in/strides-walk-in-interview-in-chennai-pharma-jobs-for-osd-roles/`
- Deep-scraped full metadata and ran through deduplication engine without errors.

### 2. Live API & Cloud Server Verification
- Verified `https://pharmabharat-scraper.onrender.com/api/telegram/scrape` on Live Server:
  ```json
  {"message":"Telegram channel scrape triggered in background","status":"success"}
  ```
- All changes pushed and active on main branch!
