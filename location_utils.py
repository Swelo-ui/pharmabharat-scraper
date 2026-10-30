import re

LOCATION_CLUSTERS = [
    {
        "canonical": "Hyderabad",
        "slug": "hyderabad",
        "aliases": [
            "hyderabad", "secunderabad", "sangareddy", "patancheru", "jeedimetla",
            "gachibowli", "choutuppal", "pashamylaram", "genome valley", "cherlapally",
            "balanagar", "nanakramguda", "shameerpet", "shamshabad", "dundigal",
            "uppal", "turkapally", "bonthapally", "rudraram", "penjerla", "kollur",
            "kazipally", "mallapur", "nacharam", "medchal", "shadnagar", "chandanagar",
            "chityal", "kothur", "jadcherla"
        ]
    },
    {
        "canonical": "Bengaluru / Bangalore",
        "slug": "bengaluru",
        "aliases": [
            "bengaluru", "bangalore", "bommasandra", "electronic city", "whitefield",
            "yeshwantpur", "peenya", "jigani", "hosur", "hebbal", "koramangala",
            "marathahalli", "sarjapur", "yelahanka", "bellandur"
        ]
    },
    {
        "canonical": "Ahmedabad",
        "slug": "ahmedabad",
        "aliases": [
            "ahmedabad", "ahmadabad", "sanand", "changodar", "bavla", "matoda",
            "sachana", "kadi", "chacharwadi", "moraiya", "vatva", "naroda",
            "odhav", "rajoda", "sarkhej", "santej", "asoj", "dholka"
        ]
    },
    {
        "canonical": "Mumbai / MMR",
        "slug": "mumbai",
        "aliases": [
            "mumbai", "bombay", "navi mumbai", "thane", "tarapur", "boisar",
            "palghar", "andheri", "kurla", "sakinaka", "airoli", "mahape",
            "turbhe", "vashi", "belapur", "panvel", "kalyan", "bhiwandi",
            "ambernath", "dombivli", "taloja", "ghansoli", "rabale"
        ]
    },
    {
        "canonical": "Vadodara (Baroda)",
        "slug": "vadodara",
        "aliases": [
            "vadodara", "baroda", "halol", "savli", "kalol", "nandesari",
            "padra", "karkhadi", "karakhadi", "tandalja", "ranu", "jarod",
            "alindra", "waghodia", "manjusar", "chhani", "makarpura"
        ]
    },
    {
        "canonical": "Gurugram / Delhi NCR",
        "slug": "gurugram",
        "aliases": [
            "gurgaon", "gurugram", "manesar", "noida", "greater noida", "delhi",
            "new delhi", "faridabad", "ghaziabad", "sohna", "udyog vihar"
        ]
    },
    {
        "canonical": "Baddi (Himachal)",
        "slug": "baddi",
        "aliases": [
            "baddi", "solan", "nalagarh", "paonta sahib", "kala amb", "mehatpur",
            "sandholi", "parwanoo", "tahliwal", "himachal"
        ]
    },
    {
        "canonical": "Indore / Pithampur",
        "slug": "indore",
        "aliases": [
            "indore", "pithampur", "pologround", "dewas", "dhar", "sanwer"
        ]
    },
    {
        "canonical": "Pune",
        "slug": "pune",
        "aliases": [
            "pune", "hinjewadi", "chakan", "hadapsar", "kurkumbh", "shirwal",
            "ranjangaon", "pirangut", "bhosari", "kharadi", "magarpatta"
        ]
    },
    {
        "canonical": "Visakhapatnam (Vizag)",
        "slug": "visakhapatnam",
        "aliases": [
            "visakhapatnam", "vizag", "parawada", "duvvada", "jnpc",
            "pydibhimavaram", "anakapalli", "gajuwaka", "sheelanagar", "achutapuram"
        ]
    },
    {
        "canonical": "Ankleshwar / Bharuch",
        "slug": "ankleshwar",
        "aliases": [
            "ankleshwar", "bharuch", "dahej", "panoli", "zaghadia", "jhagadia"
        ]
    },
    {
        "canonical": "Vapi / Daman",
        "slug": "vapi",
        "aliases": [
            "vapi", "daman", "silvassa", "sarigam", "valsad", "dabhel", "piparia"
        ]
    },
    {
        "canonical": "Chennai",
        "slug": "chennai",
        "aliases": [
            "chennai", "madras", "alathur", "sriperumbudur", "guindy",
            "tharamani", "irungattukottai", "maraimalai nagar", "ambattur"
        ]
    },
    {
        "canonical": "Chandigarh / Mohali",
        "slug": "chandigarh",
        "aliases": [
            "chandigarh", "mohali", "panchkula", "zirakpur", "dera bassi",
            "derabassi", "lalru"
        ]
    },
    {
        "canonical": "Haridwar / Dehradun",
        "slug": "haridwar",
        "aliases": [
            "haridwar", "dehradun", "rishikesh", "roorkee", "sidcul",
            "bhagwanpur", "selakui", "selaqui"
        ]
    },
    {
        "canonical": "Goa",
        "slug": "goa",
        "aliases": [
            "goa", "verna", "ponda", "kundaim", "tuem", "tivim", "mapusa",
            "panaji", "margao", "corlim"
        ]
    },
    {
        "canonical": "Sikkim",
        "slug": "sikkim",
        "aliases": [
            "sikkim", "rangpo", "ranipool", "majhitar", "gangtok", "singtam"
        ]
    },
    {
        "canonical": "Aurangabad",
        "slug": "aurangabad",
        "aliases": [
            "aurangabad", "chhatrapati sambhajinagar", "waluj", "shendra", "chikalthana"
        ]
    },
    {
        "canonical": "Kolkata",
        "slug": "kolkata",
        "aliases": [
            "kolkata", "calcutta", "howrah", "salt lake", "new town"
        ]
    },
    {
        "canonical": "Jaipur",
        "slug": "jaipur",
        "aliases": [
            "jaipur", "sitapura", "vishwakarma"
        ]
    },
    {
        "canonical": "Lucknow",
        "slug": "lucknow",
        "aliases": ["lucknow", "kursi road", "chinhat"]
    },
    {
        "canonical": "Nagpur",
        "slug": "nagpur",
        "aliases": ["nagpur", "butibori", "mihan", "kalmeshwar"]
    },
    {
        "canonical": "Surat",
        "slug": "surat",
        "aliases": ["surat", "hazira", "sachin", "ichhapore"]
    },
    {
        "canonical": "Bhopal",
        "slug": "bhopal",
        "aliases": ["bhopal", "mandideep", "govindpura"]
    },
    {
        "canonical": "Kochi / Kerala",
        "slug": "kochi",
        "aliases": ["kochi", "cochin", "trivandrum", "thiruvananthapuram", "malappuram", "kerala", "calicut", "kozhikode"]
    },
    {
        "canonical": "Mysore",
        "slug": "mysore",
        "aliases": ["mysore", "mysuru"]
    },
    {
        "canonical": "Guntur / Vijayawada",
        "slug": "guntur",
        "aliases": ["guntur", "vijayawada", "amaravati"]
    },
    {
        "canonical": "Remote / WFH",
        "slug": "remote",
        "aliases": ["remote", "work from home", "wfh", "virtual"]
    }
]

