# PharmaBharat Job Tracker

Apna khud ka scraper + webapp jo PharmaBharat.com se jobs nikalta hai,
fresher jobs ko genuinely alag dikhata hai, aur naye jobs aane par
Telegram pe notify karta hai. Koi AI/paid API call nahi -- pura
rule-based HTML parsing (requests + BeautifulSoup + regex).

## ⚠️ Pehle yeh padho

PharmaBharat.com ki Terms & Conditions automated scraping ko
explicitly prohibit karti hain ("Using automated tools or software to
access, scrape, or collect data from the Website without our
permission"). Yeh tool sirf **personal, low-frequency use** ke liye
banaya hai:

- Delay values (`delay=`) kam mat karo -- 2 second se zyada hi rakho.
- Isse public product / paid service mat banao, na kisi aur ko resell
  karo.
- Agar chaho to unhe ek baar email kar dena (site pe contact form /
  `vaishalilaxmi190@gmail.com`) permission ke liye -- chhote job
  boards aksar personal aggregator ke liye mana nahi karte agar pooch
  liya jaye.
- Agar wo kabhi block/rate-limit karein, ruk jaana -- retry-spam mat
  karna.

## Setup

```bash
cd pharmabharat-scraper
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 1. Pehli baar data lao

Sirf recent jobs (fast, ~2-3 min):
```bash
python scraper.py
```

Poori site ka historical crawl (764 pages tak, bahut slow -- kai
ghante lag sakte hain, chahiye to raat ko chalao):
```bash
python scraper.py full
```

Agar extraction galat lage (title/company/experience missing ya
gadbad), yeh chalao aur output dekho:
```bash
python scraper.py debug
```
Iska output dekh ke `scraper.py` ke regex patterns (DATE_RE,
EXPERIENCE_RE, SALARY_RE, APPLICATION_TYPES) ya `CONTENT_SELECTORS`
list ko adjust kar lena -- website ka HTML kabhi badal jaye to yehi
jagah update karni hogi.

## 2. Telegram notification setup (naye job ka alert)

1. Telegram kholo, `@BotFather` ko message karo.
2. `/newbot` bhejo, ek naam do -- tumhe ek **bot token** milega
   (kuch aisa: `123456:ABC-xyz...`).
3. Apna naya bot search karke usko koi bhi message bhejo (e.g. "hi"),
   taaki wo tumhara chat pehchan sake.
4. Yeh URL browser mein kholo (BOT_TOKEN apna daal ke):
   ```
   https://api.telegram.org/bot<BOT_TOKEN>/getUpdates
   ```
   JSON response mein `"chat":{"id": 123456789}` dikhega -- yehi
   tumhara **chat ID** hai.
5. Environment variables set karo:
   ```bash
   export TG_BOT_TOKEN="123456:ABC-xyz..."
   export TG_CHAT_ID="123456789"
   ```
   (Windows PowerShell: `$env:TG_BOT_TOKEN="..."`)

## 3. Monitoring chalu karo (background mein har 30 min check)

```bash
python monitor.py
```
Isse chalta chhod do (ya `nohup python monitor.py &` Linux/Mac pe, ya
Task Scheduler Windows pe) -- jab bhi koi naya job aayega, Telegram
pe turant message aa jayega.

## 4. Webapp dekho

```bash
python app.py
```
Browser mein: `http://localhost:5000`

Filters: category dropdown, "Fresher only" toggle (genuine -- site ke
apne experience field se derive hota hai, title-guessing nahi),
"Verified only" toggle, aur search box.

## Files kya karti hain

| File | Kaam |
|---|---|
| `scraper.py` | Listing pages + detail pages scrape karta hai |
| `db.py` | SQLite storage (`jobs.db` -- ek hi file, koi server nahi) |
| `notifier.py` | Telegram message bhejta hai |
| `monitor.py` | Har N minute mein scrape + notify loop |
| `app.py` | Flask backend + webapp serve karta hai |
| `templates/index.html` | Frontend UI |

## Fresher filter kaise kaam karta hai

Site khud har job card pe experience field deti hai ("Fresher",
"0-2 Years", "2-10 Years" waghera). Hum isi text se dो flags nikalte
hain:

- `is_fresher`: text mein explicitly "Fresher"/"Freshers" likha ho
- `is_fresher_friendly`: upar wala + "0-X years" jaisi range bhi
  (matlab fresher apply kar sakta hai, chahe title "Fresher" na kahe)

Isse title mein "Freshers Preferred" jaise misleading tags pe bharosa
nahi karna padta -- asli experience-range field use hoti hai.

## Agar scraping selectors kaam na karein

Website ka design change ho sakta hai kabhi bhi. Agar `scraper.py debug`
ka output khaali ya galat aaye:
1. Browser mein `view-source:https://pharmabharat.com/` kholo.
2. Ek job card dhoondo, uske around ka HTML dekho.
3. `parse_listing_page()` function mein jo heuristics hain (Apply Now
   link dhoondna, parent container lena, regex se fields nikalna)
   unko us naye HTML ke hisaab se adjust karo.
