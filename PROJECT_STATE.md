# PROJECT_STATE.md

## Goal
Detect and remove sold/ended eBay items from active matched listings in the scanner, local database, and public GitHub Pages dashboard.

## What Changed
- Added `check_item_availability()` to `mac_ebay_scanner/ebay_client.py`:
  - Detects `OUT_OF_STOCK` and 0 remaining/available quantity in `estimatedAvailabilities`.
  - Detects expired `itemEndDate` in the past (`LISTING_ENDED`).
  - Detects 404 / `None` from eBay Browse API (`NOT_FOUND_OR_ENDED`).
- Updated `mac_ebay_scanner/storage.py`:
  - Added `is_sold INTEGER DEFAULT 0` and `sold_at TEXT` columns with indexes to `seen_items`.
  - Added methods `mark_item_sold()`, `mark_item_active()`, `delete_item()`, `delete_sold_items()`, and `get_sold_items()`.
  - Updated `get_matched_items()` to filter out sold items by default (`include_sold=False`).
  - Updated `get_stats()` to track `active_matched` and `total_sold`.
  - Updated `get_queued_digest_items()` and `check_and_update_price()` to bypass sold items.
- Updated `mac_ebay_scanner/scanner.py`:
  - Added `check_sold_items(max_items=5)` to perform round-robin checks on active matched listings without exceeding eBay API rate limits.
  - Automatically marks sold items in storage and flags `has_updates` to trigger site push.
  - Reactivates listings if a previously sold item reappears in active eBay search results.
- Updated `mac_ebay_scanner/site_generator.py`:
  - Main listing cards only display active (unsold) matches.
  - Added "Sold / Ended" view mode switcher tab and card styling with "SOLD / ENDED" badges and "Ended on eBay" links.
  - Updated status strip to display active matching machines.
- Updated `mac_ebay_scanner/cli.py`:
  - Added `remove-sold` / `check-sold` command (with optional `--purge` for permanent deletion).
  - Added `--all` and `--sold-only` options to `matches` command.
  - Added `active_matched` and `total_sold` metrics to `stats` command.
- Updated `service_encoder1.ps1` and `README.md` with sold removal actions.
- Added comprehensive unit tests in `tests/test_sold_detection.py` (31/31 passed).

## Commands Run + Results
- `python -m pytest "D:\Code Projects\MacEbayScanner\tests" -v` -> 31 passed in 0.67s.
- `python "D:\Code Projects\MacEbayScanner\main.py" remove-sold` -> Checked 52 matched items: 43 active, 9 sold/ended detected and marked as sold, site rebuilt cleanly.
- `python "D:\Code Projects\MacEbayScanner\main.py" stats` -> Active Matching Machines: 43, Sold / Ended Items: 9.
- `python "D:\Code Projects\MacEbayScanner\main.py" matches --sold-only` -> Clean table listing all 9 sold/ended items with specs and pricing.

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
- [x] Implement sold detection and storage tracking.
- [x] Update scanner, site generator, and CLI commands.
- [x] Deploy to `encoder1`, verify live service, and verify GitHub Pages site.
