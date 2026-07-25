# 💊 PharmaBharat Pro — AI-Powered Automated Pharma Job Aggregator & Android App

[![Python Version](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Android](https://img.shields.io/badge/Android%20App-Native%20Java-3DDC84?style=for-the-badge&logo=android&logoColor=white)](https://developer.android.com/)
[![Lucide Icons](https://img.shields.io/badge/UI%20Icons-Lucide%20SVG-FF6B6B?style=for-the-badge)](https://lucide.dev/)
[![Live App](https://img.shields.io/badge/Web%20App-Live%20Demo-00C853?style=for-the-badge&logo=render&logoColor=white)](https://pharmabharat-scraper.onrender.com)

---

## 📌 Overview

**PharmaBharat Pro** is an end-to-end automated pharmaceutical job aggregator, intelligence platform, and native Android application. It automatically scrapes, cleans, deduplicates, and tags fresh pharma job openings from multiple top recruitment web portals (**PharmaBharat.com** and **PharmaRecruiter.com**), storing them permanently in a local SQLite database (`jobs.db`).

The platform provides a responsive **Single-Page Web Application**, a **Flask REST API**, automated **Telegram/Android Background Alerts**, and a **Native Android App (APK)** featuring offline background sync capabilities via `JobScheduler`.

---

## 📲 Download Native Android App (APK)

Directly download and install the latest compiled APK on your Android device:

- 🚀 **[Download PharmaBharatPro.apk (GitHub Direct)](https://github.com/Swelo-ui/pharmabharat-scraper/raw/main/PharmaBharatPro.apk)**
- 🌐 **[Download via Live Web Server](https://pharmabharat-scraper.onrender.com/PharmaBharatPro.apk)**

---

## ✨ Key Features & Highlights

- 🕷️ **Dual-Engine Scraping Core**: Deep-scrapes job title, company, location, experience range, salary, walk-in/interview status, contact email/phone, and HD recruitment banners from both **PharmaBharat** & **PharmaRecruiter**.
- 🎓 **Smart Degree Eligibility Auto-Tagging**: Automatically analyzes job descriptions to extract and tag degree eligibility:
  - 🎓 `B.PHARM` (Bachelor of Pharmacy)
  - 🎖️ `M.PHARM` (Master of Pharmacy)
  - 📖 `PHARM.D` (Doctor of Pharmacy)
  - 📜 `D.PHARM` (Diploma in Pharmacy)
- 🎨 **Modern 2x2 Segmented Filter UI**:
  - **Row 1 Quick Chips**: `All`, `Fresher`, `Verified`, `Saved` (No horizontal scrolling).
  - **Row 2 Symmetric 2x2 Trigger Buttons**: `All Categories`, `All Degrees`, `All Locations`, `Newest First`.
- ⚡ **Chronological Real-Time Sorting**: Jobs are strictly ordered by actual posting timestamp (`posted_timestamp`), bringing the newest opportunities to the top.
- 📱 **Native Android Integration**:
  - **Native Share Sheet**: Rich job sharing (*Position, Company, Location, Experience, Contact, Link*) directly into WhatsApp, Telegram, or System Chooser.
  - **Offline Background Sync**: Android system `JobScheduler` (`PharmaJobService`) checks for new jobs every 15 minutes even when the app is closed or phone reboots.
- 📑 **Full-Detail Excel Export**: Download all active scraped jobs with 15+ rich metadata columns in UTF-8 BOM Excel CSV format.
- 🔔 **Instant Telegram Alerts**: Automated bot notifications delivered straight to your Telegram channel.
- 🎨 **Strict Vector-Only Visual Design**: Built using 100% crisp Lucide SVG vector icons (Zero Emojis).

---

## 📁 Repository Structure & File Directory

```text
pharmabharat-scraper/
├── app.py                      # Flask REST API server & webapp routing
├── db.py                       # SQLite database access layer & degree detection logic
├── scraper.py                  # HTML parsing engine (BeautifulSoup + regex)
├── monitor.py                  # 24x7 background monitor script with Telegram alerts
├── notifier.py                 # Telegram Bot API notification dispatcher
├── jobs.db                     # SQLite database file storing scraped jobs & sync metadata
├── requirements.txt            # Python dependencies (Flask, requests, beautifulsoup4)
├── PharmaBharatPro.apk         # Compiled debug Android APK package
├── templates/
│   └── index.html              # Modern single-page web app UI (CSS + JS + Lucide Icons)
└── android-app/                # Native Android Studio Project
    ├── app/
    │   ├── build.gradle        # Gradle dependencies & APK build config
    │   └── src/main/
    │       ├── AndroidManifest.xml # Android permissions & JobScheduler service declaration
    │       └── java/com/pharmabharat/app/
    │           └── MainActivity.java # WebView, JS bridge, Share intent & JobScheduler
    └── gradlew.bat             # Windows Gradle wrapper build script
```

### 📄 Detailed File Descriptions

| File / Directory | Description & Purpose |
|---|---|
| 🐍 `app.py` | Main Flask web application. Serves the frontend UI (`index.html`), endpoints for jobs filtering, stats, manual scrape trigger, and full Excel export. |
| 🗄️ `db.py` | SQLite DAL layer (`jobs.db`). Handles table creation (`jobs`, `meta`), degree detection (`detect_degrees`), chronological queries, and persistent sync timestamps (`set_last_sync_time`). |
| 🕷️ `scraper.py` | Scraping engine using `requests` & `BeautifulSoup`. Extracts listing pages & deep detail pages for both PharmaBharat & PharmaRecruiter. |
| 🤖 `monitor.py` | Background loop script. Runs periodic scraping cycles, updates SQLite DB sync timestamps, and dispatches new job notifications. |
| 📢 `notifier.py` | Sends formatted Telegram alerts when new jobs are detected. |
| 📱 `android-app/` | Android Studio Native project wrapper around WebView. Integrates Android Native Share Sheet and system `JobScheduler` background sync. |
| 🎨 `templates/index.html` | Premium dark/light responsive Web UI. Utilizes CSS Grid, Glassmorphism, Bottom Sheet Modals, and Lucide vector icons. |

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
| `/api/job/<slug>` | `GET` | Fetch single job details | — |
| `/api/stats` | `GET` | Fetch dashboard metrics & last sync timestamp | — |
| `/api/categories` | `GET` | List distinct job categories | — |
| `/api/locations` | `GET` | List distinct job locations | — |
| `/api/scrape/trigger` | `POST` | Manually trigger a background scrape | `pages` (default: 1) |
| `/api/export` | `GET` | Export scraped jobs as Excel CSV | `degree`, `category`, `fresher_only` |

---

## 🛠️ Building the Android APK Locally

To compile the Android App locally using Gradle CLI:

```powershell
# Set Android SDK and Java Environment Variables (Windows PowerShell)
$env:ANDROID_HOME = "C:\Users\YOUR_USERNAME\AppData\Local\Android\Sdk"
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"

# Navigate to android-app directory
cd android-app

# Build Debug APK
.\gradlew.bat assembleDebug
```
The output APK will be generated at:
`android-app/app/build/outputs/apk/debug/app-debug.apk`

---

## 📜 Legal & Fair Use Notice

This project was developed strictly for personal job search assistance and educational purposes. Scraping logic incorporates low-frequency requests with delays to minimize server impact. Always adhere to target website Terms of Service.

---

### 👨‍💻 Maintained with ❤️ by the PharmaBharat Pro Team