# Fast lookup map
_ALIAS_TO_CLUSTER = {}
for cluster in LOCATION_CLUSTERS:
    for alias in cluster["aliases"]:
        _ALIAS_TO_CLUSTER[alias] = cluster

def clean_raw_string(s):
    if not s:
        return ""
    # Strip markdown and table residue
    s = re.sub(r'[*_#|`~]', ' ', s)
    s = re.sub(r'(?i)\blocation\s*:\s*', ' ', s)
    s = re.sub(r'(?i)\bcountry\s*:\s*', ' ', s)
    s = re.sub(r'(?i)\bcompany\s+name\s*:\s*', ' ', s)
    s = re.sub(r'(?i)\bmarket\s*:\s*', ' ', s)
    # Reject company names
    if any(k in s.lower() for k in [
        "ltd", "limited", "pharma", "laboratories", "biophore", "granules", "lactose",
        "advantmed", "amneal", "jamp", "definitive healthcare", "indian air force", "railway"
    ]):
        return ""
    return re.sub(r'\s+', ' ', s).strip()

def match_cluster_text(text):
    if not text:
        return None
    cleaned = clean_raw_string(text).lower()
    if not cleaned or cleaned in ["india", "across india", "pan india", "multiple locations"]:
        return None
    for cluster in LOCATION_CLUSTERS:
        for alias in cluster["aliases"]:
            if re.search(r'\b' + re.escape(alias) + r'\b', cleaned):
                return cluster
    return None

def resolve_smart_location(raw_loc, title=None, desc=None):
    # 1. Try raw location
    cluster = match_cluster_text(raw_loc)
    
    # 2. If raw location failed or is generic country, try title
    if not cluster and title:
        cluster = match_cluster_text(title)
        
    # 3. If still nothing, try first 1200 chars of description
    if not cluster and desc:
        cluster = match_cluster_text(desc[:1200])

    if cluster:
        return {
            "canonical": cluster["canonical"],
            "slug": cluster["slug"],
            "display": cluster["canonical"]
        }

    # Fallback: clean up raw location if it exists
    c = clean_raw_string(raw_loc)
    if c and len(c) <= 35 and c.lower() not in ["india", "across india", "pan india"]:
        # Capitalize nicely
        parts = [p.strip() for p in c.split(",") if p.strip()]
        display = parts[0].title() if parts else c.title()
        return {
            "canonical": display,
            "slug": re.sub(r'[^a-z0-9]+', '-', display.lower()).strip('-'),
            "display": display
        }

    return {
        "canonical": "Pan-India / Multiple",
        "slug": "all",
        "display": "Pan-India"
    }

def get_aliases_for_query(query):
    if not query:
        return []
    q_lower = query.strip().lower()
    for cluster in LOCATION_CLUSTERS:
        if cluster["slug"] == q_lower or cluster["canonical"].lower() == q_lower:
            return cluster["aliases"]
        for alias in cluster["aliases"]:
            if alias == q_lower:
                return cluster["aliases"]
    # If no cluster matches exactly, check partial
    for cluster in LOCATION_CLUSTERS:
        if q_lower in cluster["slug"] or q_lower in cluster["canonical"].lower():
            return cluster["aliases"]
        for alias in cluster["aliases"]:
            if q_lower in alias or alias in q_lower:
                return cluster["aliases"]
    return [q_lower]


# ── Lightweight IP Geolocation Lookup ────────────────────────────
_IP_GEO_CACHE = {}

def lookup_ip_geo(ip: str):
    if not ip or ip.startswith("127.") or ip.startswith("192.168.") or ip.startswith("10.") or ip == "localhost":
        return {"city": "Local Dev", "region": "Local", "country": "Local"}
    if ip in _IP_GEO_CACHE:
        return _IP_GEO_CACHE[ip]
    try:
        import requests
        resp = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city", timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                geo = {
                    "city": data.get("city") or "Unknown City",
                    "region": data.get("regionName") or "",
                    "country": data.get("country") or "India"
                }
                _IP_GEO_CACHE[ip] = geo
                return geo
    except Exception:
        pass
    return {"city": "India", "region": "", "country": "India"}
