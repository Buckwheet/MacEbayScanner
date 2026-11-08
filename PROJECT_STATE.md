# PROJECT_STATE.md

## Goal
Add "Discovered" timestamp and "Updated" (price change tracking with previous price and delta) to each listing card in the dashboard, with sorting and filtering options.

## What Changed
- Added `get_price_history_map()` to `mac_ebay_scanner/storage.py` and included `last_updated_at` in item retrieval queries.
- Updated `mac_ebay_scanner/site_generator.py`:
  - Formatted `discovered_str` in CST for all listings from `first_seen_at`.
  - Added price change detection evaluating sequential price history records and `last_updated_at`.
  - Computed `previous_price`, `price_change_diff`, and `price_change_pct`.
  - Enhanced dashboard UI:
    - Added "Discovered: [Time] ([TimeAgo])" to each card (both verified matches and filtered-out cards).
    - Added "Price Updated" badge (showing delta $ and %) and crossed-out previous price on updated listings.
    - Added "Price Updates ([count])" counter to the status strip.
    - Added "🔄 Price Updated ([count])" quick-filter pill button.
    - Added sort options: "🕒 Newest Discovered", "⏳ Oldest Discovered", and "🔄 Recently Updated (Price Change)".
- Added test `test_discovered_and_price_update_tracking` in `tests/test_market_and_pricing.py` (24/24 tests pass).
- Built static website files (`docs/data.json`, `docs/index.html`).

## Commands Run + Results
- `pytest "D:\Code Projects\MacEbayScanner\tests" -v` -> 24 passed in 0.45s.
- `python "D:\Code Projects\MacEbayScanner\main.py" build-site` -> Website successfully generated in `docs/`.

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
- [x] Run unit tests (24/24 pass) and build static site.
- [ ] Commit and push changes to GitHub `origin/main`.
- [ ] Deploy to `encoder1`, rebuild site docs with live database, restart service, and verify live GitHub Pages site.
