# PROJECT_STATE.md

## Goal
Enable full visibility into all evaluated eBay listings (228 total) on the public website, allowing inspection of the 150 filtered-out listings alongside the 78 verified matches with clear rejection reasons to ensure no valid target machines are overlooked.

## What Changed
- Identified that 21 genuine 256GB Mac Studio / M4 Max listings were previously marked as unmatched because they were scanned before 256GB criteria were enabled; built and executed `reconcile_unmatched_items()` in `storage.py` to rescue them into verified matches.
- Verified matches increased from 57 to 78 listings.
- Added `filter_reason` column to SQLite schema in `storage.py` and updated `scanner.py` to persist human-readable rejection reasons whenever a candidate is filtered out.
- Updated `site_generator.py` and `docs/index.html` with:
  - Tri-state View Mode Switcher:
    - **`Verified Matches (78)`** (default view with deal badges, LOQ AI analysis, and memory tags)
    - **`Filtered Out (150)`** (shows excluded listings with clear amber rejection reason boxes, e.g. Intel i5/i7, M1/M2 chips, 256GB SSD storage trap with low RAM)
    - **`All Evaluated (228)`** (shows complete catalog of scanned items)
  - Search and sort controls work dynamically across all view modes.
  - "Inspect on eBay" direct link on all rejected cards so users can review the original eBay listing.
- Deployed to `encoder1`; service restarted cleanly and verified live on GitHub Pages.

## Commands Run + Results
- `pytest tests -v` -> 17/17 tests passed.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && python3 main.py build-site"` -> Generated 228 items in `docs/data.json`.
- `python -c "import urllib.request... print('Found tabMatched in live HTML:', True)"` -> Verified `tabMatched` and `tabFiltered` live on GitHub Pages.
- `ssh encoder1 "systemctl --user status mac-ebay-scanner.service --no-pager"` -> Verified daemon active (PID 456295) polling every 180s.

## Files Touched
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/scanner.py`
- `mac_ebay_scanner/site_generator.py`
- `docs/index.html`
- `docs/data.json`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Monitor incoming eBay matches during daytime window (8:00 AM - 8:00 PM CST) on Pushbullet.
- [ ] Verify 15-minute heartbeat auto-publish triggers on GitHub Pages without manual intervention.
- [ ] Verify overnight queue transition and 5:00 AM CST summary digest generation.
