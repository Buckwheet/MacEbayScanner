# MacEbayScanner 🍎🔍

Automated eBay listing monitor specifically tailored for **Apple M3 or higher MacBook Pro or Mac Studio machines with 128GB of Unified Memory**, with real-time push notifications delivered directly to your devices via **Pushbullet**.

---

## Features

- **Strict Hardware Filtering**:
  - Requires **MacBook Pro** or **Mac Studio**.
  - Requires Apple Silicon **M3, M4, or higher** (rejects older M1, M2, and Intel architectures).
  - Requires **128GB RAM / Unified Memory** (actively avoids the "128GB SSD" trap where older laptops have 128GB storage with 8GB/16GB RAM).
  - Filters out accessories, cases, screen protectors, chargers, empty boxes, and (by default) "for parts / not working" or iCloud locked items.
- **Aspect-Level Verification**:
  - Automatically fetches full listing aspects (`localizedAspects`) from eBay's Browse API to inspect processor, memory, and model metadata.
- **Pushbullet Alerts**:
  - Delivers clickable rich push notifications to your phone, desktop, or browser with direct links, price, seller info, and exact specs.
- **Duplicate Prevention**:
  - Embedded SQLite database (`data/seen_items.db`) ensures you are never notified about the same listing twice.
- **Customizable**:
  - Configurable scan intervals, price limits, queries, and parts/repair inclusion via `.env`.

---

## Directory Layout

```
D:\Code Projects\MacEbayScanner\
├── .env                  # API keys and configuration
├── .env.example          # Template environment file
├── config.json           # Optional configuration settings
├── requirements.txt      # Python dependencies
├── main.py               # Root entrypoint
├── run_scanner.bat       # Windows launcher batch script
├── PROJECT_STATE.md      # State & development log
├── mac_ebay_scanner/     # Core package
│   ├── config.py         # Configuration loader
│   ├── ebay_client.py    # eBay OAuth 2.0 & Browse API client
│   ├── filter_engine.py  # M3+ 128GB matching engine
│   ├── notifier.py       # Pushbullet notification dispatcher
│   ├── storage.py        # SQLite database manager
│   ├── scanner.py        # Polling coordinator
│   └── cli.py            # CLI commands
└── tests/
    └── test_filter_engine.py  # Unit test suite
```

---

## Setup & Configuration

### 1. Configure Pushbullet Token

1. Go to [Pushbullet Account Settings](https://www.pushbullet.com/#settings/account).
2. Click **Create Access Token**.
3. Set your token using the CLI:
   ```powershell
   python main.py set-token <your_pushbullet_access_token>
   ```
   Or edit `.env` directly:
   ```env
   PUSHBULLET_API_TOKEN=o.abcdef123456789...
   ```

### 2. Test Connections

- **Test eBay API connection and recent sample queries:**
  ```powershell
  python main.py test-ebay
  ```

- **Test Pushbullet notification delivery:**
  ```powershell
  python main.py test-pushbullet
  ```

---

## Running the Monitor

### Continuous Monitor (Daemon)
Runs in the background and scans eBay every 180 seconds (or custom interval):
```powershell
python main.py scan
```
To run with a custom interval (e.g., every 60 seconds):
```powershell
python main.py scan --interval 60
```

### Single Scan Pass
Perform a one-time scan pass across all queries and display stats:
```powershell
python main.py scan --once
```

### View Found Matches
View all M3+ 128GB Macs stored in the local database:
```powershell
python main.py matches
```

### View Statistics
```powershell
python main.py stats
```

### Check & Remove Sold / Ended Listings
Scan active matched listings against eBay's Browse API and mark or remove sold items:
```powershell
python main.py remove-sold
```
To permanently delete sold items from the database instead of archiving:
```powershell
python main.py remove-sold --purge
```

---

## Run as a Windows Background Task / Startup

To run the monitor on Windows startup automatically:
1. Press `Win + R`, type `shell:startup`, and press Enter.
2. Create a shortcut to `run_scanner.bat`.
3. Or schedule it using Windows Task Scheduler to run at user logon.
