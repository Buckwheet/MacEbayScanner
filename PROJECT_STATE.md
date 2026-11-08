# PROJECT_STATE.md

## Goal
Add "Discovered" timestamp and "Updated" (price change tracking with previous price and delta) to each listing card in the dashboard, with sorting and filtering options.

## What Changed
- Added `get_price_history_map()` in `mac_ebay_scanner/storage.py` to extract full historical price timelines and included `last_updated_at` in queries.
- Updated `mac_ebay_scanner/site_generator.py`:
  - Formatted `discovered_str` in CST for all items from `first_seen_at`.
  - Added price change detection computing `previous_price`, `price_change_diff`, and `price_change_pct`.
  - Enhanced dashboard UI:
    - Added "Discovered: [Time] ([TimeAgo])" to each card (both verified matches and filtered-out cards).
    - Added "Price Updated" badge (showing delta $ and %) and crossed-out previous price on updated listings.
    - Added "Price Updates ([count])" counter to the status strip.
    - Added "🔄 Price Updated ([count])" quick-filter pill button.
    - Added sort options: "🕒 Newest Discovered", "⏳ Oldest Discovered", and "🔄 Recently Updated (Price Change)".
- Added test `test_discovered_and_price_update_tracking` in `tests/test_market_and_pricing.py` (24/24 tests pass).
- Deployed to remote host `encoder1`, rebuilt site docs with live database, and verified GitHub Pages live deployment.

## Commands Run + Results
- `pytest "D:\Code Projects\MacEbayScanner\tests" -v` -> 24 passed in 0.45s.
- `python "D:\Code Projects\MacEbayScanner\main.py" build-site` -> Website generated cleanly in `docs/`.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && git pull origin main && python3 main.py build-site && ..."` -> Built on encoder1, committed and pushed `7c69c97..796a2ba`.
- `gh api repos/Buckwheet/MacEbayScanner/pages/builds/latest` -> Build completed (`status: built`).
- `curl.exe -s "https://buckwheet.github.io/MacEbayScanner/"` -> Live site confirmed rendering "Discovered" and "Price Updated" on listing cards and controls.

## Files Touched
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/site_generator.py`
- `tests/test_market_and_pricing.py`
- `docs/data.json`
- `docs/index.html`
- `PROJECT_STATE.md`

## Next 3 Actions
- [x] Extract `first_seen_at`, `last_updated_at`, and price history delta in `storage.py` and `site_generator.py`.
- [x] Enhance listing cards, sorting options, and filter controls in the dashboard template.
- [x] Run unit tests (24/24 pass), deploy to `encoder1`, and verify live dashboard.
