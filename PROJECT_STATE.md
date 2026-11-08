# PROJECT_STATE.md

## Goal
Implement automatic 3-minute client-side auto-refresh on the public website with a live countdown timer, in-place data updates (preserving search/filters), and manual refresh capability.

## What Changed
- Initiating update to `site_generator.py` and `docs/index.html` to add:
  - 3-minute auto-refresh polling `data.json?t=[timestamp]`.
  - Visual countdown indicator (`Auto-refresh: 3:00`) with quick-refresh button.
  - In-place DOM re-rendering that preserves active filters, sort orders, and search inputs without full page flickers.
  - Graceful fallback to `location.reload()` if network fetch encounters errors.

## Commands Run + Results
- `read_file D:/Code Projects/MacEbayScanner/mac_ebay_scanner/site_generator.py` -> Inspected current site generator HTML structure and JS logic.

## Files Touched
- `mac_ebay_scanner/site_generator.py`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Edit `mac_ebay_scanner/site_generator.py` to embed client-side 3-minute auto-refresh, timer badge, and in-place DOM updates.
- [ ] Regenerate docs via `main.py build-site` and verify locally with tests.
- [ ] Push changes to GitHub and sync with `encoder1`.
