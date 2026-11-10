# PROJECT_STATE.md

## Goal
Detect and remove sold/ended eBay items from active matched listings in the scanner, local database, and public GitHub Pages dashboard.

## What Changed
- Added `check_item_availability()` to [ebay_client.py](file:///D:/Code%20Projects/MacEbayScanner/mac_ebay_scanner/ebay_client.py):
  - Detects `OUT_OF_STOCK` and 0 remaining/available quantity in `estimatedAvailabilities`.
  - Detects expired `itemEndDate` in the past (`LISTING_ENDED`).
  - Detects 404 / `None` from eBay Browse API (`NOT_FOUND_OR_ENDED`).
- Updated [storage.py](file:///D:/Code%20Projects/MacEbayScanner/mac_ebay_scanner/storage.py):
  - Added `is_sold INTEGER DEFAULT 0` and `sold_at TEXT` columns with indexes to `seen_items`.
  - Added methods `mark_item_sold()`, `mark_item_active()`, `delete_item()`, `delete_sold_items()`, and `get_sold_items()`.
  - Updated `get_matched_items()` to filter out sold items by default (`include_sold=False`).
  - Updated `get_stats()` to track `active_matched` and `total_sold`.
  - Updated `get_queued_digest_items()` and `check_and_update_price()` to bypass sold items.
- Updated [scanner.py](file:///D:/Code%20Projects/MacEbayScanner/mac_ebay_scanner/scanner.py):
  - Added `check_sold_items(max_items=5)` to perform round-robin checks on active matched listings without exceeding eBay API rate limits.
  - Automatically marks sold items in storage and flags `has_updates` to trigger site push.
  - Reactivates listings if a previously sold item reappears in active eBay search results.
- Updated [site_generator.py](file:///D:/Code%20Projects/MacEbayScanner/mac_ebay_scanner/site_generator.py):
  - Main listing cards only display active (unsold) matches.
  - Added "Sold / Ended" view mode switcher tab and card styling with "SOLD / ENDED" badges and "Ended on eBay" links.
  - Updated status strip to display active matching machines.
- Updated [cli.py](file:///D:/Code%20Projects/MacEbayScanner/mac_ebay_scanner/cli.py):
  - Added `remove-sold` / `check-sold` command (with optional `--purge` for permanent deletion).
  - Added `--all` and `--sold-only` options to `matches` command.
  - Added `active_matched` and `total_sold` metrics to `stats` command.
- Updated [service_encoder1.ps1](file:///D:/Code%20Projects/MacEbayScanner/service_encoder1.ps1) and [README.md](file:///D:/Code%20Projects/MacEbayScanner/README.md) with sold removal actions.
- Added unit tests in [test_sold_detection.py](file:///D:/Code%20Projects/MacEbayScanner/tests/test_sold_detection.py) (31/31 passed).
- Deployed to remote host `encoder1`, swept 96 listings (16 marked sold, 80 active), restarted `mac-ebay-scanner.service`, and verified live GitHub Pages deployment.

## Commands Run + Results
- `python -m pytest "D:\Code Projects\MacEbayScanner\tests" -v` -> 31 passed in 0.67s.
- `python "D:\Code Projects\MacEbayScanner\main.py" remove-sold` -> Local DB: 43 active, 9 sold/ended removed.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git pull origin main && python3 main.py remove-sold && ..."` -> Encoder1 DB: 80 active, 16 sold/ended removed.
- `curl.exe -s "https://buckwheet.github.io/MacEbayScanner/"` -> Live site confirmed displaying "Active Matches" and "Sold / Ended".

## Files Touched
- `mac_ebay_scanner/ebay_client.py`
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/scanner.py`
- `mac_ebay_scanner/site_generator.py`
- `mac_ebay_scanner/cli.py`
- `tests/test_sold_detection.py`
- `service_encoder1.ps1`
- `README.md`
- `docs/data.json`
- `docs/index.html`
- `PROJECT_STATE.md`

## Next 3 Actions
- [x] Implement sold item detection and database tracking (`is_sold`, `sold_at`).
- [x] Update scanner daemon, dashboard UI, and CLI commands.
- [x] Deploy to `encoder1`, sweep live database, and verify GitHub Pages.
