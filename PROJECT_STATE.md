# PROJECT_STATE.md

## Goal
Investigate and fix Unified Memory claim bug where 256GB listings displayed "128GB Unified Memory" in card footers, normalize RAM detection across storage and site generation, and visually distinguish 128GB vs 256GB models with prominent memory badges.

## What Changed
- Diagnosed root cause: Earlier site generator had hardcoded `<span class="text-xs text-gray-500 font-mono">128GB Unified Memory</span>` in the client-side HTML template card footer from before 256GB support was introduced. In addition, unnormalized strings like `"128GB Unified Memory"` caused duplicated labels.
- Updating `storage.py` with automatic schema normalization to clean legacy database rows to canonical `'128GB'` or `'256GB'`.
- Updating `site_generator.py` to:
  - Normalize RAM display (`256GB Unified Memory` vs `128GB Unified Memory`).
  - Add prominent color-coded badges to card headers (`[256GB RAM]` in purple, `[128GB RAM]` in cyan).
  - Explicitly render memory in card footers based on verified machine memory.
- Updating `notifier.py` to reference `128GB/256GB` instead of hardcoded `128GB` in overnight digests.

## Commands Run + Results
- `git grep '128GB Unified Memory'` -> Identified hardcoded strings in older HTML templates and unnormalized items in data.json.
- `ssh encoder1 "cd /home/encoder1/MacEbayScanner && python3 main.py matches --limit 15"` -> Confirmed backend SQLite database correctly classified M3/M5 Ultra models with 256GB RAM.

## Files Touched
- `mac_ebay_scanner/storage.py`
- `mac_ebay_scanner/site_generator.py`
- `mac_ebay_scanner/notifier.py`
- `PROJECT_STATE.md`

## Next 3 Actions
- [ ] Apply code updates in `storage.py`, `site_generator.py`, and `notifier.py`.
- [ ] Run test suite (`pytest tests -v`) and verify no regressions.
- [ ] Build site, push to GitHub, and deploy to `encoder1`.
