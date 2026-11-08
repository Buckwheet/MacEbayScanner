# PROJECT_STATE.md

## Goal
Enable full visibility into all evaluated eBay listings (226 total) on the public website, allowing inspection of the 169 filtered-out listings alongside the 57 verified matches with clear rejection reasons to ensure no valid target machines are overlooked.

## What Changed
- Updating `storage.py` to add `filter_reason` column migration and `get_all_seen_items()` method.
- Updating `scanner.py` to store `filter_reason` on non-matching listings.
- Updating `site_generator.py` to include both verified matches and filtered listings in `data.json`, backfilling reasons dynamically using `MacListingFilter` for legacy rows.
- Updating website UI in `docs/index.html` with:
  - Top tab toggle: `Verified Matches (57)` | `Filtered Out (169)` | `All Evaluated (226)`
  - Clear rejection reason tags on filtered cards (e.g., `⚠️ Filtered: Processor aspect indicates older chip: M1 Max`, `⚠️ Filtered: 256GB SSD storage, not RAM`).
  - Search and filter capability across both matched and filtered listings.

## Commands Run + Results
- `read_file storage.py` -> Inspected schema and query structure for `seen_items`.

## Files Touched
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/scanner.py`
- `mac_ebay_scanner/site_generator.py`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Add `filter_reason` to `storage.py` schema and add `get_all_seen_items()` method.
- [ ] Update `scanner.py` to record `filter_reason` on rejected candidates.
- [ ] Update `site_generator.py` to render both matched and filtered listings with filter tabs and rejection badges.
