# 💊 Pharmly (v3.6.0) — AI-Powered Automated Pharma Job Aggregator & Android App

[![Latest Version](https://img.shields.io/badge/App%20Version-v3.6.0%20(Build%2010)-00C853?style=for-the-badge&logo=android&logoColor=white)](https://github.com/Swelo-ui/pharmabharat-scraper/raw/main/Pharmly.apk)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Android](https://img.shields.io/badge/Android%20App-Native%20Java-3DDC84?style=for-the-badge&logo=android&logoColor=white)](https://developer.android.com/)
[![Lucide Icons](https://img.shields.io/badge/UI%20Icons-Lucide%20SVG-FF6B6B?style=for-the-badge)](https://lucide.dev/)
[![Live App](https://img.shields.io/badge/Web%20App-Live%20Demo-00C853?style=for-the-badge&logo=render&logoColor=white)](https://pharmabharat-scraper-y2g3.onrender.com)

---

## 📌 Overview

**Pharmly** is an end-to-end automated pharmaceutical job aggregator, intelligence platform, and native Android application. It automatically scrapes, cleans, deduplicates, and tags fresh pharma job openings from multiple top recruitment web portals (**PharmaBharat.com** and **PharmaRecruiter.com**), storing them permanently in a single self-contained SQLite database (`jobs.db`).

The platform provides a responsive **Single-Page Web Application**, a **Flask REST API**, automated **Telegram/Android Background Alerts**, and a **Native Android App (APK)** featuring offline background sync capabilities via `AlarmManager` and `JobScheduler`.

---

## 📲 Download Native Android App (APK - v3.6.0)

Directly download and install the latest compiled APK on your Android device:

- 🚀 **[Download Pharmly.apk (GitHub Direct - v3.6.0)](https://github.com/Swelo-ui/pharmabharat-scraper/raw/main/Pharmly.apk)**
- 🌐 **[Download via Live Web Server](https://pharmabharat-scraper-y2g3.onrender.com/Pharmly.apk)**

---

## ✨ Key Features & Highlights in v3.6.0

- 🔋 **Native Doze-Bypass Push Notification Engine**:
  - Uses `AlarmManager.setAndAllowWhileIdle()` to bypass Android OS Doze Mode & Standby Buckets.
  - Checks for instant push notifications every 2 minutes in the background and immediately on app launch/resume.
  - Delivers High-Priority status bar notifications with native sound, vibration pattern, and big text preview even when the app is completely closed or screen is off.
- 🛡️ **High-Precision 4-Field Verified Smart Deduplication Engine**:
  - Eliminates duplicate job postings across sources by cross-verifying **Company Brand + Specific Job Role + City/State Location + Experience Required Level (`is_fresher` / `experience_raw`) + Recruitment Poster Image URL / Contact Info**.
  - **Zero False Duplicates**: Preserves different job openings at the same company (e.g., *Production vs Quality Control*, or *Fresher vs Senior* roles).
  - **PharmaBharat Priority Rule**: Gives primary preference to PharmaBharat job listings over duplicates.
- ⚡ **In-App Real-Time Downloader & FileProvider Auto-Installer**:
  - Features custom thread streaming downloader displaying live `0% → 100%` progress bar inside the WebView UI.
  - Integrated with Android `FileProvider` (`Intent.ACTION_VIEW` + `FLAG_GRANT_READ_URI_PERMISSION`) to automatically trigger the native Android Package Installer prompt upon 100% download completion.
- 🎓 **Smart Degree Eligibility Auto-Tagging**:
  - Automatically parses job descriptions to tag degree eligibility: `B.PHARM`, `M.PHARM`, `PHARM.D`, `D.PHARM`.
- 🎨 **Material You Single-Line Update Card & Real Logo**:
  - Ultra-clean, single-line update banner featuring official Pharmly logo image, version badge (`v3.6.0`), concise changelog, and compact `Update Now →` button.
- 📣 **Instant Broadcast Push API (`/api/push-broadcast`)**:
  - Dedicated REST endpoint for broadcasting high-priority custom notifications to all active Android app users.
- 🔑 **Persistent Release Keystore Signing**:
  - Signed with a 30-year production release keystore (`release.keystore`) for consistent developer certificate fingerprinting.

---

## 📁 Repository Structure & Directory Sitemap

```text
pharmabharat-scraper/
├── app.py                      # Flask REST API server, app versioning & push broadcast routes
├── db.py                       # SQLite database layer & 4-field smart deduplication engine
├── scraper.py                  # HTML parsing engine (BeautifulSoup + regex) for PB & PR
├── monitor.py                  # 24x7 background monitor script with Telegram alerts
├── notifier.py                 # Telegram Bot API notification dispatcher
├── jobs.db                     # SQLite database file (DELETE journal mode, 0 WAL dependency)
├── requirements.txt            # Python dependencies (Flask, requests, beautifulsoup4)
├── Pharmly.apk                 # Latest compiled Release Android APK (v3.6.0, Code 10)
├── templates/
│   └── index.html              # Responsive Web UI (CSS Grid, Glassmorphism, In-App Progress Bar)
└── android-app/                # Native Android Studio Project
    ├── app/
    │   ├── build.gradle        # Gradle dependencies, versionCode 10 & versionName 3.6.0
    │   └── src/main/
    │       ├── AndroidManifest.xml # Permissions, FileProvider & Receiver declarations
    │       └── java/com/pharmabharat/app/
    │           ├── MainActivity.java     # WebView, JS Bridge, In-App Downloader & Instant Push Check
    │           ├── AlarmReceiver.java    # 2-Min Doze-Bypass background receiver & update checker
    │           ├── BootReceiver.java     # Device boot alarm scheduler
    │           └── NotificationHelper.java # High-Priority status bar notification builder
    └── gradlew.bat             # Windows Gradle wrapper build script
```

---

## 📄 Detailed File Descriptions

| File / Directory | Description & Purpose |
|---|---|
| 🐍 `app.py` | Main Flask web application. Serves `/api/jobs`, `/api/app-version`, `/api/push-broadcast`, manual scrape trigger, and Excel export. |
| 🗄️ `db.py` | SQLite DAL layer (`jobs.db`). Implements 4-Field Verified Smart Deduplication (`_is_duplicate_job`), degree detection, and chronological sorting. |
| 🕷️ `scraper.py` | Scraping engine using `requests` & `BeautifulSoup`. Parses listing pages and deep detail pages for both PharmaBharat & PharmaRecruiter. |
| 🔔 `android-app/` | Native Android Studio Project wrapper. Implements Doze-Bypass AlarmReceiver, FileProvider APK installer, and WebAppInterface JS bridge. |
| 🎨 `templates/index.html` | Premium dark/light responsive Web UI with Lucide vector icons, update modals, and live progress bar. |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- Android Studio / JDK 17+ (optional, only if building Android APK locally)

### 2. Local Setup & Web Server

```bash
# Clone the repository
git clone https://github.com/Swelo-ui/pharmabharat-scraper.git
cd pharmabharat-scraper

# Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run initial job scrape (Recent 2 pages)
python scraper.py

# Start Flask Development Server
python app.py
```
Open your browser and navigate to `http://localhost:5000`.

---

## 📡 API Endpoint Reference

| Endpoint | Method | Description | Query Parameters |
|---|---|---|---|
| `/api/jobs` | `GET` | Fetch paginated jobs list | `category`, `fresher_only`, `verified_only`, `degree`, `location`, `q`, `sort_by`, `page`, `per_page` |
| `/api/app-version` | `GET` | Fetch latest APK version details & changelog | — |
| `/api/push-broadcast` | `GET / POST` | Fetch or trigger instant push broadcast | `title`, `message`, `url` |
| `/api/job/<slug>` | `GET` | Fetch single job details | — |
| `/api/stats` | `GET` | Fetch dashboard metrics & last sync timestamp | — |
| `/api/categories` | `GET` | List distinct job categories | — |
| `/api/locations` | `GET` | List distinct job locations | — |
| `/api/scrape/trigger` | `POST` | Manually trigger a background scrape | `pages` (default: 1) |
| `/api/export` | `GET` | Export scraped jobs as Excel CSV | `degree`, `category`, `fresher_only` |

---

## 🛠️ Building the Android APK Locally

To compile the Release Android App locally using Gradle CLI:

```powershell
# Set Android SDK and Java Environment Variables (Windows PowerShell)
$env:ANDROID_HOME = "C:\Users\YOUR_USERNAME\AppData\Local\Android\Sdk"
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"

# Navigate to android-app directory
cd android-app

# Build Release APK
.\gradlew.bat assembleRelease
```
The compiled APK will be generated at:
`android-app/app/build/outputs/apk/release/app-release.apk`

---

## 📜 Legal & Fair Use Notice

This project was developed strictly for personal job search assistance and educational purposes. Scraping logic incorporates low-frequency requests with delays to minimize server impact. Always adhere to target website Terms of Service.

---

### 👨‍💻 Maintained with ❤️ by the Pharmly Team
