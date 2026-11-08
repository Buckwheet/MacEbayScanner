# PROJECT_STATE.md

## Goal
Build and deploy a public GitHub Pages live dashboard for M3+ 128GB Mac listings and price trends, shorten the Pushbullet morning digest to a clean summary linking to the site, and automate GitHub Pages deployment from `encoder1`.

## What Changed
- Created public GitHub repository: [`https://github.com/Buckwheet/MacEbayScanner`](https://github.com/Buckwheet/MacEbayScanner).
- Enabled GitHub Pages from `/docs` directory: live at [https://buckwheet.github.io/MacEbayScanner/](https://buckwheet.github.io/MacEbayScanner/).
- Implemented static site generator `mac_ebay_scanner/site_generator.py`:
  - Renders real-time category market price trends (Lowest, Average, Median).
  - Modern dark-mode responsive UI with model/deal filters, search bar, and price sorting.
  - Interactive cards featuring thumbnails, deal badges (`🔥 X% Under Market`), specs, LOQ AI value assessments, and direct eBay links.
- Shortened Pushbullet overnight 5:00 AM CST digest to a clean, readable 5-line alert featuring the top 3 best deals and direct link to the live dashboard.
- Configured dedicated ed25519 deploy key on `encoder1` with write access, enabling the background service on `encoder1` to automatically regenerate and publish live dashboard updates to GitHub Pages.

## Commands Run + Results
- `gh repo create MacEbayScanner --public --source=. --remote=origin --push` -> Created public repository on GitHub.
- `gh api -X POST repos/Buckwheet/MacEbayScanner/pages` -> Enabled GitHub Pages for `/docs`.
- `Invoke-WebRequest -Uri 'https://buckwheet.github.io/MacEbayScanner/'` -> HTTP 200 (Dashboard live).
- `python main.py digest --test` -> Verified shortened Pushbullet digest dispatched.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git push origin main"` -> Successfully pushed live data from `encoder1`.

## Files Touched
- `D:\Code Projects\MacEbayScanner\.gitignore`
- `D:\Code Projects\MacEbayScanner\docs\index.html`
- `D:\Code Projects\MacEbayScanner\docs\data.json`
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\site_generator.py`
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\notifier.py`
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\scanner.py`
- `D:\Code Projects\MacEbayScanner\mac_ebay_scanner\cli.py`
- `D:\Code Projects\MacEbayScanner\PROJECT_STATE.md`
- `encoder1:/home/encoder1/MacEbayScanner/*`

## Next 3 Actions
- [x] Published public GitHub Pages site and verified HTTP 200.
- [x] Shortened Pushbullet 5am digest to concise summary with link.
- [x] Configured auto-publishing pipeline from `encoder1`.
